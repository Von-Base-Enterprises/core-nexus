#!/usr/bin/env python3
"""
Test deployment health and configuration to diagnose issues.
"""

import asyncio
import httpx
import json

async def test_deployment():
    headers = {"X-API-Key": "dev-key-12345"}
    base_url = "https://core-nexus-memory-service.onrender.com"
    
    print("=" * 60)
    print("Deployment Health Check")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        # 1. Basic health check
        print("\n1. Testing basic health endpoint...")
        try:
            response = await client.get(f"{base_url}/health")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Response: {json.dumps(data, indent=2)}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # 2. Provider status with details
        print("\n2. Testing provider status...")
        try:
            response = await client.get(f"{base_url}/providers/status")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                # Check embedding model
                embed_model = data.get("embedding_model", {})
                print(f"   Embedding Model: {embed_model.get('model_type', 'Unknown')}")
                print(f"   Dimension: {embed_model.get('dimension', 'Unknown')}")
                
                # Check graph provider
                providers = data.get("providers", [])
                for provider in providers:
                    if provider["name"] == "graph":
                        print(f"\n   Graph Provider:")
                        print(f"   - Enabled: {provider.get('enabled', False)}")
                        print(f"   - Stats: {json.dumps(provider.get('stats', {}), indent=4)}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # 3. Check graph health specifically
        print("\n3. Testing graph health endpoint...")
        try:
            response = await client.get(f"{base_url}/graph/health")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Response: {json.dumps(data, indent=2)}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # 4. Test entity extraction capability
        print("\n4. Testing entity extraction capability...")
        test_memory = {
            "content": "Core Nexus is an AI system built with ChromaDB and pgvector. It uses GPT-4 and Claude for processing.",
            "tags": ["test"],
            "metadata": {"test": True}
        }
        
        try:
            response = await client.post(f"{base_url}/memories", json=test_memory)
            print(f"   Status: {response.status_code}")
            if response.status_code in [200, 201]:
                data = response.json()
                memory_id = data.get("id")
                print(f"   Memory created: {memory_id}")
                
                # Check if entities were extracted
                if "extracted_entities" in data:
                    entities = data.get("extracted_entities", [])
                    print(f"   Entities extracted: {len(entities)}")
                    if entities:
                        print(f"   Entities: {[e.get('name', '') for e in entities[:5]]}")
                else:
                    print("   No entity extraction data in response")
            else:
                print(f"   Error response: {response.text}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # 5. Check configuration/environment
        print("\n5. Checking configuration...")
        try:
            # Try to get some debug info if available
            response = await client.get(f"{base_url}/debug/config")
            if response.status_code == 200:
                data = response.json()
                print(f"   Config: {json.dumps(data, indent=2)}")
            else:
                print(f"   Debug endpoint not available (status: {response.status_code})")
        except Exception as e:
            print(f"   Debug endpoint not available: {e}")

if __name__ == "__main__":
    asyncio.run(test_deployment())