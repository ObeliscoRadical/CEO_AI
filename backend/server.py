from dotenv import load_dotenv
from pathlib import Path
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, UploadFile, File, Form, Header, Query
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime, timezone, timedelta
import logging, uuid, jwt, bcrypt, io, json, requests, random, stripe, httpx, hashlib
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone

# ---------------------------------------------------------------- DB
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------- config
JWT_ALGORITHM = "HS256"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
APP_NAME = "ceo-ai"
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY") or "sk_test_emergent"
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
EMAIL_BASE_URL = "https://integrations.emergentagent.com"
EMAIL_KEY = os.environ.get("EMERGENT_EMAIL_KEY")
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "CEO AI")

MODEL_MAP = {
    "claude": ("anthropic", "claude-opus-4-7"),
    "gpt": ("openai", "gpt-5.5"),
    "gemini": ("gemini", "gemini-3.1-pro-preview"),
}
CURRENCY_SYMBOL = {"EUR": "€", "BRL": "R$", "USD": "$"}

# ---------------------------------------------------------------- auth helpers
def get_jwt_secret() -> str:
    return os.environ["JWT_SECRET"]

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

def create_access_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email, "exp": datetime.now(timezone.utc) + timedelta(days=7), "type": "access"}
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)

def set_auth_cookie(response: Response, token: str):
    response.set_cookie(key="access_token", value=token, httponly=True, secure=True,
                        samesite="none", max_age=604800, path="/")

async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="Utilizador não encontrado")
        user["id"] = str(user["_id"])
        user["is_premium"] = bool(user.get("is_premium"))
        user.pop("_id", None)
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Sessão expirada")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

async def is_premium(user_id: str) -> bool:
    u = await db.users.find_one({"_id": ObjectId(user_id)})
    return bool(u and u.get("is_premium"))

# ---------------------------------------------------------------- company resolution
async def resolve_company(user_id: str, company_id: Optional[str] = None):
    if company_id:
        c = await db.companies.find_one({"_id": ObjectId(company_id), "user_id": user_id})
        if c:
            return c
    s = await db.settings.find_one({"user_id": user_id}) or {}
    acid = s.get("active_company_id")
    if acid:
        c = await db.companies.find_one({"_id": ObjectId(acid), "user_id": user_id})
        if c:
            return c
    return await db.companies.find_one({"user_id": user_id})

async def active_company_id(user_id: str) -> Optional[str]:
    c = await resolve_company(user_id)
    if not c:
        return None
    cid = str(c["_id"])
    # migrate orphan entries to the active company (one-time, cheap)
    await db.entries.update_many({"user_id": user_id, "company_id": {"$exists": False}},
                                 {"$set": {"company_id": cid}})
    return cid

# ---------------------------------------------------------------- models
class RegisterInput(BaseModel):
    email: EmailStr
    password: str
    name: str

class LoginInput(BaseModel):
    email: EmailStr
    password: str

class CompanyInput(BaseModel):
    name: str
    region: str = "PT"
    currency: str = "EUR"
    sector: str = ""
    employees_count: int = 0
    clients_count: int = 0
    bank_balance: float = 0
    monthly_tax_estimate: float = 0

class DNAInput(BaseModel):
    answers: Dict[str, Any]
    dream: str = ""
    target_revenue: float = 0
    work_hours: str = ""
    exit_plan: str = ""
    five_year_vision: str = ""
    ceo_mode: str = "crescimento"

class EntryInput(BaseModel):
    type: str
    category: str
    amount: float
    date: str
    description: str = ""

class MemoryInput(BaseModel):
    content: str
    category: str = "geral"

class SettingsInput(BaseModel):
    ceo_mode: Optional[str] = None
    theme: Optional[str] = None
    briefing_count: Optional[int] = None
    briefing_tone: Optional[str] = None
    model: Optional[str] = None
    monitored_widgets: Optional[List[str]] = None
    email_briefing: Optional[bool] = None

class ChatInput(BaseModel):
    session_id: Optional[str] = None
    message: str

class SimInput(BaseModel):
    scenario: str
    detail: str = ""

class ActiveCompanyInput(BaseModel):
    company_id: str

class CheckoutRequest(BaseModel):
    lookup_key: str
    origin_url: str

class OriginRequest(BaseModel):
    origin_url: str = ""

class ContactInput(BaseModel):
    name: str
    email: EmailStr
    message: str

class DecisionActInput(BaseModel):
    key: str
    title: str = ""
    status: str  # done | snoozed

# ---------------------------------------------------------------- storage
storage_key = None
def init_storage():
    global storage_key
    if storage_key:
        return storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    storage_key = resp.json()["storage_key"]
    return storage_key

def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    resp = requests.put(f"{STORAGE_URL}/objects/{path}",
                        headers={"X-Storage-Key": key, "Content-Type": content_type}, data=data, timeout=120)
    resp.raise_for_status()
    return resp.json()

# ---------------------------------------------------------------- auth routes
@api_router.post("/auth/register")
async def register(inp: RegisterInput, response: Response):
    email = inp.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email já registado")
    doc = {"email": email, "password_hash": hash_password(inp.password), "name": inp.name,
           "role": "owner", "auth_provider": "email", "picture": "", "is_premium": False,
           "created_at": datetime.now(timezone.utc).isoformat()}
    res = await db.users.insert_one(doc)
    uid = str(res.inserted_id)
    set_auth_cookie(response, create_access_token(uid, email))
    return {"id": uid, "email": email, "name": inp.name, "role": "owner", "is_premium": False}

