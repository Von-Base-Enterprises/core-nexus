"""
Pytest configuration and shared fixtures for Core Nexus Memory Service tests.

This module provides reusable fixtures for testing all components of the memory service.
"""

import asyncio
import os
import json
import uuid
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager

try:
    from typing import UUID
except ImportError:
    from uuid import UUID

import pytest
import httpx
from faker import Faker

# Set testing environment
os.environ["TESTING"] = "true"
os.environ["LOG_LEVEL"] = "WARNING"  # Reduce log noise during tests


# =====================================================
# Event Loop Configuration
# =====================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =====================================================
# Data Generation Fixtures
# =====================================================

@pytest.fixture
def fake():
    """Faker instance for generating test data."""
    return Faker()


@pytest.fixture
def sample_memory_content(fake):
    """Generate realistic memory content for testing."""
    return {
        "short": fake.sentence(nb_words=5),
        "medium": fake.text(max_nb_chars=200),
        "long": fake.text(max_nb_chars=1000),
        "very_long": fake.text(max_nb_chars=5000)
    }


@pytest.fixture
def sample_embedding():
    """Generate a sample 1536-dimensional embedding vector."""
    import random
    return [random.uniform(-1, 1) for _ in range(1536)]


@pytest.fixture
def sample_metadata(fake):
    """Generate sample metadata for memory objects."""
    return {
        "user_id": str(uuid.uuid4()),
        "conversation_id": str(uuid.uuid4()),
        "timestamp": fake.date_time().isoformat(),
        "category": fake.random_element(elements=("work", "personal", "research", "meeting")),
        "importance_score": fake.random.uniform(0, 1),
        "tags": fake.words(nb=3)
    }


# =====================================================
# Mock Database Fixtures
# =====================================================

class MockAsyncConnection:
    """Mock database connection for testing."""
    
    def __init__(self):
        self.data = {
            "vector_memories": {},
            "vector_memories_optimized": {},
            "graph_nodes": {},
            "graph_relationships": {},
            "memory_entity_map": {},
            "memory_content_hashes": {}
        }
        self.queries_executed = []
        self.closed = False
    
    async def execute(self, query: str, *args):
        """Mock execute method."""
        self.queries_executed.append({"query": query, "args": args, "type": "execute"})
        
        # Handle INSERT queries
        if "INSERT INTO vector_memories" in query:
            memory_id = str(uuid.uuid4())
            table = "vector_memories_optimized" if "vector_memories_optimized" in query else "vector_memories"
            self.data[table][memory_id] = {
                "id": memory_id,
                "content": args[1] if len(args) > 1 else "test content",
                "embedding": args[2] if len(args) > 2 else [0.1] * 1536,
                "metadata": args[3] if len(args) > 3 else {},
                "importance_score": args[4] if len(args) > 4 else 0.5,
                "created_at": "2025-01-01T00:00:00"
            }
            return memory_id
        
        return "EXECUTE 1"
    
    async def fetch(self, query: str, *args):
        """Mock fetch method returning list of records."""
        self.queries_executed.append({"query": query, "args": args, "type": "fetch"})
        
        # Handle SELECT queries
        if "SELECT" in query.upper():
            table = "vector_memories_optimized" if "vector_memories_optimized" in query else "vector_memories"
            records = []
            for memory_id, memory_data in self.data[table].items():
                records.append({
                    "id": memory_id,
                    **memory_data
                })
            
            # Apply LIMIT if specified
            if "LIMIT" in query.upper():
                try:
                    limit = int(args[0]) if args else 10
                    records = records[:limit]
                except (ValueError, IndexError):
                    records = records[:10]
            
            return records
        
        return []
    
    async def fetchrow(self, query: str, *args):
        """Mock fetchrow method returning single record."""
        self.queries_executed.append({"query": query, "args": args, "type": "fetchrow"})
        
        if "SELECT" in query.upper():
            table = "vector_memories_optimized" if "vector_memories_optimized" in query else "vector_memories"
            if self.data[table]:
                memory_id, memory_data = next(iter(self.data[table].items()))
                return {"id": memory_id, **memory_data}
        
        return None
    
    async def fetchval(self, query: str, *args):
        """Mock fetchval method returning single value."""
        self.queries_executed.append({"query": query, "args": args, "type": "fetchval"})
        
        if "COUNT(*)" in query:
            table = "vector_memories_optimized" if "vector_memories_optimized" in query else "vector_memories"
            return len(self.data[table])
        elif "SELECT 1" in query:
            return 1
        
        return None
    
    async def close(self):
        """Mock close method."""
        self.closed = True


