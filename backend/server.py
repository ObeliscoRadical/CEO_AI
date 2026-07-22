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
from typing import List, Optional, Dict, Any, Annotated
from pydantic.functional_validators import BeforeValidator
from bson import ObjectId
from datetime import datetime, timezone, timedelta
import logging, uuid, jwt, bcrypt, secrets, io, json, requests, asyncio

from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone

# ---------------------------------------------------------------- DB
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------- AUTH helpers
JWT_ALGORITHM = "HS256"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
APP_NAME = "ceo-ai"

MODEL_MAP = {
    "claude": ("anthropic", "claude-opus-4-7"),
    "gpt": ("openai", "gpt-5.5"),
    "gemini": ("gemini", "gemini-3.1-pro-preview"),
}

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
        user.pop("_id", None)
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Sessão expirada")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

# ---------------------------------------------------------------- Models
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
    type: str  # income | expense
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
    scenario: str  # e.g. "contratar", "comprar", "perder_cliente", "subir_precos"
    detail: str = ""

CURRENCY_SYMBOL = {"EUR": "€", "BRL": "R$", "USD": "$"}

# ---------------------------------------------------------------- Storage
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

# ---------------------------------------------------------------- Auth routes
@api_router.post("/auth/register")
async def register(inp: RegisterInput, response: Response):
    email = inp.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email já registado")
    doc = {"email": email, "password_hash": hash_password(inp.password), "name": inp.name,
           "role": "owner", "auth_provider": "email", "picture": "",
           "created_at": datetime.now(timezone.utc).isoformat()}
    res = await db.users.insert_one(doc)
    uid = str(res.inserted_id)
    token = create_access_token(uid, email)
    set_auth_cookie(response, token)
    return {"id": uid, "email": email, "name": inp.name, "role": "owner"}

@api_router.post("/auth/login")
async def login(inp: LoginInput, response: Response):
    email = inp.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not user.get("password_hash") or not verify_password(inp.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    uid = str(user["_id"])
    token = create_access_token(uid, email)
    set_auth_cookie(response, token)
    return {"id": uid, "email": email, "name": user.get("name", ""), "role": user.get("role", "owner")}

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
               "role": "owner", "auth_provider": "google", "picture": data.get("picture", ""),
               "created_at": datetime.now(timezone.utc).isoformat()}
        res = await db.users.insert_one(doc)
        uid = str(res.inserted_id)
    else:
        uid = str(user["_id"])
    token = create_access_token(uid, email)
    set_auth_cookie(response, token)
    return {"id": uid, "email": email, "name": data.get("name", email), "picture": data.get("picture", "")}

@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}

@api_router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user

# ---------------------------------------------------------------- Company
@api_router.get("/company")
async def get_company(user: dict = Depends(get_current_user)):
    c = await db.companies.find_one({"user_id": user["id"]})
    if not c:
        return None
    c["id"] = str(c["_id"]); c.pop("_id")
    return c

@api_router.post("/company")
async def save_company(inp: CompanyInput, user: dict = Depends(get_current_user)):
    existing = await db.companies.find_one({"user_id": user["id"]})
    data = inp.model_dump()
    data["user_id"] = user["id"]
    if existing:
        await db.companies.update_one({"_id": existing["_id"]}, {"$set": data})
        cid = str(existing["_id"])
    else:
        data["created_at"] = datetime.now(timezone.utc).isoformat()
        res = await db.companies.insert_one(data)
        cid = str(res.inserted_id)
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
    # sync ceo_mode into settings
    await db.settings.update_one({"user_id": user["id"]}, {"$set": {"ceo_mode": inp.ceo_mode}}, upsert=True)
    # store key memories
    mems = []
    if inp.dream: mems.append(("sonho", inp.dream))
    if inp.target_revenue: mems.append(("objetivo", f"Quer faturar {inp.target_revenue}"))
    if inp.five_year_vision: mems.append(("visao", inp.five_year_vision))
    for cat, content in mems:
        await db.memories.update_one({"user_id": user["id"], "category": cat},
                                     {"$set": {"content": content, "user_id": user["id"], "category": cat,
                                               "created_at": datetime.now(timezone.utc).isoformat()}}, upsert=True)
    return {"completed": True}

# ---------------------------------------------------------------- Financial entries
@api_router.get("/entries")
async def list_entries(user: dict = Depends(get_current_user)):
    entries = await db.entries.find({"user_id": user["id"]}).sort("date", -1).to_list(1000)
    for e in entries:
        e["id"] = str(e["_id"]); e.pop("_id")
    return entries