@api_router.post("/auth/login")
async def login(inp: LoginInput, response: Response):
    email = inp.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not user.get("password_hash") or not verify_password(inp.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    uid = str(user["_id"])
    set_auth_cookie(response, create_access_token(uid, email))
    return {"id": uid, "email": email, "name": user.get("name", ""), "role": user.get("role", "owner"),
            "is_premium": bool(user.get("is_premium"))}

@api_router.post("/auth/session")
async def google_session(response: Response, x_session_id: str = Header(None)):
    if not x_session_id:
        raise HTTPException(status_code=400, detail="Sem session_id")
    r = requests.get("https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                     headers={"X-Session-ID": x_session_id}, timeout=30)
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Sessão Google inválida")
    data = r.json()
    email = data["email"].lower()
    user = await db.users.find_one({"email": email})
    if not user:
        doc = {"email": email, "password_hash": "", "name": data.get("name", email),
               "role": "owner", "auth_provider": "google", "picture": data.get("picture", ""), "is_premium": False,
               "created_at": datetime.now(timezone.utc).isoformat()}
        res = await db.users.insert_one(doc)
        uid = str(res.inserted_id)
    else:
        uid = str(user["_id"])
    set_auth_cookie(response, create_access_token(uid, email))
    return {"id": uid, "email": email, "name": data.get("name", email), "picture": data.get("picture", "")}

@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}

@api_router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user

# ---------------------------------------------------------------- companies (multi)
def _company_out(c):
    return {"id": str(c["_id"]), "name": c.get("name"), "region": c.get("region"), "currency": c.get("currency"),
            "sector": c.get("sector", ""), "employees_count": c.get("employees_count", 0),
            "clients_count": c.get("clients_count", 0), "bank_balance": c.get("bank_balance", 0),
            "monthly_tax_estimate": c.get("monthly_tax_estimate", 0), "bank_connected": c.get("bank_connected", False)}

@api_router.get("/companies")
async def list_companies(user: dict = Depends(get_current_user)):
    cs = await db.companies.find({"user_id": user["id"]}).to_list(100)
    active = await active_company_id(user["id"])
    return {"companies": [_company_out(c) for c in cs], "active_company_id": active}

@api_router.post("/companies")
async def create_company(inp: CompanyInput, user: dict = Depends(get_current_user)):
    data = inp.model_dump()
    data.update({"user_id": user["id"], "created_at": datetime.now(timezone.utc).isoformat()})
    res = await db.companies.insert_one(data)
    cid = str(res.inserted_id)
    await db.settings.update_one({"user_id": user["id"]}, {"$set": {"active_company_id": cid}}, upsert=True)
    data["_id"] = res.inserted_id
    return _company_out(data)

@api_router.put("/companies/active")
async def set_active_company(inp: ActiveCompanyInput, user: dict = Depends(get_current_user)):
    c = await db.companies.find_one({"_id": ObjectId(inp.company_id), "user_id": user["id"]})
    if not c:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    await db.settings.update_one({"user_id": user["id"]}, {"$set": {"active_company_id": inp.company_id}}, upsert=True)
    return {"active_company_id": inp.company_id}

@api_router.delete("/companies/{company_id}")
async def delete_company(company_id: str, user: dict = Depends(get_current_user)):
    await db.companies.delete_one({"_id": ObjectId(company_id), "user_id": user["id"]})
    await db.entries.delete_many({"user_id": user["id"], "company_id": company_id})
    s = await db.settings.find_one({"user_id": user["id"]}) or {}
    if s.get("active_company_id") == company_id:
        other = await db.companies.find_one({"user_id": user["id"]})
        await db.settings.update_one({"user_id": user["id"]},
                                     {"$set": {"active_company_id": str(other["_id"]) if other else None}}, upsert=True)
    return {"ok": True}

@api_router.get("/company")
async def get_company(user: dict = Depends(get_current_user)):
    c = await resolve_company(user["id"])
    return _company_out(c) if c else None

@api_router.post("/company")
async def save_company(inp: CompanyInput, user: dict = Depends(get_current_user)):
    existing = await resolve_company(user["id"])
    data = inp.model_dump()
    data["user_id"] = user["id"]
    if existing:
        await db.companies.update_one({"_id": existing["_id"]}, {"$set": data})
        cid = str(existing["_id"])
    else:
        data["created_at"] = datetime.now(timezone.utc).isoformat()
        res = await db.companies.insert_one(data)
        cid = str(res.inserted_id)
        await db.settings.update_one({"user_id": user["id"]}, {"$set": {"active_company_id": cid}}, upsert=True)
    return {"id": cid, **inp.model_dump()}

# ---------------------------------------------------------------- CEO DNA
@api_router.get("/dna")
async def get_dna(user: dict = Depends(get_current_user)):
    d = await db.ceo_dna.find_one({"user_id": user["id"]})
    if not d:
        return {"completed": False}
    d["id"] = str(d["_id"]); d.pop("_id")
    return d

@api_router.post("/dna")
async def save_dna(inp: DNAInput, user: dict = Depends(get_current_user)):
    data = inp.model_dump()
    data.update({"user_id": user["id"], "completed": True})
    await db.ceo_dna.update_one({"user_id": user["id"]}, {"$set": data}, upsert=True)
    await db.settings.update_one({"user_id": user["id"]}, {"$set": {"ceo_mode": inp.ceo_mode}}, upsert=True)
    mems = []
    if inp.dream: mems.append(("sonho", inp.dream))
    if inp.target_revenue: mems.append(("objetivo", f"Quer faturar {inp.target_revenue}"))
    if inp.five_year_vision: mems.append(("visao", inp.five_year_vision))
    for cat, content in mems:
        await db.memories.update_one({"user_id": user["id"], "category": cat},
                                     {"$set": {"content": content, "user_id": user["id"], "category": cat,
                                               "created_at": datetime.now(timezone.utc).isoformat()}}, upsert=True)
    return {"completed": True}

# ---------------------------------------------------------------- entries
@api_router.get("/entries")
async def list_entries(user: dict = Depends(get_current_user)):
    cid = await active_company_id(user["id"])
    entries = await db.entries.find({"user_id": user["id"], "company_id": cid}).sort("date", -1).to_list(2000)
    for e in entries:
        e["id"] = str(e["_id"]); e.pop("_id")
    return entries

@api_router.post("/entries")
async def create_entry(inp: EntryInput, user: dict = Depends(get_current_user)):
    cid = await active_company_id(user["id"])
    data = inp.model_dump()
    data.update({"user_id": user["id"], "company_id": cid, "created_at": datetime.now(timezone.utc).isoformat()})
    res = await db.entries.insert_one(data)
    await invalidate_ai_cache(user["id"])
    return {"id": str(res.inserted_id), **inp.model_dump()}

@api_router.delete("/entries/{entry_id}")
async def delete_entry(entry_id: str, user: dict = Depends(get_current_user)):
    await db.entries.delete_one({"_id": ObjectId(entry_id), "user_id": user["id"]})
    await invalidate_ai_cache(user["id"])
    return {"ok": True}

@api_router.post("/entries/import")
async def import_csv(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    cid = await active_company_id(user["id"])
    raw = (await file.read()).decode("utf-8", errors="ignore")
    prompt = (
        "Analisa este ficheiro CSV/Excel de dados financeiros e devolve APENAS um array JSON válido. "
        "Cada objeto: {\"type\":\"income\"|\"expense\",\"category\":str,\"amount\":number,\"date\":\"YYYY-MM-DD\",\"description\":str}. "
        "Interpreta colunas em qualquer idioma. Valores negativos ou palavras como despesa/custo/pagamento => expense; "
        "receita/venda/entrada => income. Não incluas texto fora do JSON.\n\nCSV:\n" + raw[:6000]
    )
    chat = LlmChat(api_key=EMERGENT_KEY, session_id=f"import-{uuid.uuid4()}",
                   system_message="És um analista financeiro que estrutura dados. Respondes só com JSON.").with_model("openai", "gpt-5.4")
    resp = await chat.send_message(UserMessage(text=prompt))
    text = resp.strip()
    if "```" in text:
        text = text.split("```")[1].replace("json", "", 1).strip()
    try:
        rows = json.loads(text)
    except Exception:
        raise HTTPException(status_code=422, detail="Não foi possível interpretar o ficheiro")
    inserted = 0
    for r in rows if isinstance(rows, list) else []:
        try:
            await db.entries.insert_one({"user_id": user["id"], "company_id": cid,
                "type": r.get("type", "expense"), "category": str(r.get("category", "Outro")),
                "amount": float(r.get("amount", 0)), "date": str(r.get("date", datetime.now(timezone.utc).date().isoformat())),
                "description": str(r.get("description", "")), "created_at": datetime.now(timezone.utc).isoformat()})
            inserted += 1
        except Exception:
            continue
    await invalidate_ai_cache(user["id"])
    return {"imported": inserted}

# ---------------------------------------------------------------- mock bank connect
@api_router.post("/bank/connect")
async def bank_connect(user: dict = Depends(get_current_user)):
    cid = await active_company_id(user["id"])
    if not cid:
        raise HTTPException(status_code=400, detail="Cria uma empresa primeiro")
    now = datetime.now(timezone.utc)
    cats_in = ["Vendas", "Serviços", "Consultoria", "Subscrições"]
    cats_out = ["Salários", "Renda", "Fornecedores", "Marketing", "Software", "Impostos"]
    created = 0
    for m in range(6):
        d = (now - timedelta(days=30 * m))
        for _ in range(random.randint(3, 5)):
            await db.entries.insert_one({"user_id": user["id"], "company_id": cid, "type": "income",
                "category": random.choice(cats_in), "amount": round(random.uniform(1500, 9000), 2),
                "date": d.replace(day=random.randint(1, 28)).date().isoformat(),
                "description": "Movimento bancário (demo)", "created_at": now.isoformat()})
            created += 1
        for _ in range(random.randint(3, 6)):
            await db.entries.insert_one({"user_id": user["id"], "company_id": cid, "type": "expense",
                "category": random.choice(cats_out), "amount": round(random.uniform(400, 5000), 2),
                "date": d.replace(day=random.randint(1, 28)).date().isoformat(),
                "description": "Movimento bancário (demo)", "created_at": now.isoformat()})
            created += 1
    await db.companies.update_one({"_id": ObjectId(cid)}, {"$set": {"bank_connected": True}})
    await invalidate_ai_cache(user["id"])
    return {"connected": True, "imported": created}

# ---------------------------------------------------------------- snapshot / dashboard
def rag(value, good, warn, reverse=False):
    if reverse:
        if value <= good: return "green"
        if value <= warn: return "amber"
        return "red"
    if value >= good: return "green"
    if value >= warn: return "amber"
    return "red"

async def build_snapshot(user_id: str):
    company = await resolve_company(user_id) or {}
    cid = str(company["_id"]) if company.get("_id") else None
    entries = await db.entries.find({"user_id": user_id, "company_id": cid}, {"type": 1, "amount": 1, "date": 1, "category": 1}).to_list(5000) if cid else []
    now = datetime.now(timezone.utc)
    month_key = now.strftime("%Y-%m")
    income = sum(e["amount"] for e in entries if e["type"] == "income")
    expense = sum(e["amount"] for e in entries if e["type"] == "expense")
    m_income = sum(e["amount"] for e in entries if e["type"] == "income" and str(e.get("date", "")).startswith(month_key))
    m_expense = sum(e["amount"] for e in entries if e["type"] == "expense" and str(e.get("date", "")).startswith(month_key))
    net = income - expense
    m_net = m_income - m_expense
    bank = float(company.get("bank_balance", 0)) + net
    monthly_burn = m_expense if m_expense > 0 else (expense / 12 if expense else 1)
    runway = bank / monthly_burn if monthly_burn > 0 else 99
    profit_margin = (m_net / m_income * 100) if m_income > 0 else 0
    tax_reserve = float(company.get("monthly_tax_estimate", 0))
    payroll = sum(e["amount"] for e in entries if e["type"] == "expense" and "salári" in str(e.get("category", "")).lower())
    currency = company.get("currency", "EUR")

    vitals = [
        {"key": "cashflow", "label": "Fluxo de Caixa", "value": round(m_net, 2), "unit": CURRENCY_SYMBOL.get(currency, "€"),
         "status": rag(m_net, 0.01, -monthly_burn * 0.5), "hint": "Entradas menos saídas este mês"},
        {"key": "profit", "label": "Lucro", "value": round(profit_margin, 1), "unit": "%",
         "status": rag(profit_margin, 10, 3), "hint": "Margem de lucro mensal"},
        {"key": "clients", "label": "Clientes", "value": int(company.get("clients_count", 0)), "unit": "",
         "status": rag(company.get("clients_count", 0), 10, 3), "hint": "Base de clientes ativa"},
        {"key": "tax", "label": "Impostos", "value": round(tax_reserve, 2), "unit": CURRENCY_SYMBOL.get(currency, "€"),
         "status": rag(bank - tax_reserve, 0.01, -1), "hint": "Reserva vs estimativa fiscal"},
        {"key": "employees", "label": "Funcionários", "value": int(company.get("employees_count", 0)), "unit": "",
         "status": rag(m_income - payroll, 0.01, -1) if payroll else "green", "hint": "Custo de equipa sustentável"},
        {"key": "bank", "label": "Banco", "value": round(bank, 2), "unit": CURRENCY_SYMBOL.get(currency, "€"),
         "status": rag(bank, monthly_burn * 3, 0), "hint": "Saldo bancário estimado"},
        {"key": "risk", "label": "Risco", "value": round(runway, 1), "unit": "meses",
         "status": rag(runway, 6, 3), "hint": "Meses de autonomia de caixa"},
    ]
    status_score = {"green": 100, "amber": 55, "red": 20}
    health = round(sum(status_score[v["status"]] for v in vitals) / len(vitals))
    annual_profit = net if net > 0 else 0
    company_value = round(bank + annual_profit * 3, 2)
    dna = await db.ceo_dna.find_one({"user_id": user_id}) or {}
    goal_value = float(dna.get("target_revenue", 0)) or 1000000
    progress = min(100, round(company_value / goal_value * 100)) if goal_value else 0

    return {
        "health": health, "vitals": vitals, "currency": currency,
        "currency_symbol": CURRENCY_SYMBOL.get(currency, "€"),
        "company_name": company.get("name", "A minha empresa"),
        "company_value": company_value, "goal_value": goal_value, "progress": progress,
        "cash_balance": round(bank, 2), "monthly_net": round(m_net, 2),
        "monthly_income": round(m_income, 2), "monthly_expense": round(m_expense, 2),
        "runway": round(runway, 1), "profit_margin": round(profit_margin, 1),
        "total_income": round(income, 2), "total_expense": round(expense, 2),
    }

@api_router.get("/dashboard")
async def dashboard(user: dict = Depends(get_current_user)):
    return await build_snapshot(user["id"])

# ---------------------------------------------------------------- CEO Score
@api_router.get("/score")
async def ceo_score(user: dict = Depends(get_current_user)):
    snap = await build_snapshot(user["id"])
    dna = await db.ceo_dna.find_one({"user_id": user["id"]}) or {}
    company = await resolve_company(user["id"]) or {}
    cid = str(company["_id"]) if company.get("_id") else None
    n_entries = await db.entries.count_documents({"user_id": user["id"], "company_id": cid}) if cid else 0
    dims = [
        {"dimension": "Liderança", "score": 80 if dna.get("completed") else 40},
        {"dimension": "Financeiro", "score": snap["health"]},
        {"dimension": "Marketing", "score": min(100, 30 + company.get("clients_count", 0) * 4)},
        {"dimension": "Operação", "score": 70 if n_entries else 35},
        {"dimension": "Clientes", "score": min(100, 40 + company.get("clients_count", 0) * 5)},
        {"dimension": "Funcionários", "score": min(100, 50 + company.get("employees_count", 0) * 6)},
        {"dimension": "Risco", "score": min(100, int(snap["runway"] * 12))},
        {"dimension": "Inovação", "score": 60 if dna.get("five_year_vision") else 30},
    ]
    overall = round(sum(d["score"] for d in dims) / len(dims))
    return {"overall": overall, "dimensions": dims}

# ---------------------------------------------------------------- memory / settings
@api_router.get("/memories")
async def list_memories(user: dict = Depends(get_current_user)):
    mems = await db.memories.find({"user_id": user["id"]}).sort("created_at", -1).to_list(500)
    for m in mems:
        m["id"] = str(m["_id"]); m.pop("_id")
    return mems

@api_router.post("/memories")
async def add_memory(inp: MemoryInput, user: dict = Depends(get_current_user)):
    doc = {"user_id": user["id"], "content": inp.content, "category": inp.category,
           "created_at": datetime.now(timezone.utc).isoformat()}
    res = await db.memories.insert_one(doc)
    return {"id": str(res.inserted_id), **inp.model_dump()}

@api_router.delete("/memories/{mem_id}")
async def del_memory(mem_id: str, user: dict = Depends(get_current_user)):
    await db.memories.delete_one({"_id": ObjectId(mem_id), "user_id": user["id"]})
    return {"ok": True}

DEFAULT_SETTINGS = {"ceo_mode": "crescimento", "theme": "dark", "briefing_count": 4,
                    "briefing_tone": "direto", "model": "claude", "email_briefing": False,
                    "monitored_widgets": ["cashflow", "profit", "clients", "tax", "employees", "bank", "risk"]}

@api_router.get("/settings")
async def get_settings(user: dict = Depends(get_current_user)):
    s = await db.settings.find_one({"user_id": user["id"]}) or {}
    s.pop("_id", None); s.pop("user_id", None); s.pop("active_company_id", None)
    return {**DEFAULT_SETTINGS, **s}

@api_router.put("/settings")
async def update_settings(inp: SettingsInput, user: dict = Depends(get_current_user)):
    data = {k: v for k, v in inp.model_dump().items() if v is not None}
    await db.settings.update_one({"user_id": user["id"]}, {"$set": data}, upsert=True)
    s = await db.settings.find_one({"user_id": user["id"]}) or {}
    s.pop("_id", None); s.pop("user_id", None); s.pop("active_company_id", None)
    return {**DEFAULT_SETTINGS, **s}

# ---------------------------------------------------------------- CEO context
MODE_PROMPTS = {
    "conservador": "És prudente e avesso ao risco. Priorizas estabilidade, reservas de caixa e evitas dívida.",
    "crescimento": "És focado em crescimento sustentável. Equilibras oportunidade e risco.",
    "agressivo": "És ambicioso e orientado a resultados rápidos. Aceitas mais risco por retorno maior.",
    "familiar": "És equilibrado, valorizas qualidade de vida, tempo com a família e sustentabilidade do negócio.",
    "startup": "És orientado a escala, produto e captação. Pensas em métricas de crescimento e runway.",
    "investidor": "Pensas como investidor: retorno sobre capital, valor da empresa e saída (exit).",
}

async def build_system_prompt(user_id: str, user_name: str):
    settings = await db.settings.find_one({"user_id": user_id}) or {}
    mode = settings.get("ceo_mode", "crescimento")
    tone = settings.get("briefing_tone", "direto")
    dna = await db.ceo_dna.find_one({"user_id": user_id}) or {}
    memories = await db.memories.find({"user_id": user_id}).to_list(100)
    snap = await build_snapshot(user_id)
    mem_txt = "\n".join(f"- {m['content']}" for m in memories) or "- (ainda sem memórias registadas)"
    vitals_txt = "\n".join(f"- {v['label']}: {v['value']}{v['unit']} [{v['status']}]" for v in snap["vitals"])
    return (
        f"És o CEO AI — o Diretor Executivo Digital de {user_name}. NÃO és um chatbot nem um assistente técnico: "
        f"és um CEO experiente que já geriu centenas de empresas e que agora toma decisões LADO A LADO com este empresário. "
        f"A tua personalidade é experiente, calma, objectiva e confiante. {MODE_PROMPTS.get(mode, MODE_PROMPTS['crescimento'])} Tom: {tone}.\n\n"
        f"### COMO RESPONDES (obrigatório)\n"
        f"NUNCA respondas apenas com teoria e NUNCA digas 'depende'. Respondes sempre como um consultor executivo de topo, "
        f"tomando posição. Estrutura natural de cada resposta (sem cabeçalhos rígidos, de forma fluida e humana):\n"
        f"1) O QUE EU FARIA — a decisão concreta, na primeira pessoa e directa.\n"
        f"2) PORQUÊ — o raciocínio ligado aos números reais e aos objectivos pessoais do empresário.\n"
        f"3) RISCOS — o que pode correr mal.\n"
        f"4) ALTERNATIVAS — 1 ou 2 caminhos possíveis.\n"
        f"Foca-te no FUTURO e nas decisões, não no passado. Sê conciso, calmo e confiante. Fala português europeu.\n\n"
        f"### PERFIL (CEO DNA)\n"
        f"Sonho: {dna.get('dream', 'n/d')}\nFaturação desejada: {dna.get('target_revenue', 'n/d')}\n"
        f"Horas de trabalho: {dna.get('work_hours', 'n/d')}\nPlano de saída: {dna.get('exit_plan', 'n/d')}\n"
        f"Visão a 5 anos: {dna.get('five_year_vision', 'n/d')}\n\n"
        f"### MEMÓRIA (lembra-te disto sempre)\n{mem_txt}\n\n"
        f"### ESTADO ATUAL DA EMPRESA ({snap['company_name']})\n"
        f"Saúde: {snap['health']}/100\nCaixa: {snap['currency_symbol']}{snap['cash_balance']}\n"
        f"Resultado mensal: {snap['currency_symbol']}{snap['monthly_net']}\nAutonomia: {snap['runway']} meses\n"
        f"Valor da empresa: {snap['currency_symbol']}{snap['company_value']} (objetivo {snap['currency_symbol']}{snap['goal_value']}, {snap['progress']}%)\n"
        f"Sinais vitais:\n{vitals_txt}"
    )

async def get_chat(user_id: str, user_name: str, session_id: str):
    settings = await db.settings.find_one({"user_id": user_id}) or {}
    provider, model = MODEL_MAP.get(settings.get("model", "claude"), MODEL_MAP["claude"])
    sysmsg = await build_system_prompt(user_id, user_name)
    if provider == "anthropic":
        chat = LlmChat(api_key=EMERGENT_KEY, session_id=session_id, system_message=sysmsg,
                       custom_headers={"anthropic-beta": "task-budgets-2026-03-13"}).with_model(provider, model)
        chat = chat.with_params(extra_body={"output_config": {"task_budget": {"type": "tokens", "total": 200000}, "effort": "high"}}, max_tokens=8000)
    else:
        chat = LlmChat(api_key=EMERGENT_KEY, session_id=session_id, system_message=sysmsg).with_model(provider, model)
    return chat

# ---------------------------------------------------------------- chat
@api_router.get("/chat/sessions")
async def chat_sessions(user: dict = Depends(get_current_user)):
    sess = await db.chat_sessions.find({"user_id": user["id"], "session_id": {"$exists": True}}).sort("created_at", -1).to_list(100)
    return [{"session_id": s.get("session_id"), "title": s.get("title", "Conversa"), "created_at": s.get("created_at")}
            for s in sess if s.get("session_id")]

@api_router.get("/chat/{session_id}/messages")
async def chat_messages(session_id: str, user: dict = Depends(get_current_user)):
    msgs = await db.chat_messages.find({"session_id": session_id, "user_id": user["id"]}).sort("created_at", 1).to_list(1000)
    return [{"role": m["role"], "content": m["content"]} for m in msgs]

@api_router.delete("/chat/{session_id}")
async def delete_session(session_id: str, user: dict = Depends(get_current_user)):
    await db.chat_sessions.delete_one({"session_id": session_id, "user_id": user["id"]})
    await db.chat_messages.delete_many({"session_id": session_id, "user_id": user["id"]})
    return {"ok": True}

@api_router.post("/chat")
async def chat(inp: ChatInput, user: dict = Depends(get_current_user)):
    session_id = inp.session_id
    if not session_id:
        session_id = str(uuid.uuid4())
        await db.chat_sessions.insert_one({"session_id": session_id, "user_id": user["id"],
                                           "title": inp.message[:50], "created_at": datetime.now(timezone.utc).isoformat()})
    history = await db.chat_messages.find({"session_id": session_id, "user_id": user["id"]}).sort("created_at", 1).to_list(1000)
    await db.chat_messages.insert_one({"session_id": session_id, "user_id": user["id"], "role": "user",
                                       "content": inp.message, "created_at": datetime.now(timezone.utc).isoformat()})
    chat_obj = await get_chat(user["id"], user.get("name", ""), session_id)
    context_msg = inp.message
    if history:
        hist_txt = "\n".join(f"{h['role']}: {h['content']}" for h in history[-10:])
        context_msg = f"[Histórico da conversa]\n{hist_txt}\n\n[Nova mensagem do empresário]\n{inp.message}"

    async def gen():
        full = ""
        try:
            async for ev in chat_obj.stream_message(UserMessage(text=context_msg)):
                if isinstance(ev, TextDelta):
                    full += ev.content
                    yield f"data: {json.dumps({'delta': ev.content})}\n\n"
                elif isinstance(ev, StreamDone):
                    break
        except Exception as e:
            logger.error(f"chat error: {e}")
            yield f"data: {json.dumps({'delta': ' [erro de ligação com o CEO AI]'})}\n\n"
        await db.chat_messages.insert_one({"session_id": session_id, "user_id": user["id"], "role": "assistant",
                                           "content": full, "created_at": datetime.now(timezone.utc).isoformat()})
        yield f"data: {json.dumps({'done': True, 'session_id': session_id})}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

# ---------------------------------------------------------------- briefing
async def make_briefing(user_id: str, user_name: str):
    settings = await db.settings.find_one({"user_id": user_id}) or {}
    count = settings.get("briefing_count", 4)
    snap = await build_snapshot(user_id)
    sysmsg = await build_system_prompt(user_id, user_name)
    hour = datetime.now(timezone.utc).hour
    greeting = "Bom dia" if hour < 12 else ("Boa tarde" if hour < 19 else "Boa noite")
    prompt = (
        f"Gera o briefing diário para o empresário. Devolve APENAS JSON válido no formato: "
        f'{{"greeting":"{greeting}, <nome>. ...","items":[{{"title":str,"detail":str,"priority":"alta"|"media"|"baixa","icon":"cash"|"profit"|"clients"|"tax"|"risk"|"opportunity"}}]}}. '
        f"Exatamente {count} itens, priorizados pelo que mais importa hoje. "
        f"O greeting deve ser uma frase humana e calorosa a começar com '{greeting}'. Detalhes curtos, orientados ao futuro e à ação. Sem texto fora do JSON."
    )
    chat = LlmChat(api_key=EMERGENT_KEY, session_id=f"brief-{uuid.uuid4()}", system_message=sysmsg).with_model("openai", "gpt-5.4")
    try:
        resp = await chat.send_message(UserMessage(text=prompt))
        text = resp.strip()
        if "```" in text:
            text = text.split("```")[1].replace("json", "", 1).strip()
        data = json.loads(text)
    except Exception as e:
        logger.error(f"briefing error: {e}")
        data = {"greeting": f"{greeting}, {user_name}. Aqui está o que precisa da sua atenção hoje.",
                "items": [{"title": "Ligue os seus dados", "detail": "Registe receitas e despesas para eu analisar a saúde da sua empresa.",
                           "priority": "alta", "icon": "opportunity"}]}
    data["health"] = snap["health"]
    return data

@api_router.get("/briefing")
async def briefing(user: dict = Depends(get_current_user)):
    return await make_briefing(user["id"], user.get("name", ""))

# ---------------------------------------------------------------- briefing email
PRIORITY_COLOR = {"alta": "#EF4444", "media": "#F59E0B", "baixa": "#10B981"}

def build_briefing_html(name: str, data: dict, app_url: str):
    rows = ""
    for it in data.get("items", []):
        pc = PRIORITY_COLOR.get(it.get("priority", "media"), "#F59E0B")
        rows += f"""
        <tr><td style="padding:0 0 14px 0;">
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#faf9f6;border:1px solid #eee;border-radius:12px;">
            <tr>
              <td width="6" style="background:{pc};border-radius:12px 0 0 12px;">&nbsp;</td>
              <td style="padding:14px 18px;">
                <div style="font-size:15px;font-weight:700;color:#18181b;">{it.get('title','')}</div>
                <div style="font-size:14px;color:#52525b;margin-top:4px;line-height:1.5;">{it.get('detail','')}</div>
              </td>
            </tr>
          </table>
        </td></tr>"""
    return f"""<!DOCTYPE html><html><body style="margin:0;background:#0b0c10;font-family:Arial,Helvetica,sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#0b0c10;padding:32px 0;">
      <tr><td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:18px;overflow:hidden;">
          <tr><td style="background:#0b0c10;padding:28px 32px;">
            <div style="color:#D4AF37;font-size:22px;font-weight:700;letter-spacing:1px;">CEO&nbsp;AI</div>
            <div style="color:#a1a1aa;font-size:11px;letter-spacing:2px;text-transform:uppercase;margin-top:2px;">Executivo Digital · Briefing Diário</div>
          </td></tr>
          <tr><td style="padding:32px;">
            <div style="font-size:22px;color:#18181b;font-weight:700;line-height:1.35;margin-bottom:8px;">{data.get('greeting','Bom dia')}</div>
            <div style="font-size:13px;color:#71717a;margin-bottom:22px;">Saúde da empresa: <strong style="color:#D4AF37;">{data.get('health',0)}/100</strong></div>
            <table width="100%" cellpadding="0" cellspacing="0">{rows}</table>
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:22px;"><tr><td align="center">
              <a href="{app_url}" style="display:inline-block;background:#D4AF37;color:#0b0c10;text-decoration:none;font-weight:700;font-size:14px;padding:13px 28px;border-radius:999px;">Abrir o meu CEO AI</a>
            </td></tr></table>
          </td></tr>
          <tr><td style="padding:20px 32px;background:#faf9f6;border-top:1px solid #eee;">
            <div style="font-size:11px;color:#a1a1aa;">Recebes este email porque ativaste o briefing diário. Podes desativar em Personalização.</div>
          </td></tr>
        </table>
      </td></tr>
    </table></body></html>"""

async def send_email_raw(to_email: str, subject: str, html: str):
    if not EMAIL_KEY:
        logger.error("EMERGENT_EMAIL_KEY not set")
        return False
    payload = {"to": [to_email], "subject": subject, "html": html, "from_name": EMAIL_FROM_NAME}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{EMAIL_BASE_URL}/api/v1/email/send",
                                     headers={"X-Email-Key": EMAIL_KEY}, json=payload)
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"email send error: {e}")
        return False