class MockConnectionPool:
    """Mock connection pool for testing."""
    
    def __init__(self):
        self.connection = MockAsyncConnection()
        self.closed = False
    
    @asynccontextmanager
    async def acquire(self):
        """Mock acquire method."""
        yield self.connection
    
    async def close(self):
        """Mock close method."""
        self.closed = True
        await self.connection.close()


@pytest.fixture
def mock_db_connection():
    """Provide a mock database connection."""
    return MockAsyncConnection()


@pytest.fixture
def mock_db_pool():
    """Provide a mock database connection pool."""
    return MockConnectionPool()


# =====================================================
# Realistic Provider Mock Classes - Production-Aligned Architecture
# =====================================================

class RealisticPgVectorProvider:
    """Realistic PgVector provider mock that works with actual UnifiedVectorStore constructor."""
    
    def __init__(self, config):
        """Initialize with proper ProviderConfig instance."""
        self.config = config
        self.name = config.name
        self.enabled = config.enabled
        self.connection_pool = MockConnectionPool()
        self.table_name = config.config.get('table_name', 'vector_memories_optimized')
        self.embedding_dim = config.config.get('embedding_dim', 1536)
    
    async def store(self, content: str, embedding: list[float], metadata: dict[str, Any]) -> UUID:
        """Mock store method."""
        return uuid.uuid4()
    
    async def query(self, query_embedding: list[float], limit: int, filters: dict[str, Any]) -> list:
        """Mock query method."""
        return []
    
    async def health_check(self) -> dict[str, Any]:
        """Mock health check."""
        return {
            "status": "healthy",
            "details": {
                "total_vectors": 150,
                "pgvector_enabled": True,
                "table_name": self.table_name,
                "pool_size": 10
            }
        }
    
    async def get_stats(self) -> dict[str, Any]:
        """Mock stats."""
        return {
            "provider": "pgvector",
            "total_vectors": 150,
            "avg_query_time": 0.1
        }


class RealisticChromaProvider:
    """Realistic ChromaDB provider mock that works with actual UnifiedVectorStore constructor."""
    
    def __init__(self, config):
        """Initialize with proper ProviderConfig instance."""
        self.config = config
        self.name = config.name
        self.enabled = config.enabled
        self.collection_name = config.config.get('collection_name', 'test_collection')
    
    async def store(self, content: str, embedding: list[float], metadata: dict[str, Any]) -> UUID:
        """Mock store method."""
        return uuid.uuid4()
    
    async def query(self, query_embedding: list[float], limit: int, filters: dict[str, Any]) -> list:
        """Mock query method."""
        return []
    
    async def health_check(self) -> dict[str, Any]:
        """Mock health check."""
        return {
            "status": "healthy",
            "collection_count": 1,
            "vector_count": 50
        }
    
    async def get_stats(self) -> dict[str, Any]:
        """Mock stats."""
        return {
            "provider": "chromadb",
            "total_vectors": 50,
            "avg_query_time": 0.05
        }


@pytest.fixture
def realistic_pgvector_provider():
    """Create realistic PgVector provider with proper configuration."""
    from src.memory_service.models import ProviderConfig
    
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
    
    return RealisticPgVectorProvider(config)


@pytest.fixture
def realistic_chromadb_provider():
    """Create realistic ChromaDB provider with proper configuration."""
    from src.memory_service.models import ProviderConfig
    
    config = ProviderConfig(
        name="chromadb",
        enabled=True,
        primary=False,
        config={
            "host": "localhost",
            "port": 8000,
            "collection_name": "test_collection"
        }
    )
    
    return RealisticChromaProvider(config)


