#!/usr/bin/env python3
"""
Test startup logs to see what's happening during initialization.
"""

import asyncio
import httpx
import json

async def test_logs():
    headers = {"X-API-Key": "dev-key-12345"}
    base_url = "https://core-nexus-memory-service.onrender.com"
    
    print("=" * 60)
    print("Startup Logs Investigation")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        # 1. Check startup logs
        print("\n1. Checking startup logs...")
        try:
            response = await client.get(f"{base_url}/debug/startup-logs")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                logs = data.get('logs', [])
                print(f"   Found {len(logs)} startup log entries")
                
                if logs:
                    print("\n   Recent startup logs:")
                    for log in logs[-20:]:  # Last 20 entries
                        print(f"   {log}")
            else:
                print(f"   Error: {response.text}")
        except Exception as e:
            print(f"   Exception: {e}")
        
        # 2. Check recent logs
        print("\n2. Checking recent logs...")
        try:
            response = await client.get(f"{base_url}/debug/logs")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                logs = data.get('logs', [])
                
                # Look for environment-related logs
                env_logs = [log for log in logs if any(keyword in log.lower() for keyword in 
                           ['environment', 'env', 'gemini', 'openai', 'initialized', 'api_key', 'dotenv'])]
                
                if env_logs:
                    print(f"\n   Environment-related logs ({len(env_logs)} found):")
                    for log in env_logs[-10:]:
                        print(f"   {log}")
                else:
                    print("   No environment-related logs found")
                    
        except Exception as e:
            print(f"   Exception: {e}")
        
        # 3. Check system info
        print("\n3. Checking system info...")
        try:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                data = response.json()
                uptime = data.get('uptime_seconds', 0)
                print(f"   Uptime: {uptime:.1f} seconds ({uptime/60:.1f} minutes)")
                
                # If uptime is very short, deployment just restarted
                if uptime < 300:
                    print("   ⚠️  Service recently restarted (less than 5 minutes)")
                    
        except Exception as e:
            print(f"   Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_logs())