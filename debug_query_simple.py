#!/usr/bin/env python3
"""
Minimal debug test for query endpoint
"""

import asyncio
import httpx
import json

async def debug_query():
    url = "https://core-nexus-memory-service.onrender.com/memories/query"
    
    # Minimal test payload
    payload = {
        "query": "test",
        "limit": 1
    }
    
    print(f"Testing: {url}")
    print(f"Payload: {json.dumps(payload)}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, json=payload)
            print(f"Status: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            print(f"Response: {response.text}")
            
        except Exception as e:
            print(f"Exception: {e}")
            print(f"Type: {type(e)}")

if __name__ == "__main__":
    asyncio.run(debug_query())