@api_router.post("/briefing/email")
async def send_briefing_email(request: Request, user: dict = Depends(get_current_user)):
    data = await make_briefing(user["id"], user.get("name", ""))
    app_url = request.headers.get("origin") or os.environ.get("FRONTEND_URL", "")
    html = build_briefing_html(user.get("name", ""), data, app_url)
    ok = await send_email_raw(user["email"], "O teu briefing diário — CEO AI", html)
    if not ok:
        raise HTTPException(502, "Não foi possível enviar o email")
    return {"sent": True, "to": user["email"]}

async def send_daily_briefings():
    today = datetime.now(timezone.utc).date().isoformat()
    cursor = db.settings.find({"email_briefing": True})
    async for s in cursor:
        uid = s.get("user_id")
        if not uid:
            continue
        claim = await db.settings.update_one(
            {"user_id": uid, "email_briefing": True, "last_briefing_email_date": {"$ne": today}},
            {"$set": {"last_briefing_email_date": today}})
        if claim.modified_count != 1:
            continue
        try:
            u = await db.users.find_one({"_id": ObjectId(uid)})
            if not u:
                continue
            data = await make_briefing(uid, u.get("name", ""))
            html = build_briefing_html(u.get("name", ""), data, os.environ.get("FRONTEND_URL", ""))
            await send_email_raw(u["email"], "O teu briefing diário — CEO AI", html)
        except Exception as e:
            logger.error(f"daily briefing error for {uid}: {e}")

