#!/usr/bin/env python3
"""
GraphRAG Production Verification Script
Tests all aspects of the knowledge graph functionality
"""

import asyncio
import httpx
import json
from datetime import datetime

BASE_URL = "https://core-nexus-memory-service.onrender.com"
API_KEY = "dev-key-12345"  # Default development API key

async def run_tests():
    headers = {"X-API-Key": API_KEY}
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        results = []
        
        # Test 1: Check if graph provider is enabled
        print("1. Testing graph provider status...")
        try:
            resp = await client.get(f"{BASE_URL}/providers")
            data = resp.json()
            graph_enabled = any(p['name'] == 'graph' and p['enabled'] for p in data['providers'])
            results.append({
                "test": "Graph Provider Status",
                "passed": graph_enabled,
                "details": f"Graph provider {'enabled' if graph_enabled else 'NOT enabled'}",
                "response": data
            })
        except Exception as e:
            results.append({
                "test": "Graph Provider Status",
                "passed": False,
                "error": str(e)
            })
        
        # Test 2: Graph stats endpoint
        print("2. Testing graph statistics...")
        try:
            resp = await client.get(f"{BASE_URL}/graph/stats")
            if resp.status_code == 200:
                data = resp.json()
                results.append({
                    "test": "Graph Statistics",
                    "passed": True,
                    "details": f"Entities: {data.get('statistics', {}).get('total_entities', 0)}, "
                              f"Relationships: {data.get('statistics', {}).get('total_relationships', 0)}",
                    "response": data
                })
            else:
                results.append({
                    "test": "Graph Statistics",
                    "passed": False,
                    "error": f"Status {resp.status_code}: {resp.text}"
                })
        except Exception as e:
            results.append({
                "test": "Graph Statistics",
                "passed": False,
                "error": str(e)
            })
        
        # Test 3: Store a test memory with entity extraction
        print("3. Testing memory storage with entity extraction...")
        test_memory = {
            "content": "John Smith, the CTO of Von Base Enterprises, is leading the development of Core Nexus AI system using advanced machine learning technologies.",
            "metadata": {
                "test": True,
                "timestamp": datetime.now().isoformat()
            }
        }
        try:
            resp = await client.post(f"{BASE_URL}/memories/store", json=test_memory)
            if resp.status_code == 200:
                memory_id = resp.json()['id']
                results.append({
                    "test": "Memory Storage",
                    "passed": True,
                    "memory_id": memory_id,
                    "details": "Memory stored successfully"
                })
                
                # Test 4: Sync memory to graph
                print("4. Testing graph sync...")
                sync_resp = await client.post(f"{BASE_URL}/graph/sync/{memory_id}")
                if sync_resp.status_code == 200:
                    sync_data = sync_resp.json()
                    results.append({
                        "test": "Graph Sync",
                        "passed": True,
                        "entities": sync_data.get('entities_extracted', 0),
                        "relationships": sync_data.get('relationships_created', 0),
                        "details": f"Extracted {sync_data.get('entities_extracted', 0)} entities"
                    })
                else:
                    results.append({
                        "test": "Graph Sync",
                        "passed": False,
                        "error": f"Status {sync_resp.status_code}: {sync_resp.text}"
                    })
            else:
                results.append({
                    "test": "Memory Storage",
                    "passed": False,
                    "error": f"Status {resp.status_code}: {resp.text}"
                })
        except Exception as e:
            results.append({
                "test": "Memory Storage/Sync",
                "passed": False,
                "error": str(e)
            })
        
        # Test 5: Entity exploration
        print("5. Testing entity exploration...")
        try:
            resp = await client.get(f"{BASE_URL}/graph/explore/Von%20Base%20Enterprises")
            if resp.status_code == 200:
                data = resp.json()
                results.append({
                    "test": "Entity Exploration",
                    "passed": True,
                    "memories_found": data.get('memories_found', 0),
                    "details": f"Found {data.get('memories_found', 0)} memories for entity"
                })
            else:
                results.append({
                    "test": "Entity Exploration",
                    "passed": False,
                    "error": f"Status {resp.status_code}: {resp.text}"
                })
        except Exception as e:
            results.append({
                "test": "Entity Exploration",
                "passed": False,
                "error": str(e)
            })
        
        # Test 6: Graph-enhanced query
        print("6. Testing graph-enhanced query...")
        query_request = {
            "query": "Core Nexus AI development",
            "enable_graph_retrieval": True,
            "graph_weight": 0.3,
            "limit": 10
        }
        try:
            resp = await client.post(f"{BASE_URL}/memories/query-graph", json=query_request)
            if resp.status_code == 200:
                data = resp.json()
                results.append({
                    "test": "Graph-Enhanced Query",
                    "passed": True,
                    "memories_found": len(data.get('memories', [])),
                    "entities_extracted": len(data.get('extracted_entities', [])),
                    "evidence_chains": len(data.get('evidence_chains', [])),
                    "graph_enabled": data.get('graph_retrieval_enabled', False),
                    "details": f"Found {len(data.get('memories', []))} memories with {len(data.get('evidence_chains', []))} evidence chains"
                })
            else:
                results.append({
                    "test": "Graph-Enhanced Query",
                    "passed": False,
                    "error": f"Status {resp.status_code}: {resp.text}"
                })
        except Exception as e:
            results.append({
                "test": "Graph-Enhanced Query",
                "passed": False,
                "error": str(e)
            })
        
        # Test 7: Path finding
        print("7. Testing path finding between entities...")
        try:
            resp = await client.get(f"{BASE_URL}/graph/path/John%20Smith/Core%20Nexus?max_depth=3")
            if resp.status_code == 200:
                data = resp.json()
                results.append({
                    "test": "Path Finding",
                    "passed": True,
                    "paths_found": len(data.get('paths', [])),
                    "details": f"Found {len(data.get('paths', []))} paths between entities"
                })
            else:
                results.append({
                    "test": "Path Finding",
                    "passed": False,
                    "error": f"Status {resp.status_code}: {resp.text}"
                })
        except Exception as e:
            results.append({
                "test": "Path Finding",
                "passed": False,
                "error": str(e)
            })
        
        return results

