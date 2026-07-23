from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File, Form, Header, Query
from fastapi.responses import StreamingResponse
from core import *
from models import *

router = APIRouter()

def _company_out(c):
    return {"id": str(c["_id"]), "name": c.get("name"), "region": c.get("region"), "currency": c.get("currency"),
            "sector": c.get("sector", ""), "employees_count": c.get("employees_count", 0),
            "clients_count": c.get("clients_count", 0), "bank_balance": c.get("bank_balance", 0),
            "monthly_tax_estimate": c.get("monthly_tax_estimate", 0), "bank_connected": c.get("bank_connected", False)}

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
    return {"id": cid, **inp.model_dump()}
