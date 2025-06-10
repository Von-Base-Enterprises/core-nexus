#!/bin/bash

echo "🔍 Testing Core Nexus Query Fix"
echo "================================"

API_URL="https://core-nexus-memory-service.onrender.com"

echo -e "\n📝 Test 1: Empty query (was returning 3, should return more)"
curl -s -X POST "$API_URL/memories/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "",
    "limit": 100,
    "min_similarity": 0.0
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'✅ Memories returned: {len(data.get(\"memories\", []))}')
print(f'✅ Total found: {data.get(\"total_found\", 0)}')
if 'trust_metrics' in data:
    print(f'✅ Fix applied: {data[\"trust_metrics\"].get(\"fix_applied\", False)}')
    print(f'✅ Confidence: {data[\"trust_metrics\"].get(\"confidence_score\", 0)}')
"

echo -e "\n📝 Test 2: GET /memories endpoint"
curl -s "$API_URL/memories?limit=50" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'✅ Memories returned: {len(data.get(\"memories\", []))}')
print(f'✅ Total available: {data.get(\"total_found\", 0)}')
"

echo -e "\n📝 Test 3: Memory stats"
curl -s "$API_URL/memories/stats" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'✅ Total memories in system: {data.get(\"total_memories\", 0)}')
"

echo -e "\n✅ DONE - Tell Agent 3 to test their dashboard!"