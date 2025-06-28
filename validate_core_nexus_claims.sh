#!/bin/bash

# Core Nexus Claims Validation Test Suite
# Purpose: Objectively validate all claims made in the optimization report
# Date: $(date)

echo "🧪 Core Nexus Claims Validation Test Suite"
echo "=========================================="
echo ""

# Define URLs from the claims
CORE_MEMORY_API="https://core-nexus-memory-service.onrender.com"
JARVIS_API="https://jarvis-ai-agent-aa4m.onrender.com"

# Test results storage
RESULTS_FILE="validation_results_$(date +%Y%m%d_%H%M%S).json"
PERFORMANCE_LOG="performance_log_$(date +%Y%m%d_%H%M%S).txt"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Initialize results
echo "{" > $RESULTS_FILE
echo "  \"test_timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"," >> $RESULTS_FILE
echo "  \"claims_tested\": {" >> $RESULTS_FILE

# Function to test endpoint with timing
test_endpoint() {
    local url=$1
    local description=$2
    local expected_status=${3:-200}
    
    echo -e "${BLUE}Testing:${NC} $description"
    echo -e "${BLUE}URL:${NC} $url"
    
    # Measure response time and get status
    start_time=$(date +%s%N)
    response=$(curl -s -w "%{http_code},%{time_total}" -o /tmp/curl_response.tmp "$url" 2>/dev/null)
    end_time=$(date +%s%N)
    
    # Parse response
    if [[ $response == *","* ]]; then
        status_code=$(echo "$response" | cut -d',' -f1)
        response_time=$(echo "$response" | cut -d',' -f2)
    else
        status_code="ERROR"
        response_time="N/A"
    fi
    
    # Calculate response time in ms
    if [[ $response_time != "N/A" ]]; then
        response_time_ms=$(echo "$response_time * 1000" | bc)
    else
        response_time_ms="N/A"
    fi
    
    # Get response body
    response_body=$(cat /tmp/curl_response.tmp 2>/dev/null || echo "")
    
    # Determine result
    if [[ $status_code == $expected_status ]]; then
        echo -e "${GREEN}✅ PASS${NC} - Status: $status_code, Time: ${response_time_ms}ms"
        result="PASS"
    else
        echo -e "${RED}❌ FAIL${NC} - Status: $status_code, Expected: $expected_status"
        result="FAIL"
    fi
    
    # Log performance
    echo "$(date): $description - Status: $status_code, Time: ${response_time_ms}ms" >> $PERFORMANCE_LOG
    
    echo "    \"$(echo "$description" | tr ' ' '_' | tr '[:upper:]' '[:lower:]')\": {" >> $RESULTS_FILE
    echo "      \"url\": \"$url\"," >> $RESULTS_FILE
    echo "      \"status_code\": \"$status_code\"," >> $RESULTS_FILE
    echo "      \"response_time_ms\": \"$response_time_ms\"," >> $RESULTS_FILE
    echo "      \"result\": \"$result\"," >> $RESULTS_FILE
    echo "      \"response_size_bytes\": $(echo -n "$response_body" | wc -c)," >> $RESULTS_FILE
    echo "      \"response_preview\": \"$(echo "$response_body" | head -c 200 | tr '\n' ' ')\"" >> $RESULTS_FILE
    echo "    }," >> $RESULTS_FILE
    
    echo ""
    return $([ "$result" = "PASS" ] && echo 0 || echo 1)
}

