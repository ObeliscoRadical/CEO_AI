"""Tests for Apoios & Incentivos (Grants) endpoints — iteration 33."""
import os
import time
import requests
import pytest

def _read_env():
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("REACT_APP_BACKEND_URL not found")

BASE = (os.environ.get("REACT_APP_BACKEND_URL") or _read_env()).rstrip("/")
ADMIN_EMAIL = "adminceoai@gmail.com"
ADMIN_PASSWORD = "12345"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, r.text
    return s


# ------------------- Profile -------------------
def test_get_profile(session):
    r = session.get(f"{BASE}/api/grants/profile", timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "profile" in d and "countries" in d
    codes = {c["code"] for c in d["countries"]}
    assert codes == {"PT", "BR"}
    p = d["profile"]
    for f in ["country", "sector", "size", "employees", "annual_revenue", "missing"]:
        assert f in p


def test_post_profile_updates_focus_country(session):
    r = session.post(f"{BASE}/api/grants/profile", json={
        "focus_country": "BR",
        "investment_amount": 25000,
        "project_type": "digitalização",
        "interests": ["fundo", "financiamento"],
    }, timeout=30)
    assert r.status_code == 200, r.text
    p = r.json()["profile"]
    assert p["country"] == "BR"
    assert p["investment_amount"] == 25000
    assert p["project_type"] == "digitalização"
    assert set(p["interests"]) == {"fundo", "financiamento"}
    # Reset to PT for subsequent tests
    session.post(f"{BASE}/api/grants/profile", json={"focus_country": "PT"}, timeout=30)


# ------------------- Opportunities -------------------
def test_opportunities_pt_count_and_shape(session):
    r = session.get(f"{BASE}/api/grants/opportunities?country=PT", timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["country"] == "PT"
    opps = d["opportunities"]
    assert len(opps) == 10, f"PT should have 10 opps, got {len(opps)}"
    # sorted desc
    scores = [o["score"] for o in opps]
    assert scores == sorted(scores, reverse=True)
    o = opps[0]
    for f in ["title", "entity", "type_label", "amount", "deadline", "url",
              "documents", "match_reasons", "warnings", "eligibility",
              "eligibility_label", "verified_at", "tracked"]:
        assert f in o, f"missing {f}"
    assert o["eligibility"] in ("elegivel", "possivel", "confirmar")


def test_opportunities_br_count(session):
    r = session.get(f"{BASE}/api/grants/opportunities?country=BR", timeout=30)
    assert r.status_code == 200
    opps = r.json()["opportunities"]
    assert len(opps) == 8, f"BR should have 8 opps, got {len(opps)}"


# ------------------- Applications CRUD -------------------
@pytest.fixture(scope="module")
def created_app(session):
    r = session.post(f"{BASE}/api/grants/applications", json={"grant_id": "pt_vale_digital"}, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["application"]["grant_id"] == "pt_vale_digital"
    assert len(d["application"]["checklist"]) > 0
    assert len(d["application"]["steps"]) > 0
    aid = d["application"]["id"]
    yield aid
    # cleanup
    try:
        session.delete(f"{BASE}/api/grants/applications/{aid}", timeout=30)
    except Exception:
        pass


def test_create_application_idempotent(session, created_app):
    r = session.post(f"{BASE}/api/grants/applications", json={"grant_id": "pt_vale_digital"}, timeout=30)
    assert r.status_code == 200
    assert r.json().get("already") is True


def test_list_applications(session, created_app):
    r = session.get(f"{BASE}/api/grants/applications", timeout=30)
    assert r.status_code == 200
    d = r.json()
    ids = [a["id"] for a in d["applications"]]
    assert created_app in ids
    status_codes = {s["code"] for s in d["statuses"]}
    assert {"a_preparar", "submetida", "em_analise", "aprovada", "recusada"} == status_codes


def test_patch_application_status_and_deadline(session, created_app):
    r = session.patch(f"{BASE}/api/grants/applications/{created_app}",
                      json={"status": "submetida", "deadline": "2026-12-01", "notes": "teste"}, timeout=30)
    assert r.status_code == 200
    a = r.json()["application"]
    assert a["status"] == "submetida"
    assert a["deadline"] == "2026-12-01"
    assert a["notes"] == "teste"


def test_patch_application_invalid_status(session, created_app):
    r = session.patch(f"{BASE}/api/grants/applications/{created_app}",
                      json={"status": "invalid_xyz"}, timeout=30)
    assert r.status_code == 400


def test_patch_application_not_found(session):
    # valid ObjectId format but nonexistent
    r = session.patch(f"{BASE}/api/grants/applications/507f1f77bcf86cd799439011",
                      json={"status": "submetida"}, timeout=30)
    assert r.status_code == 404


def test_toggle_checklist_and_steps(session, created_app):
    r = session.post(f"{BASE}/api/grants/applications/{created_app}/toggle",
                     json={"kind": "checklist", "index": 0}, timeout=30)
    assert r.status_code == 200
    assert r.json()["application"]["checklist"][0]["done"] is True
    r2 = session.post(f"{BASE}/api/grants/applications/{created_app}/toggle",
                      json={"kind": "steps", "index": 1}, timeout=30)
    assert r2.status_code == 200
    assert r2.json()["application"]["steps"][1]["done"] is True


# ------------------- Alerts -------------------
def test_run_alert_eval_creates_notification(session, created_app):
    # Set deadline within 30 days
    from datetime import date, timedelta
    dl = (date.today() + timedelta(days=10)).isoformat()
    session.patch(f"{BASE}/api/grants/applications/{created_app}",
                  json={"deadline": dl, "status": "a_preparar"}, timeout=30)
    r = session.post(f"{BASE}/api/grants/run-alert-eval", timeout=30)
    assert r.status_code == 200
    created = r.json().get("created", 0)
    # first run should create at least 1
    # Now verify notifications endpoint
    n = session.get(f"{BASE}/api/crm/notifications", timeout=30)
    assert n.status_code == 200
    notifs = n.json() if isinstance(n.json(), list) else n.json().get("notifications", [])
    apoio = [x for x in notifs if x.get("type") == "apoio_prazo"]
    assert len(apoio) >= 1, "no apoio_prazo notifications found"


def test_delete_application(session):
    r = session.post(f"{BASE}/api/grants/applications", json={"grant_id": "pt_sifide"}, timeout=30)
    aid = r.json()["application"]["id"]
    r2 = session.delete(f"{BASE}/api/grants/applications/{aid}", timeout=30)
    assert r2.status_code == 200


# ------------------- Analyze (AI, slow) -------------------
def test_analyze_ai(session):
    r = session.post(f"{BASE}/api/grants/analyze", json={"country": "PT"}, timeout=90)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "analysis" in d
    if d["analysis"]:
        a = d["analysis"]
        for f in ["resumo", "prioridade", "lacunas", "oportunidades", "proximo_passo", "aviso"]:
            assert f in a, f"missing {f} in analysis"
        assert isinstance(a["oportunidades"], list)
