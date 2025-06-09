#!/bin/bash
# Monitor Core Nexus deployment and query fix

echo "🚀 Monitoring Core Nexus Deployment..."
echo "====================================="
echo "Waiting for Render to deploy from main branch..."
echo ""

DEPLOYMENT_COMPLETE=false
CHECK_COUNT=0
MAX_CHECKS=30  # 15 minutes max

while [ "$DEPLOYMENT_COMPLETE" = false ] && [ $CHECK_COUNT -lt $MAX_CHECKS ]; do
    CHECK_COUNT=$((CHECK_COUNT + 1))
    echo -n "Check #$CHECK_COUNT ($(date +%H:%M:%S)): "
    
    # Test if query works (indicates new code is deployed)
    RESPONSE=$(curl -s -X POST https://core-nexus-memory-service.onrender.com/memories/query \
        -H "Content-Type: application/json" \
        -d '{"query": "test", "limit": 5}' 2>&1)
    
    if echo "$RESPONSE" | grep -q "dictionary update sequence"; then
        echo "❌ Old code still running (metadata bug present)"
    elif echo "$RESPONSE" | grep -q "memories"; then
        echo "✅ NEW CODE DEPLOYED! Testing queries..."
        DEPLOYMENT_COMPLETE=true
        
        # Extract results
        TOTAL=$(echo "$RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('total_found', 0))" 2>/dev/null || echo "0")
        
        if [ "$TOTAL" -gt 0 ]; then
            echo ""
            echo "🎉 SUCCESS! Queries are returning results!"
            echo "Total memories found: $TOTAL"
            echo ""
            echo "Sample response:"
            echo "$RESPONSE" | python3 -m json.tool 2>/dev/null | head -20
        else
            echo ""
            echo "⚠️  Code deployed but queries still return 0 results"
            echo "📌 Need to create database indexes!"
            echo ""
            echo "Run this SQL in your PostgreSQL:"
            echo "CREATE INDEX idx_vector_memories_embedding ON vector_memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);"
        fi
    else
        echo "⏳ Service responding but status unclear"
    fi
    
    if [ "$DEPLOYMENT_COMPLETE" = false ]; then
        sleep 30  # Wait 30 seconds between checks
    fi
done

if [ "$DEPLOYMENT_COMPLETE" = false ]; then
    echo ""
    echo "❌ Deployment monitoring timed out after 15 minutes"
    echo "Check Render dashboard for deployment status"
fi

echo ""
echo "Final status check:"
curl -s https://core-nexus-memory-service.onrender.com/health | python3 -m json.tool 2>/dev/null | grep -E "(status|total_memories|uptime)" || echo "Failed to get health status"