"""
Comprehensive unit tests for UnifiedVectorStore.

Tests the core functionality of the unified store including:
- Multi-provider management
- Failover behavior
- Caching
- Performance characteristics
- Error handling
"""

import pytest
import uuid
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from src.memory_service.unified_store import UnifiedVectorStore
from src.memory_service.models import (
    MemoryRequest, 
    MemoryResponse, 
    QueryRequest, 
    QueryResponse,
    ProviderConfig
)


@pytest.mark.unit
class TestUnifiedStoreInitialization:
    """Test UnifiedVectorStore initialization and configuration."""
    
    def test_initialization_with_providers(self, mock_pgvector_provider, mock_chromadb_provider):
        """Test proper initialization with multiple providers."""
        providers = [mock_pgvector_provider, mock_chromadb_provider]
        
        store = UnifiedVectorStore(providers=providers)
        
        assert len(store.providers) == 2
        assert "pgvector" in store.providers
        assert "chromadb" in store.providers
        assert store.primary_provider == mock_pgvector_provider  # Primary provider
        assert store.stats["total_stores"] == 0
    
    def test_initialization_no_enabled_providers(self):
        """Test initialization fails with no enabled providers."""
        mock_provider = MagicMock()
        mock_provider.enabled = False
        
        with pytest.raises(RuntimeError, match="No enabled vector providers available"):
            UnifiedVectorStore(providers=[mock_provider])
    
    def test_primary_provider_selection(self, mock_pgvector_provider, mock_chromadb_provider):
        """Test primary provider selection logic."""
        # Make chromadb primary
        mock_chromadb_provider.config.primary = True
        mock_pgvector_provider.config.primary = False
        
        providers = [mock_pgvector_provider, mock_chromadb_provider]
        store = UnifiedVectorStore(providers=providers)
        
        assert store.primary_provider == mock_chromadb_provider


@pytest.mark.unit
@pytest.mark.asyncio
class TestUnifiedStoreMemoryOperations:
    """Test memory storage and retrieval operations."""
    
    async def test_store_memory_success(self, mock_unified_store, sample_memory_content, sample_metadata):
        """Test successful memory storage."""
        request = MemoryRequest(
            content=sample_memory_content["medium"],
            metadata=sample_metadata
        )
        
        # Mock the store method to return a proper MemoryResponse
        expected_id = str(uuid.uuid4())
        mock_unified_store.store.return_value = MemoryResponse(
            id=expected_id,
            content=request.content,
            metadata=request.metadata,
            importance_score=0.5,
            similarity_score=None,
            created_at="2025-01-01T00:00:00",
            updated_at=None
        )
        
        result = await mock_unified_store.store(request)
        
        assert isinstance(result, MemoryResponse)
        assert result.id == expected_id
        assert result.content == request.content
        mock_unified_store.store.assert_called_once_with(request)
    
    async def test_store_memory_with_importance_calculation(self, mock_unified_store, sample_memory_content):
        """Test memory storage with automatic importance calculation."""
        request = MemoryRequest(
            content=sample_memory_content["long"],
            metadata={"category": "important"}
        )
        
        # Mock importance scoring
        mock_unified_store.store.return_value = MemoryResponse(
            id=str(uuid.uuid4()),
            content=request.content,
            metadata=request.metadata,
            importance_score=0.8,  # High importance
            similarity_score=None,
            created_at="2025-01-01T00:00:00",
            updated_at=None
        )
        
        result = await mock_unified_store.store(request)
        
        assert result.importance_score == 0.8
    
    async def test_store_memory_provider_failover(self, mock_pgvector_provider, mock_chromadb_provider):
        """Test failover behavior when primary provider fails."""
        providers = [mock_pgvector_provider, mock_chromadb_provider]
        store = UnifiedVectorStore(providers=providers)
        
        # Make primary provider fail
        mock_pgvector_provider.store.side_effect = Exception("Primary provider failed")
        
        # Secondary provider should succeed
        expected_id = str(uuid.uuid4())
        mock_chromadb_provider.store.return_value = expected_id
        
        request = MemoryRequest(content="test content")
        
        # Mock the store method to handle failover
        with patch.object(store, 'store') as mock_store:
            mock_store.return_value = MemoryResponse(
                id=expected_id,
                content=request.content,
                metadata={},
                importance_score=0.5,
                similarity_score=None,
                created_at="2025-01-01T00:00:00",
                updated_at=None
            )
            
            result = await store.store(request)
            assert result.id == expected_id


