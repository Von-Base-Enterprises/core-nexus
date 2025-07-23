#!/usr/bin/env python3
"""
Test why Render environment variables aren't being detected.
"""

import asyncio
import httpx
import json
import subprocess
import os

async def test_render_env():
    headers = {"X-API-Key": "dev-key-12345"}
    base_url = "https://core-nexus-memory-service.onrender.com"
    
    print("=" * 60)
    print("Render Environment Variable Investigation")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        # 1. Direct environment check
        print("\n1. Checking environment directly via debug endpoint...")
        try:
            response = await client.get(f"{base_url}/debug/env")
            if response.status_code == 200:
                data = response.json()
                env_vars = data.get('environment', {})
                
                print("\n   Key Environment Variables:")
                important_vars = [
                    'OPENAI_API_KEY', 'GEMINI_API_KEY', 'GRAPH_ENABLED',
                    'RENDER', 'RENDER_SERVICE_NAME', 'PORT',
                    'PGVECTOR_HOST', 'PGVECTOR_DATABASE'
                ]
                
                for var in important_vars:
                    value = env_vars.get(var, 'NOT_SET')
                    if var in env_vars:
                        if 'KEY' in var:
                            # Mask sensitive data
                            print(f"   {var}: {'SET' if value else 'EMPTY'}")
                        else:
                            print(f"   {var}: {value}")
                    else:
                        print(f"   {var}: NOT_SET")
                
                # Check if running on Render
                if 'RENDER' in env_vars:
                    print("\n   ✅ Running on Render platform")
                    print(f"   Service: {env_vars.get('RENDER_SERVICE_NAME', 'unknown')}")
                else:
                    print("\n   ❌ NOT running on Render (or RENDER env var not set)")
                    
        except Exception as e:
            print(f"   Error: {e}")
        
        # 2. Test actual functionality vs reported state
        print("\n2. Testing actual functionality vs reported environment...")
        
        # Create a memory with entities that would require Gemini
        test_content = "Testing ADK integration with ML models and AI agents using SDK"
        memory_data = {
            "content": test_content,
            "tags": ["env-test"],
            "metadata": {"test": "env-check"}
        }
        
        try:
            # Create memory
            response = await client.post(f"{base_url}/memories", json=memory_data)
            if response.status_code in [200, 201]:
                memory_id = response.json().get('id')
                print(f"   Memory created: {memory_id}")
                
                # Check graph sync
                sync_response = await client.post(f"{base_url}/graph/sync/{memory_id}")
                print(f"   Graph sync status: {sync_response.status_code}")
                
                if sync_response.status_code == 200:
                    sync_data = sync_response.json()
                    entities = sync_data.get('entities_created', [])
                    print(f"   Entities created: {len(entities)}")
                    if entities:
                        entity_names = [e.get('name', '') for e in entities[:10]]
                        print(f"   Entity names: {entity_names}")
                        
                        # Check if advanced entities were found
                        advanced = ['ADK', 'ML', 'AI', 'SDK']
                        found_advanced = [e for e in entity_names if e in advanced]
                        if found_advanced:
                            print(f"   ✅ Advanced entities found: {found_advanced}")
                            print("   This suggests Gemini IS working despite env vars!")
                        else:
                            print(f"   ❌ No advanced entities found (regex only)")
                else:
                    print(f"   Sync error: {sync_response.text}")
                    
        except Exception as e:
            print(f"   Error: {e}")
        
        # 3. Check if env vars are being masked or filtered
        print("\n3. Checking for environment variable masking...")
        print("   Common issues:")
        print("   - Render may strip env vars with certain prefixes")
        print("   - Python process may not inherit all env vars")
        print("   - Application may be running in a restricted context")
        
        # 4. Test embedding model health
        print("\n4. Testing embedding model health...")
        try:
            response = await client.post(
                f"{base_url}/embeddings/test",
                json={"text": "test embedding"}
            )
            print(f"   Embedding test status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Model type: {data.get('model_type', 'unknown')}")
                print(f"   Provider: {data.get('provider', 'unknown')}")
                if data.get('model_type') == 'MockEmbeddingModel':
                    print("   ❌ Using mock embeddings (no OpenAI key)")
                else:
                    print("   ✅ Using real embeddings")
        except Exception as e:
            print(f"   Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_render_env())