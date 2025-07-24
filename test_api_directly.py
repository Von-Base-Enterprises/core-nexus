#!/usr/bin/env python3
"""
Test the API endpoint directly with detailed logging.
"""

import asyncio
import aiohttp
import json

API_URL = "https://core-nexus-memory-service.onrender.com"
API_KEY = "test-key-67890"

async def test_api():
    headers = {"X-API-Key": API_KEY}
    
    async with aiohttp.ClientSession() as session:
        # Test entity exploration
        print("Testing /graph/explore/Von Base Enterprises")
        
        try:
            async with session.get(
                f"{API_URL}/graph/explore/Von Base Enterprises",
                headers=headers
            ) as resp:
                print(f"Status: {resp.status}")
                text = await resp.text()
                print(f"Raw response: {text}")
                
                if resp.status == 200:
                    data = json.loads(text)
                    print(f"\nParsed response:")
                    print(f"- Entity: {data.get('entity')}")
                    print(f"- Max depth: {data.get('max_depth')}")
                    print(f"- Memories found: {data.get('memories_found')}")
                    print(f"- Memories array length: {len(data.get('memories', []))}")
                    
                    if data.get('memories'):
                        print(f"\nFirst memory:")
                        print(json.dumps(data['memories'][0], indent=2))
                
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_api())