# Legacy fixtures for backward compatibility
@pytest.fixture
def mock_pgvector_provider(realistic_pgvector_provider):
    """Legacy compatibility fixture."""
    return realistic_pgvector_provider


@pytest.fixture
def mock_chromadb_provider(realistic_chromadb_provider):
    """Legacy compatibility fixture."""
    return realistic_chromadb_provider


# =====================================================
# UnifiedVectorStore Mock Fixtures
# =====================================================

@pytest.fixture
def mock_unified_store(realistic_pgvector_provider, realistic_chromadb_provider):
    """Production-aligned UnifiedVectorStore using real constructor with realistic providers."""
    from src.memory_service.unified_store import UnifiedVectorStore
    
    # Use real constructor with realistic providers - CRITICAL for advanced test suite
    providers = [realistic_pgvector_provider, realistic_chromadb_provider]
    
    # Mock dependencies that the constructor needs
    with patch('src.memory_service.unified_store.ImportanceScoring') as mock_importance, \
         patch('asyncio.create_task') as mock_task, \
         patch.object(UnifiedVectorStore, '_sync_initial_stats', new_callable=AsyncMock) as mock_sync_stats:
        
        # Create real UnifiedVectorStore instance
        store = UnifiedVectorStore(
            providers=providers,
            embedding_model=AsyncMock(),
            adm_enabled=False  # Disable ADM for testing simplicity
        )
        
        # Memory storage for tracking created memories
        memory_storage = {}
        
        # Enhanced API methods with proper return types and ID tracking
        async def mock_store_memory(request):
            """Mock store_memory that returns a MemoryResponse and tracks the memory."""
            from src.memory_service.models import MemoryResponse
            memory_id = str(uuid.uuid4())
            memory = MemoryResponse(
                id=memory_id,
                content=request.content,
                metadata=request.metadata or {},
                importance_score=0.75,
                similarity_score=None,
                created_at="2025-01-01T00:00:00",
                updated_at=None
            )
            # Store for later retrieval
            memory_storage[memory_id] = memory
            return memory
        
        async def mock_query_memories(request):
            """Mock query_memories that returns a QueryResponse for API layer."""
            from src.memory_service.models import QueryResponse, MemoryResponse
            
            # Return actual stored memories instead of random samples
            stored_memories = list(memory_storage.values())
            
            # If no stored memories, return some sample ones
            if not stored_memories:
                sample_memories = [
                    MemoryResponse(
                        id=str(uuid.uuid4()),
                        content=f"Sample memory result for query: {request.query}",
                        metadata={"source": "mock", "category": "test"},
                        importance_score=0.8,
                        similarity_score=0.9,
                        created_at="2025-01-01T00:00:00",
                        updated_at=None
                    ),
                    MemoryResponse(
                        id=str(uuid.uuid4()),
                        content=f"Another test memory matching: {request.query}",
                        metadata={"source": "mock", "category": "test"},
                        importance_score=0.6,
                        similarity_score=0.7,
                        created_at="2025-01-01T00:01:00",
                        updated_at=None
                    )
                ]
                memories_to_return = sample_memories
            else:
                memories_to_return = stored_memories
            
            # Limit results based on request
            limited_memories = memories_to_return[:request.limit]
            
            return QueryResponse(
                memories=limited_memories,
                total_found=len(memories_to_return),
                query_time_ms=125.5,
                providers_used=["pgvector"],
                trust_metrics={
                    "confidence_score": 0.9,
                    "data_completeness": 1.0,
                    "query_type": "mock_test"
                },
                query_metadata={
                    "original_query": request.query,
                    "limit_requested": request.limit,
                    "api_version": "mock"
                }
            )
        
        async def mock_get_memory_by_id(memory_id):
            """Mock get_memory_by_id that retrieves stored memories."""
            # Check if memory exists in our storage
            if memory_id in memory_storage:
                return memory_storage[memory_id]
            else:
                return None  # Return None for non-existent memories
        
        # Override methods for API compatibility
        store.store_memory = mock_store_memory
        store.query_memories = mock_query_memories
        store.get_memory_by_id = mock_get_memory_by_id
        
        return store


