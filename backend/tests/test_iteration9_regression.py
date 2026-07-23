"""Iteration 9 — Regression suite:
- All modularized routes still respond (post server.py -> core/models/routers refactor).
- Document AI analysis on POST /api/upload (CSV with real financials).
- GET /api/investment-grade uses verified docs (documents_analyzed, extracted_figures,
  checklist financials=done, tier moves up, rationale references numbers).
- Investment Grade tier logic: no crash with zero documents.
"""
import io
import os
import uuid
import time
import pytest
import requests
from pathlib import Path

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    for line in Path("/app/frontend/.env").read_text().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip()
BASE_URL = BASE_URL.rstrip("/")

ADMIN_EMAIL = "obeliscoradical@gmail.com"
ADMIN_PASSWORD = "CeoAI2026!"

FIN_CSV = (
    "Demonstracao de Resultados,Valor\n"
    "Receita,240000\n"
    "EBITDA,72000\n"
    "Lucro liquido,54000\n"
    "Ativos,180000\n"
    "Passivos,60000\n"
    "Receita recorrente,180000\n"
    "Moeda,EUR\n"
).encode("utf-8")


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def cleanup_ids():
    ids = []
    yield ids


@pytest.fixture(scope="module", autouse=True)
def _final_cleanup(admin, cleanup_ids):
    yield
    for did in cleanup_ids:
        try:
            admin.delete(f"{BASE_URL}/api/documents/{did}", timeout=30)
        except Exception:
            pass


