"""Notificações proativas do CRM (Fase 1) — motor de regras + centro de notificações in-app + push com ações.
Aprovação primeiro: os alertas sugerem ações e ligam ao módulo certo para o utilizador rever antes de enviar."""
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from core import *

router = APIRouter()

PUSH_ACTIONS = [{"action": "approve", "title": "Sim, preparar"}, {"action": "snooze", "title": "Lembrar depois"}]


def _now():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.isoformat()


def _sn(d):
    return {"id": str(d["_id"]), "type": d.get("type"), "title": d.get("title"), "body": d.get("body"),
            "data": d.get("data") or {}, "status": d.get("status"), "created_at": d.get("created_at")}


async def _recent_exists(uid, cid, ntype, camp):
    cutoff = _iso(_now() - timedelta(hours=20))
    return await db.notifications.find_one({
        "user_id": uid, "company_id": cid, "type": ntype, "data.campaign": camp,
        "status": {"$in": ["unread", "read"]}, "created_at": {"$gt": cutoff}})


async def _create(uid, cid, ntype, title, body, data):
    doc = {"user_id": uid, "company_id": cid, "type": ntype, "title": title, "body": body,
           "data": data, "status": "unread", "snooze_until": None, "created_at": _iso(_now())}
    res = await db.notifications.insert_one(doc)
    try:
        await send_push_to_user(uid, title, body, url=data.get("route", "/"),
                                actions=PUSH_ACTIONS, extra={"notif_id": str(res.inserted_id)})
    except Exception as e:
        logger.error(f"push alerta: {e}")
    return res.inserted_id


# ---------------------------------------------------------------- motor de regras
async def evaluate_crm_alerts(only_user: Optional[str] = None):
    from routers.prospecting import CAMPAIGNS
    created = 0
    users = set([only_user]) if only_user else set()
    if not only_user:
        for coll in (db.prospects, db.crm_leads):
            for uid in await coll.distinct("user_id"):
                users.add(uid)
    now = _now()
    for uid in users:
        st = await db.crm_alert_settings.find_one({"user_id": uid}) or {}
        min_new = int(st.get("min_new", 10))
        fdays = int(st.get("followup_days", 5))
        cids = list(await db.prospects.distinct("company_id", {"user_id": uid}))
        for c in await db.crm_leads.distinct("company_id", {"user_id": uid}):
            if c not in cids:
                cids.append(c)
        for cid in cids:
            # Gatilho 1 — novas empresas sem contacto (por campanha)
            for camp in await db.prospects.distinct("campaign", {"user_id": uid, "company_id": cid}):
                cnt = await db.prospects.count_documents({"user_id": uid, "company_id": cid,
                                                          "campaign": camp, "contacted": {"$ne": True}})
                if cnt >= min_new and not await _recent_exists(uid, cid, "novos_sem_contacto", camp):
                    label = CAMPAIGNS.get(camp, {}).get("label", camp)
                    await _create(uid, cid, "novos_sem_contacto", "Empresas por contactar",
                                  f"Detetámos {cnt} empresas na campanha '{label}' ainda sem contacto. Quer preparar a prospeção?",
                                  {"campaign": camp, "count": cnt, "route": "/captacao"})
                    created += 1
            # Gatilho 2 — leads sem seguimento há N dias
            cutoff = _iso(now - timedelta(days=fdays))
            overdue = await db.crm_leads.count_documents({
                "user_id": uid, "company_id": cid,
                "stage": {"$in": ["novo", "qualificado", "contactado", "reuniao", "proposta"]},
                "created_at": {"$lt": cutoff}})
            if overdue >= 1 and not await _recent_exists(uid, cid, "followup", "__leads__"):
                await _create(uid, cid, "followup", "Follow-up sugerido",
                              f"Tem {overdue} lead(s) sem seguimento há mais de {fdays} dias. Sugerimos enviar um follow-up.",
                              {"campaign": "__leads__", "count": overdue, "route": "/crm"})
                created += 1
    return created


# ---------------------------------------------------------------- endpoints
@router.get("/crm/notifications")
async def list_notifs(user: dict = Depends(premium_user)):
    uid = user["id"]; now = _iso(_now())
    q = {"user_id": uid, "status": {"$in": ["unread", "read"]},
         "$or": [{"snooze_until": None}, {"snooze_until": {"$lte": now}}]}
    docs = await db.notifications.find(q).sort("created_at", -1).to_list(50)
    unread = sum(1 for d in docs if d.get("status") == "unread")
    return {"notifications": [_sn(d) for d in docs], "unread": unread}


@router.post("/crm/notifications/{nid}/read")
async def mark_read(nid: str, user: dict = Depends(premium_user)):
    await db.notifications.update_one({"_id": ObjectId(nid), "user_id": user["id"], "status": "unread"},
                                      {"$set": {"status": "read"}})
    return {"ok": True}


@router.post("/crm/notifications/{nid}/snooze")
async def snooze(nid: str, user: dict = Depends(premium_user), days: int = Body(1, embed=True)):
    until = _iso(_now() + timedelta(days=max(1, days)))
    await db.notifications.update_one({"_id": ObjectId(nid), "user_id": user["id"]},
                                      {"$set": {"snooze_until": until, "status": "read"}})
    return {"ok": True, "snooze_until": until}


@router.post("/crm/notifications/{nid}/dismiss")
async def dismiss(nid: str, user: dict = Depends(premium_user)):
    await db.notifications.update_one({"_id": ObjectId(nid), "user_id": user["id"]},
                                      {"$set": {"status": "dismissed"}})
    return {"ok": True}


@router.post("/crm/notifications/{nid}/act")
async def act(nid: str, user: dict = Depends(premium_user)):
    doc = await db.notifications.find_one({"_id": ObjectId(nid), "user_id": user["id"]})
    if not doc:
        raise HTTPException(404, "Notificação não encontrada.")
    await db.notifications.update_one({"_id": doc["_id"]}, {"$set": {"status": "acted"}})
    return {"ok": True, "data": doc.get("data") or {}}


@router.post("/crm/notifications/run-eval")
async def run_eval(user: dict = Depends(premium_user)):
    created = await evaluate_crm_alerts(only_user=user["id"])
    return {"ok": True, "created": created}


@router.get("/crm/alert-settings")
async def get_settings(user: dict = Depends(premium_user)):
    st = await db.crm_alert_settings.find_one({"user_id": user["id"]}) or {}
    return {"min_new": int(st.get("min_new", 10)), "followup_days": int(st.get("followup_days", 5))}


@router.post("/crm/alert-settings")
async def set_settings(user: dict = Depends(premium_user),
                       min_new: int = Body(10, embed=True), followup_days: int = Body(5, embed=True)):
    await db.crm_alert_settings.update_one({"user_id": user["id"]},
                                           {"$set": {"user_id": user["id"], "min_new": max(1, min_new),
                                                     "followup_days": max(1, followup_days)}}, upsert=True)
    return {"ok": True}
