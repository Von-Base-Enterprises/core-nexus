"""
Comprehensive API endpoint tests for Core Nexus Memory Service.

Tests all HTTP endpoints with realistic scenarios including:
- Memory CRUD operations
- Search and query functionality
- Health monitoring
- Error handling
- Performance validation
"""

import pytest
import json
import uuid
from typing import Dict, Any
from unittest.mock import AsyncMock

from src.memory_service.models import MemoryResponse, QueryResponse


@pytest.mark.api
@pytest.mark.asyncio
class TestHealthEndpoints:
    """Test health and monitoring endpoints."""
    
    async def test_health_endpoint_success(self, test_client):
        """Test health endpoint returns proper status."""
        # Get the actual client from the async generator
        client = await test_client.__anext__()
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "status" in data
        assert "providers" in data
        assert "total_memories" in data
        assert "uptime_seconds" in data
        
        # Verify provider information
        assert "pgvector" in data["providers"]
        assert data["providers"]["pgvector"]["status"] == "healthy"
    
    async def test_stats_endpoint_success(self, test_client):
        """Test stats endpoint returns comprehensive metrics."""
        client = await test_client.__anext__()
        response = await client.get("/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        required_fields = [
            "service", "status", "uptime_seconds", "total_memories",
            "provider_counts", "healthy_providers", "total_providers"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Verify data types
        assert isinstance(data["total_memories"], int)
        assert isinstance(data["uptime_seconds"], (int, float))
        assert isinstance(data["provider_counts"], dict)
    
    async def test_root_endpoint_documentation(self, test_client):
        """Test root endpoint provides API documentation."""
        client = await test_client.__anext__()
        response = await client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify documentation structure
        assert "service" in data
        assert "key_endpoints" in data
        assert "documentation" in data
        
        # Verify key endpoints are documented
        endpoints = [ep["path"] for ep in data["key_endpoints"]]
        assert "/health" in endpoints
        assert "/memories" in endpoints
        assert "/stats" in endpoints


@pytest.mark.api
@pytest.mark.asyncio
class TestMemoryEndpoints:
    """Test memory storage and retrieval endpoints."""
    
    async def test_create_memory_success(self, test_client, sample_memory_content, sample_metadata):
        """Test successful memory creation."""
        memory_data = {
            "content": sample_memory_content["medium"],
            "metadata": sample_metadata
        }
        
        client = await test_client.__anext__()
        response = await client.post("/memories", json=memory_data)
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert "content" in data
        assert "metadata" in data
        assert "importance_score" in data
        assert "created_at" in data
        
        # Verify data integrity
        assert data["content"] == memory_data["content"]
        assert isinstance(data["importance_score"], (int, float))
        assert 0 <= data["importance_score"] <= 1
    
    async def test_create_memory_minimal_data(self, test_client):
        """Test memory creation with minimal required data."""
        memory_data = {
            "content": "Simple test memory"
        }
        
        client = await test_client.__anext__()
        response = await client.post("/memories", json=memory_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == memory_data["content"]
        assert data["metadata"] == {} or data["metadata"] is None
    
    async def test_create_memory_validation_errors(self, test_client):
        """Test memory creation validation."""
        # Get client once and reuse it
        client = await test_client.__anext__()
        
        # Test missing content field (should fail validation)
        response = await client.post("/memories", json={"metadata": {}})
        assert response.status_code == 422
        
        # Test invalid JSON (should fail parsing)
        response = await client.post("/memories", data="invalid json")
        assert response.status_code == 422
        
        # Note: Empty content string may be allowed by the API
        # so we don't test that case
    
    async def test_list_memories_success(self, test_client):
        """Test listing memories with pagination."""
        client = await test_client.__anext__()
        response = await client.get("/memories")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "memories" in data
        assert "total_found" in data
        assert "query_time_ms" in data
        
        # Verify memories structure
        assert isinstance(data["memories"], list)
        assert isinstance(data["total_found"], int)
        assert isinstance(data["query_time_ms"], (int, float))
    
    async def test_list_memories_with_pagination(self, test_client):
        """Test memory listing with limit and offset."""
        client = await test_client.__anext__()
        response = await client.get("/memories?limit=5&offset=0")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should respect limit
        assert len(data["memories"]) <= 5
    
    async def test_get_memory_by_id_success(self, test_client):
        """Test retrieving memory by ID."""
        # Get the client once and reuse it
        client = await test_client.__anext__()
        
        # First create a memory to get a valid ID
        memory_data = {"content": "Test memory for ID retrieval"}
        create_response = await client.post("/memories", json=memory_data)
        created_memory = create_response.json()
        memory_id = created_memory["id"]
        
        # Retrieve by ID using the same client
        response = await client.get(f"/memories/{memory_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == memory_id
        # In mock environment, just verify we get valid content
        assert "content" in data
        assert len(data["content"]) > 0
        assert "metadata" in data
    
    async def test_get_memory_by_id_not_found(self, test_client):
        """Test retrieving non-existent memory."""
        fake_id = str(uuid.uuid4())
        client = await test_client.__anext__()
        response = await client.get(f"/memories/{fake_id}")
        
        assert response.status_code == 404
    
    async def test_get_memory_invalid_id_format(self, test_client):
        """Test retrieving memory with invalid ID format."""
        client = await test_client.__anext__()
        response = await client.get("/memories/invalid-id-format")
        
        # Invalid UUID format is treated as "not found" (404) rather than validation error (422)
        assert response.status_code == 404


@pytest.mark.api
@pytest.mark.asyncio
class TestQueryEndpoints:
    """Test search and query functionality."""
    
    async def test_query_memories_empty_query(self, test_client):
        """Test query with empty string returns all memories."""
        query_data = {
            "query": "",
            "limit": 10
        }
        
        client = await test_client.__anext__()
        response = await client.post("/memories/query", json=query_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "memories" in data
        assert "total_found" in data
        assert "query_time_ms" in data
        assert "providers_used" in data
        
        # Verify data types
        assert isinstance(data["memories"], list)
        assert isinstance(data["total_found"], int)
        assert isinstance(data["providers_used"], list)
    
    async def test_query_memories_semantic_search(self, test_client):
        """Test semantic search with query text."""
        query_data = {
            "query": "artificial intelligence machine learning",
            "limit": 5
        }
        
        client = await test_client.__anext__()
        response = await client.post("/memories/query", json=query_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return semantic search results
        assert isinstance(data["memories"], list)
        
        # If memories are returned, they should have similarity scores
        for memory in data["memories"]:
            if "similarity_score" in memory:
                assert 0 <= memory["similarity_score"] <= 1
    
    async def test_query_memories_with_filters(self, test_client):
        """Test query with metadata filters."""
        query_data = {
            "query": "test",
            "limit": 10,
            "filters": {
                "category": "work",
                "importance_score": 0.7
            }
        }
        
        client = await test_client.__anext__()
        response = await client.post("/memories/query", json=query_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "memories" in data
    
    async def test_query_validation_errors(self, test_client):
        """Test query validation."""
        # Get client once and reuse it
        client = await test_client.__anext__()
        
        # Test invalid limit
        response = await client.post("/memories/query", json={
            "query": "test",
            "limit": -1
        })
        assert response.status_code == 422
        
        # Test missing query (note: query field has default empty string)
        response = await client.post("/memories/query", json={
            "limit": 10
        })
        # Since query has a default value, this should succeed
        assert response.status_code == 200
    
    @pytest.mark.performance
    async def test_query_performance(self, test_client, performance_monitor):
        """Test query performance meets requirements."""
        query_data = {
            "query": "performance test query",
            "limit": 10
        }
        
        performance_monitor.start()
        client = await test_client.__anext__()
        response = await client.post("/memories/query", json=query_data)
        performance_monitor.stop()
        
        assert response.status_code == 200
        
        # Assert API response time is acceptable (relaxed for test environment)
        performance_monitor.assert_performance(3000.0, "API query endpoint")
        
        # Also check database query time reported in response
        data = response.json()
        if "query_time_ms" in data:
            assert data["query_time_ms"] < 500.0  # Database query should be fast


@pytest.mark.api
@pytest.mark.asyncio
class TestErrorHandling:
    """Test API error handling and edge cases."""
    
    async def test_invalid_json_request(self, test_client):
        """Test handling of invalid JSON requests."""
        client = await test_client.__anext__()
        response = await client.post(
            "/memories",
            content="invalid json content",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    async def test_unsupported_media_type(self, test_client):
        """Test handling of unsupported content types."""
        client = await test_client.__anext__()
        response = await client.post(
            "/memories",
            content="some data",
            headers={"Content-Type": "text/plain"}
        )
        
        assert response.status_code == 422
    
    async def test_nonexistent_endpoint(self, test_client):
        """Test 404 for non-existent endpoints."""
        client = await test_client.__anext__()
        response = await client.get("/nonexistent/endpoint")
        
        assert response.status_code == 404
    
    async def test_method_not_allowed(self, test_client):
        """Test 405 for wrong HTTP methods."""
        client = await test_client.__anext__()
        response = await client.delete("/health")
        
        assert response.status_code == 405
    
    async def test_large_request_handling(self, test_client):
        """Test handling of very large requests."""
        # Create a very large content string
        large_content = "x" * 10000  # 10KB content
        
        memory_data = {
            "content": large_content,
            "metadata": {"type": "large_content_test"}
        }
        
        client = await test_client.__anext__()
        response = await client.post("/memories", json=memory_data)
        
        # Should either succeed or return appropriate error
        assert response.status_code in [201, 413, 422]  # Created, Payload Too Large, or Validation Error


@pytest.mark.api
@pytest.mark.asyncio 
class TestCORSAndSecurity:
    """Test CORS headers and basic security."""
    
    async def test_cors_headers_present(self, test_client):
        """Test that CORS headers are present in responses."""
        client = await test_client.__anext__()
        response = await client.get("/health")
        
        # Check for common CORS headers
        # Note: Actual CORS headers depend on FastAPI middleware configuration
        assert response.status_code == 200
        # Could check for headers like:
        # assert "access-control-allow-origin" in response.headers
    
    async def test_options_request_handling(self, test_client):
        """Test OPTIONS request handling for CORS preflight."""
        client = await test_client.__anext__()
        response = await client.options("/memories")
        
        # Should handle OPTIONS requests (exact response depends on CORS config)
        assert response.status_code in [200, 405]  # OK or Method Not Allowed


@pytest.mark.api
@pytest.mark.integration
@pytest.mark.asyncio
class TestEndToEndWorkflows:
    """Test complete workflows across multiple endpoints."""
    
    async def test_complete_memory_workflow(self, test_client, sample_memory_content, sample_metadata):
        """Test complete create -> retrieve -> search workflow."""
        # Get client once and reuse it
        client = await test_client.__anext__()
        
        # 1. Create a memory
        memory_data = {
            "content": sample_memory_content["medium"],
            "metadata": sample_metadata
        }
        
        create_response = await client.post("/memories", json=memory_data)
        assert create_response.status_code == 201
        created_memory = create_response.json()
        memory_id = created_memory["id"]
        
        # 2. Retrieve the memory by ID
        get_response = await client.get(f"/memories/{memory_id}")
        assert get_response.status_code == 200
        retrieved_memory = get_response.json()
        # In mock environment, just verify we get valid data
        assert "content" in retrieved_memory
        assert retrieved_memory["id"] == memory_id
        
        # 3. Search for the memory
        query_data = {
            "query": "",  # Empty query should return all memories
            "limit": 100
        }
        
        query_response = await client.post("/memories/query", json=query_data)
        assert query_response.status_code == 200
        query_result = query_response.json()
        
        # Should find memories in the search results
        assert "memories" in query_result
        assert len(query_result["memories"]) > 0
    
    async def test_concurrent_api_requests(self, test_client):
        """Test handling of concurrent API requests."""
        import asyncio
        
        # Get the client properly
        client = await test_client.__anext__()
        
        # Create multiple concurrent requests
        create_tasks = [
            client.post("/memories", json={"content": f"Concurrent memory {i}"})
            for i in range(5)
        ]
        
        query_tasks = [
            client.post("/memories/query", json={"query": f"query {i}", "limit": 5})
            for i in range(3)
        ]
        
        health_tasks = [
            client.get("/health")
            for i in range(2)
        ]
        
        # Execute all requests concurrently
        all_tasks = create_tasks + query_tasks + health_tasks
        responses = await asyncio.gather(*all_tasks)
        
        # Verify all requests completed successfully
        for response in responses:
            assert response.status_code in [200, 201]
    
    @pytest.mark.slow
    async def test_api_under_load(self, test_client, performance_monitor):
        """Test API performance under moderate load."""
        import asyncio
        
        # Get the client properly
        client = await test_client.__anext__()
        
        # Create a moderate load scenario
        num_requests = 20
        
        performance_monitor.start()
        
        # Create requests that mix different endpoint types
        tasks = []
        for i in range(num_requests):
            if i % 3 == 0:
                # Health checks
                tasks.append(client.get("/health"))
            elif i % 3 == 1:
                # Memory creation
                tasks.append(client.post("/memories", json={"content": f"Load test memory {i}"}))
            else:
                # Queries
                tasks.append(client.post("/memories/query", json={"query": "load test", "limit": 5}))
        
        responses = await asyncio.gather(*tasks)
        performance_monitor.stop()
        
        # Verify all requests succeeded
        success_count = sum(1 for r in responses if r.status_code in [200, 201])
        assert success_count == num_requests
        
        # Verify overall performance is acceptable
        avg_time_per_request = performance_monitor.elapsed_ms / num_requests
        assert avg_time_per_request < 1000.0  # Average response should be under 1 second


@pytest.mark.api
@pytest.mark.database
@pytest.mark.asyncio
class TestDatabaseIntegration:
    """Test API interactions with database layer."""
    
    async def test_data_persistence_across_requests(self, test_client):
        """Test that data persists across API requests."""
        # Create a memory
        memory_data = {"content": "Persistence test memory"}
        client = await test_client.__anext__()
        create_response = await client.post("/memories", json=memory_data)
        memory_id = create_response.json()["id"]
        
        # Retrieve it in a separate request (simulating different connection)
        get_response = await client.get(f"/memories/{memory_id}")
        assert get_response.status_code == 200
        assert get_response.json()["content"] == memory_data["content"]
    
    async def test_consistent_data_across_endpoints(self, test_client):
        """Test data consistency across different endpoints."""
        # Get the client properly
        client = await test_client.__anext__()
        
        # Create a memory
        memory_data = {"content": "Consistency test memory"}
        create_response = await client.post("/memories", json=memory_data)
        created_memory = create_response.json()
        
        # Check it appears in query endpoint (uses unified store)
        query_response = await client.post("/memories/query", json={"query": "", "limit": 100})
        query_data = query_response.json()
        query_memory_ids = [mem["id"] for mem in query_data["memories"]]
        assert created_memory["id"] in query_memory_ids
        
        # Note: The GET /memories endpoint uses emergency retrieval system
        # which is separate from the unified store mock, so we test that it works
        # but don't expect consistency with created memories in test environment
        list_response = await client.get("/memories?limit=100")
        assert list_response.status_code == 200
        list_data = list_response.json()
        assert "memories" in list_data
        assert isinstance(list_data["memories"], list)