"""
CEO AI - Backend integration tests.
Covers auth, company, DNA, entries, dashboard, briefing, chat streaming,
score, future, memories, settings.
"""
import os
import json
import uuid
import time
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else None
# Fallback for pytest execution when only backend env is available
if not BASE_URL:
    # read from frontend env
    envp = "/app/frontend/.env"
    with open(envp) as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                break

API = f"{BASE_URL}/api"
ADMIN_EMAIL = "obeliscoradical@gmail.com"
ADMIN_PWD = "CeoAI2026!"


# ---------- fixtures ----------
@pytest.fixture(scope="session")
def admin_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PWD}, timeout=30)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    data = r.json()
    assert data["email"] == ADMIN_EMAIL
    assert "id" in data
    return s


@pytest.fixture(scope="session")
def new_user_session():
    """Register a new random user for register->onboarding tests."""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    email = f"test_{uuid.uuid4().hex[:10]}@example.com"
    r = s.post(f"{API}/auth/register", json={"email": email, "password": "Passw0rd!", "name": "Test User"}, timeout=30)
    assert r.status_code == 200, f"Register failed: {r.status_code} {r.text}"
    data = r.json()
    assert data["email"] == email
    assert data["role"] == "owner"
    s.email = email  # type: ignore[attr-defined]
    s.uid = data["id"]  # type: ignore[attr-defined]
    return s


# ---------- Auth ----------
class TestAuth:
    def test_login_admin(self, admin_session):
        r = admin_session.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 200
        me = r.json()
        assert me["email"] == ADMIN_EMAIL
        assert "id" in me
        assert "password_hash" not in me
        assert "_id" not in me

    def test_login_invalid(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"}, timeout=15)
        assert r.status_code == 401
        assert "detail" in r.json()

    def test_me_no_cookie(self):
        r = requests.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 401

    def test_register_new_user_and_me(self, new_user_session):
        r = new_user_session.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 200
        me = r.json()
        assert me["email"] == new_user_session.email
        assert me["role"] == "owner"

    def test_register_duplicate(self, new_user_session):
        r = new_user_session.post(f"{API}/auth/register", json={"email": new_user_session.email, "password": "x", "name": "y"}, timeout=15)
        assert r.status_code == 400

    def test_logout_clears_cookie(self):
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PWD}, timeout=15)
        assert r.status_code == 200
        r = s.post(f"{API}/auth/logout", timeout=15)
        assert r.status_code == 200
        r = s.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 401

    def test_google_session_no_header(self):
        r = requests.post(f"{API}/auth/session", timeout=15)
        assert r.status_code == 400


