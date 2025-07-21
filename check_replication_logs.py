#!/usr/bin/env python3
"""
Check production logs for our new debug messages.
"""

import asyncio
import aiohttp
import json

API_URL = "https://core-nexus-memory-service.onrender.com"
API_KEY = "test-key-67890"

async def check_logs():
    headers = {"X-API-Key": API_KEY}
    
    async with aiohttp.ClientSession() as session:
        print("🔍 CHECKING PRODUCTION LOGS FOR REPLICATION")
        print("=" * 60)
        
        try:
            async with session.get(f"{API_URL}/debug/logs?lines=100", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logs = data.get('logs', [])
                    
                    # Look for our new log messages
                    print("\n1. Looking for replication logs...")
                    replication_logs = []
                    for log in logs:
                        msg = log.get('message', '')
                        if any(term in msg for term in [
                            'Primary storage complete',
                            'Starting replication',
                            'GraphProvider.store() called',
                            'Successfully replicated',
                            'Failed to replicate',
                            'secondary providers',
                            'without memory_id'
                        ]):
                            replication_logs.append(log)
                    
                    if replication_logs:
                        print(f"   Found {len(replication_logs)} replication logs:")
                        for log in replication_logs[-20:]:  # Show last 20
                            print(f"   [{log['level']}] {log['message']}")
                    else:
                        print("   No replication logs found")
                    
                    # Look for errors
                    print("\n2. Looking for errors...")
                    error_logs = [log for log in logs if log.get('level') in ['ERROR', 'WARNING']]
                    if error_logs:
                        print(f"   Found {len(error_logs)} error/warning logs:")
                        for log in error_logs[-10:]:
                            print(f"   [{log['level']}] {log['message']}")
                    else:
                        print("   No errors found")
                    
                    # Check provider status
                    provider_status = data.get('system_info', {}).get('providers_status', {})
                    if provider_status:
                        print(f"\n3. Provider Status:")
                        for name, status in provider_status.items():
                            print(f"   - {name}: enabled={status.get('enabled')}, primary={status.get('primary')}")
                    
                else:
                    print(f"   ❌ Failed: {resp.status}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_logs())