#!/usr/bin/env python3
"""
Debug why replication is not working despite the fix being deployed
"""

import asyncio
import httpx
import json
from datetime import datetime

API_BASE = "https://core-nexus-memory-service.onrender.com"

async def debug_replication():
    """Comprehensive debugging of replication issue"""
    print("🔍 DEBUGGING REPLICATION ISSUE")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Check health endpoint for provider details
        print("1. 📊 Checking provider configuration...")
        response = await client.get(f"{API_BASE}/health")
        
        if response.status_code != 200:
            print(f"❌ Health check failed: {response.status_code}")
            return
            
        health_data = response.json()
        providers = health_data.get("providers", {})
        
        print(f"Found {len(providers)} providers:")
        for name, config in providers.items():
            status = config.get("status", "unknown")
            is_primary = config.get("primary", False)
            details = config.get("details", {})
            
            print(f"  {name}:")
            print(f"    Status: {status}")
            print(f"    Primary: {is_primary}")
            
            if "details" in details and "total_vectors" in details["details"]:
                vector_count = details["details"]["total_vectors"]
                print(f"    Vectors: {vector_count}")
            elif "total_vectors" in details:
                vector_count = details["total_vectors"]  
                print(f"    Vectors: {vector_count}")
            else:
                print(f"    Details: {json.dumps(details, indent=6)}")
                
        print()
        
        # 2. Check if ChromaDB is enabled and working
        chromadb_config = providers.get("chromadb", {})
        if not chromadb_config:
            print("❌ PROBLEM: ChromaDB provider not found in health response")
            return
            
        if chromadb_config.get("status") != "healthy":
            print(f"❌ PROBLEM: ChromaDB status is '{chromadb_config.get('status')}'")
            print(f"   Error: {chromadb_config.get('error', 'Unknown')}")
            return
            
        if not chromadb_config.get("primary", False):
            print("✅ ChromaDB is secondary provider (correct)")
        else:
            print("⚠️  ChromaDB is marked as primary (unexpected)")
        
        # 3. Test memory creation with detailed logging
        print("2. 📝 Testing memory creation with replication tracking...")
        
        test_content = f"🔍 Replication debug test - {datetime.now().isoformat()}"
        
        # Get before counts
        pgvector_before = providers.get("pgvector", {}).get("details", {}).get("details", {}).get("total_vectors", 0)
        chromadb_before = providers.get("chromadb", {}).get("details", {}).get("details", {}).get("total_vectors", 0)
        
        print(f"Before creation:")
        print(f"  pgvector: {pgvector_before}")
        print(f"  chromadb: {chromadb_before}")
        
        # Create memory
        create_response = await client.post(
            f"{API_BASE}/memories",
            json={
                "content": test_content,
                "metadata": {
                    "debug": True,
                    "test_type": "replication_debug",
                    "timestamp": datetime.now().isoformat()
                }
            }
        )
        
        if create_response.status_code != 200:
            print(f"❌ Memory creation failed: {create_response.status_code}")
            print(f"   Response: {create_response.text}")
            return
            
        memory_data = create_response.json()
        memory_id = memory_data.get("id")
        print(f"✅ Memory created: {memory_id}")
        
        # Wait and check again
        print("⏳ Waiting 10 seconds for replication...")
        await asyncio.sleep(10)
        
        # Get after counts
        response = await client.get(f"{API_BASE}/health")
        if response.status_code == 200:
            health_data = response.json()
            providers = health_data.get("providers", {})
            
            pgvector_after = providers.get("pgvector", {}).get("details", {}).get("details", {}).get("total_vectors", 0)
            chromadb_after = providers.get("chromadb", {}).get("details", {}).get("details", {}).get("total_vectors", 0)
            
            print(f"After creation:")
            print(f"  pgvector: {pgvector_after} (+{pgvector_after - pgvector_before})")
            print(f"  chromadb: {chromadb_after} (+{chromadb_after - chromadb_before})")
            
            # Analysis
            print("\n3. 🔍 Analysis:")
            if pgvector_after > pgvector_before:
                print("✅ Memory stored in pgvector successfully")
            else:
                print("❌ Memory NOT stored in pgvector")
                
            if chromadb_after > chromadb_before:
                print("✅ Memory replicated to ChromaDB successfully")
                print("🎉 REPLICATION IS WORKING!")
            else:
                print("❌ Memory NOT replicated to ChromaDB")
                print("\n🔍 Possible causes:")
                print("   1. ChromaDB provider is disabled in configuration")
                print("   2. ChromaDB initialization failed during startup")
                print("   3. Replication code is throwing exceptions (silently caught)")
                print("   4. ChromaDB storage is failing but health check passes")
                print("   5. Deployment hasn't taken effect yet")
                
        # 4. Check if we can query the new memory from both providers
        print("\n4. 🔍 Testing direct provider queries...")
        
        # This would require provider-specific endpoints or admin access
        print("   (Would need admin endpoints to test individual providers)")

async def main():
    try:
        await debug_replication()
    except Exception as e:
        print(f"❌ Debug failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())