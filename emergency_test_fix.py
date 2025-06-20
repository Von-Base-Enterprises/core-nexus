#!/usr/bin/env python3
"""
Emergency test to verify service restoration
"""

import asyncio
import httpx
import time
from datetime import datetime

BASE_URL = "https://core-nexus-memory-service.onrender.com"

async def emergency_service_test():
    """Quick test to verify the fix worked"""
    
    print(f"🚨 EMERGENCY SERVICE TEST")
    print(f"Time: {datetime.now()}")
    print(f"URL: {BASE_URL}")
    print()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Test 1: Health Check (should work)
        print("1. Health Check...")
        try:
            response = await client.get(f"{BASE_URL}/health")
            print(f"   Status: {response.status_code} ({'✅ PASS' if response.status_code == 200 else '❌ FAIL'})")
        except Exception as e:
            print(f"   ERROR: {e}")
        
        # Test 2: GET /memories (should work)
        print("2. GET Memories...")
        try:
            response = await client.get(f"{BASE_URL}/memories?limit=5")
            print(f"   Status: {response.status_code} ({'✅ PASS' if response.status_code == 200 else '❌ FAIL'})")
            if response.status_code == 200:
                data = response.json()
                print(f"   Results: {len(data.get('memories', []))} memories")
        except Exception as e:
            print(f"   ERROR: {e}")
        
        # Test 3: POST /memories/query (CRITICAL - was broken)
        print("3. POST Query (CRITICAL TEST)...")
        try:
            query_data = {
                "query": "test query",
                "limit": 3
            }
            response = await client.post(f"{BASE_URL}/memories/query", json=query_data)
            status = response.status_code
            print(f"   Status: {status} ({'✅ PASS' if status == 200 else '❌ FAIL'})")
            
            if status == 200:
                data = response.json()
                print(f"   Results: {len(data.get('memories', []))} memories found")
                print("   🎉 QUERY ENDPOINTS RESTORED!")
            else:
                print(f"   Error Response: {response.text[:100]}...")
                
        except Exception as e:
            print(f"   ERROR: {e}")
        
        # Test 4: Empty Query Test (was also broken)
        print("4. Empty Query Test...")
        try:
            query_data = {
                "query": "",
                "limit": 5
            }
            response = await client.post(f"{BASE_URL}/memories/query", json=query_data)
            status = response.status_code  
            print(f"   Status: {status} ({'✅ PASS' if status == 200 else '❌ FAIL'})")
            
            if status == 200:
                data = response.json()
                print(f"   Results: {len(data.get('memories', []))} memories")
                print("   🎉 EMPTY QUERIES WORKING!")
                
        except Exception as e:
            print(f"   ERROR: {e}")
        
        # Test 5: Memory Creation
        print("5. Memory Creation...")
        try:
            memory_data = {
                "content": f"Emergency test memory - {datetime.now()}",
                "metadata": {"test": "emergency_fix"}
            }
            response = await client.post(f"{BASE_URL}/memories", json=memory_data)
            status = response.status_code
            print(f"   Status: {status} ({'✅ PASS' if status in [200, 201] else '❌ FAIL'})")
            
            if status in [200, 201]:
                data = response.json()
                print(f"   Created: {data.get('id', 'unknown')}")
                print("   🎉 MEMORY CREATION WORKING!")
                
        except Exception as e:
            print(f"   ERROR: {e}")
        
        print()
        print("=" * 50)
        print("🩺 DIAGNOSIS:")
        print("If all tests show ✅ PASS, the emergency fix worked!")
        print("If any show ❌ FAIL, we need additional investigation.")
        print("Expected: All endpoints should be restored to working state.")

if __name__ == "__main__":
    asyncio.run(emergency_service_test())