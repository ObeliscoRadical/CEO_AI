"""
Backend API Testing for Social/Meta Module
Tests the new insights fields and metrics refresh endpoint
"""
import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "https://marketing-split-test-1.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"

# Test credentials from test_credentials.md
ADMIN_EMAIL = "adminceoai@gmail.com"
ADMIN_PASSWORD = "12345"

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

class TestResults:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []
    
    def add_pass(self, test_name, detail=""):
        self.passed.append((test_name, detail))
        print(f"{GREEN}✓{RESET} {test_name}")
        if detail:
            print(f"  {detail}")
    
    def add_fail(self, test_name, detail=""):
        self.failed.append((test_name, detail))
        print(f"{RED}✗{RESET} {test_name}")
        if detail:
            print(f"  {RED}{detail}{RESET}")
    
    def add_warning(self, test_name, detail=""):
        self.warnings.append((test_name, detail))
        print(f"{YELLOW}⚠{RESET} {test_name}")
        if detail:
            print(f"  {YELLOW}{detail}{RESET}")
    
    def summary(self):
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}TEST SUMMARY{RESET}")
        print(f"{BLUE}{'='*60}{RESET}")
        print(f"{GREEN}Passed: {len(self.passed)}{RESET}")
        print(f"{RED}Failed: {len(self.failed)}{RESET}")
        print(f"{YELLOW}Warnings: {len(self.warnings)}{RESET}")
        
        if self.failed:
            print(f"\n{RED}FAILED TESTS:{RESET}")
            for test_name, detail in self.failed:
                print(f"  - {test_name}")
                if detail:
                    print(f"    {detail}")
        
        return len(self.failed) == 0

