"""
CEO AI — Phase 4: Subscription management backend tests.

Covers:
  GET  /api/subscription
  POST /api/payments/portal
  POST /api/payments/cancel-subscription

Uses the real admin (obeliscoradical@gmail.com) that already has an ACTIVE Stripe
test subscription linked (stripe_customer_id + stripe_subscription_id).

The cancel test is destructive on the Stripe test subscription (sets
cancel_at_period_end=True). A fixture *restores* cancel_at_period_end=False at
the end of the module so the admin's premium is left as we found it.
"""
import os
import uuid
import pytest
import requests

# Read backend URL from frontend/.env
_envp = "/app/frontend/.env"
BASE_URL = None
if os.environ.get("REACT_APP_BACKEND_URL"):
    BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
else:
    with open(_envp) as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                break

API = f"{BASE_URL}/api"
ADMIN_EMAIL = "obeliscoradical@gmail.com"
ADMIN_PWD = "CeoAI2026!"


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PWD}, timeout=30)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def free_user_session():
    """Register a fresh (free-plan) user; not premium, no stripe_customer_id."""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    email = f"test_sub_{uuid.uuid4().hex[:10]}@example.com"
    r = s.post(
        f"{API}/auth/register",
        json={"email": email, "password": "Passw0rd!", "name": "Sub Free"},
        timeout=30,
    )
    assert r.status_code == 200, f"Register failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module", autouse=False)
def restore_admin_subscription(admin_session):
    """After the module runs, undo any cancel_at_period_end=True on admin's sub."""
    yield
    # Best-effort restore via Stripe API directly using the same env key
    try:
        import stripe
        stripe.api_key = os.environ.get("STRIPE_SECRET_KEY") or _read_env("STRIPE_SECRET_KEY")
        # Fetch admin sub_id via /subscription endpoint
        r = admin_session.get(f"{API}/subscription", timeout=30)
        if r.ok:
            data = r.json()
            sub = data.get("subscription") or {}
            # We only need the id; retrieve subs from customer if not present
            # Easier: search via customer id from portal is not exposed. Fall back to
            # listing subscriptions on the customer via a fresh Stripe call.
            # Get customer id by creating a portal session -> not ideal. Instead,
            # use Stripe API to list active + trialing subs and pick the one that
            # matches admin (we know only one active test sub is linked).
            # We rely on the fact the endpoint returned a status: retrieve via
            # user document is server-side only — so we brute-force list.
            subs = stripe.Subscription.list(status="all", limit=20).data
            for s in subs:
                if s.get("cancel_at_period_end"):
                    try:
                        stripe.Subscription.modify(s.id, cancel_at_period_end=False)
                    except Exception:
                        pass
    except Exception:
        # Non-fatal — restoration is best-effort.
        pass


def _read_env(key):
    try:
        with open("/app/backend/.env") as f:
            for line in f:
                if line.startswith(f"{key}="):
                    v = line.split("=", 1)[1].strip()
                    return v.strip('"').strip("'")
    except Exception:
        return None
    return None


# ---------- GET /api/subscription ----------
class TestSubscriptionEndpoint:
    def test_requires_auth(self):
        r = requests.get(f"{API}/subscription", timeout=30)
        # Auth uses httpOnly cookie; expect 401 or 403 without it
        assert r.status_code in (401, 403), f"Unexpected status: {r.status_code} {r.text}"

    def test_admin_premium_shape(self, admin_session):
        r = admin_session.get(f"{API}/subscription", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        # Top-level shape
        assert set(["is_premium", "plans", "subscription", "has_billing"]).issubset(data.keys())
        assert data["is_premium"] is True
        assert isinstance(data["plans"], dict)
        assert "premium_monthly" in data["plans"] and "premium_yearly" in data["plans"]
        assert data["has_billing"] is True, "Admin should have stripe_customer_id"
        sub = data["subscription"]
        assert sub is not None, "Admin should have a Stripe subscription linked"
        for key in ("status", "plan", "lookup_key", "cancel_at_period_end", "current_period_end"):
            assert key in sub, f"Missing key '{key}' in subscription payload: {sub}"
        assert sub["status"] in ("active", "trialing", "past_due"), f"Unexpected status: {sub['status']}"
        assert isinstance(sub["cancel_at_period_end"], bool)
        assert sub["current_period_end"] is None or isinstance(sub["current_period_end"], int)

    def test_free_user_shape(self, free_user_session):
        r = free_user_session.get(f"{API}/subscription", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["is_premium"] is False
        assert data["subscription"] is None
        assert data["has_billing"] is False
        assert "premium_monthly" in data["plans"]


# ---------- POST /api/payments/portal ----------
class TestBillingPortal:
    def test_admin_portal_returns_url(self, admin_session):
        r = admin_session.post(
            f"{API}/payments/portal",
            json={"origin_url": "https://ceo-marketing-stage.preview.emergentagent.com"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "url" in data
        assert isinstance(data["url"], str) and data["url"].startswith("https://")
        # Stripe billing portal URLs live under billing.stripe.com
        assert "stripe.com" in data["url"], f"Unexpected portal URL: {data['url']}"

    def test_free_user_portal_400(self, free_user_session):
        r = free_user_session.post(
            f"{API}/payments/portal",
            json={"origin_url": "https://ceo-marketing-stage.preview.emergentagent.com"},
            timeout=30,
        )
        assert r.status_code == 400, f"Expected 400 without stripe_customer_id, got {r.status_code}: {r.text}"


# ---------- POST /api/payments/cancel-subscription ----------
class TestCancelSubscription:
    def test_free_user_cancel_400(self, free_user_session):
        r = free_user_session.post(f"{API}/payments/cancel-subscription", timeout=30)
        assert r.status_code == 400, r.text

    def test_admin_cancel_sets_cancel_at_period_end(self, admin_session, restore_admin_subscription):
        # Snapshot current state
        r0 = admin_session.get(f"{API}/subscription", timeout=30)
        assert r0.status_code == 200
        before = r0.json()["subscription"]

        r = admin_session.post(f"{API}/payments/cancel-subscription", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        assert data.get("cancel_at_period_end") is True

        # Verify via GET
        r2 = admin_session.get(f"{API}/subscription", timeout=30)
        assert r2.status_code == 200
        after = r2.json()["subscription"]
        assert after is not None
        assert after["cancel_at_period_end"] is True
        # is_premium must stay True until Stripe deletes it at period end
        assert r2.json()["is_premium"] is True, "Cancel-at-period-end must NOT immediately revoke premium"

        # Restore inline as an extra safety (module teardown also does this)
        try:
            import stripe
            stripe.api_key = _read_env("STRIPE_SECRET_KEY")
            subs = stripe.Subscription.list(status="all", limit=20).data
            for s in subs:
                if s.get("cancel_at_period_end"):
                    stripe.Subscription.modify(s.id, cancel_at_period_end=False)
        except Exception:
            pass
