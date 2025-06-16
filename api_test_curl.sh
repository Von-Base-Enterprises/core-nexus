#!/bin/bash

# Comprehensive API Testing Script using curl
# Tests Core Nexus Memory Service endpoints

BASE_URL="https://core-nexus-memory-service.onrender.com"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
REPORT_FILE="api_test_report_${TIMESTAMP}.json"

# Initialize report
echo "{" > $REPORT_FILE
echo "  \"test_summary\": {" >> $REPORT_FILE
echo "    \"started_at\": \"$(date -Iseconds)\"," >> $REPORT_FILE
echo "    \"base_url\": \"$BASE_URL\"" >> $REPORT_FILE
echo "  }," >> $REPORT_FILE
echo "  \"test_results\": [" >> $REPORT_FILE

# Function to test endpoint and log results
test_endpoint() {
    local test_name="$1"
    local method="$2"
    local endpoint="$3"
    local payload="$4"
    local expected_status="$5"
    
    echo "Testing: $test_name"
    
    # Prepare curl command
    local curl_cmd="curl -s -w '%{http_code}|%{time_total}' -X $method"
    
    if [ "$method" = "POST" ] && [ -n "$payload" ]; then
        curl_cmd="$curl_cmd -H 'Content-Type: application/json' -d '$payload'"
    fi
    
    curl_cmd="$curl_cmd $BASE_URL$endpoint"
    
    # Execute request
    local start_time=$(date +%s.%N)
    local response=$(eval $curl_cmd)
    local end_time=$(date +%s.%N)
    
    # Parse response
    local http_code=$(echo "$response" | grep -o '[0-9]\{3\}|[0-9.]*$' | cut -d'|' -f1)
    local response_time=$(echo "$response" | grep -o '[0-9]\{3\}|[0-9.]*$' | cut -d'|' -f2)
    local response_body=$(echo "$response" | sed 's/[0-9]\{3\}|[0-9.]*$//')
    
    # Determine success
    local success="false"
    if [ -z "$expected_status" ]; then
        [ "$http_code" = "200" ] && success="true"
    else
        [ "$http_code" = "$expected_status" ] && success="true"
    fi
    
    # Log result
    echo "    {" >> $REPORT_FILE
    echo "      \"test_name\": \"$test_name\"," >> $REPORT_FILE
    echo "      \"method\": \"$method\"," >> $REPORT_FILE
    echo "      \"endpoint\": \"$endpoint\"," >> $REPORT_FILE
    echo "      \"success\": $success," >> $REPORT_FILE
    echo "      \"http_code\": $http_code," >> $REPORT_FILE
    echo "      \"response_time_seconds\": $response_time," >> $REPORT_FILE
    echo "      \"timestamp\": \"$(date -Iseconds)\"," >> $REPORT_FILE
    
    # Clean and add response body (truncate if too long)
    local clean_response=$(echo "$response_body" | sed 's/"/\\"/g' | head -c 500)
    echo "      \"response_preview\": \"$clean_response\"" >> $REPORT_FILE
    echo "    }," >> $REPORT_FILE
    
    # Console output
    if [ "$success" = "true" ]; then
        echo "  ✓ PASS (${http_code}, ${response_time}s)"
    else
        echo "  ✗ FAIL (${http_code}, ${response_time}s)"
    fi
    echo ""
}

echo "Starting comprehensive API testing..."
echo "Base URL: $BASE_URL"
echo "Report will be saved to: $REPORT_FILE"
echo "=========================================="
echo ""

# Test 1: Health Check
test_endpoint "Health Check" "GET" "/health"

# Test 2: Memory Stats
test_endpoint "Memory Statistics" "GET" "/memories/stats"

# Test 3: Get All Memories
test_endpoint "Get All Memories" "GET" "/memories?limit=5"

# Test 4: Create Single Memory
test_endpoint "Create Memory" "POST" "/memories" \
'{"content": "Test memory for API testing", "context": "API Test", "metadata": {"test": true}}'

# Test 5: Query Memories
test_endpoint "Query Memories" "POST" "/memories/query" \
'{"query": "test", "limit": 5}'

# Test 6: Empty Query Test
test_endpoint "Empty Query Test" "POST" "/memories/query" \
'{"query": "", "limit": 10}'

# Test 7: Batch Create Memories
test_endpoint "Batch Create Memories" "POST" "/memories/batch" \
'{"memories": [{"content": "Batch test 1", "context": "Batch"}, {"content": "Batch test 2", "context": "Batch"}]}'

# Test 8: Text Search
test_endpoint "Text Search" "GET" "/memories/search/text?q=test&limit=5"

# Test 9: Dedup Check
test_endpoint "Deduplication Check" "POST" "/dedup/check" \
'{"content": "Test content for deduplication"}'

# Test 10: Dedup Stats
test_endpoint "Dedup Statistics" "GET" "/dedup/stats"

# Test 11: Export Memories (CSV)
test_endpoint "Export CSV" "POST" "/api/v1/memories/export" \
'{"format": "csv", "limit": 10}'

# Test 12: Export Memories (JSON)  
test_endpoint "Export JSON" "POST" "/api/v1/memories/export" \
'{"format": "json", "limit": 5}'

# Test 13: Invalid Endpoint (Error Handling)
test_endpoint "Invalid Endpoint" "GET" "/non-existent" "" "404"

# Test 14: Invalid Memory Creation (Error Handling)
test_endpoint "Invalid Memory Creation" "POST" "/memories" \
'{"invalid_field": "test"}' "422"

# Test 15: Invalid Query (Error Handling)
test_endpoint "Invalid Query Limit" "POST" "/memories/query" \
'{"query": "test", "limit": "invalid"}' "422"

# Finalize report
sed -i '$ s/,$//' $REPORT_FILE  # Remove last comma
echo "  ]," >> $REPORT_FILE
echo "  \"completed_at\": \"$(date -Iseconds)\"" >> $REPORT_FILE
echo "}" >> $REPORT_FILE

echo "=========================================="
echo "Testing completed!"
echo "Report saved to: $REPORT_FILE"
echo ""

# Generate summary
total_tests=$(grep -c '"test_name"' $REPORT_FILE)
passed_tests=$(grep -c '"success": true' $REPORT_FILE)
failed_tests=$((total_tests - passed_tests))

echo "Test Summary:"
echo "- Total Tests: $total_tests"
echo "- Passed: $passed_tests"
echo "- Failed: $failed_tests"
echo "- Success Rate: $(echo "scale=1; $passed_tests * 100 / $total_tests" | bc -l)%"
echo ""
echo "See $REPORT_FILE for detailed results"