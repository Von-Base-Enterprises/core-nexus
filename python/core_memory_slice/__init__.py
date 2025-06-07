"""
Core Memory Slice - Day-1 Vertical Slice Implementation

Hybrid vector + graph storage for document ingestion and retrieval.
Designed for <500ms query performance with minimal dependencies.
"""

from .lite_vector_store import LiteVectorStore
from .lite_graph_store import LiteGraphStore

__version__ = "0.1.0"
__all__ = ["LiteVectorStore", "LiteGraphStore"]