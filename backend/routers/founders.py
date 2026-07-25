from fastapi import APIRouter, Depends, HTTPException, Request, Response, Query
from fastapi.responses import StreamingResponse
from core import *
from models import *
import io, csv

router = APIRouter()

# ---------------------------------------------------------------- PUBLIC counter
@router.get("/founders/status")
async def founders_status():
    camp = await get_campaign()
    claimed = await founder_claimed_count()
    remaining = max(0, FOUNDER_LIMIT - claimed)
    active = bool(camp.get("active", True)) and claimed < FOUNDER_LIMIT
    return {
        "limit": FOUNDER_LIMIT, "claimed": claimed, "remaining": remaining,
        "program_active": active,
        "founder_price": FOUNDER_PRICE_MONTHLY,
        "professional_price": PROFESSIONAL_PRICE_MONTHLY,
        "enterprise_price": ENTERPRISE_PRICE_MONTHLY,
        "trial_days": PROFESSIONAL_TRIAL_DAYS,
    }

# ---------------------------------------------------------------- ADMIN helpers
def _month_start():
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

async def _company_name(uid: str) -> str:
    c = await db.companies.find_one({"user_id": uid})
    return (c or {}).get("name", "")

async def _customer_row(u: dict) -> dict:
    uid = str(u["_id"])
    plan = u.get("plan")
    status = u.get("subscription_status")
    is_f = bool(u.get("is_founder"))
    monthly = 0
    if status in PREMIUM_STATUSES:
        monthly = FOUNDER_PRICE_MONTHLY if (is_f and u.get("founder_price_locked")) else PLAN_PRICE.get(plan or "professional", 0)
    return {
        "id": uid,
        "company": await _company_name(uid),
        "name": u.get("name", ""),
        "email": u.get("email", ""),
        "plan": PLAN_LABELS.get(plan, "—") if plan else "—",
        "plan_key": plan,
        "is_founder": is_f,
        "founder_number": u.get("founder_number"),
        "founder_price_locked": bool(u.get("founder_price_locked")),
        "subscription_status": status or "free",
        "monthly": monthly,
        "created_at": u.get("created_at"),
        "activated_at": u.get("subscription_started_at"),
        "last_payment_at": u.get("last_payment_at"),
        "current_period_end": u.get("current_period_end"),
        "cancelled_at": u.get("subscription_cancelled_at"),
        "stripe_customer_id": u.get("stripe_customer_id"),
        "stripe_subscription_id": u.get("stripe_subscription_id"),
        "internal_notes": u.get("internal_notes", []),
    }

# ---------------------------------------------------------------- ADMIN overview
@router.get("/admin/overview")
async def admin_overview(admin: dict = Depends(get_admin_user)):
    users = await db.users.find({}).to_list(100000)
    total_companies = await db.companies.count_documents({})
    active = [u for u in users if u.get("subscription_status") == "active"]
    trialing = [u for u in users if u.get("subscription_status") == "trialing"]
    founders_assigned = await founder_claimed_count()
    founders_active = [u for u in users if u.get("is_founder") and u.get("subscription_status") in PREMIUM_STATUSES and u.get("founder_price_locked")]
    prof_active = [u for u in users if u.get("plan") == "professional" and u.get("subscription_status") in PREMIUM_STATUSES and not (u.get("is_founder") and u.get("founder_price_locked"))]
    ent_active = [u for u in users if u.get("plan") == "enterprise" and u.get("subscription_status") in PREMIUM_STATUSES]
    founder_mrr = len(founders_active) * FOUNDER_PRICE_MONTHLY
    prof_mrr = len(prof_active) * PROFESSIONAL_PRICE_MONTHLY
    ent_mrr = len(ent_active) * ENTERPRISE_PRICE_MONTHLY
    ms = _month_start().isoformat()
    cancellations_month = len([u for u in users if (u.get("subscription_cancelled_at") or "") >= ms])
    failed_payments = await db.payment_events.count_documents({"type": "payment_failed", "created_at": {"$gte": ms}})
    now = datetime.now(timezone.utc)
    d7 = (now - timedelta(days=7)).isoformat(); d30 = (now - timedelta(days=30)).isoformat()
    new_7d = len([u for u in users if (u.get("created_at") or "") >= d7])
    new_30d = len([u for u in users if (u.get("created_at") or "") >= d30])
    camp = await get_campaign()
    return {
        "total_companies": total_companies,
        "total_users": len(users),
        "active_subscriptions": len(active) + len(trialing),
        "trialing": len(trialing),
        "founders_assigned": founders_assigned,
        "founders_active": len(founders_active),
        "remaining_slots": max(0, FOUNDER_LIMIT - founders_assigned),
        "founder_limit": FOUNDER_LIMIT,
        "professional_count": len(prof_active),
        "enterprise_count": len(ent_active),
        "mrr_total": founder_mrr + prof_mrr + ent_mrr,
        "mrr_founders": founder_mrr,
        "mrr_others": prof_mrr + ent_mrr,
        "cancellations_month": cancellations_month,
        "failed_payments": failed_payments,
        "new_7d": new_7d,
        "new_30d": new_30d,
        "campaign_active": bool(camp.get("active", True)),
    }

# ---------------------------------------------------------------- customers list
def _match_filter(u: dict, f: str) -> bool:
    st = u.get("subscription_status")
    if f == "all":
        return True
    if f == "active":
        return st in PREMIUM_STATUSES
    if f == "trial":
        return st == "trialing"
    if f == "founders":
        return bool(u.get("is_founder"))
    if f == "professional":
        return u.get("plan") == "professional"
    if f == "enterprise":
        return u.get("plan") == "enterprise"
    if f == "past_due":
        return st == "past_due"
    if f == "cancelled":
        return st in ("canceled", "unpaid", "incomplete_expired")
    return True