# Function to test with JSON data
test_post_endpoint() {
    local url=$1
    local description=$2
    local json_data=$3
    local expected_status=${4:-200}
    
    echo -e "${BLUE}Testing:${NC} $description"
    echo -e "${BLUE}URL:${NC} $url"
    echo -e "${BLUE}Data:${NC} $json_data"
    
    start_time=$(date +%s%N)
    response=$(curl -s -w "%{http_code},%{time_total}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$json_data" \
        -o /tmp/curl_response.tmp \
        "$url" 2>/dev/null)
    end_time=$(date +%s%N)
    
    if [[ $response == *","* ]]; then
        status_code=$(echo "$response" | cut -d',' -f1)
        response_time=$(echo "$response" | cut -d',' -f2)
    else
        status_code="ERROR"
        response_time="N/A"
    fi
    
    if [[ $response_time != "N/A" ]]; then
        response_time_ms=$(echo "$response_time * 1000" | bc)
    else
        response_time_ms="N/A"
    fi
    
    response_body=$(cat /tmp/curl_response.tmp 2>/dev/null || echo "")
    
    if [[ $status_code == $expected_status ]]; then
        echo -e "${GREEN}✅ PASS${NC} - Status: $status_code, Time: ${response_time_ms}ms"
        result="PASS"
    else
        echo -e "${RED}❌ FAIL${NC} - Status: $status_code, Expected: $expected_status"
        result="FAIL"
    fi
    
    echo "$(date): $description - Status: $status_code, Time: ${response_time_ms}ms" >> $PERFORMANCE_LOG
    
    echo "    \"$(echo "$description" | tr ' ' '_' | tr '[:upper:]' '[:lower:]')\": {" >> $RESULTS_FILE
    echo "      \"url\": \"$url\"," >> $RESULTS_FILE
    echo "      \"method\": \"POST\"," >> $RESULTS_FILE
    echo "      \"status_code\": \"$status_code\"," >> $RESULTS_FILE
    echo "      \"response_time_ms\": \"$response_time_ms\"," >> $RESULTS_FILE
    echo "      \"result\": \"$result\"," >> $RESULTS_FILE
    echo "      \"response_preview\": \"$(echo "$response_body" | head -c 200 | tr '\n' ' ')\"" >> $RESULTS_FILE
    echo "    }," >> $RESULTS_FILE
    
    echo ""
    return $([ "$result" = "PASS" ] && echo 0 || echo 1)
}

# START TESTING
echo "🔍 CLAIM VALIDATION TESTS"
echo "========================"
echo ""

# Test 1: Basic Connectivity
echo -e "${YELLOW}📡 Testing Basic Connectivity${NC}"
echo "-----------------------------"
test_endpoint "$CORE_MEMORY_API/health" "Core Memory API Health Check"
test_endpoint "$JARVIS_API/health" "JARVIS AI Agent Health Check"

# Test 2: Core Memory API Endpoints
echo -e "${YELLOW}🧠 Testing Core Memory API Endpoints${NC}"
echo "------------------------------------"
test_endpoint "$CORE_MEMORY_API/memories" "Get All Memories"
test_endpoint "$CORE_MEMORY_API/memories?limit=1" "Get Memories with Limit"
test_endpoint "$CORE_MEMORY_API/metrics" "Prometheus Metrics Endpoint"

# Test 3: Memory Count Validation
echo -e "${YELLOW}📊 Testing Memory Count Claim (1,643+ memories)${NC}"
echo "-----------------------------------------------"
memories_response=$(curl -s "$CORE_MEMORY_API/memories" 2>/dev/null)
if [[ $? -eq 0 ]] && [[ -n "$memories_response" ]]; then
    # Try to extract count from response
    memory_count=$(echo "$memories_response" | grep -o '"total":[0-9]*' | grep -o '[0-9]*' || echo "")
    if [[ -z "$memory_count" ]]; then
        # Try alternative extraction methods
        memory_count=$(echo "$memories_response" | jq '.total // .count // (.memories | length) // 0' 2>/dev/null || echo "0")
    fi
    
    echo "Detected memory count: $memory_count"
    if [[ $memory_count -ge 1643 ]]; then
        echo -e "${GREEN}✅ PASS${NC} - Memory count ($memory_count) meets claim (≥1,643)"
        memory_count_result="PASS"
    else
        echo -e "${RED}❌ FAIL${NC} - Memory count ($memory_count) below claim (≥1,643)"
        memory_count_result="FAIL"
    fi
else
    echo -e "${RED}❌ FAIL${NC} - Could not retrieve memory count"
    memory_count_result="FAIL"
    memory_count="N/A"
fi

echo "    \"memory_count_validation\": {" >> $RESULTS_FILE
echo "      \"claimed_count\": \"≥1,643\"," >> $RESULTS_FILE
echo "      \"actual_count\": \"$memory_count\"," >> $RESULTS_FILE
echo "      \"result\": \"$memory_count_result\"" >> $RESULTS_FILE
echo "    }," >> $RESULTS_FILE

echo ""

# Test 4: POST Memory Endpoint
echo -e "${YELLOW}💾 Testing Memory Storage (POST /memories)${NC}"
echo "--------------------------------------------"
test_memory_data='{
  "content": "Test memory for validation - Core Nexus curl test at '$(date)'",
  "metadata": {
    "source": "curl_validation_test",
    "test_timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
  }
}'
test_post_endpoint "$CORE_MEMORY_API/memories" "Store New Memory" "$test_memory_data" 201

