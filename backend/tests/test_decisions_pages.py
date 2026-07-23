"""Backend smoke tests for the new premium pages (Painel do CEO, Saúde, Valor, Relatórios, Futuro).

Focus:
- Auth (owner login)
- GET /api/decisions (verdict + decisions[] + tiles)
- POST /api/decisions/act (done, snoozed)
- GET /api/health-index (9 dims, overall)
- GET /api/valuation (value, factors, actions)
- GET /api/report (all report sections)
- GET /api/future (12-month projection) — premium
- POST /api/future/simulate (5 metrics) — premium
"""
import os
import pytest
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
OWNER = {"email": "obeliscoradical@gmail.com", "password": "CeoAI2026!"}
TIMEOUT = 60  # AI calls may take up to 30-45s each


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=OWNER, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    body = r.json()
    assert body.get("is_premium") is True, "Owner must be premium for /future tests"
    return s


# ------------------------------------------------------------ Painel do CEO
class TestPainelCEO:
    def test_decisions_shape(self, client):
        r = client.get(f"{BASE_URL}/api/decisions", timeout=TIMEOUT)
        assert r.status_code == 200
        d = r.json()
        assert "verdict" in d and isinstance(d["verdict"], str) and len(d["verdict"]) > 0
        assert "decisions" in d and isinstance(d["decisions"], list)
        assert "health" in d and isinstance(d["health"], int)
        assert "company_value" in d
        assert "currency_symbol" in d
        for dec in d["decisions"]:
            assert "key" in dec and isinstance(dec["key"], str)
            assert "title" in dec
            assert "urgency" in dec

    def test_decisions_act_done_and_snoozed(self, client):
        # need at least one decision to act on; if empty use a synthetic key (endpoint is stateless upsert)
        r = client.get(f"{BASE_URL}/api/decisions", timeout=TIMEOUT)
        assert r.status_code == 200
        decisions = r.json().get("decisions", [])
        key1 = decisions[0]["key"] if decisions else "test_key_done"
        key2 = decisions[1]["key"] if len(decisions) > 1 else "test_key_snoozed"

        r1 = client.post(f"{BASE_URL}/api/decisions/act",
                         json={"key": key1, "title": "t1", "status": "done"}, timeout=30)
        assert r1.status_code == 200 and r1.json().get("ok") is True

        r2 = client.post(f"{BASE_URL}/api/decisions/act",
                         json={"key": key2, "title": "t2", "status": "snoozed"}, timeout=30)
        assert r2.status_code == 200 and r2.json().get("ok") is True


# ------------------------------------------------------------ Saúde
class TestHealthIndex:
    def test_health_index_shape(self, client):
        r = client.get(f"{BASE_URL}/api/health-index", timeout=TIMEOUT)
        assert r.status_code == 200
        d = r.json()
        assert "overall" in d and isinstance(d["overall"], int)
        assert "dimensions" in d and isinstance(d["dimensions"], list)
        # 9 dimensions as specified
        assert len(d["dimensions"]) == 9, f"expected 9 dims, got {len(d['dimensions'])}"
        for dim in d["dimensions"]:
            assert "dimension" in dim and "score" in dim
            assert "why" in dim and "improve" in dim and "potential" in dim


# ------------------------------------------------------------ Valor
class TestValuation:
    def test_valuation_shape(self, client):
        r = client.get(f"{BASE_URL}/api/valuation", timeout=TIMEOUT)
        assert r.status_code == 200
        d = r.json()
        assert "company_value" in d
        assert "currency_symbol" in d
        assert "factors" in d and isinstance(d["factors"], list)
        assert "actions" in d and isinstance(d["actions"], list)
        assert len(d["factors"]) >= 1
        for f in d["factors"]:
            assert "name" in f and "influence" in f and "weight" in f


# ------------------------------------------------------------ Relatório
class TestReport:
    def test_report_shape(self, client):
        r = client.get(f"{BASE_URL}/api/report", timeout=TIMEOUT)
        assert r.status_code == 200
        d = r.json()
        for key in ["situacao_atual", "pontos_fortes", "pontos_fracos", "riscos",
                    "oportunidades", "valor", "projecao_12m", "plano_acao", "recomendacoes",
                    "company_name", "health", "company_value", "generated_at"]:
            assert key in d, f"missing key {key}"
        assert isinstance(d["plano_acao"], list)
        assert isinstance(d["recomendacoes"], list)


# ------------------------------------------------------------ Futuro (Premium)
class TestFuture:
    def test_future_projection(self, client):
        r = client.get(f"{BASE_URL}/api/future", timeout=TIMEOUT)
        assert r.status_code == 200, f"future returned {r.status_code}: {r.text}"
        d = r.json()
        assert "projection" in d and isinstance(d["projection"], list)
        assert len(d["projection"]) == 12
        assert "monthly_net" in d
        assert "currency_symbol" in d
        for p in d["projection"]:
            assert "month" in p and "cash" in p

    def test_future_simulate_five_metrics(self, client):
        r = client.post(f"{BASE_URL}/api/future/simulate",
                        json={"scenario": "contratar", "detail": "técnico a 1400€/mês"},
                        timeout=TIMEOUT)
        assert r.status_code == 200, f"simulate returned {r.status_code}: {r.text}"
        d = r.json()
        assert "verdict" in d and d["verdict"] in {"favoravel", "cautela", "desaconselhado"}
        assert "summary" in d
        assert "metrics" in d and isinstance(d["metrics"], dict)
        for m in ["lucro", "fluxo_caixa", "risco", "valuation", "saude"]:
            assert m in d["metrics"], f"missing metric {m}"
        assert "recommendation" in d and "timeline" in d
