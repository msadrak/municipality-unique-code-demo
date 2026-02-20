"""
Test script for Treasury Integration API
=========================================

This script tests the Treasury Integration API endpoints to ensure they work correctly.

Usage:
    python test_treasury_api.py

Requirements:
    - Server must be running (uvicorn app.main:app --reload)
    - Database must be populated with test data
    - Valid admin user credentials required
"""

import requests
import json
from datetime import datetime, timedelta


# Configuration
BASE_URL = "http://localhost:8000"
USERNAME = "admin"  # Change to your admin username
PASSWORD = "admin"  # Change to your admin password


def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_result(test_name, success, message="", data=None):
    """Print test result"""
    status = "✓ PASS" if success else "✗ FAIL"
    print(f"\n{status} - {test_name}")
    if message:
        print(f"  Message: {message}")
    if data:
        print(f"  Data: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")


def test_health_check():
    """Test 1: Health check endpoint"""
    print_section("TEST 1: Health Check")
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/treasury/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                print_result("Health Check", True, "API is healthy", data)
                return True
            else:
                print_result("Health Check", False, f"Unexpected status: {data.get('status')}")
                return False
        else:
            print_result("Health Check", False, f"HTTP {response.status_code}")
            return False
    
    except requests.exceptions.RequestException as e:
        print_result("Health Check", False, f"Connection error: {e}")
        return False


def test_login():
    """Test 2: Login and get session"""
    print_section("TEST 2: Authentication")
    
    try:
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/auth/login",
            json={"username": USERNAME, "password": PASSWORD},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                print_result("Login", True, "Authentication successful", data)
                return session
            else:
                print_result("Login", False, f"Login failed: {data}")
                return None
        else:
            print_result("Login", False, f"HTTP {response.status_code}: {response.text}")
            return None
    
    except requests.exceptions.RequestException as e:
        print_result("Login", False, f"Connection error: {e}")
        return None


def test_export_without_auth():
    """Test 3: Export endpoint without authentication (should fail)"""
    print_section("TEST 3: Export Without Authentication (Should Fail)")
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/treasury/export", timeout=5)
        
        if response.status_code == 401:
            print_result("Unauthorized Access", True, "Correctly rejected unauthenticated request")
            return True
        else:
            print_result("Unauthorized Access", False, f"Expected 401, got {response.status_code}")
            return False
    
    except requests.exceptions.RequestException as e:
        print_result("Unauthorized Access", False, f"Connection error: {e}")
        return False


