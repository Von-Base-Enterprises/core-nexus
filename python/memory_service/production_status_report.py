#!/usr/bin/env python3
"""
Core Nexus Memory Service - Production Status Report
Simple production monitoring using standard library only.
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any


class ProductionStatusMonitor:
    def __init__(self, base_url: str = "https://core-nexus-memory-service.onrender.com"):
        self.base_url = base_url
        self.results = []

    def log(self, message: str, level: str = "INFO"):
        """Log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def make_request(self, endpoint: str, method: str = "GET", data: dict | None = None, timeout: int = 10) -> dict[str, Any]:
        """Make HTTP request using urllib"""
        url = f"{self.base_url}{endpoint}"

        try:
            if data:
                data_bytes = json.dumps(data).encode('utf-8')
                req = urllib.request.Request(url, data=data_bytes, headers={'Content-Type': 'application/json'})
            else:
                req = urllib.request.Request(url)

            if method != "GET":
                req.get_method = lambda: method

            start_time = time.time()
            response = urllib.request.urlopen(req, timeout=timeout)
            duration_ms = (time.time() - start_time) * 1000

            response_data = response.read().decode('utf-8')

            return {
                "success": True,
                "status_code": response.getcode(),
                "data": json.loads(response_data) if response_data else {},
                "duration_ms": duration_ms,
                "error": None
            }

        except urllib.error.HTTPError as e:
            duration_ms = (time.time() - start_time) * 1000
            return {
                "success": False,
                "status_code": e.code,
                "data": {},
                "duration_ms": duration_ms,
                "error": f"HTTP {e.code}: {e.reason}"
            }
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return {
                "success": False,
                "status_code": None,
                "data": {},
                "duration_ms": duration_ms,
                "error": str(e)
            }

    def test_health_check(self) -> dict[str, Any]:
        """Test service health endpoint"""
        self.log("🏥 Testing health check endpoint...")

        result = self.make_request("/health", timeout=15)

        if result["success"]:
            health_data = result["data"]
            providers = health_data.get("providers", {})
            total_memories = health_data.get("total_memories", 0)

            self.log(f"✅ Health check passed in {result['duration_ms']:.2f}ms")
            self.log(f"   Status: {health_data.get('status', 'unknown')}")
            self.log(f"   Total memories: {total_memories}")
            self.log(f"   Providers: {list(providers.keys())}")

            result["health_details"] = {
                "status": health_data.get("status"),
                "total_memories": total_memories,
                "providers": list(providers.keys()),
                "uptime_seconds": health_data.get("uptime_seconds", 0)
            }
        else:
            self.log(f"❌ Health check failed: {result['error']}")

        return result

    def test_memory_storage(self) -> dict[str, Any]:
        """Test memory storage functionality"""
        self.log("💾 Testing memory storage...")

        test_memory = {
            "content": f"Production test memory created at {datetime.now().isoformat()}",
            "metadata": {
                "test": True,
                "agent": "production_monitor",
                "timestamp": datetime.now().isoformat()
            }
        }

        result = self.make_request("/memories", method="POST", data=test_memory, timeout=20)

        if result["success"]:
            memory_data = result["data"]
            memory_id = memory_data.get("id")

            self.log(f"✅ Memory stored successfully in {result['duration_ms']:.2f}ms")
            self.log(f"   Memory ID: {memory_id}")

            result["memory_details"] = {
                "memory_id": memory_id,
                "importance_score": memory_data.get("importance_score", 0)
            }
        else:
            self.log(f"❌ Memory storage failed: {result['error']}")

        return result

    def test_memory_query(self) -> dict[str, Any]:
        """Test memory query functionality"""
        self.log("🔍 Testing memory query...")

        query_data = {
            "query": "production test memory",
            "limit": 5
        }

        result = self.make_request("/memories/query", method="POST", data=query_data, timeout=15)

        if result["success"]:
            query_response = result["data"]
            memories_found = len(query_response.get("memories", []))
            query_time_ms = query_response.get("query_time_ms", 0)

            self.log(f"✅ Memory query completed in {result['duration_ms']:.2f}ms")
            self.log(f"   Memories found: {memories_found}")
            self.log(f"   Service query time: {query_time_ms:.2f}ms")

            result["query_details"] = {
                "memories_found": memories_found,
                "service_query_time_ms": query_time_ms,
                "total_found": query_response.get("total_found", 0)
            }
        else:
            self.log(f"❌ Memory query failed: {result['error']}")

        return result

    def test_api_endpoints(self) -> dict[str, Any]:
        """Test critical API endpoints"""
        self.log("🌐 Testing API endpoints...")

        endpoints = [
            ("/providers", "Provider Information"),
            ("/memories/stats", "Memory Statistics"),
            ("/docs", "API Documentation")
        ]

        endpoint_results = {}
        total_tests = len(endpoints)
        successful_tests = 0

        for endpoint, description in endpoints:
            result = self.make_request(endpoint, timeout=10)

            if result["success"]:
                self.log(f"✅ {description}: {result['status_code']} ({result['duration_ms']:.2f}ms)")
                successful_tests += 1
            else:
                self.log(f"❌ {description}: {result['error']}")

            endpoint_results[endpoint] = {
                "description": description,
                "success": result["success"],
                "status_code": result.get("status_code"),
                "duration_ms": result["duration_ms"]
            }

        return {
            "success": successful_tests >= total_tests * 0.75,  # 75% success rate
            "endpoint_results": endpoint_results,
            "successful_tests": successful_tests,
            "total_tests": total_tests,
            "success_rate": successful_tests / total_tests
        }

    def run_production_status_check(self) -> dict[str, Any]:
        """Run complete production status check"""
        self.log("🚀 Core Nexus Production Status Check")
        self.log("=" * 60)

        start_time = time.time()

        # Test health first
        health_result = self.test_health_check()

        # If service is healthy, run other tests
        if health_result["success"]:
            endpoints_result = self.test_api_endpoints()
            storage_result = self.test_memory_storage()
            query_result = self.test_memory_query()
        else:
            self.log("⚠️ Skipping other tests due to health check failure")
            endpoints_result = {"success": False, "reason": "Health check failed"}
            storage_result = {"success": False, "reason": "Health check failed"}
            query_result = {"success": False, "reason": "Health check failed"}

        total_duration = (time.time() - start_time) * 1000

        # Calculate overall status
        tests = [health_result, endpoints_result, storage_result, query_result]
        successful_tests = sum(1 for test in tests if test.get("success", False))
        total_tests = len(tests)

        overall_success = successful_tests == total_tests

        summary = {
            "timestamp": datetime.now().isoformat(),
            "service_url": self.base_url,
            "total_duration_ms": total_duration,
            "overall_success": overall_success,
            "successful_tests": successful_tests,
            "total_tests": total_tests,
            "success_rate": successful_tests / total_tests,
            "test_results": {
                "health_check": health_result,
                "api_endpoints": endpoints_result,
                "memory_storage": storage_result,
                "memory_query": query_result
            }
        }

        self.log("=" * 60)
        self.log(f"📊 Status Check Complete: {successful_tests}/{total_tests} tests passed")

        if overall_success:
            self.log("🎉 ALL TESTS PASSED - Production service is healthy!")
        else:
            failed_tests = total_tests - successful_tests
            self.log(f"⚠️ {failed_tests} tests failed - Service may need attention")

        return summary

    def save_report(self, summary: dict[str, Any]):
        """Save status report to file"""
        filename = f"production_status_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(filename, 'w') as f:
            json.dump(summary, f, indent=2, default=str)

        self.log(f"📄 Status report saved to: {filename}")

