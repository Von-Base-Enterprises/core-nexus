#!/usr/bin/env python3
"""
Test script for bulk import API functionality
Demonstrates CSV, JSON, and JSONL import capabilities
"""

import base64
import json
import time
import requests
from typing import Dict, Any

# API configuration
API_BASE_URL = "https://core-nexus-memory-service.onrender.com"
# API_BASE_URL = "http://localhost:8000"  # For local testing


def encode_data(data: str) -> str:
    """Encode data as base64."""
    return base64.b64encode(data.encode()).decode()


def test_csv_import():
    """Test CSV import functionality."""
    print("\n🧪 Testing CSV Import...")
    
    # Sample CSV data
    csv_data = """content,importance_score,category,tags
"Machine learning is a subset of artificial intelligence",0.8,technology,"AI,ML"
"Python is a popular programming language for data science",0.9,programming,"Python,DataScience"
"Neural networks are inspired by biological neurons",0.7,technology,"AI,NeuralNetworks"
"The transformer architecture revolutionized NLP",0.9,technology,"AI,NLP,Transformers"
"Docker containers provide application isolation",0.6,devops,"Docker,Containers"
"""
    
    # Create import request
    request_data = {
        "format": "csv",
        "data": encode_data(csv_data),
        "options": {
            "deduplicate": True,
            "batch_size": 2,
            "tags": ["bulk_import", "test"],
            "source": "csv_test",
            "metadata_mapping": {
                "category": "domain",
                "tags": "keywords"
            }
        }
    }
    
    # Start import
    response = requests.post(
        f"{API_BASE_URL}/api/v1/memories/import",
        json=request_data
    )
    
    if response.status_code == 200:
        result = response.json()
        import_id = result['import_id']
        print(f"✅ CSV import started: {import_id}")
        return import_id
    else:
        print(f"❌ CSV import failed: {response.status_code} - {response.text}")
        return None


def test_json_import():
    """Test JSON import functionality."""
    print("\n🧪 Testing JSON Import...")
    
    # Sample JSON data
    json_data = {
        "memories": [
            {
                "content": "Kubernetes orchestrates containerized applications",
                "importance_score": 0.8,
                "metadata": {
                    "category": "devops",
                    "tool": "kubernetes"
                }
            },
            {
                "content": "GraphQL provides a flexible API query language",
                "importance_score": 0.7,
                "metadata": {
                    "category": "api",
                    "technology": "graphql"
                }
            },
            {
                "content": "Redis is an in-memory data structure store",
                "importance_score": 0.6,
                "metadata": {
                    "category": "database",
                    "type": "nosql"
                }
            }
        ]
    }
    
    # Create import request
    request_data = {
        "format": "json",
        "data": encode_data(json.dumps(json_data)),
        "options": {
            "deduplicate": True,
            "tags": ["json_import"],
            "source": "json_test"
        }
    }
    
    # Start import
    response = requests.post(
        f"{API_BASE_URL}/api/v1/memories/import",
        json=request_data
    )
    
    if response.status_code == 200:
        result = response.json()
        import_id = result['import_id']
        print(f"✅ JSON import started: {import_id}")
        return import_id
    else:
        print(f"❌ JSON import failed: {response.status_code} - {response.text}")
        return None


def test_jsonl_import():
    """Test JSONL import functionality."""
    print("\n🧪 Testing JSONL Import...")
    
    # Sample JSONL data (newline-delimited JSON)
    jsonl_data = """{"content": "React is a JavaScript library for building UIs", "importance_score": 0.9, "metadata": {"framework": "react"}}
{"content": "Vue.js is a progressive JavaScript framework", "importance_score": 0.8, "metadata": {"framework": "vue"}}
{"content": "Angular is a TypeScript-based web framework", "importance_score": 0.8, "metadata": {"framework": "angular"}}
{"content": "Svelte compiles components at build time", "importance_score": 0.7, "metadata": {"framework": "svelte"}}"""
    
    # Create import request
    request_data = {
        "format": "jsonl",
        "data": encode_data(jsonl_data),
        "options": {
            "deduplicate": True,
            "batch_size": 2,
            "tags": ["frontend", "frameworks"],
            "source": "jsonl_test",
            "user_id": "test_user_123"
        }
    }
    
    # Start import
    response = requests.post(
        f"{API_BASE_URL}/api/v1/memories/import",
        json=request_data
    )
    
    if response.status_code == 200:
        result = response.json()
        import_id = result['import_id']
        print(f"✅ JSONL import started: {import_id}")
        return import_id
    else:
        print(f"❌ JSONL import failed: {response.status_code} - {response.text}")
        return None


