"""Gateway interno de publicação do site público, sem CMS externo."""
import re
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core import (
    active_company_id,
    ai_json,
    db,
    generate_marketing_image,
    logger,
    premium_user,
    resolve_company,
    store_public_media,
)
from routers.marketing import _ctx, _prompt_context, _short, _str_list

router = APIRouter()

SAFE_SECTION_SLOTS = {
    "login.hero_headline": {"route": "/login", "label": "Headline da página de login"},
    "login.hero_subtitle": {"route": "/login", "label": "Subheadline da página de login"},
    "pricing.hero_headline": {"route": "/planos", "label": "Headline da página de planos"},
    "pricing.hero_subtitle": {"route": "/planos", "label": "Subheadline da página de planos"},
    "contact.hero_intro": {"route": "/contacto", "label": "Introdução da página de contacto"},
}
MANAGED_ROUTE_PREFIXES = ["/insights", "/site", "/login", "/planos", "/contacto"]


class SiteSectionBlockIn(BaseModel):
    heading: str = ""
    paragraphs: list[str] = Field(default_factory=list)
    bullets: list[str] = Field(default_factory=list)


class SiteContentUpsertIn(BaseModel):
    kind: str = "article"
    title: str = ""
    slug: str = ""
    excerpt: str = ""
    intro: str = ""
    sections: list[SiteSectionBlockIn] = Field(default_factory=list)
    cta_label: str = ""
    cta_url: str = ""
    seo_keyword: str = ""
    seo_title: str = ""
    seo_description: str = ""
    strategy_reason: str = ""
    objective: str = ""
    campaign_label: str = "Organic Growth"
    slot_key: str = ""
    slot_value: str = ""
    publish_now: bool = True
    auto_generate_hero_image: bool = True


class SiteAuthorizeIn(BaseModel):
    auto_publish_after_strategy_approval: bool = True
    auto_generate_hero_images: bool = True
    allow_section_overrides: bool = True
    allow_delete: bool = True


class SiteRollbackIn(BaseModel):
    version_id: Optional[str] = None


class SiteAgentRunIn(BaseModel):
    force: bool = True
    use_ai: bool = False


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slugify(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9\s\-À-ÿ]", " ", (value or "").strip().lower())
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:96] or f"conteudo-{uuid.uuid4().hex[:8]}"


def _serialize_entry(doc: Optional[dict]) -> Optional[dict]:
    if not doc:
        return None
    out = dict(doc)
    out.pop("_id", None)
    out.pop("user_id", None)
    out.pop("company_id", None)
    return out


def _site_url_for(kind: str, slug: str = "", slot_key: str = "") -> str:
    if kind == "article":
        return f"/insights/{slug}"
    if kind == "page":
        return f"/site/{slug}"
    if kind == "section_override":
        return SAFE_SECTION_SLOTS.get(slot_key, {}).get("route", "/login")
    return "/login"


def _safe_slot(slot_key: str):
    if slot_key not in SAFE_SECTION_SLOTS:
        raise HTTPException(400, "O slot pedido não faz parte da zona pública segura do gateway.")
    return SAFE_SECTION_SLOTS[slot_key]


def _clean_section(section: dict) -> dict:
    section = section if isinstance(section, dict) else {}
    return {
        "heading": _short(section.get("heading"), "Secção"),
        "paragraphs": _str_list(section.get("paragraphs"), 5),
        "bullets": _str_list(section.get("bullets"), 6),
    }


def _snapshot(doc: dict) -> dict:
    base = _serialize_entry(doc) or {}
    base.pop("metrics", None)
    return base


def _compute_editorial_score(doc: dict) -> int:
    metrics = doc.get("metrics") or {}
    score = 20
    if doc.get("seo_keyword"):
        score += 10
    if doc.get("seo_title"):
        score += 10
    if doc.get("seo_description"):
        score += 10
    if doc.get("hero_image_url"):
        score += 10
    if len(doc.get("excerpt") or "") >= 70:
        score += 10
    if len(doc.get("sections") or []) >= 3:
        score += 15
    elif len(doc.get("sections") or []) >= 1:
        score += 8
    views = int(metrics.get("views", 0) or 0)
    if views >= 100:
        score += 10
    elif views >= 10:
        score += 5
    if doc.get("status") == "published":
        score += 10
    return min(100, score)


