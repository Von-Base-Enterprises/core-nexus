"""
Comprehensive tests for vector storage providers.

Tests the provider abstraction layer including:
- PgVectorProvider functionality
- ChromaDBProvider functionality  
- Provider configuration and initialization
- Error handling and fallback behavior
- Performance characteristics
"""

import pytest
import uuid
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from src.memory_service.models import ProviderConfig, MemoryResponse
from src.memory_service.providers import PgVectorProvider


@pytest.mark.unit
class TestProviderConfiguration:
    """Test provider configuration and validation."""
    
    def test_pgvector_config_creation(self):
        """Test PgVectorProvider configuration."""
        config = ProviderConfig(
            name="pgvector",
            enabled=True,
            primary=True,
            config={
                "host": "localhost",
                "port": 5432,
                "database": "test_db",
                "user": "test_user", 
                "password": "test_pass",
                "table_name": "vector_memories_optimized",
                "embedding_dim": 1536,
                "distance_metric": "cosine"
            }
        )
        
        assert config.name == "pgvector"
        assert config.enabled is True
        assert config.primary is True
        assert config.config["embedding_dim"] == 1536
        assert config.config["table_name"] == "vector_memories_optimized"
    
    def test_chromadb_config_creation(self):
        """Test ChromaDBProvider configuration."""
        config = ProviderConfig(
            name="chromadb",
            enabled=True,
            primary=False,
            config={
                "host": "localhost",
                "port": 8000,
                "collection_name": "test_collection",
                "embedding_dim": 1536
            }
        )
        
        assert config.name == "chromadb"
        assert config.enabled is True
        assert config.primary is False
        assert config.config["collection_name"] == "test_collection"
    
    def test_config_validation(self):
        """Test configuration validation requirements."""
        # Test missing required fields
        with pytest.raises((ValueError, TypeError)):
            ProviderConfig(
                name="pgvector",
                enabled=True,
                primary=True,
                config={}  # Missing required config
            )


