"""Backend tests for CRM (ICP, leads, drafts)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://organic-growth-agent.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = "adminceoai@gmail.com"
ADMIN_PASS = "12345"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    yield s


# --- ICP ---
class TestICP:
    def test_get_icp(self, client):
        r = client.get(f"{API}/crm/icp", timeout=30)
        assert r.status_code == 200
        assert "icp" in r.json()

    def test_save_and_read_icp(self, client):
        payload = {
            "sector": "Restauração", "size": "pequena", "region": "Lisboa",
            "decisor": "gerente", "dor": "margem baixa",
            "ticket_ideal": 1500.0, "urgencia": "alta", "notas": "TEST_note"
        }
        r = client.post(f"{API}/crm/icp", json=payload, timeout=30)
        assert r.status_code == 200
        assert r.json().get("ok") is True

        r = client.get(f"{API}/crm/icp", timeout=30)
        assert r.status_code == 200
        icp = r.json()["icp"]
        assert icp is not None
        assert icp["sector"] == "Restauração"
        assert icp["size"] == "pequena"
        assert icp["ticket_ideal"] == 1500.0
        assert icp["urgencia"] == "alta"

    def test_suggest_icp(self, client):
        r = client.post(f"{API}/crm/icp/suggest", timeout=90)
        assert r.status_code == 200
        icp = r.json().get("icp")
        assert isinstance(icp, dict)
        # At least a few expected keys must be present (AI-generated, structure only)
        keys = set(icp.keys())
        assert keys & {"sector", "size", "region", "ticket_ideal", "urgencia", "notas"}


# --- LEADS ---
class TestLeads:
    lead_id = None
    initial_score = None

    def test_list_leads_shape(self, client):
        r = client.get(f"{API}/crm/leads", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "leads" in d and isinstance(d["leads"], list)
        assert d["stages"] == ["novo", "qualificado", "reuniao", "proposta", "negociacao", "ganho", "perdido"]
        assert "counts" in d and set(d["counts"].keys()) == set(d["stages"])
        assert "pipeline_value" in d
        # ensure no _id leaks
        for l in d["leads"]:
            assert "_id" not in l
            assert "id" in l

    def test_create_lead_missing_name(self, client):
        r = client.post(f"{API}/crm/leads", json={}, timeout=30)
        assert r.status_code in (400, 422)

    def test_create_lead_low(self, client):
        payload = {"name": "TEST_low", "sector": "outro", "size": "micro",
                   "region": "Faro", "value": 500, "urgency": "baixa", "stage": "novo"}
        r = client.post(f"{API}/crm/leads", json=payload, timeout=30)
        assert r.status_code == 200
        lead = r.json()["lead"]
        assert lead["name"] == "TEST_low"
        assert lead["stage"] == "novo"
        assert isinstance(lead["score"], int)
        assert 0 <= lead["score"] <= 100
        TestLeads.lead_id = lead["id"]
        TestLeads.initial_score = lead["score"]

    def test_update_lead_recomputes_score(self, client):
        assert TestLeads.lead_id
        # Set high value + urgency alta + fit ICP sector/size/region + late stage
        payload = {"id": TestLeads.lead_id, "name": "TEST_low",
                   "sector": "Restauração", "size": "pequena", "region": "Lisboa",
                   "value": 50000, "urgency": "alta", "stage": "negociacao"}
        r = client.post(f"{API}/crm/leads", json=payload, timeout=30)
        assert r.status_code == 200
        lead = r.json()["lead"]
        assert lead["score"] > TestLeads.initial_score
        assert lead["score"] >= 70  # should be "quente"

    def test_move_stage(self, client):
        r = client.post(f"{API}/crm/leads/{TestLeads.lead_id}/stage",
                        json={"stage": "proposta"}, timeout=30)
        assert r.status_code == 200
        assert r.json().get("ok") is True
        assert isinstance(r.json().get("score"), int)

    def test_move_stage_invalid(self, client):
        r = client.post(f"{API}/crm/leads/{TestLeads.lead_id}/stage",
                        json={"stage": "invalid_stage"}, timeout=30)
        assert r.status_code == 400

    def test_draft_email(self, client):
        r = client.post(f"{API}/crm/leads/{TestLeads.lead_id}/draft",
                        json={"kind": "email"}, timeout=90)
        assert r.status_code == 200
        d = r.json()
        assert d.get("kind") == "email"
        draft = d.get("draft") or {}
        assert isinstance(draft, dict)
        assert "assunto" in draft or "corpo" in draft

    def test_draft_proposal(self, client):
        r = client.post(f"{API}/crm/leads/{TestLeads.lead_id}/draft",
                        json={"kind": "proposal"}, timeout=90)
        assert r.status_code == 200
        d = r.json()
        assert d.get("kind") == "proposal"
        draft = d.get("draft") or {}
        assert isinstance(draft, dict)
        assert "titulo" in draft or "corpo" in draft

    def test_pipeline_value_excludes_perdido(self, client):
        # Move to perdido and confirm not counted
        r = client.post(f"{API}/crm/leads/{TestLeads.lead_id}/stage",
                        json={"stage": "perdido"}, timeout=30)
        assert r.status_code == 200
        r = client.get(f"{API}/crm/leads", timeout=30)
        d = r.json()
        vals = sum((l.get("value") or 0) for l in d["leads"]
                   if l.get("stage") != "perdido")
        assert d["pipeline_value"] == vals

    def test_delete_lead(self, client):
        r = client.delete(f"{API}/crm/leads/{TestLeads.lead_id}", timeout=30)
        assert r.status_code == 200
        assert r.json().get("ok") is True
        r = client.get(f"{API}/crm/leads", timeout=30)
        ids = [l["id"] for l in r.json()["leads"]]
        assert TestLeads.lead_id not in ids


# --- Regression ---
class TestRegression:
    def test_goal(self, client):
        r = client.get(f"{API}/goal", timeout=30)
        assert r.status_code == 200

    def test_council_meeting(self, client):
        r = client.get(f"{API}/council/meeting", timeout=30)
        assert r.status_code == 200
