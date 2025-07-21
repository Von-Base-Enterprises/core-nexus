#!/usr/bin/env python3
"""
Verify GraphRAG status before running migration.
"""

import asyncio
import aiohttp
import json
from datetime import datetime

API_URL = "https://core-nexus-memory-service.onrender.com"
API_KEY = "test-key-67890"

async def verify_status():
    headers = {"X-API-Key": API_KEY}
    
    async with aiohttp.ClientSession() as session:
        print("🔍 GRAPHRAG STATUS VERIFICATION")
        print("=" * 60)
        
        # Create a memory with a known entity
        print("\n1. Creating test memory with known entity...")
        test_memory = {
            "content": f"Status check {datetime.now()}: Microsoft and OpenAI are collaborating on AI research.",
            "metadata": {"status_check": True},
            "importance_score": 0.9
        }
        
        try:
            async with session.post(f"{API_URL}/memories", 
                                  headers={**headers, "Content-Type": "application/json"}, 
                                  json=test_memory) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    memory_id = data.get('id')
                    print(f"   ✅ Memory created: {memory_id}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Wait for processing
        await asyncio.sleep(10)
        
        # Check graph stats
        print("\n2. Graph Statistics:")
        try:
            async with session.get(f"{API_URL}/graph/stats", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    stats = data['statistics']
                    print(f"   Total nodes: {stats['total_nodes']}")
                    print(f"   Total relationships: {stats['total_relationships']}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Check known entities
        print("\n3. Checking Known Entities:")
        known_entities = ["Microsoft", "OpenAI", "Von Base Enterprises", "Core Nexus"]
        
        for entity in known_entities:
            try:
                # First check if entity exists
                query = {"entity_name": entity}
                async with session.post(f"{API_URL}/graph/query", 
                                      headers={**headers, "Content-Type": "application/json"}, 
                                      json=query) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data['total_nodes'] > 0:
                            node = data['nodes'][0]
                            print(f"\n   {entity}:")
                            print(f"   - Found in graph ✅")
                            print(f"   - Mentions: {node['mention_count']}")
                            print(f"   - Relationships: {data['total_relationships']}")
                            
                            # Now check exploration
                            async with session.get(f"{API_URL}/graph/explore/{entity}", headers=headers) as resp2:
                                if resp2.status == 200:
                                    explore_data = await resp2.json()
                                    print(f"   - Connected memories: {explore_data['memories_found']}")
                                    if explore_data['memories_found'] == 0:
                                        print(f"   ⚠️  Entity exists but has no connected memories!")
                        else:
                            print(f"\n   {entity}: Not found in graph")
            except Exception as e:
                print(f"   Error checking {entity}: {e}")
        
        print("\n" + "=" * 60)
        print("CONCLUSION:")
        print("If entities exist but have 0 connected memories, the memory_entity_map")
        print("table is likely empty. Running the migration script should fix this.")
        
        # Check memory query to confirm memories exist
        print("\n4. Confirming memories exist in vector store:")
        try:
            query_req = {
                "query": "Von Base Enterprises",
                "limit": 3,
                "min_similarity": 0.0
            }
            async with session.post(f"{API_URL}/memories/query", 
                                  headers={**headers, "Content-Type": "application/json"}, 
                                  json=query_req) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   Found {data['total_found']} memories in vector store")
                    if data['total_found'] > 0:
                        print(f"   ✅ Memories exist but aren't linked to graph entities")
                        print(f"   → Migration will fix this!")
        except Exception as e:
            print(f"   Error: {e}")

if __name__ == "__main__":
    asyncio.run(verify_status())