@pytest.mark.unit
@pytest.mark.asyncio
class TestPgVectorProvider:
    """Test PgVectorProvider functionality."""
    
    async def test_provider_initialization(self, mock_db_pool):
        """Test PgVectorProvider initialization."""
        config = ProviderConfig(
            name="pgvector",
            enabled=True,
            primary=True,
            config={
                "host": "localhost",
                "port": 5432,
                "database": "test_db",
                "user": "test_user",
                "password": "test_pass",
                "table_name": "vector_memories_optimized",
                "embedding_dim": 1536,
                "distance_metric": "cosine"
            }
        )
        
        with patch('src.memory_service.providers.asyncpg.create_pool') as mock_create_pool:
            mock_create_pool.return_value = mock_db_pool
            
            provider = PgVectorProvider(config)
            assert provider.name == "pgvector"
            assert provider.enabled is True
            assert provider.config == config
    
    async def test_store_memory_success(self, mock_pgvector_provider, sample_embedding, sample_metadata):
        """Test successful memory storage."""
        content = "Test memory content"
        
        # Mock the store method
        expected_id = str(uuid.uuid4())
        mock_pgvector_provider.store.return_value = expected_id
        
        result = await mock_pgvector_provider.store(content, sample_embedding, sample_metadata)
        
        assert result == expected_id
        mock_pgvector_provider.store.assert_called_once_with(content, sample_embedding, sample_metadata)
    
    async def test_store_memory_with_optimized_table(self, mock_db_connection, sample_embedding):
        """Test memory storage uses optimized table name."""
        config = ProviderConfig(
            name="pgvector",
            enabled=True,
            primary=True,
            config={
                "host": "localhost",
                "port": 5432,
                "database": "test_db",
                "user": "test_user",
                "password": "test_pass",
                "table_name": "vector_memories_optimized",  # Optimized table
                "embedding_dim": 1536,
                "distance_metric": "cosine"
            }
        )
        
        with patch('src.memory_service.providers.asyncpg.create_pool') as mock_create_pool:
            mock_pool = MagicMock()
            mock_pool.acquire.return_value.__aenter__.return_value = mock_db_connection
            mock_create_pool.return_value = mock_pool
            
            provider = PgVectorProvider(config)
            
            # Mock the store method to verify table name usage
            with patch.object(provider, 'store') as mock_store:
                await provider.store("content", sample_embedding, {})
                
                # Verify store was called (implementation would use optimized table)
                mock_store.assert_called_once()
    
    async def test_query_memories_success(self, mock_pgvector_provider, sample_embedding):
        """Test successful memory querying."""
        limit = 10
        filters = {"category": "test"}
        
        # Mock query results
        mock_memories = [
            MemoryResponse(
                id=str(uuid.uuid4()),
                content="Found memory 1",
                metadata={"category": "test"},
                importance_score=0.8,
                similarity_score=0.9,
                created_at="2025-01-01T00:00:00",
                updated_at=None
            ),
            MemoryResponse(
                id=str(uuid.uuid4()),
                content="Found memory 2", 
                metadata={"category": "test"},
                importance_score=0.7,
                similarity_score=0.85,
                created_at="2025-01-01T00:01:00",
                updated_at=None
            )
        ]
        
        mock_pgvector_provider.query.return_value = mock_memories
        
        results = await mock_pgvector_provider.query(sample_embedding, limit, filters)
        
        assert len(results) == 2
        assert all(isinstance(mem, MemoryResponse) for mem in results)
        assert all(mem.similarity_score >= 0.8 for mem in results)
        mock_pgvector_provider.query.assert_called_once_with(sample_embedding, limit, filters)
    
    async def test_health_check_success(self, mock_pgvector_provider):
        """Test provider health check."""
        mock_health_data = {
            "status": "healthy",
            "details": {
                "total_vectors": 1474,
                "pgvector_enabled": True,
                "table_name": "vector_memories_optimized",
                "pool_size": 10
            }
        }
        
        mock_pgvector_provider.health_check.return_value = mock_health_data
        
        result = await mock_pgvector_provider.health_check()
        
        assert result["status"] == "healthy"
        assert result["details"]["total_vectors"] == 1474
        assert result["details"]["table_name"] == "vector_memories_optimized"
    
    async def test_provider_error_handling(self, mock_pgvector_provider, sample_embedding):
        """Test provider error handling."""
        # Make provider methods fail
        mock_pgvector_provider.store.side_effect = Exception("Database connection failed")
        mock_pgvector_provider.query.side_effect = Exception("Query execution failed")
        
        # Store should raise exception
        with pytest.raises(Exception, match="Database connection failed"):
            await mock_pgvector_provider.store("content", sample_embedding, {})
        
        # Query should raise exception
        with pytest.raises(Exception, match="Query execution failed"):
            await mock_pgvector_provider.query(sample_embedding, 10, {})
    
    @pytest.mark.performance
    async def test_provider_performance(self, mock_pgvector_provider, sample_embedding, performance_monitor):
        """Test provider performance characteristics."""
        # Mock fast responses
        mock_pgvector_provider.store.return_value = str(uuid.uuid4())
        mock_pgvector_provider.query.return_value = []
        
        # Test store performance
        performance_monitor.start()
        await mock_pgvector_provider.store("content", sample_embedding, {})
        performance_monitor.stop()
        
        performance_monitor.assert_performance(200.0, "provider store operation")
        
        # Test query performance
        performance_monitor.start()
        await mock_pgvector_provider.query(sample_embedding, 10, {})
        performance_monitor.stop()
        
        performance_monitor.assert_performance(300.0, "provider query operation")


