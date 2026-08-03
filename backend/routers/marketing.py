"""Diretor de Marketing — gera identidade de marca, conteúdos (Posts/Stories/Reels) e calendário editorial.
Modo rascunho/exportar (sem publicação real; integrações sociais chegam na Fase 4)."""
import base64
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from core import *

router = APIRouter()


async def _ctx(uid: str):
    company = await resolve_company(uid) or {}
    prof = company.get("profile", {}) or {}
    return {
        "name": company.get("name") or "A empresa",
        "sector": company.get("sector") or prof.get("sector") or "Geral",
        "region": company.get("region", "PT"),
        "business_model": prof.get("business_model", ""),
    }


def _serialize(doc):
    if not doc:
        return None
    doc = dict(doc); doc.pop("_id", None); doc.pop("user_id", None); doc.pop("company_id", None)
    return doc


@router.get("/marketing/content")
async def get_content(user: dict = Depends(premium_user)):
    uid = user["id"]; cid = await active_company_id(uid)
    doc = await db.marketing_content.find_one({"user_id": uid, "company_id": cid})
    return {"content": _serialize(doc)}


@router.post("/marketing/generate")
async def generate_content(user: dict = Depends(premium_user)):
    uid = user["id"]; cid = await active_company_id(uid)
    c = await _ctx(uid)
    system = ("És o Diretor de Marketing (CMO) de um conselho executivo digital para PMEs. Crias uma linha de "
              "conteúdos coerente com a marca e o setor, orientada a resultados. Português europeu.")
    prompt = (
        f"Empresa: {c['name']} · Setor: {c['sector']} · Região: {c['region']} · Modelo: {c['business_model'] or 'n/d'}.\n"
        "Cria um plano de conteúdos para 1 semana. Devolve APENAS JSON no formato: "
        '{"brand":{"tom":str,"pilares":[str]},'
        '"posts":[{"formato":str,"titulo":str,"legenda":str,"hashtags":[str],"cta":str,"dia":str}],'
        '"calendario":[{"dia":str,"formato":str,"tema":str}]}. '
        '"formato" ∈ {Post, Story, Reel}. Gera 6 peças variadas (mistura Post/Story/Reel) com legenda pronta a publicar '
        'e 4-6 hashtags relevantes ao setor e região. "calendario": 7 dias (segunda a domingo) com formato e tema. '
        "Conteúdos específicos ao setor, nunca genéricos."
    )
    content = await ai_json(system, prompt) or {}
    now_iso = datetime.now(timezone.utc).isoformat()
    doc = {"user_id": uid, "company_id": cid, "content": content, "updated_at": now_iso}
    await db.marketing_content.update_one({"user_id": uid, "company_id": cid}, {"$set": doc}, upsert=True)
    return {"content": {"content": content, "updated_at": now_iso}}


class ImageIn(BaseModel):
    index: int


@router.post("/marketing/image")
async def gen_post_image(inp: ImageIn, user: dict = Depends(premium_user)):
    """Gera (sob pedido) a imagem de UM post, com o logo da empresa aplicado, e guarda-a (cache)."""
    uid = user["id"]; cid = await active_company_id(uid)
    doc = await db.marketing_content.find_one({"user_id": uid, "company_id": cid})
    if not doc or not doc.get("content"):
        raise HTTPException(404, "Gere os conteúdos primeiro.")
    posts = doc["content"].get("posts") or []
    if inp.index < 0 or inp.index >= len(posts):
        raise HTTPException(404, "Post não encontrado.")
    p = posts[inp.index]
    c = await _ctx(uid)
    brand = doc["content"].get("brand") or {}
    prompt = (f"Cena visual conceptual para uma publicação de marketing de '{c['name']}' "
              f"(setor: {c['sector']}). Ideia a transmitir: {p.get('titulo', '')}. "
              f"Estilo/tom visual: {brand.get('tom', 'profissional e moderno')}.")
    img = await generate_marketing_image(prompt)
    logo = await db.brand_assets.find_one({"user_id": uid, "company_id": cid})
    if logo and logo.get("logo_data"):
        try:
            img = composite_logo(img, base64.b64decode(logo["logo_data"]))
        except Exception as e:
            logger.error(f"logo composite (marketing): {e}")
    url = await store_public_media(uid, img)
    posts[inp.index]["image_url"] = url
    await db.marketing_content.update_one({"user_id": uid, "company_id": cid}, {"$set": {"content.posts": posts}})
    return {"image_url": url}
