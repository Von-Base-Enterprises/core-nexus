#!/bin/bash

# Monitor Core Nexus deployment and apply data sync fix

PRODUCTION_URL="https://core-nexus-memory.onrender.com"
ADMIN_KEY="refresh-stats-2025"

echo "=== Core Nexus Data Sync Fix Script ==="
echo "Monitoring deployment status..."
echo ""

# Function to check if service is ready
check_deployment() {
    response=$(curl -s -o /dev/null -w "%{http_code}" "${PRODUCTION_URL}/health")
    echo "$response"
}

# Wait for deployment
echo -n "Waiting for deployment to complete"
for i in {1..30}; do
    status=$(check_deployment)
    if [ "$status" = "200" ]; then
        echo -e "\n✅ Service is online!"
        break
    else
        echo -n "."
        sleep 10
    fi
done

if [ "$status" != "200" ]; then
    echo -e "\n❌ Service not responding after 5 minutes. Check Render dashboard."
    exit 1
fi

echo ""
echo "Checking current stats..."

# Check current health
echo "1. Current health status:"
curl -s "${PRODUCTION_URL}/health" | grep -o '"total_memories":[0-9]*' || echo "Failed to get health"

echo ""
echo "2. Refreshing stats..."

# Call refresh endpoint
response=$(curl -s -X POST "${PRODUCTION_URL}/admin/refresh-stats?admin_key=${ADMIN_KEY}")
if [ $? -eq 0 ]; then
    echo "Response: $response"
else
    echo "❌ Failed to refresh stats"
fi

echo ""
echo "3. Checking updated health:"
curl -s "${PRODUCTION_URL}/health" | grep -o '"total_memories":[0-9]*' || echo "Failed to get health"

echo ""
echo "4. Testing memory query:"
curl -s -X POST "${PRODUCTION_URL}/memories/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "", "limit": 5}' | grep -o '"total_found":[0-9]*' || echo "Failed to query"

echo ""
echo "=== Fix Complete ==="
echo ""
echo "If successful, you should see:"
echo "- total_memories: 1095 (or more)"
echo "- total_found: 1095 (or more)"