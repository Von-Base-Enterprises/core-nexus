# Core Nexus Memory Service - Comprehensive Test Report
**Generated**: 2025-06-12T09:33:37.756277+00:00
**Service URL**: https://core-nexus-memory.onrender.com
**Overall Status**: **CRITICAL**

## Summary
- Total Tests: 8
- Passed: 1
- Failed: 5
- Warnings: 0

## Test Results

### Api Accessibility ❌
**Status**: FAILED
**Message**: API is not accessible

### Health Endpoint ❌
**Status**: FAILED
**Message**: Health endpoint failed (status: No response)

### Memory Storage ❌
**Status**: FAILED
**Message**: 5 storage tests failed
**Test Cases**:
- basic_storage: ❌ Storage failed (status: No response)
- special_characters: ❌ Failed to store memory with special characters
- large_content: ❌ Failed to store large content
- minimal_memory: ❌ Failed to store memory without metadata
- empty_content: ❌ Unexpected response to empty content

### Memory Retrieval ❌
**Status**: FAILED
**Message**: 3 retrieval tests failed
**Test Cases**:
- get_all_memories: ❌ Failed to retrieve memories
- get_nonexistent_memory: ❌ Improper handling of non-existent memory
- get_with_limit: ❌ Failed to retrieve memories with limit

### Vector Search ❌
**Status**: FAILED
**Message**: 1 vector search tests failed
**Test Cases**:
- vector_search_setup: ❌ Failed to create test memory for search

### Deduplication ✅
**Status**: PASSED
**Message**: Deduplication tests completed
**Test Cases**:
- deduplication_setup: ❌ Failed to create test memories for deduplication

### Opentelemetry ℹ️
**Status**: INFO
**Message**: Metrics endpoint not available or not exposed

### Knowledge Graph ℹ️
**Status**: INFO
**Message**: Knowledge graph features not enabled or not exposed

## Performance Metrics

### /
- Average Response Time: 0.175s
- Max Response Time: 0.175s
- Min Response Time: 0.175s
- Total Requests: 1

### /health
- Average Response Time: 0.215s
- Max Response Time: 0.215s
- Min Response Time: 0.215s
- Total Requests: 1

### /memories
- Average Response Time: 0.224s
- Max Response Time: 0.348s
- Min Response Time: 0.167s
- Total Requests: 9

### /memories/56d4b193-11ce-4845-81a1-d316f832e14b
- Average Response Time: 0.467s
- Max Response Time: 0.467s
- Min Response Time: 0.467s
- Total Requests: 1

### /memories?limit=5
- Average Response Time: 0.195s
- Max Response Time: 0.195s
- Min Response Time: 0.195s
- Total Requests: 1

### /metrics
- Average Response Time: 0.205s
- Max Response Time: 0.205s
- Min Response Time: 0.205s
- Total Requests: 1

### /graph/entities
- Average Response Time: 0.205s
- Max Response Time: 0.205s
- Min Response Time: 0.205s
- Total Requests: 1

### /graph/relationships
- Average Response Time: 0.411s
- Max Response Time: 0.411s
- Min Response Time: 0.411s
- Total Requests: 1

### /graph/query
- Average Response Time: 0.203s
- Max Response Time: 0.203s
- Min Response Time: 0.203s
- Total Requests: 1

## Recommendations

### 🚨 CRITICAL Priority
Critical services failing: api_accessibility, health_endpoint, memory_storage, vector_search. Immediate action required.

### ⚠️ HIGH Priority
Database connectivity issues detected. Check pgvector configuration.

### 💡 LOW Priority
OpenTelemetry metrics not fully configured. Consider enabling for better observability.
