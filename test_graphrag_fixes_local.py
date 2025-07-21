#!/usr/bin/env python3
"""
Test GraphRAG fixes locally before deployment.
"""

import asyncio
import aiohttp
import json
from datetime import datetime

# Local test configuration
API_URL = "http://localhost:8000"
API_KEY = "test-key-67890"

async def test_local_fixes():
    """Test GraphRAG fixes locally."""
    
    headers = {"X-API-Key": API_KEY}
    
    async with aiohttp.ClientSession() as session:
        print("🧪 TESTING GRAPHRAG FIXES LOCALLY")
        print("=" * 50)
        
        # Test 1: Create a memory
        print("\n1. Creating test memory...")
        test_memory = {
            "content": f"Local test {datetime.now()}: Von Base Enterprises and Core Nexus are testing GraphRAG fixes.",
            "metadata": {"test": "local_graphrag_fix"},
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
        
        # Wait for replication
        print("\n2. Waiting for replication...")
        await asyncio.sleep(3)
        
        # Check logs for our new logging
        print("\n3. Checking logs for replication status...")
        try:
            async with session.get(f"{API_URL}/debug/logs?lines=50", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logs = data.get('logs', [])
                    
                    # Look for our new log messages
                    relevant_logs = []
                    for log in logs:
                        msg = log.get('message', '')
                        if any(term in msg for term in [
                            'Primary storage complete',
                            'Starting replication',
                            'GraphProvider.store() called',
                            'Successfully replicated',
                            'Failed to replicate'
                        ]):
                            relevant_logs.append(log)
                    
                    if relevant_logs:
                        print("   Found replication logs:")
                        for log in relevant_logs[-10:]:
                            print(f"   [{log['level']}] {log['message']}")
                    else:
                        print("   No replication logs found")
                else:
                    print(f"   ❌ Failed: {resp.status}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test entity exploration
        print("\n4. Testing entity exploration...")
        try:
            async with session.get(f"{API_URL}/graph/explore/Von Base Enterprises", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   Memories found: {data['memories_found']}")
                    
                    if data['memories_found'] > 0:
                        print(f"   ✅ SUCCESS! Entity exploration is working!")
                        # Check if our test memory is included
                        if memory_id:
                            found = any(str(memory_id) in str(mem['id']) for mem in data['memories'])
                            if found:
                                print(f"   ✅ Test memory is properly connected!")
                    else:
                        print(f"   ⚠️  No memories found - replication might have failed")
                else:
                    print(f"   ❌ Failed: {resp.status}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print("\n" + "=" * 50)
        print("LOCAL TEST COMPLETE")
        print("\nIf entity exploration returns memories, the fix is working!")
        print("Deploy to production and run migration script.")

if __name__ == "__main__":
    # Note: Make sure local server is running with:
    # cd python/memory_service && poetry run uvicorn src.memory_service.api:app --reload
    print("Make sure local server is running on port 8000")
    print("Press Ctrl+C to cancel, or wait to continue...")
    asyncio.sleep(2)
    asyncio.run(test_local_fixes())