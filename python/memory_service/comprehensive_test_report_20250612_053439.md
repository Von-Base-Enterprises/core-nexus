# Core Nexus Memory Service - Comprehensive Test Report
**Generated**: 2025-06-12T09:34:33.055077+00:00
**Service URL**: https://core-nexus-memory-service.onrender.com
**Overall Status**: **CRITICAL**

## Summary
- Total Tests: 9
- Passed: 2
- Failed: 4
- Warnings: 1

## Test Results

### Api Accessibility ❌
**Status**: FAILED
**Message**: API is not accessible

### Health Endpoint ✅
**Status**: PASSED
**Message**: Health endpoint working

### Database Connectivity ⚠️
**Status**: WARNING
**Message**: Database status unclear from health check

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
**Message**: 2 retrieval tests failed
**Test Cases**:
- get_all_memories: ✅ Retrieved 6 memories
- get_nonexistent_memory: ❌ Improper handling of non-existent memory
- get_with_limit: ❌ Limit not respected (returned 6 memories)

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
- Average Response Time: 0.232s
- Max Response Time: 0.232s
- Min Response Time: 0.232s
- Total Requests: 1

### /health
- Average Response Time: 0.620s
- Max Response Time: 0.620s
- Min Response Time: 0.620s
- Total Requests: 1

### /memories
- Average Response Time: 0.489s
- Max Response Time: 2.734s
- Min Response Time: 0.178s
- Total Requests: 9

### /memories/1e93adc5-bd72-478b-a310-cf79fdb4ea8e
- Average Response Time: 0.176s
- Max Response Time: 0.176s
- Min Response Time: 0.176s
- Total Requests: 1

### /memories?limit=5
- Average Response Time: 0.250s
- Max Response Time: 0.250s
- Min Response Time: 0.250s
- Total Requests: 1

### /metrics
- Average Response Time: 0.194s
- Max Response Time: 0.194s
- Min Response Time: 0.194s
- Total Requests: 1

### /graph/entities
- Average Response Time: 0.182s
- Max Response Time: 0.182s
- Min Response Time: 0.182s
- Total Requests: 1

### /graph/relationships
- Average Response Time: 0.187s
- Max Response Time: 0.187s
- Min Response Time: 0.187s
- Total Requests: 1

### /graph/query
- Average Response Time: 0.187s
- Max Response Time: 0.187s
- Min Response Time: 0.187s
- Total Requests: 1

## Recommendations

### 🚨 CRITICAL Priority
Critical services failing: api_accessibility, memory_storage, vector_search. Immediate action required.

### ⚠️ HIGH Priority
Database connectivity issues detected. Check pgvector configuration.

### 💡 LOW Priority
OpenTelemetry metrics not fully configured. Consider enabling for better observability.
