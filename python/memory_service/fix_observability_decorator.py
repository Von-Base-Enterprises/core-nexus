#!/usr/bin/env python3
"""
Quick test to check if we can access the API with a workaround
"""

import requests
import json

BASE_URL = "https://core-nexus-memory-service.onrender.com"

# Try the batch endpoint which might not have the decorator issue
def test_batch_endpoint():
    print("Testing batch endpoint...")
    
    memories = [{
        "content": "Test memory from batch endpoint",
        "metadata": {"test": True, "source": "api_test"}
    }]
    
    response = requests.post(
        f"{BASE_URL}/memories/batch",
        json=memories,
        headers={"Content-Type": "application/json"},
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("Success! Batch endpoint works")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Error: {response.text}")
    
    return response.status_code == 200

# Try the simple health check
def test_health():
    print("\nTesting health endpoint...")
    response = requests.get(f"{BASE_URL}/health", timeout=10)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Service Status: {data.get('status')}")
        print(f"Uptime: {data.get('uptime_seconds', 0) / 60:.1f} minutes")
        print(f"Total memories: {data.get('total_memories', 'Unknown')}")
        
        # Check providers
        providers = data.get('providers', {})
        for name, info in providers.items():
            print(f"\n{name.upper()} Provider:")
            print(f"  Status: {info.get('status')}")
            if 'details' in info and 'details' in info['details']:
                details = info['details']['details']
                if 'total_vectors' in details:
                    print(f"  Vectors: {details['total_vectors']}")
    return response.status_code == 200

# Try import endpoint
def test_import():
    print("\nTesting import endpoint...")
    
    import_data = {
        "memories": [
            {
                "content": "Test memory via import endpoint",
                "metadata": {"test": True, "import_test": True}
            }
        ],
        "batch_size": 1,
        "provider": "pgvector"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/memories/import",
        json=import_data,
        headers={"Content-Type": "application/json"},
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code in [200, 202]:
        print("Success! Import endpoint works")
        print(response.text[:200])
    else:
        print(f"Error: {response.text}")
    
    return response.status_code in [200, 202]

# Test memory retrieval
def test_get_memories():
    print("\nTesting memory retrieval...")
    
    response = requests.get(
        f"{BASE_URL}/memories",
        params={"limit": 5},
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        # Handle both list and dict responses
        if isinstance(data, dict):
            memories = data.get('results', [])
        else:
            memories = data
        print(f"Retrieved {len(memories)} memories")
        if memories and len(memories) > 0:
            print("\nFirst memory:")
            first = memories[0]
            print(f"  ID: {first.get('id', 'N/A')}")
            print(f"  Content: {first.get('content', '')[:100]}...")
            print(f"  Created: {first.get('created_at', 'N/A')}")
    
    return response.status_code == 200

if __name__ == "__main__":
    print("Testing Core Nexus API workarounds...")
    print("=" * 60)
    
    # Run tests
    health_ok = test_health()
    get_ok = test_get_memories()
    batch_ok = test_batch_endpoint()
    import_ok = test_import()
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"Health Check: {'✓' if health_ok else '✗'}")
    print(f"GET Memories: {'✓' if get_ok else '✗'}")
    print(f"Batch Endpoint: {'✓' if batch_ok else '✗'}")
    print(f"Import Endpoint: {'✓' if import_ok else '✗'}")
    
    if not (health_ok and get_ok):
        print("\nCRITICAL: Basic functionality is broken!")
    elif not (batch_ok or import_ok):
        print("\nWARNING: Cannot create new memories!")
    else:
        print("\nService is partially functional using alternate endpoints")