def check_import_status(import_id: str) -> Dict[str, Any]:
    """Check the status of an import job."""
    response = requests.get(
        f"{API_BASE_URL}/api/v1/memories/import/{import_id}/status"
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Failed to get status: {response.status_code}")
        return None


def monitor_import(import_id: str):
    """Monitor import progress until completion."""
    print(f"\n📊 Monitoring import {import_id}...")
    
    while True:
        status = check_import_status(import_id)
        
        if not status:
            break
            
        print(f"\r⏳ Status: {status['status']} | "
              f"Progress: {status['processed_records']}/{status['total_records']} | "
              f"Success: {status['successful_records']} | "
              f"Failed: {status['failed_records']} | "
              f"Duplicates: {status['duplicate_records']}", end='')
        
        if status['status'] in ['completed', 'failed', 'partial']:
            print()  # New line
            
            if status['errors']:
                print(f"\n⚠️ Errors encountered:")
                for error in status['errors'][:5]:  # Show first 5 errors
                    print(f"  - {error['error']}: {error.get('message', 'No details')}")
                    
            if status.get('processing_time_seconds'):
                print(f"\n⏱️ Processing time: {status['processing_time_seconds']:.2f} seconds")
                
            return status
            
        time.sleep(1)  # Poll every second


def test_large_import():
    """Test importing a larger dataset."""
    print("\n🧪 Testing Large Import (1000 records)...")
    
    # Generate large dataset
    memories = []
    categories = ["technology", "science", "business", "health", "education"]
    
    for i in range(1000):
        memory = {
            "content": f"This is test memory #{i+1} with important information about {categories[i % 5]}",
            "importance_score": 0.5 + (i % 5) * 0.1,
            "metadata": {
                "index": i,
                "category": categories[i % 5],
                "batch": i // 100
            }
        }
        memories.append(memory)
    
    # Create import request
    request_data = {
        "format": "json",
        "data": encode_data(json.dumps({"memories": memories})),
        "options": {
            "deduplicate": True,
            "batch_size": 100,
            "tags": ["large_import", "performance_test"],
            "source": "large_test"
        }
    }
    
    # Start import
    response = requests.post(
        f"{API_BASE_URL}/api/v1/memories/import",
        json=request_data
    )
    
    if response.status_code == 200:
        result = response.json()
        import_id = result['import_id']
        print(f"✅ Large import started: {import_id}")
        return import_id
    else:
        print(f"❌ Large import failed: {response.status_code} - {response.text}")
        return None


def main():
    """Run all import tests."""
    print("🚀 Core Nexus Bulk Import API Test Suite")
    print("=" * 50)
    
    # Test different formats
    import_ids = []
    
    # CSV Import
    csv_id = test_csv_import()
    if csv_id:
        import_ids.append(("CSV", csv_id))
    
    # JSON Import
    json_id = test_json_import()
    if json_id:
        import_ids.append(("JSON", json_id))
    
    # JSONL Import
    jsonl_id = test_jsonl_import()
    if jsonl_id:
        import_ids.append(("JSONL", jsonl_id))
    
    # Monitor all imports
    print("\n📊 Monitoring all imports...")
    for format_name, import_id in import_ids:
        print(f"\n--- {format_name} Import ---")
        final_status = monitor_import(import_id)
        
    # Test large import
    large_id = test_large_import()
    if large_id:
        print("\n--- Large Import ---")
        final_status = monitor_import(large_id)
        
        if final_status and final_status.get('successful_records'):
            rate = final_status['successful_records'] / final_status.get('processing_time_seconds', 1)
            print(f"📈 Import rate: {rate:.2f} memories/second")
    
    print("\n✅ All tests completed!")
    
    # Test querying imported memories
    print("\n🔍 Testing query for imported memories...")
    
    test_queries = [
        "machine learning AI",
        "kubernetes docker containers",
        "javascript frameworks"
    ]
    
    for query in test_queries:
        response = requests.post(
            f"{API_BASE_URL}/memories/query",
            json={
                "query": query,
                "limit": 3,
                "min_similarity": 0.3
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n📝 Query: '{query}'")
            print(f"   Found: {result['total_found']} memories")
            for memory in result['memories'][:3]:
                print(f"   - {memory['content'][:80]}...")
        else:
            print(f"❌ Query failed: {response.status_code}")


if __name__ == "__main__":
    main()