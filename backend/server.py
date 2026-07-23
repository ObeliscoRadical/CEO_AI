from dotenv import load_dotenv
from pathlib import Path
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, UploadFile, File, Header, Query
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime, timezone, timedelta
import logging, uuid, jwt, bcrypt, io, json, requests, random, stripe

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
    return {"id": str(res.inserted_id), **inp.model_dump()}

@api_router.delete("/entries/{entry_id}")
async def delete_entry(entry_id: str, user: dict = Depends(get_current_user)):
    await db.entries.delete_one({"_id": ObjectId(entry_id), "user_id": user["id"]})
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
    entries = await db.entries.find({"user_id": user_id, "company_id": cid}).to_list(5000) if cid else []
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
                    "briefing_tone": "direto", "model": "claude",
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
        f"És o CEO AI — o executivo digital de {user_name}. Falas português de forma humana, calorosa e confiante, "
        f"como um CEO experiente e mentor de confiança. {MODE_PROMPTS.get(mode, MODE_PROMPTS['crescimento'])} "
        f"Tom: {tone}. NUNCA fales como um chatbot técnico. Foca-te no FUTURO e nas decisões, não no passado. "
        f"Liga sempre os conselhos aos objetivos pessoais do empresário. Sê conciso e prático.\n\n"
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
@api_router.get("/briefing")
async def briefing(user: dict = Depends(get_current_user)):
    settings = await db.settings.find_one({"user_id": user["id"]}) or {}
    count = settings.get("briefing_count", 4)
    snap = await build_snapshot(user["id"])
    sysmsg = await build_system_prompt(user["id"], user.get("name", ""))
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
        data = {"greeting": f"{greeting}, {user.get('name','')}. Aqui está o que precisa da sua atenção hoje.",
                "items": [{"title": "Ligue os seus dados", "detail": "Registe receitas e despesas para eu analisar a saúde da sua empresa.",
                           "priority": "alta", "icon": "opportunity"}]}
    data["health"] = snap["health"]
    return data

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
        f"Analisa o impacto FUTURO com base no estado atual da empresa. Devolve APENAS JSON: "
        f'{{"verdict":"favoravel"|"cautela"|"desaconselhado","summary":str,"impact_cash":str,"impact_profit":str,"recommendation":str,"timeline":str}}. '
        f"Sê concreto com números estimados quando possível. Sem texto fora do JSON."
    )
    chat = LlmChat(api_key=EMERGENT_KEY, session_id=f"sim-{uuid.uuid4()}", system_message=sysmsg).with_model("openai", "gpt-5.4")
    try:
        resp = await chat.send_message(UserMessage(text=prompt))
        text = resp.strip()
        if "```" in text:
            text = text.split("```")[1].replace("json", "", 1).strip()
        return json.loads(text)
    except Exception as e:
        logger.error(f"simulate error: {e}")
        raise HTTPException(status_code=500, detail="Não foi possível simular agora")

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
    entries = await db.entries.find({"user_id": user["id"], "company_id": cid}).to_list(5000) if cid else []
    dna = await db.ceo_dna.find_one({"user_id": user["id"]}) or {}
    n_docs = await db.documents.count_documents({"user_id": user["id"], "is_deleted": False})

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
        {"item": "Demonstrações financeiras completas", "done": n_docs > 0},
        {"item": "Histórico de EBITDA e fluxo de caixa (6+ meses)", "done": coverage >= 6},
        {"item": "Composição de ativos e passivos", "done": float(company.get("bank_balance", 0)) > 0 and n_docs > 0},
        {"item": "Contratos e qualidade da carteira de clientes", "done": cli > 0},
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
    for d in dims:
        d["why"] = notes.get(d["key"], "")

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
    "premium_monthly": {"label": "Premium Mensal", "price": "€19", "period": "/mês"},
    "premium_yearly": {"label": "Premium Anual", "price": "€190", "period": "/ano"},
}

@api_router.get("/subscription")
async def subscription(user: dict = Depends(get_current_user)):
    return {"is_premium": await is_premium(user["id"]), "plans": PLANS}

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

async def _activate_premium(user_id: str):
    if user_id:
        try:
            await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"is_premium": True}})
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
                await _activate_premium(record.get("user_id"))
                record = await db.payment_transactions.find_one({"session_id": session_id})
        except stripe.error.StripeError:
            pass
    return {"session_id": record["session_id"], "status": record["status"], "payment_status": record["payment_status"]}

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
        await _activate_premium((rec or {}).get("user_id") or (obj.get("metadata") or {}).get("user_id"))
    return {"status": "ok"}

# ---------------------------------------------------------------- docs
@api_router.post("/upload")
async def upload(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    ext = file.filename.split(".")[-1] if "." in file.filename else "bin"
    path = f"{APP_NAME}/uploads/{user['id']}/{uuid.uuid4()}.{ext}"
    data = await file.read()
    result = put_object(path, data, file.content_type or "application/octet-stream")
    res = await db.documents.insert_one({"user_id": user["id"], "storage_path": result["path"],
        "original_filename": file.filename, "content_type": file.content_type,
        "size": result.get("size", len(data)), "is_deleted": False, "created_at": datetime.now(timezone.utc).isoformat()})
    return {"id": str(res.inserted_id), "filename": file.filename, "size": result.get("size", len(data))}

@api_router.get("/")
async def root():
    return {"message": "CEO AI online"}

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[os.environ.get("FRONTEND_URL", "http://localhost:3000"), "http://localhost:3000"],
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

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
