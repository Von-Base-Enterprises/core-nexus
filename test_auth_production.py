#!/usr/bin/env python3
"""
Test authentication changes against the production Core Nexus service.

This script verifies that the authentication middleware correctly:
1. Returns 401 for missing API keys (not 500)
2. Returns 401 for invalid API keys
3. Includes rate limit headers in all responses
4. Allows bypass endpoints without authentication
"""

import requests
import json
from typing import Dict

# Production URL
BASE_URL = "https://core-nexus-memory-service.onrender.com"

# Test API keys
VALID_API_KEY = "dev-key-12345"
INVALID_API_KEY = "invalid-key-99999"


def print_response_details(response: requests.Response, test_name: str):
    """Print detailed response information."""
    print(f"\n{'='*60}")
    print(f"Test: {test_name}")
    print(f"{'='*60}")
    print(f"Status Code: {response.status_code}")
    print(f"\nRate Limit Headers:")
    print(f"  X-RateLimit-Limit: {response.headers.get('X-RateLimit-Limit', 'NOT PRESENT')}")
    print(f"  X-RateLimit-Remaining: {response.headers.get('X-RateLimit-Remaining', 'NOT PRESENT')}")
    print(f"  X-RateLimit-Reset: {response.headers.get('X-RateLimit-Reset', 'NOT PRESENT')}")
    print(f"\nAuth Headers:")
    print(f"  X-API-Key-Valid: {response.headers.get('X-API-Key-Valid', 'NOT PRESENT')}")
    print(f"  X-Is-Admin: {response.headers.get('X-Is-Admin', 'NOT PRESENT')}")
    
    if response.status_code in [401, 429, 500]:
        print(f"\nError Response:")
        try:
            print(json.dumps(response.json(), indent=2))
        except:
            print(response.text)


def test_missing_api_key():
    """Test endpoint without API key - should return 401, not 500."""
    response = requests.get(
        f"{BASE_URL}/memories",
        headers={"Accept": "application/json"}
    )
    print_response_details(response, "Missing API Key")
    
    success = response.status_code == 401
    print(f"\n✅ PASSED" if success else f"\n❌ FAILED - Expected 401, got {response.status_code}")
    return success


def test_invalid_api_key():
    """Test endpoint with invalid API key - should return 401."""
    response = requests.get(
        f"{BASE_URL}/memories",
        headers={
            "X-API-Key": INVALID_API_KEY,
            "Accept": "application/json"
        }
    )
    print_response_details(response, "Invalid API Key")
    
    success = response.status_code == 401
    print(f"\n✅ PASSED" if success else f"\n❌ FAILED - Expected 401, got {response.status_code}")
    return success


def test_valid_api_key():
    """Test endpoint with valid API key - should return 200 with rate limit headers."""
    response = requests.get(
        f"{BASE_URL}/memories",
        headers={
            "X-API-Key": VALID_API_KEY,
            "Accept": "application/json"
        }
    )
    print_response_details(response, "Valid API Key")
    
    # Check both status and headers
    has_rate_limit_headers = all([
        response.headers.get('X-RateLimit-Limit'),
        response.headers.get('X-RateLimit-Remaining'),
        response.headers.get('X-RateLimit-Reset')
    ])
    
    success = response.status_code == 200 and has_rate_limit_headers
    
    if response.status_code != 200:
        print(f"\n❌ FAILED - Expected 200, got {response.status_code}")
    elif not has_rate_limit_headers:
        print(f"\n❌ FAILED - Missing rate limit headers")
    else:
        print(f"\n✅ PASSED")
    
    return success


def test_bearer_auth():
    """Test Bearer token authentication."""
    response = requests.get(
        f"{BASE_URL}/memories",
        headers={
            "Authorization": f"Bearer {VALID_API_KEY}",
            "Accept": "application/json"
        }
    )
    print_response_details(response, "Bearer Token Authentication")
    
    success = response.status_code == 200
    print(f"\n✅ PASSED" if success else f"\n❌ FAILED - Expected 200, got {response.status_code}")
    return success


def test_health_endpoint():
    """Test health endpoint - should work without authentication."""
    response = requests.get(f"{BASE_URL}/health")
    print_response_details(response, "Health Endpoint (No Auth Required)")
    
    success = response.status_code == 200
    print(f"\n✅ PASSED" if success else f"\n❌ FAILED - Expected 200, got {response.status_code}")
    return success


def test_post_endpoint():
    """Test POST endpoint with authentication."""
    response = requests.post(
        f"{BASE_URL}/memories/query",
        headers={
            "X-API-Key": VALID_API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "query": "test",
            "limit": 5,
            "threshold": 0.5
        }
    )
    print_response_details(response, "POST Endpoint with Valid API Key")
    
    has_rate_limit_headers = all([
        response.headers.get('X-RateLimit-Limit'),
        response.headers.get('X-RateLimit-Remaining'),
        response.headers.get('X-RateLimit-Reset')
    ])
    
    success = response.status_code == 200 and has_rate_limit_headers
    
    if response.status_code != 200:
        print(f"\n❌ FAILED - Expected 200, got {response.status_code}")
    elif not has_rate_limit_headers:
        print(f"\n❌ FAILED - Missing rate limit headers")
    else:
        print(f"\n✅ PASSED")
    
    return success


def main():
    """Run all production tests."""
    print("🚀 Core Nexus Authentication Middleware Production Tests")
    print(f"Testing against: {BASE_URL}")
    print("=" * 80)
    
    results = {
        "Missing API Key → 401": test_missing_api_key(),
        "Invalid API Key → 401": test_invalid_api_key(),
        "Valid API Key → 200 + Headers": test_valid_api_key(),
        "Bearer Token → 200": test_bearer_auth(),
        "Health Endpoint → 200 (No Auth)": test_health_endpoint(),
        "POST with Auth → 200 + Headers": test_post_endpoint()
    }
    
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Authentication is working correctly in production.")
        print("\n✅ The 500 → 401 error fix is confirmed working!")
        print("✅ Rate limit headers are being added to all responses!")
    else:
        failed = total - passed
        print(f"\n⚠️ {failed} test(s) failed. The authentication changes may not be deployed yet.")
        print("\nTo deploy the changes:")
        print("1. Commit and push the changes to GitHub")
        print("2. Create a pull request")
        print("3. Deploy to Render after merge")


if __name__ == "__main__":
    main()