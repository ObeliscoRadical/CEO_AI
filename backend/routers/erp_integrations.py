import hashlib
import json
import os
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from core import (
    active_company_id,
    db,
    get_current_user,
    get_erp_financial_context,
    invalidate_ai_cache,
    resolve_company,
)
from models import ERPIntegrationInput

router = APIRouter()


def _mask_secret(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    if len(raw) <= 8:
        return "•" * len(raw)
    return f"{raw[:4]}{'•' * max(4, len(raw) - 8)}{raw[-4:]}"


def _public_api_base(request: Request) -> str:
    origin = (request.headers.get("origin") or os.environ.get("FRONTEND_URL") or "").rstrip("/")
    if origin.startswith("http"):
        return origin
    return str(request.base_url).rstrip("/")


def _to_number(value):
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    if isinstance(value, str):
        raw = value.strip().replace("€", "").replace("R$", "").replace("$", "").replace(" ", "")
        if not raw:
            return None
        if raw.count(",") == 1 and raw.count(".") > 1:
            raw = raw.replace(".", "").replace(",", ".")
        elif raw.count(",") == 1 and raw.count(".") == 0:
            raw = raw.replace(",", ".")
        try:
            return round(float(raw), 2)
        except Exception:
            return None
    return None


def _pick(payload: dict, *keys):
    for key in keys:
        if key in payload and payload.get(key) not in (None, "", []):
            return payload.get(key)
    return None


def _normalize_items(value, fallback_name: str):
    out = []
    if isinstance(value, dict):
        value = [{"name": k, "amount": v} for k, v in value.items()]
    if not isinstance(value, list):
        return out
    for idx, item in enumerate(value):
        if isinstance(item, dict):
            amount = _to_number(item.get("amount") if "amount" in item else item.get("value"))
            name = str(item.get("name") or item.get("label") or f"{fallback_name} {idx + 1}").strip()
        else:
            amount = _to_number(item)
            name = f"{fallback_name} {idx + 1}"
        if amount is None:
            continue
        out.append({"name": name, "amount": amount})
    return out


def _normalize_financial_payload(payload: dict):
    cash_balance = _to_number(_pick(payload, "cash_balance", "current_balance", "balance", "saldo_atual"))
    total_debt = _to_number(_pick(payload, "total_debt", "debt", "debts_total", "divida_total"))
    monthly_revenue = _to_number(_pick(payload, "monthly_revenue", "revenue_monthly", "faturacao_mensal"))
    variable_costs_pct = _to_number(_pick(payload, "variable_costs_pct", "variable_cost_percent", "custos_variaveis_pct"))
    fixed_costs = _normalize_items(_pick(payload, "fixed_costs", "custos_fixos"), "Custo fixo")
    assets = _normalize_items(_pick(payload, "assets", "ativos"), "Ativo")
    liabilities = _normalize_items(_pick(payload, "liabilities", "passivos"), "Passivo")
    credit_restructuring = _pick(payload, "credit_restructuring", "reestruturacao_credito") or {}
    meaningful = any([
        cash_balance is not None,
        total_debt is not None,
        monthly_revenue is not None,
        variable_costs_pct is not None,
        fixed_costs,
        assets,
        liabilities,
        credit_restructuring,
    ])
    event_key = str(_pick(payload, "event_id", "id", "reference", "event_reference") or hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()[:24])
    event_type = str(_pick(payload, "event_type", "type", "topic") or "financial_update")
    occurred_at = str(_pick(payload, "occurred_at", "timestamp", "sent_at", "created_at") or datetime.now(timezone.utc).isoformat())
    return {
        "meaningful": meaningful,
        "event_key": event_key,
        "event_type": event_type,
        "occurred_at": occurred_at,
        "context": {
            "cash_balance": cash_balance,
            "total_debt": total_debt,
            "monthly_revenue": monthly_revenue,
            "variable_costs_pct": variable_costs_pct,
            "fixed_costs": fixed_costs,
            "assets": assets,
            "liabilities": liabilities,
            "credit_restructuring": credit_restructuring,
        },
    }


@router.get("/erp-integration/status")
async def erp_integration_status(request: Request, user: dict = Depends(get_current_user)):
    cid = await active_company_id(user["id"])
    company = await resolve_company(user["id"]) or {}
    if not cid:
        return {"connected": False, "company": None, "connection": None, "context": None, "recent_events": []}
    conn = await db.erp_integrations.find_one({"user_id": user["id"], "company_id": cid, "active": True}, {"_id": 0, "token_hash": 0})
    ctx = await get_erp_financial_context(user["id"], cid)
    events = await db.erp_events.find({"user_id": user["id"], "company_id": cid}, {"_id": 0, "raw_payload": 0}).sort("received_at", -1).to_list(5)
    webhook_url = None
    if conn:
        webhook_url = f"{_public_api_base(request)}/api/erp-integration/inbound/{conn['endpoint_id']}"
        conn = {**conn, "webhook_url": webhook_url}
    if ctx:
        ctx = {**ctx, "total_fixed_costs": round(sum(float(c.get("amount", 0) or 0) for c in (ctx.get("fixed_costs") or [])), 2)}
    return {
        "connected": bool(conn),
        "company": {"id": cid, "name": company.get("name", "A minha empresa")},
        "connection": conn,
        "context": ctx,
        "recent_events": events,
    }


@router.post("/erp-integration/connect")
async def erp_integration_connect(inp: ERPIntegrationInput, request: Request, user: dict = Depends(get_current_user)):
    cid = await active_company_id(user["id"])
    if not cid:
        raise HTTPException(status_code=400, detail="Cria ou seleciona uma empresa antes de integrar o teu sistema de gestão.")
    existing = await db.erp_integrations.find_one({"user_id": user["id"], "company_id": cid}) or {}
    endpoint_id = existing.get("endpoint_id") or secrets.token_urlsafe(18)
    raw_token = (inp.api_token or "").strip()
    generated = False
    if inp.generate_token or (not raw_token and not existing.get("token_hash")):
        raw_token = secrets.token_urlsafe(24)
        generated = True
    if not raw_token and not existing.get("token_hash"):
        raise HTTPException(status_code=400, detail="Indica um token seguro ou pede ao CEO AI para gerar um.")
    auth_header_name = (inp.auth_header_name or existing.get("auth_header_name") or "X-ERP-Token").strip() or "X-ERP-Token"
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest() if raw_token else existing.get("token_hash")
    token_mask = _mask_secret(raw_token) if raw_token else existing.get("token_mask", "")
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "user_id": user["id"],
        "company_id": cid,
        "system_name": (inp.system_name or existing.get("system_name") or "Sistema de Gestão").strip() or "Sistema de Gestão",
        "erp_base_url": (inp.erp_base_url or existing.get("erp_base_url") or "").strip(),
        "external_webhook_url": (inp.external_webhook_url or existing.get("external_webhook_url") or "").strip(),
        "auth_header_name": auth_header_name,
        "token_hash": token_hash,
        "token_mask": token_mask,
        "notes": (inp.notes or existing.get("notes") or "").strip(),
        "endpoint_id": endpoint_id,
        "active": True,
        "updated_at": now,
    }
    await db.erp_integrations.update_one(
        {"user_id": user["id"], "company_id": cid},
        {"$set": doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    return {
        "ok": True,
        "generated_token": raw_token if generated else None,
        "connection": {
            "system_name": doc["system_name"],
            "erp_base_url": doc["erp_base_url"],
            "external_webhook_url": doc["external_webhook_url"],
            "auth_header_name": doc["auth_header_name"],
            "token_mask": doc["token_mask"],
            "webhook_url": f"{_public_api_base(request)}/api/erp-integration/inbound/{endpoint_id}",
            "updated_at": now,
        },
    }


@router.delete("/erp-integration")
async def erp_integration_disconnect(user: dict = Depends(get_current_user)):
    cid = await active_company_id(user["id"])
    if not cid:
        raise HTTPException(status_code=400, detail="Empresa ativa não encontrada")
    now = datetime.now(timezone.utc).isoformat()
    await db.erp_integrations.update_one(
        {"user_id": user["id"], "company_id": cid},
        {"$set": {"active": False, "updated_at": now, "disconnected_at": now}},
    )
    await db.erp_financial_contexts.delete_one({"user_id": user["id"], "company_id": cid})
    await invalidate_ai_cache(user["id"])
    return {"ok": True}


@router.post("/erp-integration/inbound/{endpoint_id}")
async def erp_integration_inbound(endpoint_id: str, request: Request):
    conn = await db.erp_integrations.find_one({"endpoint_id": endpoint_id, "active": True})
    if not conn:
        raise HTTPException(status_code=404, detail="Integração não encontrada")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Payload JSON inválido")
    header_name = conn.get("auth_header_name") or "X-ERP-Token"
    provided_token = request.headers.get(header_name) or request.query_params.get("token")
    if not provided_token:
        raise HTTPException(status_code=401, detail=f"Falta o cabeçalho {header_name}")
    token_hash = hashlib.sha256(provided_token.strip().encode("utf-8")).hexdigest()
    if not secrets.compare_digest(token_hash, conn.get("token_hash") or ""):
        raise HTTPException(status_code=401, detail="Token de integração inválido")
    normalized = _normalize_financial_payload(payload if isinstance(payload, dict) else {})
    if not normalized["meaningful"]:
        raise HTTPException(status_code=400, detail="O payload não contém saldo, dívida, custos fixos ou outros dados financeiros aproveitáveis.")
    now = datetime.now(timezone.utc).isoformat()
    event_doc = {
        "user_id": conn["user_id"],
        "company_id": conn["company_id"],
        "endpoint_id": endpoint_id,
        "event_key": normalized["event_key"],
        "event_type": normalized["event_type"],
        "received_at": now,
        "occurred_at": normalized["occurred_at"],
        "summary": {
            "cash_balance": normalized["context"].get("cash_balance"),
            "total_debt": normalized["context"].get("total_debt"),
            "monthly_revenue": normalized["context"].get("monthly_revenue"),
            "fixed_costs_count": len(normalized["context"].get("fixed_costs") or []),
        },
        "raw_payload": payload,
    }
    try:
        await db.erp_events.insert_one(event_doc)
    except Exception:
        existing = await db.erp_events.find_one({"endpoint_id": endpoint_id, "event_key": normalized["event_key"]}, {"_id": 0})
        if existing:
            return {"accepted": True, "duplicate": True, "event_key": normalized["event_key"]}
        raise
    source_label = f"Sistema de gestão · {conn.get('system_name') or 'ERP'}"
    ctx = normalized["context"]
    await db.erp_financial_contexts.update_one(
        {"user_id": conn["user_id"], "company_id": conn["company_id"]},
        {"$set": {
            "user_id": conn["user_id"],
            "company_id": conn["company_id"],
            "active": True,
            "system_name": conn.get("system_name") or "Sistema de Gestão",
            "source_label": source_label,
            "last_event_key": normalized["event_key"],
            "last_event_type": normalized["event_type"],
            "last_payload_at": now,
            "updated_at": now,
            **ctx,
        }, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    await db.erp_integrations.update_one(
        {"endpoint_id": endpoint_id},
        {"$set": {"last_payload_at": now, "last_event_key": normalized["event_key"], "updated_at": now}},
    )
    await invalidate_ai_cache(conn["user_id"])
    return {
        "accepted": True,
        "duplicate": False,
        "event_key": normalized["event_key"],
        "context": {
            "cash_balance": ctx.get("cash_balance"),
            "total_debt": ctx.get("total_debt"),
            "monthly_revenue": ctx.get("monthly_revenue"),
            "fixed_costs_count": len(ctx.get("fixed_costs") or []),
        },
    }