def _architecture_summary() -> dict:
    return {
        "frontend": {
            "stack": "React SPA (Create React App)",
            "public_routes": ["/login", "/planos", "/contacto", "/termos", "/privacidade"],
            "public_content_storage_today": "Copys e layouts públicos hardcoded em ficheiros JSX do frontend.",
        },
        "backend": {
            "stack": "FastAPI + APScheduler + MongoDB (Motor)",
            "api_prefix": "/api",
            "content_collections": [
                "marketing_content",
                "marketing_campaigns",
                "marketing_organic_agents",
                "marketing_organic_actions",
                "marketing_organic_reports",
            ],
        },
        "cms": {
            "exists": False,
            "details": "Não existe CMS externo nem headless CMS dedicado para o site público atual.",
        },
        "publishing_today": {
            "mode": "Mesmo projeto/infrastrutura: frontend React + backend FastAPI publicados juntos na Emergent.",
            "site_change_method_before_gateway": "Para páginas públicas hardcoded, alterar código e voltar a publicar/deployar.",
        },
        "chosen_mechanism": {
            "name": "Content Publishing Gateway interno",
            "reason": "É a forma mais simples e segura de permitir escrita autónoma sem criar CMS externo nem novo projeto.",
            "managed_paths": MANAGED_ROUTE_PREFIXES,
            "safe_write_scope": [
                "Novos artigos públicos em /insights/:slug",
                "Novas páginas públicas em /site/:slug",
                "Overrides seguros para secções públicas pré-definidas (login, planos, contacto)",
            ],
        },
    }


async def _get_settings(uid: str, cid: str) -> dict:
    company = await resolve_company(uid, cid) or {}
    existing = await db.site_publication_settings.find_one({"user_id": uid, "company_id": cid}, {"_id": 0})
    if existing:
        return existing
    return {
        "user_id": uid,
        "company_id": cid,
        "company_name": company.get("name") or "Empresa",
        "authorized": False,
        "auto_publish_after_strategy_approval": True,
        "auto_generate_hero_images": True,
        "allow_section_overrides": True,
        "allow_delete": True,
        "site_live_owner": False,
        "managed_route_prefixes": MANAGED_ROUTE_PREFIXES,
        "allowed_slot_keys": list(SAFE_SECTION_SLOTS.keys()),
        "authorization_note": "Ainda não autorizado para escrita autónoma no site público.",
        "updated_at": _now_iso(),
    }


async def _live_owner_company_id() -> Optional[str]:
    row = await db.site_publication_settings.find_one(
        {"site_live_owner": True, "authorized": True},
        {"_id": 0, "company_id": 1},
        sort=[("authorized_at", -1)],
    )
    return row.get("company_id") if row else None


async def _log_event(uid: str, cid: str, *, action: str, status: str, entry: Optional[dict] = None,
                     previous_snapshot: Optional[dict] = None, new_snapshot: Optional[dict] = None,
                     strategy_reason: str = "", seo_keyword: str = "", objective: str = "",
                     error: str = "", actor: str = "gateway") -> dict:
    log = {
        "_id": str(uuid.uuid4()),
        "user_id": uid,
        "company_id": cid,
        "entry_id": entry.get("id") if entry else None,
        "entry_title": entry.get("title") if entry else None,
        "kind": entry.get("kind") if entry else None,
        "action": action,
        "status": status,
        "url": entry.get("public_url") if entry else None,
        "previous_content": previous_snapshot,
        "new_content": new_snapshot,
        "strategy_reason": strategy_reason,
        "seo_keyword": seo_keyword,
        "objective": objective,
        "metrics_after": (entry or {}).get("metrics") or {},
        "rollback_available": bool(entry),
        "actor": actor,
        "error": error[:600] if error else "",
        "created_at": _now_iso(),
    }
    await db.site_publication_logs.insert_one(log)
    return _serialize_entry(log)


