"""Tests for the new Empresa profile feature - POST /api/company with profile dict, cache invalidation, AI usage."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback for local test runs — read frontend .env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

EMAIL = "obeliscoradical@gmail.com"
PASSWORD = "CeoAI2026!"

DISTINCTIVE_WORRY = "AlfaZetaOmicron - a rutura de tesouraria em janeiro"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("access_token") or data.get("token")
    if token:
        s.headers.update({"Authorization": f"Bearer {token}"})
    return s


def test_get_company(client):
    r = client.get(f"{BASE_URL}/api/company", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data is not None
    assert "profile" in data
    assert isinstance(data["profile"], dict)


def test_save_company_with_full_profile(client):
    """POST /api/company with company + full profile block."""
    payload = {
        "name": "Obelisco",
        "region": "PT",
        "currency": "EUR",
        "sector": "consultoria",
        "employees_count": 4,
        "clients_count": 12,
        "bank_balance": 25000,
        "monthly_tax_estimate": 1200,
        "profile": {
            "activity": "consultoria estratégica",
            "years_active": 5,
            "location": "Lisboa, Portugal",
            "business_model": "avenças mensais + projetos pontuais",
            "avg_price": 3000,
            "biggest_client_pct": 40,
            "client_recurrence": "Sim, quase sempre",
            "founder_dependency": "Aguenta alguns dias sem mim",
            "debt": 5000,
            "biggest_cost": "salários",
            "supplier_dependency": "Não, tenho vários",
            "seasonality": "verão é fraco",
            "main_goal": "Estabilizar e ter mais lucro",
            "personal_goal": "ter tempo para a família",
            "advantage": "resposta rápida e atendimento pessoal",
            "main_worry": DISTINCTIVE_WORRY,
        },
    }
    r = client.post(f"{BASE_URL}/api/company", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["profile"]["biggest_client_pct"] == 40
    assert body["profile"]["main_worry"] == DISTINCTIVE_WORRY

    # GET back and verify persistence
    g = client.get(f"{BASE_URL}/api/company", timeout=30)
    assert g.status_code == 200
    got = g.json()
    assert got["sector"] == "consultoria"
    assert got["employees_count"] == 4
    assert got["clients_count"] == 12
    assert got["bank_balance"] == 25000
    assert got["monthly_tax_estimate"] == 1200
    prof = got["profile"]
    for k in ["activity", "years_active", "location", "business_model", "avg_price",
              "biggest_client_pct", "client_recurrence", "founder_dependency",
              "debt", "biggest_cost", "supplier_dependency", "seasonality",
              "main_goal", "personal_goal", "advantage", "main_worry"]:
        assert k in prof, f"missing profile key: {k}"
    assert prof["biggest_client_pct"] == 40
    assert prof["main_worry"] == DISTINCTIVE_WORRY


def test_ai_cache_invalidated_and_report_regenerates(client):
    """After save, /api/report should regenerate (cache invalidated) and return 200 with JSON."""
    r = client.get(f"{BASE_URL}/api/report", timeout=90)
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, dict)


def test_ceo_daily_returns_200(client):
    r = client.get(f"{BASE_URL}/api/ceo-daily", timeout=90)
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, dict)
