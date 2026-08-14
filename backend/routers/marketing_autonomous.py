"""Diretor de Marketing — agente autônomo de Crescimento Orgânico."""
import asyncio
import re
import uuid
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core import active_company_id, ai_json, db, logger, premium_user
from routers.council import DIRECTORS, _ctx_text, build_council_context
from routers.marketing import _ctx, _prompt_context, _short, _str_list
from routers.site_publishing import SiteContentUpsertIn, SiteSectionBlockIn, _get_settings as _site_gateway_settings, _slugify, upsert_site_content

router = APIRouter()

STOPWORDS = {
    "para", "com", "uma", "mais", "como", "sobre", "entre", "pelos", "pelas", "este", "esta",
    "esse", "essa", "your", "ours", "with", "from", "that", "have", "will", "into", "about",
    "serviço", "servicos", "serviços", "empresa", "home", "page", "blog", "contacto", "contato",
    "contact", "sobre", "mais", "aqui", "nossa", "nosso", "para", "site", "cada", "your", "than",
}
PREFERRED_LINK_HINTS = ["sobre", "about", "servicos", "serviços", "services", "solucoes", "soluções", "blog", "case", "contact", "contacto", "contato"]


class OrganicStrategyIn(BaseModel):
    domain: str
    objective: str = "Gerar crescimento orgânico com foco em leads qualificados e conversão."


class OrganicObjectiveIn(BaseModel):
    objective: str


class _SiteParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.meta_description = ""
        self.headings = []
        self.links = []
        self._capture = None
        self._chunks = []
        self._title_chunks = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self._capture = "title"
        elif tag in {"h1", "h2", "h3"}:
            self._capture = tag
            self._chunks = []
        elif tag == "meta" and (attrs.get("name") or "").lower() == "description":
            self.meta_description = attrs.get("content", "")[:320]
        elif tag == "a" and attrs.get("href"):
            self.links.append(attrs.get("href"))
        elif tag in {"script", "style"}:
            self._capture = None

    def handle_endtag(self, tag):
        if tag == "title" and self._capture == "title":
            self.title = " ".join(self._title_chunks).strip()[:180]
            self._title_chunks = []
            self._capture = None
        elif tag in {"h1", "h2", "h3"} and self._capture == tag:
            text = " ".join(self._chunks).strip()
            if text:
                self.headings.append(text[:180])
            self._chunks = []
            self._capture = None

    def handle_data(self, data):
        cleaned = re.sub(r"\s+", " ", (data or "")).strip()
        if not cleaned:
            return
        if self._capture == "title":
            self._title_chunks.append(cleaned)
        elif self._capture in {"h1", "h2", "h3"}:
            self._chunks.append(cleaned)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _serialize(doc: Optional[dict]):
    if not doc:
        return None
    out = dict(doc)
    out.pop("_id", None)
    out.pop("user_id", None)
    out.pop("company_id", None)
    out.pop("execution_lock_until", None)
    return out


def _normalize_domain(domain: str) -> str:
    raw = (domain or "").strip()
    if not raw:
        raise HTTPException(400, "Indique o domínio do site.")
    if not re.match(r"^https?://", raw, flags=re.I):
        raw = f"https://{raw}"
    parsed = urlparse(raw)
    if not parsed.netloc:
        raise HTTPException(400, "Domínio inválido.")
    cleaned = f"{parsed.scheme}://{parsed.netloc}{parsed.path or ''}"
    return cleaned.rstrip("/") or f"{parsed.scheme}://{parsed.netloc}"


def _same_domain(url_a: str, url_b: str) -> bool:
    try:
        return urlparse(url_a).netloc == urlparse(url_b).netloc
    except Exception:
        return False


def _clean_text(text: str, max_len: int = 2800) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()[:max_len]


async def _fetch_page(url: str) -> Optional[dict]:
    headers = {"User-Agent": "CEOAIOrganicGrowth/1.0 (+https://ceo-ai.local)"}
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers=headers) as client:
            res = await client.get(url)
        if res.status_code >= 400:
            return None
        ctype = (res.headers.get("content-type") or "").lower()
        if "text/html" not in ctype and "application/xhtml+xml" not in ctype:
            return None
        parser = _SiteParser()
        parser.feed(res.text[:300000])
        return {
            "url": str(res.url),
            "title": parser.title,
            "description": parser.meta_description,
            "headings": parser.headings[:10],
            "links": parser.links[:60],
            "text": _clean_text(re.sub(r"<[^>]+>", " ", res.text), 5000),
        }
    except Exception as e:
        logger.error(f"organic fetch page error {url}: {e}")
        return None