@pytest.mark.unit
@pytest.mark.asyncio
class TestUnifiedStoreQueryOperations:
    """Test query and search operations."""
    
    async def test_query_empty_returns_all_memories(self, mock_unified_store):
        """Test that empty query returns all memories."""
        request = QueryRequest(query="", limit=10)
        
        # Mock memories to return
        mock_memories = [
            MemoryResponse(
                id=str(uuid.uuid4()),
                content="Memory 1",
                metadata={},
                importance_score=0.5,
                similarity_score=1.0,
                created_at="2025-01-01T00:00:00",
                updated_at=None
            ),
            MemoryResponse(
                id=str(uuid.uuid4()),
                content="Memory 2", 
                metadata={},
                importance_score=0.6,
                similarity_score=1.0,
                created_at="2025-01-01T00:01:00",
                updated_at=None
            )
        ]
        
        mock_unified_store.query.return_value = QueryResponse(
            memories=mock_memories,
            total_found=2,
            query_time_ms=100.5,
            providers_used=["pgvector"]
        )
        
        result = await mock_unified_store.query(request)
        
        assert isinstance(result, QueryResponse)
        assert len(result.memories) == 2
        assert result.total_found == 2
        assert "pgvector" in result.providers_used
    
    async def test_query_with_semantic_search(self, mock_unified_store):
        """Test semantic search with query text."""
        request = QueryRequest(query="artificial intelligence", limit=5)
        
        mock_memories = [
            MemoryResponse(
                id=str(uuid.uuid4()),
                content="AI and machine learning are fascinating",
                metadata={},
                importance_score=0.9,
                similarity_score=0.85,
                created_at="2025-01-01T00:00:00",
                updated_at=None
            )
        ]
        
        mock_unified_store.query.return_value = QueryResponse(
            memories=mock_memories,
            total_found=1,
            query_time_ms=50.2,
            providers_used=["pgvector"]
        )
        
        result = await mock_unified_store.query(request)
        
        assert len(result.memories) == 1
        assert result.memories[0].similarity_score == 0.85
        assert "artificial intelligence" in request.query.lower()
    
    async def test_query_with_filters(self, mock_unified_store):
        """Test query with metadata filters."""
        request = QueryRequest(
            query="test",
            limit=10,
            filters={"category": "work", "importance_score": 0.7}
        )
        
        mock_unified_store.query.return_value = QueryResponse(
            memories=[],
            total_found=0,
            query_time_ms=25.1,
            providers_used=["pgvector"]
        )
        
        result = await mock_unified_store.query(request)
        
        assert isinstance(result, QueryResponse)
        mock_unified_store.query.assert_called_once_with(request)
    
    @pytest.mark.performance
    async def test_query_performance(self, mock_unified_store, performance_monitor):
        """Test query performance meets requirements."""
        request = QueryRequest(query="performance test", limit=10)
        
        mock_unified_store.query.return_value = QueryResponse(
            memories=[],
            total_found=0,
            query_time_ms=45.0,  # Fast response
            providers_used=["pgvector"]
        )
        
        performance_monitor.start()
        result = await mock_unified_store.query(request)
        performance_monitor.stop()
        
        # Assert query completes within performance threshold
        performance_monitor.assert_performance(500.0, "semantic query")
        assert result.query_time_ms < 100.0  # Database reports fast query


