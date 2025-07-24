#!/usr/bin/env python3
"""
Test the correct endpoints based on OpenAPI spec.
"""

import asyncio
import httpx
import json

async def test_endpoints():
    headers = {"X-API-Key": "dev-key-12345"}
    base_url = "https://core-nexus-memory-service.onrender.com"
    
    print("=" * 60)
    print("Testing Correct Endpoints")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        # 1. Test graph stats (correct endpoint)
        print("\n1. Testing /graph/stats endpoint...")
        try:
            response = await client.get(f"{base_url}/graph/stats")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Response: {json.dumps(data, indent=2)}")
            else:
                print(f"   Error: {response.text}")
        except Exception as e:
            print(f"   Exception: {e}")
        
        # 2. Test providers endpoint
        print("\n2. Testing /providers endpoint...")
        try:
            response = await client.get(f"{base_url}/providers")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Providers: {data}")
            else:
                print(f"   Error: {response.text}")
        except Exception as e:
            print(f"   Exception: {e}")
        
        # 3. Test knowledge graph live stats
        print("\n3. Testing /api/knowledge-graph/live-stats...")
        try:
            response = await client.get(f"{base_url}/api/knowledge-graph/live-stats")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Response: {json.dumps(data, indent=2)}")
            else:
                print(f"   Error: {response.text}")
        except Exception as e:
            print(f"   Exception: {e}")
        
        # 4. Test debug endpoints
        print("\n4. Testing debug endpoints...")
        try:
            # Check environment variables (might reveal if GEMINI_API_KEY is set)
            response = await client.get(f"{base_url}/debug/env")
            print(f"   /debug/env status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                # Look for API keys
                env_vars = data.get('environment', {})
                print(f"   OPENAI_API_KEY set: {'OPENAI_API_KEY' in env_vars}")
                print(f"   GEMINI_API_KEY set: {'GEMINI_API_KEY' in env_vars}")
                print(f"   GRAPH_ENABLED: {env_vars.get('GRAPH_ENABLED', 'not set')}")
            else:
                print(f"   Error: {response.text}")
        except Exception as e:
            print(f"   Exception: {e}")
        
        # 5. Test ADK endpoint
        print("\n5. Testing /test/adk endpoint...")
        try:
            response = await client.get(f"{base_url}/test/adk")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   ADK Response: {json.dumps(data, indent=2)}")
            else:
                print(f"   Error: {response.text}")
        except Exception as e:
            print(f"   Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_endpoints())