"""Fase 4 — Publicação automática nas redes (Instagram + Facebook via Meta Graph API).
Agora com isolamento por empresa e sincronização com o workflow editorial do Marketing."""
import os, base64, uuid, hmac, hashlib, secrets
from datetime import datetime, timezone
from urllib.parse import urlencode, quote
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, File
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import httpx
from core import (
    active_company_id,
    composite_logo,
    db,
    generate_marketing_image,
    logger,
    prepare_logo,
    premium_user,
)
from routers.marketing import apply_post_status

router = APIRouter()

GRAPH_VER = os.environ.get("META_GRAPH_VERSION", "v25.0")
SCOPES = ["instagram_basic", "instagram_content_publish", "pages_show_list",
          "pages_read_engagement", "pages_manage_posts", "business_management"]


def _cfg():
    return os.environ.get("META_APP_ID", ""), os.environ.get("META_APP_SECRET", "")


def _base():
    return (os.environ.get("FRONTEND_URL", "") or "").rstrip("/")


def _redirect_uri():
    return f"{_base()}/api/social/callback"


def _graph(path: str) -> str:
    return f"https://graph.facebook.com/{GRAPH_VER}/{path.lstrip('/')}"


def _proof(token: str) -> str:
    _, sec = _cfg()
    return hmac.new(sec.encode(), token.encode(), hashlib.sha256).hexdigest()


async def _graph_req(method: str, url: str, params: dict, token: str) -> dict:
    params = {**params, "access_token": token, "appsecret_proof": _proof(token)}
    async with httpx.AsyncClient(timeout=90) as client:
        r = await client.request(method, url, params=params)
    try:
        data = r.json()
    except Exception:
        raise HTTPException(502, {"meta_error": r.text[:400]})
    if r.is_error or "error" in data:
        raise HTTPException(502, {"meta_error": data.get("error", data)})
    return data


