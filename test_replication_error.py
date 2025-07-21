#!/usr/bin/env python3
"""
Test if GraphProvider replication is failing silently.
"""

import asyncio
import aiohttp
import json
from datetime import datetime

API_URL = "https://core-nexus-memory-service.onrender.com"
API_KEY = "test-key-67890"

async def test_replication():
    headers = {"X-API-Key": API_KEY}
    
    async with aiohttp.ClientSession() as session:
        print("🔍 TESTING GRAPHPROVIDER REPLICATION ERROR")
        print("=" * 60)
        
        # Check recent logs for errors
        print("\n1. Checking for GraphProvider errors in logs:")
        try:
            async with session.get(f"{API_URL}/debug/logs?lines=100", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logs = data.get('logs', [])
                    
                    # Look for error logs
                    error_logs = [log for log in logs if log.get('level') in ['ERROR', 'WARNING']]
                    
                    if error_logs:
                        print(f"   Found {len(error_logs)} error/warning logs")
                        
                        # Look for GraphProvider or replication errors
                        relevant_errors = []
                        for log in error_logs:
                            msg = log.get('message', '')
                            if any(term in msg.lower() for term in ['graph', 'replicate', 'memory_id', 'valueerror']):
                                relevant_errors.append(log)
                        
                        if relevant_errors:
                            print(f"\n   ⚠️  Found {len(relevant_errors)} relevant errors:")
                            for log in relevant_errors[-5:]:  # Show last 5
                                print(f"   [{log['level']}] {log['message']}")
                        else:
                            print("   No GraphProvider-specific errors found")
                    else:
                        print("   No error logs found")
                else:
                    print(f"   ❌ Failed: {resp.status}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print("\n" + "=" * 60)
        print("HYPOTHESIS:")
        print("The GraphProvider.store() method requires memory_id but during")
        print("replication it might not be getting passed correctly, causing")
        print("silent failures in the background task.")
        print("\nThis would explain why:")
        print("- Entities exist (from previous data)")
        print("- New memories are created successfully") 
        print("- But no memory-entity mappings are created")
        print("\nThe fix might need adjustment to handle this edge case.")

if __name__ == "__main__":
    asyncio.run(test_replication())