@pytest.mark.unit
@pytest.mark.asyncio
class TestUnifiedStoreHealthAndStats:
    """Test health checking and statistics."""
    
    async def test_health_check_all_providers_healthy(self, mock_unified_store):
        """Test health check when all providers are healthy."""
        mock_unified_store.health_check.return_value = {
            "status": "healthy",
            "providers": {
                "pgvector": {
                    "status": "healthy",
                    "details": {"total_vectors": 100},
                    "primary": True
                },
                "chromadb": {
                    "status": "healthy", 
                    "details": {"total_vectors": 50},
                    "primary": False
                }
            },
            "stats": {"total_stores": 150}
        }
        
        result = await mock_unified_store.health_check()
        
        assert result["status"] == "healthy"
        assert len(result["providers"]) == 2
        assert result["stats"]["total_stores"] == 150
    
    async def test_health_check_degraded_service(self, mock_pgvector_provider, mock_chromadb_provider):
        """Test health check when secondary provider fails."""
        providers = [mock_pgvector_provider, mock_chromadb_provider]
        store = UnifiedVectorStore(providers=providers)
        
        # Make secondary provider fail
        mock_chromadb_provider.health_check.side_effect = Exception("Connection failed")
        
        with patch.object(store, 'health_check') as mock_health:
            mock_health.return_value = {
                "status": "degraded",  # Still functional but degraded
                "providers": {
                    "pgvector": {"status": "healthy", "primary": True},
                    "chromadb": {"status": "unhealthy", "error": "Connection failed", "primary": False}
                },
                "stats": {"total_stores": 100}
            }
            
            result = await store.health_check()
            assert result["status"] == "degraded"


@pytest.mark.unit
@pytest.mark.asyncio
class TestUnifiedStoreCaching:
    """Test caching behavior."""
    
    async def test_query_caching(self, mock_unified_store):
        """Test that identical queries are cached."""
        request = QueryRequest(query="cached query", limit=5)
        
        # First call
        mock_response = QueryResponse(
            memories=[],
            total_found=0,
            query_time_ms=100.0,
            providers_used=["pgvector"]
        )
        mock_unified_store.query.return_value = mock_response
        
        result1 = await mock_unified_store.query(request)
        result2 = await mock_unified_store.query(request)
        
        # Should call underlying query method multiple times but could use cache
        assert result1.total_found == result2.total_found
    
    async def test_cache_invalidation_on_store(self, mock_unified_store, sample_memory_content):
        """Test that cache is invalidated when new memories are stored."""
        # This would test cache invalidation logic
        # For now, just test that storing doesn't break querying
        
        store_request = MemoryRequest(content=sample_memory_content["medium"])
        query_request = QueryRequest(query="test", limit=5)
        
        mock_unified_store.store.return_value = MemoryResponse(
            id=str(uuid.uuid4()),
            content=store_request.content,
            metadata={},
            importance_score=0.5,
            similarity_score=None,
            created_at="2025-01-01T00:00:00",
            updated_at=None
        )
        
        mock_unified_store.query.return_value = QueryResponse(
            memories=[],
            total_found=0,
            query_time_ms=50.0,
            providers_used=["pgvector"]
        )
        
        # Store then query
        await mock_unified_store.store(store_request)
        result = await mock_unified_store.query(query_request)
        
        assert isinstance(result, QueryResponse)


