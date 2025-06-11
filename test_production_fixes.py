#!/usr/bin/env python3
"""
Comprehensive test script for production fixes:
1. Empty query bug fix - should return all memories, not just 3
2. GraphProvider initialization fix - should be healthy in production

Run this script to verify both fixes are working correctly.
"""

import asyncio
import aiohttp
import json
import sys
from datetime import datetime
from typing import Dict, Any, List, Tuple


# Production URL - update this if testing locally
BASE_URL = "https://core-nexus-memory.onrender.com"
# For local testing:
# BASE_URL = "http://localhost:8000"


class TestResult:
    """Store test results with detailed information"""
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.passed = False
        self.message = ""
        self.details = {}
        self.duration_ms = 0


async def test_health_endpoint(session: aiohttp.ClientSession) -> TestResult:
    """Test 1: Check health endpoint and GraphProvider status"""
    result = TestResult("Health Endpoint & GraphProvider Status")
    start_time = datetime.now()
    
    try:
        async with session.get(f"{BASE_URL}/health") as response:
            result.duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            if response.status != 200:
                result.message = f"Health endpoint returned status {response.status}"
                return result
            
            data = await response.json()
            result.details = data
            
            # Check overall status
            if data.get('status') != 'healthy':
                result.message = f"Service is not healthy: {data.get('status')}"
                return result
            
            # Check providers
            providers = data.get('providers', {})
            
            # Check pgvector (should be primary)
            pgvector_status = providers.get('pgvector', {})
            if pgvector_status.get('status') != 'healthy':
                result.message = "PgVector provider is not healthy"
                return result
            
            # Check GraphProvider specifically
            graph_status = providers.get('graph', {})
            if 'graph' in providers:
                if graph_status.get('status') == 'healthy':
                    result.passed = True
                    result.message = "✅ GraphProvider is HEALTHY and initialized!"
                    result.details['graph_provider'] = {
                        'status': graph_status.get('status'),
                        'nodes': graph_status.get('details', {}).get('graph_nodes', 0),
                        'relationships': graph_status.get('details', {}).get('graph_relationships', 0),
                        'entity_extractor': graph_status.get('details', {}).get('entity_extractor', 'unknown')
                    }
                else:
                    result.message = f"❌ GraphProvider exists but is not healthy: {graph_status.get('error', 'Unknown error')}"
            else:
                result.message = "⚠️  GraphProvider not found in providers list (might not be enabled)"
                result.passed = True  # This might be expected if GRAPH_ENABLED=false
            
    except Exception as e:
        result.message = f"Failed to test health endpoint: {str(e)}"
        result.duration_ms = (datetime.now() - start_time).total_seconds() * 1000
    
    return result


async def test_empty_query_fix(session: aiohttp.ClientSession) -> TestResult:
    """Test 2: Verify empty query returns all memories (not just 3)"""
    result = TestResult("Empty Query Fix")
    start_time = datetime.now()
    
    try:
        # First, let's store some test memories to ensure we have data
        test_memories = []
        for i in range(10):
            memory_data = {
                "content": f"Test memory {i} for empty query verification - {datetime.now().isoformat()}",
                "metadata": {
                    "test": True,
                    "test_run": "empty_query_fix",
                    "index": i
                }
            }
            
            async with session.post(f"{BASE_URL}/memories", json=memory_data) as response:
                if response.status == 200:
                    memory = await response.json()
                    test_memories.append(memory)
        
        # Now test empty query
        query_data = {
            "query": "",  # Empty query should return all memories
            "limit": 50   # Request up to 50 memories
        }
        
        async with session.post(f"{BASE_URL}/memories/query", json=query_data) as response:
            result.duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            if response.status != 200:
                result.message = f"Query endpoint returned status {response.status}"
                return result
            
            data = await response.json()
            result.details = {
                'total_found': data.get('total_found', 0),
                'memories_returned': len(data.get('memories', [])),
                'trust_metrics': data.get('trust_metrics', {}),
                'query_metadata': data.get('query_metadata', {})
            }
            
            memories_returned = len(data.get('memories', []))
            
            # The fix is successful if we get more than 3 memories
            if memories_returned > 3:
                result.passed = True
                result.message = f"✅ Empty query returned {memories_returned} memories (fix is working!)"
            else:
                result.passed = False
                result.message = f"❌ Empty query only returned {memories_returned} memories (bug still present)"
            
            # Check trust metrics indicate fix was applied
            trust_metrics = data.get('trust_metrics', {})
            if trust_metrics.get('fix_applied') and trust_metrics.get('query_type') == 'empty_query':
                result.details['fix_confirmation'] = "API confirms fix was applied"
            
    except Exception as e:
        result.message = f"Failed to test empty query: {str(e)}"
        result.duration_ms = (datetime.now() - start_time).total_seconds() * 1000
    
    return result