async def _create_version(uid: str, cid: str, entry_id: str, version_number: int, snapshot: dict, reason: str, actor: str):
    version = {
        "_id": str(uuid.uuid4()),
        "user_id": uid,
        "company_id": cid,
        "entry_id": entry_id,
        "version_number": version_number,
        "snapshot": snapshot,
        "reason": reason,
        "actor": actor,
        "created_at": _now_iso(),
    }
    await db.site_content_versions.insert_one(version)
    return version


async def _ensure_unique_slug(uid: str, cid: str, kind: str, slug: str, current_id: Optional[str] = None) -> str:
    base = _slugify(slug)
    candidate = base
    counter = 2
    while True:
        existing = await db.site_content_entries.find_one({
            "user_id": uid,
            "company_id": cid,
            "kind": kind,
            "slug": candidate,
            "status": {"$ne": "deleted"},
        }, {"_id": 0, "id": 1})
        if not existing or existing.get("id") == current_id:
            return candidate
        candidate = f"{base}-{counter}"
        counter += 1


async def upsert_site_content(uid: str, cid: str, inp: SiteContentUpsertIn, actor: str = "manual") -> dict:
    settings = await _get_settings(uid, cid)
    if not settings.get("authorized"):
        raise HTTPException(400, "Autorize primeiro o gateway de publicação do site.")
    kind = (inp.kind or "article").strip().lower()
    if kind not in {"article", "page", "section_override"}:
        raise HTTPException(400, "Tipo inválido. Use article, page ou section_override.")
    if kind == "section_override" and not settings.get("allow_section_overrides"):
        raise HTTPException(400, "Os overrides das páginas públicas não estão autorizados nesta empresa.")

    existing = None
    slug = ""
    slot_value = _short(inp.slot_value, "") if kind == "section_override" else ""
    if kind == "section_override":
        slot_meta = _safe_slot(inp.slot_key)
        existing = await db.site_content_entries.find_one({"user_id": uid, "company_id": cid, "kind": kind, "slot_key": inp.slot_key})
        slug = inp.slot_key.replace(".", "-")
        title = slot_meta["label"]
        excerpt = f"Override seguro do slot {inp.slot_key}."
        intro = slot_value
        sections = []
    else:
        title = _short(inp.title, "Novo conteúdo público")
        base_slug = inp.slug or title
        existing = await db.site_content_entries.find_one({"user_id": uid, "company_id": cid, "kind": kind, "slug": _slugify(base_slug)})
        slug = await _ensure_unique_slug(uid, cid, kind, base_slug, existing.get("id") if existing else None)
        excerpt = _short(inp.excerpt, inp.intro or f"{title} — conteúdo público publicado pelo gateway interno.")
        intro = _short(inp.intro, excerpt)
        sections = [_clean_section(section.model_dump()) for section in (inp.sections or [])]

    hero_image_url = (existing or {}).get("hero_image_url")
    if kind in {"article", "page"} and inp.auto_generate_hero_image and settings.get("auto_generate_hero_images") and not hero_image_url:
        try:
            image_prompt = f"Imagem editorial profissional para '{title}', relacionada com {inp.seo_keyword or title}, sem texto na imagem."
            hero_image_url = await store_public_media(uid, await generate_marketing_image(image_prompt))
        except Exception as e:
            logger.error(f"site gateway hero image error: {e}")

    now_iso = _now_iso()
    previous_snapshot = _snapshot(existing) if existing else None
    version_number = int((existing or {}).get("current_version", 0) or 0) + 1
    doc = {
        "id": (existing or {}).get("id") or str(uuid.uuid4()),
        "user_id": uid,
        "company_id": cid,
        "kind": kind,
        "title": title,
        "slug": slug,
        "public_url": _site_url_for(kind, slug, inp.slot_key),
        "status": "published" if inp.publish_now else "draft",
        "excerpt": excerpt,
        "intro": intro,
        "sections": sections,
        "cta_label": _short(inp.cta_label, "Saber mais") if kind != "section_override" else "",
        "cta_url": _short(inp.cta_url, "/contacto") if kind != "section_override" else "",
        "seo_keyword": _short(inp.seo_keyword, inp.objective or title),
        "seo_title": _short(inp.seo_title, title),
        "seo_description": _short(inp.seo_description, excerpt),
        "strategy_reason": _short(inp.strategy_reason, "Atualização autónoma alinhada com a estratégia aprovada."),
        "objective": _short(inp.objective, "crescimento orgânico"),
        "campaign_label": _short(inp.campaign_label, "Organic Growth"),
        "slot_key": inp.slot_key if kind == "section_override" else "",
        "slot_value": slot_value,
        "hero_image_url": hero_image_url,
        "managed_by": actor,
        "is_autonomous": actor != "manual",
        "current_version": version_number,
        "metrics": (existing or {}).get("metrics") or {"views": 0, "rollback_count": 0, "last_view_at": None},
        "published_at": now_iso if inp.publish_now else (existing or {}).get("published_at"),
        "created_at": (existing or {}).get("created_at") or now_iso,
        "updated_at": now_iso,
        "deleted_at": None,
    }
    doc["editorial_score"] = _compute_editorial_score(doc)
    await db.site_content_entries.update_one({"id": doc["id"], "user_id": uid, "company_id": cid}, {"$set": doc}, upsert=True)
    await _create_version(uid, cid, doc["id"], version_number, _snapshot(doc), doc["strategy_reason"], actor)
    entry = _serialize_entry(doc)
    await _log_event(
        uid,
        cid,
        action="update" if existing else "create",
        status="ok",
        entry=entry,
        previous_snapshot=previous_snapshot,
        new_snapshot=_snapshot(doc),
        strategy_reason=doc["strategy_reason"],
        seo_keyword=doc["seo_keyword"],
        objective=doc["objective"],
        actor=actor,
    )
    return entry