# Test 5: Query Functionality
echo -e "${YELLOW}🔍 Testing Query Functionality${NC}"
echo "------------------------------"
query_data='{"query": "test", "limit": 5}'
test_post_endpoint "$CORE_MEMORY_API/query" "Memory Search Query" "$query_data"

# Test 6: Performance Measurement
echo -e "${YELLOW}⚡ Performance Testing (Claimed ~850ms average)${NC}"
echo "-----------------------------------------------"
echo "Running 5 performance tests..."

total_time=0
successful_requests=0

for i in {1..5}; do
    echo "Performance Test $i/5..."
    start_time=$(date +%s%N)
    response=$(curl -s -w "%{http_code}" -o /dev/null "$CORE_MEMORY_API/memories?limit=10" 2>/dev/null)
    end_time=$(date +%s%N)
    
    if [[ $response == "200" ]]; then
        request_time=$(( (end_time - start_time) / 1000000 )) # Convert to ms
        total_time=$((total_time + request_time))
        successful_requests=$((successful_requests + 1))
        echo "  Request $i: ${request_time}ms"
    else
        echo "  Request $i: FAILED (Status: $response)"
    fi
done

if [[ $successful_requests -gt 0 ]]; then
    average_time=$((total_time / successful_requests))
    echo ""
    echo "Performance Results:"
    echo "  Successful requests: $successful_requests/5"
    echo "  Average response time: ${average_time}ms"
    echo "  Claimed average: ~850ms"
    
    if [[ $average_time -le 1000 ]]; then
        echo -e "  ${GREEN}✅ PASS${NC} - Performance within acceptable range"
        performance_result="PASS"
    else
        echo -e "  ${YELLOW}⚠️  WARN${NC} - Performance slower than optimal"
        performance_result="WARN"
    fi
else
    echo -e "  ${RED}❌ FAIL${NC} - No successful performance tests"
    performance_result="FAIL"
    average_time="N/A"
fi

echo "    \"performance_validation\": {" >> $RESULTS_FILE
echo "      \"claimed_avg_ms\": \"~850\"," >> $RESULTS_FILE
echo "      \"measured_avg_ms\": \"$average_time\"," >> $RESULTS_FILE
echo "      \"successful_requests\": \"$successful_requests\"," >> $RESULTS_FILE
echo "      \"result\": \"$performance_result\"" >> $RESULTS_FILE
echo "    }" >> $RESULTS_FILE

echo ""

# Close JSON
echo "  }" >> $RESULTS_FILE
echo "}" >> $RESULTS_FILE

# Generate Summary Report
echo -e "${YELLOW}📋 VALIDATION SUMMARY${NC}"
echo "===================="
echo ""

echo "Test Results Summary:"
grep -o '"result": "[^"]*"' $RESULTS_FILE | cut -d'"' -f4 | sort | uniq -c

echo ""
echo "Detailed results saved to: $RESULTS_FILE"
echo "Performance log saved to: $PERFORMANCE_LOG"

echo ""
echo -e "${BLUE}🎯 OBJECTIVE ASSESSMENT:${NC}"

# Count results
total_tests=$(grep -c '"result":' $RESULTS_FILE)
passed_tests=$(grep -c '"result": "PASS"' $RESULTS_FILE)
failed_tests=$(grep -c '"result": "FAIL"' $RESULTS_FILE)

echo "  Total Tests: $total_tests"
echo "  Passed: $passed_tests"
echo "  Failed: $failed_tests"

if [[ $failed_tests -eq 0 ]]; then
    echo -e "  ${GREEN}✅ VERDICT: Claims VALIDATED${NC}"
    echo "  All tested claims appear to be accurate."
elif [[ $failed_tests -lt $((total_tests / 2)) ]]; then
    echo -e "  ${YELLOW}⚠️  VERDICT: Claims PARTIALLY VALIDATED${NC}"
    echo "  Most claims validated, some issues detected."
else
    echo -e "  ${RED}❌ VERDICT: Claims DISPUTED${NC}"
    echo "  Significant issues found with reported claims."
fi

echo ""
echo "🔍 For detailed analysis, review: $RESULTS_FILE"

# Cleanup
rm -f /tmp/curl_response.tmp

exit 0