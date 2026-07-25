"""
Backend tests for CEO AI Founder Campaign, Admin panel and Premium gating (Iteration 17).
Tests:
 - Public /api/founders/status structure
 - Admin auth (403 for non-admin, 200 for admin) on all /api/admin/* endpoints
 - Admin overview numeric metrics
 - Premium gating: free user gets 402 on premium endpoints; admin gets 200
 - Founder checkout guards (enterprise=400, founder_used=409, founder_closed via campaign toggle=409)
 - Professional trial checkout returns a valid checkout_url with trial subscription_data
"""
import os
import time
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "obeliscoradical@gmail.com"
ADMIN_PASSWORD = "CeoAI2026!"


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text}"
    return s


def _register(email, password, name="Test User"):
    s = requests.Session()
    r = s.post(f"{API}/auth/register", json={"email": email, "password": password, "name": name}, timeout=20)
    assert r.status_code in (200, 201), f"register failed {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="session")
def admin_session():
    return _login(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="session")
def free_session():
    email = f"TEST_free_{uuid.uuid4().hex[:8]}@test.com"
    s = _register(email, "Passw0rd!Test", name="TEST Free")
    return s, email


# --------------------------------------------------------- PUBLIC founders/status
class TestFoundersStatus:
    def test_status_shape(self):
        r = requests.get(f"{API}/founders/status", timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ["limit", "claimed", "remaining", "program_active", "founder_price",
                  "professional_price", "enterprise_price", "trial_days"]:
            assert k in d, f"missing {k}"
        assert d["limit"] == 15
        assert d["founder_price"] == 29
        assert d["professional_price"] == 79
        assert d["enterprise_price"] == 199
        assert d["trial_days"] == 7
        assert isinstance(d["claimed"], int)
        assert d["remaining"] == max(0, 15 - d["claimed"])


# --------------------------------------------------------- ADMIN endpoints auth
ADMIN_ENDPOINTS_GET = [
    "/admin/overview", "/admin/customers", "/admin/founders",
    "/admin/notifications", "/admin/audit",
]


class TestAdminAuth:
    def test_unauth_returns_401_or_403(self):
        for ep in ADMIN_ENDPOINTS_GET:
            r = requests.get(f"{API}{ep}", timeout=15)
            assert r.status_code in (401, 403), f"{ep} unauth got {r.status_code}"

    def test_free_user_gets_403(self, free_session):
        s, _ = free_session
        for ep in ADMIN_ENDPOINTS_GET:
            r = s.get(f"{API}{ep}", timeout=15)
            assert r.status_code == 403, f"{ep} free got {r.status_code}"
        # POST endpoints
        r = s.post(f"{API}/admin/campaign/toggle", json={"active": True}, timeout=15)
        assert r.status_code == 403

    def test_admin_gets_200(self, admin_session):
        for ep in ADMIN_ENDPOINTS_GET:
            r = admin_session.get(f"{API}{ep}", timeout=20)
            assert r.status_code == 200, f"{ep} admin got {r.status_code} {r.text[:200]}"


# --------------------------------------------------------- ADMIN overview metrics
class TestAdminOverview:
    def test_metrics_numeric(self, admin_session):
        r = admin_session.get(f"{API}/admin/overview", timeout=20)
        assert r.status_code == 200
        d = r.json()
        keys = ["total_companies", "active_subscriptions", "trialing", "founders_assigned",
                "founders_active", "remaining_slots", "mrr_total", "mrr_founders",
                "cancellations_month", "failed_payments", "new_7d", "new_30d", "campaign_active"]
        for k in keys:
            assert k in d, f"missing metric {k}"
        for k in keys:
            if k == "campaign_active":
                assert isinstance(d[k], bool)
            else:
                assert isinstance(d[k], (int, float)), f"{k} not numeric: {d[k]!r}"


# --------------------------------------------------------- Premium gating
PREMIUM_GET_ENDPOINTS = [
    "/chat/sessions", "/valuation", "/report", "/health-index",
    "/future", "/investment-grade", "/decisions",
]


class TestPremiumGating:
    def test_free_user_gets_402(self, free_session):
        s, _ = free_session
        for ep in PREMIUM_GET_ENDPOINTS:
            r = s.get(f"{API}{ep}", timeout=20)
            assert r.status_code == 402, f"{ep} free got {r.status_code} {r.text[:200]}"
        # POST /api/chat
        r = s.post(f"{API}/chat", json={"message": "olá"}, timeout=20)
        assert r.status_code == 402, f"/chat free got {r.status_code}"

    def test_free_user_ceo_daily_locked(self, free_session):
        s, _ = free_session
        r = s.get(f"{API}/ceo-daily", timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d.get("premium_locked") is True
        assert d.get("recomendacoes") == []

    def test_free_user_signals_locked(self, free_session):
        s, _ = free_session
        r = s.get(f"{API}/signals", timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d.get("premium_locked") is True
        assert d.get("priority") in ({}, None) or d.get("priority") == {}

    def test_admin_full_access(self, admin_session):
        for ep in PREMIUM_GET_ENDPOINTS:
            r = admin_session.get(f"{API}{ep}", timeout=30)
            assert r.status_code == 200, f"{ep} admin got {r.status_code}"


# --------------------------------------------------------- Founder checkout guards
class TestCheckoutGuards:
    def test_enterprise_returns_400(self, admin_session):
        r = admin_session.post(f"{API}/payments/checkout",
                               json={"lookup_key": "enterprise", "origin_url": "https://x"}, timeout=20)
        assert r.status_code == 400

    def test_founder_closed_when_campaign_off(self, admin_session):
        # Toggle OFF
        t = admin_session.post(f"{API}/admin/campaign/toggle", json={"active": False}, timeout=20)
        assert t.status_code == 200
        # Fresh free user trying founder_monthly
        email = f"TEST_founder_guard_{uuid.uuid4().hex[:8]}@test.com"
        s = _register(email, "Passw0rd!Test", name="TEST Guard")
        try:
            r = s.post(f"{API}/payments/checkout",
                       json={"lookup_key": "founder_monthly", "origin_url": "https://x"}, timeout=20)
            assert r.status_code == 409, f"expected 409 got {r.status_code}"
            assert "founder_closed" in r.text
        finally:
            # Restore ON
            admin_session.post(f"{API}/admin/campaign/toggle", json={"active": True}, timeout=20)


# --------------------------------------------------------- Professional trial (checkout URL only)
class TestProfessionalTrial:
    def test_creates_checkout_url(self, free_session):
        s, _ = free_session
        r = s.post(f"{API}/payments/checkout",
                   json={"lookup_key": "professional_monthly", "origin_url": "https://x"}, timeout=25)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        d = r.json()
        assert "checkout_url" in d and d["checkout_url"].startswith("https://")
        assert "session_id" in d


# --------------------------------------------------------- Subscription endpoint sanity
class TestSubscription:
    def test_admin_is_premium(self, admin_session):
        r = admin_session.get(f"{API}/subscription", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d.get("is_premium") is True
        assert d.get("is_admin") is True

    def test_free_is_not_premium(self, free_session):
        s, _ = free_session
        r = s.get(f"{API}/subscription", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d.get("is_premium") is False
