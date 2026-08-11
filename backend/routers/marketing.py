"""Diretor de Marketing — planeamento contextual, workflow editorial e calendário operacional."""
import base64
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from core import (
    active_company_id,
    ai_json,
    build_snapshot,
    composite_logo,
    db,
    generate_marketing_image,
    get_erp_financial_context,
    logger,
    premium_user,
    resolve_company,
    store_public_media,
)

router = APIRouter()

WORKFLOW_STATUSES = {"draft", "approved", "scheduled"}
POST_FORMATS = ["Post", "Story", "Reel"]
WEEKDAYS_PT = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def _serialize(doc):
    if not doc:
        return None
    doc = dict(doc)
    doc.pop("_id", None)
    doc.pop("user_id", None)
    doc.pop("company_id", None)
    return doc


def _str_list(value, limit=8):
    if isinstance(value, list):
        out = []
        for item in value:
            text = str(item or "").strip()
            if text:
                out.append(text)
            if len(out) >= limit:
                break
        return out
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _short(value, fallback="n/d"):
    text = str(value or "").strip()
    return text or fallback


def _money(value, sym="€"):
    if not isinstance(value, (int, float)):
        return "n/d"
    return f"{sym}{int(round(value)):,}".replace(",", " ")


def _workflow_summary(posts):
    counts = {k: 0 for k in WORKFLOW_STATUSES}
    for post in posts or []:
        status = post.get("status") if isinstance(post, dict) else None
        if status not in counts:
            status = "draft"
        counts[status] += 1
    counts["total"] = len(posts or [])
    return counts


def apply_post_status(content: dict, post_id: str, status: str, scheduled_at: Optional[str] = None,
                      published_at: Optional[str] = None) -> bool:
    status = status if status in WORKFLOW_STATUSES else "draft"
    posts = content.get("posts") or []
    changed = False
    for post in posts:
        if post.get("id") != post_id:
            continue
        changed = True
        post["status"] = status
        if status == "draft":
            post["approved_at"] = None
            post["scheduled_at"] = None
            post["published_at"] = None
        elif status == "approved":
            post["approved_at"] = post.get("approved_at") or datetime.now(timezone.utc).isoformat()
            post["scheduled_at"] = None
            if published_at:
                post["published_at"] = published_at
        elif status == "scheduled":
            post["approved_at"] = post.get("approved_at") or datetime.now(timezone.utc).isoformat()
            post["scheduled_at"] = scheduled_at or post.get("scheduled_at")
            if published_at:
                post["published_at"] = published_at
        break
    if not changed:
        return False
    for item in (content.get("calendario") or []):
        if item.get("post_id") == post_id:
            item["status"] = status
            item["scheduled_at"] = scheduled_at if status == "scheduled" else None
    content["workflow_summary"] = _workflow_summary(posts)
    return True


def _fallback_brand(ctx: dict):
    sector = ctx.get("sector") or "Geral"
    return {
        "tom": f"Claro, confiante e útil para decisores no setor {sector.lower()}.",
        "pilares": [sector, "prova social", "educação", "bastidores"],
        "proposta_valor": f"Transformar a experiência de {sector.lower()} em confiança e oportunidade comercial.",
        "provas": ["Experiência prática", "Resultados concretos", "Linguagem simples"],
        "audiencias": [ctx.get("icp", {}).get("sector") or sector, "clientes atuais", "leads mornos"],
        "do_say": ["Mostrar processo", "Usar casos reais", "Fechar com CTA direto"],
        "avoid": ["Promessas vagas", "Jargão técnico em excesso", "Conteúdo genérico"],
    }


def _fallback_posts(ctx: dict, brand: dict):
    sector = ctx.get("sector") or "negócio"
    company = ctx.get("name") or "A empresa"
    pillars = _str_list(brand.get("pilares"), 4) or [sector, "prova social", "bastidores", "educação"]
    objectives = [
        "atrair novos leads",
        "gerar confiança",
        "educar o mercado",
        "reativar oportunidades paradas",
    ]
    posts = []
    for i in range(10):
        pillar = pillars[i % len(pillars)]
        objective = objectives[i % len(objectives)]
        fmt = POST_FORMATS[i % len(POST_FORMATS)]
        weekday = WEEKDAYS_PT[i % len(WEEKDAYS_PT)]
        title = f"{company}: {pillar.capitalize()} com foco em {objective}"
        legend = (
            f"Em {sector.lower()}, confiança gera negócio. Hoje mostramos como {company} trabalha {pillar} "
            f"para {objective}."
        )
        posts.append({
            "id": f"post-{i + 1}",
            "formato": fmt,
            "titulo": title,
            "legenda": legend,
            "hashtags": [f"#{sector.lower().replace(' ', '')}", "#ceoai", "#marketing", "#pme"],
            "cta": "Quer que adaptemos isto ao teu caso? Fala connosco.",
            "dia": weekday,
            "tema": pillar.capitalize(),
            "objetivo": objective,
            "pilar": pillar,
            "status": "draft",
            "approved_at": None,
            "scheduled_at": None,
            "published_at": None,
        })
    return posts


