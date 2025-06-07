# Core Memory Slice

Day-1 vertical slice implementation for hybrid vector + graph document storage and retrieval.

## Overview

This package provides a minimal implementation of Core Nexus's hybrid memory system using:
- **Vector Storage**: JSON-based storage with cosine similarity search
- **Graph Storage**: SQLite-based node and relationship storage
- **Performance Target**: <500ms query latency

## Quick Start

```python
from core_memory_slice import LiteVectorStore, LiteGraphStore

# Initialize stores
vector_store = LiteVectorStore("./data/vectors.json")
graph_store = LiteGraphStore("./data/graph.db")

# Store document with same UUID in both stores
doc_id = "mem_12345"
embedding = [0.1, 0.2, 0.3, ...]  # 1536-dimensional vector
content = "Sample document content"

vector_store.upsert(doc_id, embedding, {"content": content})
graph_store.add_node(doc_id, content, {"type": "document"})

# Search and retrieve
query_embedding = [0.15, 0.25, 0.35, ...]
results = vector_store.search(query_embedding, k=5)
for doc_id, similarity, metadata in results:
    node = graph_store.get_node(doc_id)
    print(f"Found: {node['content']} (similarity: {similarity:.4f})")
```

## Performance

- **Vector Search**: O(n) linear scan with cosine similarity
- **Graph Queries**: SQLite with indexes for fast lookups
- **Storage**: Minimal memory footprint with disk persistence

## Scaling Path

This lite implementation provides hooks for production scaling:
- Replace JSON vector store with FAISS/Milvus
- Replace SQLite graph store with Neo4j
- Add OpenAI embeddings API integration
- Implement vector indexes (HNSW/IVF) for sub-10ms search

## Dependencies

Minimal dependencies for fast setup:
- Python 3.8+
- SQLite3 (built-in)
- JSON (built-in)
- No external vector libraries required