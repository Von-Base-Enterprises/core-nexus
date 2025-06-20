#!/usr/bin/env python3
"""
Test if replication is now working after service stabilization
If it is, new memories should start appearing in ChromaDB
"""

import asyncio
import httpx
import time
from datetime import datetime

API_BASE = "https://core-nexus-memory-service.onrender.com"

async def test_current_replication():
    """Test if replication is working now that service is stable"""
    print("🧪 TESTING CURRENT REPLICATION STATUS")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # 1. Get baseline counts
        print("1. 📊 Getting baseline counts...")
        response = await client.get(f"{API_BASE}/health")
        
        if response.status_code != 200:
            print(f"❌ Health check failed: {response.status_code}")
            return
            
        health_data = response.json()
        providers = health_data.get("providers", {})
        
        pgvector_before = providers.get("pgvector", {}).get("details", {}).get("details", {}).get("total_vectors", 0)
        chromadb_before = providers.get("chromadb", {}).get("details", {}).get("details", {}).get("total_vectors", 0)
        
        print(f"Before test:")
        print(f"  pgvector: {pgvector_before} vectors")
        print(f"  ChromaDB: {chromadb_before} vectors")
        print(f"  Sync gap: {pgvector_before - chromadb_before}")
        
        # 2. Create multiple test memories
        print("\n2. 📝 Creating test memories...")
        
        test_memories = []
        for i in range(3):
            test_content = f"🧪 Replication test #{i+1} - {datetime.now().isoformat()}"
            
            try:
                response = await client.post(
                    f"{API_BASE}/memories",
                    json={
                        "content": test_content,
                        "metadata": {
                            "replication_test": True,
                            "test_number": i + 1,
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                )
                
                if response.status_code == 200:
                    memory_data = response.json()
                    memory_id = memory_data.get("id")
                    test_memories.append(memory_id)
                    print(f"✅ Test memory {i+1} created: {memory_id}")
                else:
                    print(f"❌ Test memory {i+1} failed: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Test memory {i+1} exception: {e}")
                
        if not test_memories:
            print("❌ No test memories created - cannot test replication")
            return
            
        print(f"Created {len(test_memories)} test memories")
        
        # 3. Wait for replication
        print("\n3. ⏳ Waiting 15 seconds for replication...")
        await asyncio.sleep(15)
        
        # 4. Check counts again
        print("\n4. 📊 Checking post-creation counts...")
        response = await client.get(f"{API_BASE}/health")
        
        if response.status_code == 200:
            health_data = response.json()
            providers = health_data.get("providers", {})
            
            pgvector_after = providers.get("pgvector", {}).get("details", {}).get("details", {}).get("total_vectors", 0)
            chromadb_after = providers.get("chromadb", {}).get("details", {}).get("details", {}).get("total_vectors", 0)
            
            print(f"After test:")
            print(f"  pgvector: {pgvector_after} vectors (+{pgvector_after - pgvector_before})")
            print(f"  ChromaDB: {chromadb_after} vectors (+{chromadb_after - chromadb_before})")
            print(f"  New sync gap: {pgvector_after - chromadb_after}")
            
            # 5. Analysis
            print(f"\n5. 🔍 Replication analysis:")
            
            pgvector_gained = pgvector_after - pgvector_before
            chromadb_gained = chromadb_after - chromadb_before
            
            if pgvector_gained >= len(test_memories):
                print("✅ pgvector received new memories")
            else:
                print("❌ pgvector didn't receive all new memories")
                
            if chromadb_gained >= len(test_memories):
                print("🎉 SUCCESS: ChromaDB replication is WORKING!")
                print(f"   ChromaDB gained {chromadb_gained} vectors")
                print("   New memories are being replicated properly")
                
                # Calculate improvement
                if pgvector_before > 0:
                    sync_improvement = chromadb_gained / pgvector_before * 100
                    print(f"   Sync improvement: +{sync_improvement:.2f}% of total")
                    
                return True
                
            elif chromadb_gained > 0:
                print("⚠️ PARTIAL SUCCESS: ChromaDB replication partially working")
                print(f"   ChromaDB gained {chromadb_gained} vectors (expected {len(test_memories)})")
                print("   Some replication is happening but not complete")
                
                return False
                
            else:
                print("❌ FAILURE: ChromaDB replication still not working")
                print("   ChromaDB gained 0 vectors")
                print("   Replication architecture still broken")
                
                print("\n🔍 Possible remaining issues:")
                print("   1. ChromaDB provider not actually enabled in secondary list")
                print("   2. Exception in replication code being silently caught")
                print("   3. ChromaDB storage failing but health check passing")
                print("   4. Configuration issue with ChromaDB initialization")
                
                return False
        else:
            print(f"❌ Post-test health check failed: {response.status_code}")
            return False

async def main():
    try:
        success = await test_current_replication()
        
        print("\n" + "="*60)
        print("📋 REPLICATION TEST SUMMARY")
        print("="*60)
        
        if success:
            print("🎉 RESULT: Replication is working for new memories!")
            print("Next steps:")
            print("1. ✅ Replication fix is active")
            print("2. 📋 Need to sync existing 1,149 memories")
            print("3. 🚀 Can proceed with performance migration")
        else:
            print("❌ RESULT: Replication still not working properly")
            print("Next steps:")
            print("1. 🔧 Debug replication code further")
            print("2. 💾 Try alternative sync methods")
            print("3. 🔍 Check service logs for errors")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())