@api_router.post("/entries")
async def create_entry(inp: EntryInput, user: dict = Depends(get_current_user)):
    data = inp.model_dump()
    data.update({"user_id": user["id"], "created_at": datetime.now(timezone.utc).isoformat()})
    res = await db.entries.insert_one(data)
    return {"id": str(res.inserted_id), **inp.model_dump()}

@api_router.delete("/entries/{entry_id}")
async def delete_entry(entry_id: str, user: dict = Depends(get_current_user)):
    await db.entries.delete_one({"_id": ObjectId(entry_id), "user_id": user["id"]})
    return {"ok": True}

@api_router.post("/entries/import")
async def import_csv(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    raw = (await file.read()).decode("utf-8", errors="ignore")
    # Use AI to parse arbitrary CSV into structured entries
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
    if text.startswith("```"):
        text = text.split("```")[1].replace("json", "", 1).strip() if "```" in text else text
    try:
        rows = json.loads(text)
    except Exception:
        raise HTTPException(status_code=422, detail="Não foi possível interpretar o ficheiro")
    inserted = 0
    for r in rows if isinstance(rows, list) else []:
        try:
            doc = {"user_id": user["id"], "type": r.get("type", "expense"),
                   "category": str(r.get("category", "Outro")), "amount": float(r.get("amount", 0)),
                   "date": str(r.get("date", datetime.now(timezone.utc).date().isoformat())),
                   "description": str(r.get("description", "")),
                   "created_at": datetime.now(timezone.utc).isoformat()}
            await db.entries.insert_one(doc)
            inserted += 1
        except Exception:
            continue
    return {"imported": inserted}

# ---------------------------------------------------------------- Snapshot / Dashboard
def rag(value, good, warn, reverse=False):
    """Return status green/amber/red. reverse=True means lower is better."""
    if reverse:
        if value <= good: return "green"
        if value <= warn: return "amber"
        return "red"
    if value >= good: return "green"
    if value >= warn: return "amber"
    return "red"

async def build_snapshot(user_id: str):
    company = await db.companies.find_one({"user_id": user_id}) or {}
    entries = await db.entries.find({"user_id": user_id}).to_list(5000)
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
    company = await db.companies.find_one({"user_id": user["id"]}) or {}
    entries = await db.entries.find({"user_id": user["id"]}).to_list(5000)
    has_data = len(entries) > 0
    dims = [
        {"dimension": "Liderança", "score": 80 if dna.get("completed") else 40},
        {"dimension": "Financeiro", "score": snap["health"]},
        {"dimension": "Marketing", "score": min(100, 30 + company.get("clients_count", 0) * 4)},
        {"dimension": "Operação", "score": 70 if has_data else 35},
        {"dimension": "Clientes", "score": min(100, 40 + company.get("clients_count", 0) * 5)},
        {"dimension": "Funcionários", "score": min(100, 50 + company.get("employees_count", 0) * 6)},
        {"dimension": "Risco", "score": min(100, int(snap["runway"] * 12))},
        {"dimension": "Inovação", "score": 60 if dna.get("five_year_vision") else 30},
    ]
    overall = round(sum(d["score"] for d in dims) / len(dims))
    return {"overall": overall, "dimensions": dims}

# ---------------------------------------------------------------- Memory
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

# ---------------------------------------------------------------- Settings
DEFAULT_SETTINGS = {"ceo_mode": "crescimento", "theme": "dark", "briefing_count": 4,
                    "briefing_tone": "direto", "model": "claude",
                    "monitored_widgets": ["cashflow", "profit", "clients", "tax", "employees", "bank", "risk"]}

@api_router.get("/settings")
async def get_settings(user: dict = Depends(get_current_user)):
    s = await db.settings.find_one({"user_id": user["id"]}) or {}
    s.pop("_id", None); s.pop("user_id", None)
    return {**DEFAULT_SETTINGS, **s}

@api_router.put("/settings")
async def update_settings(inp: SettingsInput, user: dict = Depends(get_current_user)):
    data = {k: v for k, v in inp.model_dump().items() if v is not None}
    await db.settings.update_one({"user_id": user["id"]}, {"$set": data}, upsert=True)
    s = await db.settings.find_one({"user_id": user["id"]})
    s.pop("_id", None); s.pop("user_id", None)
    return {**DEFAULT_SETTINGS, **s}

# ---------------------------------------------------------------- CEO context builder
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
    model_key = settings.get("model", "claude")
    provider, model = MODEL_MAP.get(model_key, MODEL_MAP["claude"])
    sysmsg = await build_system_prompt(user_id, user_name)
    kwargs = {}
    if provider == "anthropic":
        chat = LlmChat(api_key=EMERGENT_KEY, session_id=session_id, system_message=sysmsg,
                       custom_headers={"anthropic-beta": "task-budgets-2026-03-13"}).with_model(provider, model)
        chat = chat.with_params(extra_body={"output_config": {"task_budget": {"type": "tokens", "total": 200000}, "effort": "high"}}, max_tokens=8000)
    else:
        chat = LlmChat(api_key=EMERGENT_KEY, session_id=session_id, system_message=sysmsg).with_model(provider, model)
    return chat

# ---------------------------------------------------------------- Chat
@api_router.get("/chat/sessions")
async def chat_sessions(user: dict = Depends(get_current_user)):
    sess = await db.chat_sessions.find({"user_id": user["id"]}).sort("created_at", -1).to_list(100)
    for s in sess:
        s["id"] = str(s["_id"]); s.pop("_id")
    return sess

@api_router.get("/chat/{session_id}/messages")
async def chat_messages(session_id: str, user: dict = Depends(get_current_user)):
    msgs = await db.chat_messages.find({"session_id": session_id, "user_id": user["id"]}).sort("created_at", 1).to_list(1000)
    for m in msgs:
        m["id"] = str(m["_id"]); m.pop("_id")
    return msgs

@api_router.post("/chat")
async def chat(inp: ChatInput, user: dict = Depends(get_current_user)):
    session_id = inp.session_id
    if not session_id:
        session_id = str(uuid.uuid4())
        title = inp.message[:50]
        await db.chat_sessions.insert_one({"_id": ObjectId(), "sid": session_id, "user_id": user["id"],
                                           "title": title, "created_at": datetime.now(timezone.utc).isoformat()})
    # rebuild history for context
    history = await db.chat_messages.find({"session_id": session_id, "user_id": user["id"]}).sort("created_at", 1).to_list(1000)
    await db.chat_messages.insert_one({"session_id": session_id, "user_id": user["id"], "role": "user",
                                       "content": inp.message, "created_at": datetime.now(timezone.utc).isoformat()})
    chat_obj = await get_chat(user["id"], user.get("name", ""), session_id)
    # feed prior history into the fresh chat instance
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

# ---------------------------------------------------------------- Briefing
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
        f"Exatamente {count} itens, priorizados pelo que mais importa hoje (clientes atrasados, quebra de lucro, alerta de caixa, oportunidades). "
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

# ---------------------------------------------------------------- Future Engine
@api_router.get("/future")
async def future_projection(user: dict = Depends(get_current_user)):
    snap = await build_snapshot(user["id"])
    months = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    now = datetime.now(timezone.utc)
    balance = snap["cash_balance"]
    monthly_net = snap["monthly_net"]
    projection = []
    b = balance
    for i in range(12):
        idx = (now.month - 1 + i) % 12
        b += monthly_net
        projection.append({"month": months[idx], "cash": round(b, 2), "projected": True if i > 0 else False})
    projection[0]["cash"] = round(balance, 2)
    # find month running out of cash
    warning = None
    if monthly_net < 0:
        b2 = balance
        for i in range(12):
            b2 += monthly_net
            if b2 < 0:
                idx = (now.month - 1 + i) % 12
                warning = f"Se continuar assim, em {months[idx]} fica sem caixa."
                break
    return {"projection": projection, "monthly_net": monthly_net, "warning": warning,
            "currency_symbol": snap["currency_symbol"]}

@api_router.post("/future/simulate")
async def simulate(inp: SimInput, user: dict = Depends(get_current_user)):
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
        data = json.loads(text)
    except Exception as e:
        logger.error(f"simulate error: {e}")
        raise HTTPException(status_code=500, detail="Não foi possível simular agora")
    return data

# ---------------------------------------------------------------- Docs upload
@api_router.post("/upload")
async def upload(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    ext = file.filename.split(".")[-1] if "." in file.filename else "bin"
    path = f"{APP_NAME}/uploads/{user['id']}/{uuid.uuid4()}.{ext}"
    data = await file.read()
    result = put_object(path, data, file.content_type or "application/octet-stream")
    doc = {"user_id": user["id"], "storage_path": result["path"], "original_filename": file.filename,
           "content_type": file.content_type, "size": result.get("size", len(data)), "is_deleted": False,
           "created_at": datetime.now(timezone.utc).isoformat()}
    res = await db.documents.insert_one(doc)
    return {"id": str(res.inserted_id), "filename": file.filename, "size": doc["size"]}

@api_router.get("/documents")
async def list_docs(user: dict = Depends(get_current_user)):
    docs = await db.documents.find({"user_id": user["id"], "is_deleted": False}).sort("created_at", -1).to_list(500)
    for d in docs:
        d["id"] = str(d["_id"]); d.pop("_id")
    return docs

# ---------------------------------------------------------------- Startup
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
                                   "name": "Diego", "role": "owner", "auth_provider": "email", "picture": "",
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
