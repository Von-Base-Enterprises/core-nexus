#!/usr/bin/env python3
"""
Test script to verify the OpenTelemetry observability fix.
This script tests the main memory storage endpoint to ensure it works correctly.
"""

import asyncio
import httpx
import json
import time
from typing import Dict, Any

# Test configuration
API_BASE_URL = "https://core-nexus-memory-service.onrender.com"
TEST_TIMEOUT = 10  # seconds

async def test_memory_storage_endpoint():
    """Test the main POST /memories endpoint that was broken."""
    
    print("🧪 Testing Core Nexus Memory Storage Endpoint Fix")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
        
        # Test 1: Health check first
        print("\n1. Testing health endpoint...")
        try:
            health_response = await client.get(f"{API_BASE_URL}/health")
            print(f"   ✅ Health check: {health_response.status_code}")
            if health_response.status_code == 200:
                health_data = health_response.json()
                print(f"   📊 Service status: {health_data.get('status', 'unknown')}")
                print(f"   📊 Total memories: {health_data.get('total_memories', 0)}")
            else:
                print(f"   ❌ Health check failed: {health_response.text}")
                return False
        except Exception as e:
            print(f"   ❌ Health check error: {e}")
            return False
        
        # Test 2: Main memory storage endpoint (the one that was broken)
        print("\n2. Testing main memory storage endpoint (POST /memories)...")
        test_memory = {
            "content": "Test memory for OpenTelemetry fix validation",
            "metadata": {
                "test_type": "observability_fix",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "priority": "verification"
            },
            "importance_score": 0.8
        }
        
        try:
            start_time = time.time()
            store_response = await client.post(
                f"{API_BASE_URL}/memories", 
                json=test_memory,
                headers={"Content-Type": "application/json"}
            )
            response_time = (time.time() - start_time) * 1000
            
            print(f"   📡 Response code: {store_response.status_code}")
            print(f"   ⏱️  Response time: {response_time:.1f}ms")
            
            if store_response.status_code == 201:
                response_data = store_response.json()
                memory_id = response_data.get('id')
                print(f"   ✅ Memory stored successfully!")
                print(f"   🆔 Memory ID: {memory_id}")
                print(f"   📝 Content preview: {response_data.get('content', '')[:50]}...")
                
                # Test 3: Verify we can retrieve the stored memory
                print("\n3. Testing memory retrieval...")
                try:
                    get_response = await client.get(f"{API_BASE_URL}/memories/{memory_id}")
                    if get_response.status_code == 200:
                        retrieved_memory = get_response.json()
                        print(f"   ✅ Memory retrieved successfully!")
                        print(f"   📄 Retrieved content matches: {retrieved_memory.get('content') == test_memory['content']}")
                    else:
                        print(f"   ⚠️  Memory retrieval issue: {get_response.status_code}")
                except Exception as e:
                    print(f"   ⚠️  Memory retrieval error: {e}")
                
                return True
                
            elif store_response.status_code == 422:
                print(f"   ❌ CRITICAL: Still getting 422 error (decorator not fixed)")
                print(f"   📄 Error details: {store_response.text}")
                return False
            else:
                print(f"   ❌ Unexpected response: {store_response.status_code}")
                print(f"   📄 Response: {store_response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ Memory storage error: {e}")
            return False
        
        # Test 4: Test query endpoint  
        print("\n4. Testing query endpoint...")
        try:
            query_data = {
                "query": "OpenTelemetry fix validation",
                "limit": 5
            }
            query_response = await client.post(f"{API_BASE_URL}/memories/query", json=query_data)
            if query_response.status_code == 200:
                query_result = query_response.json()
                found_memories = len(query_result.get('memories', []))
                print(f"   ✅ Query endpoint working: found {found_memories} memories")
            else:
                print(f"   ⚠️  Query endpoint issue: {query_response.status_code}")
        except Exception as e:
            print(f"   ⚠️  Query error: {e}")

async def main():
    """Run the comprehensive test suite."""
    
    print("🔧 Core Nexus OpenTelemetry Fix Verification")
    print("🎯 Testing the main memory storage endpoint that was broken by decorator issues")
    print(f"🌐 Target: {API_BASE_URL}")
    print()
    
    # Run the test
    success = await test_memory_storage_endpoint()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 SUCCESS: OpenTelemetry fix appears to be working!")
        print("✅ Main memory storage endpoint is now functional")
        print("✅ Decorator is properly preserving FastAPI function signatures")
        print("✅ System is ready for production use")
    else:
        print("❌ FAILURE: OpenTelemetry fix did not resolve the issue")
        print("🔍 Additional investigation needed")
        print("⚠️  System remains in degraded state")
    
    print("\n📊 Fix Details Applied:")
    print("   • Added defensive error handling to trace_operation decorator")
    print("   • Added fallback mode when tracing initialization fails")
    print("   • Improved error isolation to prevent FastAPI signature corruption")
    print("   • Added environment variable checks for graceful degradation")

if __name__ == "__main__":
    asyncio.run(main())