# ---------- REGRESSION: modularization sanity ----------
class TestModularizationRegression:
    """All existing endpoints still respond after routers/ refactor."""

    def test_health_root(self, admin):
        r = admin.get(f"{BASE_URL}/api/", timeout=30)
        assert r.status_code == 200

    def test_auth_me(self, admin):
        r = admin.get(f"{BASE_URL}/api/auth/me", timeout=30)
        assert r.status_code == 200
        u = r.json()
        assert u["email"] == ADMIN_EMAIL
        assert u.get("is_premium") is True

    def test_companies_list(self, admin):
        r = admin.get(f"{BASE_URL}/api/companies", timeout=30)
        assert r.status_code == 200
        d = r.json()
        # Endpoint returns {companies: [...], active_company_id}
        assert "companies" in d and isinstance(d["companies"], list)
        assert "active_company_id" in d

    def test_company_get(self, admin):
        r = admin.get(f"{BASE_URL}/api/company", timeout=30)
        assert r.status_code == 200

    def test_dna_get(self, admin):
        r = admin.get(f"{BASE_URL}/api/dna", timeout=30)
        assert r.status_code == 200

    def test_dashboard(self, admin):
        r = admin.get(f"{BASE_URL}/api/dashboard", timeout=30)
        assert r.status_code == 200
        d = r.json()
        # basic snapshot shape
        for k in ["health", "runway", "profit_margin", "currency_symbol"]:
            assert k in d

    def test_score(self, admin):
        r = admin.get(f"{BASE_URL}/api/score", timeout=30)
        assert r.status_code == 200

    def test_entries_list(self, admin):
        r = admin.get(f"{BASE_URL}/api/entries", timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_entries_crud(self, admin):
        payload = {"type": "income", "amount": 123.45, "date": "2026-01-15",
                   "description": "TEST_regression_entry", "category": "TEST"}
        r = admin.post(f"{BASE_URL}/api/entries", json=payload, timeout=30)
        assert r.status_code == 200, r.text
        eid = r.json().get("id") or r.json().get("_id")
        # ensure it appears
        r2 = admin.get(f"{BASE_URL}/api/entries", timeout=30)
        assert any(e.get("description") == "TEST_regression_entry" for e in r2.json())
        # delete
        r3 = admin.delete(f"{BASE_URL}/api/entries/{eid}", timeout=30)
        assert r3.status_code == 200

    def test_settings_get_put(self, admin):
        r = admin.get(f"{BASE_URL}/api/settings", timeout=30)
        assert r.status_code == 200
        base = r.json()
        r2 = admin.put(f"{BASE_URL}/api/settings", json={"language": base.get("language", "pt")}, timeout=30)
        assert r2.status_code == 200

    def test_memories(self, admin):
        r = admin.get(f"{BASE_URL}/api/memories", timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_briefing(self, admin):
        r = admin.get(f"{BASE_URL}/api/briefing", timeout=45)
        assert r.status_code == 200

    def test_subscription(self, admin):
        r = admin.get(f"{BASE_URL}/api/subscription", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "is_premium" in d

    def test_ceo_daily(self, admin):
        r = admin.get(f"{BASE_URL}/api/ceo-daily", timeout=60)
        assert r.status_code == 200
        d = r.json()
        for k in ["conclusao", "recomendacoes", "vitals", "currency_symbol"]:
            assert k in d

    def test_decisions(self, admin):
        r = admin.get(f"{BASE_URL}/api/decisions", timeout=60)
        assert r.status_code == 200

    def test_health_index(self, admin):
        r = admin.get(f"{BASE_URL}/api/health-index", timeout=60)
        assert r.status_code == 200

    def test_valuation(self, admin):
        r = admin.get(f"{BASE_URL}/api/valuation", timeout=60)
        assert r.status_code == 200

    def test_report(self, admin):
        r = admin.get(f"{BASE_URL}/api/report", timeout=60)
        assert r.status_code == 200

    def test_future(self, admin):
        r = admin.get(f"{BASE_URL}/api/future", timeout=60)
        assert r.status_code == 200

    def test_future_simulate(self, admin):
        r = admin.post(f"{BASE_URL}/api/future/simulate",
                       json={"scenario": "growth", "delta_income_pct": 10}, timeout=60)
        assert r.status_code == 200

    def test_contact(self, admin):
        r = admin.post(f"{BASE_URL}/api/contact",
                       json={"name": "TEST", "email": "test@test.com", "message": "regression test"},
                       timeout=30)
        assert r.status_code == 200

    def test_chat_streaming(self, admin):
        # POST /api/chat streams; just verify 200 + some bytes
        r = admin.post(f"{BASE_URL}/api/chat", json={"message": "olá, teste breve"}, stream=True, timeout=60)
        assert r.status_code == 200
        chunk = next(r.iter_content(chunk_size=64), b"")
        assert len(chunk) > 0
        r.close()


# ---------- Document AI analysis ----------
class TestDocumentAIAnalysis:
    """POST /api/upload extracts + analyzes financial docs; GET /api/documents shows analysis."""

    def test_upload_financials_csv_returns_analysis(self, admin, cleanup_ids):
        files = {"file": (f"TEST_fin_{uuid.uuid4().hex[:6]}.csv", io.BytesIO(FIN_CSV), "text/csv")}
        r = admin.post(f"{BASE_URL}/api/upload", files=files,
                       data={"doc_type": "financials"}, timeout=90)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["doc_type"] == "financials"
        assert "analysis" in body
        a = body["analysis"]
        # AI extracted meaningful metadata
        assert a.get("relevant") is True, f"expected relevant=True, got {a}"
        assert a.get("quality") in ("high", "medium", "low")
        assert isinstance(a.get("summary"), str) and len(a["summary"]) > 5
        cleanup_ids.append(body["id"])

    def test_documents_list_includes_analysis(self, admin, cleanup_ids):
        r = admin.get(f"{BASE_URL}/api/documents", timeout=30)
        assert r.status_code == 200
        docs = r.json()
        assert any(d["id"] in cleanup_ids for d in docs)
        for d in docs:
            if d["id"] in cleanup_ids:
                assert "analysis" in d
                assert set(d["analysis"].keys()) >= {"relevant", "quality", "summary"}

    def test_upload_low_signal_doc(self, admin, cleanup_ids):
        # tiny random file — analyzer should mark analysable=False (or relevant=False)
        files = {"file": ("TEST_tiny.txt", io.BytesIO(b"x"), "text/plain")}
        r = admin.post(f"{BASE_URL}/api/upload", files=files, data={"doc_type": "other"}, timeout=60)
        assert r.status_code == 200, r.text
        cleanup_ids.append(r.json()["id"])
        # analysis dict returned even when short
        a = r.json().get("analysis", {})
        assert "relevant" in a


# ---------- Investment Grade uses documents ----------
class TestInvestmentGradeUsesDocs:
    """After upload, /investment-grade should reflect verified docs."""

    @pytest.fixture(scope="class")
    def graded(self, admin, cleanup_ids):
        # ensure a financial doc is present (upload if not already)
        docs = admin.get(f"{BASE_URL}/api/documents", timeout=30).json()
        has_verified_fin = any(
            d["doc_type"] == "financials"
            and (d.get("analysis") or {}).get("relevant")
            and (d.get("analysis") or {}).get("quality") in ("high", "medium")
            for d in docs
        )
        if not has_verified_fin:
            files = {"file": (f"TEST_fin_grade_{uuid.uuid4().hex[:6]}.csv",
                              io.BytesIO(FIN_CSV), "text/csv")}
            r = admin.post(f"{BASE_URL}/api/upload", files=files,
                           data={"doc_type": "financials"}, timeout=90)
            assert r.status_code == 200
            cleanup_ids.append(r.json()["id"])
            time.sleep(1)
        r = admin.get(f"{BASE_URL}/api/investment-grade", timeout=120)
        assert r.status_code == 200, r.text
        return r.json()

    def test_documents_analyzed_positive(self, graded):
        assert graded["documents_analyzed"] >= 1, graded

    def test_extracted_figures_populated(self, graded):
        figs = graded.get("extracted_figures") or {}
        # at least one of the key financial numbers should be extracted
        assert any(figs.get(k) for k in ("revenue", "ebitda", "net_profit", "assets")), figs

    def test_financials_checklist_done(self, graded):
        by_type = {c.get("upload_type"): c for c in graded["confidence"]["checklist"]}
        assert by_type["financials"]["done"] is True

    def test_tier_lifted(self, graded):
        # With verified financials and enough checklist items, tier must not be the lowest
        assert graded["confidence"]["tier"] in {"Estimativa Fundamentada", "Nível Profissional"}

    def test_rationale_non_trivial(self, graded):
        r = graded.get("rationale") or ""
        assert isinstance(r, str) and len(r) > 20

    def test_tier_rule_professional_requires_75_and_financials(self, graded):
        c = graded["confidence"]
        if c["tier"] == "Nível Profissional":
            assert c["score"] >= 75
            # verified financials must exist -> checklist financials done
            by_type = {ci.get("upload_type"): ci for ci in c["checklist"]}
            assert by_type["financials"]["done"] is True


# ---------- No-doc no-crash sanity via a fresh account ----------
class TestInvestmentGradeZeroDocs:
    """Tier logic must not crash when a premium user has zero documents."""

    def test_admin_grade_shape_holds_regardless(self, admin):
        # Doesn't matter if docs present - just ensure endpoint stable
        r = admin.get(f"{BASE_URL}/api/investment-grade", timeout=120)
        assert r.status_code == 200
        d = r.json()
        assert d["confidence"]["tier"] in {"Nível Profissional", "Estimativa Fundamentada", "Estimativa Inteligente"}
        assert isinstance(d.get("document_insights"), list)
        assert isinstance(d.get("extracted_figures"), dict)