async def remove_site_content(uid: str, cid: str, entry_id: str, actor: str = "manual") -> dict:
    settings = await _get_settings(uid, cid)
    if not settings.get("allow_delete"):
        raise HTTPException(400, "A remoção automática não está permitida nesta empresa.")
    existing = await db.site_content_entries.find_one({"id": entry_id, "user_id": uid, "company_id": cid})
    if not existing:
        raise HTTPException(404, "Conteúdo não encontrado.")
    previous_snapshot = _snapshot(existing)
    metrics = existing.get("metrics") or {}
    doc = {**existing, "status": "deleted", "deleted_at": _now_iso(), "updated_at": _now_iso(), "metrics": metrics}
    await db.site_content_entries.update_one({"id": entry_id, "user_id": uid, "company_id": cid}, {"$set": {"status": "deleted", "deleted_at": doc["deleted_at"], "updated_at": doc["updated_at"]}})
    entry = _serialize_entry(doc)
    await _create_version(uid, cid, entry_id, int(existing.get("current_version", 1) or 1) + 1, _snapshot(doc), "Remoção/arquivamento", actor)
    await _log_event(uid, cid, action="delete", status="ok", entry=entry, previous_snapshot=previous_snapshot,
                     new_snapshot=_snapshot(doc), strategy_reason="Conteúdo removido/arquivado pelo gateway.",
                     seo_keyword=existing.get("seo_keyword") or "", objective=existing.get("objective") or "", actor=actor)
    return entry


