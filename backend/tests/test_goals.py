"""Tests for 'A Minha Meta' goals feature: GET/POST /api/goal + /api/goal/plan.
Deterministic math + premium gating + on-demand AI plan.
"""
import os
import uuid
import time
import pytest
import requests

BASE_URL = (os.environ.get('REACT_APP_BACKEND_URL') or 'https://conexao-simples.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "adminceoai@gmail.com"
ADMIN_PASSWORD = "12345"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def free_session():
    s = requests.Session()
    email = f"TEST_free_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={"email": email, "password": "Test12345!", "name": "Free User"})
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    return s, email


# ---- Premium gating ----
def test_goal_requires_premium(free_session):
    s, _ = free_session
    r = s.get(f"{API}/goal")
    assert r.status_code == 402, f"expected 402 for free user, got {r.status_code}: {r.text}"

    r = s.post(f"{API}/goal", json={"target_value": 1000000})
    assert r.status_code == 402

    r = s.post(f"{API}/goal/plan")
    assert r.status_code == 402


# ---- GET /goal (empty) ----
def test_get_goal_admin_initial(admin_session):
    r = admin_session.get(f"{API}/goal")
    assert r.status_code == 200
    data = r.json()
    assert "currency_symbol" in data
    assert "current_value" in data
    assert "goal" in data
    # If already configured from previous test runs, that's fine; just validate schema


# ---- POST /goal + deterministic math validation ----
def test_save_goal_and_compute(admin_session):
    payload = {
        "target_value": 1000000,
        "target_revenue": 500000,
        "ytd_revenue": 120000,
        "ytd_as_of": "2026-06",
        "deadline_type": "years",
        "deadline_years": 3,
    }
    r = admin_session.post(f"{API}/goal", json=payload)
    assert r.status_code == 200, r.text
    assert r.json().get("ok") is True

    # GET back and verify determinism
    r = admin_session.get(f"{API}/goal")
    assert r.status_code == 200
    d = r.json()
    assert d["configured"] is True
    # annualized_revenue = 120000/6*12 = 240000
    assert d["annualized_revenue"] == 240000, f"expected 240000 got {d['annualized_revenue']}"
    assert d["months_elapsed"] == 6

    rg = d["revenue_goal"]
    assert rg["target"] == 500000
    assert rg["projected_year_end"] == 240000
    assert abs(rg["pct"] - 48.0) < 0.5, f"pct={rg['pct']}"
    assert abs(rg["gap"] - 260000) < 1, f"gap={rg['gap']}"

    vg = d["value_goal"]
    assert vg["target"] == 1000000
    # needed_per_year = (1000000 - current_value) / 3  ; admin likely 0 current_value
    # We accept ~333333 when current_value = 0
    if d["current_value"] == 0:
        assert abs(vg["needed_per_year"] - 333333.33) < 1, f"needed_per_year={vg['needed_per_year']}"
    # milestones: at least 3
    assert len(vg["milestones"]) >= 3
    years = [m["year"] for m in vg["milestones"]]
    from datetime import datetime, timezone
    ny = datetime.now(timezone.utc).year
    assert years[0] == ny + 1


# ---- Deadline by DATE ----
def test_save_goal_deadline_by_date(admin_session):
    payload = {
        "target_value": 1000000,
        "target_revenue": 500000,
        "ytd_revenue": 120000,
        "ytd_as_of": "2026-06",
        "deadline_type": "date",
        "deadline_date": "2029-01",
    }
    r = admin_session.post(f"{API}/goal", json=payload)
    assert r.status_code == 200
    r = admin_session.get(f"{API}/goal")
    d = r.json()
    assert d["configured"] is True
    # years_left roughly (2029-01 - now) / 365.25 -> ~3 years
    assert d["years_left"] > 2.0 and d["years_left"] < 4.5, f"years_left={d['years_left']}"
    assert d["goal"]["deadline_type"] == "date"


# ---- Persistence: goal survives ----
def test_goal_persistence(admin_session):
    r = admin_session.get(f"{API}/goal")
    d = r.json()
    assert d["goal"]["target_value"] == 1000000
    assert d["goal"]["target_revenue"] == 500000


# ---- Plan on-demand ----
def test_goal_plan_on_demand(admin_session):
    # Re-save with years deadline first to ensure configured
    admin_session.post(f"{API}/goal", json={
        "target_value": 1000000, "target_revenue": 500000,
        "ytd_revenue": 120000, "ytd_as_of": "2026-06",
        "deadline_type": "years", "deadline_years": 3,
    })
    r = admin_session.post(f"{API}/goal/plan", timeout=90)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("configured") is True
    plan = d.get("ceo_plan") or {}
    # AI returns dict-like; at least one of expected keys
    assert isinstance(plan, dict), f"plan not dict: {plan}"
    has_any = any(k in plan for k in ("diagnostico", "veredicto", "acoes", "frase"))
    assert has_any, f"plan missing keys: {plan}"
