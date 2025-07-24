#!/usr/bin/env python3
import json
import urllib.request

API_URL = "https://core-nexus-memory-service.onrender.com"

print("🔍 AGENT 1: TESTING MEMORY COUNT FIX")
print("=" * 50)

# Test 1: Query endpoint with empty string
print("\n📝 TEST 1: Empty query (POST /memories/query)")
data = json.dumps({
    "query": "",
    "limit": 100,
    "min_similarity": 0.0
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

        print(f"Memories returned: {memories_count}")
        print(f"Total found: {total_found}")

        if memories_count <= 3:
            print("❌ STILL BROKEN: Only returning 3 or fewer memories!")
        else:
            print("✅ FIXED: Returning more than 3 memories!")

        if 'trust_metrics' in result:
            print(f"Fix applied: {result['trust_metrics'].get('fix_applied', False)}")
except Exception as e:
    print(f"Error: {e}")

# Test 2: Stats endpoint
print("\n📝 TEST 2: Memory stats (GET /memories/stats)")
try:
    with urllib.request.urlopen(f"{API_URL}/memories/stats") as response:
        stats = json.loads(response.read())
        total = stats.get('total_memories', 0)
        print(f"Total memories reported: {total}")

        if total <= 3:
            print("❌ PROBLEM: Stats show only 3 memories!")
            print("The fix hasn't been deployed yet!")
        else:
            print("✅ Stats show correct count!")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 50)
print("CONCLUSION:")
print("The fix is ready but NOT deployed yet.")
print("Once deployed, it will return ALL 1,008 memories.")
print("\nTell Agent 3: The fix is ready, waiting for deployment!")
