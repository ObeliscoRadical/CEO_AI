"""Camada autónoma de Growth/SEO sobre o gateway interno de publicação."""
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from core import active_company_id, ai_json, db, logger, premium_user
from google_growth import GoogleGrowthClient, google_growth_status, normalize_page_path, sync_windows
from routers.site_publishing import (
    SiteContentUpsertIn,
    SiteRelatedLinkIn,
    SiteSectionBlockIn,
    _get_settings as _site_settings,
    _live_owner_company_id,
    upsert_site_content,
)

router = APIRouter()

GROWTH_HARD_RULE = (
    "O agente NUNCA deve alterar design, layout, componentes, identidade visual, experiência de navegação "
    "ou estrutura do site; só pode atuar em conteúdo e SEO usando sempre o design system existente."
)

STATIC_PUBLIC_PAGES = [
    {"page_key": "login", "title": "Login / Landing", "public_url": "/login", "kind": "static"},
    {"page_key": "pricing", "title": "Planos", "public_url": "/planos", "kind": "static"},
    {"page_key": "contact", "title": "Contacto", "public_url": "/contacto", "kind": "static"},
    {"page_key": "privacy", "title": "Privacidade", "public_url": "/privacidade", "kind": "static"},
    {"page_key": "terms", "title": "Termos", "public_url": "/termos", "kind": "static"},
    {"page_key": "insights-hub", "title": "Insights", "public_url": "/insights", "kind": "static"},
]


class GrowthRunIn(BaseModel):
    force: bool = True
    use_ai: bool = False


class PublicTrackIn(BaseModel):
    page_key: str
    path: str
    title: str = ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _public_base_url() -> str:
    status = google_growth_status()
    return status.get("site_public_base_url") or ""


def _keyword_cluster(text: str) -> str:
    words = [item.strip().lower() for item in (text or "").replace("/", " ").replace("-", " ").split() if len(item.strip()) >= 3]
    return " ".join(words[:2]) if words else "geral"


async def _live_owner_identity() -> Optional[dict]:
    row = await db.site_publication_settings.find_one({"site_live_owner": True, "authorized": True}, {"_id": 0})
    if not row:
        row = await db.site_publication_settings.find_one({"authorized": True}, {"_id": 0}, sort=[("authorized_at", -1)])
    return row or None


async def _record_internal_view(uid: str, cid: str, page_key: str, page_path: str, title: str, kind: str):
    today = datetime.now(timezone.utc).date().isoformat()
    await db.growth_internal_page_daily.update_one(
        {"user_id": uid, "company_id": cid, "date": today, "page_key": page_key},
        {
            "$set": {
                "user_id": uid,
                "company_id": cid,
                "date": today,
                "page_key": page_key,
                "page_path": normalize_page_path(page_path),
                "title": title,
                "kind": kind,
                "updated_at": _now_iso(),
            },
            "$inc": {"views": 1},
        },
        upsert=True,
    )


async def _site_inventory(uid: str, cid: str) -> list[dict]:
    base_url = _public_base_url()
    entries = await db.site_content_entries.find(
        {"user_id": uid, "company_id": cid, "status": "published", "kind": {"$in": ["article", "page"]}},
        {"_id": 0},
    ).to_list(200)
    inventory = []
    for item in STATIC_PUBLIC_PAGES:
        inventory.append({
            **item,
            "entry_id": None,
            "seo_keyword": item["title"],
            "updated_at": None,
            "canonical_url": f"{base_url}{item['public_url']}" if base_url else item["public_url"],
            "is_static": True,
            "editorial_score": None,
        })
    for row in entries:
        public_url = row.get("public_url") or "/"
        inventory.append({
            "page_key": row.get("id"),
            "title": row.get("title"),
            "public_url": public_url,
            "entry_id": row.get("id"),
            "kind": row.get("kind"),
            "seo_keyword": row.get("seo_keyword") or row.get("title"),
            "updated_at": row.get("updated_at"),
            "canonical_url": row.get("canonical_url") or (f"{base_url}{public_url}" if base_url else public_url),
            "is_static": False,
            "editorial_score": row.get("editorial_score"),
        })
    return inventory


