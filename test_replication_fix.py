#!/usr/bin/env python3
"""
Test the replication fix by creating a new memory and verifying it appears in both providers
"""

import asyncio
import httpx
import time
from datetime import datetime

API_BASE = "https://core-nexus-memory-service.onrender.com"

async def test_replication_fix():
    """Test that new memories are properly replicated to all providers"""
    print("🧪 Testing Replication Fix")
    print("="*50)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get current counts
        print("📊 Checking current provider counts...")
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
        
        # Create a test memory
        test_content = f"🧪 Replication test memory created at {datetime.now().isoformat()}"
        
        print(f"\n📝 Creating test memory...")
        print(f"Content: {test_content[:50]}...")
        
        create_response = await client.post(
            f"{API_BASE}/memories",
            json={
                "content": test_content,
                "metadata": {
                    "test": True,
                    "test_type": "replication_fix",
                    "created_at": datetime.now().isoformat()
                }
            }
        )
        
        if create_response.status_code != 200:
            print(f"❌ Memory creation failed: {create_response.status_code}")
            print(f"Response: {create_response.text}")
            return
            
        memory_data = create_response.json()
        memory_id = memory_data.get("id")
        print(f"✅ Memory created with ID: {memory_id}")
        
        # Wait a moment for replication
        print("⏳ Waiting 5 seconds for replication...")
        await asyncio.sleep(5)
        
        # Check counts again
        print("\n📊 Checking provider counts after creation...")
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
            
            # Analyze results
            print(f"\n🔍 Analysis:")
            if pgvector_after > pgvector_before:
                print("✅ Memory successfully stored in pgvector")
            else:
                print("❌ Memory not found in pgvector")
                
            if chromadb_after > chromadb_before:
                print("✅ Memory successfully replicated to ChromaDB")
                print("🎉 REPLICATION FIX IS WORKING!")
            else:
                print("❌ Memory not replicated to ChromaDB")
                print("⚠️ Replication fix may not be working yet")
                print("   This could be because:")
                print("   - The fix hasn't been deployed yet")
                print("   - ChromaDB provider is disabled")
                print("   - There's still an issue with the replication logic")
                
            # Check if sync gap is decreasing
            old_gap = pgvector_before - chromadb_before
            new_gap = pgvector_after - chromadb_after
            
            if new_gap < old_gap:
                print("✅ Sync gap is decreasing - replication is working")
            elif new_gap == old_gap and chromadb_after > chromadb_before:
                print("✅ Sync gap maintained - replication is working")
            else:
                print("⚠️ Sync gap not improving")

async def main():
    try:
        await test_replication_fix()
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())