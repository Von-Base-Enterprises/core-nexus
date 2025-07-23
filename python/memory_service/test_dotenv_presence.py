#!/usr/bin/env python3
"""
Test if dotenv was actually installed and is being used.
"""

import asyncio
import httpx
import json

async def test_dotenv():
    headers = {"X-API-Key": "dev-key-12345"}
    base_url = "https://core-nexus-memory-service.onrender.com"
    
    print("=" * 60)
    print("Testing dotenv Installation")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        # Create a test that would show if env vars are working
        print("\n1. Testing if enhanced regex is working (shows our code is deployed)...")
        
        test_memory = {
            "content": "Testing ADK and ML with AI models",
            "tags": ["test"],
            "metadata": {"test": "dotenv"}
        }
        
        try:
            # Create memory
            response = await client.post(f"{base_url}/memories", json=test_memory)
            if response.status_code in [200, 201]:
                memory_id = response.json().get('id')
                
                # Sync to graph
                sync_response = await client.post(f"{base_url}/graph/sync/{memory_id}")
                print(f"   Graph sync status: {sync_response.status_code}")
                
                if sync_response.status_code == 200:
                    sync_data = sync_response.json()
                    entities = sync_data.get('entities_created', [])
                    entity_names = [e.get('name', '') for e in entities]
                    
                    print(f"   Entities found: {entity_names}")
                    
                    # Check for entities that only enhanced regex would catch
                    enhanced_entities = ['ADK', 'ML', 'AI']
                    found = [e for e in entity_names if e in enhanced_entities]
                    
                    if found:
                        print(f"   ✅ Enhanced regex is working: {found}")
                        print("   This confirms our code changes ARE deployed")
                    else:
                        print("   ❌ Basic regex only - our changes may not be deployed")
                else:
                    print(f"   Sync error: {sync_response.text}")
                    
        except Exception as e:
            print(f"   Error: {e}")
        
        # 2. Check service metadata
        print("\n2. Checking service version/info...")
        try:
            # Try various endpoints that might show version info
            endpoints = ["/", "/info", "/version", "/api/info"]
            
            for endpoint in endpoints:
                try:
                    response = await client.get(f"{base_url}{endpoint}")
                    if response.status_code == 200:
                        print(f"   {endpoint}: {response.text[:100]}")
                except:
                    pass
                    
        except Exception as e:
            print(f"   Error: {e}")
        
        # 3. Direct test of our logging
        print("\n3. Testing if our env logging is present...")
        print("   If our startup.sh changes were deployed, we should see:")
        print("   - 'Environment Variable Check' in logs")
        print("   - 'Environment check - RENDER:' in application logs")
        print("   But logs are not accessible, so we can't verify this directly")

if __name__ == "__main__":
    asyncio.run(test_dotenv())