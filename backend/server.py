from dotenv import load_dotenv
from pathlib import Path
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timezone

from core import db, client, hash_password, verify_password, init_storage, send_daily_briefings, send_monthly_value_alerts, logger
from routers import auth, companies, finance, ceo, documents, billing, misc, voice, founders, goals

app = FastAPI()
api_router = APIRouter(prefix="/api")
for _m in (auth, companies, finance, ceo, documents, billing, misc, voice, founders, goals):
    api_router.include_router(_m.router)
app.include_router(api_router)

cors_env = os.environ.get("CORS_ORIGINS", "*").strip()
if cors_env == "*":
    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origin_regex=".*",
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=[o.strip() for o in cors_env.split(",") if o.strip()],
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("stripe_subscription_id")
    await db.users.create_index("stripe_customer_id")
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.counters.update_one({"_id": "founder"}, {"$setOnInsert": {"seq": 0}}, upsert=True)
    await db.app_config.update_one({"_id": "founder_campaign"},
                                   {"$setOnInsert": {"active": True, "milestones_sent": []}}, upsert=True)
    admin_email = os.environ.get("ADMIN_EMAIL", "").lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "")
    if admin_email and admin_password:
        existing = await db.users.find_one({"email": admin_email})
        if not existing:
            await db.users.insert_one({"email": admin_email, "password_hash": hash_password(admin_password),
                                       "name": "Admin CEO AI", "role": "admin", "auth_provider": "email", "picture": "",
                                       "is_premium": True, "created_at": datetime.now(timezone.utc).isoformat()})
        else:
            upd = {"role": "admin", "is_premium": True}
            if existing.get("password_hash") and not verify_password(admin_password, existing["password_hash"]):
                upd["password_hash"] = hash_password(admin_password)
            await db.users.update_one({"_id": existing["_id"]}, {"$set": upd})
        admin_doc = await db.users.find_one({"email": admin_email})
        if admin_doc and not await db.companies.find_one({"user_id": str(admin_doc["_id"])}):
            await db.companies.insert_one({
                "user_id": str(admin_doc["_id"]), "name": "CEO AI (Admin)",
                "region": "PT", "currency": "EUR", "sector": "", "employees_count": 0,
                "clients_count": 0, "bank_balance": 0, "monthly_tax_estimate": 0,
                "profile": {}, "created_at": datetime.now(timezone.utc).isoformat()})
        if admin_doc and not await db.ceo_dna.find_one({"user_id": str(admin_doc["_id"])}):
            await db.ceo_dna.insert_one({
                "user_id": str(admin_doc["_id"]), "completed": True, "answers": {},
                "dream": "", "target_revenue": 0, "work_hours": "", "exit_plan": "",
                "five_year_vision": "", "ceo_mode": "crescimento",
                "created_at": datetime.now(timezone.utc).isoformat()})
    try:
        init_storage()
        logger.info("Storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")
    try:
        scheduler = AsyncIOScheduler(timezone="UTC")
        scheduler.add_job(send_daily_briefings, CronTrigger(hour=7, minute=0), id="daily_briefings", replace_existing=True)
        scheduler.add_job(send_monthly_value_alerts, CronTrigger(day=1, hour=8, minute=0), id="monthly_value_alerts", replace_existing=True)
        scheduler.start()
        logger.info("Briefing scheduler started")
    except Exception as e:
        logger.error(f"Scheduler start failed: {e}")
    try:
        if (os.environ.get("STRIPE_MODE") == "live") and (os.environ.get("STRIPE_SECRET_KEY", "").startswith("sk_live")):
            import asyncio as _asyncio, setup_stripe
            _asyncio.create_task(_asyncio.to_thread(setup_stripe.main))
            logger.info("Stripe LIVE catalog ensure scheduled")
    except Exception as e:
        logger.error(f"Stripe catalog ensure failed: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