async def _upsert_snapshot(uid: str, cid: str, source: str, window: str, rows: list[dict], started_at: str, ended_at: str):
    for row in rows:
        await db.growth_page_snapshots.update_one(
            {"user_id": uid, "company_id": cid, "source": source, "window": window, "page_path": row.get("page_path")},
            {"$set": {"user_id": uid, "company_id": cid, "source": source, "window": window, "page_path": row.get("page_path"), **row, "started_at": started_at, "ended_at": ended_at, "updated_at": _now_iso()}},
            upsert=True,
        )


async def _upsert_query_snapshot(uid: str, cid: str, rows: list[dict], started_at: str, ended_at: str):
    for row in rows:
        await db.growth_query_snapshots.update_one(
            {"user_id": uid, "company_id": cid, "page_path": row.get("page_path"), "query": row.get("query")},
            {"$set": {"user_id": uid, "company_id": cid, **row, "started_at": started_at, "ended_at": ended_at, "updated_at": _now_iso()}},
            upsert=True,
        )


async def sync_growth_sources(uid: str, cid: str) -> dict:
    windows = sync_windows()
    status = google_growth_status()
    run = {
        "_id": str(uuid.uuid4()),
        "user_id": uid,
        "company_id": cid,
        "source_status": {
            "gsc": {"configured": status["gsc_configured"], "ok": False, "error": None},
            "ga4": {"configured": status["ga4_configured"], "ok": False, "error": None, "measurement_installed": status["ga4_measurement_installed"]},
            "internal": {"configured": True, "ok": True, "error": None},
        },
        "started_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    await db.growth_sync_runs.insert_one(run)

    if status["credentials_ready"] and status["gsc_configured"] and status["ga4_configured"]:
        try:
            client = GoogleGrowthClient()
            gsc_recent = client.search_console_pages(windows["recent"]["start"], windows["recent"]["end"])
            gsc_baseline = client.search_console_pages(windows["baseline"]["start"], windows["baseline"]["end"])
            gsc_queries = client.search_console_queries(windows["queries"]["start"], windows["queries"]["end"])
            await _upsert_snapshot(uid, cid, "gsc", "recent", gsc_recent, windows["recent"]["start"], windows["recent"]["end"])
            await _upsert_snapshot(uid, cid, "gsc", "baseline", gsc_baseline, windows["baseline"]["start"], windows["baseline"]["end"])
            await _upsert_query_snapshot(uid, cid, gsc_queries, windows["queries"]["start"], windows["queries"]["end"])
            run["source_status"]["gsc"]["ok"] = True
            run["source_status"]["gsc"]["rows"] = len(gsc_recent)
        except Exception as e:
            run["source_status"]["gsc"]["error"] = str(e)[:400]
            logger.error(f"growth gsc sync error: {e}")

        try:
            ga_recent = client.ga4_pages(windows["recent"]["start"], windows["recent"]["end"])
            ga_baseline = client.ga4_pages(windows["baseline"]["start"], windows["baseline"]["end"])
            await _upsert_snapshot(uid, cid, "ga4", "recent", ga_recent, windows["recent"]["start"], windows["recent"]["end"])
            await _upsert_snapshot(uid, cid, "ga4", "baseline", ga_baseline, windows["baseline"]["start"], windows["baseline"]["end"])
            run["source_status"]["ga4"]["ok"] = True
            run["source_status"]["ga4"]["rows"] = len(ga_recent)
        except Exception as e:
            run["source_status"]["ga4"]["error"] = str(e)[:400]
            logger.error(f"growth ga4 sync error: {e}")
    else:
        missing = []
        if not status["credentials_ready"]:
            missing.append("credencial Google ausente")
        if not status["gsc_configured"]:
            missing.append("GSC_SITE_URL ausente")
        if not status["ga4_configured"]:
            missing.append("GA4_PROPERTY_ID ausente")
        message = ", ".join(missing) or "configuração incompleta"
        run["source_status"]["gsc"]["error"] = message
        run["source_status"]["ga4"]["error"] = message

    run["updated_at"] = _now_iso()
    await db.growth_sync_runs.update_one({"_id": run["_id"]}, {"$set": run})
    return run


async def _page_snapshot_map(uid: str, cid: str, source: str, window: str) -> dict:
    rows = await db.growth_page_snapshots.find({"user_id": uid, "company_id": cid, "source": source, "window": window}, {"_id": 0}).to_list(5000)
    return {row.get("page_path"): row for row in rows}


async def _internal_view_map(uid: str, cid: str, days: int) -> dict:
    since = (datetime.now(timezone.utc).date() - timedelta(days=days - 1)).isoformat()
    rows = await db.growth_internal_page_daily.find({"user_id": uid, "company_id": cid, "date": {"$gte": since}}, {"_id": 0}).to_list(2000)
    totals = defaultdict(int)
    for row in rows:
        totals[row.get("page_path") or "/"] += int(row.get("views", 0) or 0)
    return totals


def _recent_vs_baseline(recent_value: float, baseline_total: float, baseline_days: int = 28, recent_days: int = 7) -> tuple[float, bool]:
    baseline_avg = (baseline_total / max(1, baseline_days)) * recent_days
    if baseline_avg < 10:
        return baseline_avg, False
    return baseline_avg, recent_value <= baseline_avg * 0.7


async def _page_comparison(uid: str, cid: str) -> list[dict]:
    inventory = await _site_inventory(uid, cid)
    gsc_recent = await _page_snapshot_map(uid, cid, "gsc", "recent")
    gsc_baseline = await _page_snapshot_map(uid, cid, "gsc", "baseline")
    ga_recent = await _page_snapshot_map(uid, cid, "ga4", "recent")
    ga_baseline = await _page_snapshot_map(uid, cid, "ga4", "baseline")
    internal_recent = await _internal_view_map(uid, cid, 7)
    internal_baseline = await _internal_view_map(uid, cid, 35)
    comparisons = []
    now = datetime.now(timezone.utc)

    for item in inventory:
      path = normalize_page_path(item.get("public_url") or "/")
      gsc_now = gsc_recent.get(path, {})
      gsc_prev = gsc_baseline.get(path, {})
      ga_now = ga_recent.get(path, {})
      ga_prev = ga_baseline.get(path, {})
      current_signal = float(internal_recent.get(path, 0)) + float(gsc_now.get("clicks", 0) or 0) + float(ga_now.get("sessions", 0) or 0)
      baseline_signal_total = max(0.0, float(internal_baseline.get(path, 0)) - float(internal_recent.get(path, 0))) + float(gsc_prev.get("clicks", 0) or 0) + float(ga_prev.get("sessions", 0) or 0)
      baseline_signal, traffic_drop = _recent_vs_baseline(current_signal, baseline_signal_total)
      impressions = float(gsc_now.get("impressions", 0) or 0)
      ctr = float(gsc_now.get("ctr", 0) or 0)
      position = float(gsc_now.get("position", 0) or 0)
      seo_opportunity = impressions >= 40 and ctr < 0.03 and 4 <= position <= 20
      stale = False
      if item.get("updated_at"):
          try:
              stale = datetime.fromisoformat(item["updated_at"]) < now - timedelta(days=35)
          except Exception:
              stale = False
      comparisons.append({
          **item,
          "page_path": path,
          "signals": {
              "internal_views_recent": int(internal_recent.get(path, 0) or 0),
              "internal_views_baseline": int(max(0, internal_baseline.get(path, 0) - internal_recent.get(path, 0))),
              "gsc_clicks_recent": float(gsc_now.get("clicks", 0) or 0),
              "gsc_impressions_recent": impressions,
              "gsc_ctr_recent": round(ctr * 100, 2) if ctr <= 1 else round(ctr, 2),
              "gsc_position_recent": round(position, 2) if position else None,
              "ga_sessions_recent": float(ga_now.get("sessions", 0) or 0),
              "ga_conversions_recent": float(ga_now.get("conversions", 0) or 0),
          },
          "baseline_signal": round(baseline_signal, 2),
          "current_signal": round(current_signal, 2),
          "traffic_drop": traffic_drop,
          "seo_opportunity": seo_opportunity,
          "stale_content": stale,
          "requires_attention": bool(traffic_drop or seo_opportunity or stale),
      })
    comparisons.sort(key=lambda row: (row["requires_attention"], row["current_signal"], row.get("editorial_score") or 0), reverse=True)
    return comparisons


async def _keyword_clusters(uid: str, cid: str, comparisons: list[dict]) -> list[dict]:
    queries = await db.growth_query_snapshots.find({"user_id": uid, "company_id": cid}, {"_id": 0}).sort("impressions", -1).to_list(250)
    clusters = {}
    for row in queries:
        cluster = _keyword_cluster(row.get("query") or "")
        item = clusters.setdefault(cluster, {"cluster": cluster, "queries": [], "impressions": 0.0, "clicks": 0.0, "pages": set(), "coverage": 0})
        item["queries"].append(row.get("query"))
        item["impressions"] += float(row.get("impressions", 0) or 0)
        item["clicks"] += float(row.get("clicks", 0) or 0)
        item["pages"].add(row.get("page_path"))
    for row in comparisons:
        cluster = _keyword_cluster(row.get("seo_keyword") or row.get("title") or "")
        item = clusters.setdefault(cluster, {"cluster": cluster, "queries": [], "impressions": 0.0, "clicks": 0.0, "pages": set(), "coverage": 0})
        item["coverage"] += 1
        item["pages"].add(row.get("page_path"))
    out = []
    for item in clusters.values():
        pages = sorted(p for p in item["pages"] if p)
        out.append({
            "cluster": item["cluster"],
            "queries": list(dict.fromkeys(item["queries"]))[:5],
            "impressions": round(item["impressions"], 2),
            "clicks": round(item["clicks"], 2),
            "pages": pages[:4],
            "coverage": item["coverage"],
            "needs_new_content": item["impressions"] >= 30 and item["coverage"] == 0,
        })
    out.sort(key=lambda row: (row["needs_new_content"], row["impressions"], row["clicks"]), reverse=True)
    return out[:12]


async def _log_growth_action(uid: str, cid: str, *, action_type: str, title: str, page_url: str, detail: str, status: str = "done", requires_approval: bool = False):
    doc = {
        "_id": str(uuid.uuid4()),
        "user_id": uid,
        "company_id": cid,
        "action_type": action_type,
        "title": title,
        "page_url": page_url,
        "detail": detail,
        "status": status,
        "requires_approval": requires_approval,
        "created_at": _now_iso(),
    }
    await db.growth_agent_actions.insert_one(doc)
    out = dict(doc)
    out.pop("_id", None)
    out.pop("user_id", None)
    out.pop("company_id", None)
    return out


async def _apply_related_links(uid: str, cid: str, comparisons: list[dict]) -> int:
    dynamic = [row for row in comparisons if not row.get("is_static") and row.get("entry_id")]
    related_map = {}
    for row in dynamic:
        cluster = _keyword_cluster(row.get("seo_keyword") or row.get("title") or "")
        peers = [peer for peer in dynamic if peer.get("entry_id") != row.get("entry_id") and _keyword_cluster(peer.get("seo_keyword") or peer.get("title") or "") == cluster]
        if not peers:
            continue
        related_map[row["entry_id"]] = [
            {
                "title": peer.get("title"),
                "url": peer.get("public_url"),
                "reason": f"Ligação interna automática dentro do cluster '{cluster}'.",
            }
            for peer in peers[:3]
        ]
    updates = 0
    for entry_id, links in related_map.items():
        await db.site_content_entries.update_one({"id": entry_id, "user_id": uid, "company_id": cid}, {"$set": {"related_links": links, "updated_at": _now_iso()}})
        updates += 1
    return updates


def _fallback_refresh_payload(row: dict) -> dict:
    keyword = row.get("seo_keyword") or row.get("title") or "crescimento orgânico"
    reason = []
    if row.get("traffic_drop"):
        reason.append("queda de tráfego")
    if row.get("seo_opportunity"):
        reason.append("oportunidade de CTR/posição")
    if row.get("stale_content"):
        reason.append("conteúdo desatualizado")
    return {
        "title": row.get("title"),
        "slug": row.get("public_url", "/").split("/")[-1],
        "excerpt": f"Conteúdo atualizado pelo agente de Growth para reforçar {keyword} com foco em SEO e consistência estratégica.",
        "intro": f"Atualização contínua orientada por dados: {', '.join(reason) or 'otimização SEO contínua'}. {GROWTH_HARD_RULE}",
        "seo_title": f"{row.get('title')} | {keyword}",
        "seo_description": f"Atualização SEO focada em {keyword}, melhorando clareza, interligação e consistência de conteúdo sem mexer no design.",
        "strategy_reason": f"Refresh automático por {', '.join(reason) or 'aprendizagem contínua'}.",
    }


async def _refresh_existing_entry(uid: str, cid: str, row: dict, use_ai: bool = False):
    existing = await db.site_content_entries.find_one({"id": row.get("entry_id"), "user_id": uid, "company_id": cid}, {"_id": 0})
    if not existing:
        return None
    payload = _fallback_refresh_payload(row)
    if use_ai:
        try:
            raw = await ai_json(
                "És um agente de Growth/SEO. Respondes só com JSON em português europeu.",
                (
                    f"Página atual: {existing}\n\n"
                    f"Sinais: {row}\n\n"
                    f"Regra inviolável: {GROWTH_HARD_RULE}\n\n"
                    "Devolve APENAS JSON com title, excerpt, intro, seo_title, seo_description e strategy_reason. "
                    "Otimiza só conteúdo/SEO, sem alterar navegação nem design."
                ),
            )
            if isinstance(raw, dict):
                payload.update({k: raw.get(k) or payload[k] for k in payload.keys()})
        except Exception as e:
            logger.error(f"growth ai refresh error: {e}")
    related_links = [SiteRelatedLinkIn(**item) for item in (existing.get("related_links") or [])]
    entry = await upsert_site_content(
        uid,
        cid,
        SiteContentUpsertIn(
            kind=existing.get("kind", "article"),
            title=payload["title"],
            slug=existing.get("slug") or payload["slug"],
            excerpt=payload["excerpt"],
            intro=payload["intro"],
            sections=[SiteSectionBlockIn(**section) for section in (existing.get("sections") or [])],
            cta_label=existing.get("cta_label") or "Saber mais",
            cta_url=existing.get("cta_url") or "/contacto",
            seo_keyword=existing.get("seo_keyword") or row.get("seo_keyword") or payload["title"],
            seo_title=payload["seo_title"],
            seo_description=payload["seo_description"],
            strategy_reason=payload["strategy_reason"],
            objective=existing.get("objective") or "crescimento orgânico",
            campaign_label="Growth Agent",
            related_links=related_links,
            publish_now=True,
            auto_generate_hero_image=False,
        ),
        actor="growth_agent",
    )
    await _log_growth_action(uid, cid, action_type="refresh", title=entry.get("title"), page_url=entry.get("public_url"), detail=payload["strategy_reason"])
    return entry


async def _create_cluster_article(uid: str, cid: str, cluster: dict, use_ai: bool = False):
    title = f"Guia prático: {cluster['cluster']}"
    payload = {
        "title": title,
        "slug": normalize_page_path(f"/insights/{title.lower().replace(' ', '-')}").split("/")[-1],
        "excerpt": f"Novo conteúdo do agente de Growth para capturar procura em torno do cluster '{cluster['cluster']}'.",
        "intro": f"Conteúdo criado autonomamente a partir de oportunidades de SEO detetadas. {GROWTH_HARD_RULE}",
        "sections": [
            {"heading": "Oportunidade detetada", "paragraphs": [f"Este cluster apresenta procura relevante: {', '.join(cluster.get('queries') or [cluster['cluster']])}."], "bullets": []},
            {"heading": "Resposta recomendada", "paragraphs": ["Criar um conteúdo evergreen e interligado com as páginas já existentes para capturar melhor a procura qualificada."], "bullets": ["SEO on-page", "links internos", "claridade comercial"]},
            {"heading": "Próximo passo", "paragraphs": ["Acompanhar impressões, cliques, views internas e sinais de conversão para decidir o reforço seguinte."], "bullets": []},
        ],
    }
    if use_ai:
        try:
            raw = await ai_json(
                "És um agente de Growth/SEO. Respondes só com JSON em português europeu.",
                (
                    f"Cluster: {cluster}\n\nRegra inviolável: {GROWTH_HARD_RULE}\n\n"
                    "Devolve APENAS JSON com title, excerpt, intro, sections, seo_title, seo_description. "
                    "Cria conteúdo novo orientado a SEO sem alterar design nem estrutura."
                ),
            )
            if isinstance(raw, dict) and raw.get("title"):
                payload.update({
                    "title": raw.get("title") or payload["title"],
                    "excerpt": raw.get("excerpt") or payload["excerpt"],
                    "intro": raw.get("intro") or payload["intro"],
                    "sections": raw.get("sections") or payload["sections"],
                    "seo_title": raw.get("seo_title") or raw.get("title") or payload["title"],
                    "seo_description": raw.get("seo_description") or payload["excerpt"],
                })
        except Exception as e:
            logger.error(f"growth ai create error: {e}")
    entry = await upsert_site_content(
        uid,
        cid,
        SiteContentUpsertIn(
            kind="article",
            title=payload["title"],
            slug=payload["slug"],
            excerpt=payload["excerpt"],
            intro=payload["intro"],
            sections=[SiteSectionBlockIn(**section) for section in payload["sections"]],
            cta_label="Ver mais insights",
            cta_url="/insights",
            seo_keyword=cluster["cluster"],
            seo_title=payload.get("seo_title") or payload["title"],
            seo_description=payload.get("seo_description") or payload["excerpt"],
            strategy_reason=f"Novo conteúdo criado para cobrir o cluster '{cluster['cluster']}'.",
            objective="crescimento orgânico",
            campaign_label="Growth Agent",
            publish_now=True,
            auto_generate_hero_image=True,
        ),
        actor="growth_agent",
    )
    await _log_growth_action(uid, cid, action_type="create", title=entry.get("title"), page_url=entry.get("public_url"), detail=f"Novo artigo criado para o cluster '{cluster['cluster']}'.")
    return entry


async def _generate_growth_report(uid: str, cid: str, period: str, reference_key: str, comparison: list[dict], clusters: list[dict], sync_run: dict):
    existing = await db.growth_agent_reports.find_one({"user_id": uid, "company_id": cid, "period": period, "reference_key": reference_key}, {"_id": 0})
    if existing:
        return existing
    actions = await db.growth_agent_actions.find({"user_id": uid, "company_id": cid}, {"_id": 0}).sort("created_at", -1).to_list(12)
    top_alerts = [row for row in comparison if row.get("requires_attention")][:4]
    report = {
        "_id": str(uuid.uuid4()),
        "user_id": uid,
        "company_id": cid,
        "period": period,
        "reference_key": reference_key,
        "headline": f"Relatório executivo {period} de Growth",
        "summary": f"O agente monitorizou {len(comparison)} páginas públicas, geriu SEO e manteve a regra explícita de nunca alterar design ou estrutura.",
        "actions_taken": [f"{item.get('action_type')}: {item.get('title')}" for item in actions[:5]] or ["Sem ações executadas ainda."],
        "impact": [
            f"Páginas com atenção: {len(top_alerts)}",
            f"Clusters monitorizados: {len(clusters)}",
            f"GSC ativo: {'sim' if sync_run.get('source_status', {}).get('gsc', {}).get('ok') else 'não'}",
            f"GA4 ativo: {'sim' if sync_run.get('source_status', {}).get('ga4', {}).get('ok') else 'não'}",
        ],
        "learnings": [
            f"{row.get('title')}: queda de tráfego detetada" for row in top_alerts if row.get('traffic_drop')
        ][:3] or ["Ainda a consolidar baseline e sinais por URL/landing page."],
        "next_steps": [
            f"Reforçar o cluster '{clusters[0]['cluster']}'" if clusters else "Continuar monitorização e criação de conteúdo",
            "Atualizar conteúdos desatualizados e melhorar interligações internas.",
        ],
        "policy": GROWTH_HARD_RULE,
        "source_status": sync_run.get("source_status") or {},
        "created_at": _now_iso(),
    }
    await db.growth_agent_reports.insert_one(report)
    out = dict(report)
    out.pop("_id", None)
    out.pop("user_id", None)
    out.pop("company_id", None)
    return out


async def _ensure_growth_reports(uid: str, cid: str, comparison: list[dict], clusters: list[dict], sync_run: dict):
    now = datetime.now(timezone.utc)
    refs = {
        "daily": now.date().isoformat(),
        "weekly": f"{now.isocalendar().year}-W{now.isocalendar().week:02d}",
        "monthly": now.strftime("%Y-%m"),
    }
    for period, ref in refs.items():
        await _generate_growth_report(uid, cid, period, ref, comparison, clusters, sync_run)


async def get_growth_status(uid: str, cid: str) -> dict:
    comparison = await _page_comparison(uid, cid)
    clusters = await _keyword_clusters(uid, cid, comparison)
    sync_run = await db.growth_sync_runs.find_one({"user_id": uid, "company_id": cid}, {"_id": 0}, sort=[("started_at", -1)]) or {"source_status": {}}
    action_rows = await db.growth_agent_actions.find({"user_id": uid, "company_id": cid}, {"_id": 0}).sort("created_at", -1).to_list(12)
    report_rows = await db.growth_agent_reports.find({"user_id": uid, "company_id": cid}, {"_id": 0}).sort("created_at", -1).to_list(12)
    site_settings = await _site_settings(uid, cid)
    blockers = []
    if sync_run.get("source_status", {}).get("gsc", {}).get("error"):
        blockers.append(f"Search Console: {sync_run['source_status']['gsc']['error']}")
    if sync_run.get("source_status", {}).get("ga4", {}).get("error"):
        blockers.append(f"GA4: {sync_run['source_status']['ga4']['error']}")
    if not google_growth_status().get("ga4_measurement_installed"):
        blockers.append("O código/tag de recolha do GA4 ainda não está instalado; até lá, o agente usa Search Console + tracking interno do próprio site.")
    if not site_settings.get("authorized"):
        blockers.append("O gateway do site ainda não está autorizado para criação/atualização autónoma de conteúdo público.")
    return {
        "policy": {"hard_rule": GROWTH_HARD_RULE},
        "google": google_growth_status(),
        "sync_run": sync_run,
        "summary": {
            "pages_monitored": len(comparison),
            "drop_alerts": len([row for row in comparison if row.get("traffic_drop")]),
            "seo_opportunities": len([row for row in comparison if row.get("seo_opportunity")]),
            "stale_pages": len([row for row in comparison if row.get("stale_content")]),
            "actions_logged": len(action_rows),
        },
        "landing_pages": comparison[:12],
        "keyword_clusters": clusters,
        "actions": action_rows,
        "reports": {
            "daily": [row for row in report_rows if row.get("period") == "daily"][:3],
            "weekly": [row for row in report_rows if row.get("period") == "weekly"][:3],
            "monthly": [row for row in report_rows if row.get("period") == "monthly"][:3],
        },
        "blockers": blockers,
    }


async def run_growth_agent_cycle(uid: str, cid: str, force: bool = False, use_ai: bool = False):
    organic = await db.marketing_organic_agents.find_one({"user_id": uid, "company_id": cid, "strategy_approved": True, "status": {"$ne": "draft"}}, {"_id": 0})
    if not organic:
        return None
    sync_run = await sync_growth_sources(uid, cid)
    comparisons = await _page_comparison(uid, cid)
    clusters = await _keyword_clusters(uid, cid, comparisons)
    site_settings = await _site_settings(uid, cid)

    await _log_growth_action(
        uid,
        cid,
        action_type="monitor",
        title="Ciclo automático de monitorização",
        page_url="/insights",
        detail=f"Monitorização executada sobre {len(comparisons)} páginas públicas. Regra ativa: {GROWTH_HARD_RULE}",
    )

    related_updates = await _apply_related_links(uid, cid, comparisons)
    if related_updates:
        await _log_growth_action(uid, cid, action_type="interlink", title="Interligações internas", page_url="/insights", detail=f"{related_updates} conteúdos receberam related links automáticos.")

    if site_settings.get("authorized"):
        target = next((row for row in comparisons if row.get("requires_attention") and not row.get("is_static") and row.get("kind") in {"article", "page"}), None)
        if target:
            await _refresh_existing_entry(uid, cid, target, use_ai=use_ai)
        cluster_gap = next((row for row in clusters if row.get("needs_new_content")), None)
        if cluster_gap:
            await _create_cluster_article(uid, cid, cluster_gap, use_ai=use_ai)
        static_attention = next((row for row in comparisons if row.get("requires_attention") and row.get("is_static")), None)
        if static_attention:
            await _log_growth_action(uid, cid, action_type="approval-needed", title=static_attention.get("title"), page_url=static_attention.get("public_url"), detail="A página principal/static apresentou sinais relevantes. Mudanças aqui podem ser estratégicas; por isso o agente sinalizou para revisão antes de mexer em copy estrutural.", status="waiting", requires_approval=True)

    await _ensure_growth_reports(uid, cid, comparisons, clusters, sync_run)
    status = await get_growth_status(uid, cid)
    await db.marketing_organic_agents.update_one(
        {"user_id": uid, "company_id": cid},
        {"$set": {"growth_monitoring": {"summary": status["summary"], "blockers": status["blockers"], "updated_at": _now_iso(), "policy": GROWTH_HARD_RULE}}},
    )
    return status


async def run_all_growth_agent_cycles():
    rows = await db.marketing_organic_agents.find({"status": "running", "strategy_approved": True}, {"_id": 0, "user_id": 1, "company_id": 1}).to_list(50)
    for row in rows:
        try:
            await run_growth_agent_cycle(row["user_id"], row["company_id"], force=False, use_ai=False)
        except Exception as e:
            logger.error(f"run_all_growth_agent_cycles error {row}: {e}")


@router.get("/marketing/growth-agent/status")
async def growth_agent_status(user: dict = Depends(premium_user)):
    uid = user["id"]
    cid = await active_company_id(uid)
    return await get_growth_status(uid, cid)


@router.post("/marketing/growth-agent/sync")
async def growth_agent_sync(user: dict = Depends(premium_user)):
    uid = user["id"]
    cid = await active_company_id(uid)
    run = await sync_growth_sources(uid, cid)
    return {"sync_run": run, "status": await get_growth_status(uid, cid)}


@router.post("/marketing/growth-agent/run")
async def growth_agent_run(inp: GrowthRunIn, user: dict = Depends(premium_user)):
    uid = user["id"]
    cid = await active_company_id(uid)
    status = await run_growth_agent_cycle(uid, cid, force=inp.force, use_ai=inp.use_ai)
    if status is None:
        raise HTTPException(400, "A estratégia inicial do Crescimento Orgânico ainda não está em modo autónomo.")
    return status


@router.get("/public/sitemap.xml")
async def public_sitemap_xml():
    owner_cid = await _live_owner_company_id()
    owner = await _live_owner_identity()
    if not owner or not owner_cid:
        return Response("<?xml version='1.0' encoding='UTF-8'?><urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'></urlset>", media_type="application/xml")
    inventory = await _site_inventory(owner["user_id"], owner_cid)
    base = _public_base_url()
    urls = []
    for item in inventory:
        loc = item.get("canonical_url") or (f"{base}{item.get('public_url')}" if base else item.get("public_url"))
        urls.append(f"<url><loc>{loc}</loc></url>")
    body = "<?xml version='1.0' encoding='UTF-8'?>" + "<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>" + "".join(urls) + "</urlset>"
    return Response(body, media_type="application/xml")


@router.post("/public/site/track-static")
async def public_track_static(inp: PublicTrackIn):
    owner = await _live_owner_identity()
    if not owner:
        return {"ok": False}
    await _record_internal_view(owner["user_id"], owner["company_id"], inp.page_key, inp.path, inp.title, "static")
    return {"ok": True}