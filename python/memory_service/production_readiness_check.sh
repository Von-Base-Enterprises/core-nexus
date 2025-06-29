#!/bin/bash

# Production Readiness Check Script for Core Nexus Memory Service
# Tests 8 critical aspects without requiring bc command
# Author: Claude Code
# Date: $(date)

set -e

# Configuration
SERVICE_URL="https://core-nexus-memory-service.onrender.com"
TIMEOUT=30
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Performance targets
HEALTH_TARGET_MS=50
STORAGE_TARGET_MS=2000
QUERY_TARGET_MS=500

# Counters
TOTAL_TESTS=8
PASSED_TESTS=0
FAILED_TESTS=0

# Results storage
declare -a TEST_RESULTS
declare -a PERFORMANCE_METRICS

echo -e "${BLUE}=== Core Nexus Memory Service - Production Readiness Check ===${NC}"
echo "Service URL: $SERVICE_URL"
echo "Target Performance: Health <${HEALTH_TARGET_MS}ms, Storage <${STORAGE_TARGET_MS}ms, Query <${QUERY_TARGET_MS}ms"
echo ""

# Function to calculate milliseconds without bc
calculate_ms() {
    local start_time=$1
    local end_time=$2
    # Convert to milliseconds using shell arithmetic
    local duration_seconds=$((end_time - start_time))
    local duration_ms=$((duration_seconds * 1000))
    # For sub-second precision, we'll use a simple approximation
    echo $duration_ms
}

# Function to record test result
record_test() {
    local test_name="$1"
    local status="$2"
    local duration_ms="$3"
    local details="$4"
    
    if [ "$status" = "PASS" ]; then
        ((PASSED_TESTS++))
        echo -e "✅ ${GREEN}PASS${NC} - $test_name (${duration_ms}ms) $details"
    else
        ((FAILED_TESTS++))
        echo -e "❌ ${RED}FAIL${NC} - $test_name (${duration_ms}ms) $details"
    fi
    
    TEST_RESULTS+=("$test_name:$status:${duration_ms}ms:$details")
}

# Function to make HTTP request and measure time
make_request() {
    local method="$1"
    local endpoint="$2"
    local headers="$3"
    local data="$4"
    
    local start_time=$(date +%s%N)
    local response
    local http_code
    
    if [ -n "$data" ]; then
        response=$(curl -s -w "%{http_code}" -X "$method" \
            -H "Content-Type: application/json" \
            $headers \
            -d "$data" \
            --max-time $TIMEOUT \
            "$SERVICE_URL$endpoint" 2>/dev/null)
    else
        response=$(curl -s -w "%{http_code}" -X "$method" \
            $headers \
            --max-time $TIMEOUT \
            "$SERVICE_URL$endpoint" 2>/dev/null)
    fi
    
    local end_time=$(date +%s%N)
    local duration_ns=$((end_time - start_time))
    local duration_ms=$((duration_ns / 1000000))
    
    # Extract HTTP code (last 3 characters)
    http_code="${response: -3}"
    # Extract response body (all but last 3 characters)
    local response_body="${response%???}"
    
    echo "$http_code|$duration_ms|$response_body"
}

echo "Starting production readiness tests..."
echo ""

# Test 1: Health Check
echo -e "${BLUE}Test 1/8: Health Check${NC}"
result=$(make_request "GET" "/health" "" "")
IFS='|' read -r http_code duration_ms response_body <<< "$result"

if [ "$http_code" = "200" ] && [ "$duration_ms" -lt "$HEALTH_TARGET_MS" ]; then
    record_test "Health Check" "PASS" "$duration_ms" "- Service healthy"
elif [ "$http_code" = "200" ]; then
    record_test "Health Check" "PASS" "$duration_ms" "- Service healthy but slow (target: <${HEALTH_TARGET_MS}ms)"
else
    record_test "Health Check" "FAIL" "$duration_ms" "- HTTP $http_code"
fi

# Test 2: Metrics Endpoint
echo -e "${BLUE}Test 2/8: Metrics Endpoint${NC}"
result=$(make_request "GET" "/metrics" "" "")
IFS='|' read -r http_code duration_ms response_body <<< "$result"

if [ "$http_code" = "200" ]; then
    record_test "Metrics Endpoint" "PASS" "$duration_ms" "- Metrics available"
else
    record_test "Metrics Endpoint" "FAIL" "$duration_ms" "- HTTP $http_code"
fi

# Test 3: Stats Endpoint
echo -e "${BLUE}Test 3/8: Stats Endpoint${NC}"
result=$(make_request "GET" "/api/v1/stats" "" "")
IFS='|' read -r http_code duration_ms response_body <<< "$result"

if [ "$http_code" = "200" ]; then
    record_test "Stats Endpoint" "PASS" "$duration_ms" "- Stats available"
else
    record_test "Stats Endpoint" "FAIL" "$duration_ms" "- HTTP $http_code"
fi

# Test 4: Memory Storage
echo -e "${BLUE}Test 4/8: Memory Storage${NC}"
test_content="Production readiness test memory - $(date +%s)"
storage_data="{\"content\": \"$test_content\", \"metadata\": {\"test\": \"production_check\", \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}"