async def rollback_site_content(uid: str, cid: str, entry_id: str, version_id: Optional[str], actor: str = "manual") -> dict:
    existing = await db.site_content_entries.find_one({"id": entry_id, "user_id": uid, "company_id": cid})
    if not existing:
        raise HTTPException(404, "Conteúdo não encontrado para rollback.")
    q = {"entry_id": entry_id, "user_id": uid, "company_id": cid}
    if version_id:
        q["_id"] = version_id
        version = await db.site_content_versions.find_one(q)
    else:
        version = await db.site_content_versions.find_one(
            {**q, "version_number": {"$lt": int(existing.get("current_version", 1) or 1)}},
            sort=[("version_number", -1)],
        )
    if not version or not isinstance(version.get("snapshot"), dict):
        raise HTTPException(404, "Versão anterior não encontrada.")
    previous_snapshot = _snapshot(existing)
    restored = {**version["snapshot"], "updated_at": _now_iso(), "current_version": int(existing.get("current_version", 1) or 1) + 1}
    restored["metrics"] = existing.get("metrics") or {"views": 0, "rollback_count": 0, "last_view_at": None}
    restored["metrics"]["rollback_count"] = int(restored["metrics"].get("rollback_count", 0) or 0) + 1
    restored["editorial_score"] = _compute_editorial_score(restored)
    await db.site_content_entries.update_one({"id": entry_id, "user_id": uid, "company_id": cid}, {"$set": restored})
    await _create_version(uid, cid, entry_id, restored["current_version"], _snapshot(restored), "Rollback", actor)
    entry = _serialize_entry(restored)
    await _log_event(uid, cid, action="rollback", status="ok", entry=entry, previous_snapshot=previous_snapshot,
                     new_snapshot=_snapshot(restored), strategy_reason=restored.get("strategy_reason") or "Rollback manual.",
                     seo_keyword=restored.get("seo_keyword") or "", objective=restored.get("objective") or "", actor=actor)
    return entry


async def get_site_publishing_status(uid: str, cid: str) -> dict:
    settings = await _get_settings(uid, cid)
    entries = await db.site_content_entries.find({"user_id": uid, "company_id": cid}).sort("updated_at", -1).to_list(50)
    logs = await db.site_publication_logs.find({"user_id": uid, "company_id": cid}).sort("created_at", -1).to_list(30)
    published = [row for row in entries if row.get("status") == "published"]
    campaign_map = {}
    keywords = []
    for row in published:
        metrics = row.get("metrics") or {}
        label = row.get("campaign_label") or "Organic Growth"
        bucket = campaign_map.setdefault(label, {"campaign_label": label, "published_count": 0, "total_views": 0, "avg_editorial_score": 0, "last_published_at": None})
        bucket["published_count"] += 1
        bucket["total_views"] += int(metrics.get("views", 0) or 0)
        bucket["avg_editorial_score"] += int(row.get("editorial_score", 0) or 0)
        bucket["last_published_at"] = max(bucket.get("last_published_at") or "", row.get("published_at") or "")
        if row.get("seo_keyword"):
            keywords.append(row.get("seo_keyword"))
    campaign_comparison = []
    for item in campaign_map.values():
        item["avg_editorial_score"] = round(item["avg_editorial_score"] / max(item["published_count"], 1), 1)
        campaign_comparison.append(item)
    campaign_comparison.sort(key=lambda item: (item["total_views"], item["avg_editorial_score"]), reverse=True)
    failures = [row for row in logs if row.get("status") == "failed"]
    return {
        "architecture": _architecture_summary(),
        "settings": settings,
        "summary": {
            "authorized": bool(settings.get("authorized")),
            "site_live_owner": bool(settings.get("site_live_owner")),
            "published_entries": len(published),
            "draft_entries": len([row for row in entries if row.get("status") == "draft"]),
            "section_overrides": len([row for row in entries if row.get("kind") == "section_override" and row.get("status") != "deleted"]),
            "failures": len(failures),
            "rollbacks": len([row for row in logs if row.get("action") == "rollback" and row.get("status") == "ok"]),
        },
        "entries": [_serialize_entry(row) for row in entries],
        "logs": [_serialize_entry(row) for row in logs],
        "analytics": {
            "campaign_comparison": campaign_comparison,
            "editorial_scores": [
                {
                    "id": row.get("id"),
                    "title": row.get("title"),
                    "kind": row.get("kind"),
                    "score": row.get("editorial_score", 0),
                    "views": (row.get("metrics") or {}).get("views", 0),
                    "url": row.get("public_url"),
                }
                for row in published[:8]
            ],
            "top_keywords": keywords[:8],
        },
    }


