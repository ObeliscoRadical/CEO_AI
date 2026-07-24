from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File, Form, Header, Query
from fastapi.responses import StreamingResponse
from core import *
from models import *

router = APIRouter()

def _company_out(c):
    return {"id": str(c["_id"]), "name": c.get("name"), "region": c.get("region"), "currency": c.get("currency"),
            "sector": c.get("sector", ""), "employees_count": c.get("employees_count", 0),
            "clients_count": c.get("clients_count", 0), "bank_balance": c.get("bank_balance", 0),
            "monthly_tax_estimate": c.get("monthly_tax_estimate", 0), "bank_connected": c.get("bank_connected", False),
            "profile": c.get("profile", {})}

@router.get("/companies")
async def list_companies(user: dict = Depends(get_current_user)):
    cs = await db.companies.find({"user_id": user["id"]}).to_list(100)
    active = await active_company_id(user["id"])
    return {"companies": [_company_out(c) for c in cs], "active_company_id": active}

@router.post("/companies")
async def create_company(inp: CompanyInput, user: dict = Depends(get_current_user)):
    data = inp.model_dump()
    data.update({"user_id": user["id"], "created_at": datetime.now(timezone.utc).isoformat()})
    res = await db.companies.insert_one(data)
    cid = str(res.inserted_id)
    await db.settings.update_one({"user_id": user["id"]}, {"$set": {"active_company_id": cid}}, upsert=True)
    data["_id"] = res.inserted_id
    return _company_out(data)

@router.put("/companies/active")
async def set_active_company(inp: ActiveCompanyInput, user: dict = Depends(get_current_user)):
    c = await db.companies.find_one({"_id": ObjectId(inp.company_id), "user_id": user["id"]})
    if not c:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    await db.settings.update_one({"user_id": user["id"]}, {"$set": {"active_company_id": inp.company_id}}, upsert=True)
    return {"active_company_id": inp.company_id}

@router.delete("/companies/{company_id}")
async def delete_company(company_id: str, user: dict = Depends(get_current_user)):
    await db.companies.delete_one({"_id": ObjectId(company_id), "user_id": user["id"]})
    await db.entries.delete_many({"user_id": user["id"], "company_id": company_id})
    s = await db.settings.find_one({"user_id": user["id"]}) or {}
    if s.get("active_company_id") == company_id:
        other = await db.companies.find_one({"user_id": user["id"]})
        await db.settings.update_one({"user_id": user["id"]},
                                     {"$set": {"active_company_id": str(other["_id"]) if other else None}}, upsert=True)
    return {"ok": True}

@router.get("/company")
async def get_company(user: dict = Depends(get_current_user)):
    c = await resolve_company(user["id"])
    return _company_out(c) if c else None

@router.post("/company")
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
    await invalidate_ai_cache(user["id"])
    return {"id": cid, **inp.model_dump()}


@router.post("/company/lookup-nif")
async def lookup_nif(payload: dict, user: dict = Depends(get_current_user)):
    nif = str(payload.get("nif", "")).strip()
    if not (nif.isdigit() and len(nif) == 9):
        raise HTTPException(400, "NIF inválido. Deve ter 9 dígitos.")
    key = os.environ.get("NIFPT_API_KEY")
    if not key:
        raise HTTPException(400, "A chave da API NIF.PT ainda não está configurada. Adiciona-a para usar a busca por NIF.")
    try:
        async with httpx.AsyncClient(timeout=15) as hc:
            r = await hc.get("https://www.nif.pt/", params={"json": 1, "q": nif, "key": key})
            data = r.json()
    except Exception as e:
        logger.error(f"nif lookup error: {e}")
        raise HTTPException(502, "Não consegui contactar o serviço NIF.PT. Tenta novamente.")
    if data.get("result") != "success" or not data.get("records"):
        raise HTTPException(404, "Não encontrei dados públicos para esse NIF.")
    rec = data["records"].get(nif) or list(data["records"].values())[0]
    loc = ", ".join(filter(None, [rec.get("city"), rec.get("pc4")])) or rec.get("address") or ""
    return {"name": rec.get("title"), "cae": rec.get("cae"), "activity": rec.get("activity"),
            "location": loc, "status": rec.get("status"), "nif": nif}


@router.post("/company/import-certidao")
async def import_certidao(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    data = await file.read()
    text = extract_document_text(data, file.content_type, file.filename)
    if not text or len(text.strip()) < 40:
        raise HTTPException(422, "Não consegui ler texto do ficheiro. Envia a certidão permanente em PDF (não uma imagem digitalizada).")
    prompt = (
        "Extrai os dados desta certidão permanente do registo comercial português. Devolve APENAS JSON: "
        '{"name":str,"nipc":str,"cae":str,"activity":str,"location":str,"objeto_social":str,'
        '"capital":number|null,"incorporation_date":str,"socios":[str]}. '
        "Preenche apenas com o que estiver no documento (senão null ou string vazia). "
        "'activity' = descrição do CAE; 'objeto_social' = o objeto/atividade da empresa. Português europeu. Sem texto fora do JSON.\n\n"
        "CONTEÚDO:\n" + text[:9000]
    )
    ai = await ai_json("És um jurista e analista de empresas. Respondes só com JSON.", prompt)
    return ai or {}
