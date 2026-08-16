import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from routers.site_publishing import _build_site_change_history


def test_change_history_builds_filters_and_rich_diff():
    logs = [
        {
            "id": "log-1",
            "entry_id": "entry-1",
            "entry_title": "Página de Serviços",
            "kind": "page",
            "action": "update",
            "status": "ok",
            "url": "/site/pagina-servicos",
            "actor": "organic_agent",
            "seo_keyword": "serviços industriais",
            "objective": "crescimento orgânico",
            "strategy_reason": "Melhorar conversão da página principal.",
            "created_at": "2026-08-16T10:00:00+00:00",
            "rollback_available": True,
            "previous_content": {
                "id": "entry-1",
                "kind": "page",
                "title": "Página de Serviços",
                "status": "published",
                "excerpt": "Versão antiga.",
                "intro": "Intro antiga.",
                "cta_label": "Falar connosco",
                "cta_url": "/contacto",
                "seo_keyword": "serviços industriais",
                "seo_title": "Serviços industriais",
                "seo_description": "Descrição antiga.",
                "sections": [{"heading": "Antes", "paragraphs": ["Texto antigo"], "bullets": []}],
                "current_version": 2,
                "public_url": "/site/pagina-servicos",
            },
            "new_content": {
                "id": "entry-1",
                "kind": "page",
                "title": "Página de Serviços Premium",
                "status": "published",
                "excerpt": "Versão nova.",
                "intro": "Intro nova.",
                "cta_label": "Marcar diagnóstico",
                "cta_url": "/contacto",
                "seo_keyword": "serviços industriais premium",
                "seo_title": "Serviços industriais premium",
                "seo_description": "Descrição nova.",
                "sections": [{"heading": "Depois", "paragraphs": ["Texto novo"], "bullets": ["Prova social"]}],
                "current_version": 3,
                "public_url": "/site/pagina-servicos",
            },
        }
    ]
    version_lookup = {"entry-1": {2: "version-2", 3: "version-3"}}

    payload = _build_site_change_history(logs, version_lookup)

    assert payload["summary"]["total"] == 1
    assert payload["summary"]["update"] == 1
    assert payload["filters"]["pages"][0]["label"] == "Página de Serviços"
    assert payload["filters"]["dates"] == ["2026-08-16"]

    item = payload["items"][0]
    assert item["rollback_version_id"] == "version-2"
    assert item["action_label"] == "Atualização"
    assert item["kind_label"] == "Página"
    assert item["before_preview"]["title"] == "Página de Serviços"
    assert item["after_preview"]["title"] == "Página de Serviços Premium"
    diff_labels = [row["label"] for row in item["diff_items"]]
    assert "Título" in diff_labels
    assert "CTA" in diff_labels
    assert "Estrutura" in diff_labels


def test_change_history_handles_create_without_previous_snapshot():
    logs = [
        {
            "id": "log-2",
            "entry_id": "entry-2",
            "entry_title": "Novo Artigo",
            "kind": "article",
            "action": "create",
            "status": "ok",
            "url": "/insights/novo-artigo",
            "created_at": "2026-08-15T09:30:00+00:00",
            "rollback_available": True,
            "previous_content": None,
            "new_content": {
                "id": "entry-2",
                "kind": "article",
                "title": "Novo Artigo",
                "status": "published",
                "excerpt": "Conteúdo publicado.",
                "current_version": 1,
                "public_url": "/insights/novo-artigo",
            },
        }
    ]

    payload = _build_site_change_history(logs, {"entry-2": {1: "version-1"}})

    item = payload["items"][0]
    assert payload["summary"]["create"] == 1
    assert item["rollback_version_id"] is None
    assert item["before_preview"] is None
    assert item["after_preview"]["title"] == "Novo Artigo"
    assert any(diff["mode"] == "added" for diff in item["diff_items"])