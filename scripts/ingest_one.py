#!/usr/bin/env python3
"""
Day-1 Vertical Slice: Ingest ONE document
Usage: python scripts/ingest_one.py [document_text]
"""

import hashlib
import os
import sys
import time
import uuid

# Add the python package to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

from core_memory_slice import LiteGraphStore, LiteVectorStore


def create_mock_embedding(text: str, dim: int = 1536) -> list[float]:
    """Create deterministic mock embedding for testing"""
    hash_bytes = hashlib.md5(text.encode()).digest()
    embedding = []
    for i in range(dim):
        byte_idx = i % len(hash_bytes)
        embedding.append(float(hash_bytes[byte_idx]) / 255.0)
    return embedding


def ingest_document(content: str, data_dir: str = "./slice_data") -> dict:
    """Ingest document into hybrid storage"""
    start_time = time.perf_counter()

    # Ensure data directory exists
    os.makedirs(data_dir, exist_ok=True)

    # Generate UUID for this document
    doc_id = f"mem_{uuid.uuid4().hex[:8]}"

    # Create embedding (mock for demo - replace with OpenAI API)
    embedding = create_mock_embedding(content)

    # Initialize stores
    vector_store = LiteVectorStore(f"{data_dir}/vectors.json")
    graph_store = LiteGraphStore(f"{data_dir}/graph.db")

    # Store in both systems with same UUID
    vector_store.upsert(doc_id, embedding, {
        "content": content,
        "timestamp": time.time(),
        "type": "document"
    })

    graph_store.add_node(doc_id, content, {
        "type": "document",
        "embedding_dim": len(embedding),
        "timestamp": time.time()
    })

    latency_ms = (time.perf_counter() - start_time) * 1000

    return {
        "doc_id": doc_id,
        "latency_ms": latency_ms,
        "embedding_dim": len(embedding),
        "content": content,
        "vector_count": vector_store.count(),
        "node_count": graph_store.count_nodes()
    }


def main():
    # Default test document
    default_doc = "Drone inspection of north field shows 15% crop stress in sector 7"

    # Use command line argument or default
    document = sys.argv[1] if len(sys.argv) > 1 else default_doc

    print("🚀 Core Nexus Day-1 Slice - Document Ingestion")
    print("=" * 50)

    try:
        result = ingest_document(document)

        print("✅ Document ingested successfully!")
        print(f"📄 Content: {result['content']}")
        print(f"🔑 Document ID: {result['doc_id']}")
        print(f"⚡ Ingest latency: {result['latency_ms']:.2f} ms")
        print(f"📊 Embedding dimension: {result['embedding_dim']}")
        print(f"💾 Total vectors stored: {result['vector_count']}")
        print(f"🌐 Total graph nodes: {result['node_count']}")

        # Performance check
        if result['latency_ms'] < 2000:  # 2 second target
            print("🎯 SUCCESS: Ingest latency under 2s target")
        else:
            print(f"⚠️  WARNING: Ingest latency {result['latency_ms']:.2f}ms >= 2s")

    except Exception as e:
        print(f"❌ Error during ingestion: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