def _normalize_brand(raw: dict, ctx: dict):
    base = _fallback_brand(ctx)
    raw = raw if isinstance(raw, dict) else {}
    brand = {
        "tom": _short(raw.get("tom"), base["tom"]),
        "pilares": _str_list(raw.get("pilares"), 6) or base["pilares"],
        "proposta_valor": _short(raw.get("proposta_valor"), base["proposta_valor"]),
        "provas": _str_list(raw.get("provas"), 6) or base["provas"],
        "audiencias": _str_list(raw.get("audiencias"), 6) or base["audiencias"],
        "do_say": _str_list(raw.get("do_say"), 6) or base["do_say"],
        "avoid": _str_list(raw.get("avoid"), 6) or base["avoid"],
    }
    return brand


def _normalize_posts(raw_posts, brand: dict, ctx: dict):
    items = raw_posts if isinstance(raw_posts, list) else []
    out = []
    for idx, item in enumerate(items[:12]):
        item = item if isinstance(item, dict) else {}
        fmt = _short(item.get("formato"), POST_FORMATS[idx % len(POST_FORMATS)]).title()
        if fmt not in POST_FORMATS:
            fmt = POST_FORMATS[idx % len(POST_FORMATS)]
        title = _short(item.get("titulo"), f"Conteúdo {idx + 1}")
        pillar = _short(item.get("pilar"), (brand.get("pilares") or [ctx.get("sector") or "marca"])[idx % max(1, len(brand.get("pilares") or [1]))])
        objective = _short(item.get("objetivo"), "gerar confiança")
        out.append({
            "id": _short(item.get("id"), f"post-{idx + 1}"),
            "formato": fmt,
            "titulo": title,
            "legenda": _short(item.get("legenda"), f"{title} — conteúdo preparado pelo Diretor de Marketing."),
            "hashtags": _str_list(item.get("hashtags"), 6) or ["#ceoai", "#marketing", "#pme"],
            "cta": _short(item.get("cta"), "Fale connosco para dar o próximo passo."),
            "dia": _short(item.get("dia"), WEEKDAYS_PT[idx % len(WEEKDAYS_PT)]),
            "tema": _short(item.get("tema"), title),
            "objetivo": objective,
            "pilar": pillar,
            "status": "draft",
            "approved_at": None,
            "scheduled_at": None,
            "published_at": None,
        })
    return out or _fallback_posts(ctx, brand)


def _normalize_library(raw_library, posts, brand):
    lib = raw_library if isinstance(raw_library, list) else []
    out = []
    for idx, item in enumerate(lib[:8]):
        item = item if isinstance(item, dict) else {}
        formats = [fmt for fmt in _str_list(item.get("formatos"), 3) if fmt.title() in POST_FORMATS]
        out.append({
            "id": _short(item.get("id"), f"lib-{idx + 1}"),
            "titulo": _short(item.get("titulo"), f"Ângulo editorial {idx + 1}"),
            "angulo": _short(item.get("angulo"), item.get("titulo") or "Ideia de conteúdo"),
            "objetivo": _short(item.get("objetivo"), "gerar tração comercial"),
            "pilar": _short(item.get("pilar"), (brand.get("pilares") or ["marca"])[idx % max(1, len(brand.get("pilares") or [1]))]),
            "formatos": formats or [POST_FORMATS[idx % len(POST_FORMATS)]],
            "cta": _short(item.get("cta"), "Responder, pedir orçamento ou marcar reunião."),
        })
    if out:
        return out
    seen = set()
    derived = []
    for idx, post in enumerate(posts[:6]):
        key = (post.get("tema") or post.get("titulo") or f"tema-{idx}").lower()
        if key in seen:
            continue
        seen.add(key)
        derived.append({
            "id": f"lib-{len(derived) + 1}",
            "titulo": post.get("tema") or post.get("titulo"),
            "angulo": post.get("titulo") or post.get("tema"),
            "objetivo": post.get("objetivo") or "gerar confiança",
            "pilar": post.get("pilar") or "marca",
            "formatos": [post.get("formato") or "Post"],
            "cta": post.get("cta") or "Pedir orçamento ou responder à publicação.",
        })
    return derived


