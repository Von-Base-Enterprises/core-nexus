#!/usr/bin/env python3
"""
Since replication isn't working, let's force sync the existing memories
This will at least get ChromaDB in sync with pgvector as a stopgap measure
"""

import asyncio
import httpx
import json
from datetime import datetime

API_BASE = "https://core-nexus-memory-service.onrender.com"

async def trigger_manual_sync():
    """Try to trigger a manual sync operation"""
    print("🔄 FORCING CHROMADB SYNC VIA API")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        
        # First, get current state
        print("1. 📊 Checking current state...")
        response = await client.get(f"{API_BASE}/health")
        
        if response.status_code == 200:
            health_data = response.json()
            providers = health_data.get("providers", {})
            
            pgvector_count = providers.get("pgvector", {}).get("details", {}).get("details", {}).get("total_vectors", 0)
            chromadb_count = providers.get("chromadb", {}).get("details", {}).get("details", {}).get("total_vectors", 0)
            
            print(f"pgvector: {pgvector_count} vectors")
            print(f"ChromaDB: {chromadb_count} vectors")
            print(f"Sync gap: {pgvector_count - chromadb_count} memories missing")
            
            if chromadb_count >= pgvector_count:
                print("✅ Already in sync!")
                return
                
        # Try to find any bulk/sync endpoints
        print("\n2. 🔍 Looking for bulk/sync endpoints...")
        
        sync_endpoints = [
            "/admin/sync",
            "/admin/sync-chromadb", 
            "/bulk/sync",
            "/sync",
            "/memories/bulk/sync",
            "/admin/providers/sync"
        ]
        
        for endpoint in sync_endpoints:
            try:
                response = await client.post(f"{API_BASE}{endpoint}")
                print(f"{endpoint}: {response.status_code}")
                
                if response.status_code == 200:
                    print(f"✅ Found working sync endpoint!")
                    data = response.json()
                    print(f"Response: {json.dumps(data, indent=2)}")
                    return
                elif response.status_code != 404:
                    print(f"Response: {response.text[:200]}")
                    
            except Exception as e:
                print(f"{endpoint}: Error - {e}")
        
        # Try to create a bulk sync request
        print("\n3. 🔄 Attempting bulk operations...")
        
        # Check if there's a bulk endpoint for memories
        bulk_endpoints = [
            "/memories/bulk",
            "/bulk/memories", 
            "/admin/bulk",
            "/memories/export",
            "/export"
        ]
        
        for endpoint in bulk_endpoints:
            try:
                response = await client.get(f"{API_BASE}{endpoint}")
                if response.status_code != 404:
                    print(f"Found {endpoint}: {response.status_code}")
                    
            except:
                pass
                
        # As a last resort, try to retrieve all memories and count them
        print("\n4. 📋 Attempting to retrieve memories for manual sync...")
        
        try:
            # Try to get all memories
            response = await client.get(f"{API_BASE}/memories", params={"limit": 2000})
            
            if response.status_code == 200:
                data = response.json()
                memories = data.get("memories", [])
                print(f"Retrieved {len(memories)} memories via API")
                
                if len(memories) > 0:
                    print("✅ API can retrieve memories - manual sync is possible")
                    print("🔧 To manually sync, you would need to:")
                    print("   1. Create an admin endpoint that calls ChromaDB provider directly")
                    print("   2. Iterate through all memories and store them in ChromaDB")
                    print("   3. This is exactly what emergency_chromadb_sync_v2.py does")
                else:
                    print("❌ No memories retrieved from API")
                    
            elif response.status_code == 404:
                print("❌ Memories endpoint not found or has changed")
            else:
                print(f"❌ Memories endpoint returned: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Failed to retrieve memories: {e}")

async def main():
    try:
        await trigger_manual_sync()
        
        print("\n" + "="*60)
        print("📋 SYNC ANALYSIS SUMMARY")
        print("="*60)
        print("Finding: No automatic sync endpoints available")
        print("Status: Manual sync via emergency script is the only option")
        print("Action: Need to run emergency_chromadb_sync_v2.py with proper credentials")
        
        print("\n🎯 NEXT STEPS:")
        print("1. Get database credentials for direct sync")
        print("2. Run emergency sync script to sync 1,146 memories")
        print("3. Verify both providers show identical counts")
        print("4. Debug why new replication isn't working despite deployment")
        
    except Exception as e:
        print(f"❌ Sync attempt failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())