def _fallback_autonomous_payload(agent: dict) -> dict:
    site = agent.get("site_analysis") or {}
    keyword = (site.get("keywords") or ["crescimento orgânico"])[0]
    service = (site.get("primary_services") or ["serviço principal"])[0]
    opportunity = ((site.get("opportunities") or [{}])[0]).get("title") or "clarificar a proposta de valor"
    title = f"{service}: guia prático para melhorar resultados com {keyword}"
    return {
        "kind": "article",
        "title": title,
        "slug": _slugify(title),
        "excerpt": f"Guia objetivo para transformar {keyword} em tração qualificada e conversão para {service}.",
        "intro": f"Este conteúdo nasce da estratégia aprovada de Crescimento Orgânico e responde à oportunidade '{opportunity}'.",
        "sections": [
            {"heading": "O problema que estamos a resolver", "paragraphs": [f"Muitas empresas em {service.lower()} atraem atenção, mas não conseguem converter essa atenção em procura qualificada.", f"O foco aqui é usar {keyword} com intenção comercial, prova e clareza de oferta."], "bullets": []},
            {"heading": "O que fazer agora", "paragraphs": ["Comece por clarificar a proposta de valor, alinhar CTA e remover fricção de contacto.", "Depois, publique conteúdo útil que responda às dúvidas reais do cliente ideal."], "bullets": ["Posicionamento claro", "Prova social visível", "CTA dominante", "Conteúdo orientado a intenção"]},
            {"heading": "Como medir a evolução", "paragraphs": ["Acompanhe URLs, visitas, interações e sinais de procura comercial para aprender rapidamente com o que foi publicado."], "bullets": ["Visitas à página", "Leads gerados", "Qualidade do tráfego", "Temas com maior procura"]},
        ],
        "cta_label": "Falar com a equipa",
        "cta_url": "/contacto",
        "seo_keyword": keyword,
        "seo_title": title,
        "seo_description": f"{service} · conteúdo criado autonomamente pelo agente para reforçar {keyword} com foco em conversão.",
        "strategy_reason": f"Conteúdo publicado para atacar a oportunidade estratégica '{opportunity}'.",
        "objective": agent.get("objective") or "crescimento orgânico",
        "campaign_label": "Organic Growth",
    }


async def maybe_publish_autonomous_site_content(uid: str, cid: str, agent: dict, use_ai: bool = False) -> Optional[dict]:
    settings = await _get_settings(uid, cid)
    if not settings.get("authorized") or not settings.get("auto_publish_after_strategy_approval"):
        return None
    recent = await db.site_content_entries.count_documents({
        "user_id": uid,
        "company_id": cid,
        "managed_by": "organic_agent",
        "status": "published",
    })
    if recent >= 6:
        return None

    fallback = _fallback_autonomous_payload(agent)
    payload = fallback
    if use_ai:
        try:
            ctx = await _ctx(uid, cid)
            raw = await ai_json(
                "És o agente autónomo de publicação do site público. Respondes só com JSON em português europeu.",
                (
                    f"Contexto da empresa:\n{_prompt_context(ctx)}\n\n"
                    f"Agente de Crescimento Orgânico: {agent}\n\n"
                    "Devolve APENAS JSON válido com a estrutura "
                    '{"kind":"article","title":str,"slug":str,"excerpt":str,"intro":str,'
                    '"sections":[{"heading":str,"paragraphs":[str],"bullets":[str]}],'
                    '"cta_label":str,"cta_url":str,"seo_keyword":str,"seo_title":str,"seo_description":str,'
                    '"strategy_reason":str,"objective":str,"campaign_label":str}. '
                    "Quero um conteúdo público seguro, útil, orientado a SEO e alinhado com a estratégia já aprovada."
                ),
            )
            if isinstance(raw, dict) and raw.get("title"):
                payload = {
                    **fallback,
                    **raw,
                    "sections": [_clean_section(item) for item in (raw.get("sections") or [])][:5] or fallback["sections"],
                }
        except Exception as e:
            logger.error(f"autonomous site content ai error: {e}")

    try:
        return await upsert_site_content(
            uid,
            cid,
            SiteContentUpsertIn(
                kind=payload.get("kind", "article"),
                title=payload.get("title") or fallback["title"],
                slug=payload.get("slug") or fallback["slug"],
                excerpt=payload.get("excerpt") or fallback["excerpt"],
                intro=payload.get("intro") or fallback["intro"],
                sections=[SiteSectionBlockIn(**section) for section in (payload.get("sections") or fallback["sections"])],
                cta_label=payload.get("cta_label") or fallback["cta_label"],
                cta_url=payload.get("cta_url") or fallback["cta_url"],
                seo_keyword=payload.get("seo_keyword") or fallback["seo_keyword"],
                seo_title=payload.get("seo_title") or fallback["seo_title"],
                seo_description=payload.get("seo_description") or fallback["seo_description"],
                strategy_reason=payload.get("strategy_reason") or fallback["strategy_reason"],
                objective=payload.get("objective") or fallback["objective"],
                campaign_label=payload.get("campaign_label") or fallback["campaign_label"],
                publish_now=True,
                auto_generate_hero_image=settings.get("auto_generate_hero_images", True),
            ),
            actor="organic_agent",
        )
    except Exception as e:
        await _log_event(uid, cid, action="publish", status="failed", entry=None, previous_snapshot=None, new_snapshot=None,
                         strategy_reason=fallback["strategy_reason"], seo_keyword=fallback["seo_keyword"],
                         objective=fallback["objective"], error=str(e), actor="organic_agent")
        raise