async def main():
    print("=" * 70)
    print("GraphRAG Production Verification")
    print(f"Target: {BASE_URL}")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 70)
    print()
    
    results = await run_tests()
    
    print("\n" + "=" * 70)
    print("TEST RESULTS")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for result in results:
        status = "✅ PASS" if result.get('passed') else "❌ FAIL"
        print(f"\n{status} - {result['test']}")
        
        if result.get('passed'):
            passed += 1
            if 'details' in result:
                print(f"   Details: {result['details']}")
            for key, value in result.items():
                if key not in ['test', 'passed', 'details', 'response', 'error']:
                    print(f"   {key}: {value}")
        else:
            failed += 1
            if 'error' in result:
                print(f"   Error: {result['error']}")
    
    print("\n" + "=" * 70)
    print(f"SUMMARY: {passed} passed, {failed} failed")
    print("=" * 70)
    
    # Save detailed results
    with open('graphrag_test_results.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'url': BASE_URL,
            'results': results,
            'summary': {
                'passed': passed,
                'failed': failed,
                'total': len(results)
            }
        }, f, indent=2, default=str)
    
    print("\nDetailed results saved to graphrag_test_results.json")
    
    # Final verdict
    if failed == 0:
        print("\n🎉 GraphRAG is FULLY FUNCTIONAL in production!")
    elif passed > failed:
        print("\n⚠️  GraphRAG is PARTIALLY FUNCTIONAL - some features need attention")
    else:
        print("\n❌ GraphRAG is NOT FUNCTIONAL - critical issues detected")

if __name__ == "__main__":
    asyncio.run(main())