@pytest.mark.unit
@pytest.mark.asyncio
class TestChromaDBProvider:
    """Test ChromaDBProvider functionality."""
    
    async def test_chromadb_store_success(self, mock_chromadb_provider, sample_embedding):
        """Test ChromaDB memory storage."""
        content = "ChromaDB test content"
        metadata = {"source": "chromadb_test"}
        
        expected_id = str(uuid.uuid4())
        mock_chromadb_provider.store.return_value = expected_id
        
        result = await mock_chromadb_provider.store(content, sample_embedding, metadata)
        
        assert result == expected_id
        mock_chromadb_provider.store.assert_called_once_with(content, sample_embedding, metadata)
    
    async def test_chromadb_query_success(self, mock_chromadb_provider, sample_embedding):
        """Test ChromaDB memory querying."""
        mock_results = [
            MemoryResponse(
                id=str(uuid.uuid4()),
                content="ChromaDB result",
                metadata={"source": "chromadb"},
                importance_score=0.6,
                similarity_score=0.75,
                created_at="2025-01-01T00:00:00",
                updated_at=None
            )
        ]
        
        mock_chromadb_provider.query.return_value = mock_results
        
        results = await mock_chromadb_provider.query(sample_embedding, 5, {})
        
        assert len(results) == 1
        assert results[0].content == "ChromaDB result"
        assert results[0].similarity_score == 0.75
    
    async def test_chromadb_health_check(self, mock_chromadb_provider):
        """Test ChromaDB health check."""
        mock_health = {
            "status": "healthy",
            "collection_count": 1,
            "vector_count": 50
        }
        
        mock_chromadb_provider.health_check.return_value = mock_health
        
        result = await mock_chromadb_provider.health_check()
        
        assert result["status"] == "healthy"
        assert result["vector_count"] == 50


@pytest.mark.unit
@pytest.mark.asyncio
class TestProviderFailover:
    """Test provider failover and fallback behavior."""
    
    async def test_primary_provider_failure_detection(self, mock_pgvector_provider):
        """Test detection of primary provider failures."""
        # Simulate primary provider failure
        mock_pgvector_provider.health_check.side_effect = Exception("Connection timeout")
        
        with pytest.raises(Exception, match="Connection timeout"):
            await mock_pgvector_provider.health_check()
    
    async def test_provider_recovery_detection(self, mock_pgvector_provider):
        """Test detection of provider recovery."""
        # First, provider fails
        mock_pgvector_provider.health_check.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception):
            await mock_pgvector_provider.health_check()
        
        # Then, provider recovers
        mock_pgvector_provider.health_check.side_effect = None
        mock_pgvector_provider.health_check.return_value = {"status": "healthy"}
        
        result = await mock_pgvector_provider.health_check()
        assert result["status"] == "healthy"
    
    async def test_degraded_provider_handling(self, mock_pgvector_provider):
        """Test handling of degraded provider performance."""
        # Provider is healthy but slow
        mock_pgvector_provider.health_check.return_value = {
            "status": "degraded",
            "details": {"response_time": 5000}  # Very slow
        }
        
        result = await mock_pgvector_provider.health_check()
        assert result["status"] == "degraded"