def _normalize_calendar(raw_calendar, posts):
    today = datetime.now(timezone.utc).date()
    raw_calendar = raw_calendar if isinstance(raw_calendar, list) else []
    out = []
    for idx in range(30):
        source = raw_calendar[idx] if idx < len(raw_calendar) and isinstance(raw_calendar[idx], dict) else {}
        post = posts[idx % len(posts)] if posts else {}
        day = today + timedelta(days=idx)
        fmt = _short(source.get("formato"), post.get("formato") or POST_FORMATS[idx % len(POST_FORMATS)]).title()
        if fmt not in POST_FORMATS:
            fmt = post.get("formato") or POST_FORMATS[idx % len(POST_FORMATS)]
        out.append({
            "dia": _short(source.get("dia"), WEEKDAYS_PT[day.weekday()]),
            "data": day.isoformat(),
            "formato": fmt,
            "tema": _short(source.get("tema"), post.get("tema") or post.get("titulo") or f"Tema {idx + 1}"),
            "objetivo": _short(source.get("objetivo"), post.get("objetivo") or "gerar consistência"),
            "pilar": _short(source.get("pilar"), post.get("pilar") or "marca"),
            "post_id": _short(source.get("post_id"), post.get("id") or None),
            "status": post.get("status") if post.get("id") == source.get("post_id") else "draft",
            "scheduled_at": None,
        })
    return out


async def _ctx(uid: str, cid: str):
    company = await resolve_company(uid, cid) or {}
    prof = company.get("profile", {}) or {}
    snap = await build_snapshot(uid)
    icp = await db.crm_icp.find_one({"user_id": uid, "company_id": cid}, {"_id": 0}) or {}
    leads = await db.crm_leads.find(
        {"user_id": uid, "company_id": cid},
        {"_id": 0, "name": 1, "stage": 1, "value": 1, "sector": 1, "urgency": 1, "source": 1, "score": 1},
    ).sort("score", -1).to_list(8)
    lead_counts = {}
    for lead in leads:
        stage = lead.get("stage") or "novo"
        lead_counts[stage] = lead_counts.get(stage, 0) + 1
    memories = await db.memories.find({"user_id": uid}, {"_id": 0, "content": 1, "category": 1}).sort("created_at", -1).to_list(8)
    erp = await get_erp_financial_context(uid, cid) or {}
    return {
        "name": company.get("name") or snap.get("company_name") or "A empresa",
        "sector": company.get("sector") or prof.get("sector") or prof.get("activity") or "Geral",
        "region": company.get("region", "PT"),
        "business_model": prof.get("business_model", ""),
        "main_goal": prof.get("main_goal", ""),
        "advantage": prof.get("advantage", ""),
        "main_worry": prof.get("main_worry", ""),
        "biggest_client_pct": prof.get("biggest_client_pct"),
        "client_recurrence": prof.get("client_recurrence", ""),
        "memories": memories,
        "icp": icp,
        "leads": leads,
        "lead_counts": lead_counts,
        "erp": erp,
        "snapshot": snap,
    }


