#\!/usr/bin/env python3
"""
Test GraphRAG after migration is complete.
"""

import asyncio
import aiohttp
import json
from datetime import datetime

API_URL = "https://core-nexus-memory-service.onrender.com"
API_KEY = "test-key-67890"

async def test_graphrag():
    headers = {"X-API-Key": API_KEY}
    
    async with aiohttp.ClientSession() as session:
        print("🧪 GRAPHRAG POST-MIGRATION TEST")
        print("=" * 60)
        
        # Test 1: Check graph statistics
        print("\n1. Graph Statistics:")
        try:
            async with session.get(f"{API_URL}/graph/stats", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    stats = data['statistics']
                    print(f"   Total nodes: {stats['total_nodes']}")
                    print(f"   Total relationships: {stats['total_relationships']}")
                    print(f"   Total entity-memory mappings: {stats.get('total_mappings', 'N/A')}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test 2: Entity exploration (should now return memories\!)
        print("\n2. Entity Exploration Results:")
        test_entities = ["Von Base Enterprises", "Core Nexus", "GraphRAG"]
        
        for entity in test_entities:
            try:
                async with session.get(f"{API_URL}/graph/explore/{entity}", headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"\n   {entity}:")
                        print(f"   - Memories found: {data['memories_found']}")
                        print(f"   - Related entities: {data['total_related_entities']}")
                        
                        if data['memories_found'] > 0:
                            print(f"   ✅ SUCCESS\! Entity has connected memories")
                            # Show first memory snippet
                            if data['memories']:
                                first_memory = data['memories'][0]
                                print(f"   - Sample memory: {first_memory['content'][:100]}...")
                        else:
                            print(f"   ⚠️  No memories found (migration may not have run)")
            except Exception as e:
                print(f"   Error checking {entity}: {e}")
        
        # Test 3: Multi-hop reasoning
        print("\n3. Multi-hop Query Test:")
        query = {
            "query": "Von Base Enterprises authentication Core Nexus",
            "max_hops": 3,
            "min_similarity": 0.5
        }
        
        try:
            async with session.post(f"{API_URL}/graph/query", 
                                  headers={**headers, "Content-Type": "application/json"}, 
                                  json=query) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   Nodes found: {data['total_nodes']}")
                    print(f"   Relationships: {data['total_relationships']}")
                    
                    if data['nodes']:
                        print("   ✅ Multi-hop query working\!")
                        for node in data['nodes'][:3]:
                            print(f"   - {node['entity_name']} ({node['entity_type']})")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test 4: Create new memory and verify immediate GraphRAG
        print("\n4. New Memory Test:")
        test_memory = {
            "content": f"Migration test {datetime.now()}: Von Base Enterprises successfully implemented GraphRAG with Core Nexus.",
            "metadata": {"test": "post-migration"},
            "importance_score": 0.9
        }
        
        try:
            async with session.post(f"{API_URL}/memories", 
                                  headers={**headers, "Content-Type": "application/json"}, 
                                  json=test_memory) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    memory_id = data.get('id')
                    print(f"   Created memory: {memory_id}")
                    
                    # Wait for processing
                    await asyncio.sleep(5)
                    
                    # Check if entities were extracted
                    async with session.get(f"{API_URL}/graph/explore/Von Base Enterprises", headers=headers) as resp2:
                        if resp2.status == 200:
                            data2 = await resp2.json()
                            print(f"   Von Base Enterprises now has {data2['memories_found']} memories")
                            print(f"   ✅ New memories are being processed correctly\!")
        except Exception as e:
            print(f"   Error: {e}")
        
        print("\n" + "=" * 60)
        print("TEST SUMMARY:")
        print("If all entities show connected memories, migration was successful\!")
        print("If entities still show 0 memories, the migration needs to be run.")

if __name__ == "__main__":
    asyncio.run(test_graphrag())
