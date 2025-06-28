#!/usr/bin/env python3
"""
Test script for JARVIS Integration

This script demonstrates how the new JARVIS reasoning integration works.
"""

import json
import asyncio
import httpx
from typing import Dict, Any

# Test endpoints
MEMORY_SERVICE_URL = "https://core-nexus-memory-service.onrender.com"
JARVIS_SERVICE_URL = "https://jarvis-ai-agent-aa4m.onrender.com"

async def test_jarvis_integration():
    """Test the new JARVIS integration functionality"""
    
    print("🧪 Testing JARVIS Integration")
    print("=" * 50)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Test 1: Query without reasoning (traditional behavior)
        print("\n1️⃣ Testing query WITHOUT reasoning (should work as before)")
        query_without_reasoning = {
            "query": "What are the key technical challenges in our European expansion?",
            "include_reasoning": False,
            "limit": 5
        }
        
        try:
            response = await client.post(
                f"{MEMORY_SERVICE_URL}/memories/query",
                json=query_without_reasoning
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Memories found: {data.get('total_found', 0)}")
                print(f"   Reasoning analysis: {data.get('reasoning_analysis') is not None}")
                print("   ✅ Traditional query works")
            else:
                print(f"   ❌ Query failed: {response.text}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 2: Query with reasoning (NEW functionality)
        print("\n2️⃣ Testing query WITH reasoning (NEW JARVIS integration)")
        query_with_reasoning = {
            "query": "What are the key technical challenges in our European expansion?",
            "include_reasoning": True,
            "limit": 5
        }
        
        try:
            response = await client.post(
                f"{MEMORY_SERVICE_URL}/memories/query",
                json=query_with_reasoning
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Memories found: {data.get('total_found', 0)}")
                
                reasoning = data.get('reasoning_analysis')
                if reasoning:
                    print("   ✅ JARVIS reasoning analysis provided!")
                    print(f"   Analysis success: {reasoning.get('success', False)}")
                    if reasoning.get('success'):
                        print(f"   Task ID: {reasoning.get('task_id', 'unknown')}")
                        print(f"   Summary: {reasoning.get('summary', 'No summary')[:100]}...")
                        performance = reasoning.get('performance', {})
                        print(f"   Duration: {performance.get('duration_seconds', 0):.2f}s")
                        print(f"   Iterations: {performance.get('iterations', 0)}")
                    else:
                        print(f"   Analysis error: {reasoning.get('error', 'Unknown error')}")
                else:
                    print("   ⚠️ No reasoning analysis in response")
            else:
                print(f"   ❌ Query failed: {response.text}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 3: Verify both services are healthy
        print("\n3️⃣ Testing service health")
        
        # Check Memory Service
        try:
            response = await client.get(f"{MEMORY_SERVICE_URL}/health")
            if response.status_code == 200:
                print("   ✅ Memory Service: Healthy")
            else:
                print("   ❌ Memory Service: Unhealthy")
        except Exception as e:
            print(f"   ❌ Memory Service error: {e}")
        
        # Check JARVIS Service
        try:
            response = await client.get(f"{JARVIS_SERVICE_URL}/health")
            if response.status_code == 200:
                data = response.json()
                print("   ✅ JARVIS Service: Healthy")
                print(f"      Active tasks: {data.get('active_tasks', 0)}")
                core_nexus = data.get('core_nexus_status', {})
                print(f"      Core Nexus connection: {core_nexus.get('status', 'unknown')}")
            else:
                print("   ❌ JARVIS Service: Unhealthy")
        except Exception as e:
            print(f"   ❌ JARVIS Service error: {e}")

def test_request_models():
    """Test that our new request/response models work correctly"""
    print("\n4️⃣ Testing new request/response models")
    
    # Test QueryRequest with new field
    from python.memory_service.src.memory_service.models import QueryRequest, QueryResponse
    
    # Test QueryRequest
    request = QueryRequest(
        query="test query",
        include_reasoning=True,
        limit=10
    )
    print("   ✅ QueryRequest with include_reasoning works")
    print(f"      include_reasoning: {request.include_reasoning}")
    
    # Test QueryResponse
    response = QueryResponse(
        memories=[],
        total_found=0,
        reasoning_analysis={"success": True, "summary": "Test analysis"}
    )
    print("   ✅ QueryResponse with reasoning_analysis works") 
    print(f"      reasoning_analysis: {response.reasoning_analysis is not None}")

async def main():
    """Main test function"""
    print("🔧 JARVIS Integration Test Suite")
    print("Testing the fix for the Core Nexus routing problem")
    print()
    
    # Test the models first (doesn't require network)
    try:
        test_request_models()
    except Exception as e:
        print(f"   ❌ Model test failed: {e}")
    
    # Test the live integration
    await test_jarvis_integration()
    
    print("\n" + "=" * 50)
    print("🎯 SUMMARY:")
    print("The integration adds the missing link between vector search and JARVIS reasoning.")
    print("Now when include_reasoning=True, the system will:")
    print("  1. Do vector search as before")
    print("  2. Send results to JARVIS for intelligent analysis") 
    print("  3. Return both memories AND reasoning analysis")
    print("\nThis fixes the core problem where JARVIS wasn't being triggered at all!")

if __name__ == "__main__":
    asyncio.run(main())