#!/usr/bin/env python3
"""
Test specific entity extraction to debug why we're getting 0 entities.
"""

import asyncio
import httpx
import json

async def test_extraction():
    headers = {"X-API-Key": "dev-key-12345"}
    
    # Test the graph-enhanced query directly with verbose logging
    query_request = {
        "query": "Core Nexus AI development",
        "enable_graph_retrieval": True,
        "graph_weight": 0.3,
        "limit": 5
    }
    
    print("Testing entity extraction with query:", query_request["query"])
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        response = await client.post(
            "https://core-nexus-memory-service.onrender.com/memories/query-graph", 
            json=query_request
        )
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"✅ Status: {response.status_code}")
            print(f"📊 Results:")
            print(f"   - Memories found: {len(data.get('memories', []))}")
            print(f"   - Entities extracted: {len(data.get('extracted_entities', []))}")
            print(f"   - Graph enabled: {data.get('graph_enabled', 'not set')}")
            print(f"   - Evidence chains: {len(data.get('evidence_chains', []))}")
            
            if data.get('extracted_entities'):
                print(f"   - Entities: {data.get('extracted_entities')}")
            else:
                print(f"   - ⚠️ No entities extracted from: '{query_request['query']}'")
                
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")

if __name__ == "__main__":
    asyncio.run(test_extraction())