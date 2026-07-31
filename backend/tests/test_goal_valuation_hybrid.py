"""Backend tests for hybrid valuation engine on /api/goal (iteration 29).
Covers 3 methods (auto, revenue, ebitda), custom multiple persistence, and clear."""
import os
import pytest
import requests

def _load_frontend_env():
    p = "/app/frontend/.env"
    if os.path.exists(p):
        for line in open(p):
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    return None

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _load_frontend_env()).rstrip("/")
ADMIN_EMAIL = "adminceoai@gmail.com"
ADMIN_PASSWORD = "12345"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return s


def _get_goal(client):
    r = client.get(f"{BASE_URL}/api/goal", timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


def _post_goal(client, payload):
    r = client.post(f"{BASE_URL}/api/goal", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


# --- 1. Baseline: valuation object structure ---
def test_valuation_object_structure(client):
    # reset to auto first
    _post_goal(client, {"valuation_method": "auto", "value_multiple_custom": None})
    data = _get_goal(client)
    v = data.get("valuation")
    assert isinstance(v, dict), "valuation missing"
    for k in ("method", "used_multiple", "custom", "ebitda", "ebitda_source", "suggestions"):
        assert k in v, f"missing key {k} in valuation: {v}"
    sug = v["suggestions"]
    assert "sector_label" in sug and "region" in sug
    for method_key in ("revenue", "ebitda"):
        assert method_key in sug
        for f in ("suggested", "min", "max"):
            assert f in sug[method_key]
    # admin has no sector -> defaults
    assert sug["sector_label"] == "Geral"
    assert sug["region"] == "Portugal / Europa"
    assert sug["revenue"]["suggested"] == 1.0
    assert sug["ebitda"]["suggested"] == 5.0


# --- 2. Method 'revenue' ---
def test_method_revenue(client):
    _post_goal(client, {"valuation_method": "revenue", "value_multiple_custom": None})
    data = _get_goal(client)
    v = data["valuation"]
    assert v["method"] == "revenue"
    assert v["custom"] is False
    used = v["used_multiple"]
    assert used == 1.0
    rev = data.get("current_revenue")
    assert rev and rev > 0, "admin should have YTD-annualized revenue"
    assert abs(data["current_value"] - round(rev * used, 2)) < 1.0
    if data.get("configured"):
        req = data["required"]
        target = data["target_value"]
        assert abs(req["required_revenue"] - target / used) < 1.0
        assert abs(req["required_monthly_revenue"] - target / used / 12) < 1.0


# --- 3. Method 'ebitda' with custom multiple 6 ---
def test_method_ebitda_custom_multiple(client):
    _post_goal(client, {"valuation_method": "ebitda", "value_multiple_custom": 6})
    data = _get_goal(client)
    v = data["valuation"]
    assert v["method"] == "ebitda"
    assert v["custom"] is True
    assert v["used_multiple"] == 6.0
    ebitda = v.get("ebitda")
    assert ebitda and ebitda > 0, "expected estimated ebitda for admin"
    assert v["ebitda_source"] in ("documento oficial", "estimado (a partir do lucro líquido)")
    assert abs(data["current_value"] - round(ebitda * 6, 2)) < 1.0
    if data.get("configured"):
        req = data["required"]
        target = data["target_value"]
        assert "required_ebitda" in req
        assert abs(req["required_ebitda"] - target / 6) < 1.0
        assert "ebitda_margin" in req and req["ebitda_margin"] > 0


# --- 4. Persistence: target_value only (exclude_unset) preserves custom multiple ---
def test_custom_multiple_persists_on_partial_post(client):
    # set custom = 7 for ebitda
    _post_goal(client, {"valuation_method": "ebitda", "value_multiple_custom": 7})
    before = _get_goal(client)
    assert before["valuation"]["used_multiple"] == 7.0
    assert before["valuation"]["custom"] is True

    # now post only target_value (simulate "Calcular Projeção")
    _post_goal(client, {"target_value": 750000, "deadline_type": "years", "deadline_years": 5})
    after = _get_goal(client)
    assert after["valuation"]["method"] == "ebitda", "method must persist"
    assert after["valuation"]["used_multiple"] == 7.0, "custom multiple must persist"
    assert after["valuation"]["custom"] is True


# --- 5. Explicit null clears custom override ---
def test_null_custom_clears_override(client):
    _post_goal(client, {"valuation_method": "ebitda", "value_multiple_custom": 7})
    _post_goal(client, {"value_multiple_custom": None})
    data = _get_goal(client)
    assert data["valuation"]["custom"] is False
    # should fall back to suggested (5.0 for 'Geral')
    assert data["valuation"]["used_multiple"] == 5.0


# --- 6. Method 'auto' returns to automatic engine ---
def test_method_auto(client):
    _post_goal(client, {"valuation_method": "auto", "value_multiple_custom": None})
    data = _get_goal(client)
    v = data["valuation"]
    assert v["method"] == "auto"
    assert v["custom"] is False
    # value should come from the automatic engine (patrimonio + rendimento)
    # not equal to revenue * 1.0 unless coincidence — just assert it's numeric
    assert isinstance(data["current_value"], (int, float))


# --- 7. Regression: share endpoint still works ---
def test_share_regression(client):
    _post_goal(client, {"target_value": 750000, "deadline_type": "years", "deadline_years": 5})
    r = client.post(f"{BASE_URL}/api/goal/share", timeout=30)
    assert r.status_code == 200
    j = r.json()
    assert j.get("ok") is True
    tok = j["token"]
    # public endpoint (no auth)
    pub = requests.get(f"{BASE_URL}/api/goal/share/{tok}", timeout=30)
    assert pub.status_code == 200
    body = pub.json()
    assert "data" in body and body["data"].get("valuation")