def main():
    """Main entry point"""
    monitor = ProductionStatusMonitor()

    try:
        # Run status check
        results = monitor.run_production_status_check()

        # Save report
        monitor.save_report(results)

        # Print summary for agents
        print("\n" + "="*60)
        print("📋 SUMMARY FOR AGENT TEAM")
        print("="*60)

        if results["overall_success"]:
            print("🟢 SERVICE STATUS: HEALTHY")
            print("✅ All core functions operational")
            print("✅ Ready for agent integration")
        else:
            print("🟡 SERVICE STATUS: NEEDS ATTENTION")
            print(f"⚠️ {results['total_tests'] - results['successful_tests']} tests failed")

            if not results["test_results"]["health_check"]["success"]:
                print("🔴 Health check failed - service may be starting up")
            else:
                print("🟡 Service responding but some features may be impacted")

        print(f"\n🌐 Service URL: {monitor.base_url}")
        print(f"⏱️ Total test time: {results['total_duration_ms']:.0f}ms")
        print(f"📊 Success rate: {results['success_rate']:.1%}")

        # Service readiness for agents
        if results["overall_success"]:
            print("\n🤖 AGENT INTEGRATION READY:")
            print("  • Memory storage: ✅ Operational")
            print("  • Memory retrieval: ✅ Operational")
            print("  • API endpoints: ✅ Available")
            print("  • Documentation: ✅ Accessible")

        return 0 if results["overall_success"] else 1

    except KeyboardInterrupt:
        monitor.log("Status check interrupted by user", "WARNING")
        return 1
    except Exception as e:
        monitor.log(f"Status check failed: {e}", "ERROR")
        return 1

if __name__ == "__main__":
    exit(main())
