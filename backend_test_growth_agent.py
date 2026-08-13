#!/usr/bin/env python3
"""
Test Growth Agent Google Integration
Tests the real state of Google integration (GA4 + GSC) after recent configuration.
"""
import requests
import json
import sys

# Configuration
BACKEND_URL = "https://agent-marketing-pt.preview.emergentagent.com/api"
ADMIN_EMAIL = "adminceoai@gmail.com"
ADMIN_PASSWORD = "12345"

# Expected configuration
EXPECTED_GA4_MEASUREMENT_ID = "G-V24WWQE39G"
EXPECTED_GSC_SITE_URL = "https://obeliscoradical.pt/"

def print_section(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def print_result(test_name, passed, details=""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {test_name}")
    if details:
        print(f"    {details}")

def login():
    """Login with admin credentials and return session cookies"""
    print_section("1. AUTHENTICATION")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print_result("Login successful", True, f"User: {data.get('name')} ({data.get('email')})")
            return response.cookies
        else:
            print_result("Login failed", False, f"Status: {response.status_code}, Response: {response.text}")
            return None
    except Exception as e:
        print_result("Login error", False, str(e))
        return None

def test_growth_agent_sync(cookies):
    """Test POST /api/marketing/growth-agent/sync"""
    print_section("2. GROWTH AGENT SYNC - Google Integration Test")
    
    if not cookies:
        print_result("Skipping sync test", False, "No valid session cookies")
        return None
    
    try:
        print("Calling POST /api/marketing/growth-agent/sync...")
        print("(This may take 30-60 seconds as it fetches data from Google APIs)\n")
        
        response = requests.post(
            f"{BACKEND_URL}/marketing/growth-agent/sync",
            cookies=cookies,
            timeout=120
        )
        
        if response.status_code != 200:
            print_result("Sync endpoint failed", False, f"Status: {response.status_code}, Response: {response.text[:500]}")
            return None
        
        data = response.json()
        print_result("Sync endpoint responded", True, "Status 200 OK")
        
        # Pretty print the response
        print("\n--- Full Response ---")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        print("--- End Response ---\n")
        
        return data
    
    except requests.exceptions.Timeout:
        print_result("Sync timeout", False, "Request took longer than 120 seconds")
        return None
    except Exception as e:
        print_result("Sync error", False, str(e))
        return None

def validate_sync_response(data):
    """Validate the sync response according to user requirements"""
    print_section("3. VALIDATION - Required Fields")
    
    if not data:
        print_result("Cannot validate", False, "No data received from sync endpoint")
        return False
    
    all_passed = True
    
    # Extract sync_run
    sync_run = data.get("sync_run", {})
    source_status = sync_run.get("source_status", {})
    
    # Check 1: ga4_measurement_installed
    ga4_status = source_status.get("ga4", {})
    ga4_measurement_installed = ga4_status.get("measurement_installed", False)
    
    if ga4_measurement_installed:
        print_result(
            "ga4_measurement_installed = true",
            True,
            f"GA4 Measurement ID is configured (expected: {EXPECTED_GA4_MEASUREMENT_ID})"
        )
    else:
        print_result(
            "ga4_measurement_installed = false",
            False,
            "GA4 Measurement ID is NOT configured"
        )
        all_passed = False
    
    # Check 2: source_status.ga4.ok
    ga4_ok = ga4_status.get("ok", False)
    ga4_error = ga4_status.get("error")
    
    if ga4_ok:
        print_result(
            "source_status.ga4.ok = true",
            True,
            f"GA4 Data API responded successfully (rows: {ga4_status.get('rows', 0)})"
        )
    else:
        print_result(
            "source_status.ga4.ok = false",
            False,
            f"GA4 Data API failed - Error: {ga4_error}"
        )
        all_passed = False
    
    # Check 3: source_status.gsc.ok
    gsc_status = source_status.get("gsc", {})
    gsc_ok = gsc_status.get("ok", False)
    gsc_error = gsc_status.get("error")
    
    if gsc_ok:
        print_result(
            "source_status.gsc.ok = true",
            True,
            f"Google Search Console responded successfully (rows: {gsc_status.get('rows', 0)})"
        )
    else:
        print_result(
            "source_status.gsc.ok = false",
            False,
            f"Google Search Console failed - Error: {gsc_error}"
        )
        # Note: User expects GSC may fail if service account doesn't have permission
        # This is not necessarily a critical failure
    
    # Additional info: Check google status from the status object
    print("\n--- Additional Configuration Info ---")
    status_obj = data.get("status", {})
    google_info = status_obj.get("google", {})
    
    if google_info:
        print(f"Credentials ready: {google_info.get('credentials_ready', 'N/A')}")
        print(f"GSC configured: {google_info.get('gsc_configured', 'N/A')}")
        print(f"GSC site URL: {google_info.get('gsc_site_url', 'N/A')}")
        print(f"GA4 configured: {google_info.get('ga4_configured', 'N/A')}")
        print(f"GA4 property ID: {google_info.get('ga4_property_id', 'N/A')}")
        print(f"GA4 measurement ID: {google_info.get('ga4_measurement_id', 'N/A')}")
        print(f"GA4 measurement installed: {google_info.get('ga4_measurement_installed', 'N/A')}")
    
    return all_passed

def main():
    print_section("GROWTH AGENT - Google Integration Test")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Admin credentials: {ADMIN_EMAIL} / {'*' * len(ADMIN_PASSWORD)}")
    print(f"Expected GA4 Measurement ID: {EXPECTED_GA4_MEASUREMENT_ID}")
    print(f"Expected GSC Site URL: {EXPECTED_GSC_SITE_URL}")
    
    # Step 1: Login
    cookies = login()
    if not cookies:
        print("\n❌ CRITICAL: Authentication failed. Cannot proceed with tests.")
        sys.exit(1)
    
    # Step 2: Test sync endpoint
    sync_data = test_growth_agent_sync(cookies)
    
    # Step 3: Validate response
    validation_passed = validate_sync_response(sync_data)
    
    # Final summary
    print_section("FINAL SUMMARY")
    
    if sync_data:
        sync_run = sync_data.get("sync_run", {})
        source_status = sync_run.get("source_status", {})
        
        print("✓ Objective 1: ga4_measurement_installed =", source_status.get("ga4", {}).get("measurement_installed", False))
        print("✓ Objective 2: source_status.ga4.ok =", source_status.get("ga4", {}).get("ok", False))
        
        ga4_error = source_status.get("ga4", {}).get("error")
        if ga4_error:
            print(f"  └─ GA4 Error: {ga4_error}")
        
        print("✓ Objective 3: source_status.gsc.ok =", source_status.get("gsc", {}).get("ok", False))
        
        gsc_error = source_status.get("gsc", {}).get("error")
        if gsc_error:
            print(f"  └─ GSC Error: {gsc_error}")
        
        print("\n" + "="*80)
        if validation_passed:
            print("✅ ALL CRITICAL CHECKS PASSED")
        else:
            print("⚠️  SOME CHECKS FAILED - See details above")
        print("="*80)
    else:
        print("❌ CRITICAL: Could not retrieve sync data")
        sys.exit(1)

if __name__ == "__main__":
    main()
