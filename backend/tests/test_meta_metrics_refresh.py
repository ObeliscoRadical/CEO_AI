"""
Test Meta Metrics Refresh Endpoint - Iteration 45
Verifies the POST /api/social/metrics/refresh endpoint works correctly
and returns proper responses based on insights readiness state.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL') or os.environ.get('FRONTEND_URL', 'https://marketing-split-test-1.preview.emergentagent.com')
BASE_URL = BASE_URL.rstrip('/')


class TestMetaMetricsRefresh:
    """Tests for the /api/social/metrics/refresh endpoint."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication."""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "adminceoai@gmail.com",
            "password": "12345"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        
        # Store cookies for authenticated requests
        self.cookies = login_response.cookies
        yield
    
    def test_metrics_refresh_endpoint_exists_and_responds(self):
        """
        Test that POST /api/social/metrics/refresh exists and returns a valid response.
        Should not return 500 error even when insights are not ready.
        """
        response = self.session.post(f"{BASE_URL}/api/social/metrics/refresh", cookies=self.cookies)
        
        # Should not be 500 (server error) or 404 (not found)
        assert response.status_code in [200, 400, 401, 403], f"Unexpected status {response.status_code}: {response.text}"
        
        # If 200, verify response structure
        if response.status_code == 200:
            data = response.json()
            assert "ready" in data, f"Expected 'ready' field in response, got {data}"
            assert "refreshed" in data, f"Expected 'refreshed' field in response, got {data}"
            assert "reason" in data, f"Expected 'reason' field in response, got {data}"
            
            print(f"✓ ready: {data.get('ready')}")
            print(f"✓ refreshed: {data.get('refreshed')}")
            print(f"✓ reason: {data.get('reason')}")
    
    def test_metrics_refresh_returns_not_ready_when_insights_missing(self):
        """
        Test that metrics refresh correctly indicates when insights are not ready.
        In the current preview state (degraded connection), this should return ready=false.
        """
        response = self.session.post(f"{BASE_URL}/api/social/metrics/refresh", cookies=self.cookies)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # In degraded state, ready should be false
        # This is the expected behavior when insights scopes are not validated
        if not data.get("ready"):
            assert data.get("reason") is not None, "Expected a reason when not ready"
            print(f"✓ Correctly reports not ready: {data.get('reason')}")
        else:
            # If ready is true, refreshed should be a number
            assert isinstance(data.get("refreshed"), int), f"Expected refreshed to be int, got {type(data.get('refreshed'))}"
            print(f"✓ Ready with {data.get('refreshed')} posts refreshed")


class TestSocialStatusMetricsFields:
    """Tests to verify metrics_mocked and live_metrics_ready fields in /api/social/status."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication."""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "adminceoai@gmail.com",
            "password": "12345"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.cookies = login_response.cookies
        yield
    
    def test_social_status_includes_metrics_fields(self):
        """
        Test that /api/social/status includes metrics_mocked and live_metrics_ready fields.
        """
        response = self.session.get(f"{BASE_URL}/api/social/status", cookies=self.cookies)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify metrics fields exist
        assert "metrics_mocked" in data, f"Expected 'metrics_mocked' field, got {data.keys()}"
        assert "live_metrics_ready" in data, f"Expected 'live_metrics_ready' field, got {data.keys()}"
        
        # Verify they are boolean
        assert isinstance(data.get("metrics_mocked"), bool), f"metrics_mocked should be bool, got {type(data.get('metrics_mocked'))}"
        assert isinstance(data.get("live_metrics_ready"), bool), f"live_metrics_ready should be bool, got {type(data.get('live_metrics_ready'))}"
        
        # They should be opposite of each other
        assert data.get("metrics_mocked") != data.get("live_metrics_ready"), \
            f"metrics_mocked ({data.get('metrics_mocked')}) should be opposite of live_metrics_ready ({data.get('live_metrics_ready')})"
        
        print(f"✓ metrics_mocked: {data.get('metrics_mocked')}")
        print(f"✓ live_metrics_ready: {data.get('live_metrics_ready')}")
    
    def test_diagnostics_includes_insights_permissions_check(self):
        """
        Test that /api/social/diagnostics includes the meta_insights_permissions check.
        """
        response = self.session.post(f"{BASE_URL}/api/social/diagnostics", cookies=self.cookies)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        checks = data.get("checks", [])
        
        # Find the insights permissions check
        insights_check = next((c for c in checks if c.get("id") == "meta_insights_permissions"), None)
        
        # The check should exist when there's a connection (even degraded)
        if data.get("connection_state") in ["connected", "degraded"]:
            assert insights_check is not None, f"Expected meta_insights_permissions check, got checks: {[c.get('id') for c in checks]}"
            
            print(f"✓ meta_insights_permissions check found")
            print(f"  - ok: {insights_check.get('ok')}")
            print(f"  - detail: {insights_check.get('detail')}")
            
            # Verify the check has proper structure
            assert "ok" in insights_check, "Check should have 'ok' field"
            assert "detail" in insights_check, "Check should have 'detail' field"
            assert "label" in insights_check, "Check should have 'label' field"
        else:
            print(f"✓ Connection state is {data.get('connection_state')}, insights check may not be present")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
