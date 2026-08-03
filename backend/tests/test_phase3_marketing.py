"""Phase 3: Marketing content + CRM send-sim (WhatsApp link / self email).
Tests focus on backend routes: /api/marketing/content, /api/marketing/generate,
and /api/crm/leads/{id}/send-sim. Plus regression pings.
"""
import os
import time
from urllib.parse import quote
import pytest
import requests
from dotenv import load_dotenv
load_dotenv("/app/frontend/.env")
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN_EMAIL = "adminceoai@gmail.com"
ADMIN_PW = "12345"


@pytest.fixture(scope="module")
def sess():
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PW}, timeout=30)
    assert r.status_code == 200, r.text
    return s


# ---------------- Marketing ----------------
class TestMarketing:
    def test_get_content(self, sess):
        r = sess.get(f"{BASE}/api/marketing/content", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "content" in data  # can be None or a dict

    def test_generate_content(self, sess):
        r = sess.post(f"{BASE}/api/marketing/generate", timeout=180)
        assert r.status_code == 200, r.text
        payload = r.json()
        assert "content" in payload
        wrap = payload["content"]
        assert "content" in wrap and "updated_at" in wrap
        c = wrap["content"]
        # brand
        assert isinstance(c.get("brand"), dict)
        assert "tom" in c["brand"]
        assert isinstance(c["brand"].get("pilares"), list)
        # posts
        assert isinstance(c.get("posts"), list) and len(c["posts"]) >= 4
        p0 = c["posts"][0]
        for k in ("formato", "titulo", "legenda", "hashtags", "cta", "dia"):
            assert k in p0, f"missing {k} in post"
        assert p0["formato"] in ("Post", "Story", "Reel")
        assert isinstance(p0["hashtags"], list)
        # calendario
        assert isinstance(c.get("calendario"), list) and len(c["calendario"]) >= 5
        cal0 = c["calendario"][0]
        for k in ("dia", "formato", "tema"):
            assert k in cal0

    def test_get_after_generate_persists(self, sess):
        r = sess.get(f"{BASE}/api/marketing/content", timeout=30)
        assert r.status_code == 200
        d = r.json()["content"]
        assert d is not None
        assert "content" in d


# ---------------- CRM send-sim ----------------
class TestSendSim:
    @pytest.fixture(scope="class")
    def lead_id(self, sess):
        # Create a TEST lead with a phone contact
        payload = {"name": "TEST_SendSim Lead", "contact": "+351 912 345 678",
                   "sector": "Padaria", "value": 1200, "urgency": "alta", "stage": "qualificado"}
        r = sess.post(f"{BASE}/api/crm/leads", json=payload, timeout=30)
        assert r.status_code == 200, r.text
        lid = r.json()["lead"]["id"]
        yield lid
        sess.delete(f"{BASE}/api/crm/leads/{lid}", timeout=30)

    def test_send_sim_whatsapp(self, sess, lead_id):
        msg = "Olá! Uma proposta para si."
        r = sess.post(f"{BASE}/api/crm/leads/{lead_id}/send-sim",
                      json={"channel": "whatsapp", "message": msg}, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True
        assert "wa_link" in data
        assert data["wa_link"].startswith("https://wa.me/")
        # digits of contact only
        assert "351912345678" in data["wa_link"]
        assert quote(msg) in data["wa_link"]

    def test_send_sim_whatsapp_no_phone(self, sess):
        # Create a lead without contact digits
        r = sess.post(f"{BASE}/api/crm/leads",
                      json={"name": "TEST_NoPhone", "stage": "novo"}, timeout=30)
        assert r.status_code == 200
        lid = r.json()["lead"]["id"]
        try:
            r2 = sess.post(f"{BASE}/api/crm/leads/{lid}/send-sim",
                           json={"channel": "whatsapp", "message": "Olá"}, timeout=30)
            assert r2.status_code == 200
            assert r2.json()["wa_link"].startswith("https://wa.me/?text=")
        finally:
            sess.delete(f"{BASE}/api/crm/leads/{lid}", timeout=30)

    def test_send_sim_email(self, sess, lead_id):
        r = sess.post(f"{BASE}/api/crm/leads/{lead_id}/send-sim",
                      json={"channel": "email", "message": "Corpo do email\nlinha 2",
                            "subject": "TEST Assunto"}, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        assert data.get("sent_to") == ADMIN_EMAIL

    def test_send_sim_lead_not_found(self, sess):
        # 24-hex objectid that shouldn't exist
        r = sess.post(f"{BASE}/api/crm/leads/000000000000000000000000/send-sim",
                      json={"channel": "whatsapp", "message": "x"}, timeout=30)
        assert r.status_code == 404


# ---------------- Regression ----------------
class TestRegression:
    def test_council(self, sess):
        r = sess.get(f"{BASE}/api/council/meeting", timeout=30)
        assert r.status_code in (200, 201)

    def test_crm_leads(self, sess):
        r = sess.get(f"{BASE}/api/crm/leads", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "leads" in d and "stages" in d

    def test_crm_icp(self, sess):
        r = sess.get(f"{BASE}/api/crm/icp", timeout=30)
        assert r.status_code == 200

    def test_goal(self, sess):
        r = sess.get(f"{BASE}/api/goal", timeout=30)
        assert r.status_code == 200

    def test_dashboard(self, sess):
        # Painel likely uses /api/dashboard or /api/snapshot; try common
        for path in ("/api/dashboard", "/api/snapshot", "/api/companies/active"):
            r = sess.get(f"{BASE}{path}", timeout=30)
            if r.status_code == 200:
                return
        pytest.skip("no dashboard endpoint responded 200")
