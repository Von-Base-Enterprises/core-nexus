#!/usr/bin/env python3
"""
Production Health Check for Core Nexus Memory Service
Tests all critical endpoints and functionality
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    endpoint: str
    status: HealthStatus
    response_time_ms: float
    message: str
    details: Optional[Dict] = None
    error: Optional[str] = None


class ProductionHealthChecker:
    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = base_url or os.getenv("MEMORY_SERVICE_URL", "https://core-nexus-memory-service.onrender.com")
        self.api_key = api_key or os.getenv("MEMORY_SERVICE_API_KEY", "")
        self.headers = {"X-API-Key": self.api_key} if self.api_key else {}
        self.test_memory_id = None
        self.results: List[HealthCheckResult] = []
        
    def _make_request(self, method: str, endpoint: str, **kwargs) -> tuple[requests.Response, float]:
        """Make HTTP request and return response with timing"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            response = requests.request(
                method, 
                url, 
                headers=self.headers,
                timeout=30,
                **kwargs
            )
            elapsed_ms = (time.time() - start_time) * 1000
            return response, elapsed_ms
        except requests.exceptions.RequestException as e:
            elapsed_ms = (time.time() - start_time) * 1000
            raise Exception(f"Request failed: {str(e)}") from e
    
    def check_health_endpoint(self) -> HealthCheckResult:
        """Check the /health endpoint"""
        try:
            response, elapsed_ms = self._make_request("GET", "/health")
            
            if response.status_code == 200:
                data = response.json()
                status = HealthStatus.HEALTHY if data.get("status") == "healthy" else HealthStatus.DEGRADED
                
                return HealthCheckResult(
                    endpoint="/health",
                    status=status,
                    response_time_ms=elapsed_ms,
                    message=f"Health check returned status: {data.get('status')}",
                    details=data
                )
            else:
                return HealthCheckResult(
                    endpoint="/health",
                    status=HealthStatus.CRITICAL,
                    response_time_ms=elapsed_ms,
                    message=f"Health check failed with status {response.status_code}",
                    error=response.text
                )
        except Exception as e:
            return HealthCheckResult(
                endpoint="/health",
                status=HealthStatus.CRITICAL,
                response_time_ms=0,
                message="Health check endpoint unreachable",
                error=str(e)
            )
    
    def check_memory_creation(self) -> HealthCheckResult:
        """Test memory creation"""
        try:
            test_memory = {
                "content": f"Health check test memory created at {datetime.utcnow().isoformat()}",
                "metadata": {
                    "type": "health_check",
                    "timestamp": datetime.utcnow().isoformat(),
                    "test_id": f"health_check_{int(time.time())}"
                }
            }
            
            response, elapsed_ms = self._make_request("POST", "/memories", json=test_memory)
            
            if response.status_code == 201:
                data = response.json()
                self.test_memory_id = data.get("id")
                
                return HealthCheckResult(
                    endpoint="POST /memories",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=elapsed_ms,
                    message=f"Successfully created test memory with ID: {self.test_memory_id}",
                    details={"memory_id": self.test_memory_id}
                )
            else:
                # Handle 200 status code (should be 201, but API returns 200)
                if response.status_code == 200:
                    data = response.json()
                    self.test_memory_id = data.get("id")
                    
                    return HealthCheckResult(
                        endpoint="POST /memories",
                        status=HealthStatus.HEALTHY,
                        response_time_ms=elapsed_ms,
                        message=f"Successfully created test memory with ID: {self.test_memory_id}",
                        details={"memory_id": self.test_memory_id}
                    )
                else:
                    return HealthCheckResult(
                        endpoint="POST /memories",
                        status=HealthStatus.CRITICAL,
                        response_time_ms=elapsed_ms,
                        message=f"Memory creation failed with status {response.status_code}",
                        error=response.text
                    )
        except Exception as e:
            return HealthCheckResult(
                endpoint="POST /memories",
                status=HealthStatus.CRITICAL,
                response_time_ms=0,
                message="Memory creation endpoint failed",
                error=str(e)
            )
    
    def check_empty_query(self) -> HealthCheckResult:
        """Test empty query (should return all memories)"""
        try:
            # Test with POST to /memories/query with empty query
            query_data = {
                "query": "",
                "limit": 100,
                "min_similarity": 0.0
            }
            response, elapsed_ms = self._make_request("POST", "/memories/query", json=query_data)
            
            if response.status_code == 200:
                data = response.json()
                memories = data.get("memories", [])
                
                return HealthCheckResult(
                    endpoint="POST /memories/query (empty)",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=elapsed_ms,
                    message=f"Empty query returned {len(memories)} memories",
                    details={"memory_count": len(memories), "total": data.get("total_found", 0)}
                )
            else:
                return HealthCheckResult(
                    endpoint="POST /memories/query (empty)",
                    status=HealthStatus.CRITICAL,
                    response_time_ms=elapsed_ms,
                    message=f"Empty query failed with status {response.status_code}",
                    error=response.text
                )
        except Exception as e:
            return HealthCheckResult(
                endpoint="POST /memories/query (empty)",
                status=HealthStatus.CRITICAL,
                response_time_ms=0,
                message="Empty query test failed",
                error=str(e)
            )
    
    def check_search_query(self) -> HealthCheckResult:
        """Test search with actual query"""
        try:
            # Search for the test memory we created
            search_query = "health check test memory"
            query_data = {
                "query": search_query,
                "limit": 10,
                "min_similarity": 0.3
            }
            response, elapsed_ms = self._make_request("POST", "/memories/query", json=query_data)
            
            if response.status_code == 200:
                data = response.json()
                memories = data.get("memories", [])
                
                # Check if we found our test memory
                found_test_memory = any(
                    m.get("id") == self.test_memory_id 
                    for m in memories
                ) if self.test_memory_id else False
                
                status = HealthStatus.HEALTHY if found_test_memory or len(memories) > 0 else HealthStatus.DEGRADED
                
                return HealthCheckResult(
                    endpoint=f"POST /memories/query",
                    status=status,
                    response_time_ms=elapsed_ms,
                    message=f"Search returned {len(memories)} memories",
                    details={
                        "memory_count": len(memories),
                        "found_test_memory": found_test_memory,
                        "query": search_query
                    }
                )
            else:
                return HealthCheckResult(
                    endpoint=f"POST /memories/query",
                    status=HealthStatus.CRITICAL,
                    response_time_ms=elapsed_ms,
                    message=f"Search query failed with status {response.status_code}",
                    error=response.text
                )
        except Exception as e:
            return HealthCheckResult(
                endpoint="POST /memories/query",
                status=HealthStatus.CRITICAL,
                response_time_ms=0,
                message="Search query test failed",
                error=str(e)
            )
    
    def check_memory_retrieval(self) -> HealthCheckResult:
        """Test retrieving a specific memory"""
        if not self.test_memory_id:
            return HealthCheckResult(
                endpoint="GET /memories/{id}",
                status=HealthStatus.UNKNOWN,
                response_time_ms=0,
                message="Skipped: No test memory ID available"
            )
        
        try:
            response, elapsed_ms = self._make_request("GET", f"/memories/{self.test_memory_id}")
            
            if response.status_code == 200:
                data = response.json()
                
                return HealthCheckResult(
                    endpoint=f"GET /memories/{self.test_memory_id}",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=elapsed_ms,
                    message="Successfully retrieved test memory",
                    details={"memory_id": self.test_memory_id}
                )
            elif response.status_code == 404:
                return HealthCheckResult(
                    endpoint=f"GET /memories/{self.test_memory_id}",
                    status=HealthStatus.DEGRADED,
                    response_time_ms=elapsed_ms,
                    message="Test memory not found (may have been cleaned up)",
                    error=response.text
                )
            else:
                return HealthCheckResult(
                    endpoint=f"GET /memories/{self.test_memory_id}",
                    status=HealthStatus.CRITICAL,
                    response_time_ms=elapsed_ms,
                    message=f"Memory retrieval failed with status {response.status_code}",
                    error=response.text
                )
        except Exception as e:
            return HealthCheckResult(
                endpoint="GET /memories/{id}",
                status=HealthStatus.CRITICAL,
                response_time_ms=0,
                message="Memory retrieval test failed",
                error=str(e)
            )
    
    def check_stats_endpoint(self) -> HealthCheckResult:
        """Check the /memories/stats endpoint"""
        try:
            response, elapsed_ms = self._make_request("GET", "/memories/stats")
            
            if response.status_code == 200:
                data = response.json()
                
                return HealthCheckResult(
                    endpoint="/memories/stats",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=elapsed_ms,
                    message="Stats endpoint working",
                    details=data
                )
            else:
                return HealthCheckResult(
                    endpoint="/memories/stats",
                    status=HealthStatus.DEGRADED,
                    response_time_ms=elapsed_ms,
                    message=f"Stats endpoint returned status {response.status_code}",
                    error=response.text
                )
        except Exception as e:
            return HealthCheckResult(
                endpoint="/memories/stats",
                status=HealthStatus.DEGRADED,
                response_time_ms=0,
                message="Stats endpoint failed",
                error=str(e)
            )
    
    def check_providers_status(self) -> HealthCheckResult:
        """Check providers status"""
        try:
            response, elapsed_ms = self._make_request("GET", "/providers")
            
            if response.status_code == 200:
                data = response.json()
                providers = data.get("providers", [])
                
                # Check if at least one provider is enabled
                enabled_providers = [
                    p['name'] for p in providers 
                    if p.get("enabled", False)
                ]
                
                if enabled_providers:
                    status = HealthStatus.HEALTHY
                    message = f"{len(enabled_providers)} providers enabled: {', '.join(enabled_providers)}"
                else:
                    status = HealthStatus.CRITICAL
                    message = "No providers enabled!"
                
                return HealthCheckResult(
                    endpoint="/providers",
                    status=status,
                    response_time_ms=elapsed_ms,
                    message=message,
                    details=data
                )
            else:
                return HealthCheckResult(
                    endpoint="/providers",
                    status=HealthStatus.DEGRADED,
                    response_time_ms=elapsed_ms,
                    message=f"Providers endpoint returned {response.status_code}",
                    error=response.text
                )
        except Exception as e:
            return HealthCheckResult(
                endpoint="/providers",
                status=HealthStatus.DEGRADED,
                response_time_ms=0,
                message="Providers check failed",
                error=str(e)
            )
    
    def cleanup_test_memory(self) -> HealthCheckResult:
        """Clean up the test memory"""
        if not self.test_memory_id:
            return HealthCheckResult(
                endpoint="DELETE /memories/{id}",
                status=HealthStatus.UNKNOWN,
                response_time_ms=0,
                message="Skipped: No test memory to clean up"
            )
        
        try:
            response, elapsed_ms = self._make_request("DELETE", f"/memories/{self.test_memory_id}")
            
            if response.status_code in [200, 204]:
                return HealthCheckResult(
                    endpoint=f"DELETE /memories/{self.test_memory_id}",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=elapsed_ms,
                    message="Test memory cleaned up successfully"
                )
            else:
                return HealthCheckResult(
                    endpoint=f"DELETE /memories/{self.test_memory_id}",
                    status=HealthStatus.DEGRADED,
                    response_time_ms=elapsed_ms,
                    message=f"Cleanup returned status {response.status_code}",
                    error=response.text
                )
        except Exception as e:
            return HealthCheckResult(
                endpoint="DELETE /memories/{id}",
                status=HealthStatus.DEGRADED,
                response_time_ms=0,
                message="Cleanup failed",
                error=str(e)
            )
    
    def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        print(f"\n🏥 Production Health Check for Core Nexus Memory Service")
        print(f"📍 Target: {self.base_url}")
        print(f"🕒 Started at: {datetime.utcnow().isoformat()}")
        print("=" * 80)
        
        # Run checks in order
        checks = [
            ("Basic Health", self.check_health_endpoint),
            ("Memory Creation", self.check_memory_creation),
            ("Empty Query", self.check_empty_query),
            ("Search Query", self.check_search_query),
            ("Memory Retrieval", self.check_memory_retrieval),
            ("Stats Endpoint", self.check_stats_endpoint),
            ("Providers Status", self.check_providers_status),
            ("Cleanup", self.cleanup_test_memory),
        ]
        
        for check_name, check_func in checks:
            print(f"\n🔍 Running: {check_name}")
            result = check_func()
            self.results.append(result)
            
            # Print result
            status_emoji = {
                HealthStatus.HEALTHY: "✅",
                HealthStatus.DEGRADED: "⚠️",
                HealthStatus.CRITICAL: "❌",
                HealthStatus.UNKNOWN: "❓"
            }
            
            print(f"   {status_emoji[result.status]} {result.status.value.upper()}: {result.message}")
            print(f"   ⏱️  Response time: {result.response_time_ms:.2f}ms")
            
            if result.details:
                print(f"   📊 Details: {json.dumps(result.details, indent=6)}")
            
            if result.error:
                print(f"   ❗ Error: {result.error}")
        
        # Generate summary
        summary = self._generate_summary()
        
        print("\n" + "=" * 80)
        print("📊 SUMMARY")
        print("=" * 80)
        print(f"Overall Status: {summary['overall_status']}")
        print(f"Total Checks: {summary['total_checks']}")
        print(f"Healthy: {summary['healthy_count']} | Degraded: {summary['degraded_count']} | Critical: {summary['critical_count']}")
        print(f"Average Response Time: {summary['avg_response_time']:.2f}ms")
        
        if summary['critical_issues']:
            print(f"\n🚨 CRITICAL ISSUES:")
            for issue in summary['critical_issues']:
                print(f"   - {issue}")
        
        if summary['warnings']:
            print(f"\n⚠️  WARNINGS:")
            for warning in summary['warnings']:
                print(f"   - {warning}")
        
        # Save detailed report
        report_filename = f"health_check_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump({
                "timestamp": datetime.utcnow().isoformat(),
                "base_url": self.base_url,
                "summary": summary,
                "results": [asdict(r) for r in self.results]
            }, f, indent=2, default=str)
        
        print(f"\n💾 Detailed report saved to: {report_filename}")
        
        return summary
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate summary of health check results"""
        healthy_count = sum(1 for r in self.results if r.status == HealthStatus.HEALTHY)
        degraded_count = sum(1 for r in self.results if r.status == HealthStatus.DEGRADED)
        critical_count = sum(1 for r in self.results if r.status == HealthStatus.CRITICAL)
        unknown_count = sum(1 for r in self.results if r.status == HealthStatus.UNKNOWN)
        
        # Calculate average response time (excluding unknown/failed)
        response_times = [r.response_time_ms for r in self.results if r.response_time_ms > 0]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Determine overall status
        if critical_count > 0:
            overall_status = "❌ CRITICAL"
        elif degraded_count > 0:
            overall_status = "⚠️  DEGRADED"
        elif healthy_count == len(self.results) - unknown_count:
            overall_status = "✅ HEALTHY"
        else:
            overall_status = "❓ UNKNOWN"
        
        # Collect critical issues and warnings
        critical_issues = [
            f"{r.endpoint}: {r.message}" 
            for r in self.results 
            if r.status == HealthStatus.CRITICAL
        ]
        
        warnings = [
            f"{r.endpoint}: {r.message}" 
            for r in self.results 
            if r.status == HealthStatus.DEGRADED
        ]
        
        return {
            "overall_status": overall_status,
            "total_checks": len(self.results),
            "healthy_count": healthy_count,
            "degraded_count": degraded_count,
            "critical_count": critical_count,
            "unknown_count": unknown_count,
            "avg_response_time": avg_response_time,
            "critical_issues": critical_issues,
            "warnings": warnings
        }


def main():
    """Main entry point"""
    # Check for command line arguments
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = None
    
    # Run health check
    checker = ProductionHealthChecker(base_url=base_url)
    summary = checker.run_all_checks()
    
    # Exit with appropriate code
    if "CRITICAL" in summary["overall_status"]:
        sys.exit(2)
    elif "DEGRADED" in summary["overall_status"]:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()