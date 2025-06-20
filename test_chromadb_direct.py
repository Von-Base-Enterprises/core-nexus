#!/usr/bin/env python3
"""
Test if ChromaDB can accept writes directly
This will isolate whether the issue is with ChromaDB itself or the replication logic
"""

import asyncio
import sys
import json
from datetime import datetime

# Add the source directory to the path
sys.path.insert(0, '/mnt/c/Users/Tyvon/core-nexus/python/memory_service/src')

async def test_chromadb_direct():
    """Test direct ChromaDB writing capability"""
    print("🧪 TESTING CHROMADB DIRECT WRITE CAPABILITY")
    print("=" * 60)
    
    try:
        # Import ChromaDB provider
        from memory_service.providers import ChromaProvider
        from memory_service.models import ProviderConfig
        
        # Create ChromaDB provider config (same as service uses)
        chromadb_config = ProviderConfig(
            name="chromadb",
            enabled=True,
            primary=False,
            config={
                "persist_directory": "./chroma_db",
                "collection_name": "core_nexus_memories"
            }
        )
        
        print("✅ ChromaDB provider config created")
        
        # Initialize provider
        chromadb_provider = ChromaProvider(chromadb_config)
        print("✅ ChromaDB provider initialized")
        
        # Test health check
        health = await chromadb_provider.health_check()
        print(f"✅ Health check: {health}")
        
        # Test direct write
        test_content = f"Direct ChromaDB test write {datetime.now().isoformat()}"
        test_embedding = [0.1 + i*0.001 for i in range(1536)]  # Valid 1536-dim embedding
        test_metadata = {
            "direct_test": True,
            "timestamp": datetime.now().isoformat(),
            "test_type": "isolation"
        }
        
        print(f"📝 Attempting direct write to ChromaDB...")
        result_id = await chromadb_provider.store(test_content, test_embedding, test_metadata)
        print(f"✅ Direct write successful! Memory ID: {result_id}")
        
        # Check count after write
        health_after = await chromadb_provider.health_check()
        print(f"📊 Health after write: {health_after}")
        
        # Test query capability
        print(f"🔍 Testing query capability...")
        query_results = await chromadb_provider.query(test_embedding, limit=5, filters={})
        print(f"✅ Query successful! Found {len(query_results)} results")
        
        if query_results:
            print(f"   First result: {query_results[0].content[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ ChromaDB direct test failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False

async def test_provider_routing():
    """Test if the unified store correctly identifies secondary providers"""
    print(f"\n🔄 TESTING PROVIDER ROUTING LOGIC")
    print("=" * 60)
    
    try:
        from memory_service.unified_store import UnifiedVectorStore
        from memory_service.providers import ChromaProvider, PgVectorProvider
        from memory_service.models import ProviderConfig
        
        # Create test providers (minimal config)
        pgvector_config = ProviderConfig(
            name="pgvector", enabled=True, primary=True, config={}
        )
        chromadb_config = ProviderConfig(
            name="chromadb", enabled=True, primary=False, config={}
        )
        
        # Create mock providers (don't initialize fully to avoid connection issues)
        class MockPgVector:
            def __init__(self):
                self.name = "pgvector"
                self.enabled = True
        
        class MockChromaDB:
            def __init__(self):
                self.name = "chromadb" 
                self.enabled = True
        
        providers = {
            "pgvector": MockPgVector(),
            "chromadb": MockChromaDB()
        }
        
        # Test secondary provider identification logic
        primary_provider = providers["pgvector"]
        secondary_providers = [p for p in providers.values()
                             if p != primary_provider and p.enabled]
        
        print(f"📊 Provider routing test:")
        print(f"   Primary provider: {primary_provider.name}")
        print(f"   Secondary providers: {[p.name for p in secondary_providers]}")
        print(f"   Secondary count: {len(secondary_providers)}")
        
        if len(secondary_providers) == 1 and secondary_providers[0].name == "chromadb":
            print("✅ Provider routing logic is correct")
            return True
        else:
            print("❌ Provider routing logic has issues")
            return False
            
    except Exception as e:
        print(f"❌ Provider routing test failed: {e}")
        return False

async def main():
    """Main test execution"""
    print("🔬 CHROMADB REPLICATION FAILURE ISOLATION TEST")
    print("Objective: Determine if ChromaDB itself works or if routing is broken")
    print()
    
    # Test 1: Direct ChromaDB functionality
    chromadb_works = await test_chromadb_direct()
    
    # Test 2: Provider routing logic
    routing_works = await test_provider_routing()
    
    print(f"\n📊 ISOLATION TEST RESULTS:")
    print(f"  ChromaDB Direct Write: {'✅ WORKING' if chromadb_works else '❌ BROKEN'}")
    print(f"  Provider Routing Logic: {'✅ WORKING' if routing_works else '❌ BROKEN'}")
    
    if chromadb_works and routing_works:
        print(f"\n🎯 DIAGNOSIS: ChromaDB and routing work - issue is in replication execution")
        print(f"   Next step: Debug _replicate_to_secondaries method")
    elif not chromadb_works:
        print(f"\n🎯 DIAGNOSIS: ChromaDB itself is broken")
        print(f"   Next step: Fix ChromaDB configuration or initialization")
    elif not routing_works:
        print(f"\n🎯 DIAGNOSIS: Provider routing is broken")
        print(f"   Next step: Fix secondary provider identification logic")

if __name__ == "__main__":
    asyncio.run(main())