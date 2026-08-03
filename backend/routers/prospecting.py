"""Captação — Campanhas Segmentadas de Prospeção (Google Places API) + atualização contínua (delta).
Minera empresas reais por segmento e região, extrai email best-effort do website, deduplica e gera proposta por IA."""
import os, re, asyncio, csv, io
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
from core import *

router = APIRouter()

CAMPAIGNS = {
    "contratos_mensais": {"label": "Contratos Mensais", "targets": ["condomínios", "escritórios", "ginásios"],
                          "hint": "Clientes recorrentes com necessidade de manutenção elétrica contínua."},
    "grandes_obras": {"label": "Grandes Obras", "targets": ["construtoras", "empreiteiras", "arquitetos"],
                      "hint": "Projetos de grande dimensão e instalações elétricas de obra."},
    "reparos": {"label": "Pequenos Reparos / Manutenção Rápida", "targets": ["lojas", "farmácias", "comércio local"],
                "hint": "Serviços rápidos e avulsos de manutenção elétrica no comércio local."},
}

GOOGLE_URL = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = ",".join([
    "places.id", "places.displayName", "places.formattedAddress", "places.nationalPhoneNumber",
    "places.internationalPhoneNumber", "places.websiteUri", "places.types", "places.primaryTypeDisplayName",
])
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")


def _key():
    return os.environ.get("GOOGLE_PLACES_API_KEY", "")


def _now():
    return datetime.now(timezone.utc).isoformat()


async def _places_search(keyword: str, region: str, api_key: str):
    body = {"textQuery": f"{keyword} in {region}", "languageCode": "pt-PT", "regionCode": "PT", "pageSize": 20}
    headers = {"Content-Type": "application/json", "X-Goog-Api-Key": api_key, "X-Goog-FieldMask": FIELD_MASK}
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(GOOGLE_URL, json=body, headers=headers)
    if r.status_code >= 400:
        try:
            err = r.json().get("error", {}).get("message", r.text)
        except Exception:
            err = r.text
        raise HTTPException(400, f"Google Places: {err}")
    return r.json().get("places", [])


async def _extract_email(website: Optional[str]) -> Optional[str]:
    if not website:
        return None
    try:
        async with httpx.AsyncClient(timeout=6, follow_redirects=True,
                                     headers={"User-Agent": "Mozilla/5.0"}) as c:
            r = await c.get(website)
        for e in EMAIL_RE.findall(r.text or ""):
            el = e.lower()
            if not el.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")) and "example" not in el and "@sentry" not in el:
                return e
    except Exception:
        return None
    return None


def _ser(d):
    return {"id": str(d["_id"]), "name": d.get("name"), "segment": d.get("segment"), "email": d.get("email"),
            "phone": d.get("phone"), "website": d.get("website"), "address": d.get("address"),
            "campaign": d.get("campaign"), "contacted": bool(d.get("contacted")),
            "sent_to_crm": bool(d.get("sent_to_crm"))}


async def _mine_and_store(uid, cid, campaign, region):
    api_key = _key()
    if not api_key:
        raise HTTPException(400, "Busca por empresas ainda não configurada (falta a chave Google Places API).")
    targets = CAMPAIGNS[campaign]["targets"]
    candidates = {}
    for kw in targets:
        for p in await _places_search(kw, region, api_key):
            pid = p.get("id") or ((p.get("displayName") or {}).get("text", "") + (p.get("formattedAddress") or ""))
            if pid and pid not in candidates:
                candidates[pid] = (p, kw)
    new_items = []
    for pid, (p, kw) in candidates.items():
        if await db.prospects.find_one({"user_id": uid, "company_id": cid, "place_id": pid}):
            continue
        new_items.append((pid, p, kw))
    sem = asyncio.Semaphore(10)

    async def _ge(w):
        async with sem:
            return await _extract_email(w)
    emails = await asyncio.gather(*[_ge(p.get("websiteUri")) for _, p, _ in new_items]) if new_items else []
    docs = []
    for (pid, p, kw), email in zip(new_items, emails):
        docs.append({
            "user_id": uid, "company_id": cid, "campaign": campaign, "region": region, "place_id": pid,
            "name": (p.get("displayName") or {}).get("text"),
            "segment": (p.get("primaryTypeDisplayName") or {}).get("text") or kw,
            "email": email, "phone": p.get("nationalPhoneNumber") or p.get("internationalPhoneNumber"),
            "website": p.get("websiteUri"), "address": p.get("formattedAddress"),
            "contacted": False, "created_at": _now()})
    if docs:
        await db.prospects.insert_many(docs)
    allp = await db.prospects.find({"user_id": uid, "company_id": cid, "campaign": campaign}).sort("created_at", -1).to_list(500)
    return len(docs), [_ser(x) for x in allp]


@router.get("/prospecting/campaigns")
async def get_campaigns(user: dict = Depends(premium_user)):
    return {"configured": bool(_key()),
            "campaigns": [{"key": k, "label": v["label"], "targets": v["targets"], "hint": v["hint"]}
                          for k, v in CAMPAIGNS.items()]}


class SearchIn(BaseModel):
    campaign: str
    region: str


