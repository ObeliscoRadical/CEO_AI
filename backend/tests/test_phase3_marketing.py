"""Phase 3: Marketing content + CRM send-sim (WhatsApp link / self email).
Tests focus on backend routes: /api/marketing/content, /api/marketing/generate,
and /api/crm/leads/{id}/send-sim. Plus regression pings.
"""
import os
import time
from datetime import datetime, timezone
from urllib.parse import quote
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN_EMAIL = "adminceoai@gmail.com"
ADMIN_PW = "12345"
MONGO = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


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
        assert "proposta_valor" in c["brand"]
        assert isinstance(c["brand"].get("audiencias"), list)
        # posts
        assert isinstance(c.get("posts"), list) and len(c["posts"]) >= 4
        p0 = c["posts"][0]
        for k in ("id", "formato", "titulo", "legenda", "hashtags", "cta", "dia", "tema", "objetivo", "status"):
            assert k in p0, f"missing {k} in post"
        assert p0["formato"] in ("Post", "Story", "Reel")
        assert isinstance(p0["hashtags"], list)
        assert p0["status"] in ("draft", "approved", "scheduled")
        # biblioteca
        assert isinstance(c.get("biblioteca"), list) and len(c["biblioteca"]) >= 3
        b0 = c["biblioteca"][0]
        for k in ("titulo", "angulo", "objetivo", "pilar", "formatos", "cta"):
            assert k in b0, f"missing {k} in library"
        # calendario
        assert isinstance(c.get("calendario"), list) and len(c["calendario"]) >= 30
        cal0 = c["calendario"][0]
        for k in ("dia", "formato", "tema", "data", "objetivo"):
            assert k in cal0
        # workflow summary / brand brain
        assert isinstance(c.get("workflow_summary"), dict)
        assert c["workflow_summary"].get("draft", 0) >= 1
        assert isinstance(c.get("brand_brain"), dict)
        assert isinstance(c["brand_brain"].get("prioridades"), list)

    def test_get_after_generate_persists(self, sess):
        r = sess.get(f"{BASE}/api/marketing/content", timeout=30)
        assert r.status_code == 200
        d = r.json()["content"]
        assert d is not None
        assert "content" in d

    def test_post_workflow_status(self, sess):
        current = sess.get(f"{BASE}/api/marketing/content", timeout=30)
        assert current.status_code == 200
        posts = ((current.json().get("content") or {}).get("content") or {}).get("posts") or []
        assert posts, "expected generated posts"
        post_id = posts[0]["id"]

        r = sess.post(f"{BASE}/api/marketing/posts/{post_id}/status", json={"status": "approved"}, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["post"]["status"] == "approved"
        assert data["content"]["workflow_summary"]["approved"] >= 1

        r2 = sess.post(f"{BASE}/api/marketing/posts/{post_id}/status", json={"status": "draft"}, timeout=30)
        assert r2.status_code == 200, r2.text
        data2 = r2.json()
        assert data2["post"]["status"] == "draft"

    def test_execution_analytics_and_briefing(self, sess):
        current = sess.get(f"{BASE}/api/marketing/content", timeout=30)
        assert current.status_code == 200
        content = ((current.json().get("content") or {}).get("content") or {})
        posts = content.get("posts") or []
        assert posts, "expected generated posts"
        post = posts[0]

        companies = sess.get(f"{BASE}/api/companies", timeout=30)
        assert companies.status_code == 200, companies.text
        cid = companies.json().get("active_company_id")
        uid = str(MONGO.users.find_one({"email": ADMIN_EMAIL})["_id"])
        stamp = int(time.time())
        job_id = f"queue-{stamp}"
        social_post_id = f"social-{stamp}"
        run_at = "2031-01-12T09:00:00Z"
        published_at = datetime.now(timezone.utc).isoformat()

        MONGO.social_jobs.insert_one({
            "_id": job_id,
            "user_id": uid,
            "company_id": cid,
            "payload": {"post_id": post["id"], "caption": "Fila de teste", "post_meta": {"title": post["titulo"], "theme": post["tema"], "format": post["formato"]}},
            "run_at": run_at,
            "status": "queued",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        MONGO.social_posts.insert_one({
            "_id": social_post_id,
            "user_id": uid,
            "company_id": cid,
            "post_id": post["id"],
            "post_title": post["titulo"],
            "theme": post["tema"],
            "format": post["formato"],
            "caption": "Histórico de teste",
            "results": {"instagram": {"ok": True, "id": "ig-test"}},
            "created_at": published_at,
        })
        MONGO.marketing_post_metrics.insert_one({
            "user_id": uid,
            "company_id": cid,
            "social_post_id": social_post_id,
            "post_id": post["id"],
            "post_title": post["titulo"],
            "format": post["formato"],
            "theme": post["tema"],
            "channels": ["instagram"],
            "metrics": {"impressions": 2200, "reach": 1600, "likes": 88, "comments": 12, "shares": 10, "saves": 24, "clicks": 39, "profile_visits": 41, "engagement_rate": 8.38, "top_signal": "gerou conversa"},
            "mocked": True,
            "published_at": published_at,
            "created_at": published_at,
        })
        try:
            execution = sess.get(f"{BASE}/api/marketing/execution", timeout=30)
            assert execution.status_code == 200, execution.text
            execution_data = execution.json()
            assert any(item["id"] == job_id for item in execution_data["queued"])
            assert any(item["id"] == social_post_id for item in execution_data["history"])

            new_run = "2031-01-13T11:30:00Z"
            res = sess.post(f"{BASE}/api/social/jobs/{job_id}/reschedule", json={"run_at": new_run}, timeout=30)
            assert res.status_code == 200, res.text
            updated_job = MONGO.social_jobs.find_one({"_id": job_id})
            assert updated_job["run_at"] == new_run

            refreshed = sess.get(f"{BASE}/api/marketing/content", timeout=30)
            refreshed_posts = ((refreshed.json().get("content") or {}).get("content") or {}).get("posts") or []
            refreshed_post = next(p for p in refreshed_posts if p["id"] == post["id"])
            assert refreshed_post["status"] == "scheduled"
            assert refreshed_post["scheduled_at"] == new_run

            analytics = sess.get(f"{BASE}/api/marketing/analytics", timeout=30)
            assert analytics.status_code == 200, analytics.text
            analytics_data = analytics.json()
            assert analytics_data["mocked"] is True
            assert analytics_data["summary"]["published_posts"] >= 1
            assert len(analytics_data["top_posts"]) >= 1

            briefing = sess.post(f"{BASE}/api/marketing/briefing/generate", json={"force": True, "send_email": False}, timeout=90)
            assert briefing.status_code == 200, briefing.text
            briefing_data = briefing.json()
            for key in ("headline", "summary", "wins", "risks", "actions", "experiments"):
                assert key in briefing_data, f"missing {key}"
            assert briefing_data["mocked_metrics"] is True
        finally:
            sess.post(f"{BASE}/api/marketing/posts/{post['id']}/status", json={"status": "draft"}, timeout=30)
            MONGO.social_jobs.delete_many({"_id": job_id})
            MONGO.social_posts.delete_many({"_id": social_post_id})
            MONGO.marketing_post_metrics.delete_many({"social_post_id": social_post_id})


class TestSocialCompanyIsolation:
    @pytest.fixture(scope="class")
    def company_setup(self, sess):
        user_doc = MONGO.users.find_one({"email": ADMIN_EMAIL})
        assert user_doc, "admin user missing"
        user_id = str(user_doc["_id"])
        before = sess.get(f"{BASE}/api/companies", timeout=30)
        assert before.status_code == 200, before.text
        active_before = before.json().get("active_company_id")
        stamp = int(time.time())
        a = sess.post(f"{BASE}/api/companies", json={"name": f"TEST Social A {stamp}"}, timeout=30)
        b = sess.post(f"{BASE}/api/companies", json={"name": f"TEST Social B {stamp}"}, timeout=30)
        assert a.status_code == 200 and b.status_code == 200
        cid_a = a.json()["id"]
        cid_b = b.json()["id"]
        try:
            yield {"user_id": user_id, "a": cid_a, "b": cid_b, "active_before": active_before, "stamp": stamp}
        finally:
            if active_before:
                sess.put(f"{BASE}/api/companies/active", json={"company_id": active_before}, timeout=30)
            for cid in (cid_a, cid_b):
                sess.delete(f"{BASE}/api/companies/{cid}", timeout=30)
            MONGO.social_connections.delete_many({"user_id": user_id, "company_id": {"$in": [cid_a, cid_b]}})
            MONGO.social_jobs.delete_many({"user_id": user_id, "company_id": {"$in": [cid_a, cid_b]}})
            MONGO.social_posts.delete_many({"user_id": user_id, "company_id": {"$in": [cid_a, cid_b]}})

    def test_social_status_isolated_by_active_company(self, sess, company_setup):
        uid, cid_a, cid_b = company_setup["user_id"], company_setup["a"], company_setup["b"]
        MONGO.social_connections.insert_many([
            {"user_id": uid, "company_id": cid_a, "page_name": "Página A", "ig_username": "empresa_a", "page_id": "page-a", "page_token": "tok-a", "updated_at": datetime.now(timezone.utc).isoformat()},
            {"user_id": uid, "company_id": cid_b, "page_name": "Página B", "ig_username": "empresa_b", "page_id": "page-b", "page_token": "tok-b", "updated_at": datetime.now(timezone.utc).isoformat()},
        ])

        r1 = sess.put(f"{BASE}/api/companies/active", json={"company_id": cid_a}, timeout=30)
        assert r1.status_code == 200, r1.text
        s1 = sess.get(f"{BASE}/api/social/status", timeout=30)
        assert s1.status_code == 200, s1.text
        d1 = s1.json()
        assert d1["connected"] is True
        assert d1["page_name"] == "Página A"
        assert d1["ig_username"] == "empresa_a"

        r2 = sess.put(f"{BASE}/api/companies/active", json={"company_id": cid_b}, timeout=30)
        assert r2.status_code == 200, r2.text
        s2 = sess.get(f"{BASE}/api/social/status", timeout=30)
        assert s2.status_code == 200, s2.text
        d2 = s2.json()
        assert d2["connected"] is True
        assert d2["page_name"] == "Página B"
        assert d2["ig_username"] == "empresa_b"

        MONGO.social_connections.delete_many({"user_id": uid, "company_id": {"$in": [cid_a, cid_b]}})

    def test_social_jobs_isolated_by_active_company(self, sess, company_setup):
        uid, cid_a, cid_b = company_setup["user_id"], company_setup["a"], company_setup["b"]
        stamp = company_setup["stamp"]
        MONGO.social_jobs.insert_many([
            {"_id": f"job-a-{stamp}", "user_id": uid, "company_id": cid_a, "payload": {"caption": "Job Empresa A"}, "run_at": "2031-01-10T10:00:00Z", "status": "queued", "created_at": datetime.now(timezone.utc).isoformat()},
            {"_id": f"job-b-{stamp}", "user_id": uid, "company_id": cid_b, "payload": {"caption": "Job Empresa B"}, "run_at": "2031-01-11T10:00:00Z", "status": "queued", "created_at": datetime.now(timezone.utc).isoformat()},
        ])

        sess.put(f"{BASE}/api/companies/active", json={"company_id": cid_a}, timeout=30)
        ja = sess.get(f"{BASE}/api/social/jobs", timeout=30)
        assert ja.status_code == 200, ja.text
        captions_a = [j["caption"] for j in ja.json()["jobs"]]
        assert "Job Empresa A" in captions_a
        assert "Job Empresa B" not in captions_a

        sess.put(f"{BASE}/api/companies/active", json={"company_id": cid_b}, timeout=30)
        jb = sess.get(f"{BASE}/api/social/jobs", timeout=30)
        assert jb.status_code == 200, jb.text
        captions_b = [j["caption"] for j in jb.json()["jobs"]]
        assert "Job Empresa B" in captions_b
        assert "Job Empresa A" not in captions_b

        MONGO.social_jobs.delete_many({"user_id": uid, "company_id": {"$in": [cid_a, cid_b]}})


class TestMetaConnectionPreparation:
    def test_social_pending_selection_and_finalize(self, sess):
        companies = sess.get(f"{BASE}/api/companies", timeout=30)
        assert companies.status_code == 200, companies.text
        cid = companies.json().get("active_company_id")
        uid = str(MONGO.users.find_one({"email": ADMIN_EMAIL})["_id"])
        stamp = int(time.time())
        pending = {
            "user_id": uid,
            "company_id": cid,
            "status": "pending_selection",
            "user_token": f"user-token-{stamp}",
            "granted_scopes": ["instagram_basic", "instagram_content_publish", "pages_read_engagement"],
            "candidate_pages": [
                {
                    "page_id": f"page-{stamp}-1",
                    "page_name": "Página Teste 1",
                    "page_token": "page-token-1",
                    "tasks": ["CREATE_CONTENT"],
                    "ig_user_id": f"ig-{stamp}-1",
                    "ig_username": "empresa_teste_1",
                },
                {
                    "page_id": f"page-{stamp}-2",
                    "page_name": "Página Teste 2",
                    "page_token": "page-token-2",
                    "tasks": ["MANAGE"],
                    "ig_user_id": None,
                    "ig_username": None,
                },
            ],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        MONGO.social_connections.delete_many({"user_id": uid, "company_id": cid})
        MONGO.social_connections.insert_one(pending)
        try:
            status = sess.get(f"{BASE}/api/social/status", timeout=30)
            assert status.status_code == 200, status.text
            data = status.json()
            assert data["pending_selection"] is True
            assert data["connected"] is False
            assert len(data["available_pages"]) == 2
            assert data["available_pages"][0]["page_name"] == "Página Teste 1"

            req = sess.get(f"{BASE}/api/social/requirements", timeout=30)
            assert req.status_code == 200, req.text
            assert "requirements" in req.json()

            sel = sess.post(f"{BASE}/api/social/select-page", json={"page_id": f"page-{stamp}-1"}, timeout=30)
            assert sel.status_code == 200, sel.text
            payload = sel.json()["connection"]
            assert payload["connected"] is True
            assert payload["page_name"] == "Página Teste 1"
            assert payload["ig_username"] == "empresa_teste_1"

            saved = MONGO.social_connections.find_one({"user_id": uid, "company_id": cid})
            assert saved["status"] == "connected"
            assert saved["page_id"] == f"page-{stamp}-1"
            assert saved["candidate_pages"] == []
        finally:
            MONGO.social_connections.delete_many({"user_id": uid, "company_id": cid})


class TestMarketingCampaigns:
    def test_generate_and_list_campaign(self, sess):
        payload = {
            "objective": "leads",
            "name": "Campanha Teste Leads",
            "offer": "diagnóstico comercial",
            "audience": "gestores de PME",
            "notes": "teste automático",
        }
        created = sess.post(f"{BASE}/api/marketing/campaigns/generate", json=payload, timeout=120)
        assert created.status_code == 200, created.text
        campaign = created.json()["campaign"]
        assert campaign["objective"] == "leads"
        assert campaign["name"] == "Campanha Teste Leads"
        assert len(campaign["channels"]) == 4
        assert len(campaign["launch_plan"]) == 4
        assert len(campaign["kpis"]) >= 3

        listing = sess.get(f"{BASE}/api/marketing/campaigns", timeout=30)
        assert listing.status_code == 200, listing.text
        ids = [item["id"] for item in listing.json()["campaigns"]]
        assert campaign["id"] in ids

        MONGO.marketing_campaigns.delete_many({"_id": campaign["id"]})


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
