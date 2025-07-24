#!/usr/bin/env python3
"""
Comprehensive GraphRAG Verification Test
Tests all critical flows: ingest, storage, retrieval, and traversal

Author: Tyvonne
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import sys

# Configuration
API_URL = "https://core-nexus-memory-service.onrender.com"
API_KEY = "test-key-67890"

# Test data - Tyvonne's examples
TEST_MEMORIES = [
    {
        "content": "Tyvonne works at Von Base Enterprises and uses React.",
        "metadata": {"test": "graphrag_verification", "memory": "A"},
        "importance_score": 0.9
    },
    {
        "content": "Von Base Enterprises uses Python for its AI platform.",
        "metadata": {"test": "graphrag_verification", "memory": "B"},
        "importance_score": 0.85
    },
    {
        "content": "React is a JavaScript library created by Facebook.",
        "metadata": {"test": "graphrag_verification", "memory": "C"},
        "importance_score": 0.8
    }
]

# Expected entities and relationships
EXPECTED_ENTITIES = ["Tyvonne", "Von Base Enterprises", "React", "Python", "JavaScript", "Facebook"]
EXPECTED_RELATIONSHIPS = [
    ("Tyvonne", "works at", "Von Base Enterprises"),
    ("Tyvonne", "uses", "React"),
    ("Von Base Enterprises", "uses", "Python"),
    ("React", "is", "JavaScript library"),
    ("React", "created by", "Facebook")
]


class GraphRAGTester:
    def __init__(self):
        self.session = None
        self.headers = {"X-API-Key": API_KEY}
        self.results = {
            "tests": [],
            "passed": 0,
            "failed": 0,
            "start_time": None,
            "end_time": None
        }
        self.initial_stats = None
        self.created_memory_ids = []
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        self.results["start_time"] = datetime.now()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        self.results["end_time"] = datetime.now()
    
    def log(self, message: str, level: str = "INFO"):
        """Log with timestamp and level"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prefix = {
            "INFO": "ℹ️ ",
            "SUCCESS": "✅",
            "FAIL": "❌",
            "WARNING": "⚠️ "
        }.get(level, "")
        print(f"[{timestamp}] {prefix} {message}")
    
    async def add_test_result(self, name: str, passed: bool, details: str = "", duration_ms: Optional[float] = None):
        """Record a test result"""
        result = {
            "name": name,
            "passed": passed,
            "details": details,
            "duration_ms": duration_ms
        }
        self.results["tests"].append(result)
        
        if passed:
            self.results["passed"] += 1
            self.log(f"{name}: PASSED {details}", "SUCCESS")
        else:
            self.results["failed"] += 1
            self.log(f"{name}: FAILED - {details}", "FAIL")
    
    async def test_api_health(self) -> bool:
        """Test 1: Basic API health check"""
        self.log("Testing API health...")
        start = time.time()
        
        try:
            async with self.session.get(f"{API_URL}/health", headers=self.headers) as resp:
                duration = (time.time() - start) * 1000
                if resp.status == 200:
                    data = await resp.json()
                    await self.add_test_result(
                        "API Health Check",
                        True,
                        f"(Response time: {duration:.0f}ms)",
                        duration
                    )
                    return True
                else:
                    await self.add_test_result(
                        "API Health Check",
                        False,
                        f"Status code: {resp.status}"
                    )
                    return False
        except Exception as e:
            await self.add_test_result(
                "API Health Check",
                False,
                str(e)
            )
            return False
    
    async def get_initial_stats(self) -> bool:
        """Test 2: Get initial graph statistics"""
        self.log("Getting initial graph statistics...")
        
        try:
            async with self.session.get(f"{API_URL}/graph/stats", headers=self.headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.initial_stats = data.get("statistics", {})
                    await self.add_test_result(
                        "Get Initial Stats",
                        True,
                        f"(Nodes: {self.initial_stats.get('total_nodes', 0)}, "
                        f"Relationships: {self.initial_stats.get('total_relationships', 0)})"
                    )
                    return True
                else:
                    await self.add_test_result(
                        "Get Initial Stats",
                        False,
                        f"Status code: {resp.status}"
                    )
                    return False
        except Exception as e:
            await self.add_test_result(
                "Get Initial Stats",
                False,
                str(e)
            )
            return False
    
    async def create_test_memories(self) -> bool:
        """Test 3: Create controlled test memories"""
        self.log("Creating test memories...")
        all_success = True
        
        for i, memory in enumerate(TEST_MEMORIES):
            try:
                start = time.time()
                async with self.session.post(
                    f"{API_URL}/memories",
                    headers={**self.headers, "Content-Type": "application/json"},
                    json=memory
                ) as resp:
                    duration = (time.time() - start) * 1000
                    if resp.status == 200:
                        data = await resp.json()
                        memory_id = data.get("id")
                        self.created_memory_ids.append(memory_id)
                        await self.add_test_result(
                            f"Create Memory {chr(65+i)}",
                            True,
                            f"ID: {memory_id} ({duration:.0f}ms)",
                            duration
                        )
                    else:
                        await self.add_test_result(
                            f"Create Memory {chr(65+i)}",
                            False,
                            f"Status: {resp.status}"
                        )
                        all_success = False
            except Exception as e:
                await self.add_test_result(
                    f"Create Memory {chr(65+i)}",
                    False,
                    str(e)
                )
                all_success = False
        
        # Wait for graph processing
        if all_success:
            self.log("Waiting 10 seconds for graph processing...")
            await asyncio.sleep(10)
        
        return all_success
    
    async def verify_stats_increased(self) -> bool:
        """Test 4: Verify graph statistics increased"""
        self.log("Verifying graph statistics increased...")
        
        try:
            async with self.session.get(f"{API_URL}/graph/stats", headers=self.headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    new_stats = data.get("statistics", {})
                    
                    nodes_before = self.initial_stats.get("total_nodes", 0)
                    nodes_after = new_stats.get("total_nodes", 0)
                    rels_before = self.initial_stats.get("total_relationships", 0)
                    rels_after = new_stats.get("total_relationships", 0)
                    
                    nodes_increased = nodes_after > nodes_before
                    rels_increased = rels_after > rels_before
                    
                    await self.add_test_result(
                        "Stats Increased",
                        nodes_increased and rels_increased,
                        f"Nodes: {nodes_before}→{nodes_after} (+{nodes_after-nodes_before}), "
                        f"Relationships: {rels_before}→{rels_after} (+{rels_after-rels_before})"
                    )
                    return nodes_increased and rels_increased
                else:
                    await self.add_test_result(
                        "Stats Increased",
                        False,
                        f"Status code: {resp.status}"
                    )
                    return False
        except Exception as e:
            await self.add_test_result(
                "Stats Increased",
                False,
                str(e)
            )
            return False
    
    async def test_entity_exploration(self) -> bool:
        """Test 5: Test entity exploration for key entities"""
        self.log("Testing entity exploration...")
        
        test_entities = ["Tyvonne", "Von Base Enterprises", "React"]
        all_success = True
        
        for entity in test_entities:
            try:
                start = time.time()
                async with self.session.get(
                    f"{API_URL}/graph/explore/{entity}",
                    headers=self.headers
                ) as resp:
                    duration = (time.time() - start) * 1000
                    if resp.status == 200:
                        data = await resp.json()
                        memories_found = data.get("memories_found", 0)
                        
                        # We expect at least 1 memory for each test entity
                        success = memories_found > 0
                        
                        await self.add_test_result(
                            f"Explore '{entity}'",
                            success,
                            f"Found {memories_found} memories ({duration:.0f}ms)",
                            duration
                        )
                        
                        if not success:
                            all_success = False
                            
                        # Log first memory content if found
                        if memories_found > 0 and data.get("memories"):
                            first_memory = data["memories"][0]
                            self.log(f"  → First memory: {first_memory['content'][:80]}...", "INFO")
                    else:
                        await self.add_test_result(
                            f"Explore '{entity}'",
                            False,
                            f"Status: {resp.status}"
                        )
                        all_success = False
            except Exception as e:
                await self.add_test_result(
                    f"Explore '{entity}'",
                    False,
                    str(e)
                )
                all_success = False
        
        return all_success
    
    async def test_graph_queries(self) -> bool:
        """Test 6: Test graph queries with filters"""
        self.log("Testing graph queries with filters...")
        
        test_queries = [
            {"entity_name": "Tyvonne"},
            {"entity_name": "Python"},
            {"entity_type": "organization"}
        ]
        
        all_success = True
        
        for query in test_queries:
            try:
                start = time.time()
                async with self.session.post(
                    f"{API_URL}/graph/query",
                    headers={**self.headers, "Content-Type": "application/json"},
                    json=query
                ) as resp:
                    duration = (time.time() - start) * 1000
                    if resp.status == 200:
                        data = await resp.json()
                        nodes_found = data.get("total_nodes", 0)
                        
                        await self.add_test_result(
                            f"Graph Query {query}",
                            True,
                            f"Found {nodes_found} nodes ({duration:.0f}ms)",
                            duration
                        )
                    else:
                        await self.add_test_result(
                            f"Graph Query {query}",
                            False,
                            f"Status: {resp.status}"
                        )
                        all_success = False
            except Exception as e:
                await self.add_test_result(
                    f"Graph Query {query}",
                    False,
                    str(e)
                )
                all_success = False
        
        return all_success
    
    async def test_security(self) -> bool:
        """Test 7: Security tests (no API key, invalid entity)"""
        self.log("Testing security...")
        
        # Test without API key
        try:
            async with self.session.get(
                f"{API_URL}/graph/stats",
                headers={}  # No API key
            ) as resp:
                success = resp.status == 401
                await self.add_test_result(
                    "No API Key → 401",
                    success,
                    f"Got status {resp.status}"
                )
        except Exception as e:
            await self.add_test_result(
                "No API Key → 401",
                False,
                str(e)
            )
        
        # Test non-existent entity
        try:
            async with self.session.get(
                f"{API_URL}/graph/explore/NonExistentEntity123456",
                headers=self.headers
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    success = data.get("memories_found", 0) == 0
                    await self.add_test_result(
                        "Non-existent Entity",
                        success,
                        "Returns empty result"
                    )
                else:
                    await self.add_test_result(
                        "Non-existent Entity",
                        False,
                        f"Got status {resp.status}"
                    )
        except Exception as e:
            await self.add_test_result(
                "Non-existent Entity",
                False,
                str(e)
            )
        
        return True
    
    async def test_live_stats(self) -> bool:
        """Test 8: Test live stats endpoint"""
        self.log("Testing live stats endpoint...")
        
        try:
            start = time.time()
            async with self.session.get(
                f"{API_URL}/api/knowledge-graph/live-stats",
                headers=self.headers
            ) as resp:
                duration = (time.time() - start) * 1000
                if resp.status == 200:
                    data = await resp.json()
                    
                    has_required_fields = all(
                        field in data for field in 
                        ["entity_count", "relationship_count", "top_entities"]
                    )
                    
                    await self.add_test_result(
                        "Live Stats",
                        has_required_fields,
                        f"Entities: {data.get('entity_count', 0)}, "
                        f"Relationships: {data.get('relationship_count', 0)} ({duration:.0f}ms)",
                        duration
                    )
                    
                    # Log top entities
                    if data.get("top_entities"):
                        self.log("  Top entities:", "INFO")
                        for entity in data["top_entities"][:3]:
                            self.log(f"    - {entity['name']}: {entity['connections']} connections", "INFO")
                    
                    return has_required_fields
                else:
                    await self.add_test_result(
                        "Live Stats",
                        False,
                        f"Status: {resp.status}"
                    )
                    return False
        except Exception as e:
            await self.add_test_result(
                "Live Stats",
                False,
                str(e)
            )
            return False
    
    def generate_report(self):
        """Generate final test report"""
        self.results["end_time"] = datetime.now()
        duration = (self.results["end_time"] - self.results["start_time"]).total_seconds()
        
        print("\n" + "="*80)
        print("📊 GRAPHRAG VERIFICATION TEST REPORT")
        print("="*80)
        print(f"Started: {self.results['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Completed: {self.results['end_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration: {duration:.1f} seconds")
        print(f"\nResults: {self.results['passed']} PASSED, {self.results['failed']} FAILED")
        print("="*80)
        
        # Group results by status
        print("\n✅ PASSED TESTS:")
        for test in self.results["tests"]:
            if test["passed"]:
                print(f"  • {test['name']} {test['details']}")
        
        if self.results["failed"] > 0:
            print("\n❌ FAILED TESTS:")
            for test in self.results["tests"]:
                if not test["passed"]:
                    print(f"  • {test['name']}: {test['details']}")
        
        # Performance summary
        print("\n⚡ PERFORMANCE:")
        timed_tests = [t for t in self.results["tests"] if t.get("duration_ms")]
        if timed_tests:
            avg_time = sum(t["duration_ms"] for t in timed_tests) / len(timed_tests)
            max_time = max(t["duration_ms"] for t in timed_tests)
            print(f"  • Average response time: {avg_time:.0f}ms")
            print(f"  • Max response time: {max_time:.0f}ms")
        
        # Final verdict
        print("\n" + "="*80)
        if self.results["failed"] == 0:
            print("🎉 VERDICT: ALL TESTS PASSED - GraphRAG is fully operational!")
        else:
            print("⚠️  VERDICT: SOME TESTS FAILED - GraphRAG needs attention")
        print("="*80)
        
        # Save report to file
        report_file = f"graphrag_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"\n📄 Detailed report saved to: {report_file}")


async def main():
    """Run the comprehensive GraphRAG test suite"""
    print("🚀 Starting Comprehensive GraphRAG Verification Test")
    print("="*80)
    
    async with GraphRAGTester() as tester:
        # Run all tests in sequence
        tests = [
            tester.test_api_health(),
            tester.get_initial_stats(),
            tester.create_test_memories(),
            tester.verify_stats_increased(),
            tester.test_entity_exploration(),
            tester.test_graph_queries(),
            tester.test_security(),
            tester.test_live_stats()
        ]
        
        # Execute tests
        for test in tests:
            result = await test
            if not result and test in [tests[0], tests[1], tests[2]]:
                # Critical failure - stop testing
                print("\n❌ Critical test failed - stopping test suite")
                break
        
        # Generate report
        tester.generate_report()


if __name__ == "__main__":
    asyncio.run(main())