#!/usr/bin/env python3
"""
Backend API Testing for CEO AI Marketing Module Expansion
Tests authentication, social endpoints, campaign generation, and regression checks.
"""
import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "https://seo-marketing-hub-12.preview.emergentagent.com/api"
TEST_EMAIL = "adminceoai@gmail.com"
TEST_PASSWORD = "12345"

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

class TestResults:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []
    
    def add_pass(self, test_name, details=""):
        self.passed.append((test_name, details))
        print(f"{GREEN}✓ PASS{RESET}: {test_name}")
        if details:
            print(f"  {details}")
    
    def add_fail(self, test_name, error):
        self.failed.append((test_name, error))
        print(f"{RED}✗ FAIL{RESET}: {test_name}")
        print(f"  {RED}{error}{RESET}")
    
    def add_warning(self, test_name, message):
        self.warnings.append((test_name, message))
        print(f"{YELLOW}⚠ WARNING{RESET}: {test_name}")
        print(f"  {message}")
    
    def summary(self):
        print(f"\n{'='*70}")
        print(f"{BLUE}TEST SUMMARY{RESET}")
        print(f"{'='*70}")
        print(f"{GREEN}Passed{RESET}: {len(self.passed)}")
        print(f"{RED}Failed{RESET}: {len(self.failed)}")
        print(f"{YELLOW}Warnings{RESET}: {len(self.warnings)}")
        
        if self.failed:
            print(f"\n{RED}FAILED TESTS:{RESET}")
            for test_name, error in self.failed:
                print(f"  • {test_name}")
                print(f"    {error}")
        
        return len(self.failed) == 0

results = TestResults()
session = requests.Session()
auth_token = None

