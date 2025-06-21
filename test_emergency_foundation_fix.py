#!/usr/bin/env python3
"""
Test Emergency Foundation Fix
Validates that the emergency retrieval system is working in production.
"""

import requests
import json
from datetime import datetime

RENDER_SERVICE_URL = "https://core-nexus-memory-service.onrender.com"

def test_emergency_foundation_fix():
    """Test all emergency foundation fix endpoints"""
    print("🚨 TESTING EMERGENCY FOUNDATION FIX")
    print("=" * 50)
    
    test_results = {
        "test_started": datetime.now().isoformat(),
        "tests": {},
        "overall_success": False
    }
    
    # Test 1: GET /memories (main endpoint that was broken)
    print("\n📋 Test 1: GET /memories (main retrieval)")
    try:
        response = requests.get(f"{RENDER_SERVICE_URL}/memories", params={"limit": 5}, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            memories = data.get("memories", [])
            emergency_mode = data.get("query_metadata", {}).get("emergency_mode", False)
            
            print(f"✅ Status: {response.status_code}")
            print(f"✅ Memories returned: {len(memories)}")
            print(f"✅ Emergency mode: {emergency_mode}")
            print(f"✅ Providers used: {data.get('providers_used', [])}")
            
            if len(memories) > 0:
                print(f"✅ Sample memory: {memories[0]['content'][:50]}...")
                test_results["tests"]["get_memories"] = {
                    "success": True,
                    "memories_count": len(memories),
                    "emergency_mode": emergency_mode
                }
            else:
                print("❌ No memories returned")
                test_results["tests"]["get_memories"] = {"success": False, "error": "No memories returned"}
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"Response: {response.text}")
            test_results["tests"]["get_memories"] = {"success": False, "error": f"HTTP {response.status_code}"}
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        test_results["tests"]["get_memories"] = {"success": False, "error": str(e)}
    
    # Test 2: GET /memories with search query
    print("\n🔍 Test 2: GET /memories with search")
    try:
        response = requests.get(
            f"{RENDER_SERVICE_URL}/memories", 
            params={"query": "test", "limit": 3}, 
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            memories = data.get("memories", [])
            
            print(f"✅ Status: {response.status_code}")
            print(f"✅ Search results: {len(memories)}")
            
            for i, memory in enumerate(memories, 1):
                print(f"  {i}. {memory['content'][:50]}... (Score: {memory.get('similarity_score', 0)})")
            
            test_results["tests"]["search_memories"] = {
                "success": True,
                "results_count": len(memories)
            }
        else:
            print(f"❌ Search failed: {response.status_code}")
            test_results["tests"]["search_memories"] = {"success": False, "error": f"HTTP {response.status_code}"}
            
    except Exception as e:
        print(f"❌ Search exception: {e}")
        test_results["tests"]["search_memories"] = {"success": False, "error": str(e)}
    
    # Test 3: GET /memories/{id} (individual memory lookup)
    # First get a memory ID from the list
    memory_id = None
    try:
        response = requests.get(f"{RENDER_SERVICE_URL}/memories", params={"limit": 1}, timeout=30)
        if response.status_code == 200:
            data = response.json()
            memories = data.get("memories", [])
            if memories:
                memory_id = memories[0]["id"]
    except:
        pass
    
    print(f"\n🎯 Test 3: GET /memories/{{id}} (individual lookup)")
    if memory_id:
        try:
            response = requests.get(f"{RENDER_SERVICE_URL}/memories/{memory_id}", timeout=30)
            
            if response.status_code == 200:
                memory = response.json()
                print(f"✅ Status: {response.status_code}")
                print(f"✅ Memory found: {memory['content'][:50]}...")
                print(f"✅ Memory ID: {memory['id']}")
                
                test_results["tests"]["get_memory_by_id"] = {
                    "success": True,
                    "memory_id": memory_id
                }
            else:
                print(f"❌ Individual lookup failed: {response.status_code}")
                print(f"Response: {response.text}")
                test_results["tests"]["get_memory_by_id"] = {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            print(f"❌ Individual lookup exception: {e}")
            test_results["tests"]["get_memory_by_id"] = {"success": False, "error": str(e)}
    else:
        print("⚠️ Skipped - no memory ID available")
        test_results["tests"]["get_memory_by_id"] = {"success": False, "error": "No memory ID available"}
    
    # Test 4: Health check to see if emergency system is initialized
    print(f"\n🏥 Test 4: Health check")
    try:
        response = requests.get(f"{RENDER_SERVICE_URL}/health", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check successful")
            print(f"✅ Service status: {data.get('status', 'unknown')}")
            
            # Check provider status
            providers = data.get("providers", {})
            for provider_name, provider_info in providers.items():
                status = provider_info.get("status", "unknown")
                print(f"  {provider_name}: {status}")
            
            test_results["tests"]["health_check"] = {
                "success": True,
                "service_status": data.get("status")
            }
        else:
            print(f"❌ Health check failed: {response.status_code}")
            test_results["tests"]["health_check"] = {"success": False, "error": f"HTTP {response.status_code}"}
            
    except Exception as e:
        print(f"❌ Health check exception: {e}")
        test_results["tests"]["health_check"] = {"success": False, "error": str(e)}
    
    # Determine overall success
    successful_tests = sum(1 for test in test_results["tests"].values() if test.get("success", False))
    total_tests = len(test_results["tests"])
    
    test_results["successful_tests"] = successful_tests
    test_results["total_tests"] = total_tests
    test_results["overall_success"] = successful_tests >= 3  # Need at least 3/4 tests to pass
    
    print(f"\n📊 TEST SUMMARY")
    print("=" * 20)
    print(f"Successful tests: {successful_tests}/{total_tests}")
    
    if test_results["overall_success"]:
        print("🎉 EMERGENCY FOUNDATION FIX SUCCESSFUL!")
        print("✅ Memory retrieval system restored")
        print("✅ API endpoints now functional")
        print("✅ Foundation ready for ChromaDB replication work")
    else:
        print("❌ EMERGENCY FOUNDATION FIX FAILED")
        print("❌ Memory retrieval still broken")
        print("❌ Need to debug emergency system")
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f"emergency_fix_test_results_{timestamp}.json"
    with open(results_file, 'w') as f:
        json.dump(test_results, f, indent=2)
    
    print(f"\n📄 Test results saved to: {results_file}")
    
    return test_results["overall_success"]

if __name__ == "__main__":
    import sys
    success = test_emergency_foundation_fix()
    sys.exit(0 if success else 1)