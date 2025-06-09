#!/bin/bash
# Verify that the query fix worked

echo "🔍 Testing Core Nexus Query Functionality..."
echo "==========================================="

# Test 1: Health Check
echo -e "\n1. Health Check:"
curl -s https://core-nexus-memory-service.onrender.com/health | jq '.status, .total_memories'

# Test 2: Store a test memory
echo -e "\n\n2. Storing test memory:"
MEMORY_RESPONSE=$(curl -s -X POST https://core-nexus-memory-service.onrender.com/memories \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Query fix verification test at '"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'",
    "metadata": {"test": true, "purpose": "verify_fix"}
  }')

MEMORY_ID=$(echo "$MEMORY_RESPONSE" | jq -r '.id')
echo "Stored memory ID: $MEMORY_ID"

# Test 3: Query for memories (THIS IS THE MAIN TEST)
echo -e "\n\n3. Testing query (should return results):"
QUERY_RESPONSE=$(curl -s -X POST https://core-nexus-memory-service.onrender.com/memories/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test verification", "limit": 5}')

TOTAL_FOUND=$(echo "$QUERY_RESPONSE" | jq -r '.total_found')
MEMORY_COUNT=$(echo "$QUERY_RESPONSE" | jq -r '.memories | length')

echo "Total memories found: $TOTAL_FOUND"
echo "Memories returned: $MEMORY_COUNT"

# Test 4: Check if fix worked
echo -e "\n\n📊 Results:"
if [ "$TOTAL_FOUND" -gt 0 ]; then
    echo "✅ SUCCESS! Queries are returning results!"
    echo "✅ Found $TOTAL_FOUND memories in the system"
    
    # Show sample results
    echo -e "\nSample results:"
    echo "$QUERY_RESPONSE" | jq '.memories[:2]'
else
    echo "❌ FAILED! Queries still returning empty results"
    echo "❌ You need to run the PSQL fix script"
    echo ""
    echo "Run this in your PostgreSQL:"
    echo "CREATE INDEX idx_vector_memories_embedding ON vector_memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);"
fi

# Test 5: Performance check
echo -e "\n\n⏱️  Performance Metrics:"
echo "$QUERY_RESPONSE" | jq '.query_time_ms'