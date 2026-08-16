import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from routers.site_publishing import (  # noqa: E402
    HOMEPAGE_MANAGED_SLOTS,
    _homepage_copy_from_slot_values,
    _homepage_default_copy,
    _homepage_slot_values,
    _normalize_homepage_copy,
)


def test_homepage_copy_normalizes_and_keeps_three_social_proof_items():
    ctx = {
        "name": "Metal Prime",
        "sector": "Indústria",
        "main_goal": "Gerar mais leads qualificados",
        "advantage": "rapidez comercial",
        "icp": {"dor": "falta de previsibilidade"},
    }

    payload = {
        "headline": "Nova headline",
        "social_proof_items": ["Uma", "Duas"],
    }

    normalized = _normalize_homepage_copy(payload, ctx)

    assert normalized["headline"] == "Nova headline"
    assert normalized["subtitle"]
    assert normalized["primary_cta_url"] == "#login-auth-panel"
    assert len(normalized["social_proof_items"]) == 3
    assert normalized["social_proof_items"][0] == "Uma"
    assert normalized["social_proof_items"][1] == "Duas"


def test_homepage_slot_roundtrip_keeps_core_fields():
    ctx = {
        "name": "Atlas AI",
        "sector": "Tecnologia",
        "main_goal": "crescer com clareza",
        "advantage": "visão unificada",
        "icp": {"dor": "equipas desalinhadas"},
    }
    copy = {
        "headline": "Atlas AI para líderes mais rápidos",
        "subtitle": "Subtítulo de teste",
        "primary_cta_label": "Entrar agora",
        "primary_cta_url": "#login-auth-panel",
        "secondary_cta_label": "Ver planos",
        "secondary_cta_url": "/planos",
        "social_proof_title": "Provas rápidas",
        "social_proof_items": ["Uma visão", "Mais foco", "Menos ruído"],
    }

    slot_values = _homepage_slot_values(copy)
    rebuilt = _homepage_copy_from_slot_values(slot_values, ctx)

    assert sorted(slot_values.keys()) == sorted(HOMEPAGE_MANAGED_SLOTS)
    assert rebuilt["headline"] == copy["headline"]
    assert rebuilt["subtitle"] == copy["subtitle"]
    assert rebuilt["social_proof_items"] == copy["social_proof_items"]


def test_homepage_default_copy_uses_business_context():
    ctx = {
        "name": "Orion Works",
        "sector": "Indústria pesada",
        "main_goal": "aumentar margem",
        "advantage": "execução disciplinada",
        "icp": {"dor": "falta de foco comercial"},
    }

    default_copy = _homepage_default_copy(ctx)

    assert "Orion Works" in default_copy["headline"]
    assert "indústria pesada" in default_copy["subtitle"].lower()
    assert len(default_copy["social_proof_items"]) == 3