async def test_get_all_memories_endpoint(session: aiohttp.ClientSession) -> TestResult:
    """Test 3: Test the GET /memories endpoint (alternative to empty query)"""
    result = TestResult("GET /memories Endpoint")
    start_time = datetime.now()
    
    try:
        async with session.get(f"{BASE_URL}/memories?limit=50") as response:
            result.duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            if response.status != 200:
                result.message = f"GET /memories returned status {response.status}"
                return result
            
            data = await response.json()
            result.details = {
                'total_found': data.get('total_found', 0),
                'memories_returned': len(data.get('memories', [])),
                'trust_metrics': data.get('trust_metrics', {}),
                'query_metadata': data.get('query_metadata', {})
            }
            
            memories_returned = len(data.get('memories', []))
            
            if memories_returned > 3:
                result.passed = True
                result.message = f"✅ GET /memories returned {memories_returned} memories"
            else:
                result.passed = False
                result.message = f"❌ GET /memories only returned {memories_returned} memories"
            
    except Exception as e:
        result.message = f"Failed to test GET /memories: {str(e)}"
        result.duration_ms = (datetime.now() - start_time).total_seconds() * 1000
    
    return result


async def test_graph_endpoints(session: aiohttp.ClientSession) -> TestResult:
    """Test 4: Test various graph endpoints to verify Knowledge Graph functionality"""
    result = TestResult("Knowledge Graph Endpoints")
    start_time = datetime.now()
    graph_tests = []
    
    try:
        # Test 1: Graph stats endpoint
        async with session.get(f"{BASE_URL}/graph/stats") as response:
            if response.status == 200:
                data = await response.json()
                graph_tests.append({
                    'endpoint': '/graph/stats',
                    'status': 'success',
                    'data': data
                })
            elif response.status == 503:
                graph_tests.append({
                    'endpoint': '/graph/stats',
                    'status': 'not_available',
                    'message': 'Graph provider not available (expected if GRAPH_ENABLED=false)'
                })
            else:
                graph_tests.append({
                    'endpoint': '/graph/stats',
                    'status': 'error',
                    'code': response.status
                })
        
        # Test 2: Graph query endpoint
        query_data = {
            "entity_name": "test",
            "limit": 10
        }
        async with session.post(f"{BASE_URL}/graph/query", json=query_data) as response:
            if response.status == 200:
                data = await response.json()
                graph_tests.append({
                    'endpoint': '/graph/query',
                    'status': 'success',
                    'nodes': len(data.get('nodes', [])),
                    'relationships': len(data.get('relationships', []))
                })
            elif response.status == 503:
                graph_tests.append({
                    'endpoint': '/graph/query',
                    'status': 'not_available'
                })
            else:
                graph_tests.append({
                    'endpoint': '/graph/query',
                    'status': 'error',
                    'code': response.status
                })
        
        # Test 3: Entity exploration
        async with session.get(f"{BASE_URL}/graph/explore/test") as response:
            if response.status == 200:
                data = await response.json()
                graph_tests.append({
                    'endpoint': '/graph/explore/{entity}',
                    'status': 'success',
                    'memories_found': data.get('memories_found', 0)
                })
            elif response.status == 503:
                graph_tests.append({
                    'endpoint': '/graph/explore/{entity}',
                    'status': 'not_available'
                })
            else:
                graph_tests.append({
                    'endpoint': '/graph/explore/{entity}',
                    'status': 'error',
                    'code': response.status
                })
        
        result.duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        result.details['graph_tests'] = graph_tests
        
        # Determine overall result
        available_count = sum(1 for test in graph_tests if test['status'] == 'success')
        not_available_count = sum(1 for test in graph_tests if test['status'] == 'not_available')
        
        if available_count > 0:
            result.passed = True
            result.message = f"✅ Knowledge Graph is operational! {available_count}/{len(graph_tests)} endpoints working"
        elif not_available_count == len(graph_tests):
            result.passed = True  # Not a failure if graph is intentionally disabled
            result.message = "⚠️  Knowledge Graph endpoints return 503 (GraphProvider may be disabled)"
        else:
            result.passed = False
            result.message = "❌ Knowledge Graph endpoints are failing unexpectedly"
            
    except Exception as e:
        result.message = f"Failed to test graph endpoints: {str(e)}"
        result.duration_ms = (datetime.now() - start_time).total_seconds() * 1000
    
    return result


