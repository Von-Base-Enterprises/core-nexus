#!/usr/bin/env python3
"""
Day-1 Vertical Slice: Query stored documents
Usage: python scripts/query_one.py [query_text]
"""

import sys
import os
import time
import hashlib

# Add the python package to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

from core_memory_slice import LiteVectorStore, LiteGraphStore


def create_mock_embedding(text: str, dim: int = 1536) -> list[float]:
    """Create deterministic mock embedding for testing"""
    hash_bytes = hashlib.md5(text.encode()).digest()
    embedding = []
    for i in range(dim):
        byte_idx = i % len(hash_bytes)
        embedding.append(float(hash_bytes[byte_idx]) / 255.0)
    return embedding


def query_documents(query: str, data_dir: str = "./slice_data", k: int = 3) -> dict:
    """Query hybrid storage for relevant documents"""
    start_time = time.perf_counter()
    
    # Initialize stores
    vector_store = LiteVectorStore(f"{data_dir}/vectors.json")
    graph_store = LiteGraphStore(f"{data_dir}/graph.db")
    
    # Generate query embedding
    query_embedding = create_mock_embedding(query)
    
    # Search vector store
    vector_results = vector_store.search(query_embedding, k=k)
    
    # Enhance with graph data
    results = []
    for doc_id, similarity, metadata in vector_results:
        graph_node = graph_store.get_node(doc_id)
        if graph_node:
            results.append({
                "doc_id": doc_id,
                "similarity": similarity,
                "content": graph_node["content"],
                "vector_metadata": metadata,
                "graph_metadata": graph_node["metadata"],
                "created_at": graph_node.get("created_at")
            })
    
    latency_ms = (time.perf_counter() - start_time) * 1000
    
    return {
        "query": query,
        "results": results,
        "latency_ms": latency_ms,
        "total_vectors": vector_store.count(),
        "total_nodes": graph_store.count_nodes()
    }


def main():
    # Default test query
    default_query = "crop stress report sector 7"
    
    # Use command line argument or default
    query = sys.argv[1] if len(sys.argv) > 1 else default_query
    
    print("🔍 Core Nexus Day-1 Slice - Document Query")
    print("=" * 50)
    
    # Check if data exists
    data_dir = "./slice_data"
    if not os.path.exists(f"{data_dir}/vectors.json") or not os.path.exists(f"{data_dir}/graph.db"):
        print("❌ No data found! Please run 'python scripts/ingest_one.py' first.")
        sys.exit(1)
    
    try:
        result = query_documents(query)
        
        print(f"🎯 Query: {result['query']}")
        print(f"⚡ Query latency: {result['latency_ms']:.2f} ms")
        print(f"📊 Searched {result['total_vectors']} vectors, {result['total_nodes']} nodes")
        print(f"📝 Found {len(result['results'])} results")
        
        # Performance check
        if result['latency_ms'] < 500:
            print(f"🎯 SUCCESS: Query latency {result['latency_ms']:.2f}ms < 500ms target")
        else:
            print(f"❌ FAIL: Query latency {result['latency_ms']:.2f}ms >= 500ms target")
        
        if result['results']:
            print("\n--- Top Results ---")
            for i, res in enumerate(result['results'][:3], 1):
                print(f"\n{i}. Document ID: {res['doc_id']}")
                print(f"   Similarity: {res['similarity']:.4f}")
                print(f"   Content: {res['content']}")
                print(f"   Created: {res['created_at']}")
        else:
            print("\n❌ No results found! Check if documents are ingested correctly.")
            
    except Exception as e:
        print(f"❌ Error during query: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
