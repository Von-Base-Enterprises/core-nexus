#!/usr/bin/env python3
"""
Test environment variable loading in production.
"""

import asyncio
import httpx
import json
import os

async def test_env_debug():
    headers = {"X-API-Key": "dev-key-12345"}
    base_url = "https://core-nexus-memory-service.onrender.com"
    
    print("=" * 60)
    print("Environment Variable Debug Test")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        # 1. Check startup logs for env loading issues
        print("\n1. Checking startup logs...")
        try:
            response = await client.get(f"{base_url}/debug/startup-logs")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                logs = data.get('logs', [])
                print(f"   Found {len(logs)} startup log entries")
                
                # Look for env-related messages
                env_logs = [log for log in logs if any(keyword in log.lower() for keyword in ['env', 'api', 'key', 'gemini', 'openai', 'config'])]
                if env_logs:
                    print("\n   Environment-related logs:")
                    for log in env_logs[:10]:
                        print(f"   - {log}")
            else:
                print(f"   Error: {response.text}")
        except Exception as e:
            print(f"   Exception: {e}")
        
        # 2. Test if Gemini is actually working despite env showing not set
        print("\n2. Testing actual Gemini functionality...")
        test_memory = {
            "content": "Testing if Gemini AI extraction works with ADK and ML models",
            "tags": ["test", "gemini"],
            "metadata": {"direct_test": True}
        }
        
        try:
            response = await client.post(f"{base_url}/memories", json=test_memory)
            print(f"   Memory creation status: {response.status_code}")
            
            if response.status_code in [200, 201]:
                memory_id = response.json().get('id')
                
                # Try to get graph insights for this memory
                insights_response = await client.get(f"{base_url}/graph/insights/{memory_id}")
                print(f"   Graph insights status: {insights_response.status_code}")
                
                if insights_response.status_code == 200:
                    insights = insights_response.json()
                    entities = insights.get('entities', [])
                    print(f"   Entities found: {len(entities)}")
                    if entities:
                        print(f"   Entity names: {[e.get('name', '') for e in entities[:5]]}")
                        # Check if these look like Gemini extraction (would include ADK, ML)
                        advanced_entities = [e for e in entities if e.get('name', '').upper() in ['ADK', 'AI', 'ML', 'GEMINI']]
                        if advanced_entities:
                            print(f"   ✅ Advanced entities found: {[e['name'] for e in advanced_entities]}")
                            print("   This suggests Gemini might actually be working!")
                else:
                    print(f"   Graph insights error: {insights_response.text}")
                    
        except Exception as e:
            print(f"   Exception: {e}")
        
        # 3. Check logs for actual API usage
        print("\n3. Checking recent logs for API calls...")
        try:
            response = await client.get(f"{base_url}/debug/logs")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                logs = data.get('logs', [])
                
                # Look for Gemini/OpenAI API calls in logs
                api_logs = [log for log in logs if any(keyword in log for keyword in ['gemini', 'openai', 'generativeai', 'embedding'])]
                if api_logs:
                    print(f"   Found {len(api_logs)} API-related log entries")
                    for log in api_logs[:5]:
                        print(f"   - {log}")
            else:
                print(f"   Error: {response.text}")
        except Exception as e:
            print(f"   Exception: {e}")
        
        # 4. Check provider configuration details
        print("\n4. Checking provider configuration...")
        try:
            response = await client.get(f"{base_url}/providers")
            if response.status_code == 200:
                data = response.json()
                embedding_model = data.get('embedding_model', {})
                
                print(f"\n   Embedding Model Details:")
                print(f"   - Type: {embedding_model.get('model_type', 'Unknown')}")
                print(f"   - Dimension: {embedding_model.get('dimension', 'Unknown')}")
                
                # If it's MockEmbeddingModel but entities are being extracted well,
                # it might mean Gemini is working for extraction but not embeddings
                if embedding_model.get('model_type') == 'MockEmbeddingModel':
                    print("\n   ⚠️  Using MockEmbeddingModel suggests OPENAI_API_KEY issue")
                    print("   But entity extraction might still use Gemini!")
                    
        except Exception as e:
            print(f"   Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_env_debug())