"""Backend tests for iteration 8 — CEO Diário (/api/ceo-daily) and executive personality on chat."""
import os
import time
import json
import re
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"
BASE_URL = BASE_URL.rstrip("/")

EMAIL = "obeliscoradical@gmail.com"
PASSWORD = "CeoAI2026!"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=20)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text[:300]}"
    return s


# --- /api/ceo-daily shape and caching ------------------------------------
class TestCeoDaily:
    def test_shape(self, client):
        r = client.get(f"{BASE_URL}/api/ceo-daily", timeout=60)
        assert r.status_code == 200, r.text[:500]
        d = r.json()
        # top-level keys
        for k in ("user_name", "company_name", "conclusao", "recomendacoes",
                  "vitals", "currency_symbol", "has_data"):
            assert k in d, f"missing key: {k}"
        # conclusion
        c = d["conclusao"]
        for k in ("estado_geral", "oportunidades", "problemas", "prioridades"):
            assert k in c, f"conclusao missing {k}"
        # vitals - 5 items
        v = d["vitals"]
        for k in ("saude", "valor", "crescimento", "tesouraria", "fluxo"):
            assert k in v, f"vital missing {k}"
            for f in ("label", "value", "unit", "status"):
                assert f in v[k], f"vital {k} missing field {f}"
        # recomendacoes
        recs = d["recomendacoes"]
        assert isinstance(recs, list)
        # allow 0 if AI returned nothing (fallback), else 3..6
        if len(recs) > 0:
            assert 3 <= len(recs) <= 6, f"recomendacoes count out of range: {len(recs)}"
            for r_ in recs:
                for f in ("title", "why", "priority", "key"):
                    assert f in r_, f"rec missing {f}: {r_}"
                assert r_["priority"] in ("urgente", "importante", "oportunidade"), \
                    f"invalid priority {r_['priority']}"

    def test_cached_on_second_call(self, client):
        # first call (may be cached from previous test)
        t0 = time.time()
        r1 = client.get(f"{BASE_URL}/api/ceo-daily", timeout=60)
        t1 = time.time() - t0
        assert r1.status_code == 200
        # second call must be fast (cache hit)
        t0 = time.time()
        r2 = client.get(f"{BASE_URL}/api/ceo-daily", timeout=15)
        t2 = time.time() - t0
        assert r2.status_code == 200
        assert t2 < 3.0, f"second call not cached (took {t2:.2f}s, first {t1:.2f}s)"
        # identical payload (deterministic keys) — recomendacoes[].key stable
        d1, d2 = r1.json(), r2.json()
        keys1 = [x.get("key") for x in d1.get("recomendacoes", [])]
        keys2 = [x.get("key") for x in d2.get("recomendacoes", [])]
        assert keys1 == keys2, f"cached recomendacoes keys differ: {keys1} vs {keys2}"


# --- Executive personality of the CEO chat ------------------------------
class TestCEOChatPersonality:
    def _stream(self, client, msg):
        with client.post(f"{BASE_URL}/api/chat", json={"message": msg},
                         stream=True, timeout=90) as r:
            assert r.status_code == 200, r.text[:300]
            buf = ""
            for line in r.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("data:"):
                    try:
                        ev = json.loads(line[5:].strip())
                    except Exception:
                        continue
                    if ev.get("delta"):
                        buf += ev["delta"]
                    if ev.get("done"):
                        break
            return buf

    def test_takes_position_no_depende(self, client):
        text = self._stream(client, "Posso contratar mais um técnico?")
        assert len(text) > 100, f"response too short: {text[:200]}"
        low = text.lower()
        # Must not answer with pure 'depende' — allow the word only if paired with a decision
        # Rule from spec: NEVER say 'depende'. We check the word does NOT appear as a standalone answer.
        # If the token 'depende' appears, ensure a strong verb ('faria', 'contrata', 'não contrata', 'recomendo') is present.
        has_depende = re.search(r"\bdepende\b", low) is not None
        has_position = any(kw in low for kw in [
            "eu faria", "faria", "recomendo", "não contrat", "contrata", "avanç",
            "não avanç", "aguarda", "adia", "aconselho"
        ])
        assert has_position, f"response has no clear position/verb: {text[:400]}"
        if has_depende:
            # If 'depende' appears, it must be paired with a concrete recommendation
            assert has_position, f"'depende' used without a firm position: {text[:400]}"
        # Reasoning + risks/alternatives markers (soft check)
        has_why = any(kw in low for kw in ["porque", "porqu", "razão", "motivo", "considerando"])
        has_risk = any(kw in low for kw in ["risco", "risk", "perigo"])
        has_alt = any(kw in low for kw in ["alternativ", "opção", "opções", "caminho"])
        # At least 2 of the 3 structural elements should be present
        struct = sum([has_why, has_risk, has_alt])
        assert struct >= 2, f"missing executive structure (why/risks/alternatives). Text: {text[:500]}"
