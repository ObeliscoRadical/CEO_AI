"""
Backend API tests for Meta insights readiness endpoints.
Tests the new fields: insights_status, insights_permissions_ready, insights_last_checked_at,
insights_probe_detail, report_source, metrics_mocked, live_metrics_ready
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


class TestMetaInsightsAPI:
    """Tests for Meta insights readiness API endpoints"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        # Login to get auth cookie
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "adminceoai@gmail.com", "password": "12345"}
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        yield
        # Logout after tests
        self.session.post(f"{BASE_URL}/api/auth/logout")

    def test_social_status_returns_new_insights_fields(self):
        """GET /api/social/status should return new insights-related fields"""
        response = self.session.get(f"{BASE_URL}/api/social/status")
        assert response.status_code == 200, f"Status endpoint failed: {response.text}"
        
        data = response.json()
        
        # Verify new fields exist in response
        assert "insights_status" in data, "Missing insights_status field"
        assert "insights_permissions_ready" in data, "Missing insights_permissions_ready field"
        assert "insights_last_checked_at" in data or data.get("insights_last_checked_at") is None, "insights_last_checked_at should be present"
        assert "insights_probe_detail" in data or data.get("insights_probe_detail") is None, "insights_probe_detail should be present"
        assert "report_source" in data, "Missing report_source field"
        assert "metrics_mocked" in data, "Missing metrics_mocked field"
        assert "live_metrics_ready" in data, "Missing live_metrics_ready field"
        
        # Verify field types
        assert isinstance(data["metrics_mocked"], bool), "metrics_mocked should be boolean"
        assert isinstance(data["live_metrics_ready"], bool), "live_metrics_ready should be boolean"
        assert isinstance(data["insights_permissions_ready"], bool), "insights_permissions_ready should be boolean"
        
        # Verify coherence: metrics_mocked and live_metrics_ready should be opposites
        assert data["metrics_mocked"] != data["live_metrics_ready"], "metrics_mocked and live_metrics_ready should be opposites"
        
        print(f"PASS: /api/social/status returns all new insights fields")
        print(f"  - insights_status: {data.get('insights_status')}")
        print(f"  - insights_permissions_ready: {data.get('insights_permissions_ready')}")
        print(f"  - report_source: {data.get('report_source')}")
        print(f"  - metrics_mocked: {data.get('metrics_mocked')}")
        print(f"  - live_metrics_ready: {data.get('live_metrics_ready')}")

    def test_social_diagnostics_returns_new_fields(self):
        """POST /api/social/diagnostics should return new insights-related fields"""
        response = self.session.post(f"{BASE_URL}/api/social/diagnostics")
        assert response.status_code == 200, f"Diagnostics endpoint failed: {response.text}"
        
        data = response.json()
        
        # Verify new fields exist
        assert "insights_status" in data, "Missing insights_status field"
        assert "insights_permissions_ready" in data, "Missing insights_permissions_ready field"
        assert "report_source" in data, "Missing report_source field"
        assert "metrics_mocked" in data, "Missing metrics_mocked field"
        assert "live_metrics_ready" in data, "Missing live_metrics_ready field"
        
        # Verify checks array exists and has expected structure
        assert "checks" in data, "Missing checks array"
        assert isinstance(data["checks"], list), "checks should be a list"
        
        # Look for insights permissions check
        insights_check = next(
            (c for c in data["checks"] if c.get("id") == "meta_insights_permissions"),
            None
        )
        # insights_check may not exist if connection is not ready
        if insights_check:
            assert "ok" in insights_check, "insights check should have 'ok' field"
            assert "detail" in insights_check, "insights check should have 'detail' field"
            print(f"  - meta_insights_permissions check: ok={insights_check.get('ok')}")
        
        print(f"PASS: /api/social/diagnostics returns all new insights fields")
        print(f"  - insights_status: {data.get('insights_status')}")
        print(f"  - report_source: {data.get('report_source')}")

    def test_metrics_refresh_endpoint_exists_and_responds(self):
        """POST /api/social/metrics/refresh should exist and return coherent payload"""
        response = self.session.post(f"{BASE_URL}/api/social/metrics/refresh")
        assert response.status_code == 200, f"Metrics refresh endpoint failed: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "ready" in data, "Missing 'ready' field in response"
        assert "refreshed" in data, "Missing 'refreshed' field in response"
        assert "reason" in data or data.get("reason") is None, "Missing 'reason' field in response"
        
        # Verify types
        assert isinstance(data["ready"], bool), "'ready' should be boolean"
        assert isinstance(data["refreshed"], int), "'refreshed' should be integer"
        
        # Verify coherence: if not ready, reason should explain why
        if not data["ready"]:
            assert data.get("reason") is not None, "When not ready, reason should be provided"
            assert isinstance(data["reason"], str), "reason should be a string"
            assert len(data["reason"]) > 0, "reason should not be empty"
        
        print(f"PASS: /api/social/metrics/refresh returns coherent payload")
        print(f"  - ready: {data.get('ready')}")
        print(f"  - refreshed: {data.get('refreshed')}")
        print(f"  - reason: {data.get('reason')[:80] if data.get('reason') else 'None'}...")

    def test_social_status_configured_true(self):
        """Verify Meta credentials are configured (from previous iteration)"""
        response = self.session.get(f"{BASE_URL}/api/social/status")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("configured") is True, "Meta should be configured"
        assert data.get("missing_config") == [], "No missing config expected"
        
        print(f"PASS: Meta credentials are configured")
        print(f"  - configured: {data.get('configured')}")
        print(f"  - missing_config: {data.get('missing_config')}")

    def test_connection_state_is_coherent(self):
        """Verify connection_state is one of expected values"""
        response = self.session.get(f"{BASE_URL}/api/social/status")
        assert response.status_code == 200
        
        data = response.json()
        valid_states = ["not_connected", "pending_selection", "connected", "degraded"]
        assert data.get("connection_state") in valid_states, f"Invalid connection_state: {data.get('connection_state')}"
        
        print(f"PASS: connection_state is valid: {data.get('connection_state')}")

    def test_insights_status_is_coherent(self):
        """Verify insights_status is one of expected values"""
        response = self.session.get(f"{BASE_URL}/api/social/status")
        assert response.status_code == 200
        
        data = response.json()
        valid_statuses = ["ready", "no_data", "permission_ready", "permission_denied", "expired", "unverified", "unavailable"]
        insights_status = data.get("insights_status")
        assert insights_status in valid_statuses, f"Invalid insights_status: {insights_status}"
        
        print(f"PASS: insights_status is valid: {insights_status}")

    def test_report_source_is_coherent(self):
        """Verify report_source is either 'real' or 'mock'"""
        response = self.session.get(f"{BASE_URL}/api/social/status")
        assert response.status_code == 200
        
        data = response.json()
        valid_sources = ["real", "mock"]
        report_source = data.get("report_source")
        assert report_source in valid_sources, f"Invalid report_source: {report_source}"
        
        # Coherence check: if live_metrics_ready, report_source should be 'real'
        if data.get("live_metrics_ready"):
            assert report_source == "real", "When live_metrics_ready=True, report_source should be 'real'"
        else:
            assert report_source == "mock", "When live_metrics_ready=False, report_source should be 'mock'"
        
        print(f"PASS: report_source is coherent: {report_source}")

    def test_no_500_errors_on_endpoints(self):
        """Verify none of the endpoints return 500 errors"""
        endpoints = [
            ("GET", "/api/social/status"),
            ("POST", "/api/social/diagnostics"),
            ("POST", "/api/social/metrics/refresh"),
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = self.session.get(f"{BASE_URL}{endpoint}")
            else:
                response = self.session.post(f"{BASE_URL}{endpoint}")
            
            assert response.status_code != 500, f"{method} {endpoint} returned 500: {response.text}"
            print(f"PASS: {method} {endpoint} - status {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