async def _find_connection(uid: str, cid: Optional[str]):
    if cid:
        conn = await db.social_connections.find_one({"user_id": uid, "company_id": cid})
        if conn:
            return conn
    legacy = await db.social_connections.find_one({"user_id": uid, "company_id": {"$exists": False}})
    if legacy and cid:
        await db.social_connections.update_one(
            {"_id": legacy["_id"]},
            {"$set": {"company_id": cid, "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        legacy["company_id"] = cid
    return legacy


async def _migrate_legacy_jobs(uid: str, cid: Optional[str]):
    if not cid:
        return
    await db.social_jobs.update_many(
        {"user_id": uid, "company_id": {"$exists": False}},
        {"$set": {"company_id": cid}},
    )


async def _sync_marketing_post(uid: str, cid: Optional[str], post_id: Optional[str], status: str,
                               scheduled_at: Optional[str] = None, published_at: Optional[str] = None):
    if not (uid and cid and post_id):
        return
    doc = await db.marketing_content.find_one({"user_id": uid, "company_id": cid})
    if not doc or not doc.get("content"):
        return
    content = doc.get("content") or {}
    if not apply_post_status(content, post_id, status, scheduled_at=scheduled_at, published_at=published_at):
        return
    await db.marketing_content.update_one(
        {"user_id": uid, "company_id": cid},
        {"$set": {"content": content, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )


# ---------------------------------------------------------------- media pública (para o Instagram buscar a imagem)
async def _store_public_image(uid: str, cid: Optional[str], data: bytes, ct: str = "image/png") -> str:
    mid = str(uuid.uuid4())
    await db.social_media.insert_one({"_id": mid, "user_id": uid, "company_id": cid,
                                      "data": base64.b64encode(data).decode(), "content_type": ct,
                                      "created_at": datetime.now(timezone.utc).isoformat()})
    return f"{_base()}/api/public/media/{mid}"


@router.get("/public/media/{mid}")
async def public_media(mid: str):
    doc = await db.social_media.find_one({"_id": mid})
    if not doc:
        raise HTTPException(404, "não encontrado")
    return Response(content=base64.b64decode(doc["data"]), media_type=doc.get("content_type", "image/png"))


# ---------------------------------------------------------------- estado / ligação
@router.get("/social/status")
async def social_status(user: dict = Depends(premium_user)):
    aid, sec = _cfg()
    cid = await active_company_id(user["id"])
    conn = await _find_connection(user["id"], cid)
    return {
        "configured": bool(aid and sec),
        "redirect_uri": _redirect_uri(),
        "connected": bool(conn),
        "page_name": conn.get("page_name") if conn else None,
        "ig_username": conn.get("ig_username") if conn else None,
        "has_instagram": bool(conn and conn.get("ig_user_id")),
    }


@router.get("/social/connect")
async def social_connect(user: dict = Depends(premium_user)):
    aid, sec = _cfg()
    if not (aid and sec):
        raise HTTPException(400, "Integração Meta ainda não configurada (falta App ID/App Secret).")
    cid = await active_company_id(user["id"])
    state = secrets.token_urlsafe(24)
    await db.social_oauth_states.insert_one({"_id": state, "user_id": user["id"], "company_id": cid,
                                             "created_at": datetime.now(timezone.utc).isoformat()})
    q = urlencode({"client_id": aid, "redirect_uri": _redirect_uri(), "state": state,
                   "scope": ",".join(SCOPES), "response_type": "code"})
    return {"auth_url": f"https://www.facebook.com/{GRAPH_VER}/dialog/oauth?{q}"}


@router.get("/social/callback")
async def social_callback(code: Optional[str] = None, state: Optional[str] = None,
                          error: Optional[str] = None, error_description: Optional[str] = None):
    base = _base()
    if error:
        return RedirectResponse(f"{base}/marketing?social_error={quote(error_description or error)}")
    st = await db.social_oauth_states.find_one_and_delete({"_id": state or ""})
    if not st or not code:
        return RedirectResponse(f"{base}/marketing?social_error=estado_invalido")
    uid = st["user_id"]
    cid = st.get("company_id") or await active_company_id(uid)
    aid, sec = _cfg()
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            short = (await client.get(_graph("oauth/access_token"), params={
                "client_id": aid, "client_secret": sec, "redirect_uri": _redirect_uri(), "code": code})).json()
            if "access_token" not in short:
                logger.error(f"social oauth short: {short}")
                return RedirectResponse(f"{base}/marketing?social_error=troca_codigo")
            user_short = short["access_token"]
            longt = (await client.get(_graph("oauth/access_token"), params={
                "grant_type": "fb_exchange_token", "client_id": aid, "client_secret": sec,
                "fb_exchange_token": user_short})).json()
            user_token = longt.get("access_token", user_short)
            pages = (await client.get(_graph("me/accounts"), params={
                "access_token": user_token, "appsecret_proof": _proof(user_token),
                "fields": "id,name,access_token,tasks,instagram_business_account"})).json()
        data = pages.get("data", [])
        if not data:
            return RedirectResponse(f"{base}/marketing?social_error=sem_pagina")
        chosen = next((p for p in data if p.get("instagram_business_account")), data[0])
        ig_id = (chosen.get("instagram_business_account") or {}).get("id")
        ig_username = None
        if ig_id:
            igd = await _graph_req("GET", _graph(ig_id), {"fields": "username"}, chosen["access_token"])
            ig_username = igd.get("username")
        await db.social_connections.update_one({"user_id": uid, "company_id": cid}, {"$set": {
            "user_id": uid, "company_id": cid, "page_id": chosen["id"], "page_name": chosen.get("name"),
            "ig_user_id": ig_id, "ig_username": ig_username,
            "page_token": chosen["access_token"], "user_token": user_token,
            "updated_at": datetime.now(timezone.utc).isoformat()}}, upsert=True)
        return RedirectResponse(f"{base}/marketing?connected=1")
    except Exception as e:
        logger.error(f"social oauth callback: {e}")
        return RedirectResponse(f"{base}/marketing?social_error=falha_oauth")


@router.post("/social/disconnect")
async def social_disconnect(user: dict = Depends(premium_user)):
    cid = await active_company_id(user["id"])
    await db.social_connections.delete_one({"user_id": user["id"], "company_id": cid})
    return {"ok": True}


# ---------------------------------------------------------------- publicação
class PublishIn(BaseModel):
    caption: str = ""
    image_prompt: Optional[str] = None
    generate_image: bool = True
    image_url: Optional[str] = None
    post_id: Optional[str] = None
    instagram: bool = True
    facebook: bool = True


class ScheduleIn(PublishIn):
    run_at: str                             # ISO 8601 UTC


async def _publish_core(uid: str, cid: Optional[str], payload: dict) -> dict:
    conn = await _find_connection(uid, cid)
    if not conn:
        raise HTTPException(400, "As redes ainda não estão ligadas.")
    caption = payload.get("caption") or ""
    image_url = payload.get("image_url")
    want_img = payload.get("generate_image", True)
    do_ig = payload.get("instagram", True)
    do_fb = payload.get("facebook", True)
    post_id = payload.get("post_id")
    if not image_url and want_img and (do_ig or do_fb):
        prompt = payload.get("image_prompt") or caption[:220] or "Conteúdo de marketing profissional"
        img = await generate_marketing_image(prompt)
        logo = await db.brand_assets.find_one({"user_id": uid, "company_id": cid})
        if logo and logo.get("logo_data"):
            try:
                img = composite_logo(img, base64.b64decode(logo["logo_data"]))
            except Exception as e:
                logger.error(f"logo composite falhou: {e}")
        image_url = await _store_public_image(uid, cid, img)
    results = {}
    if do_ig:
        ig = conn.get("ig_user_id")
        if not ig:
            results["instagram"] = {"error": "Sem conta Instagram profissional ligada à Página."}
        elif not image_url:
            results["instagram"] = {"error": "O Instagram exige uma imagem."}
        else:
            token = conn["page_token"]
            cont = await _graph_req("POST", _graph(f"{ig}/media"), {"image_url": image_url, "caption": caption}, token)
            pub = await _graph_req("POST", _graph(f"{ig}/media_publish"), {"creation_id": cont["id"]}, token)
            results["instagram"] = {"ok": True, "id": pub.get("id")}
    if do_fb:
        pid = conn["page_id"]; token = conn["page_token"]
        if image_url:
            fb = await _graph_req("POST", _graph(f"{pid}/photos"), {"url": image_url, "caption": caption}, token)
        else:
            fb = await _graph_req("POST", _graph(f"{pid}/feed"), {"message": caption}, token)
        results["facebook"] = {"ok": True, "id": fb.get("id") or fb.get("post_id")}
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.social_posts.insert_one({
        "user_id": uid,
        "company_id": cid,
        "post_id": post_id,
        "caption": caption,
        "image_url": image_url,
        "results": results,
        "created_at": now_iso,
    })
    if post_id:
        await _sync_marketing_post(uid, cid, post_id, "approved", published_at=now_iso)
    return results


@router.post("/social/publish")
async def social_publish(inp: PublishIn, user: dict = Depends(premium_user)):
    cid = await active_company_id(user["id"])
    res = await _publish_core(user["id"], cid, inp.model_dump())
    return {"ok": True, "results": res}


@router.post("/social/schedule")
async def social_schedule(inp: ScheduleIn, user: dict = Depends(premium_user)):
    cid = await active_company_id(user["id"])
    conn = await _find_connection(user["id"], cid)
    if not conn:
        raise HTTPException(400, "As redes ainda não estão ligadas.")
    d = inp.model_dump(); run_at = d.pop("run_at")
    job = {"_id": str(uuid.uuid4()), "user_id": user["id"], "company_id": cid, "payload": d, "run_at": run_at,
           "status": "queued", "created_at": datetime.now(timezone.utc).isoformat()}
    await db.social_jobs.insert_one(job)
    if d.get("post_id"):
        await _sync_marketing_post(user["id"], cid, d.get("post_id"), "scheduled", scheduled_at=run_at)
    return {"ok": True, "id": job["_id"]}


@router.get("/social/jobs")
async def social_jobs(user: dict = Depends(premium_user)):
    cid = await active_company_id(user["id"])
    await _migrate_legacy_jobs(user["id"], cid)
    jobs = await db.social_jobs.find({"user_id": user["id"], "company_id": cid}).sort("run_at", 1).to_list(100)
    out = [{"id": j["_id"], "run_at": j.get("run_at"), "status": j.get("status"),
            "caption": ((j.get("payload") or {}).get("caption") or "")[:80],
            "post_id": (j.get("payload") or {}).get("post_id"),
            "error": j.get("error")} for j in jobs]
    return {"jobs": out}


@router.delete("/social/jobs/{jid}")
async def del_job(jid: str, user: dict = Depends(premium_user)):
    cid = await active_company_id(user["id"])
    job = await db.social_jobs.find_one({"_id": jid, "user_id": user["id"], "company_id": cid})
    await db.social_jobs.delete_one({"_id": jid, "user_id": user["id"], "company_id": cid})
    post_id = ((job or {}).get("payload") or {}).get("post_id")
    if post_id:
        await _sync_marketing_post(user["id"], cid, post_id, "approved")
    return {"ok": True}


# ---------------------------------------------------------------- logo da empresa (sobreposto nas imagens)
@router.get("/social/logo")
async def get_logo(user: dict = Depends(premium_user)):
    cid = await active_company_id(user["id"])
    doc = await db.brand_assets.find_one({"user_id": user["id"], "company_id": cid})
    if not doc or not doc.get("logo_data"):
        return {"has_logo": False}
    return {"has_logo": True, "preview": f"data:{doc.get('content_type', 'image/png')};base64,{doc['logo_data']}"}


@router.post("/social/logo")
async def upload_logo(file: UploadFile = File(...), user: dict = Depends(premium_user)):
    ct = file.content_type or ""
    if not ct.startswith("image/"):
        raise HTTPException(400, "Envie um ficheiro de imagem (PNG de preferência, com fundo transparente).")
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(400, "Logo demasiado grande (máx 5 MB).")
    try:
        data = prepare_logo(data); ct = "image/png"
    except Exception as e:
        logger.error(f"prepare_logo: {e}")
    b64 = base64.b64encode(data).decode()
    cid = await active_company_id(user["id"])
    await db.brand_assets.update_one({"user_id": user["id"], "company_id": cid}, {"$set": {
        "user_id": user["id"], "company_id": cid, "logo_data": b64, "content_type": ct,
        "updated_at": datetime.now(timezone.utc).isoformat()}}, upsert=True)
    return {"ok": True, "preview": f"data:{ct};base64,{b64}"}


@router.delete("/social/logo")
async def delete_logo(user: dict = Depends(premium_user)):
    cid = await active_company_id(user["id"])
    await db.brand_assets.delete_one({"user_id": user["id"], "company_id": cid})
    return {"ok": True}


# ---------------------------------------------------------------- worker de agendamento
async def run_due_social_jobs():
    now = datetime.now(timezone.utc)
    async for job in db.social_jobs.find({"status": "queued"}):
        try:
            ra = datetime.fromisoformat(job["run_at"].replace("Z", "+00:00"))
            if ra.tzinfo is None:
                ra = ra.replace(tzinfo=timezone.utc)
            if ra > now:
                continue
            claimed = await db.social_jobs.find_one_and_update(
                {"_id": job["_id"], "status": "queued"}, {"$set": {"status": "processing"}})
            if not claimed:
                continue
            cid = job.get("company_id") or await active_company_id(job["user_id"])
            res = await _publish_core(job["user_id"], cid, job["payload"])
            published_at = datetime.now(timezone.utc).isoformat()
            await db.social_jobs.update_one({"_id": job["_id"]}, {"$set": {
                "status": "published", "result": res, "published_at": published_at}})
            post_id = ((job or {}).get("payload") or {}).get("post_id")
            if post_id:
                await _sync_marketing_post(job["user_id"], cid, post_id, "scheduled", scheduled_at=job.get("run_at"), published_at=published_at)
        except Exception as e:
            await db.social_jobs.update_one({"_id": job["_id"]}, {"$set": {
                "status": "failed", "error": str(getattr(e, "detail", e))[:500]}})
