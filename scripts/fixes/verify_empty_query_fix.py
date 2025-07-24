#!/usr/bin/env python3
"""
Verify that the empty query fix is working correctly in production.
This tests the specific issue where empty queries were only returning 3 results.
"""

import requests
import json
import os
from datetime import datetime

def test_empty_query():
    """Test that empty queries return all memories, not just 3"""
    base_url = os.getenv("MEMORY_SERVICE_URL", "https://core-nexus-memory-service.onrender.com")
    
    print(f"🔍 Testing empty query fix on: {base_url}")
    print("=" * 60)
    
    # Test 1: POST /memories/query with empty string
    print("\n1. Testing POST /memories/query with empty query...")
    response = requests.post(
        f"{base_url}/memories/query",
        json={
            "query": "",
            "limit": 100,
            "min_similarity": 0.0
        },
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        memory_count = len(data.get("memories", []))
        total_found = data.get("total_found", 0)
        
        print(f"   ✅ Success! Status: {response.status_code}")
        print(f"   📊 Memories returned: {memory_count}")
        print(f"   📊 Total available: {total_found}")
        
        if memory_count > 3:
            print(f"   ✅ VERIFIED: Empty query returns more than 3 results!")
        else:
            print(f"   ❌ ISSUE: Only {memory_count} results returned")
            
        # Show trust metrics if available
        if "trust_metrics" in data:
            print(f"   🔐 Trust metrics: {json.dumps(data['trust_metrics'], indent=6)}")
    else:
        print(f"   ❌ Failed with status: {response.status_code}")
        print(f"   Error: {response.text}")
    
    # Test 2: GET /memories endpoint
    print("\n2. Testing GET /memories endpoint...")
    response = requests.get(
        f"{base_url}/memories",
        params={"limit": 100},
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        memory_count = len(data.get("memories", []))
        total_found = data.get("total_found", 0)
        
        print(f"   ✅ Success! Status: {response.status_code}")
        print(f"   📊 Memories returned: {memory_count}")
        print(f"   📊 Total available: {total_found}")
        
        if memory_count > 3:
            print(f"   ✅ VERIFIED: GET /memories returns more than 3 results!")
        else:
            print(f"   ❌ ISSUE: Only {memory_count} results returned")
    else:
        print(f"   ❌ Failed with status: {response.status_code}")
        print(f"   Error: {response.text}")
    
    # Test 3: Compare with non-empty query
    print("\n3. Testing with actual search query for comparison...")
    response = requests.post(
        f"{base_url}/memories/query",
        json={
            "query": "test",
            "limit": 100,
            "min_similarity": 0.3
        },
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        memory_count = len(data.get("memories", []))
        
        print(f"   ✅ Success! Status: {response.status_code}")
        print(f"   📊 Memories returned: {memory_count}")
        print(f"   📍 This is a filtered search result")
    else:
        print(f"   ❌ Failed with status: {response.status_code}")
    
    print("\n" + "=" * 60)
    print("✅ Empty query fix verification complete!")
    print(f"🕒 Tested at: {datetime.utcnow().isoformat()}")

if __name__ == "__main__":
    test_empty_query()