def test_summary(session):
    """Test 4: Get summary statistics"""
    print_section("TEST 4: Summary Statistics")
    
    try:
        response = session.get(f"{BASE_URL}/api/v1/treasury/export/summary", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print_result("Summary Statistics", True, "Summary retrieved", data)
            return True, data
        else:
            print_result("Summary Statistics", False, f"HTTP {response.status_code}: {response.text}")
            return False, None
    
    except requests.exceptions.RequestException as e:
        print_result("Summary Statistics", False, f"Connection error: {e}")
        return False, None


def test_export_basic(session):
    """Test 5: Basic export (first 10 records)"""
    print_section("TEST 5: Basic Export (10 records)")
    
    try:
        response = session.get(
            f"{BASE_URL}/api/v1/treasury/export",
            params={"limit": 10},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if isinstance(data, list):
                print(f"\n  Retrieved {len(data)} transactions")
                
                if len(data) > 0:
                    # Validate first record
                    first_record = data[0]
                    required_fields = ["code_yekta", "amount", "submission_date", "financial_event", "activity"]
                    
                    missing_fields = [field for field in required_fields if field not in first_record]
                    
                    if not missing_fields:
                        print("\n  Sample Transaction:")
                        print(f"    Code Yekta: {first_record['code_yekta']}")
                        print(f"    Amount: {first_record['amount']:,} Rials")
                        print(f"    Date: {first_record['submission_date']}")
                        print(f"    Event: {first_record['financial_event']['name']} (ID: {first_record['financial_event']['id']})")
                        print(f"    Activity: {first_record['activity']['name']} (ID: {first_record['activity']['id']})")
                        
                        print_result("Basic Export", True, f"Retrieved and validated {len(data)} transactions")
                        return True
                    else:
                        print_result("Basic Export", False, f"Missing fields: {missing_fields}")
                        return False
                else:
                    print_result("Basic Export", True, "No transactions found (empty database)", {"count": 0})
                    return True
            else:
                print_result("Basic Export", False, f"Expected array, got {type(data)}")
                return False
        
        else:
            print_result("Basic Export", False, f"HTTP {response.status_code}: {response.text}")
            return False
    
    except requests.exceptions.RequestException as e:
        print_result("Basic Export", False, f"Connection error: {e}")
        return False


def test_date_filter(session):
    """Test 6: Export with date filter"""
    print_section("TEST 6: Date Filter")
    
    try:
        # Get last 30 days
        date_to = datetime.now().strftime("%Y-%m-%d")
        date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        response = session.get(
            f"{BASE_URL}/api/v1/treasury/export",
            params={
                "date_from": date_from,
                "date_to": date_to,
                "limit": 100
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print_result("Date Filter", True, f"Retrieved {len(data)} transactions from {date_from} to {date_to}")
            return True
        else:
            print_result("Date Filter", False, f"HTTP {response.status_code}: {response.text}")
            return False
    
    except requests.exceptions.RequestException as e:
        print_result("Date Filter", False, f"Connection error: {e}")
        return False


def test_invalid_date_format(session):
    """Test 7: Invalid date format (should fail)"""
    print_section("TEST 7: Invalid Date Format (Should Fail)")
    
    try:
        response = session.get(
            f"{BASE_URL}/api/v1/treasury/export",
            params={"date_from": "2025/01/01"},  # Wrong format (should be YYYY-MM-DD)
            timeout=10
        )
        
        if response.status_code == 400:
            print_result("Invalid Date Format", True, "Correctly rejected invalid date format")
            return True
        else:
            print_result("Invalid Date Format", False, f"Expected 400, got {response.status_code}")
            return False
    
    except requests.exceptions.RequestException as e:
        print_result("Invalid Date Format", False, f"Connection error: {e}")
        return False


def test_pagination(session):
    """Test 8: Pagination"""
    print_section("TEST 8: Pagination")
    
    try:
        # Get first page
        response1 = session.get(
            f"{BASE_URL}/api/v1/treasury/export",
            params={"limit": 5, "offset": 0},
            timeout=10
        )
        
        # Get second page
        response2 = session.get(
            f"{BASE_URL}/api/v1/treasury/export",
            params={"limit": 5, "offset": 5},
            timeout=10
        )
        
        if response1.status_code == 200 and response2.status_code == 200:
            page1 = response1.json()
            page2 = response2.json()
            
            print(f"\n  Page 1: {len(page1)} records")
            print(f"  Page 2: {len(page2)} records")
            
            # Check that pages are different (if we have enough data)
            if len(page1) > 0 and len(page2) > 0:
                page1_codes = [t['code_yekta'] for t in page1]
                page2_codes = [t['code_yekta'] for t in page2]
                
                if page1_codes != page2_codes:
                    print_result("Pagination", True, "Pages contain different records")
                    return True
                else:
                    print_result("Pagination", False, "Pages contain same records")
                    return False
            else:
                print_result("Pagination", True, "Pagination works (not enough data to verify uniqueness)")
                return True
        else:
            print_result("Pagination", False, f"HTTP errors: {response1.status_code}, {response2.status_code}")
            return False
    
    except requests.exceptions.RequestException as e:
        print_result("Pagination", False, f"Connection error: {e}")
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("  TREASURY INTEGRATION API - TEST SUITE")
    print("=" * 80)
    print(f"\n  Base URL: {BASE_URL}")
    print(f"  Username: {USERNAME}")
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # Test 1: Health check
    results.append(("Health Check", test_health_check()))
    
    # Test 2: Login
    session = test_login()
    if session:
        results.append(("Authentication", True))
        
        # Test 3: Unauthorized access
        results.append(("Unauthorized Access Check", test_export_without_auth()))
        
        # Test 4: Summary
        summary_success, summary_data = test_summary(session)
        results.append(("Summary Statistics", summary_success))
        
        # Test 5: Basic export
        results.append(("Basic Export", test_export_basic(session)))
        
        # Test 6: Date filter
        results.append(("Date Filter", test_date_filter(session)))
        
        # Test 7: Invalid date format
        results.append(("Invalid Date Format", test_invalid_date_format(session)))
        
        # Test 8: Pagination
        results.append(("Pagination", test_pagination(session)))
    else:
        results.append(("Authentication", False))
        print("\n⚠️  Skipping remaining tests due to authentication failure")
    
    # Summary
    print_section("TEST SUMMARY")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"\n  Total Tests: {total}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {total - passed}")
    print(f"  Success Rate: {(passed/total*100):.1f}%")
    
    print("\n  Results:")
    for test_name, success in results:
        status = "✓" if success else "✗"
        print(f"    {status} {test_name}")
    
    print("\n" + "=" * 80)
    
    if passed == total:
        print("\n  ✓ ALL TESTS PASSED!")
    else:
        print("\n  ✗ SOME TESTS FAILED - Please review the output above")
    
    print("\n" + "=" * 80 + "\n")
    
    return passed == total


if __name__ == "__main__":
    try:
        success = run_all_tests()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user\n")
        exit(1)
    except Exception as e:
        print(f"\n\n✗ FATAL ERROR: {e}\n")
        exit(1)
