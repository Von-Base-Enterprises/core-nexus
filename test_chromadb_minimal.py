#!/usr/bin/env python3
"""
Minimal ChromaDB test to isolate the replication failure
Tests ChromaDB directly without the full provider system
"""

import asyncio
import sys
import os
from uuid import uuid4

async def test_chromadb_minimal():
    """Test ChromaDB with minimal setup to isolate the issue"""
    print("🔬 MINIMAL CHROMADB TEST")
    print("=" * 50)
    
    try:
        # Test ChromaDB import
        print("📦 Testing ChromaDB import...")
        import chromadb
        from chromadb.config import Settings
        print("✅ ChromaDB imported successfully")
        
        # Initialize client
        print("🏗️  Initializing ChromaDB client...")
        client = chromadb.PersistentClient(
            path="./test_chroma_db",
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        print("✅ ChromaDB client initialized")
        
        # Get or create collection
        print("📁 Setting up collection...")
        collection_name = "test_replication_debug"
        try:
            collection = client.get_collection(collection_name)
            print(f"✅ Loaded existing collection: {collection_name}")
        except:
            collection = client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            print(f"✅ Created new collection: {collection_name}")
        
        # Test direct write
        print("📝 Testing direct ChromaDB write...")
        test_id = str(uuid4())
        test_embedding = [0.1 + i*0.001 for i in range(1536)]  # Valid 1536-dim embedding
        test_content = "ChromaDB replication failure diagnostic test"
        test_metadata = {
            "test_type": "replication_debug",
            "importance_score": 0.5,
            "created_at": "2025-06-20T06:30:00Z"
        }
        
        # This is exactly what the ChromaProvider.store() method does
        collection.add(
            embeddings=[test_embedding],
            documents=[test_content], 
            metadatas=[test_metadata],
            ids=[test_id]
        )
        print(f"✅ ChromaDB write successful! ID: {test_id}")
        
        # Test count
        count = collection.count()
        print(f"📊 Collection count after write: {count}")
        
        # Test query
        print("🔍 Testing ChromaDB query...")
        results = collection.query(
            query_embeddings=[test_embedding],
            n_results=1,
            include=['metadatas', 'documents', 'distances']
        )
        
        if results['ids'] and len(results['ids'][0]) > 0:
            print(f"✅ Query successful! Found: {results['documents'][0][0][:50]}...")
            print(f"   Distance: {results['distances'][0][0]}")
        else:
            print("❌ Query returned no results")
        
        # Clean up
        client.delete_collection(collection_name)
        print("🧹 Test collection deleted")
        
        return True
        
    except Exception as e:
        print(f"❌ ChromaDB test failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

async def test_async_executor_pattern():
    """Test the specific async executor pattern used in ChromaProvider"""
    print("\n🔄 TESTING ASYNC EXECUTOR PATTERN")
    print("=" * 50)
    
    try:
        import chromadb
        from chromadb.config import Settings
        
        # Initialize like the provider does
        client = chromadb.PersistentClient(
            path="./test_executor_chroma",
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        collection = client.create_collection(
            name="test_executor",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Test the exact pattern from ChromaProvider.store()
        test_id = str(uuid4())
        test_embedding = [0.1 + i*0.001 for i in range(1536)]
        test_content = "Async executor pattern test"
        test_metadata = {"test": "executor_pattern"}
        
        loop = asyncio.get_event_loop()
        
        def _store():
            collection.add(
                embeddings=[test_embedding],
                documents=[test_content],
                metadatas=[test_metadata],
                ids=[test_id]
            )
        
        print("🔄 Running ChromaDB write in executor...")
        await loop.run_in_executor(None, _store)
        print("✅ Async executor write successful!")
        
        # Check count
        count = collection.count()
        print(f"📊 Count after async write: {count}")
        
        # Clean up
        client.delete_collection("test_executor")
        
        return True
        
    except Exception as e:
        print(f"❌ Async executor test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all ChromaDB diagnostic tests"""
    print("🚨 CHROMADB REPLICATION FAILURE DIAGNOSTIC")
    print("Objective: Identify why ChromaDB writes are failing in replication")
    print()
    
    # Test 1: Basic ChromaDB functionality
    basic_works = await test_chromadb_minimal()
    
    # Test 2: Async executor pattern (what the provider actually uses)
    executor_works = await test_async_executor_pattern()
    
    print(f"\n📊 DIAGNOSTIC RESULTS:")
    print(f"  Basic ChromaDB Write: {'✅ WORKING' if basic_works else '❌ BROKEN'}")
    print(f"  Async Executor Pattern: {'✅ WORKING' if executor_works else '❌ BROKEN'}")
    
    if basic_works and executor_works:
        print(f"\n🎯 DIAGNOSIS: ChromaDB functionality is working properly")
        print(f"   Issue must be in the provider configuration or initialization")
        print(f"   Next: Check if ChromaDB provider is enabled in production")
    elif not basic_works:
        print(f"\n🎯 DIAGNOSIS: ChromaDB library itself has issues")
        print(f"   Next: Check ChromaDB installation and dependencies")
    else:
        print(f"\n🎯 DIAGNOSIS: Async executor pattern is broken")
        print(f"   Next: Fix the async executor implementation in ChromaProvider")

if __name__ == "__main__":
    asyncio.run(main())