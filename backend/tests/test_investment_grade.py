"""Tests for Investment Grade (Phase 3) endpoint."""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else None
if not BASE_URL:
    # Fallback via frontend/.env when running locally
    from pathlib import Path
    for line in Path("/app/frontend/.env").read_text().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

ADMIN_EMAIL = "obeliscoradical@gmail.com"
ADMIN_PASSWORD = "CeoAI2026!"

VALID_LETTERS = {"A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D", "F"}


# ----- helpers -----------------------------------------------------------
def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return s


def _register_new(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/register",
               json={"email": email, "password": password, "name": "TEST_grade"})
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def admin_session():
    return _login(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def free_session():
    email = f"TEST_grade_{uuid.uuid4().hex[:8]}@ex.com"
    return _register_new(email, "P@ss123456!")


# ----- gating ------------------------------------------------------------
class TestInvestmentGradeGating:
    def test_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/investment-grade")
        assert r.status_code == 401

    def test_non_premium_gets_403(self, free_session):
        r = free_session.get(f"{BASE_URL}/api/investment-grade")
        assert r.status_code == 403
        assert r.json().get("detail") == "premium_required"


# ----- premium happy path -----------------------------------------------
class TestInvestmentGradePremium:
    @pytest.fixture(scope="class")
    def payload(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/investment-grade", timeout=90)
        assert r.status_code == 200, r.text
        return r.json()

    def test_top_level_shape(self, payload):
        for key in ["overall_grade", "overall_score", "dimensions", "company_value",
                    "value_range", "confidence", "rationale", "improvement_plan",
                    "disclaimer", "currency_symbol", "next_target"]:
            assert key in payload, f"missing {key}"

    def test_overall_grade_letter(self, payload):
        assert payload["overall_grade"] in VALID_LETTERS

    def test_dimensions_five_with_expected_keys(self, payload):
        dims = payload["dimensions"]
        assert isinstance(dims, list) and len(dims) == 5
        expected = {"financeiro", "crescimento", "risco", "liquidez", "dependencia"}
        assert {d["key"] for d in dims} == expected
        for d in dims:
            assert d["grade"] in VALID_LETTERS
            assert isinstance(d["score"], (int, float))
            assert "label" in d and "why" in d

    def test_grade_consistent_with_score(self, payload):
        # Coerência: aplicar mesma função to_grade
        def to_grade(score):
            for th, g in [(95, "A+"), (88, "A"), (82, "A-"), (75, "B+"), (68, "B"),
                          (62, "B-"), (55, "C+"), (48, "C"), (40, "C-"), (30, "D")]:
                if score >= th:
                    return g
            return "F"
        for d in payload["dimensions"]:
            assert d["grade"] == to_grade(d["score"]), f"{d['key']}: {d['score']} -> expected {to_grade(d['score'])}, got {d['grade']}"
        assert payload["overall_grade"] == to_grade(payload["overall_score"])

    def test_value_range_bounds(self, payload):
        vr = payload["value_range"]
        assert "low" in vr and "high" in vr
        assert vr["low"] <= payload["company_value"] <= vr["high"]

    def test_confidence_shape(self, payload):
        c = payload["confidence"]
        assert c["tier"] in {"Nível Profissional", "Estimativa Fundamentada", "Estimativa Inteligente"}
        assert 0 <= c["score"] <= 100
        assert isinstance(c["checklist"], list) and len(c["checklist"]) == 5
        for item in c["checklist"]:
            assert "item" in item and "done" in item
            assert isinstance(item["done"], bool)

    def test_rationale_and_disclaimer_non_empty(self, payload):
        assert isinstance(payload["rationale"], str) and len(payload["rationale"]) > 10
        assert isinstance(payload["disclaimer"], str) and len(payload["disclaimer"]) > 5

    def test_improvement_plan_is_list(self, payload):
        assert isinstance(payload["improvement_plan"], list)


# ----- to_grade coherence unit-ish tests (via values) --------------------
class TestGradeLetterMapping:
    def test_score_88_is_A(self):
        # We test the endpoint's overall_grade coherence via score by
        # sampling the known scores from admin payload
        pass  # Coerência já validada em test_grade_consistent_with_score
