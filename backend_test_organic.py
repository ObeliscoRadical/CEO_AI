#!/usr/bin/env python3
"""
Backend API Testing for CEO AI - Organic Growth Agent (Crescimento Orgânico)
Tests the new autonomous Marketing Director subcategory.
"""
import requests
import json
import sys
import time
from datetime import datetime

# Configuration
BASE_URL = "https://marketing-split-test-1.preview.emergentagent.com/api"
TEST_EMAIL = "adminceoai@gmail.com"
TEST_PASSWORD = "12345"
TEST_DOMAIN = "example.com"

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

def test_login():
    """Test: Login authentication"""
    global session
    print(f"\n{BLUE}[TEST] Login Authentication{RESET}")
    
    try:
        response = session.post(
            f"{BASE_URL}/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            user = data.get("user", data) if isinstance(data, dict) else None
            
            if user and user.get("email") == TEST_EMAIL:
                results.add_pass("Login Authentication", f"User: {user.get('name')} | Role: {user.get('role')}")
                return True
            else:
                results.add_fail("Login Authentication", f"Invalid response structure: {data}")
                return False
        else:
            results.add_fail("Login Authentication", f"Status {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        results.add_fail("Login Authentication", f"Exception: {str(e)}")
        return False

def test_get_organic_agent_initial():
    """Test: GET /api/marketing/organic-agent (initial state)"""
    print(f"\n{BLUE}[TEST] GET /api/marketing/organic-agent (initial){RESET}")
    
    try:
        response = session.get(f"{BASE_URL}/marketing/organic-agent", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Should return agent, actions, reports structure
            if "agent" in data and "actions" in data and "reports" in data:
                agent = data.get("agent")
                if agent is None:
                    results.add_pass(
                        "GET /api/marketing/organic-agent (initial)",
                        "No agent yet (expected for first call)"
                    )
                else:
                    results.add_pass(
                        "GET /api/marketing/organic-agent (initial)",
                        f"Agent exists | Status: {agent.get('status')} | Domain: {agent.get('domain')}"
                    )
                return True
            else:
                results.add_fail("GET /api/marketing/organic-agent (initial)", f"Missing required fields in response: {list(data.keys())}")
                return False
        else:
            results.add_fail("GET /api/marketing/organic-agent (initial)", f"Status {response.status_code}: {response.text[:300]}")
            return False
    except Exception as e:
        results.add_fail("GET /api/marketing/organic-agent (initial)", f"Exception: {str(e)}")
        return False

def test_create_strategy():
    """Test: POST /api/marketing/organic-agent/strategy - Create initial strategy"""
    print(f"\n{BLUE}[TEST] POST /api/marketing/organic-agent/strategy{RESET}")
    
    try:
        payload = {
            "domain": TEST_DOMAIN,
            "objective": "Gerar crescimento orgânico com foco em leads qualificados e conversão."
        }
        
        response = session.post(
            f"{BASE_URL}/marketing/organic-agent/strategy",
            json=payload,
            timeout=180  # Allow time for site scanning and AI processing
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if "agent" not in data:
                results.add_fail("POST /api/marketing/organic-agent/strategy", "Missing 'agent' field in response")
                return False
            
            agent = data["agent"]
            
            # Validate agent.status = awaiting_approval
            if agent.get("status") != "awaiting_approval":
                results.add_fail(
                    "POST /api/marketing/organic-agent/strategy",
                    f"Expected status 'awaiting_approval', got '{agent.get('status')}'"
                )
                return False
            
            # Validate site_analysis exists
            if "site_analysis" not in agent:
                results.add_fail("POST /api/marketing/organic-agent/strategy", "Missing 'site_analysis' in agent")
                return False
            
            site_analysis = agent["site_analysis"]
            required_site_fields = ["domain", "pages_scanned", "website_summary", "positioning", "opportunities", "scanned_at"]
            missing_site_fields = [f for f in required_site_fields if f not in site_analysis]
            if missing_site_fields:
                results.add_fail(
                    "POST /api/marketing/organic-agent/strategy",
                    f"Missing site_analysis fields: {missing_site_fields}"
                )
                return False
            
            # Validate director_alignment exists
            if "director_alignment" not in agent:
                results.add_fail("POST /api/marketing/organic-agent/strategy", "Missing 'director_alignment' in agent")
                return False
            
            alignment = agent["director_alignment"]
            if "financeiro" not in alignment or "comercial" not in alignment:
                results.add_fail(
                    "POST /api/marketing/organic-agent/strategy",
                    f"Missing director alignment keys. Got: {list(alignment.keys())}"
                )
                return False
            
            # Validate strategy.phase_plan exists
            if "strategy" not in agent:
                results.add_fail("POST /api/marketing/organic-agent/strategy", "Missing 'strategy' in agent")
                return False
            
            strategy = agent["strategy"]
            if "phase_plan" not in strategy:
                results.add_fail("POST /api/marketing/organic-agent/strategy", "Missing 'phase_plan' in strategy")
                return False
            
            phase_plan = strategy["phase_plan"]
            if not isinstance(phase_plan, list) or len(phase_plan) < 3:
                results.add_fail(
                    "POST /api/marketing/organic-agent/strategy",
                    f"Expected at least 3 phases in phase_plan, got {len(phase_plan)}"
                )
                return False
            
            # Validate metrics exist
            if "metrics" not in agent:
                results.add_fail("POST /api/marketing/organic-agent/strategy", "Missing 'metrics' in agent")
                return False
            
            metrics = agent["metrics"]
            required_metrics = ["traffic", "leads", "conversion_rate"]
            missing_metrics = [m for m in required_metrics if m not in metrics]
            if missing_metrics:
                results.add_fail(
                    "POST /api/marketing/organic-agent/strategy",
                    f"Missing metrics: {missing_metrics}"
                )
                return False
            
            results.add_pass(
                "POST /api/marketing/organic-agent/strategy",
                f"Strategy created | Status: {agent.get('status')} | Domain: {site_analysis.get('domain')} | "
                f"Pages scanned: {site_analysis.get('pages_scanned')} | Opportunities: {len(site_analysis.get('opportunities', []))} | "
                f"Phase plan: {len(phase_plan)} phases | Metrics: traffic={metrics.get('traffic')}, leads={metrics.get('leads')}, conversion={metrics.get('conversion_rate')}%"
            )
            return True
        else:
            results.add_fail(
                "POST /api/marketing/organic-agent/strategy",
                f"Status {response.status_code}: {response.text[:500]}"
            )
            return False
    except Exception as e:
        results.add_fail("POST /api/marketing/organic-agent/strategy", f"Exception: {str(e)}")
        return False

def test_approve_strategy():
    """Test: POST /api/marketing/organic-agent/approve - Approve strategy"""
    print(f"\n{BLUE}[TEST] POST /api/marketing/organic-agent/approve{RESET}")
    
    try:
        response = session.post(
            f"{BASE_URL}/marketing/organic-agent/approve",
            json={},
            timeout=180  # Allow time for autonomous cycle
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if "agent" not in data:
                results.add_fail("POST /api/marketing/organic-agent/approve", "Missing 'agent' field in response")
                return False
            
            agent = data["agent"]
            
            # Validate agent.status = running
            if agent.get("status") != "running":
                results.add_fail(
                    "POST /api/marketing/organic-agent/approve",
                    f"Expected status 'running', got '{agent.get('status')}'"
                )
                return False
            
            # Validate agent.autonomous_mode = true
            if agent.get("autonomous_mode") != True:
                results.add_fail(
                    "POST /api/marketing/organic-agent/approve",
                    f"Expected autonomous_mode=true, got {agent.get('autonomous_mode')}"
                )
                return False
            
            # Validate agent.strategy_approved = true
            if agent.get("strategy_approved") != True:
                results.add_fail(
                    "POST /api/marketing/organic-agent/approve",
                    f"Expected strategy_approved=true, got {agent.get('strategy_approved')}"
                )
                return False
            
            # Validate actions exist
            if "actions" not in data:
                results.add_fail("POST /api/marketing/organic-agent/approve", "Missing 'actions' in response")
                return False
            
            actions = data["actions"]
            if not isinstance(actions, list):
                results.add_fail("POST /api/marketing/organic-agent/approve", f"Expected actions to be a list, got {type(actions)}")
                return False
            
            # Validate reports exist
            if "reports" not in data:
                results.add_fail("POST /api/marketing/organic-agent/approve", "Missing 'reports' in response")
                return False
            
            reports = data["reports"]
            if "daily" not in reports or "weekly" not in reports or "monthly" not in reports:
                results.add_fail(
                    "POST /api/marketing/organic-agent/approve",
                    f"Missing report periods. Got: {list(reports.keys())}"
                )
                return False
            
            # Validate metrics
            metrics = agent.get("metrics", {})
            if "traffic" not in metrics or "leads" not in metrics or "conversion_rate" not in metrics:
                results.add_fail(
                    "POST /api/marketing/organic-agent/approve",
                    f"Missing metrics. Got: {list(metrics.keys())}"
                )
                return False
            
            results.add_pass(
                "POST /api/marketing/organic-agent/approve",
                f"Strategy approved | Status: {agent.get('status')} | Autonomous: {agent.get('autonomous_mode')} | "
                f"Approved: {agent.get('strategy_approved')} | Actions: {len(actions)} | "
                f"Reports: daily={len(reports.get('daily', []))}, weekly={len(reports.get('weekly', []))}, monthly={len(reports.get('monthly', []))}"
            )
            return True
        else:
            results.add_fail(
                "POST /api/marketing/organic-agent/approve",
                f"Status {response.status_code}: {response.text[:500]}"
            )
            return False
    except Exception as e:
        results.add_fail("POST /api/marketing/organic-agent/approve", f"Exception: {str(e)}")
        return False

def test_pause_agent():
    """Test: POST /api/marketing/organic-agent/pause - Pause agent"""
    print(f"\n{BLUE}[TEST] POST /api/marketing/organic-agent/pause{RESET}")
    
    try:
        response = session.post(
            f"{BASE_URL}/marketing/organic-agent/pause",
            json={},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if "agent" not in data:
                results.add_fail("POST /api/marketing/organic-agent/pause", "Missing 'agent' field in response")
                return False
            
            agent = data["agent"]
            
            # Validate agent.status = paused
            if agent.get("status") != "paused":
                results.add_fail(
                    "POST /api/marketing/organic-agent/pause",
                    f"Expected status 'paused', got '{agent.get('status')}'"
                )
                return False
            
            results.add_pass(
                "POST /api/marketing/organic-agent/pause",
                f"Agent paused successfully | Status: {agent.get('status')}"
            )
            return True
        else:
            results.add_fail(
                "POST /api/marketing/organic-agent/pause",
                f"Status {response.status_code}: {response.text[:300]}"
            )
            return False
    except Exception as e:
        results.add_fail("POST /api/marketing/organic-agent/pause", f"Exception: {str(e)}")
        return False

def test_resume_agent():
    """Test: POST /api/marketing/organic-agent/resume - Resume agent"""
    print(f"\n{BLUE}[TEST] POST /api/marketing/organic-agent/resume{RESET}")
    
    try:
        response = session.post(
            f"{BASE_URL}/marketing/organic-agent/resume",
            json={},
            timeout=180  # Allow time for cycle execution
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if "agent" not in data:
                results.add_fail("POST /api/marketing/organic-agent/resume", "Missing 'agent' field in response")
                return False
            
            agent = data["agent"]
            
            # Validate agent.status = running
            if agent.get("status") != "running":
                results.add_fail(
                    "POST /api/marketing/organic-agent/resume",
                    f"Expected status 'running', got '{agent.get('status')}'"
                )
                return False
            
            # Validate autonomous_mode is still true
            if agent.get("autonomous_mode") != True:
                results.add_fail(
                    "POST /api/marketing/organic-agent/resume",
                    f"Expected autonomous_mode=true, got {agent.get('autonomous_mode')}"
                )
                return False
            
            results.add_pass(
                "POST /api/marketing/organic-agent/resume",
                f"Agent resumed successfully | Status: {agent.get('status')} | Autonomous: {agent.get('autonomous_mode')}"
            )
            return True
        else:
            results.add_fail(
                "POST /api/marketing/organic-agent/resume",
                f"Status {response.status_code}: {response.text[:300]}"
            )
            return False
    except Exception as e:
        results.add_fail("POST /api/marketing/organic-agent/resume", f"Exception: {str(e)}")
        return False

def test_update_objective():
    """Test: POST /api/marketing/organic-agent/objective - Update objective"""
    print(f"\n{BLUE}[TEST] POST /api/marketing/organic-agent/objective{RESET}")
    
    try:
        new_objective = "Priorizar qualidade do lead antes de escalar volume"
        
        response = session.post(
            f"{BASE_URL}/marketing/organic-agent/objective",
            json={"objective": new_objective},
            timeout=180  # Allow time for strategy rebuild
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if "agent" not in data:
                results.add_fail("POST /api/marketing/organic-agent/objective", "Missing 'agent' field in response")
                return False
            
            agent = data["agent"]
            
            # Validate objective was updated
            if agent.get("objective") != new_objective:
                results.add_fail(
                    "POST /api/marketing/organic-agent/objective",
                    f"Expected objective '{new_objective}', got '{agent.get('objective')}'"
                )
                return False
            
            # Validate strategy was updated (should have new last_analysis_at)
            if "last_analysis_at" not in agent:
                results.add_fail("POST /api/marketing/organic-agent/objective", "Missing 'last_analysis_at' after objective update")
                return False
            
            results.add_pass(
                "POST /api/marketing/organic-agent/objective",
                f"Objective updated successfully | New objective: {agent.get('objective')[:60]}..."
            )
            return True
        else:
            results.add_fail(
                "POST /api/marketing/organic-agent/objective",
                f"Status {response.status_code}: {response.text[:300]}"
            )
            return False
    except Exception as e:
        results.add_fail("POST /api/marketing/organic-agent/objective", f"Exception: {str(e)}")
        return False

def test_reanalyze_site():
    """Test: POST /api/marketing/organic-agent/reanalyze - Reanalyze site"""
    print(f"\n{BLUE}[TEST] POST /api/marketing/organic-agent/reanalyze{RESET}")
    
    try:
        # Get current scanned_at timestamp
        current_response = session.get(f"{BASE_URL}/marketing/organic-agent", timeout=30)
        if current_response.status_code != 200:
            results.add_fail("POST /api/marketing/organic-agent/reanalyze", "Failed to get current agent state")
            return False
        
        current_agent = current_response.json().get("agent", {})
        old_scanned_at = current_agent.get("site_analysis", {}).get("scanned_at")
        
        # Wait a moment to ensure timestamp difference
        time.sleep(2)
        
        response = session.post(
            f"{BASE_URL}/marketing/organic-agent/reanalyze",
            json={},
            timeout=180  # Allow time for site rescan
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if "agent" not in data:
                results.add_fail("POST /api/marketing/organic-agent/reanalyze", "Missing 'agent' field in response")
                return False
            
            agent = data["agent"]
            
            # Validate site_analysis.scanned_at was updated
            if "site_analysis" not in agent:
                results.add_fail("POST /api/marketing/organic-agent/reanalyze", "Missing 'site_analysis' in agent")
                return False
            
            new_scanned_at = agent["site_analysis"].get("scanned_at")
            
            if not new_scanned_at:
                results.add_fail("POST /api/marketing/organic-agent/reanalyze", "Missing 'scanned_at' in site_analysis")
                return False
            
            if old_scanned_at and new_scanned_at <= old_scanned_at:
                results.add_fail(
                    "POST /api/marketing/organic-agent/reanalyze",
                    f"scanned_at not updated. Old: {old_scanned_at}, New: {new_scanned_at}"
                )
                return False
            
            results.add_pass(
                "POST /api/marketing/organic-agent/reanalyze",
                f"Site reanalyzed successfully | New scanned_at: {new_scanned_at}"
            )
            return True
        else:
            results.add_fail(
                "POST /api/marketing/organic-agent/reanalyze",
                f"Status {response.status_code}: {response.text[:300]}"
            )
            return False
    except Exception as e:
        results.add_fail("POST /api/marketing/organic-agent/reanalyze", f"Exception: {str(e)}")
        return False

def test_no_errors_or_timeouts():
    """Test: Verify no 500/502 errors or timeouts in previous tests"""
    print(f"\n{BLUE}[TEST] No 500/502 errors or timeouts{RESET}")
    
    # This is validated by checking if any previous tests failed with 500/502
    has_server_errors = False
    for test_name, error in results.failed:
        if "500" in str(error) or "502" in str(error) or "timeout" in str(error).lower():
            has_server_errors = True
            break
    
    if not has_server_errors:
        results.add_pass(
            "No 500/502 errors or timeouts",
            "All endpoints responded without server errors or timeouts"
        )
        return True
    else:
        results.add_fail(
            "No 500/502 errors or timeouts",
            "Some endpoints returned 500/502 errors or timed out"
        )
        return False

def test_autonomous_flow_no_reapproval():
    """Test: Verify autonomous flow doesn't require new approval after first one"""
    print(f"\n{BLUE}[TEST] Autonomous flow - no reapproval needed{RESET}")
    
    try:
        # Get current agent state
        response = session.get(f"{BASE_URL}/marketing/organic-agent", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            agent = data.get("agent", {})
            
            # Verify agent is still running and approved
            if agent.get("status") == "running" and agent.get("strategy_approved") == True:
                results.add_pass(
                    "Autonomous flow - no reapproval needed",
                    f"Agent remains running and approved | Status: {agent.get('status')} | Approved: {agent.get('strategy_approved')}"
                )
                return True
            else:
                results.add_fail(
                    "Autonomous flow - no reapproval needed",
                    f"Agent state unexpected | Status: {agent.get('status')} | Approved: {agent.get('strategy_approved')}"
                )
                return False
        else:
            results.add_fail(
                "Autonomous flow - no reapproval needed",
                f"Failed to get agent state: {response.status_code}"
            )
            return False
    except Exception as e:
        results.add_fail("Autonomous flow - no reapproval needed", f"Exception: {str(e)}")
        return False

def main():
    print(f"\n{'='*70}")
    print(f"{BLUE}CEO AI - Organic Growth Agent Backend Testing{RESET}")
    print(f"{'='*70}")
    print(f"Base URL: {BASE_URL}")
    print(f"Test User: {TEST_EMAIL}")
    print(f"Test Domain: {TEST_DOMAIN}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"{'='*70}")
    
    # Run tests in sequence
    if not test_login():
        print(f"\n{RED}Authentication failed. Stopping tests.{RESET}")
        sys.exit(1)
    
    # Test sequence
    test_get_organic_agent_initial()
    test_create_strategy()
    test_approve_strategy()
    test_pause_agent()
    test_resume_agent()
    test_update_objective()
    test_reanalyze_site()
    test_no_errors_or_timeouts()
    test_autonomous_flow_no_reapproval()
    
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
