#!/usr/bin/env python3
"""
Debug GraphRAG memory-entity mapping issue.
"""

import asyncio
import aiohttp
import json
from datetime import datetime

API_URL = "https://core-nexus-memory-service.onrender.com"
API_KEY = "test-key-67890"

async def debug_graphrag():
    headers = {"X-API-Key": API_KEY}
    
    async with aiohttp.ClientSession() as session:
        print("🔍 DEBUGGING GRAPHRAG MEMORY-ENTITY MAPPING")
        print("=" * 60)
        
        # Create a simple test memory
        print("\n1. Creating test memory...")
        test_memory = {
            "content": f"Debug test: Von Base Enterprises and Core Nexus are working together.",
            "metadata": {"debug": True},
            "importance_score": 0.8
        }
        
        memory_id = None
        try:
            async with session.post(f"{API_URL}/memories", headers={**headers, "Content-Type": "application/json"}, json=test_memory) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    memory_id = data.get('id')
                    print(f"   ✅ Memory created: {memory_id}")
                else:
                    print(f"   ❌ Failed: {resp.status}")
                    print(await resp.text())
                    return
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return
        
        # Wait for processing
        print("\n2. Waiting for entity extraction...")
        await asyncio.sleep(5)
        
        # Check if Von Base Enterprises entity exists
        print("\n3. Checking if entity exists...")
        query = {"entity_name": "Von Base Enterprises"}
        try:
            async with session.post(f"{API_URL}/graph/query", headers={**headers, "Content-Type": "application/json"}, json=query) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data['total_nodes'] > 0:
                        entity = data['nodes'][0]
                        print(f"   ✅ Entity found: {entity['entity_name']}")
                        print(f"      ID: {entity['id']}")
                        print(f"      Mentions: {entity['mention_count']}")
                    else:
                        print(f"   ❌ Entity not found")
                else:
                    print(f"   ❌ Query failed: {resp.status}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Try to explore the entity
        print("\n4. Exploring entity for connected memories...")
        try:
            async with session.get(f"{API_URL}/graph/explore/Von Base Enterprises", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   Memories found: {data['memories_found']}")
                    if data['memories_found'] == 0:
                        print(f"   ⚠️  No memories connected to this entity!")
                        print(f"   This suggests memory-entity mappings aren't being created")
                    else:
                        for mem in data['memories'][:2]:
                            print(f"   - {mem['content'][:60]}...")
                else:
                    print(f"   ❌ Explore failed: {resp.status}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Check graph stats to see if relationships exist
        print("\n5. Checking relationship counts...")
        try:
            async with session.get(f"{API_URL}/graph/stats", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    stats = data['statistics']
                    print(f"   Total relationships: {stats['total_relationships']}")
                    print(f"   Relationship types: {stats['relationship_types']}")
                else:
                    print(f"   ❌ Stats failed: {resp.status}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Query all memories to check if they have metadata
        print("\n6. Checking recent memories...")
        query_request = {
            "query": "",  # Empty query to get all
            "limit": 5,
            "min_similarity": 0.0
        }
        try:
            async with session.post(f"{API_URL}/memories/query", headers={**headers, "Content-Type": "application/json"}, json=query_request) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   Found {data['total_found']} memories")
                    if data['memories']:
                        mem = data['memories'][0]
                        print(f"   Sample memory ID: {mem['id']}")
                        print(f"   Content: {mem['content'][:60]}...")
                        print(f"   Metadata keys: {list(mem['metadata'].keys())}")
                else:
                    print(f"   ❌ Query failed: {resp.status}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print("\n" + "=" * 60)
        print("DIAGNOSIS:")
        print("The issue appears to be that memory-entity mappings are NOT being created.")
        print("This is likely because the GraphProvider.store() method is not being called")
        print("during replication, or it's failing silently.")
        print("\nPossible causes:")
        print("1. GraphProvider might not be enabled in production")
        print("2. Replication might be failing due to the memory_id requirement")
        print("3. Entity extraction might be failing in GraphProvider.store()")

if __name__ == "__main__":
    asyncio.run(debug_graphrag())