#!/usr/bin/env python3
"""
Core Nexus Memory Service - Production Test Suite
Real-time monitoring and performance validation for live production service.
"""

import asyncio
import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

import httpx


@dataclass
class TestResult:
    test_name: str
    success: bool
    duration_ms: float
    details: dict[str, Any]
    timestamp: datetime
    error_message: str | None = None

class ProductionMonitor:
    def __init__(self, base_url: str = "https://core-nexus-memory-service.onrender.com"):
        self.base_url = base_url
        self.test_results: list[TestResult] = []
        self.performance_baseline = {
            "health_check_max_ms": 1000,
            "memory_store_max_ms": 2000,
            "memory_query_max_ms": 500,
            "batch_operation_max_ms": 5000
        }

    def log(self, message: str, level: str = "INFO"):
        """Log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    async def test_service_health(self) -> TestResult:
        """Test basic service health and availability"""
        start_time = time.time()
        test_name = "service_health"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/health")
                duration_ms = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    health_data = response.json()
                    success = health_data.get("status") == "healthy"

                    result = TestResult(
                        test_name=test_name,
                        success=success,
                        duration_ms=duration_ms,
                        details={
                            "status_code": response.status_code,
                            "health_data": health_data,
                            "providers": health_data.get("providers", {}),
                            "total_memories": health_data.get("total_memories", 0)
                        },
                        timestamp=datetime.now()
                    )

                    if success:
                        self.log(f"✅ Health check passed in {duration_ms:.2f}ms")
                    else:
                        self.log("⚠️ Health check returned unhealthy status", "WARNING")

                else:
                    result = TestResult(
                        test_name=test_name,
                        success=False,
                        duration_ms=duration_ms,
                        details={"status_code": response.status_code},
                        timestamp=datetime.now(),
                        error_message=f"HTTP {response.status_code}"
                    )
                    self.log(f"❌ Health check failed: HTTP {response.status_code}", "ERROR")

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result = TestResult(
                test_name=test_name,
                success=False,
                duration_ms=duration_ms,
                details={},
                timestamp=datetime.now(),
                error_message=str(e)
            )
            self.log(f"❌ Health check failed: {e}", "ERROR")

        self.test_results.append(result)
        return result

    async def test_memory_lifecycle(self) -> TestResult:
        """Test complete memory storage and retrieval cycle"""
        start_time = time.time()
        test_name = "memory_lifecycle"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Test memory storage
                test_content = f"Production test memory - {datetime.now().isoformat()}"
                test_metadata = {
                    "test": True,
                    "agent": "production_monitor",
                    "timestamp": datetime.now().isoformat(),
                    "test_type": "lifecycle"
                }

                store_start = time.time()
                store_response = await client.post(
                    f"{self.base_url}/memories",
                    json={
                        "content": test_content,
                        "metadata": test_metadata
                    }
                )
                store_duration = (time.time() - store_start) * 1000

                if store_response.status_code not in [200, 201]:
                    raise Exception(f"Store failed: HTTP {store_response.status_code}")

                memory_data = store_response.json()
                memory_id = memory_data.get("id")

                # Test memory query
                query_start = time.time()
                query_response = await client.post(
                    f"{self.base_url}/memories/query",
                    json={
                        "query": "production test memory",
                        "limit": 5
                    }
                )
                query_duration = (time.time() - query_start) * 1000

                if query_response.status_code != 200:
                    raise Exception(f"Query failed: HTTP {query_response.status_code}")

                query_data = query_response.json()
                memories_found = len(query_data.get("memories", []))

                total_duration = (time.time() - start_time) * 1000

                # Performance validation
                store_ok = store_duration < self.performance_baseline["memory_store_max_ms"]
                query_ok = query_duration < self.performance_baseline["memory_query_max_ms"]
                success = store_ok and query_ok and memories_found > 0

                result = TestResult(
                    test_name=test_name,
                    success=success,
                    duration_ms=total_duration,
                    details={
                        "memory_id": memory_id,
                        "store_duration_ms": store_duration,
                        "query_duration_ms": query_duration,
                        "memories_found": memories_found,
                        "store_within_sla": store_ok,
                        "query_within_sla": query_ok,
                        "total_memories": query_data.get("total_found", 0)
                    },
                    timestamp=datetime.now()
                )

                if success:
                    self.log(f"✅ Memory lifecycle test passed - Store: {store_duration:.2f}ms, Query: {query_duration:.2f}ms")
                else:
                    self.log(f"⚠️ Memory lifecycle test concerns - Store: {store_duration:.2f}ms, Query: {query_duration:.2f}ms", "WARNING")

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result = TestResult(
                test_name=test_name,
                success=False,
                duration_ms=duration_ms,
                details={},
                timestamp=datetime.now(),
                error_message=str(e)
            )
            self.log(f"❌ Memory lifecycle test failed: {e}", "ERROR")

        self.test_results.append(result)
        return result

    async def test_api_endpoints(self) -> TestResult:
        """Test critical API endpoints availability"""
        start_time = time.time()
        test_name = "api_endpoints"

        endpoints = [
            ("/health", "Health Check"),
            ("/providers", "Provider Information"),
            ("/memories/stats", "Memory Statistics"),
            ("/docs", "API Documentation")
        ]

        endpoint_results = {}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                for endpoint, description in endpoints:
                    try:
                        ep_start = time.time()
                        response = await client.get(f"{self.base_url}{endpoint}")
                        ep_duration = (time.time() - ep_start) * 1000

                        endpoint_results[endpoint] = {
                            "status_code": response.status_code,
                            "duration_ms": ep_duration,
                            "success": response.status_code in [200, 201],
                            "description": description
                        }

                        if response.status_code in [200, 201]:
                            self.log(f"✅ {description}: {response.status_code} ({ep_duration:.2f}ms)")
                        else:
                            self.log(f"❌ {description}: {response.status_code}", "ERROR")

                    except Exception as e:
                        endpoint_results[endpoint] = {
                            "success": False,
                            "error": str(e),
                            "description": description
                        }
                        self.log(f"❌ {description}: {e}", "ERROR")

                total_duration = (time.time() - start_time) * 1000
                successful_endpoints = sum(1 for ep in endpoint_results.values() if ep.get("success", False))
                success = successful_endpoints >= len(endpoints) * 0.75  # 75% success rate

                result = TestResult(
                    test_name=test_name,
                    success=success,
                    duration_ms=total_duration,
                    details={
                        "endpoints_tested": len(endpoints),
                        "successful_endpoints": successful_endpoints,
                        "success_rate": successful_endpoints / len(endpoints),
                        "endpoint_results": endpoint_results
                    },
                    timestamp=datetime.now()
                )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result = TestResult(
                test_name=test_name,
                success=False,
                duration_ms=duration_ms,
                details={"endpoint_results": endpoint_results},
                timestamp=datetime.now(),
                error_message=str(e)
            )
            self.log(f"❌ API endpoints test failed: {e}", "ERROR")

        self.test_results.append(result)
        return result

    async def test_performance_under_load(self, concurrent_requests: int = 5) -> TestResult:
        """Test service performance under concurrent load"""
        start_time = time.time()
        test_name = "performance_load"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Create concurrent health check requests
                tasks = []
                for i in range(concurrent_requests):
                    task = client.get(f"{self.base_url}/health")
                    tasks.append(task)

                responses = await asyncio.gather(*tasks, return_exceptions=True)

                total_duration = (time.time() - start_time) * 1000
                successful_responses = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code == 200)

                success = successful_responses >= concurrent_requests * 0.8  # 80% success rate

                result = TestResult(
                    test_name=test_name,
                    success=success,
                    duration_ms=total_duration,
                    details={
                        "concurrent_requests": concurrent_requests,
                        "successful_responses": successful_responses,
                        "success_rate": successful_responses / concurrent_requests,
                        "avg_response_time_ms": total_duration / concurrent_requests
                    },
                    timestamp=datetime.now()
                )

                if success:
                    self.log(f"✅ Load test passed: {successful_responses}/{concurrent_requests} requests succeeded")
                else:
                    self.log(f"⚠️ Load test concerns: {successful_responses}/{concurrent_requests} requests succeeded", "WARNING")

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result = TestResult(
                test_name=test_name,
                success=False,
                duration_ms=duration_ms,
                details={"concurrent_requests": concurrent_requests},
                timestamp=datetime.now(),
                error_message=str(e)
            )
            self.log(f"❌ Load test failed: {e}", "ERROR")

        self.test_results.append(result)
        return result

    async def run_full_test_suite(self) -> dict[str, Any]:
        """Run complete production test suite"""
        self.log("🚀 Starting Core Nexus Production Test Suite")
        self.log("=" * 60)

        suite_start = time.time()

        # Run all tests
        health_result = await self.test_service_health()

        # Only run other tests if service is healthy
        if health_result.success:
            endpoints_result = await self.test_api_endpoints()
            lifecycle_result = await self.test_memory_lifecycle()
            load_result = await self.test_performance_under_load()
        else:
            self.log("⚠️ Skipping additional tests due to health check failure", "WARNING")
            endpoints_result = lifecycle_result = load_result = None

        suite_duration = (time.time() - suite_start) * 1000

        # Calculate overall results
        all_results = [r for r in [health_result, endpoints_result, lifecycle_result, load_result] if r is not None]
        successful_tests = sum(1 for r in all_results if r.success)
        total_tests = len(all_results)

        summary = {
            "timestamp": datetime.now().isoformat(),
            "suite_duration_ms": suite_duration,
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "success_rate": successful_tests / total_tests if total_tests > 0 else 0,
            "overall_success": successful_tests == total_tests,
            "test_results": [asdict(r) for r in all_results],
            "performance_baseline": self.performance_baseline
        }

        self.log("=" * 60)
        self.log(f"📊 Test Suite Complete: {successful_tests}/{total_tests} tests passed")

        if summary["overall_success"]:
            self.log("🎉 ALL TESTS PASSED - Production service is healthy!", "SUCCESS")
        else:
            self.log(f"⚠️ {total_tests - successful_tests} tests failed - Investigation needed", "WARNING")

        return summary

    def save_results(self, summary: dict[str, Any], filename: str = None):
        """Save test results to file"""
        if filename is None:
            filename = f"production_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(filename, 'w') as f:
            json.dump(summary, f, indent=2, default=str)

        self.log(f"📊 Test results saved to: {filename}")

async def main():
    """Main production testing entry point"""
    monitor = ProductionMonitor()

    try:
        # Run full test suite
        results = await monitor.run_full_test_suite()

        # Save results
        monitor.save_results(results)

        # Exit with appropriate code
        sys.exit(0 if results["overall_success"] else 1)

    except KeyboardInterrupt:
        monitor.log("Production testing interrupted by user", "WARNING")
        sys.exit(1)
    except Exception as e:
        monitor.log(f"Production testing failed: {e}", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