# ---------------------------------------------------------------- executive intelligence
async def ai_json(system: str, prompt: str, model=("openai", "gpt-5.4")):
    chat = LlmChat(api_key=EMERGENT_KEY, session_id=f"j-{uuid.uuid4()}", system_message=system).with_model(*model)
    try:
        resp = await chat.send_message(UserMessage(text=prompt))
        t = resp.strip()
        if "```" in t:
            t = t.split("```")[1].replace("json", "", 1).strip()
        return json.loads(t)
    except Exception as e:
        logger.error(f"ai_json error: {e}")
        return None

async def cached_ai(kind: str, uid: str, cid, system: str, prompt: str):
    today = datetime.now(timezone.utc).date().isoformat()
    q = {"kind": kind, "user_id": uid, "company_id": cid, "date": today}
    hit = await db.ai_cache.find_one(q)
    if hit and hit.get("payload"):
        return hit["payload"]
    payload = await ai_json(system, prompt)
    if payload:
        await db.ai_cache.update_one(q, {"$set": {"payload": payload, "created_at": datetime.now(timezone.utc).isoformat()}}, upsert=True)
    return payload

async def invalidate_ai_cache(uid: str):
    await db.ai_cache.delete_many({"user_id": uid})

async def _growth_score(uid: str, cid: str):
    entries = await db.entries.find({"user_id": uid, "company_id": cid}, {"type": 1, "amount": 1, "date": 1}).to_list(5000) if cid else []
    inc = {}
    for e in entries:
        mk = str(e.get("date", ""))[:7]
        if len(mk) == 7 and e["type"] == "income":
            inc[mk] = inc.get(mk, 0) + e["amount"]
    sm = sorted(inc)
    g = 50
    if len(sm) >= 2:
        recent = sum(inc[m] for m in sm[-3:]); prior = sum(inc[m] for m in sm[-6:-3])
        if prior > 0:
            g = max(5, min(100, int(60 + ((recent - prior) / prior) * 100)))
        elif recent > 0:
            g = 72
    return g

