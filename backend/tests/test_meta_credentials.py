"""
Test Meta Credentials Configuration - Iteration 44
Verifies that META_APP_ID and META_APP_SECRET are properly recognized by the backend.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestMetaCredentialsConfiguration:
    """Tests to verify Meta credentials are properly configured in the preview environment."""
    
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
    
    def test_social_status_shows_configured_true(self):
        """
        Test that /api/social/status returns configured=true and missing_config is empty.
        This verifies META_APP_ID and META_APP_SECRET are recognized at runtime.
        """
        response = self.session.get(f"{BASE_URL}/api/social/status", cookies=self.cookies)
        
        # Status code assertion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Critical assertions for credential configuration
        assert data.get("configured") == True, f"Expected configured=true, got {data.get('configured')}"
        assert data.get("missing_config") == [], f"Expected missing_config=[], got {data.get('missing_config')}"
        
        # Additional verification
        print(f"✓ configured: {data.get('configured')}")
        print(f"✓ missing_config: {data.get('missing_config')}")
        print(f"✓ config_id_present: {data.get('config_id_present')}")
        print(f"✓ connection_state: {data.get('connection_state')}")
        print(f"✓ connected: {data.get('connected')}")
        
        # Verify config_id is also present (META_CONFIG_ID)
        assert data.get("config_id_present") == True, f"Expected config_id_present=true, got {data.get('config_id_present')}"
    
    def test_social_diagnostics_confirms_credentials(self):
        """
        Test that /api/social/diagnostics confirms Meta app credentials are ready.
        This runs a full diagnostic check on the Meta integration.
        """
        response = self.session.post(f"{BASE_URL}/api/social/diagnostics", cookies=self.cookies)
        
        # Status code assertion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Critical assertions for credential configuration
        assert data.get("configured") == True, f"Expected configured=true, got {data.get('configured')}"
        assert data.get("missing_config") == [], f"Expected missing_config=[], got {data.get('missing_config')}"
        
        # Check the checks array for meta_app_credentials
        checks = data.get("checks", [])
        credentials_check = next((c for c in checks if c.get("id") == "meta_app_credentials"), None)
        
        assert credentials_check is not None, "meta_app_credentials check not found in diagnostics"
        assert credentials_check.get("ok") == True, f"meta_app_credentials check failed: {credentials_check}"
        
        print(f"✓ configured: {data.get('configured')}")
        print(f"✓ missing_config: {data.get('missing_config')}")
        print(f"✓ meta_app_credentials check: {credentials_check}")
        
        # Print connection state for context
        print(f"✓ connection_state: {data.get('connection_state')}")
        print(f"✓ connected: {data.get('connected')}")
        
        # If there's a degraded state, it should be about token/connection, not credentials
        if data.get("connection_state") == "degraded":
            print("⚠ Connection is degraded - this is expected if token/page needs reconnection")
            # Find the failing checks
            failing_checks = [c for c in checks if not c.get("ok")]
            for fc in failing_checks:
                print(f"  - {fc.get('id')}: {fc.get('detail')}")
    
    def test_social_requirements_shows_no_missing_credentials(self):
        """
        Test that /api/social/requirements confirms no missing credentials.
        """
        response = self.session.get(f"{BASE_URL}/api/social/requirements", cookies=self.cookies)
        
        # Status code assertion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Critical assertions
        assert data.get("configured") == True, f"Expected configured=true, got {data.get('configured')}"
        assert data.get("missing_config") == [], f"Expected missing_config=[], got {data.get('missing_config')}"
        
        print(f"✓ configured: {data.get('configured')}")
        print(f"✓ missing_config: {data.get('missing_config')}")
        print(f"✓ requirements: {data.get('requirements')}")
    
    def test_social_connect_returns_auth_url(self):
        """
        Test that /api/social/connect returns an auth_url when credentials are configured.
        This proves the backend can generate OAuth URLs with the configured credentials.
        """
        response = self.session.get(f"{BASE_URL}/api/social/connect", cookies=self.cookies)
        
        # Status code assertion - should be 200 if credentials are configured
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Should return an auth_url
        assert "auth_url" in data, f"Expected auth_url in response, got {data}"
        auth_url = data.get("auth_url", "")
        
        # Verify the auth_url contains the META_APP_ID
        assert "2623447624739815" in auth_url, f"Expected META_APP_ID in auth_url, got {auth_url}"
        
        print(f"✓ auth_url generated successfully")
        print(f"✓ Contains META_APP_ID: {'2623447624739815' in auth_url}")
        print(f"✓ Contains config_id: {'1032274772743161' in auth_url}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