def _pick_internal_links(base_url: str, links: list[str]) -> list[str]:
    out = []
    seen = set()
    for href in links or []:
        absolute = urljoin(base_url, href)
        if not _same_domain(base_url, absolute):
            continue
        if any(absolute.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp", ".svg", ".pdf", ".zip")):
            continue
        cleaned = absolute.rstrip("/")
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        out.append(cleaned)
    scored = sorted(
        out,
        key=lambda item: (
            0 if any(hint in item.lower() for hint in PREFERRED_LINK_HINTS) else 1,
            len(item),
        ),
    )
    return scored[:4]


def _keyword_candidates(text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-]{2,}", (text or "").lower())
    freq = {}
    for token in tokens:
        if token in STOPWORDS or token.isdigit() or len(token) < 4:
            continue
        freq[token] = freq.get(token, 0) + 1
    return [k for k, _ in sorted(freq.items(), key=lambda item: item[1], reverse=True)[:8]]


def _fallback_site_analysis(domain: str, pages: list[dict]) -> dict:
    pages = [page for page in pages if page]
    first_page = pages[0] if pages else {}
    combined_text = " ".join(page.get("text", "") for page in pages)
    headings = []
    for page in pages:
        headings.extend(page.get("headings") or [])
    keywords = _keyword_candidates(" ".join(headings) + " " + combined_text)
    services = [item for item in headings if 3 <= len(item.split()) <= 10][:5] or [domain.split("//")[-1].split("/")[0]]
    cta_hits = []
    for item in ["contactar", "contacte", "pedir", "marcar", "orçamento", "diagnóstico", "demo", "fale", "ligar", "solicitar"]:
        if item in combined_text.lower():
            cta_hits.append(item)
    trust_hits = []
    for item in ["clientes", "testemunhos", "casos", "anos", "equipa", "resultados", "projetos", "parceiros"]:
        if item in combined_text.lower():
            trust_hits.append(item)

    opportunities = []
    if len(pages) <= 1:
        opportunities.append({
            "title": "Expandir páginas-chave do site",
            "detail": "Criar ou reforçar páginas de serviços, prova social e captação para dar mais matéria ao crescimento orgânico.",
            "priority": "alta",
        })
    if not any("blog" in (page.get("url") or "") or "artigo" in (page.get("title") or "").lower() for page in pages):
        opportunities.append({
            "title": "Abrir cluster editorial",
            "detail": "O site não mostra uma área editorial forte. Vale criar conteúdos evergreen e páginas de resposta a dúvidas do ICP.",
            "priority": "alta",
        })
    if not cta_hits:
        opportunities.append({
            "title": "Reforçar CTA principal",
            "detail": "O site precisa de um CTA dominante e repetido para transformar atenção em lead.",
            "priority": "alta",
        })
    if not trust_hits:
        opportunities.append({
            "title": "Adicionar prova social visível",
            "detail": "Faltam sinais fortes de confiança, casos ou clientes para aumentar a conversão orgânica.",
            "priority": "média",
        })
    if len(keywords) < 4:
        opportunities.append({
            "title": "Clarificar linguagem e keywords",
            "detail": "As páginas precisam de temas e mensagens mais consistentes para captar procura qualificada.",
            "priority": "média",
        })

    return {
        "domain": domain,
        "final_url": first_page.get("url") or domain,
        "fetch_ok": bool(pages),
        "pages_scanned": len(pages),
        "website_summary": _short(first_page.get("description") or (headings[0] if headings else f"Site institucional em {domain}."), f"Site institucional em {domain}."),
        "positioning": _short((headings[0] if headings else "Presença digital a clarificar com foco em proposta de valor e conversão.")),
        "primary_services": services,
        "keywords": keywords or ["crescimento", "conversão", "autoridade"],
        "trust_signals": trust_hits or ["equipa", "resultados"],
        "calls_to_action": cta_hits or ["pedir diagnóstico", "falar com a equipa"],
        "content_angles": [
            "Responder às perguntas que o cliente ideal faz antes de comprar",
            "Mostrar prova real, bastidores e resultados",
            "Transformar páginas de serviço em ativos de conversão",
        ],
        "opportunities": opportunities[:5] or [{
            "title": "Clarificar posicionamento orgânico",
            "detail": "Definir temas, prova e CTA para o site sustentar conteúdos e conversão.",
            "priority": "alta",
        }],
        "page_snapshots": [
            {
                "url": page.get("url"),
                "title": page.get("title") or page.get("url"),
                "description": page.get("description"),
                "headings": page.get("headings") or [],
            }
            for page in pages[:4]
        ],
        "scanned_at": _now_iso(),
    }


def _normalize_site_ai(raw: dict, fallback: dict) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    return {
        **fallback,
        "website_summary": _short(raw.get("website_summary"), fallback.get("website_summary")),
        "positioning": _short(raw.get("positioning"), fallback.get("positioning")),
        "primary_services": _str_list(raw.get("primary_services"), 6) or fallback.get("primary_services") or [],
        "keywords": _str_list(raw.get("keywords"), 8) or fallback.get("keywords") or [],
        "trust_signals": _str_list(raw.get("trust_signals"), 6) or fallback.get("trust_signals") or [],
        "calls_to_action": _str_list(raw.get("calls_to_action"), 6) or fallback.get("calls_to_action") or [],
        "content_angles": _str_list(raw.get("content_angles"), 6) or fallback.get("content_angles") or [],
        "opportunities": [
            {
                "title": _short(item.get("title"), fallback["opportunities"][0]["title"]),
                "detail": _short(item.get("detail"), fallback["opportunities"][0]["detail"]),
                "priority": _short(item.get("priority"), "média").lower(),
            }
            for item in (raw.get("opportunities") if isinstance(raw.get("opportunities"), list) else [])[:5]
            if isinstance(item, dict)
        ] or fallback.get("opportunities") or [],
    }


async def scan_site(domain: str) -> dict:
    normalized = _normalize_domain(domain)
    home = await _fetch_page(normalized)
    pages = [home] if home else []
    links = _pick_internal_links(home.get("url") if home else normalized, home.get("links") if home else [])
    if links:
        results = await asyncio.gather(*[_fetch_page(link) for link in links[:3]])
        for item in results:
            if item:
                pages.append(item)
    fallback = _fallback_site_analysis(normalized, pages)
    corpus = {
        "pages": [{
            "url": page.get("url"),
            "title": page.get("title"),
            "description": page.get("description"),
            "headings": page.get("headings") or [],
            "excerpt": _clean_text(page.get("text"), 1200),
        } for page in pages[:4]],
    }
    try:
        ai = await ai_json(
            "És um estratega de SEO e conteúdo orgânico. Respondes só com JSON em português europeu.",
            (
                f"Analisa o site {normalized} com base nestas páginas reais: {corpus}. "
                "Devolve APENAS JSON válido com a estrutura "
                '{"website_summary":str,"positioning":str,"primary_services":[str],"keywords":[str],'
                '"trust_signals":[str],"calls_to_action":[str],"content_angles":[str],'
                '"opportunities":[{"title":str,"detail":str,"priority":str}]}. '
                "Quero um resumo objetivo, oportunidades acionáveis e linguagem executiva."
            ),
        )
    except Exception:
        ai = {}
    return _normalize_site_ai(ai, fallback)


def _director_alignment_fallback(key: str, council_ctx: dict, site_analysis: dict) -> dict:
    if key == "financeiro":
        runway = council_ctx.get("runway")
        cash_pressure = "Proteger caixa e priorizar tráfego com intenção alta." if isinstance(runway, (int, float)) and runway <= 6 else "Crescer com disciplina, sem sacrificar margem."
        return {
            "summary": cash_pressure,
            "priorities": [
                "Dar prioridade a páginas e conteúdos com potencial de conversão",
                "Medir leads qualificados antes de aumentar volume",
                "Usar prova e oferta clara para encurtar tempo até receita",
            ],
            "constraints": [
                "Evitar dispersão editorial sem ligação ao objetivo de receita",
                "Manter foco em conversão e qualidade do lead",
            ],
            "metrics": ["tráfego acionado", "leads qualificados", "taxa de conversão"],
        }
    return {
        "summary": "O crescimento orgânico deve servir o pipeline e o ICP, não apenas gerar alcance.",
        "priorities": [
            "Atrair procura com fit ao ICP atual",
            "Criar conteúdos que respondam às objeções comerciais",
            "Apoiar follow-up, prova social e reativação de oportunidades",
        ],
        "constraints": [
            "Não sacrificar qualidade do lead por volume de alcance",
            f"Alinhar mensagem com o site e oferta principal: {(site_analysis.get('primary_services') or ['serviços principais'])[0]}",
        ],
        "metrics": ["leads novos", "leads em reunião/proposta", "conversão lead/tráfego"],
    }


async def _run_alignment_for(key: str, council_ctx: dict, site_analysis: dict) -> tuple[str, dict]:
    fallback = _director_alignment_fallback(key, council_ctx, site_analysis)
    try:
        raw = await ai_json(
            DIRECTORS[key]["system"],
            (
                f"Contexto do Conselho: {_ctx_text(council_ctx)}\n"
                f"Análise do site: {site_analysis}\n\n"
                "Devolve APENAS JSON válido no formato "
                '{"summary":str,"priorities":[str],"constraints":[str],"metrics":[str]}. '
                "Quero o alinhamento do diretor com foco no Crescimento Orgânico autônomo."
            ),
        )
    except Exception:
        raw = {}
    raw = raw if isinstance(raw, dict) else {}
    return key, {
        "summary": _short(raw.get("summary"), fallback["summary"]),
        "priorities": _str_list(raw.get("priorities"), 4) or fallback["priorities"],
        "constraints": _str_list(raw.get("constraints"), 4) or fallback["constraints"],
        "metrics": _str_list(raw.get("metrics"), 4) or fallback["metrics"],
    }


async def director_alignment(uid: str, cid: str, site_analysis: dict) -> dict:
    council_ctx = await build_council_context(uid, cid)
    results = await asyncio.gather(
        _run_alignment_for("financeiro", council_ctx, site_analysis),
        _run_alignment_for("comercial", council_ctx, site_analysis),
    )
    return {key: value for key, value in results}


def _strategy_fallback(ctx: dict, site_analysis: dict, alignment: dict, objective: str) -> dict:
    service = (site_analysis.get("primary_services") or [ctx.get("sector") or "serviço principal"])[0]
    return {
        "thesis": f"Transformar o site e os conteúdos em ativos de captação contínua para {service}, priorizando qualidade e conversão antes de escalar volume.",
        "north_star": objective or "Gerar crescimento orgânico previsível com foco em leads qualificados.",
        "phase_plan": [
            {"phase": "Dias 1-30", "goal": "Clarificar proposta de valor, páginas prioritárias e CTA principal.", "actions": ["Reforçar mensagens do site", "Publicar conteúdo de autoridade", "Criar provas de confiança"]},
            {"phase": "Dias 31-60", "goal": "Aumentar tráfego com intenção e repetir os formatos com melhor sinal.", "actions": ["Escalar temas vencedores", "Testar novos ganchos", "Apoiar follow-up comercial"]},
            {"phase": "Dias 61-90", "goal": "Converter melhor e consolidar um ritmo autónomo sustentável.", "actions": ["Otimizar CTA e distribuição", "Reciclar prova social", "Atualizar páginas com base nos dados"]},
        ],
        "content_pillars": [
            {"name": "Prova e autoridade", "reason": "Aumenta confiança e reduz fricção comercial."},
            {"name": "Educação com intenção", "reason": "Capta procura qualificada ao responder a dúvidas reais."},
            {"name": "Oferta e conversão", "reason": "Transforma atenção em pedido de contacto."},
        ],
        "channel_plan": [
            {"channel": "Site", "approach": "Reforçar páginas-chave, CTA e prova social.", "cadence": "Ajustes contínuos semanais"},
            {"channel": "Instagram / Facebook", "approach": "Publicar conteúdos que empurram tráfego e confiança.", "cadence": "3-4 peças por semana"},
            {"channel": "CRM", "approach": "Reciclar conteúdos fortes para follow-up e reativação.", "cadence": "1-2 ativações por semana"},
        ],
        "kpis": [
            {"label": "Tráfego acionado", "target": "Subir cliques e sinais de visita com intenção", "reason": "Mede atração útil."},
            {"label": "Leads qualificados", "target": "Aumentar leads novos e oportunidades em reunião/proposta", "reason": "Liga marketing a pipeline."},
            {"label": "Conversão", "target": "Melhorar a taxa lead/tráfego ao longo dos 90 dias", "reason": "Privilegia qualidade sobre volume."},
        ],
        "decision_guardrails": (alignment.get("financeiro", {}).get("constraints") or [])[:2] + (alignment.get("comercial", {}).get("constraints") or [])[:2],
        "first_actions": [
            f"Mapear o site e reforçar a promessa principal de {service}.",
            "Publicar a primeira sequência de conteúdos orientados a prova + dor do ICP.",
            "Medir sinais iniciais e ajustar o CTA dominante.",
        ],
        "ask_approval_only_when": [
            "Houver mudança estratégica relevante na oferta ou posicionamento",
            "Existir risco reputacional ou conflito com prioridades financeiras/comerciais",
            "For preciso alterar o objetivo principal do agente",
        ],
    }


def _normalize_strategy(raw: dict, fallback: dict) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    phases = []
    for item in (raw.get("phase_plan") if isinstance(raw.get("phase_plan"), list) else [])[:3]:
        if not isinstance(item, dict):
            continue
        phases.append({
            "phase": _short(item.get("phase"), "Fase"),
            "goal": _short(item.get("goal"), "Objetivo"),
            "actions": _str_list(item.get("actions"), 4) or ["Executar ações coerentes com a fase."],
        })
    pillars = []
    for item in (raw.get("content_pillars") if isinstance(raw.get("content_pillars"), list) else [])[:4]:
        if not isinstance(item, dict):
            continue
        pillars.append({"name": _short(item.get("name"), "Pilar"), "reason": _short(item.get("reason"), "Razão")})
    channels = []
    for item in (raw.get("channel_plan") if isinstance(raw.get("channel_plan"), list) else [])[:4]:
        if not isinstance(item, dict):
            continue
        channels.append({
            "channel": _short(item.get("channel"), "Canal"),
            "approach": _short(item.get("approach"), "Abordagem"),
            "cadence": _short(item.get("cadence"), "Cadência"),
        })
    kpis = []
    for item in (raw.get("kpis") if isinstance(raw.get("kpis"), list) else [])[:4]:
        if not isinstance(item, dict):
            continue
        kpis.append({
            "label": _short(item.get("label"), "KPI"),
            "target": _short(item.get("target"), "Meta"),
            "reason": _short(item.get("reason"), "Razão"),
        })
    return {
        **fallback,
        "thesis": _short(raw.get("thesis"), fallback.get("thesis")),
        "north_star": _short(raw.get("north_star"), fallback.get("north_star")),
        "phase_plan": phases or fallback.get("phase_plan") or [],
        "content_pillars": pillars or fallback.get("content_pillars") or [],
        "channel_plan": channels or fallback.get("channel_plan") or [],
        "kpis": kpis or fallback.get("kpis") or [],
        "decision_guardrails": _str_list(raw.get("decision_guardrails"), 4) or fallback.get("decision_guardrails") or [],
        "first_actions": _str_list(raw.get("first_actions"), 4) or fallback.get("first_actions") or [],
        "ask_approval_only_when": _str_list(raw.get("ask_approval_only_when"), 4) or fallback.get("ask_approval_only_when") or [],
    }


async def build_strategy(uid: str, cid: str, objective: str, domain: str) -> tuple[dict, dict, dict, dict]:
    ctx = await _ctx(uid, cid)
    site_analysis = await scan_site(domain)
    alignment = await director_alignment(uid, cid, site_analysis)
    fallback = _strategy_fallback(ctx, site_analysis, alignment, objective)
    try:
        raw = await ai_json(
            "És o agente autônomo de Crescimento Orgânico do Diretor de Marketing. Respondes só com JSON em português europeu.",
            (
                f"Contexto real da empresa:\n{_prompt_context(ctx)}\n\n"
                f"Site analisado: {site_analysis}\n\n"
                f"Alinhamento Financeiro e Comercial: {alignment}\n\n"
                f"Objetivo principal do agente: {objective}\n\n"
                "Devolve APENAS JSON válido no formato "
                '{"thesis":str,"north_star":str,"phase_plan":[{"phase":str,"goal":str,"actions":[str]}],'
                '"content_pillars":[{"name":str,"reason":str}],'
                '"channel_plan":[{"channel":str,"approach":str,"cadence":str}],'
                '"kpis":[{"label":str,"target":str,"reason":str}],'
                '"decision_guardrails":[str],"first_actions":[str],"ask_approval_only_when":[str]}. '
                "Quero uma estratégia de 90 dias que privilegie qualidade e alinhamento antes de aumentar volume."
            ),
        )
    except Exception:
        raw = {}
    strategy = _normalize_strategy(raw, fallback)
    return ctx, site_analysis, alignment, strategy


async def build_strategy_fast(uid: str, cid: str, objective: str, domain: str, refresh_site: bool = True, current_site: Optional[dict] = None) -> tuple[dict, dict, dict, dict]:
    ctx = await _ctx(uid, cid)
    site_analysis = await scan_site(domain) if refresh_site else (current_site or await scan_site(domain))
    council_ctx = await build_council_context(uid, cid)
    alignment = {
        "financeiro": _director_alignment_fallback("financeiro", council_ctx, site_analysis),
        "comercial": _director_alignment_fallback("comercial", council_ctx, site_analysis),
    }
    strategy = _strategy_fallback(ctx, site_analysis, alignment, objective)
    return ctx, site_analysis, alignment, strategy


async def _metrics_snapshot(uid: str, cid: str) -> dict:
    since = (datetime.now(timezone.utc).date() - timedelta(days=29)).isoformat()
    static_rows = await db.growth_internal_page_daily.find({"user_id": uid, "company_id": cid, "date": {"$gte": since}}, {"_id": 0, "views": 1}).to_list(500)
    site_rows = await db.site_content_entries.find(
        {"user_id": uid, "company_id": cid, "status": "published"},
        {"_id": 0, "metrics.views": 1, "managed_by": 1},
    ).to_list(200)
    traffic = sum(int(row.get("views", 0) or 0) for row in static_rows)
    traffic += sum(int((row.get("metrics") or {}).get("views", 0) or 0) for row in site_rows)
    leads = await db.crm_leads.count_documents({"user_id": uid, "company_id": cid, "created_at": {"$gte": since}})
    converted = await db.crm_leads.count_documents({
        "user_id": uid,
        "company_id": cid,
        "created_at": {"$gte": since},
        "stage": {"$in": ["reuniao", "proposta", "negociacao", "ganho"]},
    })
    latest_growth = await db.growth_agent_reports.find_one(
        {"user_id": uid, "company_id": cid},
        {"_id": 0, "learnings": 1, "next_steps": 1},
        sort=[("created_at", -1)],
    ) or {}
    published_entries = len(site_rows)
    return {
        "traffic": traffic,
        "traffic_label": "Views do site e páginas públicas (30d)",
        "leads": leads,
        "conversion_rate": round((leads / max(traffic, 1)) * 100, 2) if traffic else 0,
        "converted_pipeline": converted,
        "published_site_entries": published_entries,
        "metrics_mocked": False,
        "analytics_insights": _str_list(latest_growth.get("learnings"), 3),
        "recommended_actions": _str_list(latest_growth.get("next_steps"), 3),
        "captured_at": _now_iso(),
    }


def _action_fallback(agent: dict, metrics: dict, site_gateway: dict) -> list[dict]:
    site = agent.get("site_analysis") or {}
    opportunities = site.get("opportunities") or []
    service = (site.get("primary_services") or ["serviço principal"])[0]
    keyword = (site.get("keywords") or [service])[0]
    first_opportunity = (opportunities[0] or {}).get("title") if opportunities else "Clarificar proposta de valor"
    second_opportunity = (opportunities[1] or {}).get("title") if len(opportunities) > 1 else "Reforçar prova e CTA"
    return [
        {
            "title": f"{service}: guia prático sobre {keyword}",
            "theme": "conteúdo evergreen",
            "format": "Artigo SEO",
            "goal": "Captar procura qualificada no site e responder a uma intenção concreta.",
            "why_now": f"O site mostra a oportunidade '{first_opportunity}' e o agente precisa de reforçar cobertura orgânica sem depender das redes sociais.",
            "target_kind": "article",
            "seo_keyword": keyword,
            "cta": "Pedir diagnóstico ou contacto.",
        },
        {
            "title": f"{service}: página de conversão reforçada",
            "theme": "otimização de página",
            "format": "Página do site",
            "goal": "Melhorar clareza, prova social e CTA numa página crítica do site.",
            "why_now": f"O agente está a trabalhar para {agent.get('objective') or 'crescimento orgânico'} e a prioridade seguinte é '{second_opportunity}'.",
            "target_kind": "page",
            "seo_keyword": service.lower(),
            "cta": "Levar o visitante a pedir contacto.",
        },
    ]


def _normalize_actions(raw: dict, fallback: list[dict]) -> list[dict]:
    items = raw.get("actions") if isinstance(raw, dict) and isinstance(raw.get("actions"), list) else []
    out = []
    for idx, item in enumerate(items[:2]):
        if not isinstance(item, dict):
            continue
        fb = fallback[idx if idx < len(fallback) else 0]
        out.append({
            "title": _short(item.get("title"), fb["title"]),
            "theme": _short(item.get("theme"), fb["theme"]),
            "format": _short(item.get("format"), fb["format"]),
            "goal": _short(item.get("goal"), fb["goal"]),
            "why_now": _short(item.get("why_now"), fb["why_now"]),
            "target_kind": _short(item.get("target_kind"), fb["target_kind"]),
            "seo_keyword": _short(item.get("seo_keyword"), fb["seo_keyword"]),
            "cta": _short(item.get("cta"), fb["cta"]),
        })
    return out or fallback


async def _generate_next_actions(uid: str, cid: str, agent: dict, metrics: dict, site_gateway: dict, queue_depth: int, use_ai: bool = True) -> list[dict]:
    fallback = _action_fallback(agent, metrics, site_gateway)
    if not use_ai:
        return fallback
    try:
        raw = await ai_json(
            "És o agente autônomo de Crescimento Orgânico. Respondes só com JSON em português europeu.",
            (
                f"Agente atual: {agent}\n"
                f"Métricas atuais: {metrics}\n"
                f"Gateway do site: {site_gateway}\n"
                f"Fila atual: {queue_depth}\n\n"
                "Devolve APENAS JSON válido com a estrutura "
                '{"actions":[{"title":str,"theme":str,"format":str,"goal":str,"why_now":str,'
                '"target_kind":str,"seo_keyword":str,"cta":str}]}. '
                "Quero 2 ações autónomas focadas apenas no site, SEO e conteúdo público."
            ),
        )
    except Exception:
        raw = {}
    return _normalize_actions(raw, fallback)


async def _publish_growth_site_action(uid: str, cid: str, agent: dict, action_doc: dict, use_ai: bool = False) -> dict:
    settings = await _site_gateway_settings(uid, cid)
    if not settings.get("authorized"):
        note = "O gateway do site ainda não está autorizado para publicação automática."
        await db.marketing_organic_actions.update_one(
            {"_id": action_doc["_id"]},
            {"$set": {"status": "ready", "note": note, "updated_at": _now_iso()}},
        )
        action_doc.update({"status": "ready", "note": note})
        return action_doc

    site = agent.get("site_analysis") or {}
    service = (site.get("primary_services") or ["serviço principal"])[0]
    title = action_doc.get("title") or f"{service}: atualização do site"
    excerpt = f"Atualização do Growth Agent para reforçar {action_doc.get('seo_keyword') or service} com foco em procura qualificada e conversão."
    intro = action_doc.get("why_now") or f"Conteúdo criado autonomamente para reforçar {service} sem alterar design ou navegação."
    sections = [
        SiteSectionBlockIn(
            heading="Porque esta atualização existe",
            paragraphs=[action_doc.get("why_now") or "O agente identificou uma oportunidade clara no site."],
            bullets=[],
        ),
        SiteSectionBlockIn(
            heading="O que esta página precisa de resolver",
            paragraphs=[action_doc.get("goal") or "Responder à intenção de procura e reduzir fricção até ao contacto."],
            bullets=["clareza de oferta", "prova social", "CTA direto"],
        ),
        SiteSectionBlockIn(
            heading="Próximo passo recomendado",
            paragraphs=["O objetivo é transformar a visita em contacto qualificado, sem mexer no layout do site."],
            bullets=[action_doc.get("cta") or "Pedir diagnóstico"],
        ),
    ]

    entry = await upsert_site_content(
        uid,
        cid,
        SiteContentUpsertIn(
            kind="page" if action_doc.get("target_kind") == "page" else "article",
            title=title,
            slug=_slugify(title),
            excerpt=excerpt,
            intro=intro,
            sections=sections,
            cta_label="Falar com a equipa",
            cta_url="/contacto",
            seo_keyword=action_doc.get("seo_keyword") or service,
            seo_title=title,
            seo_description=excerpt,
            strategy_reason=action_doc.get("why_now") or "Ação autónoma do Growth Agent.",
            objective=agent.get("objective") or "crescimento orgânico",
            campaign_label="Growth Agent",
            publish_now=True,
            auto_generate_hero_image=settings.get("auto_generate_hero_images", True),
        ),
        actor="organic_agent",
    )
    await db.marketing_organic_actions.update_one(
        {"_id": action_doc["_id"]},
        {"$set": {
            "status": "published",
            "public_url": entry.get("public_url"),
            "site_entry_id": entry.get("id"),
            "published_at": _now_iso(),
            "note": "Publicado automaticamente pelo Growth Agent no site.",
            "updated_at": _now_iso(),
        }},
    )
    action_doc.update({
        "status": "published",
        "public_url": entry.get("public_url"),
        "site_entry_id": entry.get("id"),
        "published_at": _now_iso(),
        "note": "Publicado automaticamente pelo Growth Agent no site.",
    })
    return action_doc


async def _generate_report(uid: str, cid: str, agent: dict, metrics: dict, period: str, reference_key: str, use_ai: bool = True):
    existing = await db.marketing_organic_reports.find_one({
        "user_id": uid,
        "company_id": cid,
        "period": period,
        "reference_key": reference_key,
    }, {"_id": 0})
    if existing:
        return existing
    actions = await db.marketing_organic_actions.find({"user_id": uid, "company_id": cid}, {"_id": 0}).sort("created_at", -1).to_list(6)
    fallback = {
        "headline": f"Relatório {period} do Growth Agent",
        "summary": "O agente manteve o foco em qualidade, alinhamento com vendas/finanças e ajuste contínuo da estratégia.",
        "executed_actions": [item.get("title") for item in actions[:3] if item.get("title")] or ["Sem ações relevantes registadas ainda."],
        "results": [
            f"Tráfego monitorizado: {metrics.get('traffic', 0)}",
            f"Leads monitorizados: {metrics.get('leads', 0)}",
            f"Conversão atual: {metrics.get('conversion_rate', 0)}%",
        ],
        "learnings": metrics.get("analytics_insights")[:3] or ["Ainda a recolher sinais para otimização mais forte."],
        "next_adjustments": metrics.get("recommended_actions")[:3] or ["Continuar a testar ângulos e CTA com melhor intenção."],
        "recommendations": ["Manter o foco em tráfego com intenção e prova clara antes de aumentar volume."],
    }
    if use_ai:
        try:
            raw = await ai_json(
                "És um Diretor de Marketing executivo. Respondes só com JSON em português europeu.",
                (
                    f"Agente: {agent}\nMétricas: {metrics}\nAções recentes: {actions}\n\n"
                    f"Gera um relatório {period} automático. Devolve APENAS JSON válido no formato "
                    '{"headline":str,"summary":str,"executed_actions":[str],"results":[str],'
                    '"learnings":[str],"next_adjustments":[str],"recommendations":[str]}. '
                    "Quero objetividade, foco em desempenho e recomendações acionáveis."
                ),
            )
        except Exception:
            raw = {}
    else:
        raw = {}
    raw = raw if isinstance(raw, dict) else {}
    doc = {
        "_id": str(uuid.uuid4()),
        "user_id": uid,
        "company_id": cid,
        "period": period,
        "reference_key": reference_key,
        "headline": _short(raw.get("headline"), fallback["headline"]),
        "summary": _short(raw.get("summary"), fallback["summary"]),
        "executed_actions": _str_list(raw.get("executed_actions"), 5) or fallback["executed_actions"],
        "results": _str_list(raw.get("results"), 5) or fallback["results"],
        "learnings": _str_list(raw.get("learnings"), 4) or fallback["learnings"],
        "next_adjustments": _str_list(raw.get("next_adjustments"), 4) or fallback["next_adjustments"],
        "recommendations": _str_list(raw.get("recommendations"), 4) or fallback["recommendations"],
        "metrics_snapshot": metrics,
        "created_at": _now_iso(),
    }
    await db.marketing_organic_reports.insert_one(doc)
    return _serialize(doc)


async def _ensure_reports(uid: str, cid: str, agent: dict, metrics: dict, use_ai: bool = True):
    now = datetime.now(timezone.utc)
    weekly_key = f"{now.isocalendar().year}-W{now.isocalendar().week:02d}"
    monthly_key = now.strftime("%Y-%m")
    await _generate_report(uid, cid, agent, metrics, "daily", now.date().isoformat(), use_ai=use_ai)
    await _generate_report(uid, cid, agent, metrics, "weekly", weekly_key, use_ai=use_ai)
    await _generate_report(uid, cid, agent, metrics, "monthly", monthly_key, use_ai=use_ai)


async def _panel_payload(uid: str, cid: str):
    agent_doc = await db.marketing_organic_agents.find_one({"user_id": uid, "company_id": cid})
    actions = await db.marketing_organic_actions.find({"user_id": uid, "company_id": cid}).sort("created_at", -1).to_list(8)
    report_rows = await db.marketing_organic_reports.find({"user_id": uid, "company_id": cid}).sort("created_at", -1).to_list(20)
    reports = {
        "daily": [_serialize(row) for row in report_rows if row.get("period") == "daily"][:3],
        "weekly": [_serialize(row) for row in report_rows if row.get("period") == "weekly"][:3],
        "monthly": [_serialize(row) for row in report_rows if row.get("period") == "monthly"][:3],
    }
    return {"agent": _serialize(agent_doc), "actions": [_serialize(row) for row in actions], "reports": reports}


async def run_organic_growth_agent_cycle(uid: str, cid: str, force: bool = False, fast_mode: bool = False):
    now = datetime.now(timezone.utc)
    lock_query = {
        "$or": [
            {"execution_lock_until": {"$exists": False}},
            {"execution_lock_until": {"$lt": now.isoformat()}},
        ]
    }
    claim_query = {
        "user_id": uid,
        "company_id": cid,
        "status": "running",
        **lock_query,
    }
    if not force:
        claim_query["next_run_at"] = {"$lte": now.isoformat()}
    agent = await db.marketing_organic_agents.find_one(claim_query)
    if not agent:
        return None
    lock_until = (now + timedelta(minutes=10)).isoformat()
    claimed = await db.marketing_organic_agents.find_one_and_update(
        {"_id": agent["_id"], "status": "running", **lock_query},
        {"$set": {"execution_lock_until": lock_until, "updated_at": _now_iso()}},
    )
    if not claimed:
        return None
    agent = dict(claimed)
    try:
        last_analysis = agent.get("last_analysis_at") or ""
        if not last_analysis or last_analysis < (now - timedelta(hours=24)).isoformat():
            _, site_analysis, alignment, strategy = await build_strategy(uid, cid, agent.get("objective") or "", agent.get("domain") or "")
            agent.update({"site_analysis": site_analysis, "director_alignment": alignment, "strategy": strategy, "last_analysis_at": _now_iso()})
        metrics = await _metrics_snapshot(uid, cid)
        site_gateway = await _site_gateway_settings(uid, cid)
        blockers = []
        if not site_gateway.get("authorized"):
            blockers.append("O gateway interno do site público ainda não foi autorizado; o agente analisa e decide, mas ainda não publica no site público.")

        pending_actions = await db.marketing_organic_actions.find(
            {"user_id": uid, "company_id": cid, "status": {"$in": ["draft", "ready"]}},
        ).sort("created_at", 1).to_list(10)

        if len(pending_actions) < 2:
            new_actions = await _generate_next_actions(uid, cid, agent, metrics, site_gateway, len(pending_actions), use_ai=not fast_mode)
            for item in new_actions[: max(1, 2 - len(pending_actions))]:
                action_doc = {
                    "_id": str(uuid.uuid4()),
                    "user_id": uid,
                    "company_id": cid,
                    "agent_id": agent["_id"],
                    "title": item.get("title"),
                    "theme": item.get("theme"),
                    "format": item.get("format"),
                    "goal": item.get("goal"),
                    "why_now": item.get("why_now"),
                    "target_kind": item.get("target_kind") or "article",
                    "seo_keyword": item.get("seo_keyword") or item.get("theme"),
                    "cta": item.get("cta"),
                    "status": "draft",
                    "created_at": _now_iso(),
                    "updated_at": _now_iso(),
                }
                await db.marketing_organic_actions.insert_one(action_doc)
            pending_actions = await db.marketing_organic_actions.find(
                {"user_id": uid, "company_id": cid, "status": {"$in": ["draft", "ready"]}},
            ).sort("created_at", 1).to_list(10)

        site_publication = None
        if site_gateway.get("authorized") and site_gateway.get("auto_publish_after_strategy_approval"):
            for action_doc in pending_actions[:2]:
                try:
                    published = await _publish_growth_site_action(uid, cid, agent, action_doc, use_ai=not fast_mode)
                    site_publication = {"public_url": published.get("public_url"), "title": published.get("title")}
                except Exception as e:
                    blockers.append(f"Falha ao publicar no site público: {str(e)[:180]}")
                    await db.marketing_organic_actions.update_one(
                        {"_id": action_doc["_id"]},
                        {"$set": {"status": "blocked", "note": str(e)[:180], "updated_at": _now_iso()}},
                    )
        else:
            for action_doc in pending_actions:
                await db.marketing_organic_actions.update_one(
                    {"_id": action_doc["_id"]},
                    {"$set": {"status": "ready", "note": "À espera de autorização do gateway do site.", "updated_at": _now_iso()}},
                )

        await _ensure_reports(uid, cid, agent, metrics, use_ai=not fast_mode)
        await db.marketing_organic_agents.update_one(
            {"_id": agent["_id"]},
            {"$set": {
                "site_analysis": agent.get("site_analysis"),
                "director_alignment": agent.get("director_alignment"),
                "strategy": agent.get("strategy"),
                "metrics": metrics,
                "blockers": blockers,
                "site_publishing": {
                    "authorized": bool(site_gateway.get("authorized")),
                    "auto_publish_after_strategy_approval": bool(site_gateway.get("auto_publish_after_strategy_approval")),
                    "latest_publication": site_publication,
                },
                "last_run_at": _now_iso(),
                "next_run_at": (now + timedelta(hours=6)).isoformat(),
                "last_error": None,
                "execution_lock_until": (now - timedelta(seconds=1)).isoformat(),
                "updated_at": _now_iso(),
            }},
        )
        return await _panel_payload(uid, cid)
    except Exception as e:
        logger.error(f"organic growth cycle error {uid}/{cid}: {e}")
        await db.marketing_organic_agents.update_one(
            {"_id": agent["_id"]},
            {"$set": {
                "last_error": str(e)[:400],
                "next_run_at": (now + timedelta(hours=1)).isoformat(),
                "execution_lock_until": (now - timedelta(seconds=1)).isoformat(),
                "updated_at": _now_iso(),
            }},
        )
        return None


async def run_all_organic_growth_agents():
    now_iso = _now_iso()
    rows = await db.marketing_organic_agents.find({"status": "running", "strategy_approved": True, "next_run_at": {"$lte": now_iso}}).to_list(50)
    for row in rows:
        try:
            await run_organic_growth_agent_cycle(row["user_id"], row["company_id"], force=False)
        except Exception as e:
            logger.error(f"run_all_organic_growth_agents error {row.get('_id')}: {e}")


@router.get("/marketing/organic-agent")
async def get_organic_growth_agent(user: dict = Depends(premium_user)):
    uid = user["id"]
    cid = await active_company_id(uid)
    return await _panel_payload(uid, cid)


@router.post("/marketing/organic-agent/strategy")
async def create_organic_growth_strategy(inp: OrganicStrategyIn, user: dict = Depends(premium_user)):
    uid = user["id"]
    cid = await active_company_id(uid)
    if not cid:
        raise HTTPException(400, "Sem empresa ativa.")
    _, site_analysis, alignment, strategy = await build_strategy(uid, cid, inp.objective, inp.domain)
    now_iso = _now_iso()
    existing = await db.marketing_organic_agents.find_one({"user_id": uid, "company_id": cid}, {"_id": 1, "created_at": 1})
    doc = {
        "user_id": uid,
        "company_id": cid,
        "domain": _normalize_domain(inp.domain),
        "objective": _short(inp.objective, "Gerar crescimento orgânico com foco em leads qualificados e conversão."),
        "status": "awaiting_approval",
        "strategy_approved": False,
        "autonomous_mode": False,
        "site_analysis": site_analysis,
        "director_alignment": alignment,
        "strategy": strategy,
        "metrics": await _metrics_snapshot(uid, cid),
        "blockers": [],
        "last_analysis_at": now_iso,
        "last_run_at": None,
        "next_run_at": now_iso,
        "updated_at": now_iso,
        "created_at": existing.get("created_at") if existing else now_iso,
    }
    await db.marketing_organic_agents.update_one({"user_id": uid, "company_id": cid}, {"$set": doc, "$setOnInsert": {"_id": str(uuid.uuid4())}}, upsert=True)
    return await _panel_payload(uid, cid)


@router.post("/marketing/organic-agent/approve")
async def approve_organic_growth_strategy(user: dict = Depends(premium_user)):
    uid = user["id"]
    cid = await active_company_id(uid)
    agent = await db.marketing_organic_agents.find_one({"user_id": uid, "company_id": cid})
    if not agent:
        raise HTTPException(404, "Crie primeiro a estratégia inicial do Growth Agent.")
    now_iso = _now_iso()
    await db.marketing_organic_agents.update_one(
        {"_id": agent["_id"]},
        {"$set": {"status": "running", "strategy_approved": True, "autonomous_mode": True, "approved_at": now_iso, "next_run_at": now_iso, "updated_at": now_iso}},
    )
    await run_organic_growth_agent_cycle(uid, cid, force=True, fast_mode=True)
    return await _panel_payload(uid, cid)


@router.post("/marketing/organic-agent/pause")
async def pause_organic_growth_agent(user: dict = Depends(premium_user)):
    uid = user["id"]
    cid = await active_company_id(uid)
    await db.marketing_organic_agents.update_one(
        {"user_id": uid, "company_id": cid},
        {"$set": {"status": "paused", "updated_at": _now_iso()}},
    )
    return await _panel_payload(uid, cid)


@router.post("/marketing/organic-agent/resume")
async def resume_organic_growth_agent(user: dict = Depends(premium_user)):
    uid = user["id"]
    cid = await active_company_id(uid)
    agent = await db.marketing_organic_agents.find_one({"user_id": uid, "company_id": cid})
    if not agent:
        raise HTTPException(404, "Growth Agent não encontrado.")
    now_iso = _now_iso()
    await db.marketing_organic_agents.update_one(
        {"_id": agent["_id"]},
        {"$set": {"status": "running", "autonomous_mode": True, "next_run_at": now_iso, "updated_at": now_iso}},
    )
    await run_organic_growth_agent_cycle(uid, cid, force=True, fast_mode=True)
    return await _panel_payload(uid, cid)


@router.post("/marketing/organic-agent/reanalyze")
async def reanalyze_organic_growth_agent(user: dict = Depends(premium_user)):
    uid = user["id"]
    cid = await active_company_id(uid)
    agent = await db.marketing_organic_agents.find_one({"user_id": uid, "company_id": cid})
    if not agent:
        raise HTTPException(404, "Growth Agent não encontrado.")
    _, site_analysis, alignment, strategy = await build_strategy_fast(uid, cid, agent.get("objective") or "", agent.get("domain") or "", refresh_site=True)
    now_iso = _now_iso()
    await db.marketing_organic_agents.update_one(
        {"_id": agent["_id"]},
        {"$set": {"site_analysis": site_analysis, "director_alignment": alignment, "strategy": strategy, "last_analysis_at": now_iso, "next_run_at": now_iso, "updated_at": now_iso}},
    )
    if agent.get("strategy_approved"):
        await run_organic_growth_agent_cycle(uid, cid, force=True, fast_mode=True)
    return await _panel_payload(uid, cid)


@router.post("/marketing/organic-agent/objective")
async def update_organic_growth_objective(inp: OrganicObjectiveIn, user: dict = Depends(premium_user)):
    uid = user["id"]
    cid = await active_company_id(uid)
    agent = await db.marketing_organic_agents.find_one({"user_id": uid, "company_id": cid})
    if not agent:
        raise HTTPException(404, "Growth Agent não encontrado.")
    _, site_analysis, alignment, strategy = await build_strategy_fast(
        uid,
        cid,
        inp.objective,
        agent.get("domain") or "",
        refresh_site=False,
        current_site=agent.get("site_analysis") or {},
    )
    now_iso = _now_iso()
    await db.marketing_organic_agents.update_one(
        {"_id": agent["_id"]},
        {"$set": {
            "objective": _short(inp.objective, agent.get("objective") or ""),
            "site_analysis": site_analysis,
            "director_alignment": alignment,
            "strategy": strategy,
            "last_analysis_at": now_iso,
            "next_run_at": now_iso,
            "updated_at": now_iso,
        }},
    )
    if agent.get("strategy_approved"):
        await run_organic_growth_agent_cycle(uid, cid, force=True, fast_mode=True)
    return await _panel_payload(uid, cid)