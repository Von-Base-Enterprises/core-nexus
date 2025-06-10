#!/usr/bin/env python3
"""
Knowledge Graph Validation Test Suite
Tests all graph endpoints against production
"""

import json
import time
import urllib.error
import urllib.request
from datetime import datetime


def test_endpoint(name, method, url, data=None, headers=None):
    """Test a single endpoint and return results."""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"Method: {method}")
    print(f"URL: {url}")

    start_time = time.time()

    try:
        req = urllib.request.Request(url, method=method)

        # Add headers
        if headers:
            for key, value in headers.items():
                req.add_header(key, value)

        # Add data for POST requests
        if data and method == "POST":
            req.data = json.dumps(data).encode('utf-8')
            req.add_header('Content-Type', 'application/json')

        # Make request
        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.status
            body = json.loads(response.read().decode('utf-8'))
            elapsed = time.time() - start_time

            print(f"✅ Status: {status}")
            print(f"Response time: {elapsed:.2f}s")
            print(f"Response: {json.dumps(body, indent=2)[:200]}...")

            return {
                "endpoint": name,
                "status": status,
                "success": True,
                "response": body,
                "time": elapsed
            }

    except urllib.error.HTTPError as e:
        elapsed = time.time() - start_time
        error_body = None
        try:
            error_body = json.loads(e.read().decode('utf-8'))
        except:
            error_body = {"error": str(e)}

        print(f"❌ Status: {e.code}")
        print(f"Response time: {elapsed:.2f}s")
        print(f"Error: {json.dumps(error_body, indent=2)[:200]}...")

        return {
            "endpoint": name,
            "status": e.code,
            "success": False,
            "error": error_body,
            "time": elapsed
        }

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ Connection Error: {str(e)}")

        return {
            "endpoint": name,
            "status": 0,
            "success": False,
            "error": str(e),
            "time": elapsed
        }


def main():
    """Run all graph endpoint tests."""
    print("🔍 Knowledge Graph Validation Test Suite")
    print(f"Time: {datetime.now().isoformat()}")
    print("Target: https://core-nexus-memory-service.onrender.com")

    base_url = "https://core-nexus-memory-service.onrender.com"

    # Define all graph endpoints to test
    tests = [
        # 1. Graph Stats
        {
            "name": "Graph Stats",
            "method": "GET",
            "url": f"{base_url}/graph/stats"
        },

        # 2. Graph Query
        {
            "name": "Graph Query",
            "method": "POST",
            "url": f"{base_url}/graph/query",
            "data": {"query_type": "entity_search", "limit": 10}
        },

        # 3. Entity Exploration
        {
            "name": "Entity Exploration (VBE)",
            "method": "GET",
            "url": f"{base_url}/graph/explore/VBE"
        },

        # 4. Path Finding
        {
            "name": "Path Finding (VBE to Nike)",
            "method": "GET",
            "url": f"{base_url}/graph/path/VBE/Nike"
        },

        # 5. Memory Sync (using test ID)
        {
            "name": "Memory Sync",
            "method": "POST",
            "url": f"{base_url}/graph/sync/test-memory-id"
        },

        # 6. Bulk Sync
        {
            "name": "Bulk Sync",
            "method": "POST",
            "url": f"{base_url}/graph/bulk-sync",
            "data": {"memory_ids": ["id1", "id2"]}
        },

        # 7. Graph Insights
        {
            "name": "Graph Insights",
            "method": "GET",
            "url": f"{base_url}/graph/insights/test-memory-id"
        }
    ]

    # Run all tests
    results = []
    for test in tests:
        result = test_endpoint(
            name=test["name"],
            method=test["method"],
            url=test["url"],
            data=test.get("data"),
            headers=test.get("headers")
        )
        results.append(result)

    # Summary
    print(f"\n{'='*60}")
    print("📊 SUMMARY")
    print('='*60)

    total = len(results)
    success = sum(1 for r in results if r["success"])
    status_503 = sum(1 for r in results if r["status"] == 503)
    status_501 = sum(1 for r in results if r["status"] == 501)
    status_500 = sum(1 for r in results if r["status"] == 500)
    status_200 = sum(1 for r in results if r["status"] == 200)

    print(f"Total endpoints tested: {total}")
    print(f"✅ Successful (200): {status_200}")
    print(f"⚠️  Not Implemented (501): {status_501}")
    print(f"🔒 Service Unavailable (503): {status_503}")
    print(f"❌ Server Error (500): {status_500}")

    # Analysis
    print("\n💡 ANALYSIS")
    print('='*60)

    if status_503 == total:
        print("🎯 ALL endpoints return 503 - Graph provider is NOT ENABLED")
        print("✅ Good news: Implementation exists, just needs activation!")
        print("🔧 Fix: Set GRAPH_ENABLED=true in production environment")

    elif status_503 > 0 and status_503 < total:
        print("⚠️  Mixed results - Some endpoints unavailable")
        print("This suggests partial implementation or configuration issues")

    elif status_501 > 0:
        print("🚧 Some endpoints not implemented (501)")
        print("Need to complete implementation for full functionality")

    elif status_500 > 0:
        print("❌ Server errors detected - Implementation issues")
        print("Debug and fix errors before proceeding")

    elif status_200 == total:
        print("✅ All endpoints working! Knowledge graph is fully functional")

    # Save detailed results
    with open('graph_validation_results.json', 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": total,
                "success": success,
                "by_status": {
                    "200": status_200,
                    "501": status_501,
                    "503": status_503,
                    "500": status_500
                }
            },
            "results": results
        }, f, indent=2)

    print("\nDetailed results saved to: graph_validation_results.json")

    return results


if __name__ == "__main__":
    main()
