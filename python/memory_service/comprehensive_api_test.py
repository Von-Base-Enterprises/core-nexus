#!/usr/bin/env python3
"""
Comprehensive test suite for Core Nexus Memory Service
Tests all major functionality including edge cases
"""

import requests
import json
import time
import random
import string
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import uuid
import sys

# Production API URL
BASE_URL = "https://core-nexus-memory-service.onrender.com"

# Test configuration
TEST_TIMEOUT = 30  # seconds
VECTOR_DIM = 1536  # OpenAI embedding dimension

class MemoryServiceTester:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service_url": BASE_URL,
            "tests": {},
            "overall_status": "PENDING",
            "errors": [],
            "warnings": [],
            "performance_metrics": {},
            "recommendations": []
        }
        self.test_memory_ids = []
        
    def log(self, message: str, level: str = "INFO"):
        """Log test progress"""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def make_request(self, method: str, endpoint: str, **kwargs) -> Optional[requests.Response]:
        """Make HTTP request with error handling"""
        url = f"{BASE_URL}{endpoint}"
        kwargs.setdefault('timeout', TEST_TIMEOUT)
        
        try:
            start_time = time.time()
            response = requests.request(method, url, **kwargs)
            elapsed = time.time() - start_time
            
            # Track performance metrics
            if endpoint not in self.results["performance_metrics"]:
                self.results["performance_metrics"][endpoint] = []
            self.results["performance_metrics"][endpoint].append({
                "method": method,
                "status_code": response.status_code,
                "response_time": elapsed
            })
            
            return response
        except requests.exceptions.Timeout:
            self.log(f"Timeout on {method} {endpoint}", "ERROR")
            self.results["errors"].append(f"Timeout on {method} {endpoint}")
            return None
        except requests.exceptions.ConnectionError as e:
            self.log(f"Connection error on {method} {endpoint}: {e}", "ERROR")
            self.results["errors"].append(f"Connection error on {method} {endpoint}: {str(e)}")
            return None
        except Exception as e:
            self.log(f"Unexpected error on {method} {endpoint}: {e}", "ERROR")
            self.results["errors"].append(f"Unexpected error on {method} {endpoint}: {str(e)}")
            return None
    
    def test_api_accessibility(self):
        """Test 1: Check if production API is accessible"""
        self.log("Testing API accessibility...")
        test_name = "api_accessibility"
        
        response = self.make_request("GET", "/")
        if response and response.status_code < 500:
            self.results["tests"][test_name] = {
                "status": "PASSED",
                "message": f"API is accessible (status: {response.status_code})"
            }
            return True
        else:
            self.results["tests"][test_name] = {
                "status": "FAILED",
                "message": "API is not accessible"
            }
            return False
    
    def test_health_endpoint(self):
        """Test 2: Test health endpoint"""
        self.log("Testing health endpoint...")
        test_name = "health_endpoint"
        
        response = self.make_request("GET", "/health")
        if response and response.status_code == 200:
            try:
                data = response.json()
                self.results["tests"][test_name] = {
                    "status": "PASSED",
                    "message": "Health endpoint working",
                    "details": data
                }
                
                # Check database connectivity from health response
                if "database" in data and data["database"].get("status") == "healthy":
                    self.results["tests"]["database_connectivity"] = {
                        "status": "PASSED",
                        "message": "Database is healthy",
                        "details": data["database"]
                    }
                else:
                    self.results["tests"]["database_connectivity"] = {
                        "status": "WARNING",
                        "message": "Database status unclear from health check",
                        "details": data.get("database", {})
                    }
                    
                return True
            except:
                self.results["tests"][test_name] = {
                    "status": "WARNING",
                    "message": "Health endpoint returned non-JSON response"
                }
                return True
        else:
            self.results["tests"][test_name] = {
                "status": "FAILED",
                "message": f"Health endpoint failed (status: {response.status_code if response else 'No response'})"
            }
            return False
    
    def test_memory_storage(self):
        """Test 3: Test memory storage functionality"""
        self.log("Testing memory storage...")
        test_name = "memory_storage"
        test_cases = []
        
        # Test case 1: Basic memory storage
        memory_data = {
            "content": f"Test memory created at {datetime.now(timezone.utc).isoformat()}",
            "metadata": {
                "test": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "test_id": str(uuid.uuid4())
            }
        }
        
        response = self.make_request("POST", "/memories", json=memory_data)
        if response and response.status_code == 201:
            try:
                created_memory = response.json()
                self.test_memory_ids.append(created_memory["id"])
                test_cases.append({
                    "case": "basic_storage",
                    "status": "PASSED",
                    "message": "Basic memory storage successful",
                    "memory_id": created_memory["id"]
                })
            except:
                test_cases.append({
                    "case": "basic_storage",
                    "status": "FAILED",
                    "message": "Failed to parse response"
                })
        else:
            test_cases.append({
                "case": "basic_storage",
                "status": "FAILED",
                "message": f"Storage failed (status: {response.status_code if response else 'No response'})"
            })
        
        # Test case 2: Memory with special characters
        special_memory = {
            "content": "Test with special chars: 🚀 émojis, 中文, \n\nnewlines, and \"quotes\"",
            "metadata": {"test": True, "type": "special_chars"}
        }
        
        response = self.make_request("POST", "/memories", json=special_memory)
        if response and response.status_code == 201:
            memory = response.json()
            self.test_memory_ids.append(memory["id"])
            test_cases.append({
                "case": "special_characters",
                "status": "PASSED",
                "message": "Special character handling successful"
            })
        else:
            test_cases.append({
                "case": "special_characters",
                "status": "FAILED",
                "message": "Failed to store memory with special characters"
            })
        
        # Test case 3: Large memory content
        large_content = "This is a test of large memory content. " * 100
        large_memory = {
            "content": large_content,
            "metadata": {"test": True, "type": "large_content", "size": len(large_content)}
        }
        
        response = self.make_request("POST", "/memories", json=large_memory)
        if response and response.status_code == 201:
            memory = response.json()
            self.test_memory_ids.append(memory["id"])
            test_cases.append({
                "case": "large_content",
                "status": "PASSED",
                "message": f"Large content storage successful ({len(large_content)} chars)"
            })
        else:
            test_cases.append({
                "case": "large_content",
                "status": "FAILED",
                "message": "Failed to store large content"
            })
        
        # Test case 4: Memory without metadata
        minimal_memory = {
            "content": "Minimal test memory without metadata"
        }
        
        response = self.make_request("POST", "/memories", json=minimal_memory)
        if response and response.status_code == 201:
            memory = response.json()
            self.test_memory_ids.append(memory["id"])
            test_cases.append({
                "case": "minimal_memory",
                "status": "PASSED",
                "message": "Memory without metadata stored successfully"
            })
        else:
            test_cases.append({
                "case": "minimal_memory",
                "status": "FAILED",
                "message": "Failed to store memory without metadata"
            })
        
        # Test case 5: Empty content (edge case)
        empty_memory = {
            "content": "",
            "metadata": {"test": True, "type": "empty_content"}
        }
        
        response = self.make_request("POST", "/memories", json=empty_memory)
        if response and response.status_code in [201, 400, 422]:
            if response.status_code == 201:
                memory = response.json()
                self.test_memory_ids.append(memory["id"])
                test_cases.append({
                    "case": "empty_content",
                    "status": "WARNING",
                    "message": "Empty content accepted - may need validation"
                })
            else:
                test_cases.append({
                    "case": "empty_content",
                    "status": "PASSED",
                    "message": "Empty content properly rejected"
                })
        else:
            test_cases.append({
                "case": "empty_content",
                "status": "FAILED",
                "message": "Unexpected response to empty content"
            })
        
        # Determine overall test status
        failed_cases = [tc for tc in test_cases if tc["status"] == "FAILED"]
        if not failed_cases:
            self.results["tests"][test_name] = {
                "status": "PASSED",
                "message": "All storage tests passed",
                "test_cases": test_cases
            }
        else:
            self.results["tests"][test_name] = {
                "status": "FAILED",
                "message": f"{len(failed_cases)} storage tests failed",
                "test_cases": test_cases
            }
    
    def test_memory_retrieval(self):
        """Test 4: Test memory retrieval and query functionality"""
        self.log("Testing memory retrieval...")
        test_name = "memory_retrieval"
        test_cases = []
        
        # Test case 1: Get all memories
        response = self.make_request("GET", "/memories")
        if response and response.status_code == 200:
            try:
                memories = response.json()
                test_cases.append({
                    "case": "get_all_memories",
                    "status": "PASSED",
                    "message": f"Retrieved {len(memories)} memories",
                    "count": len(memories)
                })
            except:
                test_cases.append({
                    "case": "get_all_memories",
                    "status": "FAILED",
                    "message": "Failed to parse memories response"
                })
        else:
            test_cases.append({
                "case": "get_all_memories",
                "status": "FAILED",
                "message": "Failed to retrieve memories"
            })
        
        # Test case 2: Get specific memory (if we have test IDs)
        if self.test_memory_ids:
            memory_id = self.test_memory_ids[0]
            response = self.make_request("GET", f"/memories/{memory_id}")
            if response and response.status_code == 200:
                memory = response.json()
                test_cases.append({
                    "case": "get_specific_memory",
                    "status": "PASSED",
                    "message": "Retrieved specific memory successfully",
                    "memory_id": memory_id
                })
            else:
                test_cases.append({
                    "case": "get_specific_memory",
                    "status": "FAILED",
                    "message": f"Failed to retrieve memory {memory_id}"
                })
        
        # Test case 3: Get non-existent memory
        fake_id = str(uuid.uuid4())
        response = self.make_request("GET", f"/memories/{fake_id}")
        if response and response.status_code == 404:
            test_cases.append({
                "case": "get_nonexistent_memory",
                "status": "PASSED",
                "message": "Properly handles non-existent memory"
            })
        else:
            test_cases.append({
                "case": "get_nonexistent_memory",
                "status": "FAILED",
                "message": "Improper handling of non-existent memory"
            })
        
        # Test case 4: Get memories with limit
        response = self.make_request("GET", "/memories?limit=5")
        if response and response.status_code == 200:
            memories = response.json()
            if len(memories) <= 5:
                test_cases.append({
                    "case": "get_with_limit",
                    "status": "PASSED",
                    "message": f"Limit parameter working (returned {len(memories)} memories)"
                })
            else:
                test_cases.append({
                    "case": "get_with_limit",
                    "status": "FAILED",
                    "message": f"Limit not respected (returned {len(memories)} memories)"
                })
        else:
            test_cases.append({
                "case": "get_with_limit",
                "status": "FAILED",
                "message": "Failed to retrieve memories with limit"
            })
        
        # Determine overall test status
        failed_cases = [tc for tc in test_cases if tc["status"] == "FAILED"]
        if not failed_cases:
            self.results["tests"][test_name] = {
                "status": "PASSED",
                "message": "All retrieval tests passed",
                "test_cases": test_cases
            }
        else:
            self.results["tests"][test_name] = {
                "status": "FAILED",
                "message": f"{len(failed_cases)} retrieval tests failed",
                "test_cases": test_cases
            }
    
    def test_vector_search(self):
        """Test 5: Verify vector search functionality"""
        self.log("Testing vector search...")
        test_name = "vector_search"
        test_cases = []
        
        # First, create a memory with specific content for searching
        search_content = "The quantum computer revolutionized cryptography in 2024"
        search_memory = {
            "content": search_content,
            "metadata": {"test": True, "type": "search_test"}
        }
        
        response = self.make_request("POST", "/memories", json=search_memory)
        if response and response.status_code == 201:
            memory_id = response.json()["id"]
            self.test_memory_ids.append(memory_id)
            
            # Wait a bit for indexing
            time.sleep(2)
            
            # Test case 1: Search with related query
            search_data = {"query": "quantum computing cryptography"}
            response = self.make_request("POST", "/search", json=search_data)
            if response and response.status_code == 200:
                results = response.json()
                found = any(m.get("id") == memory_id for m in results)
                test_cases.append({
                    "case": "semantic_search",
                    "status": "PASSED" if found else "WARNING",
                    "message": f"Semantic search {'found' if found else 'did not find'} target memory",
                    "results_count": len(results)
                })
            else:
                test_cases.append({
                    "case": "semantic_search",
                    "status": "FAILED",
                    "message": "Search request failed"
                })
            
            # Test case 2: Search with exact match
            exact_search = {"query": search_content}
            response = self.make_request("POST", "/search", json=exact_search)
            if response and response.status_code == 200:
                results = response.json()
                test_cases.append({
                    "case": "exact_match_search",
                    "status": "PASSED",
                    "message": f"Exact match search returned {len(results)} results"
                })
            else:
                test_cases.append({
                    "case": "exact_match_search",
                    "status": "FAILED",
                    "message": "Exact match search failed"
                })
            
            # Test case 3: Empty query search
            empty_search = {"query": ""}
            response = self.make_request("POST", "/search", json=empty_search)
            if response and response.status_code == 200:
                results = response.json()
                test_cases.append({
                    "case": "empty_query_search",
                    "status": "PASSED",
                    "message": f"Empty query handled correctly (returned {len(results)} results)"
                })
            else:
                test_cases.append({
                    "case": "empty_query_search",
                    "status": "FAILED",
                    "message": "Empty query search failed"
                })
            
            # Test case 4: Search with limit
            limited_search = {"query": "test", "limit": 3}
            response = self.make_request("POST", "/search", json=limited_search)
            if response and response.status_code == 200:
                results = response.json()
                if len(results) <= 3:
                    test_cases.append({
                        "case": "limited_search",
                        "status": "PASSED",
                        "message": f"Search limit respected (returned {len(results)} results)"
                    })
                else:
                    test_cases.append({
                        "case": "limited_search",
                        "status": "FAILED",
                        "message": f"Search limit not respected (returned {len(results)} results)"
                    })
            else:
                test_cases.append({
                    "case": "limited_search",
                    "status": "FAILED",
                    "message": "Limited search failed"
                })
        else:
            test_cases.append({
                "case": "vector_search_setup",
                "status": "FAILED",
                "message": "Failed to create test memory for search"
            })
        
        # Determine overall test status
        failed_cases = [tc for tc in test_cases if tc["status"] == "FAILED"]
        if not failed_cases:
            self.results["tests"][test_name] = {
                "status": "PASSED",
                "message": "All vector search tests passed",
                "test_cases": test_cases
            }
        else:
            self.results["tests"][test_name] = {
                "status": "FAILED",
                "message": f"{len(failed_cases)} vector search tests failed",
                "test_cases": test_cases
            }
    
    def test_deduplication(self):
        """Test 6: Test deduplication features"""
        self.log("Testing deduplication...")
        test_name = "deduplication"
        test_cases = []
        
        # Create duplicate memories
        duplicate_content = f"Duplicate test memory created at {datetime.now(timezone.utc).isoformat()}"
        
        # Create first memory
        memory1 = {"content": duplicate_content, "metadata": {"test": True, "duplicate": 1}}
        response1 = self.make_request("POST", "/memories", json=memory1)
        
        # Create second memory with same content
        memory2 = {"content": duplicate_content, "metadata": {"test": True, "duplicate": 2}}
        response2 = self.make_request("POST", "/memories", json=memory2)
        
        if response1 and response1.status_code == 201:
            id1 = response1.json()["id"]
            self.test_memory_ids.append(id1)
            
            if response2 and response2.status_code == 201:
                id2 = response2.json()["id"]
                self.test_memory_ids.append(id2)
                
                # Check if deduplication endpoint exists
                response = self.make_request("POST", "/deduplicate")
                if response and response.status_code in [200, 404]:
                    if response.status_code == 200:
                        test_cases.append({
                            "case": "deduplication_endpoint",
                            "status": "PASSED",
                            "message": "Deduplication endpoint available and working"
                        })
                    else:
                        test_cases.append({
                            "case": "deduplication_endpoint",
                            "status": "INFO",
                            "message": "Deduplication endpoint not available"
                        })
                else:
                    test_cases.append({
                        "case": "deduplication_endpoint",
                        "status": "FAILED",
                        "message": "Error accessing deduplication endpoint"
                    })
                
                # Test duplicate detection in search
                search_response = self.make_request("POST", "/search", json={"query": duplicate_content})
                if search_response and search_response.status_code == 200:
                    results = search_response.json()
                    duplicate_ids = [r["id"] for r in results if r["id"] in [id1, id2]]
                    if len(duplicate_ids) == 2:
                        test_cases.append({
                            "case": "duplicate_detection",
                            "status": "WARNING",
                            "message": "Duplicates exist in system (deduplication may be needed)"
                        })
                    else:
                        test_cases.append({
                            "case": "duplicate_detection",
                            "status": "INFO",
                            "message": f"Found {len(duplicate_ids)} copies of duplicate content"
                        })
        else:
            test_cases.append({
                "case": "deduplication_setup",
                "status": "FAILED",
                "message": "Failed to create test memories for deduplication"
            })
        
        self.results["tests"][test_name] = {
            "status": "PASSED",
            "message": "Deduplication tests completed",
            "test_cases": test_cases
        }
    
    def test_opentelemetry(self):
        """Test 7: Check OpenTelemetry status"""
        self.log("Testing OpenTelemetry...")
        test_name = "opentelemetry"
        
        # Check metrics endpoint
        response = self.make_request("GET", "/metrics")
        if response and response.status_code == 200:
            metrics_text = response.text
            if "memory_service" in metrics_text or "http_request" in metrics_text:
                self.results["tests"][test_name] = {
                    "status": "PASSED",
                    "message": "OpenTelemetry metrics available",
                    "sample_metrics": metrics_text[:500] + "..." if len(metrics_text) > 500 else metrics_text
                }
            else:
                self.results["tests"][test_name] = {
                    "status": "WARNING",
                    "message": "Metrics endpoint available but no OpenTelemetry metrics found"
                }
        else:
            self.results["tests"][test_name] = {
                "status": "INFO",
                "message": "Metrics endpoint not available or not exposed"
            }
    
    def test_knowledge_graph(self):
        """Test 8: Test knowledge graph features if enabled"""
        self.log("Testing knowledge graph features...")
        test_name = "knowledge_graph"
        
        # Check if knowledge graph endpoints exist
        kg_endpoints = ["/graph/entities", "/graph/relationships", "/graph/query"]
        kg_available = False
        
        for endpoint in kg_endpoints:
            response = self.make_request("GET", endpoint)
            if response and response.status_code != 404:
                kg_available = True
                break
        
        if kg_available:
            self.results["tests"][test_name] = {
                "status": "INFO",
                "message": "Knowledge graph endpoints detected",
                "note": "Further testing would require GRAPH_ENABLED=true"
            }
        else:
            self.results["tests"][test_name] = {
                "status": "INFO",
                "message": "Knowledge graph features not enabled or not exposed"
            }
    
    def analyze_performance(self):
        """Analyze performance metrics"""
        self.log("Analyzing performance metrics...")
        
        perf_summary = {}
        for endpoint, metrics in self.results["performance_metrics"].items():
            response_times = [m["response_time"] for m in metrics]
            if response_times:
                perf_summary[endpoint] = {
                    "avg_response_time": sum(response_times) / len(response_times),
                    "max_response_time": max(response_times),
                    "min_response_time": min(response_times),
                    "request_count": len(response_times)
                }
        
        self.results["performance_summary"] = perf_summary
        
        # Add performance warnings
        for endpoint, stats in perf_summary.items():
            if stats["avg_response_time"] > 5.0:
                self.results["warnings"].append(
                    f"High average response time for {endpoint}: {stats['avg_response_time']:.2f}s"
                )
            if stats["max_response_time"] > 10.0:
                self.results["warnings"].append(
                    f"Very high max response time for {endpoint}: {stats['max_response_time']:.2f}s"
                )
    
    def cleanup_test_data(self):
        """Clean up test memories"""
        self.log("Cleaning up test data...")
        
        for memory_id in self.test_memory_ids:
            response = self.make_request("DELETE", f"/memories/{memory_id}")
            if response and response.status_code in [200, 204]:
                self.log(f"Deleted test memory {memory_id}")
            else:
                self.log(f"Failed to delete test memory {memory_id}", "WARNING")
    
    def generate_recommendations(self):
        """Generate recommendations based on test results"""
        self.log("Generating recommendations...")
        
        # Check for critical failures
        critical_tests = ["api_accessibility", "health_endpoint", "memory_storage", "vector_search"]
        critical_failures = [
            test for test in critical_tests 
            if self.results["tests"].get(test, {}).get("status") == "FAILED"
        ]
        
        if critical_failures:
            self.results["recommendations"].append({
                "priority": "CRITICAL",
                "message": f"Critical services failing: {', '.join(critical_failures)}. Immediate action required."
            })
        
        # Performance recommendations
        if self.results["performance_summary"]:
            slow_endpoints = [
                ep for ep, stats in self.results["performance_summary"].items()
                if stats["avg_response_time"] > 3.0
            ]
            if slow_endpoints:
                self.results["recommendations"].append({
                    "priority": "HIGH",
                    "message": f"Performance optimization needed for: {', '.join(slow_endpoints)}"
                })
        
        # Database recommendations
        db_status = self.results["tests"].get("database_connectivity", {}).get("status")
        if db_status != "PASSED":
            self.results["recommendations"].append({
                "priority": "HIGH",
                "message": "Database connectivity issues detected. Check pgvector configuration."
            })
        
        # Deduplication recommendations
        dedup_tests = self.results["tests"].get("deduplication", {}).get("test_cases", [])
        if any(tc.get("status") == "WARNING" for tc in dedup_tests):
            self.results["recommendations"].append({
                "priority": "MEDIUM",
                "message": "Duplicate memories detected. Consider running deduplication process."
            })
        
        # OpenTelemetry recommendations
        otel_status = self.results["tests"].get("opentelemetry", {}).get("status")
        if otel_status != "PASSED":
            self.results["recommendations"].append({
                "priority": "LOW",
                "message": "OpenTelemetry metrics not fully configured. Consider enabling for better observability."
            })
    
    def determine_overall_status(self):
        """Determine overall service status"""
        failed_tests = [
            name for name, result in self.results["tests"].items()
            if result.get("status") == "FAILED"
        ]
        
        warning_tests = [
            name for name, result in self.results["tests"].items()
            if result.get("status") == "WARNING"
        ]
        
        if failed_tests:
            self.results["overall_status"] = "DEGRADED" if len(failed_tests) < 3 else "CRITICAL"
        elif warning_tests:
            self.results["overall_status"] = "OPERATIONAL_WITH_WARNINGS"
        else:
            self.results["overall_status"] = "HEALTHY"
        
        self.results["summary"] = {
            "total_tests": len(self.results["tests"]),
            "passed": len([t for t in self.results["tests"].values() if t.get("status") == "PASSED"]),
            "failed": len(failed_tests),
            "warnings": len(warning_tests)
        }
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        self.log("Starting comprehensive API test suite...")
        
        # Update todo list
        self.update_todo("1", "in_progress")
        
        # Run tests
        tests = [
            (self.test_api_accessibility, "1"),
            (self.test_health_endpoint, "1"),
            (self.test_memory_storage, "2"),
            (self.test_memory_retrieval, "3"),
            (self.test_vector_search, "4"),
            (self.test_deduplication, "6"),
            (self.test_opentelemetry, "7"),
            (self.test_knowledge_graph, "8")
        ]
        
        for test_func, todo_id in tests:
            try:
                if todo_id != "1":  # Already marked in progress
                    self.update_todo(todo_id, "in_progress")
                test_func()
                self.update_todo(todo_id, "completed")
            except Exception as e:
                self.log(f"Error in {test_func.__name__}: {e}", "ERROR")
                self.results["errors"].append(f"Test {test_func.__name__} crashed: {str(e)}")
        
        # Analyze results
        self.analyze_performance()
        self.cleanup_test_data()
        self.generate_recommendations()
        self.determine_overall_status()
        
        # Save results
        self.update_todo("9", "in_progress")
        self.save_results()
        self.update_todo("9", "completed")
        
        self.log(f"Test suite completed. Overall status: {self.results['overall_status']}")
    
    def update_todo(self, todo_id: str, status: str):
        """Update todo status (placeholder for actual implementation)"""
        pass
    
    def save_results(self):
        """Save test results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"comprehensive_test_results_{timestamp}.json"
        
        with open(filename, "w") as f:
            json.dump(self.results, f, indent=2)
        
        self.log(f"Results saved to {filename}")
        
        # Also create a markdown report
        self.create_markdown_report(timestamp)
    
    def create_markdown_report(self, timestamp: str):
        """Create a detailed markdown report"""
        report_lines = [
            f"# Core Nexus Memory Service - Comprehensive Test Report",
            f"**Generated**: {self.results['timestamp']}",
            f"**Service URL**: {self.results['service_url']}",
            f"**Overall Status**: **{self.results['overall_status']}**",
            "",
            "## Summary",
            f"- Total Tests: {self.results['summary']['total_tests']}",
            f"- Passed: {self.results['summary']['passed']}",
            f"- Failed: {self.results['summary']['failed']}",
            f"- Warnings: {self.results['summary']['warnings']}",
            "",
            "## Test Results",
            ""
        ]
        
        for test_name, result in self.results["tests"].items():
            status_emoji = {
                "PASSED": "✅",
                "FAILED": "❌",
                "WARNING": "⚠️",
                "INFO": "ℹ️"
            }.get(result.get("status", ""), "❓")
            
            report_lines.append(f"### {test_name.replace('_', ' ').title()} {status_emoji}")
            report_lines.append(f"**Status**: {result.get('status', 'UNKNOWN')}")
            report_lines.append(f"**Message**: {result.get('message', 'No message')}")
            
            if "test_cases" in result:
                report_lines.append("**Test Cases**:")
                for tc in result["test_cases"]:
                    tc_emoji = {
                        "PASSED": "✅",
                        "FAILED": "❌",
                        "WARNING": "⚠️",
                        "INFO": "ℹ️"
                    }.get(tc.get("status", ""), "❓")
                    report_lines.append(f"- {tc['case']}: {tc_emoji} {tc['message']}")
            
            report_lines.append("")
        
        # Performance section
        report_lines.extend([
            "## Performance Metrics",
            ""
        ])
        
        for endpoint, stats in self.results.get("performance_summary", {}).items():
            report_lines.extend([
                f"### {endpoint}",
                f"- Average Response Time: {stats['avg_response_time']:.3f}s",
                f"- Max Response Time: {stats['max_response_time']:.3f}s",
                f"- Min Response Time: {stats['min_response_time']:.3f}s",
                f"- Total Requests: {stats['request_count']}",
                ""
            ])
        
        # Errors and warnings
        if self.results["errors"]:
            report_lines.extend([
                "## Errors",
                ""
            ])
            for error in self.results["errors"]:
                report_lines.append(f"- ❌ {error}")
            report_lines.append("")
        
        if self.results["warnings"]:
            report_lines.extend([
                "## Warnings",
                ""
            ])
            for warning in self.results["warnings"]:
                report_lines.append(f"- ⚠️ {warning}")
            report_lines.append("")
        
        # Recommendations
        if self.results["recommendations"]:
            report_lines.extend([
                "## Recommendations",
                ""
            ])
            
            # Sort by priority
            priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
            sorted_recs = sorted(
                self.results["recommendations"],
                key=lambda x: priority_order.get(x["priority"], 99)
            )
            
            for rec in sorted_recs:
                priority_emoji = {
                    "CRITICAL": "🚨",
                    "HIGH": "⚠️",
                    "MEDIUM": "📋",
                    "LOW": "💡"
                }.get(rec["priority"], "📝")
                
                report_lines.append(f"### {priority_emoji} {rec['priority']} Priority")
                report_lines.append(rec["message"])
                report_lines.append("")
        
        # Write report
        report_filename = f"comprehensive_test_report_{timestamp}.md"
        with open(report_filename, "w") as f:
            f.write("\n".join(report_lines))
        
        self.log(f"Markdown report saved to {report_filename}")
        print(f"\n{'='*60}")
        print("\n".join(report_lines))


if __name__ == "__main__":
    tester = MemoryServiceTester()
    tester.run_all_tests()