"""Tests for Phase 5 (Report v2 with clickable checklist):
- POST /api/upload accepts doc_type Form field
- GET /api/documents lists user's docs (excludes soft-deleted)
- DELETE /api/documents/{id} soft-deletes
- /investment-grade checklist has upload_type + reacts to doc_type presence
- Confidence tier / score / value_range narrows when docs are uploaded
"""
import io
import os
import time
import uuid
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


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def admin():
    return _login(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def created_docs(admin):
    """Track ids created during tests so we can soft-delete them at the end."""
    ids = []
    yield ids
    # cleanup
    for did in ids:
        try:
            admin.delete(f"{BASE_URL}/api/documents/{did}", timeout=30)
        except Exception:
            pass


# --- Documents CRUD -------------------------------------------------------
class TestDocumentsCRUD:
    def test_list_documents_starts_clean(self, admin):
        r = admin.get(f"{BASE_URL}/api/documents", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)

    def test_upload_with_doc_type_financials(self, admin, created_docs):
        files = {"file": ("TEST_financials.txt", io.BytesIO(b"revenue,100\ncosts,60\n"), "text/plain")}
        data = {"doc_type": "financials"}
        r = admin.post(f"{BASE_URL}/api/upload", files=files, data=data, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["filename"] == "TEST_financials.txt"
        assert body["doc_type"] == "financials"
        assert isinstance(body["id"], str) and len(body["id"]) > 0
        created_docs.append(body["id"])

    def test_upload_default_doc_type_is_other(self, admin, created_docs):
        files = {"file": ("TEST_default.txt", io.BytesIO(b"x"), "text/plain")}
        # No doc_type sent -> should default to 'other'
        r = admin.post(f"{BASE_URL}/api/upload", files=files, timeout=60)
        assert r.status_code == 200, r.text
        assert r.json()["doc_type"] == "other"
        created_docs.append(r.json()["id"])

    def test_get_documents_returns_uploaded(self, admin, created_docs):
        r = admin.get(f"{BASE_URL}/api/documents", timeout=30)
        assert r.status_code == 200
        docs = r.json()
        ids = {d["id"] for d in docs}
        for did in created_docs:
            assert did in ids
        # Structure check
        sample = next(d for d in docs if d["id"] == created_docs[0])
        for k in ["id", "filename", "doc_type", "size", "created_at"]:
            assert k in sample

    def test_delete_document_soft_deletes(self, admin, created_docs):
        # Upload a throwaway
        files = {"file": ("TEST_del.txt", io.BytesIO(b"delete-me"), "text/plain")}
        r = admin.post(f"{BASE_URL}/api/upload", files=files, data={"doc_type": "other"}, timeout=60)
        assert r.status_code == 200
        did = r.json()["id"]
        # Delete
        r = admin.delete(f"{BASE_URL}/api/documents/{did}", timeout=30)
        assert r.status_code == 200
        assert r.json().get("ok") is True
        # Ensure it no longer appears in list
        r = admin.get(f"{BASE_URL}/api/documents", timeout=30)
        ids = {d["id"] for d in r.json()}
        assert did not in ids

    def test_documents_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/documents", timeout=30)
        assert r.status_code == 401


# --- Investment Grade checklist tied to doc_types -------------------------
class TestInvestmentGradeChecklist:
    @pytest.fixture(scope="class")
    def cleanup_ids(self, admin):
        ids = []
        yield ids
        for did in ids:
            try:
                admin.delete(f"{BASE_URL}/api/documents/{did}", timeout=30)
            except Exception:
                pass

    def _get_grade(self, admin):
        r = admin.get(f"{BASE_URL}/api/investment-grade", timeout=90)
        assert r.status_code == 200, r.text
        return r.json()

    def _upload(self, admin, doc_type, cleanup_ids):
        files = {"file": (f"TEST_{doc_type}_{uuid.uuid4().hex[:6]}.txt",
                          io.BytesIO(f"content for {doc_type}".encode()), "text/plain")}
        r = admin.post(f"{BASE_URL}/api/upload", files=files,
                       data={"doc_type": doc_type}, timeout=60)
        assert r.status_code == 200, r.text
        cleanup_ids.append(r.json()["id"])

    def test_checklist_has_upload_type_only_on_document_items(self, admin, cleanup_ids):
        # Ensure a clean baseline: delete any existing docs of the 3 upload types
        docs = admin.get(f"{BASE_URL}/api/documents").json()
        for d in docs:
            if d["doc_type"] in {"financials", "assets", "contracts"}:
                admin.delete(f"{BASE_URL}/api/documents/{d['id']}")

        payload = self._get_grade(admin)
        checklist = payload["confidence"]["checklist"]
        assert len(checklist) == 5
        # Items with upload_type = financials/assets/contracts
        items_by_type = {c.get("upload_type"): c for c in checklist}
        for t in ["financials", "assets", "contracts"]:
            assert t in items_by_type, f"Missing checklist item with upload_type={t}"
        # EBITDA + dependency items should NOT have upload_type
        no_upload = [c for c in checklist if not c.get("upload_type")]
        assert len(no_upload) == 2, "Expected exactly 2 items without upload_type (EBITDA + dependency)"

    def test_uploading_toggles_done_and_raises_tier(self, admin, cleanup_ids):
        # Baseline
        base = self._get_grade(admin)
        base_score = base["confidence"]["score"]
        base_tier = base["confidence"]["tier"]
        base_range = base["value_range"]
        base_width = base_range["high"] - base_range["low"]

        # Upload all 3 doc types
        for t in ["financials", "assets", "contracts"]:
            self._upload(admin, t, cleanup_ids)

        # Slight delay to let LLM/next call breathe
        time.sleep(1)
        after = self._get_grade(admin)
        after_score = after["confidence"]["score"]
        after_tier = after["confidence"]["tier"]
        after_range = after["value_range"]
        after_width = after_range["high"] - after_range["low"]

        # Confidence score should rise
        assert after_score > base_score, f"Expected score to rise, got {base_score} -> {after_score}"

        # Checklist items for those types should be marked done
        by_type = {c.get("upload_type"): c for c in after["confidence"]["checklist"]}
        for t in ["financials", "assets", "contracts"]:
            assert by_type[t]["done"] is True, f"Item {t} should be done after upload"

        # Tier should be at least equal or better (Estimativa Inteligente -> Fundamentada -> Profissional)
        order = {"Estimativa Inteligente": 0, "Estimativa Fundamentada": 1, "Nível Profissional": 2}
        assert order[after_tier] >= order[base_tier]

        # Value range should be narrower or equal (only when company_value>0; if 0, both zero)
        if base["company_value"] > 0:
            assert after_width <= base_width, f"Range should narrow: was {base_width}, now {after_width}"

    def test_soft_delete_removes_done_flag(self, admin, cleanup_ids):
        # Fetch existing doc of type financials and delete it
        docs = admin.get(f"{BASE_URL}/api/documents").json()
        fin = next((d for d in docs if d["doc_type"] == "financials"), None)
        if not fin:
            # upload one first
            files = {"file": ("TEST_fin_x.txt", io.BytesIO(b"f"), "text/plain")}
            r = admin.post(f"{BASE_URL}/api/upload", files=files,
                           data={"doc_type": "financials"}, timeout=60)
            fin = {"id": r.json()["id"]}
            cleanup_ids.append(fin["id"])

        admin.delete(f"{BASE_URL}/api/documents/{fin['id']}")
        payload = self._get_grade(admin)
        by_type = {c.get("upload_type"): c for c in payload["confidence"]["checklist"]}
        # Only fails if no other financials doc remains
        remaining = [d for d in admin.get(f"{BASE_URL}/api/documents").json()
                     if d["doc_type"] == "financials"]
        if not remaining:
            assert by_type["financials"]["done"] is False


# --- Non-premium gating on upload (upload endpoint is not premium-gated,
# but documents is auth-only). Verify auth required for upload.
class TestUploadAuth:
    def test_upload_requires_auth(self):
        files = {"file": ("x.txt", io.BytesIO(b"x"), "text/plain")}
        r = requests.post(f"{BASE_URL}/api/upload", files=files, timeout=30)
        assert r.status_code == 401