@router.get("/admin/customers")
async def admin_customers(admin: dict = Depends(get_admin_user), filter: str = "all", search: str = ""):
    users = await db.users.find({}).sort("created_at", -1).to_list(100000)
    users = [u for u in users if _match_filter(u, filter)]
    rows = [await _customer_row(u) for u in users]
    if search:
        s = search.lower()
        rows = [r for r in rows if s in (r["company"] or "").lower() or s in (r["name"] or "").lower() or s in (r["email"] or "").lower()]
    return {"customers": rows, "count": len(rows)}

@router.get("/admin/customers/export")
async def admin_customers_export(admin: dict = Depends(get_admin_user)):
    users = await db.users.find({}).sort("created_at", -1).to_list(100000)
    rows = [await _customer_row(u) for u in users]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Empresa", "Responsável", "Email", "Plano", "Fundadora", "Nº Fundadora", "Estado",
                "Valor mensal (€)", "Registo", "Ativação", "Último pagamento", "Próxima cobrança",
                "Stripe Customer", "Stripe Subscription"])
    for r in rows:
        w.writerow([r["company"], r["name"], r["email"], r["plan"], "Sim" if r["is_founder"] else "Não",
                    r["founder_number"] or "", r["subscription_status"], r["monthly"], r["created_at"] or "",
                    r["activated_at"] or "", r["last_payment_at"] or "", r["current_period_end"] or "",
                    r["stripe_customer_id"] or "", r["stripe_subscription_id"] or ""])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=clientes_ceo_ai.csv"})

# ---------------------------------------------------------------- founder positions
@router.get("/admin/founders")
async def admin_founders(admin: dict = Depends(get_admin_user)):
    users = await db.users.find({"founder_number": {"$exists": True}}).sort("founder_number", 1).to_list(1000)
    out = []
    for u in users:
        out.append({
            "founder_number": u.get("founder_number"),
            "company": await _company_name(str(u["_id"])),
            "name": u.get("name", ""), "email": u.get("email", ""),
            "price_locked": bool(u.get("founder_price_locked")),
            "status": u.get("subscription_status"),
            "activated_at": u.get("founder_activated_at"),
        })
    claimed = await founder_claimed_count()
    return {"positions": out, "claimed": claimed, "limit": FOUNDER_LIMIT, "remaining": max(0, FOUNDER_LIMIT - claimed)}

# ---------------------------------------------------------------- campaign toggle
@router.post("/admin/campaign/toggle")
async def admin_campaign_toggle(inp: CampaignToggleInput, admin: dict = Depends(get_admin_user)):
    before = await get_campaign()
    await set_campaign_active(inp.active)
    await audit_log(admin["email"], "campaign_toggle", target="founder_campaign",
                    before={"active": before.get("active")}, after={"active": inp.active})
    return {"active": inp.active}

# ---------------------------------------------------------------- notes / cancel / resend
@router.post("/admin/customers/{uid}/note")
async def admin_add_note(uid: str, inp: AdminNoteInput, admin: dict = Depends(get_admin_user)):
    note = {"text": inp.note, "by": admin["email"], "at": datetime.now(timezone.utc).isoformat()}
    await db.users.update_one({"_id": ObjectId(uid)}, {"$push": {"internal_notes": note}})
    await audit_log(admin["email"], "add_note", target=uid, after=note)
    return {"ok": True, "note": note}

@router.post("/admin/customers/{uid}/cancel")
async def admin_cancel(uid: str, admin: dict = Depends(get_admin_user)):
    u = await db.users.find_one({"_id": ObjectId(uid)}) or {}
    sub_id = u.get("stripe_subscription_id")
    if not sub_id:
        raise HTTPException(400, "Cliente sem subscrição ativa")
    try:
        stripe.Subscription.modify(sub_id, cancel_at_period_end=True)
        await db.users.update_one({"_id": u["_id"]}, {"$set": {"cancel_at_period_end": True}})
    except Exception as e:
        logger.error(f"admin cancel error: {e}")
        raise HTTPException(500, "Não foi possível cancelar via Stripe")
    await audit_log(admin["email"], "cancel_subscription", target=uid)
    return {"ok": True}

@router.post("/admin/customers/{uid}/resend-notification")
async def admin_resend(uid: str, admin: dict = Depends(get_admin_user)):
    u = await db.users.find_one({"_id": ObjectId(uid)}) or {}
    if not u.get("founder_number"):
        raise HTTPException(400, "Este cliente não é Empresa Fundadora")
    remaining = max(0, FOUNDER_LIMIT - await founder_claimed_count())
    await notify_founder_activated(u, u.get("founder_number"), remaining)
    await audit_log(admin["email"], "resend_notification", target=uid)
    return {"ok": True}

# ---------------------------------------------------------------- notifications / audit
@router.get("/admin/notifications")
async def admin_notifications(admin: dict = Depends(get_admin_user)):
    notes = await db.admin_notifications.find({}).sort("created_at", -1).to_list(200)
    for n in notes:
        n["id"] = str(n.pop("_id"))
    unread = len([n for n in notes if not n.get("read")])
    return {"notifications": notes, "unread": unread}

@router.post("/admin/notifications/read-all")
async def admin_notifications_read(admin: dict = Depends(get_admin_user)):
    await db.admin_notifications.update_many({"read": {"$ne": True}}, {"$set": {"read": True}})
    return {"ok": True}

@router.get("/admin/audit")
async def admin_audit(admin: dict = Depends(get_admin_user)):
    logs = await db.audit_log.find({}).sort("created_at", -1).to_list(300)
    for l in logs:
        l["id"] = str(l.pop("_id"))
    return {"logs": logs}
