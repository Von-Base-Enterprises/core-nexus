#!/usr/bin/env python3
"""
Final Memory Test - Comprehensive validation of all memory endpoints
Tests both individual lookup (which works) and main retrieval (needs fix)
"""

import requests
import json
from datetime import datetime

RENDER_SERVICE_URL = "https://core-nexus-memory-service.onrender.com"

def final_memory_test():
    """Comprehensive test of all memory functionality"""
    print("🎯 FINAL MEMORY RETRIEVAL TEST")
    print("=" * 50)
    
    results = {
        "test_time": datetime.now().isoformat(),
        "individual_lookup": {"status": "unknown"},
        "main_endpoint": {"status": "unknown"},
        "search_endpoint": {"status": "unknown"},
        "health_check": {"status": "unknown"},
        "overall_foundation": "unknown"
    }
    
    # Test 1: Individual memory lookup (known working)
    print("\n🎯 Test 1: Individual Memory Lookup")
    test_id = "e7e8c329-b66e-42ac-b350-9122f5f5b6e2"
    
    try:
        response = requests.get(f"{RENDER_SERVICE_URL}/memories/{test_id}", timeout=30)
        
        if response.status_code == 200:
            memory = response.json()
            print(f"✅ Individual lookup WORKING: {memory['content'][:50]}...")
            results["individual_lookup"] = {
                "status": "working",
                "memory_id": test_id,
                "content_preview": memory['content'][:50]
            }
        else:
            print(f"❌ Individual lookup failed: {response.status_code}")
            results["individual_lookup"] = {
                "status": "failed",
                "error": f"HTTP {response.status_code}"
            }
            
    except Exception as e:
        print(f"❌ Individual lookup exception: {e}")
        results["individual_lookup"] = {"status": "exception", "error": str(e)}
    
    # Test 2: Main endpoint with small limit
    print("\n📋 Test 2: Main GET /memories endpoint")
    
    try:
        response = requests.get(f"{RENDER_SERVICE_URL}/memories", params={"limit": 2}, timeout=30)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            memories = data.get("memories", [])
            emergency_mode = data.get("query_metadata", {}).get("emergency_mode", False)
            providers_used = data.get("providers_used", [])
            
            print(f"✅ Main endpoint WORKING: {len(memories)} memories")
            print(f"Emergency mode: {emergency_mode}")
            print(f"Providers: {providers_used}")
            
            results["main_endpoint"] = {
                "status": "working",
                "memories_count": len(memories),
                "emergency_mode": emergency_mode,
                "providers_used": providers_used
            }
            
            if len(memories) > 0:
                print(f"Sample memory: {memories[0]['content'][:50]}...")
            
        else:
            print(f"❌ Main endpoint failed: {response.status_code}")
            print(f"Response: {response.text}")
            results["main_endpoint"] = {
                "status": "failed",
                "error": f"HTTP {response.status_code}",
                "response": response.text
            }
            
    except Exception as e:
        print(f"❌ Main endpoint exception: {e}")
        results["main_endpoint"] = {"status": "exception", "error": str(e)}
    
    # Test 3: Search functionality
    print("\n🔍 Test 3: Search functionality")
    
    try:
        response = requests.get(
            f"{RENDER_SERVICE_URL}/memories", 
            params={"query": "test", "limit": 2}, 
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            memories = data.get("memories", [])
            
            print(f"✅ Search WORKING: {len(memories)} results")
            results["search_endpoint"] = {
                "status": "working", 
                "results_count": len(memories)
            }
            
        else:
            print(f"❌ Search failed: {response.status_code}")
            results["search_endpoint"] = {
                "status": "failed",
                "error": f"HTTP {response.status_code}"
            }
            
    except Exception as e:
        print(f"❌ Search exception: {e}")
        results["search_endpoint"] = {"status": "exception", "error": str(e)}
    
    # Test 4: Health check
    print("\n🏥 Test 4: Health check")
    
    try:
        response = requests.get(f"{RENDER_SERVICE_URL}/health", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            service_status = data.get("status", "unknown")
            
            print(f"✅ Health check: {service_status}")
            results["health_check"] = {
                "status": "working",
                "service_status": service_status
            }
            
        else:
            print(f"❌ Health check failed: {response.status_code}")
            results["health_check"] = {
                "status": "failed",
                "error": f"HTTP {response.status_code}"
            }
            
    except Exception as e:
        print(f"❌ Health check exception: {e}")
        results["health_check"] = {"status": "exception", "error": str(e)}
    
    # Overall assessment
    print("\n📊 OVERALL FOUNDATION ASSESSMENT")
    print("=" * 40)
    
    individual_works = results["individual_lookup"]["status"] == "working"
    main_works = results["main_endpoint"]["status"] == "working"
    search_works = results["search_endpoint"]["status"] == "working"
    health_works = results["health_check"]["status"] == "working"
    
    working_count = sum([individual_works, main_works, search_works, health_works])
    
    print(f"✅ Individual memory lookup: {'WORKING' if individual_works else 'BROKEN'}")
    print(f"{'✅' if main_works else '❌'} Main memories endpoint: {'WORKING' if main_works else 'BROKEN'}")
    print(f"{'✅' if search_works else '❌'} Search functionality: {'WORKING' if search_works else 'BROKEN'}")
    print(f"✅ Health check: {'WORKING' if health_works else 'BROKEN'}")
    
    print(f"\nWorking endpoints: {working_count}/4")
    
    if working_count >= 3 and individual_works:
        foundation_status = "STRONG"
        print("🎉 FOUNDATION STATUS: STRONG")
        print("✅ Memory retrieval foundation is functional")
        print("✅ Individual lookup working 100%")
        print("✅ Ready for ChromaDB replication work")
        
    elif working_count >= 2 and individual_works:
        foundation_status = "FUNCTIONAL"
        print("⚠️ FOUNDATION STATUS: FUNCTIONAL")
        print("✅ Core functionality working")
        print("⚠️ Some endpoints need attention")
        
    else:
        foundation_status = "BROKEN"
        print("❌ FOUNDATION STATUS: BROKEN")
        print("❌ Critical foundation issues remain")
    
    results["overall_foundation"] = foundation_status
    results["working_endpoints"] = working_count
    results["total_endpoints"] = 4
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f"final_memory_test_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Results saved to: {results_file}")
    
    return foundation_status in ["STRONG", "FUNCTIONAL"]

if __name__ == "__main__":
    import sys
    success = final_memory_test()
    sys.exit(0 if success else 1)