# ---------- Onboarding: Company + DNA ----------
class TestOnboarding:
    def test_save_company(self, admin_session):
        payload = {"name": "TEST_Silva & Filhos", "region": "PT", "currency": "EUR", "sector": "Serviços",
                   "employees_count": 3, "clients_count": 12, "bank_balance": 5000, "monthly_tax_estimate": 800}
        r = admin_session.post(f"{API}/company", json=payload, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == payload["name"]
        assert data["employees_count"] == 3
        # verify persisted
        r2 = admin_session.get(f"{API}/company", timeout=15)
        assert r2.status_code == 200
        c = r2.json()
        assert c["name"] == payload["name"]
        assert c["employees_count"] == 3
        assert "_id" not in c

    def test_save_dna(self, admin_session):
        payload = {"answers": {"foo": "bar"}, "dream": "Liberdade financeira",
                   "target_revenue": 1000000, "work_hours": "40h",
                   "exit_plan": "crescer", "five_year_vision": "1M em faturação",
                   "ceo_mode": "crescimento"}
        r = admin_session.post(f"{API}/dna", json=payload, timeout=15)
        assert r.status_code == 200
        assert r.json()["completed"] is True
        # verify
        r2 = admin_session.get(f"{API}/dna", timeout=15)
        assert r2.status_code == 200
        d = r2.json()
        assert d["completed"] is True
        assert d["dream"] == payload["dream"]


# ---------- Entries ----------
class TestEntries:
    def test_create_income_and_list(self, admin_session):
        r = admin_session.post(f"{API}/entries", json={
            "type": "income", "category": "Serviço", "amount": 2500, "date": "2026-01-05",
            "description": "TEST_receita"}, timeout=15)
        assert r.status_code == 200
        eid = r.json()["id"]
        assert eid
        r2 = admin_session.get(f"{API}/entries", timeout=15)
        assert r2.status_code == 200
        ids = [e["id"] for e in r2.json()]
        assert eid in ids

    def test_create_expense_and_delete(self, admin_session):
        r = admin_session.post(f"{API}/entries", json={
            "type": "expense", "category": "Renda", "amount": 500, "date": "2026-01-04",
            "description": "TEST_despesa"}, timeout=15)
        assert r.status_code == 200
        eid = r.json()["id"]
        r = admin_session.delete(f"{API}/entries/{eid}", timeout=15)
        assert r.status_code == 200
        r2 = admin_session.get(f"{API}/entries", timeout=15)
        ids = [e["id"] for e in r2.json()]
        assert eid not in ids

    def test_import_csv_ai(self, admin_session):
        csv_text = "tipo,categoria,valor,data,descricao\nreceita,Consultoria,3500,2026-01-06,Cliente TEST\ndespesa,Salário,1200,2026-01-06,Salário técnico TEST\n"
        files = {"file": ("test.csv", csv_text.encode("utf-8"), "text/csv")}
        # remove Content-Type json header for multipart
        s = requests.Session()
        s.cookies.update(admin_session.cookies)
        r = s.post(f"{API}/entries/import", files=files, timeout=90)
        assert r.status_code == 200, r.text
        assert r.json().get("imported", 0) >= 1


# ---------- Dashboard / Snapshot ----------
class TestDashboard:
    def test_dashboard_shape(self, admin_session):
        r = admin_session.get(f"{API}/dashboard", timeout=30)
        assert r.status_code == 200
        d = r.json()
        for k in ("health", "vitals", "company_value", "goal_value", "progress", "currency_symbol"):
            assert k in d, f"missing {k}"
        assert isinstance(d["vitals"], list) and len(d["vitals"]) == 7
        keys = {v["key"] for v in d["vitals"]}
        assert keys == {"cashflow", "profit", "clients", "tax", "employees", "bank", "risk"}
        for v in d["vitals"]:
            assert v["status"] in {"green", "amber", "red"}
        assert 0 <= d["health"] <= 100


# ---------- Briefing (AI) ----------
class TestBriefing:
    def test_briefing_ai(self, admin_session):
        r = admin_session.get(f"{API}/briefing", timeout=90)
        assert r.status_code == 200
        b = r.json()
        assert "greeting" in b and isinstance(b["greeting"], str) and len(b["greeting"]) > 5
        assert "items" in b and isinstance(b["items"], list)
        assert len(b["items"]) >= 1
        for it in b["items"]:
            assert "title" in it and "detail" in it and "priority" in it


# ---------- Chat streaming ----------
class TestChatStreaming:
    def test_chat_stream(self, admin_session):
        # streaming: use requests with stream=True
        s = requests.Session()
        s.cookies.update(admin_session.cookies)
        with s.post(f"{API}/chat", json={"message": "Diz apenas 'ola' brevemente."},
                    stream=True, timeout=120) as r:
            assert r.status_code == 200
            deltas = []
            done_seen = False
            sid = None
            for line in r.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("data:"):
                    try:
                        obj = json.loads(line[5:].strip())
                    except Exception:
                        continue
                    if "delta" in obj:
                        deltas.append(obj["delta"])
                    if obj.get("done"):
                        done_seen = True
                        sid = obj.get("session_id")
                        break
            assert done_seen, "Stream did not complete"
            assert sid, "No session_id in done event"
            assert len("".join(deltas)) > 0, "No content streamed"


# ---------- Score ----------
class TestScore:
    def test_score(self, admin_session):
        r = admin_session.get(f"{API}/score", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "overall" in d and isinstance(d["overall"], int)
        assert "dimensions" in d and len(d["dimensions"]) == 8
        names = {x["dimension"] for x in d["dimensions"]}
        for req in ["Liderança", "Financeiro", "Marketing", "Operação", "Clientes", "Funcionários", "Risco", "Inovação"]:
            assert req in names


# ---------- Future ----------
class TestFuture:
    def test_future_projection(self, admin_session):
        r = admin_session.get(f"{API}/future", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "projection" in d and len(d["projection"]) == 12
        for p in d["projection"]:
            assert "month" in p and "cash" in p
        assert "monthly_net" in d

    def test_future_simulate(self, admin_session):
        r = admin_session.post(f"{API}/future/simulate",
                               json={"scenario": "contratar", "detail": "contratar 1 técnico a 1200€/mês"},
                               timeout=120)
        assert r.status_code == 200
        d = r.json()
        for k in ("verdict", "summary", "recommendation"):
            assert k in d, f"missing {k}"
        assert d["verdict"] in {"favoravel", "cautela", "desaconselhado"}


# ---------- Memories ----------
class TestMemories:
    def test_memory_crud(self, admin_session):
        r = admin_session.post(f"{API}/memories", json={"content": "TEST_memoria xyz", "category": "geral"}, timeout=15)
        assert r.status_code == 200
        mid = r.json()["id"]
        r = admin_session.get(f"{API}/memories", timeout=15)
        assert r.status_code == 200
        assert any(m["id"] == mid for m in r.json())
        r = admin_session.delete(f"{API}/memories/{mid}", timeout=15)
        assert r.status_code == 200
        r = admin_session.get(f"{API}/memories", timeout=15)
        assert not any(m["id"] == mid for m in r.json())


# ---------- Settings ----------
class TestSettings:
    def test_settings_get_defaults(self, admin_session):
        r = admin_session.get(f"{API}/settings", timeout=15)
        assert r.status_code == 200
        s = r.json()
        for k in ("ceo_mode", "theme", "briefing_count", "briefing_tone", "model"):
            assert k in s

    def test_settings_update(self, admin_session):
        payload = {"ceo_mode": "agressivo", "model": "claude", "theme": "dark",
                   "briefing_count": 5, "briefing_tone": "direto"}
        r = admin_session.put(f"{API}/settings", json=payload, timeout=15)
        assert r.status_code == 200
        s = r.json()
        assert s["ceo_mode"] == "agressivo"
        assert s["briefing_count"] == 5
        assert s["model"] == "claude"
        # verify persisted
        r2 = admin_session.get(f"{API}/settings", timeout=15)
        assert r2.json()["ceo_mode"] == "agressivo"