@router.post("/prospecting/search")
async def search(inp: SearchIn, user: dict = Depends(premium_user)):
    if inp.campaign not in CAMPAIGNS:
        raise HTTPException(400, "Campanha inválida.")
    if not (inp.region or "").strip():
        raise HTTPException(400, "Indique a região.")
    uid = user["id"]; cid = await active_company_id(uid)
    added, prospects = await _mine_and_store(uid, cid, inp.campaign, inp.region.strip())
    return {"added": added, "prospects": prospects}


@router.post("/prospecting/update")
async def update(inp: SearchIn, user: dict = Depends(premium_user)):
    """Atualizar Clientes (delta): procura novas empresas e adiciona só as que ainda não existem."""
    if inp.campaign not in CAMPAIGNS:
        raise HTTPException(400, "Campanha inválida.")
    uid = user["id"]; cid = await active_company_id(uid)
    added, prospects = await _mine_and_store(uid, cid, inp.campaign, inp.region.strip())
    return {"added": added, "prospects": prospects}


@router.get("/prospecting/list")
async def list_prospects(campaign: str, user: dict = Depends(premium_user)):
    uid = user["id"]; cid = await active_company_id(uid)
    allp = await db.prospects.find({"user_id": uid, "company_id": cid, "campaign": campaign}).sort("created_at", -1).to_list(500)
    return {"prospects": [_ser(x) for x in allp]}


@router.get("/prospecting/export")
async def export_csv(campaign: str, user: dict = Depends(premium_user)):
    uid = user["id"]; cid = await active_company_id(uid)
    allp = await db.prospects.find({"user_id": uid, "company_id": cid, "campaign": campaign}).sort("created_at", -1).to_list(1000)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Nome da Empresa", "Segmento", "E-mail", "Telefone", "Website", "Endereço"])
    for d in allp:
        w.writerow([d.get("name") or "", d.get("segment") or "", d.get("email") or "",
                    d.get("phone") or "", d.get("website") or "", d.get("address") or ""])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename=captacao-{campaign}.csv"})


class MsgIn(BaseModel):
    campaign: str
    prospect_id: Optional[str] = None


@router.post("/prospecting/message")
async def message(inp: MsgIn, user: dict = Depends(premium_user)):
    if inp.campaign not in CAMPAIGNS:
        raise HTTPException(400, "Campanha inválida.")
    uid = user["id"]; cid = await active_company_id(uid)
    company = await resolve_company(uid) or {}
    camp = CAMPAIGNS[inp.campaign]
    target = None
    if inp.prospect_id:
        p = await db.prospects.find_one({"_id": ObjectId(inp.prospect_id), "user_id": uid})
        if p:
            target = f"Empresa-alvo: {p.get('name')} ({p.get('segment')}), em {p.get('address') or 'n/d'}."
    system = ("És o Diretor Comercial da empresa. Escreves propostas de prospeção B2B curtas, persuasivas e "
              "profissionais em português europeu, orientadas ao segmento indicado.")
    prompt = (f"A minha empresa: {company.get('name') or 'a nossa empresa'} (setor: {company.get('sector') or 'eletricidade'}).\n"
              f"Campanha: {camp['label']} — {camp['hint']} Segmentos-alvo: {', '.join(camp['targets'])}.\n"
              f"{target or ''}\n"
              "Escreve uma PROPOSTA de primeiro contacto (email) para este segmento. "
              'Devolve APENAS JSON: {"assunto":str,"corpo":str}. '
              "Corpo curto (2-3 parágrafos), com proposta de valor específica ao segmento e um CTA claro para reunião/orçamento.")
    draft = await ai_json(system, prompt) or {}
    return {"message": draft, "campaign": inp.campaign}


class CampIn(BaseModel):
    campaign: str


@router.post("/prospecting/to-crm")
async def to_crm(inp: CampIn, user: dict = Depends(premium_user)):
    """Envia as empresas encontradas (ainda não enviadas) para o pipeline do CRM, com lead score."""
    if inp.campaign not in CAMPAIGNS:
        raise HTTPException(400, "Campanha inválida.")
    from routers.crm import compute_lead_score
    uid = user["id"]; cid = await active_company_id(uid)
    icp = await db.crm_icp.find_one({"user_id": uid, "company_id": cid}) or {}
    snap = await build_snapshot(uid)
    ar = (snap.get("valuation") or {}).get("annual_revenue")
    mrev = (ar / 12.0) if isinstance(ar, (int, float)) and ar else None
    prospects = await db.prospects.find({"user_id": uid, "company_id": cid, "campaign": inp.campaign,
                                         "sent_to_crm": {"$ne": True}}).to_list(500)
    added = 0
    for p in prospects:
        lead = {"name": p.get("name"), "contact": p.get("email") or p.get("phone"),
                "sector": p.get("segment"), "region": p.get("region"), "stage": "novo", "urgency": "media",
                "source": f"Captação · {CAMPAIGNS[inp.campaign]['label']}",
                "notes": "\n".join(x for x in [p.get("address"), p.get("website")] if x)}
        lead["score"] = compute_lead_score(lead, icp, mrev)
        lead.update({"user_id": uid, "company_id": cid, "created_at": _now()})
        await db.crm_leads.insert_one(lead)
        await db.prospects.update_one({"_id": p["_id"]}, {"$set": {"sent_to_crm": True}})
        added += 1
    return {"added": added}