@api_router.get("/decisions")
async def decisions(user: dict = Depends(get_current_user)):
    uid = user["id"]
    cid = await active_company_id(uid)
    snap = await build_snapshot(uid)
    sysmsg = await build_system_prompt(uid, user.get("name", ""))
    prompt = (
        "Como CEO, define o veredicto de hoje e as decisões prioritárias. Devolve APENAS JSON: "
        '{"verdict":str,"decisions":[{"title":str,"why":str,"impact":str,"action":str,"urgency":"alta"|"media"|"baixa"}],'
        '"vitals_phrases":{"cashflow":str,"profit":str,"clients":str,"tax":str,"employees":str,"bank":str,"risk":str}}. '
        "O 'verdict' é 1 frase humana e directa sobre o estado hoje (sem números crus). 1 a 3 decisões concretas orientadas ao futuro, "
        "cada uma com o porquê, o impacto estimado (em € quando possível) e a acção. Em 'vitals_phrases', 1 frase-decisão curta por sinal vital. "
        "Português europeu, tom de executivo de confiança. Sem texto fora do JSON."
    )
    data = await cached_ai("decisions", uid, cid, sysmsg, prompt) or {"verdict": f"Olá {user.get('name','')}. Vamos focar no essencial hoje.", "decisions": [], "vitals_phrases": {}}
    today = datetime.now(timezone.utc).date().isoformat()
    fb = await db.decision_feedback.find({"user_id": uid, "company_id": cid, "date": today}).to_list(200)
    hidden = {f["key"] for f in fb}
    out = []
    for d in data.get("decisions", []):
        key = hashlib.md5(d.get("title", "").encode()).hexdigest()[:10]
        if key in hidden:
            continue
        d["key"] = key
        out.append(d)
    ph = data.get("vitals_phrases", {})
    for v in snap["vitals"]:
        v["phrase"] = ph.get(v["key"], v.get("hint", ""))
    return {"verdict": data.get("verdict"), "decisions": out, "vitals": snap["vitals"], "health": snap["health"],
            "company_value": snap["company_value"], "goal_value": snap["goal_value"], "progress": snap["progress"],
            "currency_symbol": snap["currency_symbol"], "company_name": snap["company_name"]}

