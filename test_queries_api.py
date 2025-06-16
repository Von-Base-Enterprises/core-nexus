#!/usr/bin/env python3
"""
Core Nexus Query API Test Script
Tests query functionality using only REST API calls
"""

import urllib.request
import urllib.parse
import urllib.error
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

# API Configuration
BASE_URL = "https://core-nexus-memory-service.onrender.com"
HEADERS = {"Content-Type": "application/json"}

# Test configuration
VERBOSE = True  # Set to False for less output

def log(message: str, level: str = "INFO"):
    """Simple logging function"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def make_request(method: str, endpoint: str, params: Optional[Dict] = None, json_data: Optional[Dict] = None) -> Dict[str, Any]:
    """Make HTTP request and return parsed response"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        # Add query parameters for GET requests
        if method == "GET" and params:
            query_string = urllib.parse.urlencode(params)
            url = f"{url}?{query_string}"
        
        # Create request
        req = urllib.request.Request(url, headers=HEADERS)
        req.get_method = lambda: method
        
        # Add JSON data for POST requests
        if method == "POST" and json_data:
            data = json.dumps(json_data).encode('utf-8')
            req.add_header('Content-Length', str(len(data)))
            req.data = data
        
        # Log request details
        if VERBOSE:
            log(f"{method} {url} (params: {params}, json: {json_data})")
        
        # Make request
        with urllib.request.urlopen(req, timeout=30) as response:
            status_code = response.getcode()
            response_data = response.read().decode('utf-8')
            
            if VERBOSE:
                log(f"Response: {status_code}")
            
            # Parse JSON response
            try:
                parsed_data = json.loads(response_data) if response_data else {}
            except json.JSONDecodeError:
                parsed_data = {"raw": response_data}
            
            return {
                "success": True,
                "status_code": status_code,
                "data": parsed_data,
                "headers": dict(response.headers)
            }
            
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        return {
            "success": False,
            "status_code": e.code,
            "error": error_body,
            "headers": dict(e.headers)
        }
    except urllib.error.URLError as e:
        return {"success": False, "error": f"Connection error: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def test_health_endpoint():
    """Test the health endpoint"""
    log("Testing health endpoint...")
    result = make_request("GET", "/health")
    
    if result["success"]:
        data = result["data"]
        log(f"Health check passed: {json.dumps(data, indent=2)}")
        return {
            "endpoint": "/health",
            "success": True,
            "memory_count": data.get("total_memories", 0),
            "status": data.get("status", "unknown"),
            "providers": data.get("providers", {}),
            "data": data
        }
    else:
        log(f"Health check failed: {result['error']}", "ERROR")
        return {
            "endpoint": "/health",
            "success": False,
            "error": result["error"]
        }

def test_query_endpoint(query: str = "", limit: int = 10):
    """Test the POST /memories/query endpoint"""
    log(f"Testing POST /memories/query endpoint with query='{query}', limit={limit}...")
    
    json_data = {"limit": limit}
    if query:
        json_data["query"] = query
    
    result = make_request("POST", "/memories/query", json_data=json_data)
    
    if result["success"]:
        data = result["data"]
        memories = data.get("results", [])
        log(f"Query returned {len(memories)} memories")
        if memories and VERBOSE:
            log(f"First memory sample: {json.dumps(memories[0], indent=2)}")
        return {
            "endpoint": "POST /memories/query",
            "query": query,
            "limit": limit,
            "success": True,
            "count": len(memories),
            "total_in_db": data.get("total", 0),
            "memories": memories[:3] if memories else []  # First 3 for sample
        }
    else:
        log(f"Query failed: {result['error']}", "ERROR")
        return {
            "endpoint": "POST /memories/query",
            "query": query,
            "limit": limit,
            "success": False,
            "error": result["error"]
        }

def test_memories_get_endpoint(limit: int = 10):
    """Test the GET /memories endpoint"""
    log(f"Testing GET /memories endpoint with limit={limit}...")
    
    result = make_request("GET", "/memories", params={"limit": limit})
    
    if result["success"]:
        data = result["data"]
        # Handle both list and dict responses
        if isinstance(data, dict) and "results" in data:
            memories = data["results"]
            total = data.get("total", len(memories))
        else:
            memories = []
            total = 0
            
        log(f"GET /memories returned {len(memories)} memories (total in DB: {total})")
        return {
            "endpoint": "GET /memories",
            "limit": limit,
            "success": True,
            "count": len(memories),
            "total_in_db": total,
            "memories": memories[:3] if isinstance(memories, list) else []  # First 3 for sample
        }
    else:
        log(f"GET /memories failed: {result['error']}", "ERROR")
        return {
            "endpoint": "GET /memories",
            "limit": limit,
            "success": False,
            "error": result["error"]
        }

def test_memory_stats():
    """Test the /memories/stats endpoint"""
    log("Testing /memories/stats endpoint...")
    
    result = make_request("GET", "/memories/stats")
    
    if result["success"]:
        stats = result["data"]
        log(f"Memory stats: {json.dumps(stats, indent=2)}")
        return {
            "endpoint": "/memories/stats",
            "success": True,
            "stats": stats
        }
    else:
        log(f"Memory stats failed: {result['error']}", "ERROR")
        return {
            "endpoint": "/memories/stats",
            "success": False,
            "error": result["error"]
        }

def test_text_search(query: str):
    """Test the /memories/search/text endpoint"""
    log(f"Testing /memories/search/text endpoint with query='{query}'...")
    
    result = make_request("GET", "/memories/search/text", params={"query": query, "limit": 10})
    
    if result["success"]:
        data = result["data"]
        memories = data.get("results", []) if isinstance(data, dict) else []
        log(f"Text search returned {len(memories)} results")
        return {
            "endpoint": "/memories/search/text",
            "query": query,
            "success": True,
            "count": len(memories),
            "memories": memories[:3] if memories else []
        }
    else:
        log(f"Text search failed: {result['error']}", "ERROR")
        return {
            "endpoint": "/memories/search/text",
            "query": query,
            "success": False,
            "error": result["error"]
        }

def test_emergency_find_all():
    """Test the emergency find all endpoint"""
    log("Testing /emergency/find-all-memories endpoint...")
    
    result = make_request("GET", "/emergency/find-all-memories")
    
    if result["success"]:
        data = result["data"]
        total = data.get("total_memories", 0)
        memories = data.get("memories", [])
        log(f"Emergency endpoint found {total} total memories, returned {len(memories)}")
        return {
            "endpoint": "/emergency/find-all-memories",
            "success": True,
            "total_count": total,
            "returned_count": len(memories),
            "memories": memories[:3] if memories else []
        }
    else:
        log(f"Emergency endpoint failed: {result['error']}", "ERROR")
        return {
            "endpoint": "/emergency/find-all-memories",
            "success": False,
            "error": result["error"]
        }

def test_providers():
    """Test the /providers endpoint"""
    log("Testing /providers endpoint...")
    
    result = make_request("GET", "/providers")
    
    if result["success"]:
        providers = result["data"]
        log(f"Providers info: {json.dumps(providers, indent=2)}")
        return {
            "endpoint": "/providers",
            "success": True,
            "providers": providers
        }
    else:
        log(f"Providers endpoint failed: {result['error']}", "ERROR")
        return {
            "endpoint": "/providers",
            "success": False,
            "error": result["error"]
        }

def run_comprehensive_tests():
    """Run all tests and generate report"""
    log("Starting comprehensive Core Nexus API tests...", "INFO")
    log(f"Target: {BASE_URL}", "INFO")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "base_url": BASE_URL,
        "tests": []
    }
    
    # 1. Test health endpoint first
    log("\n=== Testing Health Endpoint ===", "INFO")
    health_result = test_health_endpoint()
    results["tests"].append(health_result)
    results["reported_memory_count"] = health_result.get("memory_count", 0) if health_result["success"] else "unknown"
    
    # 2. Test providers endpoint
    log("\n=== Testing Providers ===", "INFO")
    providers_result = test_providers()
    results["tests"].append(providers_result)
    
    # 3. Test memory stats
    log("\n=== Testing Memory Stats ===", "INFO")
    stats_result = test_memory_stats()
    results["tests"].append(stats_result)
    
    # 4. Test emergency find all endpoint
    log("\n=== Testing Emergency Find All ===", "INFO")
    emergency_result = test_emergency_find_all()
    results["tests"].append(emergency_result)
    time.sleep(0.5)
    
    # 5. Test empty queries with different limits using POST endpoint
    log("\n=== Testing Empty Queries (POST) ===", "INFO")
    for limit in [5, 10, 50, 100]:
        result = test_query_endpoint("", limit)
        results["tests"].append(result)
        time.sleep(0.5)  # Rate limiting
    
    # 6. Test search queries with various terms
    log("\n=== Testing Search Queries (POST) ===", "INFO")
    search_terms = [
        "test",
        "memory",
        "data",
        "embedding",
        "vector",
        "claude",
        "ai",
        "knowledge"
    ]
    
    for term in search_terms:
        result = test_query_endpoint(term, 10)
        results["tests"].append(result)
        time.sleep(0.5)  # Rate limiting
    
    # 7. Test GET /memories endpoint
    log("\n=== Testing GET /memories Endpoint ===", "INFO")
    for limit in [10, 50, 100]:
        result = test_memories_get_endpoint(limit)
        results["tests"].append(result)
        time.sleep(0.5)
    
    # 8. Test text search endpoint
    log("\n=== Testing Text Search Endpoint ===", "INFO")
    for term in ["test", "memory", "ai"]:
        result = test_text_search(term)
        results["tests"].append(result)
        time.sleep(0.5)
    
    # Analyze results
    analyze_results(results)
    
    # Save full report
    report_filename = f"api_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    log(f"\nFull report saved to: {report_filename}", "INFO")
    
    return results

