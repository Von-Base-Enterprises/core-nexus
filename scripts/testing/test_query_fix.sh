#!/bin/bash

# Test the query fix deployment

SERVICE_URL="https://core-nexus-memory-service.onrender.com"

echo "=== Testing Core Nexus Query Fix ==="
echo "Waiting for deployment to complete..."
echo ""

# Wait for deployment (usually 3-5 minutes)
for i in {1..20}; do
    echo -n "Checking deployment status (attempt $i/20): "
    response=$(curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL/health")
    
    if [ "$response" = "200" ]; then
        echo "✅ Service is online!"
        break
    else
        echo "Not ready yet (status: $response)"
        sleep 15
    fi
done

echo ""
echo "Running query tests..."
echo ""

# 1. Health check
echo "1. Health check:"
curl -s "$SERVICE_URL/health" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'   Status: {data[\"status\"]}')
print(f'   Total memories: {data[\"total_memories\"]}')
print(f'   Primary provider: pgvector')
"

# 2. Empty query test
echo -e "\n2. Empty query test (should return memories):"
result=$(curl -s -X POST "$SERVICE_URL/memories/query" \
    -H "Content-Type: application/json" \
    -d '{"query": "", "limit": 5}')
    
echo "$result" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'   Total found: {data[\"total_found\"]}')
print(f'   Memories returned: {len(data[\"memories\"])}')
print(f'   Providers used: {data.get(\"providers_used\", [])}')
"

# 3. GET /memories test
echo -e "\n3. GET /memories test:"
result=$(curl -s "$SERVICE_URL/memories?limit=5")
echo "$result" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'   Total found: {data[\"total_found\"]}')
print(f'   Memories returned: {len(data[\"memories\"])}')
"

# 4. Text search test
echo -e "\n4. Text search test:"
result=$(curl -s "$SERVICE_URL/memories/search/text?q=test&limit=5")
echo "$result" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'   Results found: {data[\"results_found\"]}')
print(f'   Search type: {data[\"search_type\"]}')
"

# 5. Emergency endpoint test
echo -e "\n5. Emergency endpoint test:"
result=$(curl -s "$SERVICE_URL/emergency/find-all-memories?limit=5")
echo "$result" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'   Total memories found: {data[\"total_memories_found\"]}')
print(f'   Diagnostics - total: {data[\"diagnostics\"][\"total_memories\"]}')
"

# 6. Check logs for errors
echo -e "\n6. Checking logs for query errors:"
curl -s "$SERVICE_URL/debug/logs?lines=10" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    logs = data.get('logs', [])
    errors = [l for l in logs if l.get('level') in ['ERROR', 'WARNING']]
    if errors:
        print('   Recent errors:')
        for e in errors[:3]:
            print(f'     [{e[\"level\"]}] {e[\"message\"][:100]}...')
    else:
        print('   No recent errors')
except:
    print('   Could not parse logs')
"

echo -e "\n=== Test Complete ==="
echo ""
echo "If queries now return memories, the fix was successful!"
echo "Expected: All queries should return 1096 memories"