# =====================================================
# FastAPI Test Client Fixtures
# =====================================================

@pytest.fixture(scope="function")  
async def test_client(mock_unified_store):
    """Test client for FastAPI endpoints with persistent mock injection."""
    import importlib
    from src.memory_service import api
    from src.memory_service.models import MemoryResponse
    
    # Force reload the API module to ensure clean state
    importlib.reload(api)
    
    # Create mock emergency retrieval that connects to unified store's memory storage
    mock_emergency = MagicMock()
    mock_emergency.connection = True
    
    # Smart emergency retrieval that delegates to unified store
    async def smart_emergency_get_memory_by_id(memory_id):
        """Smart emergency retrieval that delegates to the unified store."""
        # Call the unified store's get_memory_by_id method
        return await mock_unified_store.get_memory_by_id(memory_id)
    
    mock_emergency.get_memory_by_id = smart_emergency_get_memory_by_id
    
    # Forcibly set the global variables in the API module BEFORE creating the app
    api.unified_store = mock_unified_store
    api.emergency_retrieval = mock_emergency
    
    # Verify the injection worked
    assert api.unified_store is not None, "Mock unified_store injection failed"
    assert api.unified_store is mock_unified_store, "Mock unified_store not properly set"
    
    # Create app with injected mocks
    app = api.create_memory_app()
    
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client


# =====================================================
# Environment and Configuration Fixtures
# =====================================================

@pytest.fixture
def test_config():
    """Test configuration overrides."""
    return {
        "TESTING": True,
        "LOG_LEVEL": "WARNING",
        "PGVECTOR_HOST": "localhost",
        "PGVECTOR_PORT": "5432",
        "PGVECTOR_DATABASE": "test_db",
        "PGVECTOR_USER": "test_user",
        "PGVECTOR_PASSWORD": "test_pass",
        "TABLE_NAME": "vector_memories_optimized",
        "OPENAI_API_KEY": "test-key-for-testing"
    }


@pytest.fixture(autouse=True)
def set_test_env(test_config):
    """Automatically set test environment variables."""
    original_env = {}
    
    # Store original values
    for key, value in test_config.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = str(value)
    
    yield
    
    # Restore original values
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


# =====================================================
# Performance Testing Fixtures
# =====================================================

@pytest.fixture
def performance_monitor():
    """Monitor for performance testing."""
    import time
    
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.metrics = {}
        
        def start(self):
            self.start_time = time.perf_counter()
        
        def stop(self):
            self.end_time = time.perf_counter()
        
        @property
        def elapsed_ms(self):
            if self.start_time and self.end_time:
                return (self.end_time - self.start_time) * 1000
            return None
        
        def assert_performance(self, max_time_ms: float, operation: str = "operation"):
            """Assert that operation completed within time limit."""
            elapsed = self.elapsed_ms
            assert elapsed is not None, f"Performance monitor not properly started/stopped for {operation}"
            assert elapsed <= max_time_ms, f"{operation} took {elapsed:.2f}ms, expected <= {max_time_ms}ms"
    
    return PerformanceMonitor()


# =====================================================
# Cleanup Fixtures
# =====================================================

@pytest.fixture(autouse=True)
async def cleanup_after_test():
    """Clean up resources after each test."""
    yield
    
    # Clean up any async resources, clear caches, etc.
    # This runs after each test
    pass


# =====================================================
# Parametrized Test Data
# =====================================================

@pytest.fixture(params=[
    {"size": "small", "content_length": 50, "vectors": 10},
    {"size": "medium", "content_length": 200, "vectors": 100}, 
    {"size": "large", "content_length": 1000, "vectors": 500}
])
def scale_test_data(request):
    """Parametrized data for scale testing."""
    return request.param


@pytest.fixture(params=["pgvector", "chromadb"])
def provider_names(request):
    """Parametrized provider names for multi-provider testing."""
    return request.param