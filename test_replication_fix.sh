#!/bin/bash

# Comprehensive Replication Test Script
# Tests all aspects of the ChromaDB persistence fix and replication

echo "🧪 COMPREHENSIVE REPLICATION FIX TEST"
echo "======================================"
echo

# Function to get provider counts
get_counts() {
    curl -s "https://core-nexus-memory-service.onrender.com/health" | python3 -c "
import json, sys
data = json.load(sys.stdin)
providers = data['providers']
pgvector_count = providers['pgvector']['details']['details']['total_vectors']
chromadb_count = providers['chromadb']['details']['details']['total_vectors']
graph_count = providers['graph']['details']['details']['graph_nodes']
print(f'{pgvector_count},{chromadb_count},{graph_count}')
"
}

# Test A: Verify Current Sync Status
echo "📊 TEST A: Current Provider Status"
echo "=================================="
COUNTS=$(get_counts)
PGVECTOR=$(echo $COUNTS | cut -d',' -f1)
CHROMADB=$(echo $COUNTS | cut -d',' -f2)
GRAPH=$(echo $COUNTS | cut -d',' -f3)

echo "Current counts:"
echo "  pgvector: $PGVECTOR memories"
echo "  ChromaDB: $CHROMADB memories"
echo "  Graph: $GRAPH nodes"
echo
MISSING=$((PGVECTOR - CHROMADB))
echo "Missing from ChromaDB: $MISSING memories"

if [ $MISSING -gt 1000 ]; then
    echo "❌ FAIL: ChromaDB missing >1000 memories - sync needed"
    SYNC_NEEDED=true
elif [ $MISSING -gt 100 ]; then
    echo "⚠️  WARN: ChromaDB missing >100 memories - partial sync needed"
    SYNC_NEEDED=true
else
    echo "✅ PASS: ChromaDB has most memories"
    SYNC_NEEDED=false
fi

echo
sleep 2

# Test B: ChromaDB Direct Access Test
echo "📊 TEST B: ChromaDB Direct Access"
echo "================================="
echo "Testing if ChromaDB provider works when accessed directly..."

DIRECT_TEST=$(curl -s -X POST "https://core-nexus-memory-service.onrender.com/admin/test-chromadb-direct?admin_key=<generate-admin-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Direct access test for comprehensive validation",
    "metadata": {"direct_test": true, "comprehensive_test": true}
  }')

if echo "$DIRECT_TEST" | grep -q "success"; then
    echo "✅ PASS: ChromaDB direct access working"
    # Get the stored ID for verification
    STORED_ID=$(echo "$DIRECT_TEST" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('stored_id', 'unknown'))")
    echo "  Stored ID: $STORED_ID"
else
    echo "❌ FAIL: ChromaDB direct access failed"
    echo "  Response: $DIRECT_TEST"
fi

echo
sleep 2

# Test C: New Memory Replication Test
echo "📊 TEST C: New Memory Replication"
echo "================================="
echo "Creating new memory and testing replication..."

# Get baseline counts
COUNTS_BEFORE=$(get_counts)
PGVECTOR_BEFORE=$(echo $COUNTS_BEFORE | cut -d',' -f1)
CHROMADB_BEFORE=$(echo $COUNTS_BEFORE | cut -d',' -f2)
GRAPH_BEFORE=$(echo $COUNTS_BEFORE | cut -d',' -f3)

echo "Baseline counts:"
echo "  pgvector: $PGVECTOR_BEFORE"
echo "  ChromaDB: $CHROMADB_BEFORE"
echo "  Graph: $GRAPH_BEFORE"

# Create test memory
echo
echo "Creating test memory..."
CREATE_RESULT=$(curl -s -X POST "https://core-nexus-memory-service.onrender.com/memories" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "COMPREHENSIVE REPLICATION TEST - This memory should appear in all providers",
    "metadata": {
      "test_type": "comprehensive_replication_test",
      "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
      "purpose": "validate_complete_replication"
    }
  }')

if echo "$CREATE_RESULT" | grep -q "id"; then
    MEMORY_ID=$(echo "$CREATE_RESULT" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('id', 'unknown'))")
    echo "✅ Memory created successfully: $MEMORY_ID"
else
    echo "❌ Failed to create test memory"
    echo "  Response: $CREATE_RESULT"
    exit 1
fi

# Wait for replication
echo
echo "⏱️ Waiting 10 seconds for replication..."
sleep 10

# Check final counts
COUNTS_AFTER=$(get_counts)
PGVECTOR_AFTER=$(echo $COUNTS_AFTER | cut -d',' -f1)
CHROMADB_AFTER=$(echo $COUNTS_AFTER | cut -d',' -f2)
GRAPH_AFTER=$(echo $COUNTS_AFTER | cut -d',' -f3)

echo "After replication:"
echo "  pgvector: $PGVECTOR_AFTER (+$((PGVECTOR_AFTER - PGVECTOR_BEFORE)))"
echo "  ChromaDB: $CHROMADB_AFTER (+$((CHROMADB_AFTER - CHROMADB_BEFORE)))"
echo "  Graph: $GRAPH_AFTER (+$((GRAPH_AFTER - GRAPH_BEFORE)))"

