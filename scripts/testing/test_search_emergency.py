#!/usr/bin/env python3
"""
EMERGENCY: Test Core Nexus search functionality
"""

import json
import urllib.request

API_URL = "https://core-nexus-memory-service.onrender.com"

def test_search(query_text, limit=10):
    """Test search with specific query"""
    print(f"\n🔍 Testing search for: '{query_text}'")

    data = json.dumps({
        "query": query_text,
        "limit": limit,
        "min_similarity": 0.3  # Low threshold to catch anything
    }).encode('utf-8')

    req = urllib.request.Request(
        f"{API_URL}/memories/query",
        data=data,
        headers={'Content-Type': 'application/json'}
    )

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read())
            memories_count = len(result.get('memories', []))
            total_found = result.get('total_found', 0)

            print("✅ Response received")
            print(f"📊 Memories returned: {memories_count}")
            print(f"📊 Total found: {total_found}")

            if memories_count > 0:
                print("\n📝 First result:")
                first = result['memories'][0]
                print(f"  Content: {first['content'][:100]}...")
                print(f"  Similarity: {first.get('similarity_score', 'N/A')}")
            else:
                print("❌ NO RESULTS RETURNED!")

            return result
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

# Run emergency tests
print("🚨 EMERGENCY SEARCH DIAGNOSIS")
print("=" * 50)

# Test 1: Search for "VBE"
test_search("VBE")

# Test 2: Search for common words
test_search("memory")
test_search("AI")
test_search("data")

# Test 3: Empty query (should return all)
test_search("")

# Test 4: Check with very low threshold
print("\n🔬 Testing with VERY low threshold (0.0)")
data = json.dumps({
    "query": "VBE",
    "limit": 10,
    "min_similarity": 0.0  # Accept ANY result
}).encode('utf-8')

req = urllib.request.Request(
    f"{API_URL}/memories/query",
    data=data,
    headers={'Content-Type': 'application/json'}
)

try:
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read())
        print(f"With threshold 0.0: {len(result.get('memories', []))} results")
except Exception as e:
    print(f"Error: {e}")
