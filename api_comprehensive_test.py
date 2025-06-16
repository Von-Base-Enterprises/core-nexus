#!/usr/bin/env python3
"""
Comprehensive API Testing Script for Core Nexus Memory Service
Tests all endpoints and generates a detailed report.
"""

import json
import time
import requests
import asyncio
import aiohttp
from typing import Dict, List, Any
from datetime import datetime
import csv
import io

BASE_URL = "https://core-nexus-memory-service.onrender.com"

class APITester:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.test_results = []
        self.test_memories = []
        
    def log_test(self, test_name: str, success: bool, response_time: float, 
                 details: Dict[str, Any], error: str = None):
        """Log test results"""
        result = {
            "test_name": test_name,
            "success": success,
            "response_time_ms": round(response_time * 1000, 2),
            "timestamp": datetime.now().isoformat(),
            "details": details,
            "error": error
        }
        self.test_results.append(result)
        print(f"✓ {test_name}: {'PASS' if success else 'FAIL'} ({result['response_time_ms']}ms)")
        if error:
            print(f"  Error: {error}")
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/health")
            response_time = time.time() - start_time
            
            success = response.status_code == 200
            details = {
                "status_code": response.status_code,
                "response": response.json() if success else response.text
            }
            
            self.log_test("Health Check", success, response_time, details,
                         None if success else f"HTTP {response.status_code}")
            
        except Exception as e:
            self.log_test("Health Check", False, 0, {}, str(e))
    
    def test_memory_stats(self):
        """Test memory statistics endpoint"""
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/memories/stats")
            response_time = time.time() - start_time
            
            success = response.status_code == 200
            details = {
                "status_code": response.status_code,
                "response": response.json() if success else response.text
            }
            
            self.log_test("Memory Stats", success, response_time, details,
                         None if success else f"HTTP {response.status_code}")
            
        except Exception as e:
            self.log_test("Memory Stats", False, 0, {}, str(e))
    
    def test_create_memory(self):
        """Test creating a new memory"""
        test_memory = {
            "content": "This is a test memory for API testing",
            "context": "API Testing Context",
            "metadata": {"test": True, "timestamp": datetime.now().isoformat()}
        }
        
        try:
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/memories", json=test_memory)
            response_time = time.time() - start_time
            
            success = response.status_code == 200
            details = {
                "status_code": response.status_code,
                "request_payload": test_memory
            }
            
            if success:
                response_data = response.json()
                details["response"] = response_data
                self.test_memories.append(response_data.get("id"))
            else:
                details["response"] = response.text
            
            self.log_test("Create Memory", success, response_time, details,
                         None if success else f"HTTP {response.status_code}")
            
        except Exception as e:
            self.log_test("Create Memory", False, 0, {"request_payload": test_memory}, str(e))
    
    def test_batch_create_memories(self):
        """Test batch memory creation"""
        batch_memories = [
            {
                "content": f"Batch test memory {i}",
                "context": "Batch Testing",
                "metadata": {"batch_test": True, "index": i}
            }
            for i in range(3)
        ]
        
        try:
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/memories/batch", 
                                       json={"memories": batch_memories})
            response_time = time.time() - start_time
            
            success = response.status_code == 200
            details = {
                "status_code": response.status_code,
                "request_payload": {"memory_count": len(batch_memories)}
            }
            
            if success:
                response_data = response.json()
                details["response"] = response_data
                # Store memory IDs if available
                if "memory_ids" in response_data:
                    self.test_memories.extend(response_data["memory_ids"])
            else:
                details["response"] = response.text
            
            self.log_test("Batch Create Memories", success, response_time, details,
                         None if success else f"HTTP {response.status_code}")
            
        except Exception as e:
            self.log_test("Batch Create Memories", False, 0, 
                         {"request_payload": {"memory_count": len(batch_memories)}}, str(e))
    
    def test_query_memories(self):
        """Test querying memories"""
        query_tests = [
            {"query": "test memory", "limit": 5},
            {"query": "", "limit": 10},  # Empty query test
            {"query": "API testing context", "limit": 3}
        ]
        
        for i, query_data in enumerate(query_tests):
            try:
                start_time = time.time()
                response = self.session.post(f"{self.base_url}/memories/query", json=query_data)
                response_time = time.time() - start_time
                
                success = response.status_code == 200
                details = {
                    "status_code": response.status_code,
                    "request_payload": query_data
                }
                
                if success:
                    response_data = response.json()
                    details["response"] = {
                        "memory_count": len(response_data.get("memories", [])),
                        "query_time": response_data.get("query_time_ms")
                    }
                else:
                    details["response"] = response.text
                
                self.log_test(f"Query Memories {i+1}", success, response_time, details,
                             None if success else f"HTTP {response.status_code}")
                
            except Exception as e:
                self.log_test(f"Query Memories {i+1}", False, 0, 
                             {"request_payload": query_data}, str(e))
    
    def test_get_all_memories(self):
        """Test getting all memories"""
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/memories?limit=5")
            response_time = time.time() - start_time
            
            success = response.status_code == 200
            details = {
                "status_code": response.status_code,
                "request_params": {"limit": 5}
            }
            
            if success:
                response_data = response.json()
                details["response"] = {
                    "memory_count": len(response_data.get("memories", [])),
                    "total_count": response_data.get("total_count")
                }
            else:
                details["response"] = response.text
            
            self.log_test("Get All Memories", success, response_time, details,
                         None if success else f"HTTP {response.status_code}")
            
        except Exception as e:
            self.log_test("Get All Memories", False, 0, {"request_params": {"limit": 5}}, str(e))
    
    def test_text_search(self):
        """Test text-based search fallback"""
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/memories/search/text?q=test&limit=5")
            response_time = time.time() - start_time
            
            success = response.status_code == 200
            details = {
                "status_code": response.status_code,
                "request_params": {"q": "test", "limit": 5}
            }
            
            if success:
                response_data = response.json()
                details["response"] = {
                    "memory_count": len(response_data.get("memories", [])),
                    "search_time": response_data.get("search_time_ms")
                }
            else:
                details["response"] = response.text
            
            self.log_test("Text Search", success, response_time, details,
                         None if success else f"HTTP {response.status_code}")
            
        except Exception as e:
            self.log_test("Text Search", False, 0, 
                         {"request_params": {"q": "test", "limit": 5}}, str(e))
    
    def test_dedup_check(self):
        """Test deduplication check"""
        test_content = "This is a test for deduplication checking functionality"
        
        try:
            start_time = time.time()
            response = self.session.post(f"{self.base_url}/dedup/check", 
                                       json={"content": test_content})
            response_time = time.time() - start_time
            
            success = response.status_code == 200
            details = {
                "status_code": response.status_code,
                "request_payload": {"content": test_content[:50] + "..."}
            }
            
            if success:
                response_data = response.json()
                details["response"] = response_data
            else:
                details["response"] = response.text
            
            self.log_test("Dedup Check", success, response_time, details,
                         None if success else f"HTTP {response.status_code}")
            
        except Exception as e:
            self.log_test("Dedup Check", False, 0, 
                         {"request_payload": {"content": test_content[:50] + "..."}}, str(e))
    
    def test_dedup_stats(self):
        """Test deduplication statistics"""
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/dedup/stats")
            response_time = time.time() - start_time
            
            success = response.status_code == 200
            details = {
                "status_code": response.status_code
            }
            
            if success:
                response_data = response.json()
                details["response"] = response_data
            else:
                details["response"] = response.text
            
            self.log_test("Dedup Stats", success, response_time, details,
                         None if success else f"HTTP {response.status_code}")
            
        except Exception as e:
            self.log_test("Dedup Stats", False, 0, {}, str(e))
    
    def test_import_export(self):
        """Test import/export functionality"""
        # Test CSV export
        try:
            start_time = time.time()
            export_payload = {
                "format": "csv",
                "limit": 10,
                "filters": {"metadata": {"test": True}}
            }
            response = self.session.post(f"{self.base_url}/api/v1/memories/export", 
                                       json=export_payload)
            response_time = time.time() - start_time
            
            success = response.status_code == 200
            details = {
                "status_code": response.status_code,
                "request_payload": export_payload
            }
            
            if success:
                # Check if it's CSV content
                content_type = response.headers.get('content-type', '')
                if 'csv' in content_type or response.text.startswith('id,'):
                    details["response"] = {
                        "content_type": content_type,
                        "data_preview": response.text[:200] + "..." if len(response.text) > 200 else response.text
                    }
                else:
                    details["response"] = response.json()
            else:
                details["response"] = response.text
            
            self.log_test("Export CSV", success, response_time, details,
                         None if success else f"HTTP {response.status_code}")
            
        except Exception as e:
            self.log_test("Export CSV", False, 0, {"request_payload": export_payload}, str(e))
    
    def test_error_handling(self):
        """Test error handling with invalid requests"""
        error_tests = [
            {
                "name": "Invalid Memory Creation",
                "method": "POST",
                "endpoint": "/memories",
                "payload": {"invalid_field": "test"}
            },
            {
                "name": "Invalid Query",
                "method": "POST", 
                "endpoint": "/memories/query",
                "payload": {"limit": "invalid"}
            },
            {
                "name": "Non-existent Endpoint",
                "method": "GET",
                "endpoint": "/non-existent-endpoint",
                "payload": None
            }
        ]
        
        for test in error_tests:
            try:
                start_time = time.time()
                if test["method"] == "POST":
                    response = self.session.post(f"{self.base_url}{test['endpoint']}", 
                                               json=test["payload"])
                else:
                    response = self.session.get(f"{self.base_url}{test['endpoint']}")
                response_time = time.time() - start_time
                
                # For error handling tests, we expect non-200 status codes
                expected_error = response.status_code >= 400
                details = {
                    "status_code": response.status_code,
                    "request_payload": test["payload"]
                }
                
                try:
                    details["response"] = response.json()
                except:
                    details["response"] = response.text
                
                self.log_test(test["name"], expected_error, response_time, details,
                             None if expected_error else f"Expected error but got HTTP {response.status_code}")
                
            except Exception as e:
                self.log_test(test["name"], False, 0, {"request_payload": test["payload"]}, str(e))
    
    async def test_concurrent_requests(self):
        """Test concurrent request handling"""
        async def make_request(session, url, payload=None):
            start_time = time.time()
            try:
                if payload:
                    async with session.post(url, json=payload) as response:
                        response_time = time.time() - start_time
                        return {
                            "success": response.status == 200,
                            "status": response.status,
                            "response_time": response_time
                        }
                else:
                    async with session.get(url) as response:
                        response_time = time.time() - start_time
                        return {
                            "success": response.status == 200,
                            "status": response.status, 
                            "response_time": response_time
                        }
            except Exception as e:
                return {
                    "success": False,
                    "status": 0,
                    "response_time": time.time() - start_time,
                    "error": str(e)
                }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Create multiple concurrent requests
                tasks = []
                
                # Health checks
                for i in range(5):
                    tasks.append(make_request(session, f"{self.base_url}/health"))
                
                # Memory queries
                for i in range(3):
                    query_payload = {"query": f"concurrent test {i}", "limit": 5}
                    tasks.append(make_request(session, f"{self.base_url}/memories/query", query_payload))
                
                start_time = time.time()
                results = await asyncio.gather(*tasks)
                total_time = time.time() - start_time
                
                success_count = sum(1 for r in results if r["success"])
                avg_response_time = sum(r["response_time"] for r in results) / len(results)
                
                details = {
                    "total_requests": len(tasks),
                    "successful_requests": success_count,
                    "success_rate": f"{(success_count / len(tasks)) * 100:.1f}%",
                    "total_time": round(total_time, 2),
                    "average_response_time": round(avg_response_time * 1000, 2),
                    "results_summary": {
                        "status_codes": [r["status"] for r in results],
                        "errors": [r.get("error") for r in results if not r["success"]]
                    }
                }
                
                self.log_test("Concurrent Requests", success_count > len(tasks) * 0.8, 
                             total_time, details)
                
        except Exception as e:
            self.log_test("Concurrent Requests", False, 0, {}, str(e))
    
    def run_all_tests(self):
        """Run all tests"""
        print("Starting comprehensive API testing...")
        print(f"Target URL: {self.base_url}")
        print("=" * 60)
        
        # Basic endpoint tests
        self.test_health_endpoint()
        self.test_memory_stats()
        
        # Memory operations
        self.test_create_memory()
        self.test_batch_create_memories()
        self.test_get_all_memories()
        
        # Search functionality
        self.test_query_memories()
        self.test_text_search()
        
        # Deduplication
        self.test_dedup_check()
        self.test_dedup_stats()
        
        # Import/Export
        self.test_import_export()
        
        # Error handling
        self.test_error_handling()
        
        # Concurrent requests
        print("\nTesting concurrent requests...")
        asyncio.run(self.test_concurrent_requests())
        
        print("\n" + "=" * 60)
        print("All tests completed!")
        
        return self.generate_report()
    
    def generate_report(self):
        """Generate comprehensive test report"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["success"])
        failed_tests = total_tests - passed_tests
        
        avg_response_time = sum(r["response_time_ms"] for r in self.test_results) / total_tests
        
        report = {
            "test_summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": f"{(passed_tests / total_tests) * 100:.1f}%",
                "average_response_time_ms": round(avg_response_time, 2)
            },
            "test_results": self.test_results,
            "recommendations": self.generate_recommendations(),
            "generated_at": datetime.now().isoformat()
        }
        
        return report
    
    def generate_recommendations(self):
        """Generate recommendations based on test results"""
        recommendations = []
        
        failed_tests = [r for r in self.test_results if not r["success"]]
        slow_tests = [r for r in self.test_results if r["response_time_ms"] > 5000]
        
        if failed_tests:
            recommendations.append({
                "category": "Critical",
                "issue": f"{len(failed_tests)} tests failed",
                "recommendation": "Investigate and fix failing endpoints immediately",
                "failed_tests": [t["test_name"] for t in failed_tests]
            })
        
        if slow_tests:
            recommendations.append({
                "category": "Performance",
                "issue": f"{len(slow_tests)} tests had slow response times (>5s)",
                "recommendation": "Optimize slow endpoints for better user experience",
                "slow_tests": [(t["test_name"], t["response_time_ms"]) for t in slow_tests]
            })
        
        # Check for specific issues
        health_test = next((r for r in self.test_results if r["test_name"] == "Health Check"), None)
        if health_test and health_test["success"]:
            health_data = health_test["details"]["response"]
            if health_data.get("uptime", 0) < 300:  # Less than 5 minutes
                recommendations.append({
                    "category": "Monitoring",
                    "issue": "Low uptime detected",
                    "recommendation": "Monitor for frequent restarts or cold starts"
                })
        
        if not recommendations:
            recommendations.append({
                "category": "Status",
                "issue": "No issues detected",
                "recommendation": "API is performing well. Continue monitoring."
            })
        
        return recommendations

if __name__ == "__main__":
    tester = APITester()
    report = tester.run_all_tests()
    
    # Save report to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"api_test_report_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nTest report saved to: {filename}")
    print(f"\nTest Summary:")
    print(f"- Total Tests: {report['test_summary']['total_tests']}")
    print(f"- Passed: {report['test_summary']['passed']}")
    print(f"- Failed: {report['test_summary']['failed']}")
    print(f"- Success Rate: {report['test_summary']['success_rate']}")
    print(f"- Avg Response Time: {report['test_summary']['average_response_time_ms']}ms")