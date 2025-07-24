#!/bin/bash

# Continuous monitoring script for Core Nexus deployment

PRODUCTION_URL="https://core-nexus-memory.onrender.com"
ADMIN_KEY="refresh-stats-2025"
CHECK_INTERVAL=30
MAX_CHECKS=20

echo "=== Core Nexus Continuous Deployment Monitor ==="
echo "Started at: $(date)"
echo "Checking every ${CHECK_INTERVAL} seconds..."
echo ""

check_count=0
service_online=false

while [ $check_count -lt $MAX_CHECKS ]; do
    check_count=$((check_count + 1))
    echo -n "[$(date +%H:%M:%S)] Check #${check_count}: "
    
    # Check health endpoint
    response=$(curl -s -o /dev/null -w "%{http_code}" "${PRODUCTION_URL}/health")
    
    if [ "$response" = "200" ]; then
        echo "✅ SERVICE IS ONLINE!"
        service_online=true
        break
    else
        echo "Status: $response - Still waiting..."
    fi
    
    sleep $CHECK_INTERVAL
done

if [ "$service_online" = true ]; then
    echo ""
    echo "=== Service is online! Running data sync fix... ==="
    echo ""
    
    # Get current health status
    echo "1. Current health status:"
    health_response=$(curl -s "${PRODUCTION_URL}/health")
    echo "$health_response" | grep -o '"total_memories":[0-9]*' || echo "Could not parse health response"
    
    echo ""
    echo "2. Applying data sync fix..."
    
    # Call refresh endpoint
    refresh_response=$(curl -s -X POST "${PRODUCTION_URL}/admin/refresh-stats?admin_key=${ADMIN_KEY}")
    echo "Refresh response: $refresh_response"
    
    echo ""
    echo "3. Verifying fix..."
    
    # Check health again
    sleep 2
    health_after=$(curl -s "${PRODUCTION_URL}/health")
    echo "Total memories after fix: "
    echo "$health_after" | grep -o '"total_memories":[0-9]*' || echo "Could not parse response"
    
    echo ""
    echo "4. Testing memory query..."
    query_response=$(curl -s -X POST "${PRODUCTION_URL}/memories/query" \
        -H "Content-Type: application/json" \
        -d '{"query": "", "limit": 5}')
    echo "Query found: "
    echo "$query_response" | grep -o '"total_found":[0-9]*' || echo "Could not parse query response"
    
    echo ""
    echo "=== Fix Complete! ==="
    echo "If successful, you should see 1,095+ memories"
else
    echo ""
    echo "❌ Service did not come online after $((MAX_CHECKS * CHECK_INTERVAL)) seconds"
    echo "Please check https://dashboard.render.com for deployment status"
fi

echo ""
echo "Finished at: $(date)"