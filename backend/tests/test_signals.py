"""Backend tests for iteration 14 — CEO Signals (/api/signals)."""
import os
import re
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"
BASE_URL = BASE_URL.rstrip("/")

EMAIL = "obeliscoradical@gmail.com"
PASSWORD = "CeoAI2026!"

VALID_TYPES = {"critical", "attention", "positive", "risk", "opportunity"}


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=20)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text[:300]}"
    return s


class TestSignalsAuth:
    def test_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/signals", timeout=10)
        assert r.status_code == 401, f"expected 401 without auth, got {r.status_code}"


class TestSignalsShape:
    def test_shape_and_quantified(self, client):
        r = client.get(f"{BASE_URL}/api/signals", timeout=60)
        assert r.status_code == 200, r.text[:500]
        d = r.json()
        for k in ("user_name", "count", "signals", "priority", "has_data"):
            assert k in d, f"missing key: {k}"
        assert isinstance(d["signals"], list)
        assert d["count"] == len(d["signals"])
        # Owner has seeded data → expect signals to be present
        assert d["has_data"] is True, "owner should have seed data"
        assert 3 <= len(d["signals"]) <= 6, f"signals count out of range: {len(d['signals'])}"

        quantified = 0
        for s in d["signals"]:
            for f in ("type", "text", "detail"):
                assert f in s, f"signal missing {f}: {s}"
            assert s["type"] in VALID_TYPES, f"invalid type {s['type']}"
            assert isinstance(s["text"], str) and len(s["text"]) > 3
            # quantified: contains € or %  or digits
            if re.search(r"[€%]", s["text"]) or re.search(r"\d", s["text"]):
                quantified += 1
        # Most signals must be quantified (contain € or % or numbers)
        assert quantified >= max(1, len(d["signals"]) - 1), \
            f"too few quantified signals ({quantified}/{len(d['signals'])}): {[s['text'] for s in d['signals']]}"

        # priority
        p = d["priority"]
        assert isinstance(p, dict) and p.get("text"), f"priority missing text: {p}"

    def test_cached_on_second_call(self, client):
        # warm up (may already be cached)
        client.get(f"{BASE_URL}/api/signals", timeout=60)
        t0 = time.time()
        r2 = client.get(f"{BASE_URL}/api/signals", timeout=15)
        dt = time.time() - t0
        assert r2.status_code == 200
        assert dt < 3.0, f"second /signals call too slow (not cached): {dt:.2f}s"
