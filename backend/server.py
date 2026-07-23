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

from core import db, client, hash_password, verify_password, init_storage, send_daily_briefings, logger
from routers import auth, companies, finance, ceo, documents, billing, misc, voice

app = FastAPI()
api_router = APIRouter(prefix="/api")
for _m in (auth, companies, finance, ceo, documents, billing, misc, voice):
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
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@example.com").lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one({"email": admin_email, "password_hash": hash_password(admin_password),
                                   "name": "Diego", "role": "owner", "auth_provider": "email", "picture": "", "is_premium": False,
                                   "created_at": datetime.now(timezone.utc).isoformat()})
    elif existing.get("password_hash") and not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_password)}})
    try:
        init_storage()
        logger.info("Storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")
    try:
        scheduler = AsyncIOScheduler(timezone="UTC")
        scheduler.add_job(send_daily_briefings, CronTrigger(hour=7, minute=0), id="daily_briefings", replace_existing=True)
        scheduler.start()
        logger.info("Briefing scheduler started")
    except Exception as e:
        logger.error(f"Scheduler start failed: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
