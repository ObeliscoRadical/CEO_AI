"""Fase 4 — Publicação automática nas redes (Instagram + Facebook via Meta Graph API).
Ligação OAuth da conta do utilizador, publicação imediata e agendamento a partir dos conteúdos de Marketing.
Em modo de desenvolvimento a Meta só permite publicar em contas com papel na app (admin/developer/tester)."""
import os, base64, uuid, hmac, hashlib
from urllib.parse import urlencode, quote
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import httpx
from core import *

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


# ---------------------------------------------------------------- media pública (para o Instagram buscar a imagem)
async def _store_public_image(uid: str, data: bytes, ct: str = "image/png") -> str:
    mid = str(uuid.uuid4())
    await db.social_media.insert_one({"_id": mid, "user_id": uid,
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
    conn = await db.social_connections.find_one({"user_id": user["id"]})
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
    state = secrets.token_urlsafe(24)
    await db.social_oauth_states.insert_one({"_id": state, "user_id": user["id"],
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
        await db.social_connections.update_one({"user_id": uid}, {"$set": {
            "user_id": uid, "page_id": chosen["id"], "page_name": chosen.get("name"),
            "ig_user_id": ig_id, "ig_username": ig_username,
            "page_token": chosen["access_token"], "user_token": user_token,
            "updated_at": datetime.now(timezone.utc).isoformat()}}, upsert=True)
        return RedirectResponse(f"{base}/marketing?connected=1")
    except Exception as e:
        logger.error(f"social oauth callback: {e}")
        return RedirectResponse(f"{base}/marketing?social_error=falha_oauth")


@router.post("/social/disconnect")
async def social_disconnect(user: dict = Depends(premium_user)):
    await db.social_connections.delete_one({"user_id": user["id"]})
    return {"ok": True}


# ---------------------------------------------------------------- publicação
class PublishIn(BaseModel):
    caption: str = ""
    image_prompt: Optional[str] = None
    generate_image: bool = True
    image_url: Optional[str] = None
    instagram: bool = True
    facebook: bool = True


class ScheduleIn(PublishIn):
    run_at: str                             # ISO 8601 UTC


async def _publish_core(uid: str, payload: dict) -> dict:
    conn = await db.social_connections.find_one({"user_id": uid})
    if not conn:
        raise HTTPException(400, "As redes ainda não estão ligadas.")
    caption = payload.get("caption") or ""
    image_url = payload.get("image_url")
    want_img = payload.get("generate_image", True)
    do_ig = payload.get("instagram", True)
    do_fb = payload.get("facebook", True)
    if not image_url and want_img and (do_ig or do_fb):
        prompt = payload.get("image_prompt") or caption[:220] or "Conteúdo de marketing profissional"
        img = await generate_marketing_image(prompt)
        image_url = await _store_public_image(uid, img)
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
    await db.social_posts.insert_one({"user_id": uid, "caption": caption, "image_url": image_url,
                                      "results": results, "created_at": datetime.now(timezone.utc).isoformat()})
    return results


@router.post("/social/publish")
async def social_publish(inp: PublishIn, user: dict = Depends(premium_user)):
    res = await _publish_core(user["id"], inp.model_dump())
    return {"ok": True, "results": res}


@router.post("/social/schedule")
async def social_schedule(inp: ScheduleIn, user: dict = Depends(premium_user)):
    conn = await db.social_connections.find_one({"user_id": user["id"]})
    if not conn:
        raise HTTPException(400, "As redes ainda não estão ligadas.")
    d = inp.model_dump(); run_at = d.pop("run_at")
    job = {"_id": str(uuid.uuid4()), "user_id": user["id"], "payload": d, "run_at": run_at,
           "status": "queued", "created_at": datetime.now(timezone.utc).isoformat()}
    await db.social_jobs.insert_one(job)
    return {"ok": True, "id": job["_id"]}


@router.get("/social/jobs")
async def social_jobs(user: dict = Depends(premium_user)):
    jobs = await db.social_jobs.find({"user_id": user["id"]}).sort("run_at", 1).to_list(100)
    out = [{"id": j["_id"], "run_at": j.get("run_at"), "status": j.get("status"),
            "caption": ((j.get("payload") or {}).get("caption") or "")[:80], "error": j.get("error")} for j in jobs]
    return {"jobs": out}


@router.delete("/social/jobs/{jid}")
async def del_job(jid: str, user: dict = Depends(premium_user)):
    await db.social_jobs.delete_one({"_id": jid, "user_id": user["id"]})
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
            res = await _publish_core(job["user_id"], job["payload"])
            await db.social_jobs.update_one({"_id": job["_id"]}, {"$set": {
                "status": "published", "result": res, "published_at": datetime.now(timezone.utc).isoformat()}})
        except Exception as e:
            await db.social_jobs.update_one({"_id": job["_id"]}, {"$set": {
                "status": "failed", "error": str(getattr(e, "detail", e))[:500]}})