@api_router.post("/decisions/act")
async def decisions_act(inp: DecisionActInput, user: dict = Depends(get_current_user)):
    cid = await active_company_id(user["id"])
    today = datetime.now(timezone.utc).date().isoformat()
    await db.decision_feedback.update_one(
        {"user_id": user["id"], "company_id": cid, "date": today, "key": inp.key},
        {"$set": {"status": inp.status, "title": inp.title, "updated_at": datetime.now(timezone.utc).isoformat()}}, upsert=True)
    return {"ok": True}

@api_router.get("/ceo-daily")
async def ceo_daily(user: dict = Depends(get_current_user)):
    uid = user["id"]
    cid = await active_company_id(uid)
    snap = await build_snapshot(uid)
    growth = await _growth_score(uid, cid)
    runway = snap["runway"]; m_net = snap["monthly_net"]
    treasury = ("Confortável", "green") if runway >= 6 else ("Apertada", "amber") if runway >= 3 else ("Crítica", "red")
    cashflow = ("Positivo", "green") if m_net > 0 else ("Equilibrado", "amber") if m_net == 0 else ("Negativo", "red")
    sysmsg = await build_system_prompt(uid, user.get("name", ""))
    today = datetime.now(timezone.utc).date().isoformat()
    prompt = (
        f"Hoje é {today}. Como Diretor Executivo Digital, analisaste toda a empresa. Devolve APENAS JSON: "
        '{"conclusao":{"estado_geral":str,"oportunidades":str,"problemas":str,"prioridades":str},'
        '"recomendacoes":[{"title":str,"why":str,"priority":"urgente"|"importante"|"oportunidade"}]}. '
        "Em 'conclusao', cada campo tem 1-2 frases directas e humanas. Em 'recomendacoes', dá ENTRE 3 e 6 acções concretas "
        "e personalizadas para hoje (ex: 'Cobrar o cliente X', 'Não contratar este mês', 'Aumentar o preço médio', "
        "'Negociar com o fornecedor', 'Adiar a compra de equipamento 30 dias'), cada uma com o motivo ('why', 1 frase) "
        "e a prioridade. Varia a linguagem — a análise de hoje nunca deve ser igual à de outro dia. "
        "Português europeu, tom de CEO experiente, calmo e confiante. Sem texto fora do JSON."
    )
    data = await cached_ai("ceo_daily", uid, cid, sysmsg, prompt) or {
        "conclusao": {"estado_geral": "Ainda estou a conhecer a tua empresa. Adiciona dados financeiros para uma leitura completa.",
                      "oportunidades": "—", "problemas": "—", "prioridades": "Liga o teu banco ou importa um CSV."},
        "recomendacoes": []}
    fb = await db.decision_feedback.find({"user_id": uid, "company_id": cid, "date": today}).to_list(200)
    hidden = {f["key"] for f in fb}
    recs = []
    for r in data.get("recomendacoes", []):
        key = hashlib.md5((r.get("title", "") + today).encode()).hexdigest()[:10]
        if key in hidden:
            continue
        r["key"] = key
        recs.append(r)
    return {
        "user_name": user.get("name", ""),
        "company_name": snap["company_name"],
        "conclusao": data.get("conclusao", {}),
        "recomendacoes": recs,
        "vitals": {
            "saude": {"label": "Saúde Empresarial", "value": snap["health"], "unit": "/100",
                      "status": "green" if snap["health"] >= 70 else "amber" if snap["health"] >= 45 else "red"},
            "valor": {"label": "Valor estimado", "value": snap["company_value"], "unit": snap["currency_symbol"], "status": "gold"},
            "crescimento": {"label": "Probabilidade de crescimento", "value": growth, "unit": "%",
                            "status": "green" if growth >= 65 else "amber" if growth >= 45 else "red"},
            "tesouraria": {"label": "Tesouraria", "value": treasury[0], "unit": "", "status": treasury[1]},
            "fluxo": {"label": "Fluxo de caixa", "value": cashflow[0], "unit": "", "status": cashflow[1]},
        },
        "currency_symbol": snap["currency_symbol"],
        "has_data": snap["total_income"] > 0 or snap["total_expense"] > 0,
    }