@router.get("/marketing/site-publishing/architecture")
async def get_site_architecture(user: dict = Depends(premium_user)):
    uid = user["id"]
    cid = await active_company_id(uid)
    return {
        "architecture": _architecture_summary(),
        "settings": await _get_settings(uid, cid),
    }


@router.get("/marketing/site-publishing/status")
async def site_publishing_status(user: dict = Depends(premium_user)):
    uid = user["id"]
    cid = await active_company_id(uid)
    return await get_site_publishing_status(uid, cid)


@router.post("/marketing/site-publishing/authorize")
async def authorize_site_publishing(inp: SiteAuthorizeIn, user: dict = Depends(premium_user)):
    uid = user["id"]
    cid = await active_company_id(uid)
    company = await resolve_company(uid, cid) or {}
    doc = {
        "user_id": uid,
        "company_id": cid,
        "company_name": company.get("name") or "Empresa",
        "authorized": True,
        "site_live_owner": True,
        "authorized_at": _now_iso(),
        "auto_publish_after_strategy_approval": inp.auto_publish_after_strategy_approval,
        "auto_generate_hero_images": inp.auto_generate_hero_images,
        "allow_section_overrides": inp.allow_section_overrides,
        "allow_delete": inp.allow_delete,
        "managed_route_prefixes": MANAGED_ROUTE_PREFIXES,
        "allowed_slot_keys": list(SAFE_SECTION_SLOTS.keys()),
        "authorization_note": "Autorização única registada. O agente pode criar, editar, remover e reverter conteúdos públicos dentro do escopo seguro deste gateway.",
        "updated_at": _now_iso(),
    }
    await db.site_publication_settings.update_many({}, {"$set": {"site_live_owner": False}})
    await db.site_publication_settings.update_one({"user_id": uid, "company_id": cid}, {"$set": doc}, upsert=True)
    return await get_site_publishing_status(uid, cid)


@router.post("/marketing/site-publishing/content")
async def create_or_update_site_content(inp: SiteContentUpsertIn, user: dict = Depends(premium_user)):
    uid = user["id"]
    cid = await active_company_id(uid)
    entry = await upsert_site_content(uid, cid, inp, actor="manual")
    return {"entry": entry, "status": await get_site_publishing_status(uid, cid)}


@router.post("/marketing/site-publishing/content/{entry_id}/remove")
async def delete_site_content(entry_id: str, user: dict = Depends(premium_user)):
    uid = user["id"]
    cid = await active_company_id(uid)
    entry = await remove_site_content(uid, cid, entry_id, actor="manual")
    return {"entry": entry, "status": await get_site_publishing_status(uid, cid)}


