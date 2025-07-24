#!/bin/bash

# Verify Core Nexus deployment and apply fixes

echo "=== Core Nexus Deployment Verification ==="
echo "Time: $(date)"
echo ""

# Function to test endpoint
test_endpoint() {
    local url=$1
    local method=${2:-GET}
    local data=${3:-}
    
    if [ "$method" = "POST" ] && [ -n "$data" ]; then
        curl -s -X POST "$url" -H "Content-Type: application/json" -d "$data" -w "\nStatus: %{http_code}\n"
    else
        curl -s "$url" -w "\nStatus: %{http_code}\n"
    fi
}

# 1. Check if service is up
echo "1. Checking service availability..."
echo "   Testing: https://core-nexus-memory.onrender.com/health"
health_response=$(test_endpoint "https://core-nexus-memory.onrender.com/health")
echo "$health_response" | tail -1

# Extract status code
status_code=$(echo "$health_response" | tail -1 | grep -o '[0-9]\+')

if [ "$status_code" = "200" ]; then
    echo "   ✅ Service is ONLINE!"
    
    # Parse current memory count
    current_count=$(echo "$health_response" | grep -o '"total_memories":[0-9]*' | grep -o '[0-9]*$')
    echo "   Current memory count: ${current_count:-unknown}"
    
    # 2. Apply the fix if needed
    if [ "${current_count:-0}" -eq 0 ]; then
        echo ""
        echo "2. Applying data sync fix..."
        echo "   Calling: POST /admin/refresh-stats"
        
        refresh_response=$(test_endpoint "https://core-nexus-memory.onrender.com/admin/refresh-stats?admin_key=refresh-stats-2025" "POST")
        echo "$refresh_response"
        
        # 3. Verify the fix
        echo ""
        echo "3. Verifying fix..."
        sleep 2
        
        health_after=$(test_endpoint "https://core-nexus-memory.onrender.com/health")
        new_count=$(echo "$health_after" | grep -o '"total_memories":[0-9]*' | grep -o '[0-9]*$')
        echo "   Memory count after fix: ${new_count:-unknown}"
        
        if [ "${new_count:-0}" -gt 0 ]; then
            echo "   ✅ Fix successful! Data sync issue resolved."
        else
            echo "   ⚠️  Fix may not have worked. Check logs."
        fi
    else
        echo "   ℹ️  Memory count already synced ($current_count memories)"
    fi
    
    # 4. Test query functionality
    echo ""
    echo "4. Testing query functionality..."
    query_response=$(test_endpoint "https://core-nexus-memory.onrender.com/memories/query" "POST" '{"query":"","limit":5}')
    total_found=$(echo "$query_response" | grep -o '"total_found":[0-9]*' | grep -o '[0-9]*$')
    echo "   Query returned: ${total_found:-unknown} memories"
    
elif [ "$status_code" = "404" ]; then
    echo "   ❌ Service returning 404 - Still deploying or misconfigured"
    echo ""
    echo "Possible issues:"
    echo "1. Deployment still in progress (check https://dashboard.render.com)"
    echo "2. Service failed to start (check Render logs)"
    echo "3. URL structure changed"
    
elif [ "$status_code" = "502" ] || [ "$status_code" = "503" ]; then
    echo "   ⚠️  Service unavailable (${status_code}) - Likely still starting up"
    echo "   Try again in a few minutes"
    
else
    echo "   ❓ Unexpected status: ${status_code}"
fi

echo ""
echo "=== Verification Complete ==="
echo ""

# Provide next steps
if [ "$status_code" != "200" ]; then
    echo "Next steps:"
    echo "1. Check Render dashboard: https://dashboard.render.com"
    echo "2. Look for 'core-nexus-memory' service"
    echo "3. Check deployment logs for errors"
    echo "4. Wait 5-10 minutes if deployment is in progress"
else
    echo "Success! The Core Nexus Memory Service is operational."
    echo "Data synchronization has been ${current_count:-0} -> ${new_count:-$current_count} memories"
fi