@api_router.get("/health-index")
async def health_index(user: dict = Depends(get_current_user)):
    uid = user["id"]
    snap = await build_snapshot(uid)
    company = await resolve_company(uid) or {}
    cid = str(company["_id"]) if company.get("_id") else None
    emp = int(company.get("employees_count", 0)); cli = int(company.get("clients_count", 0))
    g = await _growth_score(uid, cid)
    margin = snap["profit_margin"]; runway = snap["runway"]
    dims = {
        "Financeiro": snap["health"],
        "Clientes": min(100, 40 + cli * 5),
        "Equipa": min(100, 50 + emp * 6),
        "Dependência do Fundador": min(100, 28 + emp * 12 + (12 if cli > 5 else 0)),
        "Marca": min(100, 30 + cli * 4),
        "Liquidez": min(100, int(runway * 14)),
        "Margem": max(0, min(100, int(margin * 4) + 40)),
        "Crescimento": g,
        "Risco": min(100, int(runway * 12 + (20 if margin > 0 else 0))),
    }
    overall = round(sum(dims.values()) / len(dims))
    sysmsg = await build_system_prompt(uid, user.get("name", ""))
    prompt = (
        "Explica o índice de Saúde Empresarial. Notas actuais (0-100): " + json.dumps(dims, ensure_ascii=False) +
        '. Devolve APENAS JSON: {"summary":str,"dimensions":{"<nome exacto>":{"why":str,"improve":str,"potential":str}}}. '
        "'summary': 1-2 frases sobre a saúde global. Por dimensão: 'why' (porque tem esta nota, 1 frase), 'improve' (o que fazer, 1 frase), "
        "'potential' (quanto pode subir, ex '+15 pontos'). Português europeu. Sem texto fora do JSON."
    )
    ai = await cached_ai("health", uid, cid, sysmsg, prompt) or {}
    notes = ai.get("dimensions", {})
    out = [{"dimension": k, "score": v, "why": notes.get(k, {}).get("why", ""),
            "improve": notes.get(k, {}).get("improve", ""), "potential": notes.get(k, {}).get("potential", "")} for k, v in dims.items()]
    return {"overall": overall, "summary": ai.get("summary", ""), "dimensions": out}

@api_router.get("/valuation")
async def valuation(user: dict = Depends(get_current_user)):
    uid = user["id"]
    cid = await active_company_id(uid)
    snap = await build_snapshot(uid)
    sym = snap["currency_symbol"]; value = snap["company_value"]
    sysmsg = await build_system_prompt(uid, user.get("name", ""))
    prompt = (
        f"Decompõe o valor da empresa (valor actual estimado {sym}{value}). Devolve APENAS JSON: "
        '{"factors":[{"name":str,"influence":"positiva"|"negativa"|"neutra","weight":str,"note":str}],'
        '"actions":[{"action":str,"uplift":str,"note":str}]}. '
        "'factors' DEVE incluir exactamente: Ativos, Marca, Carteira de Clientes, Capacidade de gerar lucro, Know-how, "
        "Potencial de crescimento, Dependência do Fundador — cada um com 'influence', 'weight' (ex '+18%' ou '-12%') e 'note' (1 frase). "
        "'actions': 3 a 5 formas concretas de aumentar o valuation (ex: contratar gestor operacional, criar contratos recorrentes, "
        "reduzir dependência do fundador, melhorar margem), cada uma com 'uplift' (ex '+45.000 €') e 'note'. Português europeu. Sem texto fora do JSON."
    )
    ai = await cached_ai("valuation", uid, cid, sysmsg, prompt) or {"factors": [], "actions": []}
    return {"company_value": value, "currency_symbol": sym, "goal_value": snap["goal_value"], "progress": snap["progress"],
            "factors": ai.get("factors", []), "actions": ai.get("actions", [])}

@api_router.get("/report")
async def strategic_report(user: dict = Depends(get_current_user)):
    uid = user["id"]
    cid = await active_company_id(uid)
    snap = await build_snapshot(uid)
    sysmsg = await build_system_prompt(uid, user.get("name", ""))
    prompt = (
        "Prepara um Relatório Estratégico da Empresa ao nível de uma consultora de topo (McKinsey/Deloitte). Devolve APENAS JSON: "
        '{"situacao_atual":str,"riscos":[str],"oportunidades":[str],"pontos_fortes":[str],"pontos_fracos":[str],'
        '"valor":{"atual":str,"comentario":str},"projecao_12m":str,"plano_acao":[{"acao":str,"prazo":str,"impacto":str}],"recomendacoes":[str]}. '
        "Profundo mas conciso, orientado a decisões e ao futuro, com linguagem executiva. Português europeu. Sem texto fora do JSON."
    )
    ai = await cached_ai("report", uid, cid, sysmsg, prompt) or {}
    ai = dict(ai)
    ai["company_name"] = snap["company_name"]; ai["health"] = snap["health"]
    ai["company_value"] = snap["company_value"]; ai["currency_symbol"] = snap["currency_symbol"]
    ai["generated_at"] = datetime.now(timezone.utc).isoformat()
    return ai

# ---------------------------------------------------------------- Future Engine (PREMIUM)
@api_router.get("/future")
async def future_projection(user: dict = Depends(get_current_user)):
    if not await is_premium(user["id"]):
        raise HTTPException(status_code=403, detail="premium_required")
    snap = await build_snapshot(user["id"])
    months = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    now = datetime.now(timezone.utc)
    balance = snap["cash_balance"]; monthly_net = snap["monthly_net"]
    projection = []; b = balance
    for i in range(12):
        idx = (now.month - 1 + i) % 12
        b += monthly_net
        projection.append({"month": months[idx], "cash": round(b, 2)})
    projection[0]["cash"] = round(balance, 2)
    warning = None
    if monthly_net < 0:
        b2 = balance
        for i in range(12):
            b2 += monthly_net
            if b2 < 0:
                warning = f"Se continuar assim, em {months[(now.month - 1 + i) % 12]} fica sem caixa."
                break
    return {"projection": projection, "monthly_net": monthly_net, "warning": warning, "currency_symbol": snap["currency_symbol"]}

@api_router.post("/future/simulate")
async def simulate(inp: SimInput, user: dict = Depends(get_current_user)):
    if not await is_premium(user["id"]):
        raise HTTPException(status_code=403, detail="premium_required")
    sysmsg = await build_system_prompt(user["id"], user.get("name", ""))
    prompt = (
        f"O empresário quer simular esta decisão: '{inp.scenario}'. Detalhe: '{inp.detail}'. "
        f"Analisa o impacto FUTURO com base no estado actual. Devolve APENAS JSON: "
        f'{{"verdict":"favoravel"|"cautela"|"desaconselhado","summary":str,'
        f'"metrics":{{"lucro":str,"fluxo_caixa":str,"risco":str,"valuation":str,"saude":str}},'
        f'"recommendation":str,"timeline":str}}. '
        f"Em 'metrics' indica o impacto em cada eixo (ex: '+28.000 €/ano', '-2 meses de autonomia', 'sobe para 78/100'). "
        f"Sê concreto com números estimados. Português europeu. Sem texto fora do JSON."
    )
    ai = await ai_json(sysmsg, prompt)
    if not ai:
        raise HTTPException(status_code=500, detail="Não foi possível simular agora")
    return ai

# ---------------------------------------------------------------- Investment Grade (PREMIUM)
def to_grade(score: float) -> str:
    for th, g in [(95, "A+"), (88, "A"), (82, "A-"), (75, "B+"), (68, "B"), (62, "B-"),
                  (55, "C+"), (48, "C"), (40, "C-"), (30, "D")]:
        if score >= th:
            return g
    return "F"