def _prompt_context(ctx: dict):
    snap = ctx.get("snapshot") or {}
    val = snap.get("valuation") or {}
    sym = snap.get("currency_symbol", "€")
    mem_lines = "\n".join(f"- [{m.get('category', 'geral')}] {m.get('content', '')}" for m in (ctx.get("memories") or [])[:6]) or "- sem memórias registadas"
    icp = ctx.get("icp") or {}
    icp_line = (
        f"ICP: setor {icp.get('sector') or 'n/d'} · dimensão {icp.get('size') or 'n/d'} · região {icp.get('region') or 'n/d'} · "
        f"decisor {icp.get('decisor') or 'n/d'} · dor {icp.get('dor') or 'n/d'} · ticket ideal {_money(icp.get('ticket_ideal'), sym)}"
    )
    leads_line = "\n".join(
        f"- {l.get('name')} | fase {l.get('stage')} | score {l.get('score')} | valor {_money(l.get('value'), sym)} | urgência {l.get('urgency') or 'n/d'}"
        for l in (ctx.get("leads") or [])[:5]
    ) or "- sem leads no CRM"
    erp = ctx.get("erp") or {}
    erp_fixed = ", ".join(f"{c.get('name')}: {_money(c.get('amount'), sym)}" for c in (erp.get("fixed_costs") or [])[:5]) or "n/d"
    erp_line = (
        f"Fonte financeira ativa: {erp.get('source_label') or snap.get('financial_context_source') or 'sem ERP ativo'}\n"
        f"Caixa: {_money(erp.get('cash_balance', snap.get('cash_available')), sym)} · Dívida: {_money(erp.get('total_debt', snap.get('total_liabilities')), sym)} · "
        f"Faturação mensal: {_money(erp.get('monthly_revenue'), sym)} · Custos fixos: {erp_fixed}"
    )
    return (
        f"Empresa: {ctx['name']}\n"
        f"Setor: {ctx['sector']} · Região: {ctx['region']} · Modelo de negócio: {ctx.get('business_model') or 'n/d'}\n"
        f"Objetivo principal: {ctx.get('main_goal') or 'n/d'}\n"
        f"Vantagem competitiva: {ctx.get('advantage') or 'n/d'}\n"
        f"Maior preocupação: {ctx.get('main_worry') or 'n/d'}\n"
        f"Maior cliente: {ctx.get('biggest_client_pct') or 'n/d'}% · Recorrência: {ctx.get('client_recurrence') or 'n/d'}\n"
        f"Saúde: {snap.get('health', 'n/d')}/100 · Valor da empresa: {_money(snap.get('company_value'), sym)} · "
        f"Lucro anual estimado: {_money(val.get('annual_profit'), sym)}\n\n"
        f"MEMÓRIAS ÚTEIS:\n{mem_lines}\n\n"
        f"CRM E CLIENTE IDEAL:\n{icp_line}\n"
        f"Leads prioritários:\n{leads_line}\n\n"
        f"CONTEXTO FINANCEIRO/ERP:\n{erp_line}"
    )


def _brand_brain(ctx: dict, brand: dict, library: list, posts: list):
    snap = ctx.get("snapshot") or {}
    lead_counts = ctx.get("lead_counts") or {}
    priorities = []
    if (ctx.get("icp") or {}).get("dor"):
        priorities.append(f"Responder à dor central do ICP: {ctx['icp']['dor']}")
    if ctx.get("biggest_client_pct") and float(ctx.get("biggest_client_pct") or 0) >= 30:
        priorities.append("Reduzir dependência do maior cliente com prova social e novos segmentos")
    if snap.get("health") is not None and snap.get("health") < 60:
        priorities.append("Privilegiar conteúdo de conversão e caixa de curto prazo")
    if lead_counts.get("proposta") or lead_counts.get("negociacao"):
        priorities.append("Criar peças para desbloquear leads já em proposta/negociação")
    if not priorities:
        priorities.append("Manter consistência editorial e reforçar posicionamento")
    return {
        "context_sources": {
            "memories": len(ctx.get("memories") or []),
            "crm_leads": len(ctx.get("leads") or []),
            "icp_defined": bool(ctx.get("icp")),
            "erp_active": bool(ctx.get("erp")),
        },
        "prioridades": priorities,
        "angles": [item.get("angulo") for item in library[:4] if item.get("angulo")],
        "headline_focus": posts[0].get("titulo") if posts else "",
        "positioning": brand.get("proposta_valor"),
        "financial_guardrail": snap.get("financial_context_source") or "os teus dados",
    }


def _normalize_content(raw: dict, ctx: dict):
    raw = raw if isinstance(raw, dict) else {}
    brand = _normalize_brand(raw.get("brand"), ctx)
    posts = _normalize_posts(raw.get("posts"), brand, ctx)
    library = _normalize_library(raw.get("biblioteca") or raw.get("library"), posts, brand)
    calendar = _normalize_calendar(raw.get("calendario"), posts)
    content = {
        "brand": brand,
        "biblioteca": library,
        "posts": posts,
        "calendario": calendar,
    }
    content["brand_brain"] = _brand_brain(ctx, brand, library, posts)
    content["workflow_summary"] = _workflow_summary(posts)
    return content


class ImageIn(BaseModel):
    index: int


class PostStatusIn(BaseModel):
    status: str


@router.get("/marketing/content")
async def get_content(user: dict = Depends(premium_user)):
    uid = user["id"]
    cid = await active_company_id(uid)
    doc = await db.marketing_content.find_one({"user_id": uid, "company_id": cid})
    return {"content": _serialize(doc)}


