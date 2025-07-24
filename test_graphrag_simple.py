#!/usr/bin/env python3
"""
Simple test to verify GraphRAG fix is working.
"""

import asyncio
import aiohttp
import json
from datetime import datetime

API_URL = "https://core-nexus-memory-service.onrender.com"
API_KEY = "test-key-67890"

async def simple_test():
    headers = {"X-API-Key": API_KEY}
    
    async with aiohttp.ClientSession() as session:
        print("🧪 SIMPLE GRAPHRAG TEST")
        print("=" * 50)
        
        # 1. Create a simple memory
        print("\n1. Creating test memory...")
        test_memory = {
            "content": f"Simple test {datetime.now()}: Von Base Enterprises works with Core Nexus.",
            "metadata": {"simple_test": True},
            "importance_score": 0.8
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
                else:
                    print(f"   ❌ Failed: {resp.status}")
                    return
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return
        
        # 2. Wait longer for replication
        print("\n2. Waiting 10 seconds for replication...")
        await asyncio.sleep(10)
        
        # 3. Check if Von Base Enterprises has any memories
        print("\n3. Checking Von Base Enterprises memories...")
        try:
            async with session.get(f"{API_URL}/graph/explore/Von Base Enterprises", 
                                 headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    memories_found = data['memories_found']
                    print(f"   Memories found: {memories_found}")
                    
                    if memories_found > 0:
                        print(f"   ✅ SUCCESS! GraphRAG is working!")
                        print(f"   Sample: {data['memories'][0]['content'][:60]}...")
                    else:
                        print(f"   ❌ No memories found - GraphRAG not working yet")
                else:
                    print(f"   ❌ Failed: {resp.status}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 4. Check recent logs
        print("\n4. Checking recent logs...")
        try:
            async with session.get(f"{API_URL}/debug/logs?lines=30", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logs = data.get('logs', [])
                    
                    # Look for any graph-related logs
                    for log in logs[-10:]:
                        if 'graph' in log.get('message', '').lower():
                            print(f"   [{log['level']}] {log['message']}")
                else:
                    print(f"   ❌ Failed: {resp.status}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print("\n" + "=" * 50)
        print("CONCLUSION:")
        print("If memories_found is 0, the memory-entity mapping is still not working.")
        print("This means we need to investigate further or run the migration.")

if __name__ == "__main__":
    asyncio.run(simple_test())