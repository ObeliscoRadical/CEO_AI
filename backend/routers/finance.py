from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File, Form, Header, Query
from fastapi.responses import StreamingResponse
from core import *
from models import *

router = APIRouter()

@router.get("/dna")
async def get_dna(user: dict = Depends(get_current_user)):
    d = await db.ceo_dna.find_one({"user_id": user["id"]})
    if not d:
        return {"completed": False}
    d["id"] = str(d["_id"]); d.pop("_id")
    return d

@router.post("/dna")
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
@router.get("/entries")
async def list_entries(user: dict = Depends(get_current_user)):
    cid = await active_company_id(user["id"])
    entries = await db.entries.find({"user_id": user["id"], "company_id": cid}).sort("date", -1).to_list(2000)
    for e in entries:
        e["id"] = str(e["_id"]); e.pop("_id")
    return entries

@router.post("/entries")
async def create_entry(inp: EntryInput, user: dict = Depends(get_current_user)):
    cid = await active_company_id(user["id"])
    data = inp.model_dump()
    data.update({"user_id": user["id"], "company_id": cid, "created_at": datetime.now(timezone.utc).isoformat()})
    res = await db.entries.insert_one(data)
    await invalidate_ai_cache(user["id"])
    return {"id": str(res.inserted_id), **inp.model_dump()}

@router.delete("/entries/{entry_id}")
async def delete_entry(entry_id: str, user: dict = Depends(get_current_user)):
    await db.entries.delete_one({"_id": ObjectId(entry_id), "user_id": user["id"]})
    await invalidate_ai_cache(user["id"])
    return {"ok": True}

@router.post("/entries/import")
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
@router.post("/bank/connect")
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

@router.get("/dashboard")
async def dashboard(user: dict = Depends(get_current_user)):
    return await build_snapshot(user["id"])

# ---------------------------------------------------------------- CEO Score
@router.get("/score")
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
