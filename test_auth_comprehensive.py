#!/usr/bin/env python3
"""
Comprehensive authentication test suite for Core Nexus.
Tests all aspects of the authentication and rate limiting system.
"""

import asyncio
import time
from typing import Dict, List, Tuple
import aiohttp
import json
from datetime import datetime

# Test configuration
API_URL = "https://core-nexus-memory-service.onrender.com"
VALID_API_KEY = "test-key-67890"
INVALID_API_KEY = "invalid-key-12345"
ADMIN_API_KEY = "admin-key-super-secret"

# Test results tracking
test_results = []

async def log_test(name: str, passed: bool, details: str = ""):
    """Log test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    result = {
        "name": name,
        "passed": passed,
        "status": status,
        "details": details,
        "timestamp": datetime.now().isoformat()
    }
    test_results.append(result)
    print(f"{status} - {name}")
    if details:
        print(f"     {details}")

async def test_missing_api_key(session: aiohttp.ClientSession):
    """Test that missing API key returns 401."""
    try:
        async with session.get(f"{API_URL}/memories") as response:
            status = response.status
            if status == 401:
                await log_test("Missing API key returns 401", True)
                return True
            else:
                await log_test("Missing API key returns 401", False, f"Got {status} instead")
                return False
    except Exception as e:
        await log_test("Missing API key returns 401", False, str(e))
        return False

async def test_invalid_api_key(session: aiohttp.ClientSession):
    """Test that invalid API key returns 401."""
    try:
        headers = {"X-API-Key": INVALID_API_KEY}
        async with session.get(f"{API_URL}/memories", headers=headers) as response:
            status = response.status
            if status == 401:
                await log_test("Invalid API key returns 401", True)
                return True
            else:
                await log_test("Invalid API key returns 401", False, f"Got {status} instead")
                return False
    except Exception as e:
        await log_test("Invalid API key returns 401", False, str(e))
        return False

async def test_valid_api_key(session: aiohttp.ClientSession):
    """Test that valid API key allows access."""
    try:
        headers = {"X-API-Key": VALID_API_KEY}
        async with session.get(f"{API_URL}/memories", headers=headers) as response:
            status = response.status
            if status == 200:
                await log_test("Valid API key allows access", True)
                return True
            else:
                await log_test("Valid API key allows access", False, f"Got {status} instead")
                return False
    except Exception as e:
        await log_test("Valid API key allows access", False, str(e))
        return False

async def test_bearer_token_auth(session: aiohttp.ClientSession):
    """Test Bearer token authentication."""
    try:
        headers = {"Authorization": f"Bearer {VALID_API_KEY}"}
        async with session.get(f"{API_URL}/memories", headers=headers) as response:
            status = response.status
            if status == 200:
                await log_test("Bearer token authentication works", True)
                return True
            else:
                await log_test("Bearer token authentication works", False, f"Got {status} instead")
                return False
    except Exception as e:
        await log_test("Bearer token authentication works", False, str(e))
        return False

async def test_rate_limit_headers(session: aiohttp.ClientSession):
    """Test that rate limit headers are present."""
    try:
        headers = {"X-API-Key": VALID_API_KEY}
        async with session.get(f"{API_URL}/memories", headers=headers) as response:
            rate_headers = {
                k: v for k, v in response.headers.items() 
                if k.lower().startswith('x-ratelimit')
            }
            
            required_headers = ['x-ratelimit-limit', 'x-ratelimit-remaining', 'x-ratelimit-reset']
            missing_headers = [h for h in required_headers if h not in [k.lower() for k in rate_headers.keys()]]
            
            if not missing_headers:
                await log_test("Rate limit headers present", True, f"Headers: {rate_headers}")
                return True
            else:
                await log_test("Rate limit headers present", False, f"Missing: {missing_headers}")
                return False
    except Exception as e:
        await log_test("Rate limit headers present", False, str(e))
        return False

async def test_bypass_endpoints(session: aiohttp.ClientSession):
    """Test that bypass endpoints work without authentication."""
    bypass_endpoints = ["/health", "/docs", "/openapi.json", "/metrics"]
    all_passed = True
    
    for endpoint in bypass_endpoints:
        try:
            # No auth headers
            async with session.get(f"{API_URL}{endpoint}") as response:
                status = response.status
                if status in [200, 307]:  # 307 for redirects like /docs
                    await log_test(f"Bypass endpoint {endpoint}", True)
                else:
                    await log_test(f"Bypass endpoint {endpoint}", False, f"Got {status}")
                    all_passed = False
        except Exception as e:
            await log_test(f"Bypass endpoint {endpoint}", False, str(e))
            all_passed = False
    
    return all_passed

async def test_rate_limiting(session: aiohttp.ClientSession):
    """Test rate limiting enforcement."""
    headers = {"X-API-Key": VALID_API_KEY}
    requests_made = 0
    rate_limited = False
    
    print("\n🔄 Testing rate limiting (this may take a while)...")
    
    # Make requests until rate limited
    for i in range(70):  # Default limit is 60/minute
        try:
            async with session.get(f"{API_URL}/memories", headers=headers) as response:
                requests_made += 1
                
                if response.status == 429:
                    rate_limited = True
                    retry_after = response.headers.get('Retry-After', 'unknown')
                    await log_test("Rate limiting enforced", True, 
                                 f"Limited after {requests_made} requests. Retry after: {retry_after}s")
                    return True
                
                # Check remaining count
                remaining = response.headers.get('X-RateLimit-Remaining', 'unknown')
                if i % 10 == 0:
                    print(f"  Request {i+1}: Remaining: {remaining}")
                    
        except Exception as e:
            if "429" in str(e):
                rate_limited = True
                await log_test("Rate limiting enforced", True, f"Limited after {requests_made} requests")
                return True
            else:
                await log_test("Rate limiting enforced", False, str(e))
                return False
        
        # Small delay between requests
        await asyncio.sleep(0.1)
    
    if not rate_limited:
        await log_test("Rate limiting enforced", False, f"Made {requests_made} requests without being limited")
    return rate_limited

async def test_error_response_format(session: aiohttp.ClientSession):
    """Test that error responses have correct format."""
    try:
        # Test with missing API key
        async with session.get(f"{API_URL}/memories") as response:
            if response.status == 401:
                try:
                    error_data = await response.json()
                    if 'detail' in error_data:
                        await log_test("Error response format", True, f"Contains detail: {error_data['detail']}")
                        return True
                    else:
                        await log_test("Error response format", False, "Missing 'detail' field")
                        return False
                except:
                    await log_test("Error response format", False, "Response is not valid JSON")
                    return False
            else:
                await log_test("Error response format", False, f"Expected 401, got {response.status}")
                return False
    except Exception as e:
        await log_test("Error response format", False, str(e))
        return False

async def test_admin_key_access(session: aiohttp.ClientSession):
    """Test admin key has special access."""
    try:
        headers = {"X-API-Key": ADMIN_API_KEY}
        async with session.get(f"{API_URL}/memories", headers=headers) as response:
            # Check for admin indicator in headers
            is_admin = response.headers.get('X-Is-Admin', 'false')
            if response.status == 200 and is_admin == 'true':
                await log_test("Admin key special access", True, "Admin header present")
                return True
            else:
                await log_test("Admin key special access", False, 
                             f"Status: {response.status}, Is-Admin: {is_admin}")
                return False
    except Exception as e:
        await log_test("Admin key special access", False, str(e))
        return False

async def run_all_tests():
    """Run all authentication tests."""
    print("🚀 CORE NEXUS AUTHENTICATION TEST SUITE")
    print("=" * 50)
    print(f"Testing: {API_URL}")
    print(f"Time: {datetime.now()}")
    print("=" * 50)
    
    # Create session with timeout
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        # Run all tests
        await test_missing_api_key(session)
        await test_invalid_api_key(session)
        await test_valid_api_key(session)
        await test_bearer_token_auth(session)
        await test_rate_limit_headers(session)
        await test_bypass_endpoints(session)
        await test_error_response_format(session)
        await test_admin_key_access(session)
        
        # Rate limiting test (optional - takes time)
        print("\n⚠️  Rate limiting test will make many requests.")
        # await test_rate_limiting(session)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for r in test_results if r['passed'])
    failed = len(test_results) - passed
    
    print(f"Total Tests: {len(test_results)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    if failed > 0:
        print("\nFailed Tests:")
        for result in test_results:
            if not result['passed']:
                print(f"  - {result['name']}: {result['details']}")
    
    # Save results
    with open('auth_test_results.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'url': API_URL,
            'summary': {
                'total': len(test_results),
                'passed': passed,
                'failed': failed
            },
            'results': test_results
        }, f, indent=2)
    
    print(f"\n💾 Results saved to auth_test_results.json")
    
    return failed == 0

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)