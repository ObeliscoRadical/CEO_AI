"""Tests for sector-specialization in CEO AI outputs (report/signals/ceo-daily)."""
import os
import re
import json
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://editorial-executor.preview.emergentagent.com").rstrip("/")
EMAIL = "obeliscoradical@gmail.com"
PASSWORD = "CeoAI2026!"

AI_TIMEOUT = 90  # AI cold calls can take 10-25s; be generous

# Restaurant vocabulary (word-boundary matching to avoid substring false positives).
RESTAURANT_TERMS = [
    r"\bfood\s*cost\b",
    r"\bementa\b",     # avoid substring like 'incrementa'
    r"\bmesas?\b",
    r"\brotaç(ão|ões)\s+de\s+mesas?\b",
    r"\bturnos?\b",
    r"\bcozinha\b",
    r"\brestaurant\w*\b",
]

CONSTRUCTION_TERMS = [
    r"\bempreitadas?\b",
    r"\badjudica\w*\b",
    r"\bestaleiro\b",
    r"\bsubempreiteir\w*\b",
    r"\balvar[áa]\b",
    r"\bdono\s+de\s+obra\b",
]


def _count_matches(text: str, patterns):
    t = text.lower()
    hits = {}
    for p in patterns:
        m = re.findall(p, t, flags=re.IGNORECASE)
        if m:
            hits[p] = len(m)
    return hits


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return s


def _get_company(session):
    r = session.get(f"{BASE_URL}/api/company", timeout=30)
    assert r.status_code == 200, r.text
    return r.json() or {}


def _save_company(session, sector, activity, cae, name="Obelisco"):
    body = {
        "name": name,
        "region": "PT",
        "currency": "EUR",
        "sector": sector,
        "profile": {"activity": activity, "cae": cae},
    }
    r = session.post(f"{BASE_URL}/api/company", json=body, timeout=30)
    assert r.status_code == 200, f"save company failed: {r.status_code} {r.text}"
    return r.json()


def _fetch_all_text(session):
    """Fetch /api/report and /api/signals and concatenate all string values recursively."""
    r_rep = session.get(f"{BASE_URL}/api/report", timeout=AI_TIMEOUT)
    assert r_rep.status_code == 200, f"/api/report failed: {r_rep.status_code} {r_rep.text[:400]}"
    r_sig = session.get(f"{BASE_URL}/api/signals", timeout=AI_TIMEOUT)
    assert r_sig.status_code == 200, f"/api/signals failed: {r_sig.status_code} {r_sig.text[:400]}"

    def flatten(v, acc):
        if isinstance(v, str):
            acc.append(v)
        elif isinstance(v, dict):
            for x in v.values():
                flatten(x, acc)
        elif isinstance(v, list):
            for x in v:
                flatten(x, acc)

    acc = []
    flatten(r_rep.json(), acc)
    flatten(r_sig.json(), acc)
    return " \n ".join(acc), r_rep.json(), r_sig.json()


def test_login_ok(session):
    r = session.get(f"{BASE_URL}/api/auth/me", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data.get("email") == EMAIL


def test_restaurant_sector_produces_restaurant_language(session):
    _save_company(session, sector="restaurante / restauração",
                  activity="restaurante", cae="56101")
    text, rep, sig = _fetch_all_text(session)
    rest_hits = _count_matches(text, RESTAURANT_TERMS)
    con_hits = _count_matches(text, CONSTRUCTION_TERMS)
    total_rest = sum(rest_hits.values())
    total_con = sum(con_hits.values())
    print("RESTAURANT run — restaurant hits:", rest_hits, "construction hits:", con_hits)
    print("Sample report keys:", list(rep.keys()) if isinstance(rep, dict) else type(rep))
    print("Sample signals keys:", list(sig.keys()) if isinstance(sig, dict) else type(sig))
    assert total_rest >= 2, f"Expected restaurant-domain vocabulary, got hits={rest_hits}. Text preview: {text[:800]}"
    # Construction terms should be effectively absent
    assert total_con <= 1, f"Unexpected construction vocabulary in restaurant context: {con_hits}"


def test_construction_sector_switches_language(session):
    _save_company(session, sector="construção civil",
                  activity="construção civil", cae="41200")
    text, rep, sig = _fetch_all_text(session)
    rest_hits = _count_matches(text, RESTAURANT_TERMS)
    con_hits = _count_matches(text, CONSTRUCTION_TERMS)
    total_rest = sum(rest_hits.values())
    total_con = sum(con_hits.values())
    print("CONSTRUCTION run — construction hits:", con_hits, "restaurant hits:", rest_hits)
    assert total_con >= 1, f"Expected construction-domain vocabulary, got hits={con_hits}. Text preview: {text[:1200]}"
    assert total_rest <= 1, f"Unexpected restaurant vocabulary in construction context: {rest_hits}"


def test_ceo_daily_returns_valid_json_after_sector_change(session):
    r = session.get(f"{BASE_URL}/api/ceo-daily", timeout=AI_TIMEOUT)
    assert r.status_code == 200, f"/api/ceo-daily failed: {r.status_code} {r.text[:400]}"
    data = r.json()
    assert isinstance(data, dict), f"expected dict, got {type(data)}"
    # sanity: some keys expected
    assert len(data.keys()) > 0
    print("ceo-daily top-level keys:", list(data.keys()))


def test_cache_invalidation_switches_output(session):
    """Switch back to restaurante and verify output regenerates with restaurant terms (cache was invalidated)."""
    _save_company(session, sector="restaurante / restauração",
                  activity="restaurante", cae="56101")
    text, _, _ = _fetch_all_text(session)
    rest_hits = _count_matches(text, RESTAURANT_TERMS)
    con_hits = _count_matches(text, CONSTRUCTION_TERMS)
    print("SWITCH-BACK run — restaurant hits:", rest_hits, "construction hits:", con_hits)
    assert sum(rest_hits.values()) >= 2, f"Cache invalidation failed — still not restaurant-flavored. rest={rest_hits}, con={con_hits}"
