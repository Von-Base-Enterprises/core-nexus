#!/usr/bin/env python3
"""
Comprehensive stress test for Core Nexus query performance.

Tests:
1. Concurrent query load
2. Various query patterns
3. Edge cases
4. Sustained load
5. Memory usage patterns
"""

import asyncio
import json
import time
import statistics
import random
import string
import aiohttp
from datetime import datetime
from typing import List, Dict, Any
import concurrent.futures
from collections import defaultdict


class QueryStressTester:
    def __init__(self, base_url="https://core-nexus-memory-service.onrender.com", api_key="dev-key-12345"):
        self.base_url = base_url
        self.api_key = api_key
        self.results = defaultdict(list)
        self.errors = defaultdict(int)
        
    async def make_query(self, session: aiohttp.ClientSession, query: str, limit: int = 5) -> Dict[str, Any]:
        """Make a single query request."""
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }
        
        data = {
            "query": query,
            "limit": limit
        }
        
        start_time = time.time()
        try:
            async with session.post(
                f"{self.base_url}/memories/query",
                json=data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                result = await response.json()
                end_time = time.time()
                
                return {
                    "success": True,
                    "query": query,
                    "status_code": response.status,
                    "query_time_ms": result.get("query_time_ms", 0),
                    "total_time_ms": (end_time - start_time) * 1000,
                    "results_count": len(result.get("memories", [])),
                    "total_found": result.get("total_found", 0)
                }
        except asyncio.TimeoutError:
            self.errors["timeout"] += 1
            return {
                "success": False,
                "query": query,
                "error": "timeout",
                "total_time_ms": 30000
            }
        except Exception as e:
            self.errors[str(type(e).__name__)] += 1
            return {
                "success": False,
                "query": query,
                "error": str(e),
                "total_time_ms": (time.time() - start_time) * 1000
            }
    
    def generate_test_queries(self) -> List[str]:
        """Generate various test query patterns."""
        queries = []
        
        # Empty queries
        queries.extend([""] * 5)
        
        # Single words
        single_words = ["test", "memory", "data", "production", "system", "vector", "query", "ai", "embeddings", "search"]
        queries.extend(single_words)
        
        # Common phrases
        phrases = [
            "test memory", "production data", "vector search", "ai system",
            "query performance", "database optimization", "memory storage",
            "embedding similarity", "knowledge graph", "entity extraction"
        ]
        queries.extend(phrases)
        
        # Technical queries
        technical = [
            "pgvector index optimization",
            "cosine similarity threshold",
            "embedding dimension reduction",
            "vector database performance",
            "semantic search algorithm"
        ]
        queries.extend(technical)
        
        # Random strings (edge cases)
        for _ in range(10):
            random_query = ''.join(random.choices(string.ascii_letters + string.digits, k=random.randint(5, 20)))
            queries.append(random_query)
        
        # Special characters
        special = ["test!", "data?", "memory#", "@system", "$price", "test & debug", "query|filter", "test\\escape"]
        queries.extend(special)
        
        # Long queries
        long_query = " ".join(["test"] * 50)
        queries.append(long_query)
        
        # Unicode
        unicode_queries = ["测试", "тест", "テスト", "🚀 rocket", "memory 🧠"]
        queries.extend(unicode_queries)
        
        return queries
    
    async def test_concurrent_load(self, num_concurrent: int = 10, num_requests: int = 100):
        """Test concurrent query load."""
        print(f"\n🔥 Testing concurrent load: {num_concurrent} concurrent, {num_requests} total requests")
        
        queries = self.generate_test_queries()
        tasks = []
        
        async with aiohttp.ClientSession() as session:
            for i in range(num_requests):
                query = random.choice(queries)
                task = self.make_query(session, query)
                tasks.append(task)
                
                # Limit concurrent requests
                if len(tasks) >= num_concurrent:
                    results = await asyncio.gather(*tasks)
                    for result in results:
                        if result["success"]:
                            self.results["concurrent"].append(result)
                    tasks = []
            
            # Process remaining tasks
            if tasks:
                results = await asyncio.gather(*tasks)
                for result in results:
                    if result["success"]:
                        self.results["concurrent"].append(result)
    
    async def test_burst_load(self, burst_size: int = 50):
        """Test burst query load (all at once)."""
        print(f"\n💥 Testing burst load: {burst_size} simultaneous requests")
        
        queries = self.generate_test_queries()
        tasks = []
        
        async with aiohttp.ClientSession() as session:
            for i in range(burst_size):
                query = random.choice(queries)
                task = self.make_query(session, query)
                tasks.append(task)
            
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            burst_duration = (time.time() - start_time) * 1000
            
            successful = 0
            for result in results:
                if isinstance(result, dict) and result.get("success"):
                    self.results["burst"].append(result)
                    successful += 1
            
            print(f"  Burst completed in {burst_duration:.0f}ms")
            print(f"  Success rate: {successful}/{burst_size} ({successful/burst_size*100:.1f}%)")
    
    async def test_sustained_load(self, duration_seconds: int = 30, rate_per_second: int = 5):
        """Test sustained query load over time."""
        print(f"\n⏱️ Testing sustained load: {rate_per_second} queries/sec for {duration_seconds}s")
        
        queries = self.generate_test_queries()
        start_time = time.time()
        request_count = 0
        
        async with aiohttp.ClientSession() as session:
            while time.time() - start_time < duration_seconds:
                batch_start = time.time()
                tasks = []
                
                for _ in range(rate_per_second):
                    query = random.choice(queries)
                    task = self.make_query(session, query)
                    tasks.append(task)
                    request_count += 1
                
                results = await asyncio.gather(*tasks)
                for result in results:
                    if result["success"]:
                        self.results["sustained"].append(result)
                
                # Wait to maintain rate
                batch_duration = time.time() - batch_start
                if batch_duration < 1.0:
                    await asyncio.sleep(1.0 - batch_duration)
                
                # Progress update
                elapsed = int(time.time() - start_time)
                if elapsed % 5 == 0:
                    print(f"  Progress: {elapsed}/{duration_seconds}s, Requests: {request_count}")
    
    async def test_edge_cases(self):
        """Test edge cases and error conditions."""
        print(f"\n🔧 Testing edge cases")
        
        edge_cases = [
            ("Empty query", "", 10),
            ("Max limit", "test", 100),
            ("Zero limit", "test", 0),
            ("Negative limit", "test", -1),
            ("Very long query", "a" * 1000, 5),
            ("Special chars", "'; DROP TABLE--", 5),
            ("Unicode emoji", "🚀🎉🔥💯", 5),
            ("Null-like string", "null", 5),
            ("Boolean string", "true", 5),
            ("Number string", "123456", 5),
        ]
        
        async with aiohttp.ClientSession() as session:
            for name, query, limit in edge_cases:
                print(f"  Testing: {name}")
                result = await self.make_query(session, query, limit)
                self.results["edge_cases"].append({**result, "test_name": name})
    
    def analyze_results(self) -> Dict[str, Any]:
        """Analyze test results and generate report."""
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "total_requests": sum(len(results) for results in self.results.values()),
            "total_errors": sum(self.errors.values()),
            "error_breakdown": dict(self.errors),
            "test_results": {}
        }
        
        for test_name, results in self.results.items():
            if not results:
                continue
                
            query_times = [r["query_time_ms"] for r in results if "query_time_ms" in r]
            total_times = [r["total_time_ms"] for r in results if "total_time_ms" in r]
            
            analysis["test_results"][test_name] = {
                "request_count": len(results),
                "success_count": len([r for r in results if r.get("success")]),
                "avg_query_time_ms": statistics.mean(query_times) if query_times else 0,
                "min_query_time_ms": min(query_times) if query_times else 0,
                "max_query_time_ms": max(query_times) if query_times else 0,
                "p50_query_time_ms": statistics.median(query_times) if query_times else 0,
                "p95_query_time_ms": statistics.quantiles(query_times, n=20)[18] if len(query_times) > 20 else max(query_times) if query_times else 0,
                "avg_total_time_ms": statistics.mean(total_times) if total_times else 0,
            }
        
        return analysis
    
    async def run_comprehensive_test(self):
        """Run all stress tests."""
        print("🚀 Starting Comprehensive Query Stress Test")
        print("=" * 60)
        print(f"Target: {self.base_url}")
        print(f"Start Time: {datetime.now().isoformat()}")
        print("=" * 60)
        
        # Run tests
        await self.test_edge_cases()
        await self.test_burst_load(burst_size=25)
        await self.test_concurrent_load(num_concurrent=5, num_requests=50)
        await self.test_sustained_load(duration_seconds=20, rate_per_second=3)
        
        # Analyze results
        analysis = self.analyze_results()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 STRESS TEST SUMMARY")
        print("=" * 60)
        
        print(f"\nTotal Requests: {analysis['total_requests']}")
        print(f"Total Errors: {analysis['total_errors']}")
        
        if analysis['error_breakdown']:
            print(f"Error Types: {json.dumps(analysis['error_breakdown'], indent=2)}")
        
        print("\nPerformance by Test Type:")
        for test_name, stats in analysis['test_results'].items():
            print(f"\n{test_name.upper()}:")
            print(f"  Requests: {stats['request_count']}")
            print(f"  Avg Query Time: {stats['avg_query_time_ms']:.1f}ms")
            print(f"  Min/Max Query Time: {stats['min_query_time_ms']:.1f}ms / {stats['max_query_time_ms']:.1f}ms")
            print(f"  P50/P95 Query Time: {stats['p50_query_time_ms']:.1f}ms / {stats['p95_query_time_ms']:.1f}ms")
            print(f"  Avg Total Time: {stats['avg_total_time_ms']:.1f}ms")
        
        # Overall assessment
        all_query_times = []
        for results in self.results.values():
            all_query_times.extend([r["query_time_ms"] for r in results if "query_time_ms" in r])
        
        if all_query_times:
            overall_avg = statistics.mean(all_query_times)
            overall_p95 = statistics.quantiles(all_query_times, n=20)[18] if len(all_query_times) > 20 else max(all_query_times)
            
            print("\n" + "=" * 60)
            print("🎯 OVERALL PERFORMANCE")
            print("=" * 60)
            print(f"Average Query Time: {overall_avg:.1f}ms")
            print(f"P95 Query Time: {overall_p95:.1f}ms")
            
            if overall_avg < 100:
                print("✅ EXCELLENT: Meets <100ms target")
            elif overall_avg < 300:
                print("⚠️ GOOD: Acceptable performance")
            else:
                print("❌ NEEDS IMPROVEMENT: Above 300ms average")
            
            # Error rate
            error_rate = analysis['total_errors'] / (analysis['total_requests'] + analysis['total_errors']) * 100
            print(f"\nError Rate: {error_rate:.1f}%")
            if error_rate < 1:
                print("✅ EXCELLENT: Very low error rate")
            elif error_rate < 5:
                print("⚠️ ACCEPTABLE: Some errors occurring")
            else:
                print("❌ HIGH ERROR RATE: Needs investigation")
        
        # Save detailed results
        with open('stress_test_results.json', 'w') as f:
            json.dump(analysis, f, indent=2)
        
        print("\n📄 Detailed results saved to stress_test_results.json")
        
        return analysis


async def main():
    """Run the stress test."""
    tester = QueryStressTester()
    await tester.run_comprehensive_test()


if __name__ == "__main__":
    asyncio.run(main())