"""Tests for /api/company/import-certidao and /api/company/lookup-nif (Empresa auto-fill)."""
import io
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

EMAIL = "obeliscoradical@gmail.com"
PASSWORD = "CeoAI2026!"

CERT_TEXT = (
    "CERTIDÃO PERMANENTE DO REGISTO COMERCIAL\n"
    "Firma: OBELISCO CONSULTORIA UNIPESSOAL LDA\n"
    "NIPC: 509442013\n"
    "CAE Principal: 70220 - Actividades de consultoria para os negócios e a gestão\n"
    "Sede: Rua das Flores, 100, 4000-001 Porto\n"
    "Objeto: consultoria de gestão e apoio a empresas\n"
    "Capital social: 5000 EUR\n"
    "Data de constituição: 2012-05-10\n"
    "Sócios: Diego Fernandes\n"
)


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def anon():
    return requests.Session()


# --- Auth guard ---
def test_import_certidao_requires_auth(anon):
    files = {"file": ("cert.txt", io.BytesIO(CERT_TEXT.encode("utf-8")), "text/plain")}
    r = anon.post(f"{BASE_URL}/api/company/import-certidao", files=files, timeout=30)
    assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"


def test_lookup_nif_requires_auth(anon):
    r = anon.post(f"{BASE_URL}/api/company/lookup-nif", json={"nif": "509442013"}, timeout=30)
    assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"


# --- lookup-nif ---
def test_lookup_nif_invalid_returns_400(client):
    r = client.post(f"{BASE_URL}/api/company/lookup-nif", json={"nif": "123"}, timeout=30)
    assert r.status_code == 400
    detail = r.json().get("detail", "")
    assert "9" in detail or "inválido" in detail.lower()


def test_lookup_nif_valid_but_no_key_returns_400(client):
    # NIFPT_API_KEY is intentionally not configured; must be graceful 400
    assert not os.environ.get("NIFPT_API_KEY"), "This test assumes the key is not set"
    r = client.post(f"{BASE_URL}/api/company/lookup-nif", json={"nif": "509442013"}, timeout=30)
    assert r.status_code == 400
    detail = r.json().get("detail", "").lower()
    assert "chave" in detail or "api" in detail or "nif.pt" in detail


# --- import-certidao ---
def test_import_certidao_empty_returns_422(client):
    files = {"file": ("empty.txt", io.BytesIO(b"abc"), "text/plain")}
    r = client.post(f"{BASE_URL}/api/company/import-certidao", files=files, timeout=45)
    assert r.status_code == 422, f"expected 422, got {r.status_code} {r.text}"


def test_import_certidao_extracts_fields(client):
    files = {"file": ("cert.txt", io.BytesIO(CERT_TEXT.encode("utf-8")), "text/plain")}
    r = client.post(f"{BASE_URL}/api/company/import-certidao", files=files, timeout=60)
    assert r.status_code == 200, r.text
    data = r.json()
    # Expected keys
    for k in ["name", "nipc", "cae", "activity", "location", "objeto_social", "capital", "incorporation_date", "socios"]:
        assert k in data, f"missing key {k} in {data}"
    # Distinctive values
    assert "OBELISCO" in (data.get("name") or "").upper()
    assert "509442013" in str(data.get("nipc") or "")
    assert "70220" in str(data.get("cae") or "")