@router.post("/marketing/site-publishing/content/{entry_id}/rollback")
async def rollback_site_entry(entry_id: str, inp: SiteRollbackIn, user: dict = Depends(premium_user)):
    uid = user["id"]
    cid = await active_company_id(uid)
    entry = await rollback_site_content(uid, cid, entry_id, inp.version_id, actor="manual")
    return {"entry": entry, "status": await get_site_publishing_status(uid, cid)}


@router.post("/marketing/site-publishing/run")
async def run_site_publication_now(inp: SiteAgentRunIn, user: dict = Depends(premium_user)):
    uid = user["id"]
    cid = await active_company_id(uid)
    agent = await db.marketing_organic_agents.find_one({"user_id": uid, "company_id": cid, "strategy_approved": True}, {"_id": 0})
    if not agent:
        raise HTTPException(400, "A estratégia inicial do Crescimento Orgânico ainda não foi aprovada.")
    entry = await maybe_publish_autonomous_site_content(uid, cid, deepcopy(agent), use_ai=inp.use_ai)
    return {"published_entry": entry, "status": await get_site_publishing_status(uid, cid)}


@router.get("/public/site/entries")
async def public_site_entries(kind: str = "article", limit: int = 20):
    owner_cid = await _live_owner_company_id()
    if not owner_cid:
        return {"entries": []}
    rows = await db.site_content_entries.find({"company_id": owner_cid, "kind": kind, "status": "published"}, {"_id": 0, "user_id": 0, "company_id": 0}).sort("published_at", -1).to_list(max(1, min(limit, 50)))
    return {"entries": rows}


@router.get("/public/site/article/{slug}")
async def public_site_article(slug: str):
    owner_cid = await _live_owner_company_id()
    row = await db.site_content_entries.find_one({"company_id": owner_cid, "kind": "article", "slug": slug, "status": "published"}, {"_id": 0, "user_id": 0, "company_id": 0})
    if not row:
        raise HTTPException(404, "Artigo não encontrado.")
    return {"entry": row}


@router.get("/public/site/page/{slug}")
async def public_site_page(slug: str):
    owner_cid = await _live_owner_company_id()
    row = await db.site_content_entries.find_one({"company_id": owner_cid, "kind": "page", "slug": slug, "status": "published"}, {"_id": 0, "user_id": 0, "company_id": 0})
    if not row:
        raise HTTPException(404, "Página não encontrada.")
    return {"entry": row}


@router.get("/public/site/sections")
async def public_site_sections(slots: str = ""):
    slot_keys = [item.strip() for item in (slots or "").split(",") if item.strip()]
    if not slot_keys:
        return {"sections": {}}
    owner_cid = await _live_owner_company_id()
    rows = await db.site_content_entries.find({"company_id": owner_cid, "kind": "section_override", "slot_key": {"$in": slot_keys}, "status": "published"}, {"_id": 0, "slot_key": 1, "slot_value": 1, "public_url": 1, "updated_at": 1}).to_list(len(slot_keys))
    payload = {row.get("slot_key"): {"value": row.get("slot_value"), "url": row.get("public_url"), "updated_at": row.get("updated_at")} for row in rows}
    return {"sections": payload}


@router.post("/public/site/view/{kind}/{slug}")
async def public_site_track_view(kind: str, slug: str):
    if kind not in {"article", "page"}:
        raise HTTPException(400, "Tipo inválido.")
    owner_cid = await _live_owner_company_id()
    row = await db.site_content_entries.find_one({"company_id": owner_cid, "kind": kind, "slug": slug, "status": "published"})
    if not row:
        raise HTTPException(404, "Conteúdo não encontrado.")
    metrics = row.get("metrics") or {"views": 0, "rollback_count": 0, "last_view_at": None}
    metrics["views"] = int(metrics.get("views", 0) or 0) + 1
    metrics["last_view_at"] = _now_iso()
    editorial_score = _compute_editorial_score({**row, "metrics": metrics})
    await db.site_content_entries.update_one({"id": row.get("id")}, {"$set": {"metrics": metrics, "editorial_score": editorial_score, "updated_at": _now_iso()}})
    return {"ok": True, "views": metrics["views"]}