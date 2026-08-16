#!/usr/bin/env python3
"""
Backend Smoke Test - Marketing Module
Tests all main endpoints used by the Marketing page after visual reorganization
"""
import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "https://marketing-split-test-1.preview.emergentagent.com"
API_URL = f"{BASE_URL}/api"
LOGIN_EMAIL = "adminceoai@gmail.com"
LOGIN_PASSWORD = "12345"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.END}")

def print_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.END}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.END}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.END}")

class MarketingBackendTester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.results = {
            "passed": [],
            "failed": [],
            "warnings": []
        }
    
    def login(self):
        """Authenticate and get session token"""
        print_info(f"Logging in as {LOGIN_EMAIL}...")
        try:
            response = self.session.post(
                f"{API_URL}/auth/login",
                json={"email": LOGIN_EMAIL, "password": LOGIN_PASSWORD},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if "email" in data and data["email"] == LOGIN_EMAIL:
                    print_success(f"Login successful - User: {data.get('name', 'N/A')}, Role: {data.get('role', 'N/A')}")
                    return True
                else:
                    print_error(f"Login response missing expected fields: {data}")
                    return False
            else:
                print_error(f"Login failed with status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            print_error(f"Login exception: {str(e)}")
            return False
    
    def test_get_endpoint(self, endpoint, name, required_fields=None):
        """Test a GET endpoint"""
        print_info(f"Testing GET {endpoint}...")
        try:
            response = self.session.get(f"{API_URL}{endpoint}", timeout=30)
            
            if response.status_code == 500:
                self.results["failed"].append(f"{name}: 500 Internal Server Error")
                print_error(f"{name}: 500 Internal Server Error")
                print_error(f"Response: {response.text[:500]}")
                return False
            
            if response.status_code != 200:
                self.results["warnings"].append(f"{name}: Status {response.status_code}")
                print_warning(f"{name}: Status {response.status_code} (not 500, but not 200)")
                return False
            
            data = response.json()
            
            # Check required fields if specified
            if required_fields:
                missing_fields = [f for f in required_fields if f not in data]
                if missing_fields:
                    self.results["warnings"].append(f"{name}: Missing fields {missing_fields}")
                    print_warning(f"{name}: Missing required fields: {missing_fields}")
                else:
                    self.results["passed"].append(f"{name}: OK (all required fields present)")
                    print_success(f"{name}: OK - Status 200, all required fields present")
            else:
                self.results["passed"].append(f"{name}: OK")
                print_success(f"{name}: OK - Status 200")
            
            return True
            
        except requests.exceptions.Timeout:
            self.results["failed"].append(f"{name}: Timeout")
            print_error(f"{name}: Request timeout")
            return False
        except Exception as e:
            self.results["failed"].append(f"{name}: Exception - {str(e)}")
            print_error(f"{name}: Exception - {str(e)}")
            return False
    
    def test_post_endpoint(self, endpoint, name, payload, required_fields=None):
        """Test a POST endpoint"""
        print_info(f"Testing POST {endpoint}...")
        try:
            response = self.session.post(
                f"{API_URL}{endpoint}",
                json=payload,
                timeout=60  # Longer timeout for POST operations
            )
            
            if response.status_code == 500:
                self.results["failed"].append(f"{name}: 500 Internal Server Error")
                print_error(f"{name}: 500 Internal Server Error")
                print_error(f"Response: {response.text[:500]}")
                return False
            
            if response.status_code != 200:
                self.results["warnings"].append(f"{name}: Status {response.status_code}")
                print_warning(f"{name}: Status {response.status_code} (not 500, but not 200)")
                return False
            
            data = response.json()
            
            # Check required fields if specified
            if required_fields:
                missing_fields = [f for f in required_fields if f not in data]
                if missing_fields:
                    self.results["warnings"].append(f"{name}: Missing fields {missing_fields}")
                    print_warning(f"{name}: Missing required fields: {missing_fields}")
                else:
                    self.results["passed"].append(f"{name}: OK (all required fields present)")
                    print_success(f"{name}: OK - Status 200, all required fields present")
            else:
                self.results["passed"].append(f"{name}: OK")
                print_success(f"{name}: OK - Status 200")
            
            return True
            
        except requests.exceptions.Timeout:
            self.results["failed"].append(f"{name}: Timeout")
            print_error(f"{name}: Request timeout")
            return False
        except Exception as e:
            self.results["failed"].append(f"{name}: Exception - {str(e)}")
            print_error(f"{name}: Exception - {str(e)}")
            return False
    
    def run_smoke_tests(self):
        """Run all smoke tests for Marketing module endpoints"""
        print("\n" + "="*80)
        print("MARKETING MODULE BACKEND SMOKE TEST")
        print(f"Testing against: {BASE_URL}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print("="*80 + "\n")
        
        # Step 1: Login
        if not self.login():
            print_error("Cannot proceed without authentication")
            return False
        
        print("\n" + "-"*80)
        print("TESTING ENDPOINTS")
        print("-"*80 + "\n")
        
        # Test all endpoints from the review request
        self.test_get_endpoint(
            "/marketing/content",
            "GET /api/marketing/content",
            required_fields=["content"]
        )
        
        self.test_get_endpoint(
            "/social/status",
            "GET /api/social/status",
            required_fields=["configured", "connection_state"]
        )
        
        self.test_get_endpoint(
            "/social/media-agent",
            "GET /api/social/media-agent"
        )
        
        self.test_get_endpoint(
            "/marketing/organic-agent",
            "GET /api/marketing/organic-agent",
            required_fields=["agent", "actions", "reports"]
        )
        
        self.test_get_endpoint(
            "/marketing/site-publishing/status",
            "GET /api/marketing/site-publishing/status"
        )
        
        self.test_get_endpoint(
            "/marketing/growth-agent/status",
            "GET /api/marketing/growth-agent/status"
        )
        
        self.test_get_endpoint(
            "/marketing/campaigns",
            "GET /api/marketing/campaigns"
        )
        
        self.test_get_endpoint(
            "/marketing/execution",
            "GET /api/marketing/execution",
            required_fields=["summary", "queued", "history"]
        )
        
        self.test_get_endpoint(
            "/marketing/analytics",
            "GET /api/marketing/analytics",
            required_fields=["mocked", "summary"]
        )
        
        self.test_post_endpoint(
            "/marketing/briefing/generate",
            "POST /api/marketing/briefing/generate",
            payload={"force": False, "send_email": False},
            required_fields=["headline", "summary"]
        )
        
        # Print summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80 + "\n")
        
        print(f"{Colors.GREEN}PASSED: {len(self.results['passed'])}{Colors.END}")
        for item in self.results['passed']:
            print(f"  ✅ {item}")
        
        if self.results['warnings']:
            print(f"\n{Colors.YELLOW}WARNINGS: {len(self.results['warnings'])}{Colors.END}")
            for item in self.results['warnings']:
                print(f"  ⚠️  {item}")
        
        if self.results['failed']:
            print(f"\n{Colors.RED}FAILED: {len(self.results['failed'])}{Colors.END}")
            for item in self.results['failed']:
                print(f"  ❌ {item}")
        
        print("\n" + "="*80)
        
        # Determine overall result
        has_500_errors = any("500" in item for item in self.results['failed'])
        has_timeouts = any("Timeout" in item for item in self.results['failed'])
        
        if has_500_errors:
            print_error("SMOKE TEST FAILED: 500 errors detected")
            return False
        elif has_timeouts:
            print_error("SMOKE TEST FAILED: Timeouts detected")
            return False
        elif self.results['failed']:
            print_error("SMOKE TEST FAILED: Critical errors detected")
            return False
        elif self.results['warnings']:
            print_warning("SMOKE TEST PASSED WITH WARNINGS: Some endpoints returned non-200 status")
            return True
        else:
            print_success("SMOKE TEST PASSED: All endpoints stable, no 500 errors")
            return True

if __name__ == "__main__":
    tester = MarketingBackendTester()
    success = tester.run_smoke_tests()
    exit(0 if success else 1)
