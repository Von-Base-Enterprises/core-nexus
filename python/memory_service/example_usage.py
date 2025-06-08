#!/usr/bin/env python3
"""
Example usage of the Core Nexus Unified Memory Service

Demonstrates how to use the LTMM with existing vector providers
while preparing for integration with the larger Core Nexus system.
"""

import asyncio
import logging
import os
from typing import List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the src directory to the path for imports
import sys
sys.path.insert(0, 'src')

from memory_service import (
    UnifiedVectorStore, MemoryRequest, MemoryResponse, 
    QueryRequest, ChromaProvider, ProviderConfig
)


async def demonstrate_memory_service():
    """
    Demonstrate the unified memory service capabilities.
    
    Shows storage, querying, and provider management.
    """
    
    print("🧠 Core Nexus Memory Service Demo")
    print("=" * 50)
    
    # Step 1: Initialize ChromaDB provider (works without external dependencies)
    print("\n1. Initializing ChromaDB provider...")
    
    chroma_config = ProviderConfig(
        name="chromadb",
        enabled=True,
        primary=True,
        config={
            "collection_name": "demo_memories",
            "persist_directory": "./demo_chroma_db"
        }
    )
    
    try:
        chroma_provider = ChromaProvider(chroma_config)
        print("✅ ChromaDB provider initialized")
    except Exception as e:
        print(f"❌ Failed to initialize ChromaDB: {e}")
        return
    
    # Step 2: Create unified store
    print("\n2. Creating unified vector store...")
    
    unified_store = UnifiedVectorStore([chroma_provider])
    print(f"✅ Unified store created with {len(unified_store.providers)} provider(s)")
    
    # Step 3: Store some demo memories
    print("\n3. Storing demo memories...")
    
    demo_memories = [
        {
            "content": "The user prefers morning meetings and uses Python for data analysis projects.",
            "user_id": "user_123",
            "conversation_id": "conv_001",
            "metadata": {"topic": "preferences", "importance": "high"}
        },
        {
            "content": "Discussed the benefits of vector databases for semantic search applications.",
            "user_id": "user_123", 
            "conversation_id": "conv_002",
            "metadata": {"topic": "technical", "importance": "medium"}
        },
        {
            "content": "User mentioned working on a machine learning project involving natural language processing.",
            "user_id": "user_123",
            "conversation_id": "conv_003", 
            "metadata": {"topic": "projects", "importance": "high"}
        }
    ]
    
    stored_memories: List[MemoryResponse] = []
    
    for i, memory_data in enumerate(demo_memories):
        try:
            memory_request = MemoryRequest(**memory_data)
            # Note: In real usage, you'd have an embedding model configured
            # For demo purposes, we'll use mock embeddings
            memory_request.embedding = [0.1] * 1536  # Mock OpenAI embedding
            
            memory = await unified_store.store_memory(memory_request)
            stored_memories.append(memory)
            print(f"  ✅ Stored memory {i+1}: {memory.id}")
            
        except Exception as e:
            print(f"  ❌ Failed to store memory {i+1}: {e}")
    
    # Step 4: Query memories
    print(f"\n4. Querying memories (stored {len(stored_memories)} total)...")
    
    test_queries = [
        "What are the user's preferences?",
        "Tell me about technical discussions",
        "What projects is the user working on?"
    ]
    
    for query_text in test_queries:
        try:
            query = QueryRequest(
                query=query_text,
                limit=5,
                min_similarity=0.0,  # Lower threshold for demo
                user_id="user_123"
            )
            
            # Mock query embedding
            query_embedding = [0.1] * 1536
            
            # For demo, we'll directly call the provider since we don't have embedding model
            results = await chroma_provider.query(
                query_embedding=query_embedding,
                limit=query.limit,
                filters={"user_id": query.user_id} if query.user_id else {}
            )
            
            print(f"\n  🔍 Query: '{query_text}'")
            print(f"  📊 Found {len(results)} memories:")
            
            for j, memory in enumerate(results[:3]):  # Show top 3
                print(f"    {j+1}. {memory.content[:80]}...")
                print(f"       Similarity: {memory.similarity_score:.3f}, Importance: {memory.importance_score:.3f}")
                
        except Exception as e:
            print(f"  ❌ Query failed: {e}")
    
    # Step 5: Health check
    print("\n5. Checking service health...")
    
    try:
        health = await unified_store.health_check()
        print(f"  🏥 Service status: {health['status']}")
        print(f"  📈 Total stores: {health['stats']['total_stores']}")
        print(f"  ⚡ Avg query time: {health['stats']['avg_query_time']:.2f}ms")
        
        for provider_name, provider_health in health['providers'].items():
            status = provider_health['status']
            emoji = "✅" if status == "healthy" else "❌"
            primary = " (PRIMARY)" if provider_health.get('primary') else ""
            print(f"  {emoji} {provider_name}: {status}{primary}")
            
    except Exception as e:
        print(f"  ❌ Health check failed: {e}")
    
    # Step 6: Show statistics
    print("\n6. Service statistics...")
    print(f"  📊 Stats: {unified_store.stats}")
    
    print("\n" + "=" * 50)
    print("🎉 Demo completed!")
    print("\nNext steps:")
    print("- Add OpenAI embeddings integration")
    print("- Configure Pinecone for cloud scale")  
    print("- Add pgvector for SQL queries")
    print("- Integrate with existing Core Nexus APIs")


async def demonstrate_api_server():
    """
    Demonstrate running the FastAPI server.
    
    Shows how to integrate with the REST API.
    """
    print("\n🌐 API Server Demo")
    print("=" * 30)
    
    try:
        from memory_service.api import create_memory_app
        
        app = create_memory_app()
        print("✅ FastAPI app created successfully")
        print("📡 To run the server, use:")
        print("   uvicorn memory_service.api:app --reload --port 8000")
        print("📖 API docs available at: http://localhost:8000/docs")
        
        # Show available endpoints
        print("\n🛣️ Available endpoints:")
        for route in app.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                methods = ', '.join(route.methods)
                print(f"  {methods:12} {route.path}")
                
    except Exception as e:
        print(f"❌ Failed to create API app: {e}")


if __name__ == "__main__":
    print("🚀 Starting Core Nexus Memory Service Examples")
    
    # Run the main demo
    asyncio.run(demonstrate_memory_service())
    
    # Show API demo
    asyncio.run(demonstrate_api_server())
    
    print("\n✨ All demos completed!")
    print("💡 Check the generated ./demo_chroma_db directory for persisted data")