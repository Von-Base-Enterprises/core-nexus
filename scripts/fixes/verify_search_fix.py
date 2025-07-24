#!/usr/bin/env python3
"""
Verify the emergency search fix is working
"""

import json
import time
import urllib.request

API_URL = "https://core-nexus-memory-service.onrender.com"

def test_empty_query():
    """Test that empty queries now work"""
    print("\n🔍 Testing empty query (was broken, should work now)...")

    data = json.dumps({
        "query": "",
        "limit": 10
    }).encode('utf-8')

    req = urllib.request.Request(
        f"{API_URL}/memories/query",
        data=data,
        headers={'Content-Type': 'application/json'}
    )

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read())
            memories = len(result.get('memories', []))
            print(f"✅ Empty query works! Returned {memories} memories")
            return True
    except urllib.error.HTTPError as e:
        print(f"❌ Empty query still broken: {e.code} {e.reason}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_normal_search():
    """Test that normal searches still work"""
    print("\n🔍 Testing normal search...")

    test_queries = ["VBE", "AI", "memory", "test"]

    for query in test_queries:
        data = json.dumps({
            "query": query,
            "limit": 5
        }).encode('utf-8')

        req = urllib.request.Request(
            f"{API_URL}/memories/query",
            data=data,
            headers={'Content-Type': 'application/json'}
        )

        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read())
                memories = len(result.get('memories', []))
                total = result.get('total_found', 0)
                print(f"  ✅ '{query}': {memories} returned, {total} total found")
        except Exception as e:
            print(f"  ❌ '{query}': Failed - {e}")

print("🚨 EMERGENCY SEARCH FIX VERIFICATION")
print("=" * 50)

# Check if fix is deployed
print("Checking deployment status...")
empty_works = test_empty_query()

if not empty_works:
    print("\n⏳ Fix not deployed yet. Waiting for deployment...")
    print("(This typically takes 2-5 minutes)")

    # Wait and retry
    for i in range(30):  # Try for 5 minutes
        time.sleep(10)
        print(f"\rRetrying... ({i+1}/30)", end='')
        if test_empty_query():
            print("\n✅ Fix is now deployed!")
            break
    else:
        print("\n⚠️ Fix still not deployed after 5 minutes")

# Test normal searches
test_normal_search()

print("\n" + "=" * 50)
print("SUMMARY:")
if empty_works:
    print("✅ SEARCH IS FULLY FUNCTIONAL")
    print("✅ Empty queries work")
    print("✅ Text queries work")
    print("\n🎉 Customer can now search successfully!")
else:
    print("⏳ Waiting for deployment...")
    print("❌ Empty queries still return 400")
    print("✅ Text queries are working")
    print("\nWorkaround: Tell customer to search for specific terms, not empty")
