"""
Core Nexus Memory Service

Unified Long Term Memory Module (LTMM) providing multi-provider vector storage
with automatic failover, caching, and temporal query capabilities.

This service leverages existing implementations:
- Pinecone (cloud scale)
- ChromaDB (local speed) 
- pgvector (unified queries)
"""

__version__ = "0.1.0"
__author__ = "Core Nexus Team"

from .models import (
    MemoryRequest, MemoryResponse, QueryRequest, QueryResponse,
    GraphNode, GraphRelationship, GraphQuery, GraphResponse, EntityInsights
)
from .unified_store import UnifiedVectorStore
from .providers import PineconeProvider, ChromaProvider, PgVectorProvider, GraphProvider
from .temporal import TemporalMemoryStore
from .api import create_memory_app

__all__ = [
    "UnifiedVectorStore",
    "MemoryRequest", 
    "MemoryResponse",
    "QueryRequest",
    "QueryResponse",
    "GraphNode",
    "GraphRelationship",
    "GraphQuery",
    "GraphResponse",
    "EntityInsights",
    "PineconeProvider",
    "ChromaProvider", 
    "PgVectorProvider",
    "GraphProvider",
    "TemporalMemoryStore",
    "create_memory_app",
]