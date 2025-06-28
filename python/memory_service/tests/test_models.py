"""
Tests for Pydantic models and data validation.

Tests the core data models including:
- MemoryRequest/Response validation
- QueryRequest/Response validation
- ProviderConfig validation
- Error handling for invalid data
"""

import pytest
import uuid
from datetime import datetime
from typing import Dict, Any

from src.memory_service.models import (
    MemoryRequest,
    MemoryResponse, 
    QueryRequest,
    QueryResponse,
    ProviderConfig,
    HealthCheckResponse
)


@pytest.mark.unit
class TestMemoryModels:
    """Test memory-related Pydantic models."""
    
    def test_memory_request_valid(self, sample_metadata):
        """Test valid MemoryRequest creation."""
        request = MemoryRequest(
            content="Test memory content",
            metadata=sample_metadata
        )
        
        assert request.content == "Test memory content"
        assert request.metadata == sample_metadata
    
    def test_memory_request_minimal(self):
        """Test MemoryRequest with minimal data."""
        request = MemoryRequest(content="Minimal content")
        
        assert request.content == "Minimal content"
        assert request.metadata is None
    
    def test_memory_request_validation_errors(self):
        """Test MemoryRequest validation failures."""
        # Empty content should fail
        with pytest.raises(ValueError):
            MemoryRequest(content="")
        
        # None content should fail
        with pytest.raises(ValueError):
            MemoryRequest(content=None)
    
    def test_memory_response_valid(self, sample_metadata):
        """Test valid MemoryResponse creation."""
        response = MemoryResponse(
            id=str(uuid.uuid4()),
            content="Response content",
            metadata=sample_metadata,
            importance_score=0.75,
            similarity_score=0.85,
            created_at="2025-01-01T00:00:00",
            updated_at=None
        )
        
        assert response.content == "Response content"
        assert response.importance_score == 0.75
        assert response.similarity_score == 0.85
        assert 0 <= response.importance_score <= 1
        assert 0 <= response.similarity_score <= 1
    
    def test_memory_response_score_validation(self):
        """Test importance and similarity score validation."""
        # Invalid importance score
        with pytest.raises(ValueError):
            MemoryResponse(
                id=str(uuid.uuid4()),
                content="Test",
                metadata={},
                importance_score=1.5,  # > 1.0
                similarity_score=0.5,
                created_at="2025-01-01T00:00:00",
                updated_at=None
            )
        
        # Invalid similarity score
        with pytest.raises(ValueError):
            MemoryResponse(
                id=str(uuid.uuid4()),
                content="Test",
                metadata={},
                importance_score=0.5,
                similarity_score=-0.1,  # < 0.0
                created_at="2025-01-01T00:00:00",
                updated_at=None
            )


@pytest.mark.unit
class TestQueryModels:
    """Test query-related Pydantic models."""
    
    def test_query_request_valid(self):
        """Test valid QueryRequest creation."""
        request = QueryRequest(
            query="test query",
            limit=10,
            filters={"category": "work"}
        )
        
        assert request.query == "test query"
        assert request.limit == 10
        assert request.filters == {"category": "work"}
    
    def test_query_request_defaults(self):
        """Test QueryRequest with default values."""
        request = QueryRequest(query="test")
        
        assert request.query == "test"
        assert request.limit == 10  # Default limit
        assert request.filters is None
    
    def test_query_request_empty_query(self):
        """Test QueryRequest with empty query."""
        request = QueryRequest(query="", limit=5)
        
        assert request.query == ""
        assert request.limit == 5
    
    def test_query_request_validation(self):
        """Test QueryRequest validation."""
        # Invalid limit
        with pytest.raises(ValueError):
            QueryRequest(query="test", limit=0)
        
        with pytest.raises(ValueError):
            QueryRequest(query="test", limit=-1)
    
    def test_query_response_valid(self):
        """Test valid QueryResponse creation."""
        memories = [
            MemoryResponse(
                id=str(uuid.uuid4()),
                content="Memory 1",
                metadata={},
                importance_score=0.5,
                similarity_score=0.8,
                created_at="2025-01-01T00:00:00",
                updated_at=None
            )
        ]
        
        response = QueryResponse(
            memories=memories,
            total_found=1,
            query_time_ms=125.5,
            providers_used=["pgvector"]
        )
        
        assert len(response.memories) == 1
        assert response.total_found == 1
        assert response.query_time_ms == 125.5
        assert response.providers_used == ["pgvector"]
    
    def test_query_response_empty(self):
        """Test QueryResponse with no results."""
        response = QueryResponse(
            memories=[],
            total_found=0,
            query_time_ms=50.0,
            providers_used=["pgvector"]
        )
        
        assert len(response.memories) == 0
        assert response.total_found == 0


@pytest.mark.unit
class TestProviderConfig:
    """Test provider configuration models."""
    
    def test_provider_config_valid(self):
        """Test valid ProviderConfig creation."""
        config = ProviderConfig(
            name="test_provider",
            enabled=True,
            primary=False,
            config={
                "host": "localhost",
                "port": 5432,
                "database": "test_db"
            }
        )
        
        assert config.name == "test_provider"
        assert config.enabled is True
        assert config.primary is False
        assert config.config["host"] == "localhost"
    
    def test_provider_config_defaults(self):
        """Test ProviderConfig with default values."""
        config = ProviderConfig(
            name="default_provider",
            config={}
        )
        
        assert config.name == "default_provider"
        assert config.enabled is True  # Default
        assert config.primary is False  # Default
        assert config.config == {}
    
    def test_provider_config_validation(self):
        """Test ProviderConfig validation."""
        # Empty name should fail
        with pytest.raises(ValueError):
            ProviderConfig(name="", config={})
        
        # None name should fail
        with pytest.raises(ValueError):
            ProviderConfig(name=None, config={})