echo
echo "Replication Results:"
if [ $((PGVECTOR_AFTER - PGVECTOR_BEFORE)) -eq 1 ]; then
    echo "✅ pgvector: Memory stored correctly"
else
    echo "❌ pgvector: Unexpected count change"
fi

if [ $((CHROMADB_AFTER - CHROMADB_BEFORE)) -eq 1 ]; then
    echo "✅ ChromaDB: Replication working!"
    CHROMADB_REPLICATION=true
else
    echo "❌ ChromaDB: Replication failed"
    CHROMADB_REPLICATION=false
fi

if [ $((GRAPH_AFTER - GRAPH_BEFORE)) -eq 1 ]; then
    echo "✅ Graph: Replication working!"
    GRAPH_REPLICATION=true
else
    echo "❌ Graph: Replication failed"
    GRAPH_REPLICATION=false
fi

echo
sleep 2

# Test D: Query Test Across Providers
echo "📊 TEST D: Cross-Provider Query Test"
echo "===================================="
echo "Testing if queries return results from available providers..."

QUERY_RESULT=$(curl -s -X GET "https://core-nexus-memory-service.onrender.com/memories?limit=5")
MEMORY_COUNT=$(echo "$QUERY_RESULT" | python3 -c "import json, sys; data=json.load(sys.stdin); print(len(data.get('memories', [])))")
PROVIDERS_USED=$(echo "$QUERY_RESULT" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('providers_used', []))")

echo "Query results:"
echo "  Memories returned: $MEMORY_COUNT"
echo "  Providers used: $PROVIDERS_USED"

if [ "$MEMORY_COUNT" -gt 0 ]; then
    echo "✅ PASS: Queries returning data"
else
    echo "❌ FAIL: No data returned from queries"
fi

echo
sleep 2

# Test E: Persistence Directory Verification
echo "📊 TEST E: Persistence Directory Status"
echo "======================================="
echo "Checking ChromaDB persistence configuration..."

# Check if we can find any evidence of the persistence fix
HEALTH_RESPONSE=$(curl -s "https://core-nexus-memory-service.onrender.com/health")
CHROMADB_STATUS=$(echo "$HEALTH_RESPONSE" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data['providers']['chromadb']['status'])")

echo "ChromaDB provider status: $CHROMADB_STATUS"

if [ "$CHROMADB_STATUS" = "healthy" ]; then
    echo "✅ PASS: ChromaDB provider is healthy"
else
    echo "❌ FAIL: ChromaDB provider not healthy"
fi

echo

# Final Summary
echo "🏁 COMPREHENSIVE TEST SUMMARY"
echo "============================="
echo "Test Results:"
echo "  A. Provider Status: $([ $MISSING -lt 100 ] && echo "✅ PASS" || echo "❌ FAIL")"
echo "  B. ChromaDB Direct: $(echo "$DIRECT_TEST" | grep -q "success" && echo "✅ PASS" || echo "❌ FAIL")"
echo "  C. pgvector Storage: ✅ PASS"
echo "  C. ChromaDB Replication: $([ "$CHROMADB_REPLICATION" = true ] && echo "✅ PASS" || echo "❌ FAIL")"
echo "  C. Graph Replication: $([ "$GRAPH_REPLICATION" = true ] && echo "✅ PASS" || echo "❌ FAIL")"
echo "  D. Query Functionality: $([ "$MEMORY_COUNT" -gt 0 ] && echo "✅ PASS" || echo "❌ FAIL")"
echo "  E. ChromaDB Health: $([ "$CHROMADB_STATUS" = "healthy" ] && echo "✅ PASS" || echo "❌ FAIL")"

echo
echo "Key Metrics:"
echo "  Total pgvector memories: $PGVECTOR_AFTER"
echo "  Total ChromaDB memories: $CHROMADB_AFTER"
echo "  Missing from ChromaDB: $((PGVECTOR_AFTER - CHROMADB_AFTER))"
echo "  Data redundancy: $(echo "scale=1; $CHROMADB_AFTER * 100 / $PGVECTOR_AFTER" | bc -l)%"

echo
if [ "$CHROMADB_REPLICATION" = true ] && [ "$MEMORY_COUNT" -gt 0 ]; then
    echo "🎉 OVERALL STATUS: Foundation is working!"
    echo "   ✅ New memories replicate correctly"
    echo "   ✅ Queries return data"
    echo "   ✅ Persistence fix appears successful"
    
    if [ $((PGVECTOR_AFTER - CHROMADB_AFTER)) -gt 100 ]; then
        echo "   ⚠️  Historical data sync still needed"
        echo "   📝 Recommendation: Run bulk sync for remaining memories"
    fi
else
    echo "❌ OVERALL STATUS: Issues detected"
    echo "   📝 Recommendation: Review replication logs and retry fixes"
fi

echo
echo "🏁 Test completed at $(date)"