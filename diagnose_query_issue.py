#!/usr/bin/env python3
"""Diagnose the query issue in production"""

import requests
import json

BASE_URL = "https://core-nexus-memory-service.onrender.com"

print("🔍 Diagnosing Core Nexus Query Issue")
print("=" * 50)

# 1. Check health
print("\n1. Health Check:")
health = requests.get(f"{BASE_URL}/health").json()
print(f"   Status: {health['status']}")
print(f"   Total Memories: {health['total_memories']}")
print(f"   Providers: {list(health['providers'].keys())}")

# 2. Check provider details
print("\n2. Provider Details:")
providers = requests.get(f"{BASE_URL}/providers").json()
for provider in providers['providers']:
    print(f"   {provider['name']}: enabled={provider['enabled']}, primary={provider['primary']}")

# 3. Test embedding
print("\n3. Test Embedding Generation:")
try:
    embed_test = requests.post(f"{BASE_URL}/embeddings/test?text=test").json()
    print(f"   Model: {embed_test.get('model_type', 'Unknown')}")
    print(f"   Success: {embed_test.get('success', False)}")
    print(f"   Generation Time: {embed_test.get('generation_time_ms', 'N/A')}ms")
except Exception as e:
    print(f"   Error: {e}")

# 4. Test memory storage
print("\n4. Test Memory Storage:")
memory_data = {
    "content": "Diagnostic test memory for query debugging",
    "metadata": {"test": True, "purpose": "diagnosis"}
}
try:
    store_response = requests.post(
        f"{BASE_URL}/memories",
        json=memory_data,
        headers={"Content-Type": "application/json"}
    ).json()
    print(f"   Success: Memory ID = {store_response.get('id', 'Failed')}")
except Exception as e:
    print(f"   Error: {e}")

# 5. Test query with different parameters
print("\n5. Testing Query Endpoint:")

# Test 1: Simple query
print("\n   Test 1 - Simple query:")
try:
    response = requests.post(
        f"{BASE_URL}/memories/query",
        json={"query": "test", "limit": 5},
        headers={"Content-Type": "application/json"}
    )
    if response.status_code == 200:
        data = response.json()
        print(f"   Success: Found {data.get('total_found', 0)} memories")
    else:
        print(f"   Error {response.status_code}: {response.text}")
except Exception as e:
    print(f"   Exception: {e}")

# Test 2: Empty query
print("\n   Test 2 - Empty query:")
try:
    response = requests.post(
        f"{BASE_URL}/memories/query",
        json={"query": "", "limit": 5},
        headers={"Content-Type": "application/json"}
    )
    print(f"   Response: {response.status_code}")
except Exception as e:
    print(f"   Exception: {e}")

# 6. Check logs
print("\n6. Recent Logs:")
try:
    logs = requests.get(f"{BASE_URL}/debug/logs?lines=10").json()
    if 'logs' in logs and logs['logs']:
        for log in logs['logs'][-3:]:
            print(f"   [{log.get('level')}] {log.get('message', '')[:100]}")
except Exception as e:
    print(f"   Could not fetch logs: {e}")

print("\n" + "=" * 50)
print("Diagnosis complete. The issue appears to be:")
print("'dictionary update sequence element #0 has length 1; 2 is required'")
print("\nThis suggests a problem with how metadata is being processed in queries.")
print("The fix requires updating the pgvector provider code or the database schema.")