@api_router.get("/investment-grade")
async def investment_grade(user: dict = Depends(get_current_user)):
    if not await is_premium(user["id"]):
        raise HTTPException(status_code=403, detail="premium_required")
    snap = await build_snapshot(user["id"])
    company = await resolve_company(user["id"]) or {}
    cid = str(company["_id"]) if company.get("_id") else None
    entries = await db.entries.find({"user_id": user["id"], "company_id": cid}, {"type": 1, "amount": 1, "date": 1}).to_list(5000) if cid else []
    dna = await db.ceo_dna.find_one({"user_id": user["id"]}) or {}
    docs = await db.documents.find({"user_id": user["id"], "is_deleted": False}).to_list(500)
    doc_types = set(d.get("doc_type", "other") for d in docs)
    n_docs = len(docs)

    inc, months_set = {}, set()
    for e in entries:
        mk = str(e.get("date", ""))[:7]
        if len(mk) == 7:
            months_set.add(mk)
            if e["type"] == "income":
                inc[mk] = inc.get(mk, 0) + e["amount"]
    sorted_m = sorted(inc.keys())
    growth_score = 50
    if len(sorted_m) >= 2:
        recent = sum(inc[m] for m in sorted_m[-3:])
        prior = sum(inc[m] for m in sorted_m[-6:-3])
        if prior > 0:
            growth_score = max(5, min(100, int(60 + ((recent - prior) / prior) * 100)))
        elif recent > 0:
            growth_score = 72
    coverage = len(months_set)
    emp = int(company.get("employees_count", 0)); cli = int(company.get("clients_count", 0))
    dependency_score = min(100, 28 + emp * 12 + (12 if cli > 5 else 0))
    liquidity_score = min(100, int(snap["runway"] * 14))
    risk_score = min(100, int(snap["runway"] * 12 + (20 if snap["profit_margin"] > 0 else 0)))
    fin_score = snap["health"]

    dims = [
        {"key": "financeiro", "label": "Financeiro", "score": fin_score},
        {"key": "crescimento", "label": "Crescimento", "score": growth_score},
        {"key": "risco", "label": "Risco", "score": risk_score},
        {"key": "liquidez", "label": "Liquidez", "score": liquidity_score},
        {"key": "dependencia", "label": "Dependência do Fundador", "score": dependency_score},
    ]
    for d in dims:
        d["grade"] = to_grade(d["score"])
    overall_score = round(sum(d["score"] for d in dims) / len(dims))
    overall_grade = to_grade(overall_score)

    checklist = [
        {"item": "Demonstrações financeiras completas", "upload_type": "financials", "done": "financials" in doc_types},
        {"item": "Histórico de EBITDA e fluxo de caixa (6+ meses)", "done": coverage >= 6},
        {"item": "Composição de ativos e passivos", "upload_type": "assets", "done": "assets" in doc_types},
        {"item": "Contratos e qualidade da carteira de clientes", "upload_type": "contracts", "done": ("contracts" in doc_types) or cli > 0},
        {"item": "Avaliação de dependência do fundador", "done": bool(dna.get("completed")) and emp > 0},
    ]
    done = sum(1 for c in checklist if c["done"])
    completeness = round(done / len(checklist) * 100)
    if completeness >= 75:
        tier, margin = "Nível Profissional", 0.10
    elif completeness >= 40:
        tier, margin = "Estimativa Fundamentada", 0.20
    else:
        tier, margin = "Estimativa Inteligente", 0.35
    value = snap["company_value"]
    value_range = {"low": round(value * (1 - margin)), "high": round(value * (1 + margin))}
    next_target = round(value * 1.4) if value else snap["goal_value"]
    sym = snap["currency_symbol"]

    sysmsg = await build_system_prompt(user["id"], user.get("name", ""))
    grades_txt = ", ".join(f"{d['label']}: {d['grade']}" for d in dims)
    prompt = (
        f"Estás a produzir um RELATÓRIO DE INVESTIMENTO estilo agência de rating para esta empresa. "
        f"Valor estimado atual: {sym}{value} (intervalo {sym}{value_range['low']}–{sym}{value_range['high']}). "
        f"Rating global: {overall_grade}. Notas: {grades_txt}. "
        f"Nível de confiança dos dados: {tier} ({completeness}% completos). "
        f"Devolve APENAS JSON: {{\"rationale\":str, \"grade_notes\":{{\"financeiro\":str,\"crescimento\":str,\"risco\":str,\"liquidez\":str,\"dependencia\":str}}, "
        f"\"improvement_plan\":[{{\"action\":str,\"impact\":str}}], \"disclaimer\":str}}. "
        f"'rationale': explica em 2-3 frases PORQUE a empresa vale este valor. "
        f"'grade_notes': 1 frase curta por dimensão a justificar a nota. "
        f"'improvement_plan': 3-4 ações concretas e priorizadas para subir o valor até {sym}{next_target}, cada uma com o impacto estimado. "
        f"'disclaimer': 1 frase a esclarecer que é uma estimativa fundamentada nos dados fornecidos e não uma avaliação pericial oficial. "
        f"Tudo em português. Sem texto fora do JSON."
    )
    chat = LlmChat(api_key=EMERGENT_KEY, session_id=f"grade-{uuid.uuid4()}", system_message=sysmsg).with_model("openai", "gpt-5.4")
    ai = {}
    try:
        resp = await chat.send_message(UserMessage(text=prompt))
        text = resp.strip()
        if "```" in text:
            text = text.split("```")[1].replace("json", "", 1).strip()
        ai = json.loads(text)
    except Exception as e:
        logger.error(f"grade error: {e}")
    notes = ai.get("grade_notes", {})
    fallback_why = {
        "financeiro": "Baseado na saúde financeira e margem de lucro atuais.",
        "crescimento": "Baseado na tendência de receita e na base de clientes.",
        "risco": "Baseado na autonomia de caixa e na rentabilidade.",
        "liquidez": "Baseado no saldo disponível face às despesas mensais.",
        "dependencia": "Baseado na estrutura de equipa e na maturidade operacional.",
    }
    for d in dims:
        d["why"] = notes.get(d["key"]) or fallback_why.get(d["key"], "")

    return {
        "overall_grade": overall_grade, "overall_score": overall_score,
        "dimensions": dims, "company_value": value, "value_range": value_range,
        "currency_symbol": sym, "next_target": next_target,
        "confidence": {"tier": tier, "score": completeness, "checklist": checklist},
        "rationale": ai.get("rationale", "Estimativa baseada nos dados financeiros e no perfil da empresa fornecidos."),
        "improvement_plan": ai.get("improvement_plan", []),
        "disclaimer": ai.get("disclaimer", "Esta é uma estimativa fundamentada nos dados fornecidos e nos documentos analisados, não uma avaliação pericial oficial."),
    }

# ---------------------------------------------------------------- subscription / Stripe
PLANS = {
    "premium_monthly": {"label": "Premium Mensal", "price": "€29", "period": "/mês"},
    "premium_yearly": {"label": "Premium Anual", "price": "€290", "period": "/ano"},
}

@api_router.get("/subscription")
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

@api_router.post("/payments/checkout")
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

@api_router.get("/payments/status/{session_id}")
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

@api_router.post("/payments/portal")
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

@api_router.post("/payments/cancel-subscription")
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

@api_router.post("/stripe/webhook")
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

# ---------------------------------------------------------------- docs
@api_router.post("/upload")
async def upload(file: UploadFile = File(...), doc_type: str = Form("other"), user: dict = Depends(get_current_user)):
    ext = file.filename.split(".")[-1] if "." in file.filename else "bin"
    path = f"{APP_NAME}/uploads/{user['id']}/{uuid.uuid4()}.{ext}"
    data = await file.read()
    result = put_object(path, data, file.content_type or "application/octet-stream")
    res = await db.documents.insert_one({"user_id": user["id"], "storage_path": result["path"],
        "original_filename": file.filename, "content_type": file.content_type, "doc_type": doc_type,
        "size": result.get("size", len(data)), "is_deleted": False, "created_at": datetime.now(timezone.utc).isoformat()})
    return {"id": str(res.inserted_id), "filename": file.filename, "doc_type": doc_type, "size": result.get("size", len(data))}

@api_router.get("/documents")
async def list_docs(user: dict = Depends(get_current_user)):
    docs = await db.documents.find({"user_id": user["id"], "is_deleted": False}).sort("created_at", -1).to_list(500)
    return [{"id": str(d["_id"]), "filename": d.get("original_filename"), "doc_type": d.get("doc_type", "other"),
             "size": d.get("size", 0), "created_at": d.get("created_at")} for d in docs]

@api_router.delete("/documents/{doc_id}")
async def delete_doc(doc_id: str, user: dict = Depends(get_current_user)):
    await db.documents.update_one({"_id": ObjectId(doc_id), "user_id": user["id"]}, {"$set": {"is_deleted": True}})
    return {"ok": True}

@api_router.post("/contact")
async def contact(inp: ContactInput):
    await db.contact_messages.insert_one({
        "name": inp.name, "email": inp.email.lower(), "message": inp.message,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"ok": True}

@api_router.get("/")
async def root():
    return {"message": "CEO AI online"}

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