@pytest.mark.unit
class TestHealthCheckResponse:
    """Test health check response models."""
    
    def test_health_check_response_valid(self):
        """Test valid HealthCheckResponse creation."""
        response = HealthCheckResponse(
            status="healthy",
            providers={
                "pgvector": {
                    "status": "healthy",
                    "details": {"total_vectors": 100},
                    "primary": True
                }
            },
            total_memories=100,
            avg_query_time_ms=125.5,
            uptime_seconds=3600.0
        )
        
        assert response.status == "healthy"
        assert "pgvector" in response.providers
        assert response.total_memories == 100
        assert response.avg_query_time_ms == 125.5
        assert response.uptime_seconds == 3600.0
    
    def test_health_check_response_degraded(self):
        """Test HealthCheckResponse for degraded service."""
        response = HealthCheckResponse(
            status="degraded",
            providers={
                "pgvector": {"status": "healthy", "primary": True},
                "chromadb": {"status": "unhealthy", "error": "Connection failed", "primary": False}
            },
            total_memories=50,
            avg_query_time_ms=250.0,
            uptime_seconds=1800.0
        )
        
        assert response.status == "degraded"
        assert len(response.providers) == 2


@pytest.mark.unit 
class TestModelSerialization:
    """Test model serialization and deserialization."""
    
    def test_memory_request_json_serialization(self, sample_metadata):
        """Test MemoryRequest JSON serialization."""
        request = MemoryRequest(
            content="Serialization test",
            metadata=sample_metadata
        )
        
        # Serialize to dict
        request_dict = request.model_dump()
        assert request_dict["content"] == "Serialization test"
        assert request_dict["metadata"] == sample_metadata
        
        # Deserialize from dict
        reconstructed = MemoryRequest(**request_dict)
        assert reconstructed.content == request.content
        assert reconstructed.metadata == request.metadata
    
    def test_query_response_json_serialization(self):
        """Test QueryResponse JSON serialization."""
        memories = [
            MemoryResponse(
                id=str(uuid.uuid4()),
                content="Serialized memory",
                metadata={"test": True},
                importance_score=0.6,
                similarity_score=0.9,
                created_at="2025-01-01T00:00:00",
                updated_at=None
            )
        ]
        
        response = QueryResponse(
            memories=memories,
            total_found=1,
            query_time_ms=75.0,
            providers_used=["test_provider"]
        )
        
        # Serialize to dict
        response_dict = response.model_dump()
        assert len(response_dict["memories"]) == 1
        assert response_dict["total_found"] == 1
        
        # Deserialize from dict
        reconstructed = QueryResponse(**response_dict)
        assert len(reconstructed.memories) == 1
        assert reconstructed.total_found == response.total_found
    
    def test_nested_model_serialization(self):
        """Test serialization of models with nested structures."""
        # Create complex nested structure
        provider_config = ProviderConfig(
            name="nested_test",
            enabled=True,
            config={
                "nested": {
                    "deep": {
                        "value": "test"
                    }
                },
                "list": [1, 2, 3]
            }
        )
        
        # Serialize and deserialize
        config_dict = provider_config.model_dump()
        reconstructed = ProviderConfig(**config_dict)
        
        assert reconstructed.config["nested"]["deep"]["value"] == "test"
        assert reconstructed.config["list"] == [1, 2, 3]


@pytest.mark.integration
class TestModelInteroperability:
    """Test how models work together in realistic scenarios."""
    
    def test_request_response_cycle(self, sample_memory_content, sample_metadata):
        """Test complete request -> response cycle."""
        # Create request
        request = MemoryRequest(
            content=sample_memory_content["medium"],
            metadata=sample_metadata
        )
        
        # Simulate processing into response
        response = MemoryResponse(
            id=str(uuid.uuid4()),
            content=request.content,
            metadata=request.metadata,
            importance_score=0.7,
            similarity_score=None,  # No similarity for storage
            created_at=datetime.now().isoformat(),
            updated_at=None
        )
        
        # Verify data integrity
        assert response.content == request.content
        assert response.metadata == request.metadata
        assert response.importance_score is not None
    
    def test_query_request_response_cycle(self):
        """Test query request -> response cycle."""
        # Create query request
        query_request = QueryRequest(
            query="integration test",
            limit=5,
            filters={"category": "test"}
        )
        
        # Create mock response
        memories = [
            MemoryResponse(
                id=str(uuid.uuid4()),
                content="Found memory",
                metadata={"category": "test"},
                importance_score=0.8,
                similarity_score=0.75,
                created_at="2025-01-01T00:00:00",
                updated_at=None
            )
        ]
        
        query_response = QueryResponse(
            memories=memories,
            total_found=1,
            query_time_ms=100.0,
            providers_used=["test_provider"]
        )
        
        # Verify query was processed correctly
        assert len(query_response.memories) <= query_request.limit
        assert query_response.memories[0].metadata["category"] == query_request.filters["category"]