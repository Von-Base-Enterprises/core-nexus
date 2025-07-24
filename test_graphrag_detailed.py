#!/usr/bin/env python3
"""
Detailed GraphRAG test to understand exactly what's happening.
"""

import asyncio
import aiohttp
import json
from datetime import datetime
import uuid

API_URL = "https://core-nexus-memory-service.onrender.com"
API_KEY = "test-key-67890"

async def detailed_test():
    headers = {"X-API-Key": API_KEY}
    test_id = str(uuid.uuid4())[:8]
    
    async with aiohttp.ClientSession() as session:
        print("🔍 DETAILED GRAPHRAG DIAGNOSTIC")
        print("=" * 60)
        print(f"Test ID: {test_id}")
        print(f"Time: {datetime.now()}")
        print("=" * 60)
        
        # 1. Check current stats before test
        print("\n1. INITIAL STATE:")
        try:
            async with session.get(f"{API_URL}/graph/stats", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    stats = data['statistics']
                    print(f"   Nodes: {stats['total_nodes']}")
                    print(f"   Relationships: {stats['total_relationships']}")
                    initial_nodes = stats['total_nodes']
        except Exception as e:
            print(f"   Error: {e}")
            initial_nodes = 0
        
        # 2. Create test memory with unique content
        print(f"\n2. CREATING TEST MEMORY:")
        unique_entity = f"TestEntity{test_id}"
        test_memory = {
            "content": f"Test {test_id}: {unique_entity} is working with Von Base Enterprises on Core Nexus GraphRAG testing.",
            "metadata": {"test_id": test_id, "test_type": "detailed_diagnostic"},
            "importance_score": 0.95
        }
        
        memory_id = None
        try:
            async with session.post(f"{API_URL}/memories", 
                                  headers={**headers, "Content-Type": "application/json"}, 
                                  json=test_memory) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    memory_id = data.get('id')
                    print(f"   ✅ Memory created: {memory_id}")
                    print(f"   Content: {test_memory['content']}")
                else:
                    print(f"   ❌ Failed: {resp.status}")
                    print(await resp.text())
                    return
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return
        
        # 3. Wait and check logs multiple times
        print(f"\n3. MONITORING REPLICATION:")
        for i in range(3):
            await asyncio.sleep(5)
            print(f"\n   Check {i+1}/3 (after {(i+1)*5} seconds):")
            
            # Check logs
            try:
                async with session.get(f"{API_URL}/debug/logs?lines=20", headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        logs = data.get('logs', [])
                        
                        # Look for our memory_id in logs
                        relevant_logs = [log for log in logs if memory_id and str(memory_id) in log.get('message', '')]
                        if relevant_logs:
                            print("   Found logs for our memory:")
                            for log in relevant_logs:
                                print(f"   [{log['level']}] {log['message']}")
                        
                        # Also check for graph-related logs
                        graph_logs = [log for log in logs if 'graph' in log.get('message', '').lower()]
                        if graph_logs and not relevant_logs:
                            print("   Recent graph logs:")
                            for log in graph_logs[-3:]:
                                print(f"   [{log['level']}] {log['message'][:100]}...")
            except Exception as e:
                print(f"   Log check error: {e}")
            
            # Check if entity was created
            try:
                query = {"entity_name": unique_entity}
                async with session.post(f"{API_URL}/graph/query", 
                                      headers={**headers, "Content-Type": "application/json"}, 
                                      json=query) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data['total_nodes'] > 0:
                            print(f"   ✅ Unique entity '{unique_entity}' found in graph!")
                        else:
                            print(f"   ❌ Unique entity '{unique_entity}' NOT found")
            except Exception as e:
                print(f"   Entity check error: {e}")
        
        # 4. Final comprehensive check
        print(f"\n4. FINAL VERIFICATION:")
        
        # Check Von Base Enterprises
        print("\n   Checking Von Base Enterprises:")
        try:
            async with session.get(f"{API_URL}/graph/explore/Von Base Enterprises", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   Memories found: {data['memories_found']}")
                    
                    # Check if our test memory is there
                    if data['memories_found'] > 0 and memory_id:
                        found_test = any(str(memory_id) in str(mem.get('id', '')) for mem in data['memories'])
                        if found_test:
                            print(f"   ✅ Our test memory IS connected!")
                        else:
                            print(f"   ❌ Our test memory is NOT in the results")
                            print(f"   Latest memory: {data['memories'][0]['content'][:60]}...")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Check unique entity
        print(f"\n   Checking {unique_entity}:")
        try:
            async with session.get(f"{API_URL}/graph/explore/{unique_entity}", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   Memories found: {data['memories_found']}")
                    if data['memories_found'] > 0:
                        print(f"   ✅ Entity exploration working for new entity!")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Check final stats
        print("\n   Final graph stats:")
        try:
            async with session.get(f"{API_URL}/graph/stats", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    stats = data['statistics']
                    new_nodes = stats['total_nodes']
                    print(f"   Nodes: {new_nodes} (+" + str(new_nodes - initial_nodes) + " new)")
                    print(f"   Relationships: {stats['total_relationships']}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # 5. Check if we can query the memory directly
        print(f"\n5. DIRECT MEMORY QUERY:")
        try:
            query_req = {
                "query": unique_entity,
                "limit": 5,
                "min_similarity": 0.5
            }
            async with session.post(f"{API_URL}/memories/query", 
                                  headers={**headers, "Content-Type": "application/json"}, 
                                  json=query_req) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   Found {data['total_found']} memories for '{unique_entity}'")
                    if data['total_found'] > 0:
                        print(f"   ✅ Memory query works")
                        found_test = any(test_id in str(mem.get('metadata', {})) for mem in data['memories'])
                        if found_test:
                            print(f"   ✅ Our test memory found in vector search!")
        except Exception as e:
            print(f"   Error: {e}")
        
        print("\n" + "=" * 60)
        print("DIAGNOSIS COMPLETE")
        print("\nKey indicators:")
        print("- If unique entity was created but has no memories: mapping issue persists")
        print("- If no replication logs appear: deployment might not include our logging")
        print("- If vector search finds memory but graph doesn't: confirms mapping issue")

if __name__ == "__main__":
    asyncio.run(detailed_test())