def login(session, results):
    """Login and get authentication cookie"""
    print(f"\n{BLUE}=== AUTHENTICATION ==={RESET}")
    
    try:
        response = session.post(
            f"{API_BASE}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("email") == ADMIN_EMAIL:
                results.add_pass("Authentication", f"Logged in as {data.get('name', 'Admin')}")
                return True
            else:
                results.add_fail("Authentication", "Login response missing expected user data")
                return False
        else:
            results.add_fail("Authentication", f"Login failed with status {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        results.add_fail("Authentication", f"Login error: {str(e)}")
        return False

def test_social_status(session, results):
    """Test GET /api/social/status - verify new insights fields"""
    print(f"\n{BLUE}=== GET /api/social/status ==={RESET}")
    
    try:
        response = session.get(f"{API_BASE}/social/status", timeout=30)
        
        if response.status_code != 200:
            results.add_fail("GET /api/social/status", f"Status {response.status_code}: {response.text[:200]}")
            return None
        
        results.add_pass("GET /api/social/status", "Endpoint responded successfully")
        
        data = response.json()
        
        # Check for new fields
        required_new_fields = [
            "insights_status",
            "insights_permissions_ready",
            "insights_last_checked_at",
            "report_source",
            "metrics_mocked",
            "live_metrics_ready"
        ]
        
        missing_fields = []
        present_fields = {}
        
        for field in required_new_fields:
            if field in data:
                present_fields[field] = data[field]
            else:
                missing_fields.append(field)
        
        if missing_fields:
            results.add_fail(
                "New insights fields in /social/status",
                f"Missing fields: {', '.join(missing_fields)}"
            )
        else:
            results.add_pass(
                "New insights fields in /social/status",
                f"All 6 new fields present"
            )
        
        # Verify field values are coherent
        print(f"\n  {BLUE}Field values:{RESET}")
        for field, value in present_fields.items():
            print(f"    {field}: {value}")
        
        # Check coherence
        if present_fields.get("metrics_mocked") is not None:
            if present_fields.get("live_metrics_ready") == True and present_fields.get("metrics_mocked") == True:
                results.add_warning(
                    "Field coherence",
                    "live_metrics_ready=True but metrics_mocked=True (contradictory)"
                )
            else:
                results.add_pass("Field coherence", "metrics_mocked and live_metrics_ready are coherent")
        
        # Check report_source
        if present_fields.get("report_source"):
            if present_fields["report_source"] in ["real", "mock"]:
                results.add_pass("report_source field", f"Valid value: {present_fields['report_source']}")
            else:
                results.add_warning("report_source field", f"Unexpected value: {present_fields['report_source']}")
        
        # Check insights_status
        if present_fields.get("insights_status"):
            valid_statuses = ["ready", "no_data", "permission_denied", "expired", "unavailable", "unverified", "permission_ready"]
            if present_fields["insights_status"] in valid_statuses:
                results.add_pass("insights_status field", f"Valid value: {present_fields['insights_status']}")
            else:
                results.add_warning("insights_status field", f"Unexpected value: {present_fields['insights_status']}")
        
        return data
        
    except Exception as e:
        results.add_fail("GET /api/social/status", f"Error: {str(e)}")
        return None

def test_social_diagnostics(session, results):
    """Test POST /api/social/diagnostics - verify new insights fields"""
    print(f"\n{BLUE}=== POST /api/social/diagnostics ==={RESET}")
    
    try:
        response = session.post(f"{API_BASE}/social/diagnostics", timeout=30)
        
        if response.status_code != 200:
            results.add_fail("POST /api/social/diagnostics", f"Status {response.status_code}: {response.text[:200]}")
            return None
        
        results.add_pass("POST /api/social/diagnostics", "Endpoint responded successfully")
        
        data = response.json()
        
        # Check for new fields (same as status endpoint)
        required_new_fields = [
            "insights_status",
            "insights_permissions_ready",
            "insights_last_checked_at",
            "report_source",
            "metrics_mocked",
            "live_metrics_ready"
        ]
        
        missing_fields = []
        present_fields = {}
        
        for field in required_new_fields:
            if field in data:
                present_fields[field] = data[field]
            else:
                missing_fields.append(field)
        
        if missing_fields:
            results.add_fail(
                "New insights fields in /social/diagnostics",
                f"Missing fields: {', '.join(missing_fields)}"
            )
        else:
            results.add_pass(
                "New insights fields in /social/diagnostics",
                f"All 6 new fields present"
            )
        
        # Verify field values are coherent
        print(f"\n  {BLUE}Field values:{RESET}")
        for field, value in present_fields.items():
            print(f"    {field}: {value}")
        
        # Check if diagnostics updated insights_last_checked_at
        if present_fields.get("insights_last_checked_at"):
            try:
                checked_time = datetime.fromisoformat(present_fields["insights_last_checked_at"].replace("Z", "+00:00"))
                now = datetime.now(checked_time.tzinfo)
                diff = (now - checked_time).total_seconds()
                if diff < 300:  # Within last 5 minutes
                    results.add_pass(
                        "insights_last_checked_at updated",
                        f"Timestamp is recent (within last 5 minutes)"
                    )
                else:
                    results.add_warning(
                        "insights_last_checked_at",
                        f"Timestamp is {int(diff/60)} minutes old"
                    )
            except Exception as e:
                results.add_warning("insights_last_checked_at", f"Could not parse timestamp: {e}")
        
        # Check checks array for insights-related checks
        checks = data.get("checks", [])
        insights_checks = [c for c in checks if "insight" in c.get("id", "").lower() or "insight" in c.get("label", "").lower()]
        
        if insights_checks:
            results.add_pass(
                "Insights diagnostic checks",
                f"Found {len(insights_checks)} insights-related checks"
            )
            for check in insights_checks:
                print(f"    - {check.get('label')}: {'OK' if check.get('ok') else 'NOT OK'}")
                if check.get('detail'):
                    print(f"      {check.get('detail')}")
        else:
            results.add_warning("Insights diagnostic checks", "No insights-related checks found")
        
        return data
        
    except Exception as e:
        results.add_fail("POST /api/social/diagnostics", f"Error: {str(e)}")
        return None

def test_social_metrics_refresh(session, results):
    """Test POST /api/social/metrics/refresh - verify reason field is clear"""
    print(f"\n{BLUE}=== POST /api/social/metrics/refresh ==={RESET}")
    
    try:
        response = session.post(f"{API_BASE}/social/metrics/refresh", timeout=30)
        
        if response.status_code != 200:
            results.add_fail("POST /api/social/metrics/refresh", f"Status {response.status_code}: {response.text[:200]}")
            return None
        
        results.add_pass("POST /api/social/metrics/refresh", "Endpoint responded successfully")
        
        data = response.json()
        
        # Check required fields
        required_fields = ["ready", "refreshed", "reason"]
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            results.add_fail(
                "Required fields in /social/metrics/refresh",
                f"Missing fields: {', '.join(missing_fields)}"
            )
        else:
            results.add_pass(
                "Required fields in /social/metrics/refresh",
                "All required fields present (ready, refreshed, reason)"
            )
        
        print(f"\n  {BLUE}Response:{RESET}")
        print(f"    ready: {data.get('ready')}")
        print(f"    refreshed: {data.get('refreshed')}")
        print(f"    reason: {data.get('reason')}")
        
        # Check if ready=false, reason should be present and clear
        if data.get("ready") == False:
            reason = data.get("reason")
            if reason and isinstance(reason, str) and len(reason) > 10:
                results.add_pass(
                    "Reason field when not ready",
                    f"Clear reason provided: '{reason[:100]}...'" if len(reason) > 100 else f"Clear reason provided: '{reason}'"
                )
            elif reason is None:
                results.add_fail(
                    "Reason field when not ready",
                    "ready=False but reason is None (should explain why)"
                )
            else:
                results.add_warning(
                    "Reason field when not ready",
                    f"Reason is too short or unclear: '{reason}'"
                )
        else:
            # ready=true
            if data.get("refreshed", 0) > 0:
                results.add_pass(
                    "Metrics refresh successful",
                    f"Refreshed {data.get('refreshed')} posts"
                )
            else:
                results.add_warning(
                    "Metrics refresh",
                    "ready=True but refreshed=0 (no posts to refresh?)"
                )
        
        return data
        
    except Exception as e:
        results.add_fail("POST /api/social/metrics/refresh", f"Error: {str(e)}")
        return None

def test_marketing_analytics(session, results):
    """Test GET /api/marketing/analytics - regression test"""
    print(f"\n{BLUE}=== GET /api/marketing/analytics ==={RESET}")
    
    try:
        response = session.get(f"{API_BASE}/marketing/analytics", timeout=30)
        
        if response.status_code != 200:
            results.add_fail("GET /api/marketing/analytics", f"Status {response.status_code}: {response.text[:200]}")
            return None
        
        results.add_pass("GET /api/marketing/analytics", "Endpoint responded successfully")
        
        data = response.json()
        
        # Check required fields
        required_fields = ["mocked", "summary"]
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            results.add_fail(
                "Required fields in /marketing/analytics",
                f"Missing fields: {', '.join(missing_fields)}"
            )
        else:
            results.add_pass(
                "Required fields in /marketing/analytics",
                "All required fields present"
            )
        
        # Check summary structure
        summary = data.get("summary", {})
        summary_fields = ["published_posts", "reach", "impressions", "clicks", "avg_engagement_rate"]
        missing_summary_fields = [f for f in summary_fields if f not in summary]
        
        if missing_summary_fields:
            results.add_warning(
                "Summary fields in /marketing/analytics",
                f"Missing summary fields: {', '.join(missing_summary_fields)}"
            )
        else:
            results.add_pass(
                "Summary fields in /marketing/analytics",
                "All summary fields present"
            )
        
        print(f"\n  {BLUE}Analytics summary:{RESET}")
        print(f"    mocked: {data.get('mocked')}")
        print(f"    published_posts: {summary.get('published_posts', 0)}")
        print(f"    reach: {summary.get('reach', 0)}")
        print(f"    clicks: {summary.get('clicks', 0)}")
        
        return data
        
    except Exception as e:
        results.add_fail("GET /api/marketing/analytics", f"Error: {str(e)}")
        return None

def main():
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Backend API Testing - Social/Meta Module{RESET}")
    print(f"{BLUE}Testing new insights fields and metrics refresh{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"Base URL: {BASE_URL}")
    print(f"Testing with: {ADMIN_EMAIL}")
    
    results = TestResults()
    session = requests.Session()
    
    # Step 1: Login
    if not login(session, results):
        print(f"\n{RED}Authentication failed. Cannot proceed with tests.{RESET}")
        return False
    
    # Step 2: Test GET /api/social/status
    status_data = test_social_status(session, results)
    
    # Step 3: Test POST /api/social/diagnostics
    diagnostics_data = test_social_diagnostics(session, results)
    
    # Step 4: Test POST /api/social/metrics/refresh
    refresh_data = test_social_metrics_refresh(session, results)
    
    # Step 5: Test GET /api/marketing/analytics (regression)
    analytics_data = test_marketing_analytics(session, results)
    
    # Summary
    success = results.summary()
    
    if success:
        print(f"\n{GREEN}All tests passed!{RESET}")
    else:
        print(f"\n{RED}Some tests failed. See details above.{RESET}")
    
    return success

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
