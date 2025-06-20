#!/usr/bin/env python3
"""
Staging Environment Test Suite - JARVIS-Scale
Tests both staging and production environments to ensure parity
"""

import asyncio
import httpx
import json
import time
from datetime import datetime
from typing import Dict, List

# Environment URLs (will be updated after staging deployment)
ENVIRONMENTS = {
    "production": "https://core-nexus-memory-service.onrender.com",
    "staging": "https://core-nexus-memory-service-staging.onrender.com"  # Future URL
}

class EnvironmentTester:
    def __init__(self):
        self.results = {}
        
    async def test_environment(self, env_name: str, base_url: str) -> Dict:
        """Test a single environment comprehensively"""
        print(f"\n🧪 Testing {env_name.upper()} Environment")
        print(f"URL: {base_url}")
        print("=" * 60)
        
        env_results = {
            "environment": env_name,
            "base_url": base_url,
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "summary": {}
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            
            # Test 1: Health Check
            health_result = await self._test_health(client, base_url)
            env_results["tests"]["health"] = health_result
            print(f"Health: {'✅' if health_result['passed'] else '❌'} ({health_result['duration']:.3f}s)")
            
            # Test 2: Memory Creation
            create_result = await self._test_memory_creation(client, base_url, env_name)
            env_results["tests"]["memory_creation"] = create_result
            print(f"Create: {'✅' if create_result['passed'] else '❌'} ({create_result['duration']:.3f}s)")
            
            # Test 3: Memory Query
            query_result = await self._test_memory_query(client, base_url)
            env_results["tests"]["memory_query"] = query_result
            print(f"Query: {'✅' if query_result['passed'] else '❌'} ({query_result['duration']:.3f}s)")
            
            # Test 4: Empty Query
            empty_result = await self._test_empty_query(client, base_url)
            env_results["tests"]["empty_query"] = empty_result
            print(f"Empty Query: {'✅' if empty_result['passed'] else '❌'} ({empty_result['duration']:.3f}s)")
            
            # Test 5: Get All Memories
            get_all_result = await self._test_get_all_memories(client, base_url)
            env_results["tests"]["get_all"] = get_all_result
            print(f"Get All: {'✅' if get_all_result['passed'] else '❌'} ({get_all_result['duration']:.3f}s)")
            
            # Calculate summary
            total_tests = len(env_results["tests"])
            passed_tests = sum(1 for test in env_results["tests"].values() if test["passed"])
            env_results["summary"] = {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "pass_rate": passed_tests / total_tests * 100,
                "overall_status": "PASS" if passed_tests == total_tests else "FAIL"
            }
            
        return env_results
    
    async def _test_health(self, client: httpx.AsyncClient, base_url: str) -> Dict:
        """Test health endpoint"""
        start = time.time()
        try:
            response = await client.get(f"{base_url}/health")
            duration = time.time() - start
            
            return {
                "passed": response.status_code == 200,
                "status_code": response.status_code,
                "duration": duration,
                "data": response.json() if response.status_code == 200 else None,
                "error": None
            }
        except Exception as e:
            return {
                "passed": False,
                "status_code": None,
                "duration": time.time() - start,
                "data": None,
                "error": str(e)
            }
    
    async def _test_memory_creation(self, client: httpx.AsyncClient, base_url: str, env_name: str) -> Dict:
        """Test memory creation"""
        start = time.time()
        try:
            test_memory = {
                "content": f"Staging test memory from {env_name} - {datetime.now()}",
                "metadata": {
                    "test_type": "staging_validation",
                    "environment": env_name,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            response = await client.post(f"{base_url}/memories", json=test_memory)
            duration = time.time() - start
            
            return {
                "passed": response.status_code in [200, 201],
                "status_code": response.status_code,
                "duration": duration,
                "memory_id": response.json().get("id") if response.status_code in [200, 201] else None,
                "error": response.text if response.status_code not in [200, 201] else None
            }
        except Exception as e:
            return {
                "passed": False,
                "status_code": None,
                "duration": time.time() - start,
                "memory_id": None,
                "error": str(e)
            }
    
    async def _test_memory_query(self, client: httpx.AsyncClient, base_url: str) -> Dict:
        """Test semantic search query"""
        start = time.time()
        try:
            query_data = {
                "query": "staging test memory",
                "limit": 5
            }
            
            response = await client.post(f"{base_url}/memories/query", json=query_data)
            duration = time.time() - start
            
            result_data = response.json() if response.status_code == 200 else None
            
            return {
                "passed": response.status_code == 200,
                "status_code": response.status_code,
                "duration": duration,
                "results_count": len(result_data.get("memories", [])) if result_data else 0,
                "error": response.text if response.status_code != 200 else None
            }
        except Exception as e:
            return {
                "passed": False,
                "status_code": None,
                "duration": time.time() - start,
                "results_count": 0,
                "error": str(e)
            }
    
    async def _test_empty_query(self, client: httpx.AsyncClient, base_url: str) -> Dict:
        """Test empty query handling"""
        start = time.time()
        try:
            query_data = {
                "query": "",
                "limit": 5
            }
            
            response = await client.post(f"{base_url}/memories/query", json=query_data)
            duration = time.time() - start
            
            result_data = response.json() if response.status_code == 200 else None
            
            return {
                "passed": response.status_code == 200,
                "status_code": response.status_code,
                "duration": duration,
                "results_count": len(result_data.get("memories", [])) if result_data else 0,
                "error": response.text if response.status_code != 200 else None
            }
        except Exception as e:
            return {
                "passed": False,
                "status_code": None,
                "duration": time.time() - start,
                "results_count": 0,
                "error": str(e)
            }
    
    async def _test_get_all_memories(self, client: httpx.AsyncClient, base_url: str) -> Dict:
        """Test get all memories endpoint"""
        start = time.time()
        try:
            response = await client.get(f"{base_url}/memories?limit=5")
            duration = time.time() - start
            
            result_data = response.json() if response.status_code == 200 else None
            
            return {
                "passed": response.status_code == 200,
                "status_code": response.status_code,
                "duration": duration,
                "results_count": len(result_data.get("memories", [])) if result_data else 0,
                "error": response.text if response.status_code != 200 else None
            }
        except Exception as e:
            return {
                "passed": False,
                "status_code": None,
                "duration": time.time() - start,
                "results_count": 0,
                "error": str(e)
            }
    
    async def run_comparative_tests(self) -> Dict:
        """Run tests on all environments and compare"""
        print("🚀 JARVIS-Scale Staging Environment Test Suite")
        print(f"Started: {datetime.now()}")
        print("Testing both staging and production environments...")
        
        all_results = {
            "test_suite": "staging_environment_validation",
            "timestamp": datetime.now().isoformat(),
            "environments": {},
            "comparison": {}
        }
        
        # Test each environment
        for env_name, base_url in ENVIRONMENTS.items():
            try:
                env_result = await self.test_environment(env_name, base_url)
                all_results["environments"][env_name] = env_result
            except Exception as e:
                print(f"❌ Failed to test {env_name}: {e}")
                all_results["environments"][env_name] = {
                    "error": str(e),
                    "environment": env_name,
                    "base_url": base_url
                }
        
        # Generate comparison
        if len(all_results["environments"]) >= 2:
            all_results["comparison"] = self._generate_comparison(all_results["environments"])
        
        return all_results
    
    def _generate_comparison(self, env_results: Dict) -> Dict:
        """Generate comparison between environments"""
        comparison = {
            "parity_check": {},
            "performance_comparison": {},
            "recommendations": []
        }
        
        environments = list(env_results.keys())
        if len(environments) >= 2:
            env1, env2 = environments[0], environments[1]
            
            # Check if both have the same pass rate
            pass_rate_1 = env_results[env1].get("summary", {}).get("pass_rate", 0)
            pass_rate_2 = env_results[env2].get("summary", {}).get("pass_rate", 0)
            
            comparison["parity_check"] = {
                "environments_compared": [env1, env2],
                "pass_rate_match": abs(pass_rate_1 - pass_rate_2) < 5,  # Within 5%
                "both_passing": pass_rate_1 >= 80 and pass_rate_2 >= 80
            }
            
            # Performance comparison
            comparison["performance_comparison"] = {
                f"{env1}_avg_response_time": self._calculate_avg_response_time(env_results[env1]),
                f"{env2}_avg_response_time": self._calculate_avg_response_time(env_results[env2])
            }
            
            # Recommendations
            if not comparison["parity_check"]["both_passing"]:
                comparison["recommendations"].append("⚠️  One or both environments failing tests - investigate before deploying")
            if comparison["parity_check"]["pass_rate_match"] and comparison["parity_check"]["both_passing"]:
                comparison["recommendations"].append("✅ Environments have good parity - safe to use staging for testing")
            
        return comparison
    
    def _calculate_avg_response_time(self, env_result: Dict) -> float:
        """Calculate average response time for an environment"""
        tests = env_result.get("tests", {})
        total_time = sum(test.get("duration", 0) for test in tests.values())
        return total_time / len(tests) if tests else 0

async def main():
    """Main test runner"""
    tester = EnvironmentTester()
    
    # Run comparative tests
    results = await tester.run_comparative_tests()
    
    # Print summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    
    for env_name, env_result in results["environments"].items():
        if "summary" in env_result:
            summary = env_result["summary"]
            print(f"{env_name.upper()}: {summary['passed_tests']}/{summary['total_tests']} tests passed ({summary['pass_rate']:.1f}%) - {summary['overall_status']}")
        else:
            print(f"{env_name.upper()}: ERROR - {env_result.get('error', 'Unknown error')}")
    
    # Print comparison
    if "comparison" in results and results["comparison"]:
        comp = results["comparison"]
        print(f"\n🔍 ENVIRONMENT COMPARISON:")
        
        if "parity_check" in comp:
            parity = comp["parity_check"]
            print(f"   Parity Check: {'✅' if parity.get('pass_rate_match') else '❌'}")
            print(f"   Both Passing: {'✅' if parity.get('both_passing') else '❌'}")
        
        if "recommendations" in comp:
            print(f"\n💡 RECOMMENDATIONS:")
            for rec in comp["recommendations"]:
                print(f"   {rec}")
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"staging_test_results_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: {filename}")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())