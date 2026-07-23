"""
Phase 2 tests: multi-company, chat sessions, premium gating,
Stripe checkout, mock bank connect, subscription.
"""
import os
import json
import pytest
import requests
from pymongo import MongoClient
from bson import ObjectId

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().strip('"')
                break
BASE_URL = BASE_URL.rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = "obeliscoradical@gmail.com"
ADMIN_PWD = "CeoAI2026!"

# Mongo direct (to reset premium at end + inspect)
MONGO_URL = None
DB_NAME = None
with open("/app/backend/.env") as f:
    for line in f:
        line = line.strip()
        if line.startswith("MONGO_URL="):
            MONGO_URL = line.split("=", 1)[1].strip().strip('"')
        if line.startswith("DB_NAME="):
            DB_NAME = line.split("=", 1)[1].strip().strip('"')

mongo = MongoClient(MONGO_URL) if MONGO_URL else None
mdb = mongo[DB_NAME] if mongo is not None and DB_NAME else None


@pytest.fixture(scope="session")
def admin_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    # Ensure clean premium state at start
    if mdb is not None:
        mdb.users.update_one({"email": ADMIN_EMAIL}, {"$set": {"is_premium": False}})
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PWD}, timeout=30)
    assert r.status_code == 200, r.text
    s.uid = r.json()["id"]  # type: ignore[attr-defined]
    return s


