import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from routers.social import _base_checks, _scope_set, _status_payload


def _sample_connection(scopes=None, granular_scopes=None, insights_status=None):
    scopes = scopes or []
    granular_scopes = granular_scopes or []
    checks = [{"id": "meta_insights_permissions", "ok": bool(scopes or granular_scopes)}]
    return {
        "status": "connected",
        "page_id": "page-1",
        "page_token": "page-token",
        "page_name": "Página Teste",
        "ig_user_id": "ig-1",
        "ig_username": "perfil_teste",
        "tasks": ["CREATE_CONTENT", "MANAGE", "ANALYZE"],
        "granted_scopes": scopes,
        "granular_scopes": granular_scopes,
        "insights_status": insights_status,
        "last_diagnostics": {"checks": checks},
    }


def test_live_metrics_ready_when_insights_scopes_exist():
    conn = _sample_connection(
        scopes=[
            "instagram_basic",
            "instagram_manage_insights",
            "pages_read_engagement",
            "read_insights",
        ],
        insights_status="ready",
    )
    checks = _base_checks("aid", "sec", conn)
    insights_check = next(item for item in checks if item["id"] == "meta_insights_permissions")
    payload = _status_payload(conn, "aid", "sec", checks)

    assert insights_check["ok"] is True
    assert payload["live_metrics_ready"] is True
    assert payload["metrics_mocked"] is False


def test_live_metrics_stay_mocked_without_insights_scopes():
    conn = _sample_connection(scopes=[])
    checks = _base_checks("aid", "sec", conn)
    insights_check = next(item for item in checks if item["id"] == "meta_insights_permissions")
    payload = _status_payload(conn, "aid", "sec", checks)

    assert insights_check["ok"] is False
    assert payload["live_metrics_ready"] is False
    assert payload["metrics_mocked"] is True


def test_granular_scopes_are_treated_as_valid_permissions():
    conn = _sample_connection(granular_scopes=[
        {"scope": "instagram_basic"},
        {"scope": "instagram_manage_insights"},
        {"scope": "pages_read_engagement"},
        {"scope": "read_insights"},
    ])

    assert _scope_set(conn) == {
        "instagram_basic",
        "instagram_manage_insights",
        "pages_read_engagement",
        "read_insights",
    }

    checks = _base_checks("aid", "sec", conn)
    insights_check = next(item for item in checks if item["id"] == "meta_insights_permissions")
    payload = _status_payload(conn, "aid", "sec", checks)

    assert insights_check["ok"] is True
    assert payload["insights_permissions_ready"] is True


def test_permissions_can_be_ready_while_metrics_stay_mocked_without_data():
    conn = _sample_connection(
        scopes=[
            "instagram_basic",
            "instagram_manage_insights",
            "pages_read_engagement",
            "read_insights",
        ],
        insights_status="no_data",
    )

    checks = _base_checks("aid", "sec", conn)
    insights_check = next(item for item in checks if item["id"] == "meta_insights_permissions")
    payload = _status_payload(conn, "aid", "sec", checks)

    assert insights_check["ok"] is True
    assert payload["insights_permissions_ready"] is True
    assert payload["live_metrics_ready"] is False
    assert payload["metrics_mocked"] is True
    assert payload["insights_status"] == "no_data"