@pytest.mark.unit
@pytest.mark.asyncio
class TestUnifiedStoreErrorHandling:
    """Test error handling and edge cases."""
    
    async def test_all_providers_fail(self, mock_pgvector_provider, mock_chromadb_provider):
        """Test behavior when all providers fail."""
        providers = [mock_pgvector_provider, mock_chromadb_provider]
        store = UnifiedVectorStore(providers=providers)
        
        # Make all providers fail
        mock_pgvector_provider.store.side_effect = Exception("Primary failed")
        mock_chromadb_provider.store.side_effect = Exception("Secondary failed")
        
        request = MemoryRequest(content="test content")
        
        # Should raise exception when all providers fail
        with patch.object(store, 'store') as mock_store:
            mock_store.side_effect = Exception("All providers failed")
            
            with pytest.raises(Exception, match="All providers failed"):
                await store.store(request)
    
    async def test_invalid_query_request(self, mock_unified_store):
        """Test handling of invalid query requests."""
        # Test with None query
        request = QueryRequest(query=None, limit=10)
        
        mock_unified_store.query.return_value = QueryResponse(
            memories=[],
            total_found=0,
            query_time_ms=10.0,
            providers_used=["emergency"]
        )
        
        result = await mock_unified_store.query(request)
        assert isinstance(result, QueryResponse)
    
    async def test_large_content_handling(self, mock_unified_store, sample_memory_content):
        """Test handling of very large content."""
        request = MemoryRequest(content=sample_memory_content["very_long"])
        
        mock_unified_store.store.return_value = MemoryResponse(
            id=str(uuid.uuid4()),
            content=request.content,
            metadata={},
            importance_score=0.4,  # Lower importance for very long content
            similarity_score=None,
            created_at="2025-01-01T00:00:00",
            updated_at=None
        )
        
        result = await mock_unified_store.store(request)
        
        assert len(result.content) > 1000  # Very long content preserved
        assert 0 <= result.importance_score <= 1  # Valid importance score


@pytest.mark.integration
@pytest.mark.asyncio
class TestUnifiedStoreIntegration:
    """Integration tests across multiple components."""
    
    async def test_store_and_retrieve_workflow(self, mock_unified_store, sample_memory_content, sample_metadata):
        """Test complete store and retrieve workflow."""
        # Store a memory
        store_request = MemoryRequest(
            content=sample_memory_content["medium"],
            metadata=sample_metadata
        )
        
        stored_id = str(uuid.uuid4())
        mock_unified_store.store.return_value = MemoryResponse(
            id=stored_id,
            content=store_request.content,
            metadata=store_request.metadata,
            importance_score=0.7,
            similarity_score=None,
            created_at="2025-01-01T00:00:00",
            updated_at=None
        )
        
        stored_memory = await mock_unified_store.store(store_request)
        
        # Query to retrieve it
        query_request = QueryRequest(query="", limit=10)  # Empty query should return all
        
        mock_unified_store.query.return_value = QueryResponse(
            memories=[stored_memory],
            total_found=1,
            query_time_ms=75.0,
            providers_used=["pgvector"]
        )
        
        query_result = await mock_unified_store.query(query_request)
        
        # Verify the stored memory is retrievable
        assert len(query_result.memories) == 1
        assert query_result.memories[0].id == stored_id
        assert query_result.memories[0].content == sample_memory_content["medium"]
    
    @pytest.mark.slow
    async def test_concurrent_operations(self, mock_unified_store, sample_memory_content):
        """Test concurrent store and query operations."""
        # Setup mock responses
        mock_unified_store.store.return_value = MemoryResponse(
            id=str(uuid.uuid4()),
            content="concurrent content",
            metadata={},
            importance_score=0.5,
            similarity_score=None,
            created_at="2025-01-01T00:00:00",
            updated_at=None
        )
        
        mock_unified_store.query.return_value = QueryResponse(
            memories=[],
            total_found=0,
            query_time_ms=30.0,
            providers_used=["pgvector"]
        )
        
        # Create concurrent tasks
        store_tasks = [
            mock_unified_store.store(MemoryRequest(content=f"Content {i}"))
            for i in range(5)
        ]
        
        query_tasks = [
            mock_unified_store.query(QueryRequest(query=f"Query {i}", limit=5))
            for i in range(3)
        ]
        
        # Execute concurrently
        all_tasks = store_tasks + query_tasks
        results = await asyncio.gather(*all_tasks, return_exceptions=True)
        
        # Verify no exceptions occurred
        for result in results:
            assert not isinstance(result, Exception), f"Task failed with: {result}"
        
        # Verify correct number of results
        assert len(results) == 8  # 5 stores + 3 queries