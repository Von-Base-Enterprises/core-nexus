#!/usr/bin/env python3
"""
Test script to verify GraphRAG fixes before deployment.

Tests:
1. Memory storage with proper ID propagation
2. Entity extraction and mapping
3. Graph queries with case-insensitive matching
4. Entity exploration returning connected memories
"""

import asyncio
import aiohttp
import json
from datetime import datetime

# Configuration
API_URL = "http://localhost:8000"  # Change to production URL for prod testing
API_KEY = "test-key-67890"

async def test_graphrag_fixes():
    """Test all GraphRAG fixes."""
    
    headers = {"X-API-Key": API_KEY}
    
    async with aiohttp.ClientSession() as session:
        print("🧪 TESTING GRAPHRAG FIXES")
        print("=" * 50)
        
        # Test 1: Create a memory with entities
        print("\n1. Testing Memory Creation with Entity Extraction:")
        test_memory = {
            "content": f"GraphRAG Test {datetime.now()}: John Smith from Von Base Enterprises is collaborating with Claude from Anthropic on the Core Nexus project. They are implementing advanced GraphRAG features using GPT-4 technology.",
            "metadata": {
                "test": "graphrag_fix_test",
                "timestamp": datetime.now().isoformat()
            },
            "importance_score": 0.8
        }
        
        try:
            async with session.post(f"{API_URL}/memories", headers={**headers, "Content-Type": "application/json"}, json=test_memory) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    memory_id = data.get('id')
                    print(f"   ✅ Memory created: {memory_id}")
                else:
                    print(f"   ❌ Failed to create memory: {resp.status}")
                    return
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return
        
        # Wait a moment for async replication
        await asyncio.sleep(2)
        
        # Test 2: Query graph for entities (case-insensitive)
        print("\n2. Testing Graph Query (Case-Insensitive):")
        test_queries = [
            {"query_type": "entities_by_type", "entity_type": "ORGANIZATION"},  # Uppercase
            {"query_type": "entities_by_type", "entity_type": "organization"},  # Lowercase
            {"query_type": "entities_by_type", "entity_type": "Technology"}     # Mixed case
        ]
        
        for query in test_queries:
            try:
                async with session.post(f"{API_URL}/graph/query", headers={**headers, "Content-Type": "application/json"}, json=query) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"   Query {query['entity_type']}: {data['total_nodes']} nodes, {data['total_relationships']} relationships")
                        if data['total_nodes'] > 0:
                            print(f"   ✅ Found: {data['nodes'][0]['entity_name']} ({data['nodes'][0]['entity_type']})")
                    else:
                        print(f"   ❌ Query failed: {resp.status}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        # Test 3: Entity exploration
        print("\n3. Testing Entity Exploration:")
        test_entities = ["Von Base Enterprises", "John Smith", "Core Nexus", "Claude"]
        
        for entity in test_entities:
            try:
                async with session.get(f"{API_URL}/graph/explore/{entity}", headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"   {entity}: {data['memories_found']} memories found")
                        if data['memories_found'] > 0:
                            print(f"   ✅ Sample: {data['memories'][0]['content'][:50]}...")
                    else:
                        print(f"   ❌ Exploration failed for {entity}: {resp.status}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        # Test 4: Graph statistics
        print("\n4. Testing Graph Statistics:")
        try:
            async with session.get(f"{API_URL}/graph/stats", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    stats = data['statistics']
                    print(f"   ✅ Total Nodes: {stats['total_nodes']}")
                    print(f"   ✅ Total Relationships: {stats['total_relationships']}")
                    print(f"   ✅ Entity Types: {stats['entity_types']}")
                    print(f"   ✅ Relationship Types: {stats['relationship_types']}")
                else:
                    print(f"   ❌ Stats failed: {resp.status}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 5: Verify memory-entity mapping
        print("\n5. Testing Memory-Entity Mapping:")
        if memory_id:
            # Query for our test entity
            query = {
                "query_type": "entities_by_name",
                "entity_name": "John Smith",
                "limit": 5
            }
            
            try:
                async with session.post(f"{API_URL}/graph/query", headers={**headers, "Content-Type": "application/json"}, json=query) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data['total_nodes'] > 0:
                            # Now explore this entity to see if our memory is connected
                            async with session.get(f"{API_URL}/graph/explore/John Smith", headers=headers) as resp2:
                                if resp2.status == 200:
                                    explore_data = await resp2.json()
                                    # Check if our test memory is in the results
                                    found = any(memory_id in str(mem['id']) for mem in explore_data['memories'])
                                    if found:
                                        print(f"   ✅ Memory-entity mapping verified!")
                                    else:
                                        print(f"   ⚠️  Memory not found in entity exploration (might need migration)")
                    else:
                        print(f"   ❌ Query failed: {resp.status}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        print("\n" + "=" * 50)
        print("GRAPHRAG FIX VERIFICATION COMPLETE")
        print("\nNext Steps:")
        print("1. If all tests pass, deploy to production")
        print("2. Run migration script on production to fix existing memories")
        print("3. Monitor graph queries for proper results")

if __name__ == "__main__":
    asyncio.run(test_graphrag_fixes())