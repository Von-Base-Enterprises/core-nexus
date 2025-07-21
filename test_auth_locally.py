#!/usr/bin/env python3
"""
Test script to verify authentication middleware functionality locally.

Tests:
1. Missing API key returns 401
2. Invalid API key returns 401
3. Valid API key returns success with rate limit headers
4. Rate limiting works correctly
5. Bypass endpoints work without authentication
"""

import requests
import time
import json
from typing import Dict

# Local test server URL
BASE_URL = "http://localhost:8000"

# Test API keys (matching defaults in auth.py)
VALID_API_KEY = "dev-key-12345"
INVALID_API_KEY = "invalid-key-99999"


def print_test_result(test_name: str, passed: bool, details: str = ""):
    """Print formatted test result."""
    status = "✅ PASSED" if passed else "❌ FAILED"
    print(f"\n{test_name}: {status}")
    if details:
        print(f"  Details: {details}")


def test_missing_api_key():
    """Test that missing API key returns 401."""
    print("\n=== Testing Missing API Key ===")
    
    response = requests.get(f"{BASE_URL}/memories")
    
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print(f"Response: {response.text}")
    
    passed = response.status_code == 401
    details = ""
    
    if passed:
        try:
            data = response.json()
            if "API key required" in data.get("detail", ""):
                details = "Correct error message returned"
            else:
                passed = False
                details = f"Wrong error message: {data.get('detail')}"
        except:
            passed = False
            details = "Response is not valid JSON"
    
    print_test_result("Missing API Key Test", passed, details)
    return passed


def test_invalid_api_key():
    """Test that invalid API key returns 401."""
    print("\n=== Testing Invalid API Key ===")
    
    headers = {"X-API-Key": INVALID_API_KEY}
    response = requests.get(f"{BASE_URL}/memories", headers=headers)
    
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print(f"Response: {response.text}")
    
    passed = response.status_code == 401
    details = ""
    
    if passed:
        try:
            data = response.json()
            if "Invalid API key" in data.get("detail", ""):
                details = "Correct error message returned"
            else:
                passed = False
                details = f"Wrong error message: {data.get('detail')}"
        except:
            passed = False
            details = "Response is not valid JSON"
    
    print_test_result("Invalid API Key Test", passed, details)
    return passed


def test_valid_api_key_with_headers():
    """Test that valid API key returns success with rate limit headers."""
    print("\n=== Testing Valid API Key with Rate Limit Headers ===")
    
    headers = {"X-API-Key": VALID_API_KEY}
    response = requests.get(f"{BASE_URL}/memories", headers=headers)
    
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    
    # Check for rate limit headers
    rate_limit_headers = {
        "X-RateLimit-Limit": response.headers.get("X-RateLimit-Limit"),
        "X-RateLimit-Remaining": response.headers.get("X-RateLimit-Remaining"),
        "X-RateLimit-Reset": response.headers.get("X-RateLimit-Reset"),
        "X-API-Key-Valid": response.headers.get("X-API-Key-Valid"),
        "X-Is-Admin": response.headers.get("X-Is-Admin")
    }
    
    print(f"Rate Limit Headers: {rate_limit_headers}")
    
    passed = (
        response.status_code == 200 and
        all(rate_limit_headers.values()) and
        rate_limit_headers["X-API-Key-Valid"] == "true"
    )
    
    details = "All rate limit headers present" if passed else "Missing rate limit headers"
    
    print_test_result("Valid API Key Test", passed, details)
    return passed


def test_bearer_token_auth():
    """Test that Bearer token authentication works."""
    print("\n=== Testing Bearer Token Authentication ===")
    
    headers = {"Authorization": f"Bearer {VALID_API_KEY}"}
    response = requests.get(f"{BASE_URL}/memories", headers=headers)
    
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    
    passed = response.status_code == 200
    details = "Bearer token accepted" if passed else "Bearer token rejected"
    
    print_test_result("Bearer Token Test", passed, details)
    return passed


def test_bypass_endpoints():
    """Test that bypass endpoints work without authentication."""
    print("\n=== Testing Bypass Endpoints ===")
    
    bypass_endpoints = ["/health", "/docs", "/openapi.json"]
    all_passed = True
    
    for endpoint in bypass_endpoints:
        response = requests.get(f"{BASE_URL}{endpoint}")
        passed = response.status_code in [200, 307]  # 307 for redirect to /docs/
        all_passed = all_passed and passed
        
        print(f"{endpoint}: {'✅' if passed else '❌'} (Status: {response.status_code})")
    
    print_test_result("Bypass Endpoints Test", all_passed)
    return all_passed


def test_rate_limiting():
    """Test that rate limiting works correctly."""
    print("\n=== Testing Rate Limiting ===")
    print("Note: This test requires RATE_LIMIT_PER_MINUTE=5 for testing purposes")
    
    headers = {"X-API-Key": VALID_API_KEY}
    
    # Make multiple requests quickly
    for i in range(7):
        response = requests.get(f"{BASE_URL}/memories", headers=headers)
        remaining = response.headers.get("X-RateLimit-Remaining", "?")
        
        print(f"Request {i+1}: Status={response.status_code}, Remaining={remaining}")
        
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "?")
            print(f"Rate limit hit! Retry-After: {retry_after}s")
            
            # Check rate limit headers are still present
            passed = all([
                response.headers.get("X-RateLimit-Limit"),
                response.headers.get("X-RateLimit-Remaining") == "0",
                response.headers.get("X-RateLimit-Reset"),
                response.headers.get("Retry-After")
            ])
            
            print_test_result("Rate Limiting Test", passed, 
                            "Rate limit enforced with proper headers" if passed else "Missing headers on 429")
            return passed
        
        time.sleep(0.1)  # Small delay between requests
    
    print_test_result("Rate Limiting Test", False, "Rate limit not triggered (may need lower limit for testing)")
    return False


def main():
    """Run all authentication tests."""
    print("=" * 60)
    print("Core Nexus Authentication Middleware Test Suite")
    print("=" * 60)
    print(f"Testing against: {BASE_URL}")
    print("\nMake sure the service is running locally with:")
    print("cd python/memory_service && python -m uvicorn src.memory_service.api:app --reload")
    print("=" * 60)
    
    input("\nPress Enter to start tests...")
    
    # Run all tests
    results = {
        "Missing API Key": test_missing_api_key(),
        "Invalid API Key": test_invalid_api_key(),
        "Valid API Key": test_valid_api_key_with_headers(),
        "Bearer Token": test_bearer_token_auth(),
        "Bypass Endpoints": test_bypass_endpoints(),
        # "Rate Limiting": test_rate_limiting()  # Commented out as it requires specific config
    }
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        print(f"{test_name}: {'✅ PASSED' if result else '❌ FAILED'}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Authentication middleware is working correctly.")
    else:
        print("\n⚠️ Some tests failed. Please check the implementation.")


if __name__ == "__main__":
    main()