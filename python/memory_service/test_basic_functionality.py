#!/usr/bin/env python3
"""
Test basic functionality to isolate the issue.
"""

import asyncio
import httpx
import json

async def test_basic():
    headers = {"X-API-Key": "dev-key-12345"}
    base_url = "https://core-nexus-memory-service.onrender.com"
    
    print("=" * 60)
    print("Basic Functionality Test")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        # 1. Test simple memory creation
        print("\n1. Testing simple memory creation...")
        memory = {
            "content": "This is a simple test memory",
            "tags": ["test"],
            "metadata": {}
        }
        
        try:
            response = await client.post(f"{base_url}/memories", json=memory)
            print(f"   Status: {response.status_code}")
            if response.status_code in [200, 201]:
                data = response.json()
                print(f"   Memory ID: {data.get('id')}")
                print(f"   Response keys: {list(data.keys())}")
            else:
                print(f"   Error: {response.text}")
        except Exception as e:
            print(f"   Exception: {e}")
        
        # 2. Test simple query (no graph)
        print("\n2. Testing simple query (no graph)...")
        query = {
            "query": "test memory",
            "limit": 5
        }
        
        try:
            response = await client.post(f"{base_url}/memories/query", json=query)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Memories found: {len(data.get('memories', []))}")
            else:
                print(f"   Error: {response.text}")
        except Exception as e:
            print(f"   Exception: {e}")
        
        # 3. Test graph statistics endpoint
        print("\n3. Testing graph statistics...")
        try:
            response = await client.get(f"{base_url}/graph/statistics")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                stats = data.get('statistics', {})
                print(f"   Total nodes: {stats.get('total_nodes', 0)}")
                print(f"   Total relationships: {stats.get('total_relationships', 0)}")
                print(f"   Health status: {data.get('health', {}).get('status', 'unknown')}")
                details = data.get('health', {}).get('details', {})
                print(f"   Entity extractor: {details.get('entity_extractor', 'unknown')}")
            else:
                print(f"   Error: {response.text}")
        except Exception as e:
            print(f"   Exception: {e}")
        
        # 4. Check what endpoints are available
        print("\n4. Checking available endpoints...")
        endpoints = [
            "/docs",
            "/openapi.json",
            "/providers/status",
            "/graph/health",
            "/metrics"
        ]
        
        for endpoint in endpoints:
            try:
                response = await client.get(f"{base_url}{endpoint}")
                print(f"   {endpoint}: {response.status_code}")
            except Exception as e:
                print(f"   {endpoint}: Error - {str(e)[:50]}")

if __name__ == "__main__":
    asyncio.run(test_basic())