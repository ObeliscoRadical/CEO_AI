"""Tests for the new Briefing por Email feature (Phase 6).

Covers:
- POST /api/briefing/email (auth) returns {sent:true, to:<email>}
- GET /api/briefing continues to return greeting + items + health (make_briefing refactor didn't regress)
- GET/PUT /api/settings expose and persist email_briefing (bool, default False)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or "https://seo-marketing-hub-12.preview.emergentagent.com"
ADMIN_EMAIL = "obeliscoradical@gmail.com"
ADMIN_PASSWORD = "CeoAI2026!"


@pytest.fixture(scope="module")
def admin_client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def initial_email_briefing(admin_client):
    r = admin_client.get(f"{BASE_URL}/api/settings", timeout=15)
    assert r.status_code == 200
    val = bool(r.json().get("email_briefing", False))
    yield val
    # restore original value
    admin_client.put(f"{BASE_URL}/api/settings", json={"email_briefing": val}, timeout=15)


# ---- Settings: email_briefing default + persistence ----

class TestSettingsEmailBriefing:
    def test_get_settings_exposes_email_briefing_field(self, admin_client, initial_email_briefing):
        r = admin_client.get(f"{BASE_URL}/api/settings", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "email_briefing" in data
        assert isinstance(data["email_briefing"], bool)

    def test_put_settings_persists_email_briefing_true(self, admin_client, initial_email_briefing):
        r = admin_client.put(f"{BASE_URL}/api/settings", json={"email_briefing": True}, timeout=15)
        assert r.status_code == 200
        assert r.json().get("email_briefing") is True
        # GET after PUT to verify persistence
        r2 = admin_client.get(f"{BASE_URL}/api/settings", timeout=15)
        assert r2.status_code == 200
        assert r2.json().get("email_briefing") is True

    def test_put_settings_persists_email_briefing_false(self, admin_client, initial_email_briefing):
        r = admin_client.put(f"{BASE_URL}/api/settings", json={"email_briefing": False}, timeout=15)
        assert r.status_code == 200
        assert r.json().get("email_briefing") is False
        r2 = admin_client.get(f"{BASE_URL}/api/settings", timeout=15)
        assert r2.status_code == 200
        assert r2.json().get("email_briefing") is False


# ---- GET /api/briefing (refactor sanity) ----

class TestBriefingGet:
    def test_briefing_returns_greeting_items_and_health(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/briefing", timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "greeting" in data and isinstance(data["greeting"], str) and len(data["greeting"]) > 0
        assert "items" in data and isinstance(data["items"], list) and len(data["items"]) >= 1
        assert "health" in data and isinstance(data["health"], (int, float))
        first = data["items"][0]
        for k in ("title", "detail", "priority", "icon"):
            assert k in first, f"missing key {k} in briefing item"


# ---- POST /api/briefing/email ----

class TestBriefingEmail:
    def test_briefing_email_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/briefing/email", timeout=30)
        assert r.status_code == 401

    def test_briefing_email_sends_to_current_user(self, admin_client):
        r = admin_client.post(f"{BASE_URL}/api/briefing/email", timeout=90)
        assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert data.get("sent") is True
        assert data.get("to", "").lower() == ADMIN_EMAIL.lower()
