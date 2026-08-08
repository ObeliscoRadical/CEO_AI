"""Backend tests for ERP / Sistema de Gestão integration."""
import os
import uuid
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN_EMAIL = "adminceoai@gmail.com"
ADMIN_PW = "12345"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PW}, timeout=30)
    assert r.status_code == 200, r.text
    return s


def test_connect_and_status(session):
    unique = uuid.uuid4().hex[:8]
    payload = {
        "system_name": f"Obelisco Manager {unique}",
        "erp_base_url": "https://erp.exemplo.pt",
        "auth_header_name": "X-ERP-Token",
        "api_token": f"segredo-{unique}",
        "notes": "teste automatico",
    }
    r = session.post(f"{BASE}/api/erp-integration/connect", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    assert data["connection"]["system_name"].startswith("Obelisco Manager")
    assert "/api/erp-integration/inbound/" in data["connection"]["webhook_url"]

    s = session.get(f"{BASE}/api/erp-integration/status", timeout=30)
    assert s.status_code == 200, s.text
    st = s.json()
    assert st["connected"] is True
    assert st["connection"]["auth_header_name"] == "X-ERP-Token"
    assert st["connection"]["token_mask"].startswith("segr")


def test_inbound_payload_updates_context(session):
    st = session.get(f"{BASE}/api/erp-integration/status", timeout=30).json()
    token_header = st["connection"]["auth_header_name"]
    # reuse known token from previous test isn't possible from mask, so rotate to generated token
    regen = session.post(f"{BASE}/api/erp-integration/connect", json={"system_name": st["connection"]["system_name"], "generate_token": True}, timeout=30)
    assert regen.status_code == 200, regen.text
    generated = regen.json()["generated_token"]
    assert generated
    webhook_url = regen.json()["connection"]["webhook_url"]
    payload = {
        "event_id": uuid.uuid4().hex[:12],
        "cash_balance": 42100,
        "total_debt": 17000,
        "monthly_revenue": 35500,
        "fixed_costs": [{"name": "Renda", "amount": 3000}, {"name": "Salários", "amount": 9100}],
        "credit_restructuring": {"status": "em curso", "monthly_payment": 700},
    }
    r = requests.post(webhook_url, json=payload, headers={token_header: generated}, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["accepted"] is True
    assert body["context"]["cash_balance"] == 42100

    st2 = session.get(f"{BASE}/api/erp-integration/status", timeout=30)
    assert st2.status_code == 200
    ctx = st2.json()["context"]
    assert ctx["cash_balance"] == 42100
    assert ctx["total_debt"] == 17000
    assert ctx["total_fixed_costs"] == 12100
    assert len(st2.json()["recent_events"]) >= 1


def test_disconnect(session):
    r = session.delete(f"{BASE}/api/erp-integration", timeout=30)
    assert r.status_code == 200, r.text
    st = session.get(f"{BASE}/api/erp-integration/status", timeout=30)
    assert st.status_code == 200
    assert st.json()["connected"] is False


def test_inbound_rejects_invalid_token(session):
    """Webhook should reject requests with wrong/missing token."""
    # First connect to get a webhook URL
    unique = uuid.uuid4().hex[:8]
    payload = {
        "system_name": f"Test ERP {unique}",
        "auth_header_name": "X-ERP-Token",
        "api_token": f"correct-token-{unique}",
    }
    r = session.post(f"{BASE}/api/erp-integration/connect", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    webhook_url = r.json()["connection"]["webhook_url"]

    # Test with wrong token
    fin_payload = {"cash_balance": 10000, "total_debt": 5000}
    r_wrong = requests.post(webhook_url, json=fin_payload, headers={"X-ERP-Token": "wrong-token"}, timeout=30)
    assert r_wrong.status_code == 401, f"Expected 401 for wrong token, got {r_wrong.status_code}"

    # Test with missing token
    r_missing = requests.post(webhook_url, json=fin_payload, timeout=30)
    assert r_missing.status_code == 401, f"Expected 401 for missing token, got {r_missing.status_code}"

    # Cleanup
    session.delete(f"{BASE}/api/erp-integration", timeout=30)


def test_inbound_rejects_invalid_payload(session):
    """Webhook should reject payloads without meaningful financial data."""
    unique = uuid.uuid4().hex[:8]
    payload = {
        "system_name": f"Test ERP {unique}",
        "auth_header_name": "X-ERP-Token",
        "generate_token": True,
    }
    r = session.post(f"{BASE}/api/erp-integration/connect", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    webhook_url = r.json()["connection"]["webhook_url"]
    token = r.json()["generated_token"]

    # Test with empty payload (no financial data)
    r_empty = requests.post(webhook_url, json={"event_id": "test-empty"}, headers={"X-ERP-Token": token}, timeout=30)
    assert r_empty.status_code == 400, f"Expected 400 for empty payload, got {r_empty.status_code}"

    # Test with invalid JSON
    r_invalid = requests.post(webhook_url, data="not json", headers={"X-ERP-Token": token, "Content-Type": "application/json"}, timeout=30)
    assert r_invalid.status_code == 400, f"Expected 400 for invalid JSON, got {r_invalid.status_code}"

    # Cleanup
    session.delete(f"{BASE}/api/erp-integration", timeout=30)


def test_finance_profile_uses_erp_context(session):
    """GET /api/finance/profile should merge ERP context when active."""
    # Connect ERP and send financial data
    unique = uuid.uuid4().hex[:8]
    connect_payload = {
        "system_name": f"Test ERP {unique}",
        "auth_header_name": "X-ERP-Token",
        "generate_token": True,
    }
    r = session.post(f"{BASE}/api/erp-integration/connect", json=connect_payload, timeout=30)
    assert r.status_code == 200, r.text
    webhook_url = r.json()["connection"]["webhook_url"]
    token = r.json()["generated_token"]

    # Send financial data via webhook
    fin_payload = {
        "event_id": f"fin-{unique}",
        "cash_balance": 55000,
        "total_debt": 22000,
        "monthly_revenue": 40000,
        "fixed_costs": [{"name": "Renda", "amount": 4000}, {"name": "Salários", "amount": 12000}],
    }
    r_inbound = requests.post(webhook_url, json=fin_payload, headers={"X-ERP-Token": token}, timeout=30)
    assert r_inbound.status_code == 200, r_inbound.text

    # Check finance profile includes ERP context
    r_profile = session.get(f"{BASE}/api/finance/profile", timeout=30)
    assert r_profile.status_code == 200, r_profile.text
    profile = r_profile.json()
    assert profile["has_external_context"] is True
    assert profile["cash_balance"] == 55000
    assert profile["total_debt"] == 22000
    assert profile["monthly_revenue"] == 40000

    # Cleanup
    session.delete(f"{BASE}/api/erp-integration", timeout=30)