# ---------- Multi-company ----------
class TestCompanies:
    def test_list_companies_returns_active(self, admin_session):
        r = admin_session.get(f"{API}/companies", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "companies" in data and isinstance(data["companies"], list)
        assert "active_company_id" in data
        assert len(data["companies"]) >= 1
        for c in data["companies"]:
            assert "id" in c and "name" in c

    def test_create_second_company_and_isolation(self, admin_session):
        # Snapshot: entries + dashboard on current active
        r_list = admin_session.get(f"{API}/companies", timeout=15).json()
        original_active = r_list["active_company_id"]
        entries_before = admin_session.get(f"{API}/entries", timeout=15).json()
        dash_before = admin_session.get(f"{API}/dashboard", timeout=30).json()

        # Create a fresh test company
        payload = {"name": "TEST_Phase2 Nova", "region": "PT", "currency": "EUR",
                   "sector": "Tech", "employees_count": 1, "clients_count": 2,
                   "bank_balance": 1000, "monthly_tax_estimate": 100}
        rc = admin_session.post(f"{API}/companies", json=payload, timeout=15)
        assert rc.status_code == 200, rc.text
        new_c = rc.json()
        assert new_c["name"] == payload["name"]
        new_cid = new_c["id"]
        assert new_cid

        # Active should have switched (POST /companies sets active)
        r_after = admin_session.get(f"{API}/companies", timeout=15).json()
        assert r_after["active_company_id"] == new_cid

        # New company entries must be empty (isolation)
        entries_new = admin_session.get(f"{API}/entries", timeout=15).json()
        assert isinstance(entries_new, list)
        assert len(entries_new) == 0, f"New company should have 0 entries, got {len(entries_new)}"

        # Dashboard on new company: name changed, cash flows differ
        dash_new = admin_session.get(f"{API}/dashboard", timeout=30).json()
        assert dash_new["company_name"] == payload["name"]
        # totals should be zero on fresh company
        assert dash_new["total_income"] == 0 or dash_new["total_income"] != dash_before.get("total_income", -1)

        # Switch back to original
        r_switch = admin_session.put(f"{API}/companies/active",
                                     json={"company_id": original_active}, timeout=15)
        assert r_switch.status_code == 200
        assert r_switch.json()["active_company_id"] == original_active

        # Entries should be restored
        entries_back = admin_session.get(f"{API}/entries", timeout=15).json()
        assert len(entries_back) == len(entries_before)

        # Cleanup: delete new company
        rd = admin_session.delete(f"{API}/companies/{new_cid}", timeout=15)
        assert rd.status_code == 200

    def test_switch_to_invalid_company(self, admin_session):
        r = admin_session.put(f"{API}/companies/active",
                              json={"company_id": str(ObjectId())}, timeout=15)
        assert r.status_code == 404


# ---------- Chat sessions ----------
class TestChatSessions:
    def test_create_and_list_session(self, admin_session):
        # Send a short chat to create a session
        s = requests.Session()
        s.cookies.update(admin_session.cookies)
        with s.post(f"{API}/chat", json={"message": "TEST_phase2 diz apenas ok"},
                    stream=True, timeout=120) as r:
            assert r.status_code == 200
            sid = None
            for line in r.iter_lines(decode_unicode=True):
                if line and line.startswith("data:"):
                    try:
                        obj = json.loads(line[5:].strip())
                    except Exception:
                        continue
                    if obj.get("done"):
                        sid = obj.get("session_id")
                        break
            assert sid, "No session_id returned from chat stream"

        # List sessions
        r = admin_session.get(f"{API}/chat/sessions", timeout=15)
        assert r.status_code == 200
        sessions = r.json()
        assert isinstance(sessions, list)
        assert any(x["session_id"] == sid for x in sessions), "New session not in list"

        # Messages
        r = admin_session.get(f"{API}/chat/{sid}/messages", timeout=15)
        assert r.status_code == 200
        msgs = r.json()
        assert len(msgs) >= 2  # user + assistant
        assert any(m["role"] == "user" for m in msgs)
        assert any(m["role"] == "assistant" for m in msgs)

        # Delete
        r = admin_session.delete(f"{API}/chat/{sid}", timeout=15)
        assert r.status_code == 200

        # Verify removed
        r = admin_session.get(f"{API}/chat/sessions", timeout=15)
        assert not any(x["session_id"] == sid for x in r.json())


# ---------- Premium gating (before payment) ----------
class TestPremiumGatingBefore:
    def test_subscription_endpoint(self, admin_session):
        r = admin_session.get(f"{API}/subscription", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "is_premium" in d
        assert "plans" in d
        assert "premium_monthly" in d["plans"]
        assert "premium_yearly" in d["plans"]

    def test_future_gated_403(self, admin_session):
        # Ensure not premium
        if mdb is not None:
            mdb.users.update_one({"email": ADMIN_EMAIL}, {"$set": {"is_premium": False}})
        r = admin_session.get(f"{API}/future", timeout=15)
        assert r.status_code == 403
        assert r.json().get("detail") == "premium_required"

    def test_simulate_gated_403(self, admin_session):
        if mdb is not None:
            mdb.users.update_one({"email": ADMIN_EMAIL}, {"$set": {"is_premium": False}})
        r = admin_session.post(f"{API}/future/simulate",
                               json={"scenario": "contratar", "detail": "x"}, timeout=30)
        assert r.status_code == 403


# ---------- Stripe checkout ----------
class TestStripeCheckout:
    def test_checkout_monthly(self, admin_session):
        r = admin_session.post(f"{API}/payments/checkout",
                               json={"lookup_key": "premium_monthly",
                                     "origin_url": "https://example.com"},
                               timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "checkout_url" in d and d["checkout_url"].startswith("https://")
        assert "session_id" in d and d["session_id"].startswith("cs_")
        # persisted in payment_transactions
        if mdb is not None:
            rec = mdb.payment_transactions.find_one({"session_id": d["session_id"]})
            assert rec is not None
            assert rec["payment_status"] == "pending"
            assert rec["lookup_key"] == "premium_monthly"

    def test_checkout_yearly(self, admin_session):
        r = admin_session.post(f"{API}/payments/checkout",
                               json={"lookup_key": "premium_yearly",
                                     "origin_url": "https://example.com"},
                               timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["checkout_url"].startswith("https://")

    def test_checkout_invalid_lookup(self, admin_session):
        r = admin_session.post(f"{API}/payments/checkout",
                               json={"lookup_key": "does_not_exist",
                                     "origin_url": "https://example.com"},
                               timeout=30)
        assert r.status_code == 500

    def test_payment_status_pending(self, admin_session):
        # Create a fresh session and check status is pending (unpaid)
        r = admin_session.post(f"{API}/payments/checkout",
                               json={"lookup_key": "premium_monthly",
                                     "origin_url": "https://example.com"},
                               timeout=30)
        sid = r.json()["session_id"]
        rs = admin_session.get(f"{API}/payments/status/{sid}", timeout=30)
        assert rs.status_code == 200
        d = rs.json()
        assert d["payment_status"] in ("pending", "unpaid"), d


# ---------- Premium activation (simulated via direct DB flip) ----------
class TestPremiumAfterActivation:
    """We cannot fully complete Stripe checkout in a headless env, so we simulate
    the effect of a successful payment by flipping is_premium via DB (which is
    exactly what /payments/status does when Stripe reports 'paid'). We then verify
    the API surfaces the premium features."""

    def test_activate_and_access_future(self, admin_session):
        assert mdb is not None
        mdb.users.update_one({"email": ADMIN_EMAIL}, {"$set": {"is_premium": True}})

        # subscription reflects premium
        r = admin_session.get(f"{API}/subscription", timeout=15)
        assert r.json()["is_premium"] is True

        # /future now returns 200 with projection
        r = admin_session.get(f"{API}/future", timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "projection" in d and len(d["projection"]) == 12

        # /future/simulate now returns 200
        r = admin_session.post(f"{API}/future/simulate",
                               json={"scenario": "contratar",
                                     "detail": "1 técnico a 1200€/mês"},
                               timeout=120)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("verdict") in {"favoravel", "cautela", "desaconselhado"}
        assert "summary" in d


# ---------- Mock bank connect ----------
class TestBankConnect:
    def test_bank_connect_imports_movements(self, admin_session):
        # entries before
        before = admin_session.get(f"{API}/entries", timeout=15).json()
        count_before = len(before)
        r = admin_session.post(f"{API}/bank/connect", timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("connected") is True
        assert d.get("imported", 0) >= 30, f"Expected ~40-50 movements, got {d.get('imported')}"
        # Company now marked bank_connected
        cs = admin_session.get(f"{API}/companies", timeout=15).json()
        active = [c for c in cs["companies"] if c["id"] == cs["active_company_id"]]
        assert active and active[0]["bank_connected"] is True
        # entries increased by that amount
        after = admin_session.get(f"{API}/entries", timeout=15).json()
        assert len(after) - count_before == d["imported"]

        # Cleanup: remove demo entries just inserted (by description marker)
        if mdb is not None:
            mdb.entries.delete_many({"user_id": admin_session.uid,
                                     "description": "Movimento bancário (demo)"})


# ---------- Cleanup fixture (session end) ----------
@pytest.fixture(scope="session", autouse=True)
def _reset_premium_at_end():
    yield
    if mdb is not None:
        mdb.users.update_one({"email": ADMIN_EMAIL}, {"$set": {"is_premium": False}})
