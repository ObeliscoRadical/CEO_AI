from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File, Form, Header, Query
from fastapi.responses import StreamingResponse
from core import *
from models import *

router = APIRouter()

# ---------------------------------------------------------------- subscription / Stripe
PLANS = {
    "premium_monthly": {"label": "Premium Mensal", "price": "€29", "period": "/mês"},
    "premium_yearly": {"label": "Premium Anual", "price": "€290", "period": "/ano"},
}

@router.get("/subscription")
async def subscription(user: dict = Depends(get_current_user)):
    prem = await is_premium(user["id"])
    u = await db.users.find_one({"_id": ObjectId(user["id"])}) or {}
    sub_info = None
    sub_id = u.get("stripe_subscription_id")
    if sub_id:
        try:
            s = stripe.Subscription.retrieve(sub_id)
            item = s["items"]["data"][0]
            lk = item["price"].get("lookup_key")
            period_end = s.get("current_period_end") or item.get("current_period_end")
            sub_info = {
                "status": s["status"],
                "plan": PLANS.get(lk, {}).get("label", "Premium"),
                "lookup_key": lk,
                "cancel_at_period_end": s.get("cancel_at_period_end", False),
                "current_period_end": period_end,
            }
        except Exception as e:
            logger.error(f"sub retrieve error: {e}")
    return {"is_premium": prem, "plans": PLANS, "subscription": sub_info,
            "has_billing": bool(u.get("stripe_customer_id"))}

@router.post("/payments/checkout")
async def create_checkout(req: CheckoutRequest, user: dict = Depends(get_current_user)):
    prices = stripe.Price.list(lookup_keys=[req.lookup_key], active=True, limit=1).data
    if not prices:
        raise HTTPException(400, f"Preço não encontrado: {req.lookup_key}")
    price = prices[0]
    kwargs = dict(
        line_items=[{"price": price.id, "quantity": 1}],
        mode="subscription",
        success_url=f"{req.origin_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{req.origin_url}/payment/cancel",
        metadata={"user_id": user["id"], "lookup_key": req.lookup_key},
    )
    try:
        session = stripe.checkout.Session.create(**kwargs, managed_payments={"enabled": True})
    except stripe.error.InvalidRequestError as e:
        msg = (e.user_message or "").lower()
        if "managed payments" in msg or "ineligible" in msg:
            session = stripe.checkout.Session.create(**kwargs, automatic_tax={"enabled": True}, billing_address_collection="required")
        else:
            raise
    await db.payment_transactions.insert_one({
        "session_id": session.id, "user_id": user["id"], "lookup_key": req.lookup_key,
        "amount": (price.unit_amount or 0), "currency": price.currency,
        "status": "initiated", "payment_status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"checkout_url": session.url, "session_id": session.id}

async def _activate_premium(user_id: str, customer_id: str = None, subscription_id: str = None):
    if not user_id:
        return
    try:
        upd = {"is_premium": True}
        if customer_id:
            upd["stripe_customer_id"] = customer_id
        if subscription_id:
            upd["stripe_subscription_id"] = subscription_id
        await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": upd})
    except Exception:
        pass

@router.get("/payments/status/{session_id}")
async def get_status(session_id: str):
    record = await db.payment_transactions.find_one({"session_id": session_id})
    if not record:
        raise HTTPException(404, "Transação não encontrada")
    if record.get("payment_status") != "paid":
        try:
            s = stripe.checkout.Session.retrieve(session_id)
            if s.payment_status == "paid" or s.status == "complete":
                await db.payment_transactions.update_one(
                    {"session_id": session_id, "payment_status": {"$ne": "paid"}},
                    {"$set": {"status": "completed", "payment_status": "paid",
                              "stripe_subscription_id": s.subscription, "updated_at": datetime.now(timezone.utc).isoformat()}})
                await _activate_premium(record.get("user_id"), s.customer, s.subscription)
                record = await db.payment_transactions.find_one({"session_id": session_id})
        except stripe.error.StripeError:
            pass
    return {"session_id": record["session_id"], "status": record["status"], "payment_status": record["payment_status"]}

def _get_portal_config():
    cfgs = stripe.billing_portal.Configuration.list(limit=1).data
    if cfgs:
        return cfgs[0].id
    cfg = stripe.billing_portal.Configuration.create(
        business_profile={"headline": "CEO AI — Gestão da subscrição"},
        features={
            "invoice_history": {"enabled": True},
            "payment_method_update": {"enabled": True},
            "subscription_cancel": {"enabled": True, "mode": "at_period_end"},
        },
    )
    return cfg.id

@router.post("/payments/portal")
async def billing_portal(req: OriginRequest, user: dict = Depends(get_current_user)):
    u = await db.users.find_one({"_id": ObjectId(user["id"])}) or {}
    cust = u.get("stripe_customer_id")
    if not cust:
        raise HTTPException(400, "Sem subscrição ativa")
    origin = req.origin_url or os.environ.get("FRONTEND_URL", "")
    try:
        sess = stripe.billing_portal.Session.create(customer=cust, configuration=_get_portal_config(),
                                                     return_url=f"{origin}/subscricao")
        return {"url": sess.url}
    except Exception as e:
        logger.error(f"portal error: {e}")
        raise HTTPException(500, "Portal indisponível")

@router.post("/payments/cancel-subscription")
async def cancel_subscription(user: dict = Depends(get_current_user)):
    u = await db.users.find_one({"_id": ObjectId(user["id"])}) or {}
    sub_id = u.get("stripe_subscription_id")
    if not sub_id:
        raise HTTPException(400, "Sem subscrição ativa")
    try:
        stripe.Subscription.modify(sub_id, cancel_at_period_end=True)
    except Exception as e:
        logger.error(f"cancel error: {e}")
        raise HTTPException(500, "Não foi possível cancelar")
    return {"ok": True, "cancel_at_period_end": True}

@router.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(400, "Assinatura inválida")
    obj, t = event["data"]["object"], event["type"]
    if t == "checkout.session.completed":
        await db.payment_transactions.update_one(
            {"session_id": obj["id"], "payment_status": {"$ne": "paid"}},
            {"$set": {"status": "completed", "payment_status": obj.get("payment_status", "paid"),
                      "stripe_subscription_id": obj.get("subscription"), "updated_at": datetime.now(timezone.utc).isoformat()}})
        rec = await db.payment_transactions.find_one({"session_id": obj["id"]})
        await _activate_premium((rec or {}).get("user_id") or (obj.get("metadata") or {}).get("user_id"),
                                obj.get("customer"), obj.get("subscription"))
    elif t in ("customer.subscription.deleted",) or (t == "customer.subscription.updated" and obj.get("status") in ("canceled", "unpaid", "incomplete_expired")):
        sub_id = obj.get("id")
        u = await db.users.find_one({"stripe_subscription_id": sub_id})
        if u:
            await db.users.update_one({"_id": u["_id"]}, {"$set": {"is_premium": False}})
    return {"status": "ok"}
