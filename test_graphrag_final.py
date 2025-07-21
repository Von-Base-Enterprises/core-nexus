#!/usr/bin/env python3
"""
Final comprehensive test suite for GraphRAG after all fixes.
"""

import asyncio
import aiohttp
import json
from datetime import datetime
import uuid

API_URL = "https://core-nexus-memory-service.onrender.com"
API_KEY = "test-key-67890"

class GraphRAGTester:
    def __init__(self):
        self.api_url = API_URL
        self.headers = {"X-API-Key": API_KEY}
        self.test_results = {
            "passed": 0,
            "failed": 0,
            "warnings": 0
        }
    
    async def run_test(self, name, test_func):
        """Run a single test and track results."""
        print(f"\n🧪 {name}")
        print("-" * 50)
        try:
            result = await test_func()
            if result:
                self.test_results["passed"] += 1
                print("   ✅ PASSED")
            else:
                self.test_results["failed"] += 1
                print("   ❌ FAILED")
            return result
        except Exception as e:
            self.test_results["failed"] += 1
            print(f"   ❌ ERROR: {e}")
            return False
    
    async def test_memory_creation_with_entities(self):
        """Test that new memories create entity mappings."""
        async with aiohttp.ClientSession() as session:
            # Create a unique test memory
            test_id = str(uuid.uuid4())[:8]
            test_memory = {
                "content": f"Test {test_id}: Anthropic's Claude is helping Von Base Enterprises improve Core Nexus GraphRAG capabilities.",
                "metadata": {"test_id": test_id},
                "importance_score": 0.9
            }
            
            # Create memory
            async with session.post(f"{self.api_url}/memories", 
                                  headers={**self.headers, "Content-Type": "application/json"}, 
                                  json=test_memory) as resp:
                if resp.status != 200:
                    print(f"   Failed to create memory: {resp.status}")
                    return False
                
                data = await resp.json()
                memory_id = data.get('id')
                print(f"   Memory created: {memory_id}")
            
            # Wait for entity extraction
            await asyncio.sleep(3)
            
            # Check if entities were extracted
            entities_to_check = ["Anthropic", "Claude", "Von Base Enterprises", "Core Nexus"]
            found_entities = 0
            
            for entity in entities_to_check:
                async with session.get(f"{self.api_url}/graph/explore/{entity}", 
                                     headers=self.headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data['memories_found'] > 0:
                            found_entities += 1
                            # Check if our test memory is included
                            if any(test_id in str(mem.get('content', '')) for mem in data['memories']):
                                print(f"   ✓ {entity} linked to test memory")
            
            return found_entities >= 2  # At least 2 entities should be linked
    
    async def test_entity_exploration(self):
        """Test that entity exploration returns memories."""
        async with aiohttp.ClientSession() as session:
            # Test key entities
            test_entities = ["Von Base Enterprises", "Core Nexus", "GPT-4"]
            entities_with_memories = 0
            
            for entity in test_entities:
                async with session.get(f"{self.api_url}/graph/explore/{entity}", 
                                     headers=self.headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data['memories_found'] > 0:
                            entities_with_memories += 1
                            print(f"   ✓ {entity}: {data['memories_found']} memories")
                        else:
                            print(f"   ✗ {entity}: No memories found")
                            self.test_results["warnings"] += 1
            
            return entities_with_memories > 0
    
    async def test_graph_queries(self):
        """Test various graph query types."""
        async with aiohttp.ClientSession() as session:
            queries = [
                {"query_type": "entities_by_type", "entity_type": "organization"},
                {"query_type": "entities_by_type", "entity_type": "TECHNOLOGY"},
                {"entity_name": "Von Base Enterprises"},
                {"entity_name": "Claude", "entity_type": "technology"}
            ]
            
            successful_queries = 0
            for query in queries:
                async with session.post(f"{self.api_url}/graph/query", 
                                      headers={**self.headers, "Content-Type": "application/json"}, 
                                      json=query) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data['total_nodes'] > 0 or data['total_relationships'] > 0:
                            successful_queries += 1
                            print(f"   ✓ Query {query}: {data['total_nodes']} nodes, {data['total_relationships']} relationships")
                        else:
                            print(f"   ✗ Query {query}: Empty results")
            
            return successful_queries >= 2
    
    async def test_relationship_detection(self):
        """Test that relationships are being created."""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.api_url}/graph/stats", headers=self.headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    stats = data['statistics']
                    
                    print(f"   Total nodes: {stats['total_nodes']}")
                    print(f"   Total relationships: {stats['total_relationships']}")
                    print(f"   Relationship types: {stats['relationship_types']}")
                    
                    return stats['total_relationships'] > 25
                return False
    
    async def test_live_stats(self):
        """Test the live stats endpoint."""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.api_url}/api/knowledge-graph/live-stats", 
                                 headers=self.headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    print(f"   Entity count: {data['entity_count']}")
                    print(f"   Top entity: {data['top_entities'][0]['name']} ({data['top_entities'][0]['connections']} connections)")
                    
                    return data['entity_count'] > 150 and data['relationship_count'] > 20
                return False
    
    async def test_memory_query_integration(self):
        """Test that regular memory queries still work."""
        async with aiohttp.ClientSession() as session:
            query = {
                "query": "Von Base Enterprises",
                "limit": 5,
                "min_similarity": 0.5
            }
            
            async with session.post(f"{self.api_url}/memories/query", 
                                  headers={**self.headers, "Content-Type": "application/json"}, 
                                  json=query) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   Found {data['total_found']} memories")
                    print(f"   Query time: {data['query_time_ms']:.1f}ms")
                    return data['total_found'] > 0
                return False
    
    async def run_all_tests(self):
        """Run all GraphRAG tests."""
        print("🔍 COMPREHENSIVE GRAPHRAG VALIDATION")
        print("=" * 60)
        print(f"API: {self.api_url}")
        print(f"Time: {datetime.now()}")
        print("=" * 60)
        
        # Run all tests
        await self.run_test("Memory Creation with Entity Extraction", self.test_memory_creation_with_entities)
        await self.run_test("Entity Exploration", self.test_entity_exploration)
        await self.run_test("Graph Queries", self.test_graph_queries)
        await self.run_test("Relationship Detection", self.test_relationship_detection)
        await self.run_test("Live Stats Endpoint", self.test_live_stats)
        await self.run_test("Memory Query Integration", self.test_memory_query_integration)
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {self.test_results['passed']}")
        print(f"❌ Failed: {self.test_results['failed']}")
        print(f"⚠️  Warnings: {self.test_results['warnings']}")
        
        success_rate = (self.test_results['passed'] / 
                       (self.test_results['passed'] + self.test_results['failed']) * 100)
        print(f"\nSuccess Rate: {success_rate:.1f}%")
        
        if success_rate == 100:
            print("\n🎉 GRAPHRAG IS FULLY OPERATIONAL!")
        elif success_rate >= 80:
            print("\n✅ GraphRAG is mostly working - check warnings")
        else:
            print("\n❌ GraphRAG needs attention - check failed tests")
        
        print("\n📝 NEXT STEPS:")
        if self.test_results['warnings'] > 0:
            print("1. Run migration script to fix existing memories")
        print("2. Monitor entity extraction rate")
        print("3. Implement multi-hop query features")
        print("4. Add more sophisticated relationship types")

if __name__ == "__main__":
    tester = GraphRAGTester()
    asyncio.run(tester.run_all_tests())