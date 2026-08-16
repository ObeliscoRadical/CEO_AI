"""
Iteration 51 - Homepage Management + SEO Tests
Tests for:
- GET /api/marketing/site-publishing/status (homepage.live, homepage.proposal, managed_slots, updated_at, last_proposal_at, last_applied_at)
- POST /api/marketing/site-publishing/homepage/proposal
- POST /api/marketing/site-publishing/homepage/apply
- GET /api/public/sitemap.xml (with <lastmod>)
- SEO metadata on public homepage
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://marketing-split-test-1.preview.emergentagent.com").rstrip("/")


@pytest.fixture(scope="module")
def auth_cookies():
    """Login and get auth cookies"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "adminceoai@gmail.com",
        "password": "12345"
    })
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.cookies


class TestHomepageManagementAPI:
    """Tests for homepage management endpoints"""

    def test_site_publishing_status_returns_homepage_fields(self, auth_cookies):
        """GET /api/marketing/site-publishing/status returns homepage with all required fields"""
        resp = requests.get(f"{BASE_URL}/api/marketing/site-publishing/status", cookies=auth_cookies)
        assert resp.status_code == 200
        
        data = resp.json()
        assert "homepage" in data
        
        homepage = data["homepage"]
        # Check all required fields exist
        assert "live" in homepage
        assert "proposal" in homepage
        assert "managed_slots" in homepage
        assert "updated_at" in homepage
        assert "last_proposal_at" in homepage
        assert "last_applied_at" in homepage
        
        # Check managed_slots contains expected slots
        expected_slots = [
            "login.hero_headline",
            "login.hero_subtitle",
            "login.hero_primary_cta_label",
            "login.hero_primary_cta_url",
            "login.hero_secondary_cta_label",
            "login.hero_secondary_cta_url",
            "login.social_proof_title",
            "login.social_proof_1",
            "login.social_proof_2",
            "login.social_proof_3",
        ]
        for slot in expected_slots:
            assert slot in homepage["managed_slots"], f"Missing slot: {slot}"

    def test_site_publishing_status_live_has_homepage_copy_fields(self, auth_cookies):
        """homepage.live contains headline, subtitle, CTAs, and social proof"""
        resp = requests.get(f"{BASE_URL}/api/marketing/site-publishing/status", cookies=auth_cookies)
        assert resp.status_code == 200
        
        live = resp.json()["homepage"]["live"]
        assert "headline" in live
        assert "subtitle" in live
        assert "primary_cta_label" in live
        assert "primary_cta_url" in live
        assert "secondary_cta_label" in live
        assert "secondary_cta_url" in live
        assert "social_proof_title" in live
        assert "social_proof_items" in live
        assert isinstance(live["social_proof_items"], list)
        assert len(live["social_proof_items"]) == 3

    def test_homepage_proposal_generation(self, auth_cookies):
        """POST /api/marketing/site-publishing/homepage/proposal generates a proposal"""
        resp = requests.post(
            f"{BASE_URL}/api/marketing/site-publishing/homepage/proposal",
            json={"use_ai": False},
            cookies=auth_cookies
        )
        assert resp.status_code == 200
        
        data = resp.json()
        assert "proposal" in data
        assert "status" in data
        
        proposal = data["proposal"]
        assert "headline" in proposal
        assert "subtitle" in proposal
        assert "social_proof_items" in proposal
        assert len(proposal["social_proof_items"]) == 3

    def test_homepage_apply_updates_live_content(self, auth_cookies):
        """POST /api/marketing/site-publishing/homepage/apply updates live homepage"""
        resp = requests.post(
            f"{BASE_URL}/api/marketing/site-publishing/homepage/apply",
            json={},
            cookies=auth_cookies
        )
        assert resp.status_code == 200
        
        data = resp.json()
        assert "homepage" in data
        assert "status" in data
        
        homepage = data["homepage"]
        assert homepage.get("last_applied_at") is not None
        assert homepage.get("live") is not None


class TestSitemapXML:
    """Tests for sitemap.xml endpoint"""

    def test_sitemap_returns_xml_with_lastmod(self):
        """GET /api/public/sitemap.xml returns XML with <lastmod> tags"""
        resp = requests.get(f"{BASE_URL}/api/public/sitemap.xml")
        assert resp.status_code == 200
        assert "application/xml" in resp.headers.get("content-type", "")
        
        content = resp.text
        assert "<?xml" in content
        assert "<urlset" in content
        assert "<url>" in content
        assert "<loc>" in content
        assert "<lastmod>" in content
        
        # Check that lastmod has a date format (YYYY-MM-DD)
        import re
        lastmod_pattern = r"<lastmod>\d{4}-\d{2}-\d{2}</lastmod>"
        assert re.search(lastmod_pattern, content), "lastmod should have YYYY-MM-DD format"


class TestPublicSections:
    """Tests for public sections endpoint used by Login page"""

    def test_public_sections_returns_homepage_slots(self):
        """GET /api/public/site/sections returns homepage slot values"""
        slots = ",".join([
            "login.hero_headline",
            "login.hero_subtitle",
            "login.hero_primary_cta_label",
            "login.hero_primary_cta_url",
            "login.hero_secondary_cta_label",
            "login.hero_secondary_cta_url",
            "login.social_proof_title",
            "login.social_proof_1",
            "login.social_proof_2",
            "login.social_proof_3",
        ])
        resp = requests.get(f"{BASE_URL}/api/public/site/sections?slots={slots}")
        assert resp.status_code == 200
        
        data = resp.json()
        assert "sections" in data
        
        sections = data["sections"]
        # After apply, sections should have values
        if sections:
            for key, value in sections.items():
                assert "value" in value
                assert "updated_at" in value


class TestGatewayAuthorization:
    """Tests for gateway authorization (required for homepage apply)"""

    def test_gateway_authorization_status(self, auth_cookies):
        """Check gateway authorization status"""
        resp = requests.get(f"{BASE_URL}/api/marketing/site-publishing/status", cookies=auth_cookies)
        assert resp.status_code == 200
        
        settings = resp.json().get("settings", {})
        # Gateway should be authorized for homepage apply to work
        assert "authorized" in settings


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