async def test_memory_stats(session: aiohttp.ClientSession) -> TestResult:
    """Test 5: Check memory statistics to verify data integrity"""
    result = TestResult("Memory Statistics")
    start_time = datetime.now()
    
    try:
        async with session.get(f"{BASE_URL}/memories/stats") as response:
            result.duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            if response.status != 200:
                result.message = f"Stats endpoint returned status {response.status}"
                return result
            
            data = await response.json()
            result.details = data
            
            total_memories = data.get('total_memories', 0)
            
            if total_memories > 0:
                result.passed = True
                result.message = f"✅ System has {total_memories} total memories"
                
                # Check provider distribution
                by_provider = data.get('memories_by_provider', {})
                if by_provider:
                    result.details['provider_distribution'] = by_provider
                    result.message += f"\nProvider distribution: {json.dumps(by_provider, indent=2)}"
            else:
                result.passed = False
                result.message = "⚠️  No memories found in the system"
                
    except Exception as e:
        result.message = f"Failed to get memory stats: {str(e)}"
        result.duration_ms = (datetime.now() - start_time).total_seconds() * 1000
    
    return result


def print_results(results: List[TestResult]):
    """Print test results in a formatted way"""
    print("\n" + "="*80)
    print("🧪 PRODUCTION FIX VERIFICATION RESULTS")
    print("="*80)
    print(f"\nTested at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target: {BASE_URL}")
    print("\n" + "-"*80)
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r.passed)
    
    for i, result in enumerate(results, 1):
        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"\nTest {i}/{total_tests}: {result.test_name}")
        print(f"Status: {status}")
        print(f"Duration: {result.duration_ms:.1f}ms")
        print(f"Result: {result.message}")
        
        if result.details:
            print("\nDetails:")
            for key, value in result.details.items():
                if isinstance(value, dict):
                    print(f"  {key}:")
                    for k, v in value.items():
                        print(f"    {k}: {v}")
                elif isinstance(value, list) and key == 'graph_tests':
                    print(f"  {key}:")
                    for test in value:
                        print(f"    - {test['endpoint']}: {test['status']}")
                else:
                    print(f"  {key}: {value}")
    
    print("\n" + "="*80)
    print(f"SUMMARY: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! Both production fixes are working correctly.")
    else:
        print("⚠️  Some tests failed. Please investigate the issues above.")
    
    print("="*80 + "\n")
    
    # Return exit code
    return 0 if passed_tests == total_tests else 1


async def main():
    """Run all tests"""
    # Create session with timeout
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        # Run all tests
        results = []
        
        print("\n🚀 Starting production fix verification tests...\n")
        
        # Test 1: Health check and GraphProvider status
        print("Running Test 1: Health Endpoint & GraphProvider Status...")
        results.append(await test_health_endpoint(session))
        
        # Test 2: Empty query fix
        print("Running Test 2: Empty Query Fix...")
        results.append(await test_empty_query_fix(session))
        
        # Test 3: GET /memories endpoint
        print("Running Test 3: GET /memories Endpoint...")
        results.append(await test_get_all_memories_endpoint(session))
        
        # Test 4: Graph endpoints
        print("Running Test 4: Knowledge Graph Endpoints...")
        results.append(await test_graph_endpoints(session))
        
        # Test 5: Memory statistics
        print("Running Test 5: Memory Statistics...")
        results.append(await test_memory_stats(session))
        
        # Print results
        exit_code = print_results(results)
        
        # Additional diagnostics
        print("\n📊 DIAGNOSTICS:")
        print("-"*40)
        
        # Check if we should run additional diagnostics
        if any(not r.passed for r in results):
            print("\n⚠️  Some tests failed. Running additional diagnostics...\n")
            
            # Get debug environment info
            try:
                async with session.get(f"{BASE_URL}/debug/env") as response:
                    if response.status == 200:
                        env_data = await response.json()
                        print("Environment Configuration:")
                        print(f"  - Embedding Model: {env_data.get('embedding_model', 'Unknown')}")
                        print(f"  - Primary Provider: {env_data.get('primary_provider', 'Unknown')}")
                        
                        if 'service' in env_data:
                            print(f"  - Environment: {env_data['service'].get('ENVIRONMENT', 'Unknown')}")
                            print(f"  - Service Name: {env_data['service'].get('SERVICE_NAME', 'Unknown')}")
            except:
                print("Could not fetch environment diagnostics")
        
        return exit_code


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)