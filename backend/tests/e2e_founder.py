import asyncio, uuid, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import stripe
from datetime import datetime, timezone
from bson import ObjectId
import core
from core import (db, handle_founder_activation, sync_subscription, founder_claimed_count,
                  set_campaign_active, FOUNDER_LIMIT)

TESTP = "E2ETEST_"

async def mk_user(n):
    email = f"{TESTP}{n}_{uuid.uuid4().hex[:6]}@t.com"
    res = await db.users.insert_one({"email": email, "name": f"T{n}", "role": "owner",
        "auth_provider": "email", "password_hash": "", "is_premium": False,
        "created_at": datetime.now(timezone.utc).isoformat()})
    await db.companies.insert_one({"user_id": str(res.inserted_id), "name": f"Empresa {n}",
        "region": "PT", "currency": "EUR", "sector": "servicos",
        "created_at": datetime.now(timezone.utc).isoformat()})
    return await db.users.find_one({"_id": res.inserted_id})

async def cleanup():
    users = await db.users.find({"email": {"$regex": f"^{TESTP}"}}).to_list(1000)
    ids = [str(u["_id"]) for u in users]
    await db.users.delete_many({"email": {"$regex": f"^{TESTP}"}})
    for i in ids:
        await db.companies.delete_many({"user_id": i})
    # reset counter to number of REAL (non-test) founders remaining
    real = await db.users.count_documents({"founder_number": {"$exists": True}})
    await db.counters.update_one({"_id": "founder"}, {"$set": {"seq": real}}, upsert=True)
    await set_campaign_active(True)
    await db.app_config.update_one({"_id": "founder_campaign"}, {"$set": {"milestones_sent": []}})

async def main():
    ok = True
    await cleanup()
    start = await founder_claimed_count()
    print("start claimed:", start)

    # 1. allocation
    u1 = await mk_user(1)
    n1 = await handle_founder_activation(u1)
    print("alloc u1 ->", n1)
    assert n1 == start + 1, "expected next number"

    # 2. idempotency per-user: same user again -> no new slot
    u1f = await db.users.find_one({"_id": u1["_id"]})
    n1b = await handle_founder_activation(u1f)
    print("re-alloc u1 ->", n1b, "(should be None)")
    assert n1b is None
    assert await founder_claimed_count() == start + 1, "claimed must not double"

    # 3. concurrency: two users at once -> distinct numbers
    u2 = await mk_user(2); u3 = await mk_user(3)
    r2, r3 = await asyncio.gather(handle_founder_activation(u2), handle_founder_activation(u3))
    print("concurrent ->", r2, r3)
    assert r2 != r3 and None not in (r2, r3), "distinct numbers"
    assert await founder_claimed_count() == start + 3

    # 4. cap at FOUNDER_LIMIT
    await db.counters.update_one({"_id": "founder"}, {"$set": {"seq": FOUNDER_LIMIT}})
    uc = await mk_user("cap")
    rc = await handle_founder_activation(uc)
    print("at cap ->", rc, "(should be None)")
    assert rc is None

    # 5. Stripe: trialing does NOT allocate, active DOES
    await db.counters.update_one({"_id": "founder"}, {"$set": {"seq": 0}})
    await set_campaign_active(True)
    price_f = stripe.Price.list(lookup_keys=["founder_monthly"], active=True, limit=1).data[0]
    price_p = stripe.Price.list(lookup_keys=["professional_monthly"], active=True, limit=1).data[0]

    def new_customer():
        c = stripe.Customer.create()
        pm = stripe.PaymentMethod.attach("pm_card_visa", customer=c.id)
        stripe.Customer.modify(c.id, invoice_settings={"default_payment_method": pm.id})
        return c

    # trial professional
    up = await mk_user("prof")
    cp = new_customer()
    subp = stripe.Subscription.create(customer=cp.id, items=[{"price": price_p.id}],
                                      trial_period_days=7, metadata={"user_id": str(up["_id"])})
    await sync_subscription(subp.id, str(up["_id"]))
    upf = await db.users.find_one({"_id": up["_id"]})
    print("professional trial status:", upf.get("subscription_status"), "is_premium:", upf.get("is_premium"),
          "is_founder:", bool(upf.get("is_founder")))
    assert upf.get("subscription_status") == "trialing"
    assert upf.get("is_premium") is True
    assert not upf.get("is_founder"), "trial must NOT take a founder slot"
    claimed_after_trial = await founder_claimed_count()
    assert claimed_after_trial == 0, "trial must not increment claimed"

    # active founder
    uf = await mk_user("founder")
    cf = new_customer()
    subf = stripe.Subscription.create(customer=cf.id, items=[{"price": price_f.id}],
                                      metadata={"user_id": str(uf["_id"])})
    print("founder sub status:", subf.status)
    await sync_subscription(subf.id, str(uf["_id"]))
    uff = await db.users.find_one({"_id": uf["_id"]})
    print("founder ->", "is_founder:", bool(uff.get("is_founder")), "number:", uff.get("founder_number"),
          "price_locked:", uff.get("founder_price_locked"))
    assert uff.get("is_founder") and uff.get("founder_number") == 1
    assert await founder_claimed_count() == 1

    # idempotent sync again -> no double
    await sync_subscription(subf.id, str(uf["_id"]))
    assert await founder_claimed_count() == 1, "second sync must not double-allocate"

    # cancel founder -> keeps number, loses price
    stripe.Subscription.cancel(subf.id)
    await sync_subscription(subf.id, str(uf["_id"]))
    ufc = await db.users.find_one({"_id": uf["_id"]})
    print("after cancel:", "number kept:", ufc.get("founder_number"), "price_locked:", ufc.get("founder_price_locked"),
          "status:", ufc.get("subscription_status"))
    assert ufc.get("founder_number") == 1, "historical number kept"
    assert ufc.get("founder_price_locked") is False, "price lost"
    assert await founder_claimed_count() == 1, "slot NOT freed on cancel"

    print("\nALL FOUNDER E2E CHECKS PASSED ✅")
    await cleanup()
    print("cleaned up; claimed now:", await founder_claimed_count())

asyncio.run(main())