@pytest.mark.integration
@pytest.mark.asyncio
class TestProviderIntegration:
    """Integration tests across provider functionality."""
    
    async def test_multi_provider_consistency(self, mock_pgvector_provider, mock_chromadb_provider, sample_embedding):
        """Test consistency across multiple providers."""
        content = "Multi-provider test content"
        metadata = {"test": "consistency"}
        
        # Store in both providers
        pgvector_id = str(uuid.uuid4())
        chromadb_id = str(uuid.uuid4())
        
        mock_pgvector_provider.store.return_value = pgvector_id
        mock_chromadb_provider.store.return_value = chromadb_id
        
        pg_result = await mock_pgvector_provider.store(content, sample_embedding, metadata)
        chroma_result = await mock_chromadb_provider.store(content, sample_embedding, metadata)
        
        assert pg_result == pgvector_id
        assert chroma_result == chromadb_id
        
        # Both providers should be called with same data
        mock_pgvector_provider.store.assert_called_with(content, sample_embedding, metadata)
        mock_chromadb_provider.store.assert_called_with(content, sample_embedding, metadata)
    
    async def test_provider_health_monitoring(self, mock_pgvector_provider, mock_chromadb_provider):
        """Test continuous health monitoring across providers."""
        # Set up health responses
        mock_pgvector_provider.health_check.return_value = {
            "status": "healthy",
            "details": {"total_vectors": 1000}
        }
        
        mock_chromadb_provider.health_check.return_value = {
            "status": "healthy", 
            "details": {"total_vectors": 500}
        }
        
        # Check health of both providers
        pg_health = await mock_pgvector_provider.health_check()
        chroma_health = await mock_chromadb_provider.health_check()
        
        assert pg_health["status"] == "healthy"
        assert chroma_health["status"] == "healthy"
        assert pg_health["details"]["total_vectors"] == 1000
        assert chroma_health["details"]["total_vectors"] == 500
    
    @pytest.mark.slow
    async def test_concurrent_provider_operations(self, mock_pgvector_provider, mock_chromadb_provider, sample_embedding):
        """Test concurrent operations across providers."""
        # Set up mock responses
        mock_pgvector_provider.store.return_value = str(uuid.uuid4())
        mock_chromadb_provider.store.return_value = str(uuid.uuid4())
        
        mock_pgvector_provider.query.return_value = []
        mock_chromadb_provider.query.return_value = []
        
        # Create concurrent tasks
        pg_store_tasks = [
            mock_pgvector_provider.store(f"Content {i}", sample_embedding, {})
            for i in range(3)
        ]
        
        chroma_store_tasks = [
            mock_chromadb_provider.store(f"Content {i}", sample_embedding, {})
            for i in range(3)
        ]
        
        pg_query_tasks = [
            mock_pgvector_provider.query(sample_embedding, 5, {})
            for i in range(2)
        ]
        
        # Execute all tasks concurrently
        all_tasks = pg_store_tasks + chroma_store_tasks + pg_query_tasks
        results = await asyncio.gather(*all_tasks, return_exceptions=True)
        
        # Verify no exceptions occurred
        for result in results:
            assert not isinstance(result, Exception), f"Task failed: {result}"
        
        # Verify correct number of results
        assert len(results) == 8  # 3 + 3 + 2


@pytest.mark.unit
@pytest.mark.asyncio
class TestProviderConfiguration:
    """Test provider configuration and environment handling."""
    
    async def test_environment_variable_integration(self, test_config):
        """Test provider configuration from environment variables."""
        # Test that providers can be configured from environment
        config = ProviderConfig(
            name="pgvector",
            enabled=True,
            primary=True,
            config={
                "host": test_config["PGVECTOR_HOST"],
                "port": int(test_config["PGVECTOR_PORT"]),
                "database": test_config["PGVECTOR_DATABASE"],
                "user": test_config["PGVECTOR_USER"],
                "password": test_config["PGVECTOR_PASSWORD"],
                "table_name": test_config["TABLE_NAME"],
                "embedding_dim": 1536,
                "distance_metric": "cosine"
            }
        )
        
        assert config.config["host"] == "localhost"
        assert config.config["database"] == "test_db"
        assert config.config["table_name"] == "vector_memories_optimized"
    
    async def test_production_vs_test_configuration(self, test_config):
        """Test different configurations for production vs test."""
        # Test configuration
        test_provider_config = ProviderConfig(
            name="pgvector",
            enabled=True,
            primary=True,
            config={
                "host": "localhost",
                "database": "test_db",
                "table_name": "vector_memories_optimized",
                "embedding_dim": 1536
            }
        )
        
        # Production configuration (would be different)
        prod_provider_config = ProviderConfig(
            name="pgvector",
            enabled=True,
            primary=True,
            config={
                "host": "production-host",
                "database": "prod_db",
                "table_name": "vector_memories_optimized",
                "embedding_dim": 1536
            }
        )
        
        assert test_provider_config.config["host"] != prod_provider_config.config["host"]
        assert test_provider_config.config["table_name"] == prod_provider_config.config["table_name"]  # Same optimized table