@router.post("/marketing/generate")
async def generate_content(user: dict = Depends(premium_user)):
    uid = user["id"]
    cid = await active_company_id(uid)
    ctx = await _ctx(uid, cid)
    system = (
        "És o Diretor de Marketing (CMO) executor de um conselho executivo digital para PMEs. "
        "Crias conteúdo com contexto real de CRM, memórias estratégicas e situação financeira atual. "
        "Tens de ser específico ao setor, orientado a receita e coerente com a marca. Português europeu."
    )
    prompt = (
        f"Usa APENAS este contexto real da empresa:\n{_prompt_context(ctx)}\n\n"
        "Cria um plano editorial operativo. Devolve APENAS JSON válido com esta estrutura: "
        '{"brand":{"tom":str,"pilares":[str],"proposta_valor":str,"provas":[str],"audiencias":[str],"do_say":[str],"avoid":[str]},'
        '"biblioteca":[{"id":str,"titulo":str,"angulo":str,"objetivo":str,"pilar":str,"formatos":[str],"cta":str}],'
        '"posts":[{"id":str,"formato":str,"titulo":str,"legenda":str,"hashtags":[str],"cta":str,"dia":str,"tema":str,"objetivo":str,"pilar":str}],'
        '"calendario":[{"dia":str,"formato":str,"tema":str,"objetivo":str,"pilar":str,"post_id":str|null}]}. '
        'Regras: 1) "formato" ∈ {Post, Story, Reel}. 2) Gera 10 a 12 posts reutilizáveis. 3) "biblioteca" = 6 a 8 ângulos editoriais. '
        '4) "calendario" = exatamente 30 entradas, com distribuição realista ao longo de 30 dias. 5) Usa as dores do ICP, o estado das oportunidades do CRM '
        'e a pressão financeira atual para escolher temas e CTAs. 6) Nunca escrever conteúdo genérico; falar como esta empresa, neste setor, nesta região.'
    )
    ai_content = await ai_json(system, prompt) or {}
    content = _normalize_content(ai_content, ctx)
    now_iso = datetime.now(timezone.utc).isoformat()
    doc = {"user_id": uid, "company_id": cid, "content": content, "updated_at": now_iso}
    await db.marketing_content.update_one({"user_id": uid, "company_id": cid}, {"$set": doc}, upsert=True)
    return {"content": {"content": content, "updated_at": now_iso}}


@router.post("/marketing/posts/{post_id}/status")
async def update_post_status(post_id: str, inp: PostStatusIn, user: dict = Depends(premium_user)):
    uid = user["id"]
    cid = await active_company_id(uid)
    doc = await db.marketing_content.find_one({"user_id": uid, "company_id": cid})
    if not doc or not doc.get("content"):
        raise HTTPException(404, "Gere os conteúdos primeiro.")
    content = doc.get("content") or {}
    if not apply_post_status(content, post_id, inp.status):
        raise HTTPException(404, "Post não encontrado.")
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.marketing_content.update_one(
        {"user_id": uid, "company_id": cid},
        {"$set": {"content": content, "updated_at": now_iso}},
    )
    post = next((p for p in (content.get("posts") or []) if p.get("id") == post_id), None)
    return {"ok": True, "post": post, "content": content, "updated_at": now_iso}


@router.post("/marketing/image")
async def gen_post_image(inp: ImageIn, user: dict = Depends(premium_user)):
    """Gera (sob pedido) a imagem de UM post, com o logo da empresa aplicado, e guarda-a (cache)."""
    uid = user["id"]
    cid = await active_company_id(uid)
    doc = await db.marketing_content.find_one({"user_id": uid, "company_id": cid})
    if not doc or not doc.get("content"):
        raise HTTPException(404, "Gere os conteúdos primeiro.")
    content = doc.get("content") or {}
    posts = content.get("posts") or []
    if inp.index < 0 or inp.index >= len(posts):
        raise HTTPException(404, "Post não encontrado.")
    post = posts[inp.index]
    ctx = await _ctx(uid, cid)
    brand = content.get("brand") or {}
    prompt = (
        f"Cena visual conceptual para uma publicação de marketing de '{ctx['name']}' "
        f"(setor: {ctx['sector']}, região: {ctx['region']}). Ideia: {post.get('titulo', '')}. "
        f"Tema: {post.get('tema', '')}. Tom visual: {brand.get('tom', 'profissional e moderno')}."
    )
    img = await generate_marketing_image(prompt)
    logo = await db.brand_assets.find_one({"user_id": uid, "company_id": cid})
    if logo and logo.get("logo_data"):
        try:
            img = composite_logo(img, base64.b64decode(logo["logo_data"]))
        except Exception as e:
            logger.error(f"logo composite (marketing): {e}")
    url = await store_public_media(uid, img)
    posts[inp.index]["image_url"] = url
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.marketing_content.update_one(
        {"user_id": uid, "company_id": cid},
        {"$set": {"content": content, "updated_at": now_iso}},
    )
    return {"image_url": url}
