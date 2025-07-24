#!/usr/bin/env python3
"""
Wait for deployment and notify when GraphRAG is working.
"""

import asyncio
import aiohttp
import json
from datetime import datetime
import time

API_URL = "https://core-nexus-memory-service.onrender.com"
API_KEY = "test-key-67890"

async def check_deployment():
    headers = {"X-API-Key": API_KEY}
    
    async with aiohttp.ClientSession() as session:
        # Create a test memory
        test_memory = {
            "content": f"Deployment test {datetime.now()}: Von Base Enterprises GraphRAG test.",
            "metadata": {"deployment_test": True},
            "importance_score": 0.8
        }
        
        try:
            async with session.post(f"{API_URL}/memories", 
                                  headers={**headers, "Content-Type": "application/json"}, 
                                  json=test_memory) as resp:
                if resp.status != 200:
                    return False, "Failed to create memory"
                
                data = await resp.json()
                memory_id = data.get('id')
        except Exception as e:
            return False, f"Error creating memory: {e}"
        
        # Wait for replication
        await asyncio.sleep(5)
        
        # Check logs for the specific error
        try:
            async with session.get(f"{API_URL}/debug/logs?lines=30", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logs = data.get('logs', [])
                    
                    # Look for the parameter error
                    for log in logs:
                        if memory_id and str(memory_id) in log.get('message', ''):
                            if "7 arguments for this query, 6 were passed" in log.get('message', ''):
                                return False, "Old version still deployed (SQL parameter error)"
                            elif "Stored memory" in log.get('message', '') and "entities" in log.get('message', ''):
                                return True, "GraphRAG is working!"
        except:
            pass
        
        # Check if Von Base Enterprises has memories
        try:
            async with session.get(f"{API_URL}/graph/explore/Von Base Enterprises", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data['memories_found'] > 0:
                        return True, f"GraphRAG is working! Found {data['memories_found']} memories"
        except:
            pass
        
        return False, "GraphRAG not working yet"

async def wait_for_graphrag():
    print("⏳ WAITING FOR GRAPHRAG DEPLOYMENT")
    print("=" * 50)
    print(f"Started: {datetime.now()}")
    print("Checking every 30 seconds...")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    start_time = time.time()
    check_count = 0
    
    while True:
        check_count += 1
        elapsed = int(time.time() - start_time)
        print(f"\nCheck #{check_count} (after {elapsed}s):", end=" ")
        
        working, message = await check_deployment()
        print(message)
        
        if working:
            print("\n" + "🎉" * 20)
            print("GRAPHRAG IS LIVE AND WORKING!")
            print("🎉" * 20)
            print(f"\nDeployment took {elapsed} seconds")
            print("\nNext steps:")
            print("1. Run comprehensive tests: python3 test_graphrag_final.py")
            print("2. Run migration: ./run_production_migration.sh")
            break
        
        await asyncio.sleep(30)

if __name__ == "__main__":
    try:
        asyncio.run(wait_for_graphrag())
    except KeyboardInterrupt:
        print("\n\nStopped waiting. Check deployment status manually.")