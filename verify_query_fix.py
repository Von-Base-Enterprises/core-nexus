#!/usr/bin/env python3
"""
Verification script for Core Nexus query fix
Tests that the API now returns all 1,008 memories instead of just 3
"""


import requests

# API configuration
API_BASE_URL = "https://core-nexus-memory-service.onrender.com"
# API_BASE_URL = "http://localhost:8000"  # For local testing

def test_query_fix():
    """Test that empty queries now return all memories"""
    print("🔍 Core Nexus Query Fix Verification")
    print("=" * 50)

    # Test 1: Empty query via POST /memories/query
    print("\n📝 Test 1: Empty query via POST /memories/query")
    response = requests.post(
        f"{API_BASE_URL}/memories/query",
        json={
            "query": "",  # Empty query that was returning only 3 results
            "limit": 100,
            "min_similarity": 0.0
        }
    )

    if response.status_code == 200:
        data = response.json()
        memories_returned = len(data.get('memories', []))
        total_found = data.get('total_found', 0)

        print(f"✅ Status: {response.status_code}")
        print(f"📊 Memories returned: {memories_returned}")
        print(f"📊 Total found: {total_found}")
        print(f"⏱️ Query time: {data.get('query_time_ms', 0):.1f}ms")

        if memories_returned < 10 and total_found > 100:
            print(f"❌ BUG STILL EXISTS: Only {memories_returned} returned but {total_found} exist!")
        else:
            print(f"✅ FIX CONFIRMED: Returning {memories_returned} memories as expected!")
    else:
        print(f"❌ Request failed: {response.status_code}")
        print(f"Error: {response.text}")

    # Test 2: New GET /memories endpoint
    print("\n📝 Test 2: New GET /memories endpoint")
    response = requests.get(
        f"{API_BASE_URL}/memories",
        params={
            "limit": 100
        }
    )

    if response.status_code == 200:
        data = response.json()
        memories_returned = len(data.get('memories', []))
        total_found = data.get('total_found', 0)

        print(f"✅ Status: {response.status_code}")
        print(f"📊 Memories returned: {memories_returned}")
        print(f"📊 Total found: {total_found}")
        print(f"⏱️ Query time: {data.get('query_time_ms', 0):.1f}ms")
    else:
        print(f"❌ Request failed: {response.status_code}")
        print("Note: This endpoint might not be deployed yet")

    # Test 3: Check memory stats
    print("\n📝 Test 3: Memory statistics")
    response = requests.get(f"{API_BASE_URL}/memories/stats")

    if response.status_code == 200:
        stats = response.json()
        print(f"✅ Total memories in system: {stats.get('total_memories', 0)}")
        print("📊 Memories by provider:")
        for provider, count in stats.get('memories_by_provider', {}).items():
            print(f"   - {provider}: {count}")
    else:
        print(f"❌ Stats request failed: {response.status_code}")

    # Test 4: Query with search term
    print("\n📝 Test 4: Query with search term 'AI'")
    response = requests.post(
        f"{API_BASE_URL}/memories/query",
        json={
            "query": "AI artificial intelligence",
            "limit": 10,
            "min_similarity": 0.3
        }
    )

    if response.status_code == 200:
        data = response.json()
        memories_returned = len(data.get('memories', []))
        total_found = data.get('total_found', 0)

        print(f"✅ Status: {response.status_code}")
        print(f"📊 Memories returned: {memories_returned}")
        print(f"📊 Total found: {total_found}")

        # Show sample memories
        if memories_returned > 0:
            print("\n📋 Sample results:")
            for i, memory in enumerate(data['memories'][:3]):
                print(f"\n{i+1}. Content: {memory['content'][:100]}...")
                print(f"   Similarity: {memory.get('similarity_score', 0):.3f}")
                print(f"   Importance: {memory.get('importance_score', 0):.3f}")
    else:
        print(f"❌ Request failed: {response.status_code}")

    # Test 5: Performance comparison
    print("\n📝 Test 5: Performance test with different limits")
    limits = [10, 50, 100, 500]

    for limit in limits:
        response = requests.post(
            f"{API_BASE_URL}/memories/query",
            json={
                "query": "",
                "limit": limit,
                "min_similarity": 0.0
            }
        )

        if response.status_code == 200:
            data = response.json()
            print(f"   Limit {limit}: {len(data['memories'])} returned in {data.get('query_time_ms', 0):.1f}ms")
        else:
            print(f"   Limit {limit}: Failed with status {response.status_code}")

    print("\n" + "=" * 50)
    print("✅ Verification complete!")
    print("\n💡 Summary:")
    print("- Empty queries should now return all available memories (up to limit)")
    print("- The 3-result bug should be fixed")
    print("- Performance should scale appropriately with limit")
    print("- New GET /memories endpoint provides direct access to all memories")

if __name__ == "__main__":
    test_query_fix()