def analyze_results(results: Dict):
    """Analyze test results and identify patterns"""
    log("\n=== ANALYSIS SUMMARY ===", "INFO")
    
    # Count successes and failures by endpoint
    endpoint_stats = {}
    total_memories_found = 0
    query_endpoint_memories = 0
    
    for test in results["tests"]:
        endpoint = test.get("endpoint", "unknown")
        if endpoint not in endpoint_stats:
            endpoint_stats[endpoint] = {"success": 0, "failure": 0, "total_memories": 0}
        
        if test.get("success", False):
            endpoint_stats[endpoint]["success"] += 1
            if "count" in test:
                endpoint_stats[endpoint]["total_memories"] += test["count"]
                total_memories_found += test["count"]
                if "POST /memories/query" in endpoint:
                    query_endpoint_memories += test["count"]
            if "total_count" in test:  # For emergency endpoint
                endpoint_stats[endpoint]["total_memories"] = test["total_count"]
        else:
            endpoint_stats[endpoint]["failure"] += 1
    
    # Print endpoint statistics
    log("\nEndpoint Statistics:", "INFO")
    for endpoint, stats in endpoint_stats.items():
        total = stats["success"] + stats["failure"]
        success_rate = (stats["success"] / total * 100) if total > 0 else 0
        log(f"  {endpoint}:", "INFO")
        log(f"    Success rate: {success_rate:.1f}% ({stats['success']}/{total})", "INFO")
        log(f"    Memories found: {stats['total_memories']}", "INFO")
    
    # Identify discrepancies
    log("\nKey Findings:", "INFO")
    
    reported_count = results.get("reported_memory_count", "unknown")
    log(f"  - Health endpoint reports: {reported_count} memories", "INFO")
    log(f"  - Total memories retrieved across all queries: {total_memories_found}", "INFO")
    log(f"  - Memories from /memories/query endpoint: {query_endpoint_memories}", "INFO")
    
    # Check emergency endpoint specifically
    emergency_test = next((t for t in results["tests"] if t.get("endpoint") == "/emergency/find-all-memories"), None)
    if emergency_test and emergency_test.get("success"):
        emergency_total = emergency_test.get("total_count", 0)
        log(f"  - Emergency endpoint reports: {emergency_total} total memories", "INFO")
    
    if reported_count != "unknown" and reported_count > 0 and total_memories_found == 0:
        log(f"  - CRITICAL: Health reports {reported_count} memories but queries return 0!", "ERROR")
    
    # Check for pattern of failures
    query_results = [t for t in results["tests"] if "memories/query" in t.get("endpoint", "")]
    empty_query_results = [t for t in query_results if t.get("query", "") == ""]
    search_query_results = [t for t in query_results if t.get("query", "") != ""]
    
    empty_success = sum(1 for t in empty_query_results if t.get("success", False) and t.get("count", 0) > 0)
    search_success = sum(1 for t in search_query_results if t.get("success", False) and t.get("count", 0) > 0)
    
    log(f"  - Empty queries returning data: {empty_success}/{len(empty_query_results)}", "INFO")
    log(f"  - Search queries returning data: {search_success}/{len(search_query_results)}", "INFO")
    
    # Potential root causes
    log("\nPotential Root Causes:", "INFO")
    
    if reported_count != "unknown" and reported_count > 0 and query_endpoint_memories == 0:
        log("  1. Query processing layer is broken - data exists but can't be retrieved", "ERROR")
        log("  2. Vector similarity search is failing (all similarities might be 0)", "ERROR")
        log("  3. Database connection for queries different from health check", "ERROR")
        log("  4. Query filtering logic is incorrectly filtering out all results", "ERROR")
        log("  5. Embedding generation for queries is failing silently", "ERROR")
        log("  6. The unified store's query method has a bug", "ERROR")
    
    # Check if any endpoint works
    working_endpoints = [ep for ep, stats in endpoint_stats.items() 
                        if stats["total_memories"] > 0]
    
    if working_endpoints:
        log(f"\nWorking endpoints: {', '.join(working_endpoints)}", "INFO")
    else:
        log("\nNo endpoints are returning memory data!", "ERROR")
    
    # Recommendations
    log("\nRecommendations:", "INFO")
    log("  1. Check server logs for query processing errors", "INFO")
    log("  2. Verify embedding generation is working", "INFO")
    log("  3. Test direct database queries to confirm data exists", "INFO")
    log("  4. Check if vector similarity calculations are working", "INFO")
    log("  5. Review recent deployments for breaking changes", "INFO")
    log("  6. Test with known memory IDs to isolate the issue", "INFO")

if __name__ == "__main__":
    try:
        results = run_comprehensive_tests()
        log("\nTests completed successfully!", "INFO")
    except KeyboardInterrupt:
        log("\nTests interrupted by user", "WARNING")
    except Exception as e:
        log(f"\nUnexpected error: {e}", "ERROR")
        import traceback
        traceback.print_exc()