"""Backend test for Homepage Manager and SEO endpoints - Portuguese Review Request Validation."""
import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "https://marketing-split-test-1.preview.emergentagent.com/api"
PUBLIC_BASE_URL = "https://marketing-split-test-1.preview.emergentagent.com"
ADMIN_EMAIL = "adminceoai@gmail.com"
ADMIN_PASSWORD = "12345"

def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def print_result(test_name, passed, details=""):
    """Print test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {test_name}")
    if details:
        print(f"    {details}")

def login():
    """Login and return session with auth cookie."""
    print_section("AUTHENTICATION")
    session = requests.Session()
    
    response = session.post(
        f"{BASE_URL}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    
    if response.status_code == 200:
        user_data = response.json()
        print_result("Login", True, f"Logged in as: {user_data.get('email')} ({user_data.get('name')})")
        return session
    else:
        print_result("Login", False, f"Status: {response.status_code}, Response: {response.text[:200]}")
        return None

def test_1_site_publishing_status(session):
    """
    TEST 1: GET /api/marketing/site-publishing/status
    Should return: homepage.live, homepage.proposal, managed_slots, updated_at, 
                   last_proposal_at, last_applied_at
    """
    print_section("TEST 1: GET /api/marketing/site-publishing/status")
    
    try:
        response = session.get(f"{BASE_URL}/marketing/site-publishing/status")
        
        # Check status code
        if response.status_code != 200:
            print_result("Status Code", False, f"Expected 200, got {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
        
        print_result("Status Code", True, "200 OK")
        
        # Parse JSON
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            print_result("JSON Parse", False, f"Invalid JSON: {e}")
            return False
        
        print_result("JSON Parse", True, "Valid JSON response")
        
        # Validate required fields from review request
        print("\n--- Required Fields Validation (Portuguese Review Request) ---")
        
        # Check for homepage object
        homepage_exists = "homepage" in data
        print_result("Field 'homepage' exists", homepage_exists)
        if not homepage_exists:
            return False
        
        homepage = data.get("homepage", {})
        
        # Check homepage.live
        live_exists = "live" in homepage
        print_result("homepage.live exists", live_exists, 
                    f"Value: {json.dumps(homepage.get('live', 'N/A'), ensure_ascii=False)[:100]}...")
        
        # Check homepage.proposal
        proposal_exists = "proposal" in homepage
        print_result("homepage.proposal exists", proposal_exists,
                    f"Value: {json.dumps(homepage.get('proposal', 'N/A'), ensure_ascii=False)[:100]}...")
        
        # Check managed_slots (inside homepage object)
        managed_slots_exists = "managed_slots" in homepage
        managed_slots = homepage.get("managed_slots", [])
        print_result("homepage.managed_slots exists", managed_slots_exists,
                    f"Count: {len(managed_slots) if isinstance(managed_slots, list) else 'N/A'}")
        
        # Check updated_at (inside homepage object)
        updated_at_exists = "updated_at" in homepage
        print_result("homepage.updated_at exists", updated_at_exists,
                    f"Value: {homepage.get('updated_at', 'N/A')}")
        
        # Check last_proposal_at (inside homepage object)
        last_proposal_at_exists = "last_proposal_at" in homepage
        print_result("homepage.last_proposal_at exists", last_proposal_at_exists,
                    f"Value: {homepage.get('last_proposal_at', 'N/A')}")
        
        # Check last_applied_at (inside homepage object)
        last_applied_at_exists = "last_applied_at" in homepage
        print_result("homepage.last_applied_at exists", last_applied_at_exists,
                    f"Value: {homepage.get('last_applied_at', 'N/A')}")
        
        # All required fields must be present
        all_fields_present = (
            homepage_exists and live_exists and proposal_exists and 
            managed_slots_exists and updated_at_exists and 
            last_proposal_at_exists and last_applied_at_exists
        )
        
        if not all_fields_present:
            print("\n❌ CRITICAL: Not all required fields present")
            return False
        
        print("\n✅ TEST 1 PASSED: All required fields present")
        return True
        
    except requests.exceptions.RequestException as e:
        print_result("HTTP Request", False, f"Request failed: {e}")
        return False
    except Exception as e:
        print_result("Test Execution", False, f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_2_homepage_proposal(session):
    """
    TEST 2: POST /api/marketing/site-publishing/homepage/proposal {use_ai:false}
    Should return: 200
    """
    print_section("TEST 2: POST /api/marketing/site-publishing/homepage/proposal")
    
    try:
        response = session.post(
            f"{BASE_URL}/marketing/site-publishing/homepage/proposal",
            json={"use_ai": False}
        )
        
        # Check status code
        if response.status_code != 200:
            print_result("Status Code", False, f"Expected 200, got {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
        
        print_result("Status Code", True, "200 OK")
        
        # Parse JSON
        try:
            data = response.json()
            print_result("JSON Parse", True, f"Valid JSON response")
            
            # Print sample of response
            print(f"\nResponse preview: {json.dumps(data, ensure_ascii=False)[:200]}...")
            
        except json.JSONDecodeError as e:
            print_result("JSON Parse", False, f"Invalid JSON: {e}")
            return False
        
        print("\n✅ TEST 2 PASSED: Proposal endpoint returns 200")
        return True
        
    except requests.exceptions.RequestException as e:
        print_result("HTTP Request", False, f"Request failed: {e}")
        return False
    except Exception as e:
        print_result("Test Execution", False, f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_3_homepage_apply(session):
    """
    TEST 3: POST /api/marketing/site-publishing/homepage/apply {}
    Should return: 200 when gateway is authorized
    """
    print_section("TEST 3: POST /api/marketing/site-publishing/homepage/apply")
    
    try:
        response = session.post(
            f"{BASE_URL}/marketing/site-publishing/homepage/apply",
            json={}
        )
        
        # Check status code
        if response.status_code != 200:
            print_result("Status Code", False, f"Expected 200, got {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
            # Check if it's an authorization issue
            if response.status_code == 403 or response.status_code == 401:
                print("\n⚠️  NOTE: Gateway may not be authorized. This is expected if authorization is not set up.")
                print("    The review request states this should return 200 'when gateway is authorized'.")
                return False
            
            return False
        
        print_result("Status Code", True, "200 OK - Gateway is authorized")
        
        # Parse JSON
        try:
            data = response.json()
            print_result("JSON Parse", True, f"Valid JSON response")
            
            # Print sample of response
            print(f"\nResponse preview: {json.dumps(data, ensure_ascii=False)[:200]}...")
            
        except json.JSONDecodeError as e:
            print_result("JSON Parse", False, f"Invalid JSON: {e}")
            return False
        
        print("\n✅ TEST 3 PASSED: Apply endpoint returns 200 (gateway authorized)")
        return True
        
    except requests.exceptions.RequestException as e:
        print_result("HTTP Request", False, f"Request failed: {e}")
        return False
    except Exception as e:
        print_result("Test Execution", False, f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_4_public_sitemap(session):
    """
    TEST 4: GET /api/public/sitemap.xml
    Should return: 200 and contain <lastmod>
    """
    print_section("TEST 4: GET /api/public/sitemap.xml")
    
    try:
        # Note: sitemap is public, but we'll use session for consistency
        response = session.get(f"{BASE_URL}/public/sitemap.xml")
        
        # Check status code
        if response.status_code != 200:
            print_result("Status Code", False, f"Expected 200, got {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
        
        print_result("Status Code", True, "200 OK")
        
        # Check content type
        content_type = response.headers.get('Content-Type', '')
        is_xml = 'xml' in content_type.lower() or response.text.strip().startswith('<?xml')
        print_result("Content Type", is_xml, f"Content-Type: {content_type}")
        
        # Check for <lastmod> tag
        sitemap_content = response.text
        has_lastmod = '<lastmod>' in sitemap_content
        print_result("Contains <lastmod>", has_lastmod)
        
        if not has_lastmod:
            print("\n❌ CRITICAL: Sitemap does not contain <lastmod> tag")
            print(f"Sitemap preview: {sitemap_content[:500]}...")
            return False
        
        # Count lastmod occurrences
        lastmod_count = sitemap_content.count('<lastmod>')
        print(f"\n    Found {lastmod_count} <lastmod> tag(s) in sitemap")
        
        # Show sample lastmod value
        import re
        lastmod_match = re.search(r'<lastmod>([^<]+)</lastmod>', sitemap_content)
        if lastmod_match:
            print(f"    Sample <lastmod> value: {lastmod_match.group(1)}")
        
        print("\n✅ TEST 4 PASSED: Sitemap returns 200 and contains <lastmod>")
        return True
        
    except requests.exceptions.RequestException as e:
        print_result("HTTP Request", False, f"Request failed: {e}")
        return False
    except Exception as e:
        print_result("Test Execution", False, f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_5_public_homepage(session):
    """
    TEST 5: Public homepage /login
    Should return: 200
    """
    print_section("TEST 5: GET /login (Public Homepage)")
    
    try:
        # Test public homepage - use a fresh session without auth
        public_session = requests.Session()
        response = public_session.get(f"{PUBLIC_BASE_URL}/login")
        
        # Check status code
        if response.status_code != 200:
            print_result("Status Code", False, f"Expected 200, got {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
        
        print_result("Status Code", True, "200 OK")
        
        # Check content type
        content_type = response.headers.get('Content-Type', '')
        is_html = 'html' in content_type.lower()
        print_result("Content Type", is_html, f"Content-Type: {content_type}")
        
        # Check for basic HTML structure
        html_content = response.text
        has_html_tag = '<html' in html_content.lower()
        has_body_tag = '<body' in html_content.lower()
        
        print_result("Contains <html>", has_html_tag)
        print_result("Contains <body>", has_body_tag)
        
        # Check content length
        content_length = len(html_content)
        has_content = content_length > 1000  # Reasonable minimum for a real page
        print_result("Has substantial content", has_content, f"Length: {content_length} chars")
        
        if not (has_html_tag and has_body_tag and has_content):
            print("\n⚠️  WARNING: Homepage may not be rendering correctly")
            print(f"Preview: {html_content[:500]}...")
            return False
        
        print("\n✅ TEST 5 PASSED: Public homepage /login returns 200")
        return True
        
    except requests.exceptions.RequestException as e:
        print_result("HTTP Request", False, f"Request failed: {e}")
        return False
    except Exception as e:
        print_result("Test Execution", False, f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test execution."""
    print("\n" + "="*80)
    print("  HOMEPAGE MANAGER & SEO BACKEND TEST")
    print("  Portuguese Review Request Validation")
    print("  Preview: https://marketing-split-test-1.preview.emergentagent.com")
    print("="*80)
    
    # Login
    session = login()
    if not session:
        print("\n❌ CRITICAL: Authentication failed. Cannot proceed with tests.")
        return False
    
    # Run all tests
    results = {}
    
    results['test_1'] = test_1_site_publishing_status(session)
    results['test_2'] = test_2_homepage_proposal(session)
    results['test_3'] = test_3_homepage_apply(session)
    results['test_4'] = test_4_public_sitemap(session)
    results['test_5'] = test_5_public_homepage(session)
    
    # Final summary
    print("\n" + "="*80)
    print("  FINAL SUMMARY")
    print("="*80)
    
    print("\nTest Results:")
    print(f"  1. GET /api/marketing/site-publishing/status: {'✅ PASS' if results['test_1'] else '❌ FAIL'}")
    print(f"  2. POST /api/marketing/site-publishing/homepage/proposal: {'✅ PASS' if results['test_2'] else '❌ FAIL'}")
    print(f"  3. POST /api/marketing/site-publishing/homepage/apply: {'✅ PASS' if results['test_3'] else '❌ FAIL'}")
    print(f"  4. GET /api/public/sitemap.xml: {'✅ PASS' if results['test_4'] else '❌ FAIL'}")
    print(f"  5. GET /login (public homepage): {'✅ PASS' if results['test_5'] else '❌ FAIL'}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*80)
    if all_passed:
        print("  🎉 ALL TESTS PASSED")
        print("  Homepage gerida e reforço SEO não introduziram regressões")
    else:
        print("  ❌ SOME TESTS FAILED")
        print("  See details above for specific failures")
    print("="*80 + "\n")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