def test_login():
    """Test 1: Login authentication"""
    global auth_token
    print(f"\n{BLUE}[TEST 1] Login Authentication{RESET}")
    
    try:
        response = session.post(
            f"{BASE_URL}/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            # Response can be either {"user": {...}} or directly the user object
            user = data.get("user", data) if isinstance(data, dict) else None
            
            if user and user.get("email") == TEST_EMAIL:
                results.add_pass("Login Authentication", f"User: {user.get('name')} | Role: {user.get('role')}")
                return True
            else:
                results.add_fail("Login Authentication", f"Invalid response structure or email mismatch: {data}")
                return False
        else:
            results.add_fail("Login Authentication", f"Status {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        results.add_fail("Login Authentication", f"Exception: {str(e)}")
        return False

def test_social_status():
    """Test 2: GET /api/social/status"""
    print(f"\n{BLUE}[TEST 2] GET /api/social/status{RESET}")
    
    try:
        response = session.get(f"{BASE_URL}/social/status", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Validate expected fields
            required_fields = ["configured", "missing_config", "connected", "connection_state", "checks"]
            missing_fields = [f for f in required_fields if f not in data]
            
            if missing_fields:
                results.add_fail("GET /api/social/status", f"Missing fields: {missing_fields}")
                return False
            
            # Check that it reports not configured (since META_APP_ID/SECRET are empty)
            if not data.get("configured"):
                if "META_APP_ID" in data.get("missing_config", []) and "META_APP_SECRET" in data.get("missing_config", []):
                    results.add_pass(
                        "GET /api/social/status",
                        f"Correctly reports missing config: {data.get('missing_config')} | State: {data.get('connection_state')}"
                    )
                    return True
                else:
                    results.add_warning(
                        "GET /api/social/status",
                        f"Configured=False but missing_config unexpected: {data.get('missing_config')}"
                    )
                    return True
            else:
                results.add_warning(
                    "GET /api/social/status",
                    "Reports configured=True despite empty META credentials in .env"
                )
                return True
        else:
            results.add_fail("GET /api/social/status", f"Status {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        results.add_fail("GET /api/social/status", f"Exception: {str(e)}")
        return False

def test_social_requirements():
    """Test 3: GET /api/social/requirements"""
    print(f"\n{BLUE}[TEST 3] GET /api/social/requirements{RESET}")
    
    try:
        response = session.get(f"{BASE_URL}/social/requirements", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Validate expected fields
            required_fields = ["configured", "requirements", "checks"]
            missing_fields = [f for f in required_fields if f not in data]
            
            if missing_fields:
                results.add_fail("GET /api/social/requirements", f"Missing fields: {missing_fields}")
                return False
            
            # Check requirements list
            requirements = data.get("requirements", [])
            if isinstance(requirements, list) and len(requirements) > 0:
                results.add_pass(
                    "GET /api/social/requirements",
                    f"Returns {len(requirements)} requirements | Checks: {len(data.get('checks', []))}"
                )
                return True
            else:
                results.add_fail("GET /api/social/requirements", "Requirements list is empty or invalid")
                return False
        else:
            results.add_fail("GET /api/social/requirements", f"Status {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        results.add_fail("GET /api/social/requirements", f"Exception: {str(e)}")
        return False

def test_social_diagnostics():
    """Test 4: POST /api/social/diagnostics"""
    print(f"\n{BLUE}[TEST 4] POST /api/social/diagnostics{RESET}")
    
    try:
        response = session.post(f"{BASE_URL}/social/diagnostics", json={}, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Validate it doesn't crash and returns checks
            if "checks" in data:
                checks = data.get("checks", [])
                if isinstance(checks, list):
                    results.add_pass(
                        "POST /api/social/diagnostics",
                        f"No crash without Meta config | Returns {len(checks)} diagnostic checks | State: {data.get('connection_state')}"
                    )
                    return True
                else:
                    results.add_fail("POST /api/social/diagnostics", "Checks field is not a list")
                    return False
            else:
                results.add_fail("POST /api/social/diagnostics", "Missing 'checks' field in response")
                return False
        else:
            results.add_fail("POST /api/social/diagnostics", f"Status {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        results.add_fail("POST /api/social/diagnostics", f"Exception: {str(e)}")
        return False

def test_campaign_generate():
    """Test 5: POST /api/marketing/campaigns/generate with objective=leads"""
    print(f"\n{BLUE}[TEST 5] POST /api/marketing/campaigns/generate (objective=leads){RESET}")
    
    try:
        payload = {
            "objective": "leads",
            "name": "Campanha de Leads - Teste Backend",
            "offer": "Diagnóstico gratuito de 30 minutos",
            "audience": "PMEs em crescimento",
            "notes": "Teste de validação backend"
        }
        
        response = session.post(
            f"{BASE_URL}/marketing/campaigns/generate",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if "campaign" not in data:
                results.add_fail("POST /api/marketing/campaigns/generate", "Missing 'campaign' field in response")
                return False
            
            campaign = data["campaign"]
            
            # Validate campaign structure
            required_fields = ["objective", "name", "channels", "kpis", "launch_plan", "next_actions"]
            missing_fields = [f for f in required_fields if f not in campaign]
            
            if missing_fields:
                results.add_fail("POST /api/marketing/campaigns/generate", f"Missing campaign fields: {missing_fields}")
                return False
            
            # Validate objective
            if campaign.get("objective") != "leads":
                results.add_fail("POST /api/marketing/campaigns/generate", f"Expected objective 'leads', got '{campaign.get('objective')}'")
                return False
            
            # Validate channels (should have 4)
            channels = campaign.get("channels", [])
            if not isinstance(channels, list) or len(channels) < 3:
                results.add_fail("POST /api/marketing/campaigns/generate", f"Expected at least 3 channels, got {len(channels)}")
                return False
            
            # Validate each channel has required fields
            for idx, channel in enumerate(channels):
                channel_required = ["channel", "format", "hook", "cta", "distribution", "purpose"]
                channel_missing = [f for f in channel_required if f not in channel]
                if channel_missing:
                    results.add_fail("POST /api/marketing/campaigns/generate", f"Channel {idx} missing fields: {channel_missing}")
                    return False
            
            # Validate KPIs
            kpis = campaign.get("kpis", [])
            if not isinstance(kpis, list) or len(kpis) < 3:
                results.add_fail("POST /api/marketing/campaigns/generate", f"Expected at least 3 KPIs, got {len(kpis)}")
                return False
            
            # Validate launch_plan
            launch_plan = campaign.get("launch_plan", [])
            if not isinstance(launch_plan, list) or len(launch_plan) < 3:
                results.add_fail("POST /api/marketing/campaigns/generate", f"Expected at least 3 launch plan items, got {len(launch_plan)}")
                return False
            
            # Validate next_actions
            next_actions = campaign.get("next_actions", [])
            if not isinstance(next_actions, list) or len(next_actions) < 2:
                results.add_fail("POST /api/marketing/campaigns/generate", f"Expected at least 2 next actions, got {len(next_actions)}")
                return False
            
            results.add_pass(
                "POST /api/marketing/campaigns/generate",
                f"Campaign created | Objective: {campaign.get('objective')} | Channels: {len(channels)} | KPIs: {len(kpis)} | Launch steps: {len(launch_plan)}"
            )
            return True
        else:
            results.add_fail("POST /api/marketing/campaigns/generate", f"Status {response.status_code}: {response.text[:300]}")
            return False
    except Exception as e:
        results.add_fail("POST /api/marketing/campaigns/generate", f"Exception: {str(e)}")
        return False

def test_campaigns_list():
    """Test 6: GET /api/marketing/campaigns"""
    print(f"\n{BLUE}[TEST 6] GET /api/marketing/campaigns{RESET}")
    
    try:
        response = session.get(f"{BASE_URL}/marketing/campaigns", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            if "campaigns" not in data:
                results.add_fail("GET /api/marketing/campaigns", "Missing 'campaigns' field in response")
                return False
            
            campaigns = data.get("campaigns", [])
            if not isinstance(campaigns, list):
                results.add_fail("GET /api/marketing/campaigns", "Campaigns field is not a list")
                return False
            
            # Should have at least the campaign we just created
            if len(campaigns) > 0:
                # Check first campaign structure
                campaign = campaigns[0]
                if "objective" in campaign and "name" in campaign:
                    results.add_pass(
                        "GET /api/marketing/campaigns",
                        f"Returns {len(campaigns)} campaign(s) | Latest: {campaign.get('name', 'N/A')[:50]}"
                    )
                    return True
                else:
                    results.add_fail("GET /api/marketing/campaigns", "Campaign missing required fields (objective, name)")
                    return False
            else:
                results.add_warning(
                    "GET /api/marketing/campaigns",
                    "No campaigns found (expected at least 1 from previous test)"
                )
                return True
        else:
            results.add_fail("GET /api/marketing/campaigns", f"Status {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        results.add_fail("GET /api/marketing/campaigns", f"Exception: {str(e)}")
        return False

def test_marketing_content():
    """Test 7: GET /api/marketing/content (regression)"""
    print(f"\n{BLUE}[TEST 7] GET /api/marketing/content (regression){RESET}")
    
    try:
        response = session.get(f"{BASE_URL}/marketing/content", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            if "content" in data:
                results.add_pass("GET /api/marketing/content", "Endpoint responds correctly")
                return True
            else:
                results.add_fail("GET /api/marketing/content", "Missing 'content' field in response")
                return False
        else:
            results.add_fail("GET /api/marketing/content", f"Status {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        results.add_fail("GET /api/marketing/content", f"Exception: {str(e)}")
        return False

def test_marketing_execution():
    """Test 8: GET /api/marketing/execution (regression)"""
    print(f"\n{BLUE}[TEST 8] GET /api/marketing/execution (regression){RESET}")
    
    try:
        response = session.get(f"{BASE_URL}/marketing/execution", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            required_fields = ["summary", "queued", "history"]
            missing_fields = [f for f in required_fields if f not in data]
            
            if missing_fields:
                results.add_fail("GET /api/marketing/execution", f"Missing fields: {missing_fields}")
                return False
            
            results.add_pass(
                "GET /api/marketing/execution",
                f"Queued: {data.get('summary', {}).get('queued', 0)} | Published: {data.get('summary', {}).get('published', 0)}"
            )
            return True
        else:
            results.add_fail("GET /api/marketing/execution", f"Status {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        results.add_fail("GET /api/marketing/execution", f"Exception: {str(e)}")
        return False

def test_marketing_analytics():
    """Test 9: GET /api/marketing/analytics (regression)"""
    print(f"\n{BLUE}[TEST 9] GET /api/marketing/analytics (regression){RESET}")
    
    try:
        response = session.get(f"{BASE_URL}/marketing/analytics", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            required_fields = ["mocked", "summary"]
            missing_fields = [f for f in required_fields if f not in data]
            
            if missing_fields:
                results.add_fail("GET /api/marketing/analytics", f"Missing fields: {missing_fields}")
                return False
            
            results.add_pass(
                "GET /api/marketing/analytics",
                f"Mocked: {data.get('mocked')} | Published posts: {data.get('summary', {}).get('published_posts', 0)}"
            )
            return True
        else:
            results.add_fail("GET /api/marketing/analytics", f"Status {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        results.add_fail("GET /api/marketing/analytics", f"Exception: {str(e)}")
        return False

def test_marketing_briefing_generate():
    """Test 10: POST /api/marketing/briefing/generate (regression)"""
    print(f"\n{BLUE}[TEST 10] POST /api/marketing/briefing/generate (regression){RESET}")
    
    try:
        payload = {
            "send_email": False,
            "force": False
        }
        
        response = session.post(
            f"{BASE_URL}/marketing/briefing/generate",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            
            required_fields = ["headline", "summary", "wins", "risks", "actions"]
            missing_fields = [f for f in required_fields if f not in data]
            
            if missing_fields:
                results.add_fail("POST /api/marketing/briefing/generate", f"Missing fields: {missing_fields}")
                return False
            
            results.add_pass(
                "POST /api/marketing/briefing/generate",
                f"Briefing generated | Wins: {len(data.get('wins', []))} | Actions: {len(data.get('actions', []))}"
            )
            return True
        else:
            results.add_fail("POST /api/marketing/briefing/generate", f"Status {response.status_code}: {response.text[:300]}")
            return False
    except Exception as e:
        results.add_fail("POST /api/marketing/briefing/generate", f"Exception: {str(e)}")
        return False

def test_growth_agent_status():
    """Test 11: GET /api/marketing/growth-agent/status"""
    print(f"\n{BLUE}[TEST 11] GET /api/marketing/growth-agent/status{RESET}")
    
    try:
        response = session.get(f"{BASE_URL}/marketing/growth-agent/status", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Validate google configuration
            if "google" not in data:
                results.add_fail("GET /api/marketing/growth-agent/status", "Missing 'google' field in response")
                return False
            
            google = data.get("google", {})
            
            # Check gsc_site_url
            gsc_site_url = google.get("gsc_site_url")
            if gsc_site_url != "https://www.obeliscoradical.pt/":
                results.add_fail(
                    "GET /api/marketing/growth-agent/status",
                    f"Expected gsc_site_url='https://www.obeliscoradical.pt/', got '{gsc_site_url}'"
                )
                return False
            
            # Check credentials_ready
            credentials_ready = google.get("credentials_ready")
            if not credentials_ready:
                results.add_fail(
                    "GET /api/marketing/growth-agent/status",
                    f"Expected credentials_ready=true, got {credentials_ready}"
                )
                return False
            
            # Check gsc_configured
            gsc_configured = google.get("gsc_configured")
            if not gsc_configured:
                results.add_fail(
                    "GET /api/marketing/growth-agent/status",
                    f"Expected gsc_configured=true, got {gsc_configured}"
                )
                return False
            
            # Check ga4_configured
            ga4_configured = google.get("ga4_configured")
            if not ga4_configured:
                results.add_fail(
                    "GET /api/marketing/growth-agent/status",
                    f"Expected ga4_configured=true, got {ga4_configured}"
                )
                return False
            
            results.add_pass(
                "GET /api/marketing/growth-agent/status",
                f"GSC URL: {gsc_site_url} | Credentials ready: {credentials_ready} | GSC configured: {gsc_configured} | GA4 configured: {ga4_configured}"
            )
            return True
        else:
            results.add_fail("GET /api/marketing/growth-agent/status", f"Status {response.status_code}: {response.text[:300]}")
            return False
    except Exception as e:
        results.add_fail("GET /api/marketing/growth-agent/status", f"Exception: {str(e)}")
        return False

def test_growth_agent_sync():
    """Test 12: POST /api/marketing/growth-agent/sync"""
    print(f"\n{BLUE}[TEST 12] POST /api/marketing/growth-agent/sync{RESET}")
    
    try:
        response = session.post(f"{BASE_URL}/marketing/growth-agent/sync", json={}, timeout=90)
        
        if response.status_code == 200:
            data = response.json()
            
            # Validate sync_run
            if "sync_run" not in data:
                results.add_fail("POST /api/marketing/growth-agent/sync", "Missing 'sync_run' field in response")
                return False
            
            sync_run = data.get("sync_run", {})
            source_status = sync_run.get("source_status", {})
            
            # Check GSC status
            gsc_status = source_status.get("gsc", {})
            gsc_ok = gsc_status.get("ok")
            gsc_error = gsc_status.get("error")
            
            # Check GA4 status
            ga4_status = source_status.get("ga4", {})
            ga4_ok = ga4_status.get("ok")
            ga4_error = ga4_status.get("error")
            
            # Check blockers
            status = data.get("status", {})
            blockers = status.get("blockers", [])
            
            # Build detailed message
            details = []
            details.append(f"GSC: {'✓ OK' if gsc_ok else '✗ FAILED'}")
            if gsc_error:
                details.append(f"GSC Error: {gsc_error[:100]}")
            if gsc_ok and "rows" in gsc_status:
                details.append(f"GSC Rows: {gsc_status.get('rows')}")
            
            details.append(f"GA4: {'✓ OK' if ga4_ok else '✗ FAILED'}")
            if ga4_error:
                details.append(f"GA4 Error: {ga4_error[:100]}")
            if ga4_ok and "rows" in ga4_status:
                details.append(f"GA4 Rows: {ga4_status.get('rows')}")
            
            if blockers:
                details.append(f"Blockers: {len(blockers)}")
                for blocker in blockers[:2]:
                    details.append(f"  - {blocker[:80]}")
            else:
                details.append("Blockers: None")
            
            # Determine if test passes
            if gsc_ok and ga4_ok:
                results.add_pass(
                    "POST /api/marketing/growth-agent/sync",
                    " | ".join(details)
                )
                return True
            else:
                # If either GSC or GA4 failed, it's a failure
                results.add_fail(
                    "POST /api/marketing/growth-agent/sync",
                    " | ".join(details)
                )
                return False
        else:
            results.add_fail("POST /api/marketing/growth-agent/sync", f"Status {response.status_code}: {response.text[:300]}")
            return False
    except Exception as e:
        results.add_fail("POST /api/marketing/growth-agent/sync", f"Exception: {str(e)}")
        return False

def main():
    print(f"\n{'='*70}")
    print(f"{BLUE}CEO AI - Backend Marketing Module Testing{RESET}")
    print(f"{'='*70}")
    print(f"Base URL: {BASE_URL}")
    print(f"Test User: {TEST_EMAIL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"{'='*70}")
    
    # Run tests in sequence
    if not test_login():
        print(f"\n{RED}Authentication failed. Stopping tests.{RESET}")
        sys.exit(1)
    
    test_social_status()
    test_social_requirements()
    test_social_diagnostics()
    test_campaign_generate()
    test_campaigns_list()
    test_marketing_content()
    test_marketing_execution()
    test_marketing_analytics()
    test_marketing_briefing_generate()
    test_growth_agent_status()
    test_growth_agent_sync()
    
    # Print summary
    success = results.summary()
    
    print(f"\n{'='*70}")
    if success:
        print(f"{GREEN}ALL TESTS PASSED ✓{RESET}")
        sys.exit(0)
    else:
        print(f"{RED}SOME TESTS FAILED ✗{RESET}")
        sys.exit(1)

if __name__ == "__main__":
    main()
