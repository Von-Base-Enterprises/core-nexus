#!/usr/bin/env python3
"""
Test if Gemini API is configured and working in production.
"""

import asyncio
import httpx
import json

async def test_gemini():
    headers = {"X-API-Key": "dev-key-12345"}
    base_url = "https://core-nexus-memory-service.onrender.com"
    
    print("=" * 60)
    print("Gemini Configuration Test")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        # Test 1: Create a memory with known entities that regex would miss
        print("\n1. Testing entity extraction with challenging content...")
        test_cases = [
            {
                "content": "AI and ML are transforming how we use APIs. ChromaDB works with GPT-4.",
                "expected_entities": ["AI", "ML", "APIs", "ChromaDB", "GPT-4"]
            },
            {
                "content": "The ADK from Google enables multi-agent systems with Claude and Gemini.",
                "expected_entities": ["ADK", "Google", "Claude", "Gemini"]
            },
            {
                "content": "pgvector integrates with FastAPI for vector similarity search in PostgreSQL.",
                "expected_entities": ["pgvector", "FastAPI", "PostgreSQL"]
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            print(f"\n   Test Case {i+1}:")
            print(f"   Content: {test_case['content']}")
            
            memory_data = {
                "content": test_case['content'],
                "tags": ["test", "gemini"],
                "metadata": {"test_case": i+1}
            }
            
            try:
                # Create memory
                response = await client.post(f"{base_url}/memories", json=memory_data)
                print(f"   Status: {response.status_code}")
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    memory_id = data.get("id")
                    
                    # Now query with graph enabled to see entities
                    query_data = {
                        "query": test_case['content'],
                        "enable_graph_retrieval": True,
                        "limit": 1
                    }
                    
                    query_response = await client.post(
                        f"{base_url}/memories/query-graph", 
                        json=query_data
                    )
                    
                    if query_response.status_code == 200:
                        query_result = query_response.json()
                        extracted_entities = query_result.get('extracted_entities', [])
                        
                        print(f"   Entities found: {len(extracted_entities)}")
                        if extracted_entities:
                            entity_names = [e['name'] for e in extracted_entities[:10]]
                            print(f"   Entity names: {entity_names}")
                            
                            # Check if we found the expected entities
                            found_expected = []
                            for expected in test_case['expected_entities']:
                                if any(expected.lower() in entity.lower() for entity in entity_names):
                                    found_expected.append(expected)
                            
                            print(f"   Expected entities found: {found_expected}")
                            print(f"   Missing entities: {[e for e in test_case['expected_entities'] if e not in found_expected]}")
                        else:
                            print("   ⚠️  No entities extracted!")
                    else:
                        print(f"   Query failed: {query_response.status_code}")
                else:
                    print(f"   Memory creation failed: {response.text}")
                    
            except Exception as e:
                print(f"   Error: {e}")
        
        # Test 2: Check if we're using advanced extraction
        print("\n\n2. Analyzing extraction patterns...")
        print("   If using basic regex:")
        print("   - Would miss: AI, ML, API, SDK, ADK (all caps)")
        print("   - Would miss: ChromaDB, FastAPI (CamelCase)")
        print("   - Would only catch: Title Case Names")
        print("\n   If using Gemini/enhanced extraction:")
        print("   - Should catch all entity types")
        print("   - Should provide confidence scores")
        print("   - Should understand context")

if __name__ == "__main__":
    asyncio.run(test_gemini())