#!/usr/bin/env python3
"""
Check production environment and GraphProvider status.
"""

import asyncio
import aiohttp
import json

API_URL = "https://core-nexus-memory-service.onrender.com"
API_KEY = "test-key-67890"

async def check_env():
    headers = {"X-API-Key": API_KEY}
    
    async with aiohttp.ClientSession() as session:
        print("🔍 CHECKING PRODUCTION ENVIRONMENT")
        print("=" * 60)
        
        # Check debug endpoint
        print("\n1. Environment Variables:")
        try:
            async with session.get(f"{API_URL}/debug/env", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Check GRAPH_ENABLED
                    graph_enabled = data['env'].get('GRAPH_ENABLED', 'NOT_SET')
                    print(f"   GRAPH_ENABLED: {graph_enabled}")
                    
                    # Check providers
                    print(f"\n   Embedding Model: {data.get('embedding_model', 'None')}")
                    print(f"   Primary Provider: {data.get('primary_provider', 'None')}")
                    
                    # Check database settings
                    db_info = data.get('database', {})
                    if db_info:
                        print(f"\n   Database:")
                        print(f"   - Host: {db_info.get('PGVECTOR_HOST', 'NOT_SET')}")
                        print(f"   - Database: {db_info.get('PGVECTOR_DATABASE', 'NOT_SET')}")
                else:
                    print(f"   ❌ Failed: {resp.status}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Check startup logs
        print("\n\n2. Recent Logs (looking for GraphProvider init):")
        try:
            async with session.get(f"{API_URL}/debug/logs?lines=20", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logs = data.get('logs', [])
                    
                    # Look for graph-related logs
                    graph_logs = [log for log in logs if 'graph' in log.get('message', '').lower()]
                    
                    if graph_logs:
                        print("   Graph-related logs found:")
                        for log in graph_logs[-5:]:
                            print(f"   [{log['level']}] {log['message']}")
                    else:
                        print("   No graph-related logs found")
                        
                    # Check provider status
                    provider_status = data.get('system_info', {}).get('providers_status', {})
                    if provider_status:
                        print(f"\n   Provider Status:")
                        for name, status in provider_status.items():
                            print(f"   - {name}: enabled={status.get('enabled')}, primary={status.get('primary')}")
                else:
                    print(f"   ❌ Failed: {resp.status}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Check health endpoint
        print("\n\n3. Health Check:")
        try:
            async with session.get(f"{API_URL}/health", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   Overall Status: {data['status']}")
                    
                    providers = data.get('providers', {})
                    if providers:
                        print(f"\n   Provider Health:")
                        for name, health in providers.items():
                            status = health.get('status', 'unknown')
                            print(f"   - {name}: {status}")
                            if name == 'graph' and health.get('details'):
                                details = health['details']
                                print(f"     Connection: {details.get('connection')}")
                                print(f"     Nodes: {details.get('graph_nodes')}")
                                print(f"     Relationships: {details.get('graph_relationships')}")
                else:
                    print(f"   ❌ Failed: {resp.status}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print("\n" + "=" * 60)
        print("SUMMARY:")
        print("Check if GRAPH_ENABLED is 'true' in production")
        print("Check if graph provider shows as enabled and healthy")
        print("Look for any error logs related to GraphProvider initialization")

if __name__ == "__main__":
    asyncio.run(check_env())