result=$(make_request "POST" "/api/v1/memories" "" "$storage_data")
IFS='|' read -r http_code duration_ms response_body <<< "$result"

if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
    # Extract memory ID from response
    memory_id=$(echo "$response_body" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
    if [ "$duration_ms" -lt "$STORAGE_TARGET_MS" ]; then
        record_test "Memory Storage" "PASS" "$duration_ms" "- Memory stored (ID: ${memory_id:0:8}...)"
    else
        record_test "Memory Storage" "PASS" "$duration_ms" "- Memory stored but slow (target: <${STORAGE_TARGET_MS}ms)"
    fi
else
    record_test "Memory Storage" "FAIL" "$duration_ms" "- HTTP $http_code"
    memory_id=""
fi

# Test 5: Memory Retrieval
echo -e "${BLUE}Test 5/8: Memory Retrieval${NC}"
if [ -n "$memory_id" ]; then
    result=$(make_request "GET" "/api/v1/memories/$memory_id" "" "")
    IFS='|' read -r http_code duration_ms response_body <<< "$result"
    
    if [ "$http_code" = "200" ]; then
        # Check if retrieved content matches stored content
        if echo "$response_body" | grep -q "$test_content"; then
            record_test "Memory Retrieval" "PASS" "$duration_ms" "- Memory retrieved successfully"
        else
            record_test "Memory Retrieval" "FAIL" "$duration_ms" "- Content mismatch"
        fi
    else
        record_test "Memory Retrieval" "FAIL" "$duration_ms" "- HTTP $http_code"
    fi
else
    record_test "Memory Retrieval" "FAIL" "0" "- No memory ID to retrieve"
fi

# Test 6: Semantic Query
echo -e "${BLUE}Test 6/8: Semantic Query${NC}"
query_data="{\"query\": \"production test\", \"limit\": 5}"
result=$(make_request "POST" "/api/v1/query" "" "$query_data")
IFS='|' read -r http_code duration_ms response_body <<< "$result"

if [ "$http_code" = "200" ]; then
    if [ "$duration_ms" -lt "$QUERY_TARGET_MS" ]; then
        record_test "Semantic Query" "PASS" "$duration_ms" "- Query successful"
    else
        record_test "Semantic Query" "PASS" "$duration_ms" "- Query successful but slow (target: <${QUERY_TARGET_MS}ms)"
    fi
else
    record_test "Semantic Query" "FAIL" "$duration_ms" "- HTTP $http_code"
fi

# Test 7: Authentication Test
echo -e "${BLUE}Test 7/8: Authentication${NC}"
result=$(make_request "GET" "/api/v1/stats" "-H 'X-API-Key: invalid-key-test'" "")
IFS='|' read -r http_code duration_ms response_body <<< "$result"

if [ "$http_code" = "401" ] || [ "$http_code" = "403" ]; then
    record_test "Authentication" "PASS" "$duration_ms" "- Properly rejects invalid API key (HTTP $http_code)"
elif [ "$http_code" = "500" ]; then
    record_test "Authentication" "FAIL" "$duration_ms" "- Returns 500 instead of 401/403 for invalid key"
else
    record_test "Authentication" "FAIL" "$duration_ms" "- Unexpected response (HTTP $http_code)"
fi

# Test 8: Error Handling
echo -e "${BLUE}Test 8/8: Error Handling${NC}"
invalid_data="{\"invalid\": \"json data structure\"}"
result=$(make_request "POST" "/api/v1/memories" "" "$invalid_data")
IFS='|' read -r http_code duration_ms response_body <<< "$result"

if [ "$http_code" = "400" ] || [ "$http_code" = "422" ]; then
    record_test "Error Handling" "PASS" "$duration_ms" "- Properly handles invalid data (HTTP $http_code)"
else
    record_test "Error Handling" "FAIL" "$duration_ms" "- HTTP $http_code (expected 400/422)"
fi

echo ""
echo -e "${BLUE}=== Production Readiness Summary ===${NC}"
echo "Total Tests: $TOTAL_TESTS"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed: ${RED}$FAILED_TESTS${NC}"

# Calculate success rate using shell arithmetic
success_rate=$((PASSED_TESTS * 100 / TOTAL_TESTS))
echo "Success Rate: $success_rate%"

echo ""
echo -e "${BLUE}=== Performance Analysis ===${NC}"
for result in "${TEST_RESULTS[@]}"; do
    IFS=':' read -r test_name status duration details <<< "$result"
    echo "$test_name: $duration ($status) $details"
done

echo ""
if [ "$PASSED_TESTS" -eq "$TOTAL_TESTS" ]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED - SERVICE IS PRODUCTION READY! 🎉${NC}"
    exit 0
elif [ "$success_rate" -ge 75 ]; then
    echo -e "${YELLOW}⚠️  SERVICE IS MOSTLY READY - Some issues need attention ⚠️${NC}"
    exit 1
else
    echo -e "${RED}❌ SERVICE NOT READY FOR PRODUCTION - Critical issues found ❌${NC}"
    exit 2
fi