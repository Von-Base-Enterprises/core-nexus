#!/usr/bin/env python3
"""
Simulate the exact replication scenario to identify the failure point
This recreates the production replication logic locally
"""

import asyncio
import sys
import os
import logging
from uuid import uuid4
from datetime import datetime

# Add the source directory to the path
sys.path.insert(0, '/mnt/c/Users/Tyvon/core-nexus/python/memory_service/src')

# Setup logging to see detailed output
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def simulate_replication_scenario():
    """Simulate the exact scenario that's failing in production"""
    print("🔄 SIMULATING PRODUCTION REPLICATION SCENARIO")
    print("=" * 60)
    
    try:
        # Import the exact classes used in production
        from memory_service.providers import ChromaProvider, PgVectorProvider
        from memory_service.models import ProviderConfig
        
        # Create ChromaDB provider with SAME config as production
        chroma_config = ProviderConfig(
            name="chromadb",
            enabled=True,
            primary=False,  # Secondary like in production
            config={
                "collection_name": "core_nexus_memories",
                "persist_directory": "./simulation_chroma"  # Local test directory
            }
        )
        
        print("🏗️  Initializing ChromaDB provider (like production)...")
        chroma_provider = ChromaProvider(chroma_config)
        print(f"✅ ChromaDB initialized: {chroma_provider.enabled}")
        
        # Test the exact data that would be replicated
        print("📝 Testing replication data format...")
        test_memory_id = uuid4()
        test_content = "Replication simulation test - ChromaDB should receive this"
        test_embedding = [0.1 + i*0.001 for i in range(1536)]  # Valid embedding
        test_metadata = {
            "user_id": None,
            "conversation_id": None, 
            "importance_score": 0.5,
            "created_at": 1750401024.0,
            "content_length": len(test_content),
            "simulation_test": True
        }
        
        print(f"   Memory ID: {test_memory_id}")
        print(f"   Content length: {len(test_content)}")
        print(f"   Embedding dimension: {len(test_embedding)}")
        print(f"   Metadata keys: {list(test_metadata.keys())}")
        
        # This is the EXACT call made in _replicate_to_secondaries
        print("🔄 Executing exact replication call...")
        stored_id = await chroma_provider.store(test_content, test_embedding, test_metadata)
        print(f"✅ Replication successful! Stored ID: {stored_id}")
        
        # Verify the write worked
        health = await chroma_provider.health_check()
        print(f"📊 ChromaDB count after replication: {health['details']['total_vectors']}")
        
        # Test query to ensure it's really there
        print("🔍 Testing query after replication...")
        query_results = await chroma_provider.query(test_embedding, limit=1, filters={})
        if query_results:
            print(f"✅ Query successful: {query_results[0].content[:50]}...")
        else:
            print("❌ Query returned no results")
        
        return True
        
    except Exception as e:
        print(f"❌ Replication simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_replication_with_retry():
    """Test the _store_with_retry pattern used in replication"""
    print(f"\n🔄 TESTING RETRY PATTERN")
    print("=" * 50)
    
    try:
        from memory_service.providers import ChromaProvider
        from memory_service.models import ProviderConfig
        
        # Create provider
        config = ProviderConfig(
            name="chromadb",
            enabled=True,
            primary=False,
            retry_count=3,  # Test retry logic
            config={
                "collection_name": "retry_test",
                "persist_directory": "./retry_test_chroma"
            }
        )
        
        provider = ChromaProvider(config)
        
        # Test the exact retry pattern from _store_with_retry
        test_content = "Retry pattern test"
        test_embedding = [0.1] * 1536
        test_metadata = {"retry_test": True}
        
        for attempt in range(config.retry_count):
            try:
                print(f"   Attempt {attempt + 1}/{config.retry_count}...")
                result_id = await provider.store(test_content, test_embedding, test_metadata)
                print(f"✅ Retry pattern successful on attempt {attempt + 1}: {result_id}")
                return True
            except Exception as e:
                if attempt == config.retry_count - 1:
                    raise
                print(f"   ⚠️  Attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        return False
        
    except Exception as e:
        print(f"❌ Retry pattern test failed: {e}")
        return False

async def test_async_loop_context():
    """Test if there are any async loop context issues"""
    print(f"\n🔄 TESTING ASYNC LOOP CONTEXT")
    print("=" * 50)
    
    try:
        from memory_service.providers import ChromaProvider
        from memory_service.models import ProviderConfig
        
        config = ProviderConfig(
            name="chromadb",
            enabled=True,
            primary=False,
            config={
                "collection_name": "loop_test",
                "persist_directory": "./loop_test_chroma"
            }
        )
        
        provider = ChromaProvider(config)
        
        # Test multiple writes in sequence (like production)
        print("📝 Testing sequential writes (production pattern)...")
        for i in range(3):
            test_id = str(uuid4())
            test_content = f"Loop test {i+1}"
            test_embedding = [0.1 + i*0.01] * 1536
            test_metadata = {"loop_test": i+1}
            
            stored_id = await provider.store(test_content, test_embedding, test_metadata)
            print(f"   Write {i+1}: ✅ {stored_id}")
        
        # Check final count
        health = await provider.health_check()
        count = health['details']['total_vectors']
        print(f"📊 Final count: {count}")
        
        if count == 3:
            print("✅ All sequential writes successful")
            return True
        else:
            print(f"❌ Expected 3 writes, got {count}")
            return False
        
    except Exception as e:
        print(f"❌ Async loop context test failed: {e}")
        return False

async def main():
    """Run all replication simulation tests"""
    print("🚨 REPLICATION FAILURE SIMULATION")
    print("Objective: Reproduce the exact replication failure scenario")
    print()
    
    # Test 1: Exact replication scenario
    replication_works = await simulate_replication_scenario()
    
    # Test 2: Retry pattern
    retry_works = await test_replication_with_retry()
    
    # Test 3: Async loop context
    loop_works = await test_async_loop_context()
    
    print(f"\n📊 SIMULATION RESULTS:")
    print(f"  Replication Scenario: {'✅ WORKING' if replication_works else '❌ BROKEN'}")
    print(f"  Retry Pattern: {'✅ WORKING' if retry_works else '❌ BROKEN'}")
    print(f"  Async Loop Context: {'✅ WORKING' if loop_works else '❌ BROKEN'}")
    
    if all([replication_works, retry_works, loop_works]):
        print(f"\n🎯 DIAGNOSIS: Replication logic works perfectly locally")
        print(f"   Issue must be in the production environment:")
        print(f"   1. Directory permissions in Render")
        print(f"   2. Ephemeral file system issues")
        print(f"   3. Provider not actually being included in secondaries list")
        print(f"   Next: Check if ChromaDB provider is in the secondary providers list")
    else:
        print(f"\n🎯 DIAGNOSIS: Found specific replication logic issues")
        print(f"   Fix the failed patterns before deploying")

if __name__ == "__main__":
    asyncio.run(main())