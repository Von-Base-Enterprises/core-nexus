"""
Performance benchmarks for Knowledge Graph operations.

Tests performance characteristics and helps identify optimization opportunities.
"""

import asyncio
import time
import pytest
import statistics
from typing import List, Dict, Any, Tuple
from uuid import uuid4
import random
import string


class PerformanceTester:
    """Base class for performance testing."""
    
    def __init__(self):
        self.results = []
    
    def record_time(self, operation: str, duration: float):
        """Record a timing result."""
        self.results.append({
            'operation': operation,
            'duration_ms': duration * 1000,
            'timestamp': time.time()
        })
    
    def get_stats(self, operation: str = None) -> Dict[str, float]:
        """Get statistics for recorded times."""
        if operation:
            times = [r['duration_ms'] for r in self.results if r['operation'] == operation]
        else:
            times = [r['duration_ms'] for r in self.results]
        
        if not times:
            return {}
        
        return {
            'count': len(times),
            'mean_ms': statistics.mean(times),
            'median_ms': statistics.median(times),
            'min_ms': min(times),
            'max_ms': max(times),
            'stdev_ms': statistics.stdev(times) if len(times) > 1 else 0
        }


class TestEntityExtractionPerformance:
    """Benchmark entity extraction performance."""
    
    def generate_test_content(self, length: int = 500) -> str:
        """Generate test content with entities."""
        entities = [
            "Microsoft", "Google", "Apple", "Amazon", "Tesla",
            "OpenAI", "DeepMind", "Anthropic", "Meta", "IBM"
        ]
        
        words = []
        for i in range(length // 10):
            # Add some entities
            if i % 5 == 0:
                words.append(random.choice(entities))
            # Add regular words
            words.extend([
                ''.join(random.choices(string.ascii_lowercase, k=random.randint(3, 8)))
                for _ in range(9)
            ])
        
        return ' '.join(words)
    
    @pytest.mark.asyncio
    async def test_regex_extraction_performance(self):
        """Benchmark regex-based entity extraction."""
        import re
        
        pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        perf = PerformanceTester()
        
        # Test different content sizes
        sizes = [100, 500, 1000, 5000]
        
        for size in sizes:
            content = self.generate_test_content(size)
            
            # Warm up
            list(re.finditer(pattern, content))
            
            # Benchmark
            iterations = 100
            for _ in range(iterations):
                start = time.perf_counter()
                entities = list(re.finditer(pattern, content))
                duration = time.perf_counter() - start
                perf.record_time(f'regex_{size}', duration)
        
        # Report results
        for size in sizes:
            stats = perf.get_stats(f'regex_{size}')
            print(f"\nRegex extraction for {size} words:")
            print(f"  Mean: {stats.get('mean_ms', 0):.2f}ms")
            print(f"  Median: {stats.get('median_ms', 0):.2f}ms")
            print(f"  Min/Max: {stats.get('min_ms', 0):.2f}ms / {stats.get('max_ms', 0):.2f}ms")
            
            # Performance assertions
            assert stats['mean_ms'] < 10, f"Regex too slow for {size} words"
    
    @pytest.mark.asyncio
    async def test_batch_extraction_performance(self):
        """Test performance of batch entity extraction."""
        import re
        
        pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        perf = PerformanceTester()
        
        # Generate batch of content
        batch_sizes = [10, 50, 100]
        content_length = 200
        
        for batch_size in batch_sizes:
            contents = [self.generate_test_content(content_length) for _ in range(batch_size)]
            
            # Sequential processing
            start = time.perf_counter()
            for content in contents:
                list(re.finditer(pattern, content))
            seq_duration = time.perf_counter() - start
            perf.record_time(f'sequential_{batch_size}', seq_duration)
            
            # Simulated parallel processing
            start = time.perf_counter()
            results = await asyncio.gather(*[
                self.extract_entities_async(content, pattern) for content in contents
            ])
            par_duration = time.perf_counter() - start
            perf.record_time(f'parallel_{batch_size}', par_duration)
        
        # Compare sequential vs parallel
        for batch_size in batch_sizes:
            seq_stats = perf.get_stats(f'sequential_{batch_size}')
            par_stats = perf.get_stats(f'parallel_{batch_size}')
            
            print(f"\nBatch size {batch_size}:")
            print(f"  Sequential: {seq_stats.get('mean_ms', 0):.2f}ms")
            print(f"  Parallel: {par_stats.get('mean_ms', 0):.2f}ms")
            print(f"  Speedup: {seq_stats.get('mean_ms', 1) / par_stats.get('mean_ms', 1):.2f}x")
    
    async def extract_entities_async(self, content: str, pattern: str) -> List[str]:
        """Async wrapper for entity extraction."""
        import re
        # Simulate async operation
        await asyncio.sleep(0.001)
        return [m.group() for m in re.finditer(pattern, content)]


class TestRelationshipInferencePerformance:
    """Benchmark relationship inference performance."""
    
    def generate_entities(self, count: int) -> List[Dict[str, Any]]:
        """Generate test entities."""
        types = ['person', 'organization', 'technology', 'location', 'product']
        entities = []
        
        for i in range(count):
            entities.append({
                'name': f'Entity_{i}',
                'type': random.choice(types),
                'start': i * 50,
                'end': i * 50 + 10,
                'confidence': random.uniform(0.5, 1.0)
            })
        
        return entities
    
    @pytest.mark.asyncio
    async def test_relationship_inference_scaling(self):
        """Test how relationship inference scales with entity count."""
        perf = PerformanceTester()
        
        entity_counts = [5, 10, 20, 50]
        
        for count in entity_counts:
            entities = self.generate_entities(count)
            
            # Warm up
            self.infer_relationships(entities)
            
            # Benchmark
            iterations = 50
            for _ in range(iterations):
                start = time.perf_counter()
                relationships = self.infer_relationships(entities)
                duration = time.perf_counter() - start
                perf.record_time(f'inference_{count}', duration)
        
        # Analyze scaling
        for count in entity_counts:
            stats = perf.get_stats(f'inference_{count}')
            print(f"\nRelationship inference for {count} entities:")
            print(f"  Mean: {stats.get('mean_ms', 0):.2f}ms")
            print(f"  Relationships: {count * (count - 1) // 2}")
            
            # Should scale roughly O(n²)
            if count <= 20:
                assert stats['mean_ms'] < 50, f"Inference too slow for {count} entities"
    
    def infer_relationships(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Simple relationship inference based on distance."""
        relationships = []
        
        for i, entity1 in enumerate(entities):
            for j, entity2 in enumerate(entities):
                if i >= j:
                    continue
                
                distance = abs(entity1['start'] - entity2['start'])
                if distance < 200:
                    strength = 1.0 - (distance / 200.0)
                    relationships.append({
                        'from': entity1['name'],
                        'to': entity2['name'],
                        'strength': strength,
                        'type': 'relates_to'
                    })
        
        return relationships


class TestGraphQueryPerformance:
    """Benchmark graph query performance."""
    
    def create_test_graph(self, node_count: int, edge_density: float = 0.1) -> Tuple[Dict, Dict]:
        """Create a test graph."""
        nodes = {}
        edges = {}
        
        # Create nodes
        for i in range(node_count):
            node_id = uuid4()
            nodes[node_id] = {
                'id': node_id,
                'name': f'Node_{i}',
                'type': random.choice(['person', 'org', 'tech']),
                'importance': random.uniform(0.1, 1.0)
            }
        
        # Create edges
        node_ids = list(nodes.keys())
        edge_count = int(node_count * (node_count - 1) * edge_density / 2)
        
        for _ in range(edge_count):
            from_id = random.choice(node_ids)
            to_id = random.choice(node_ids)
            if from_id != to_id:
                edge_id = uuid4()
                edges[edge_id] = {
                    'id': edge_id,
                    'from': from_id,
                    'to': to_id,
                    'type': 'relates_to',
                    'strength': random.uniform(0.1, 1.0)
                }
        
        return nodes, edges
    
    @pytest.mark.asyncio
    async def test_graph_traversal_performance(self):
        """Test graph traversal performance at different scales."""
        perf = PerformanceTester()
        
        graph_sizes = [50, 100, 500]
        
        for size in graph_sizes:
            nodes, edges = self.create_test_graph(size, edge_density=0.1)
            
            # Pick random start nodes
            start_nodes = random.sample(list(nodes.keys()), min(10, size))
            
            for start_node in start_nodes:
                start = time.perf_counter()
                visited = self.bfs_traverse(start_node, nodes, edges, max_depth=3)
                duration = time.perf_counter() - start
                perf.record_time(f'traverse_{size}', duration)
        
        # Report results
        for size in graph_sizes:
            stats = perf.get_stats(f'traverse_{size}')
            print(f"\nGraph traversal for {size} nodes:")
            print(f"  Mean: {stats.get('mean_ms', 0):.2f}ms")
            print(f"  Median: {stats.get('median_ms', 0):.2f}ms")
            
            # Performance expectations
            assert stats['mean_ms'] < 100, f"Traversal too slow for {size} nodes"
    
    def bfs_traverse(self, start_node, nodes, edges, max_depth=3):
        """Breadth-first search traversal."""
        visited = set()
        queue = [(start_node, 0)]
        
        while queue:
            current, depth = queue.pop(0)
            if current in visited or depth > max_depth:
                continue
            
            visited.add(current)
            
            # Find neighbors
            for edge in edges.values():
                if edge['from'] == current:
                    queue.append((edge['to'], depth + 1))
                elif edge['to'] == current:
                    queue.append((edge['from'], depth + 1))
        
        return visited


class TestMemoryEfficiency:
    """Test memory efficiency of graph operations."""
    
    @pytest.mark.asyncio
    async def test_entity_storage_efficiency(self):
        """Test memory usage for entity storage."""
        import sys
        
        # Create entities with different property sizes
        base_entity = {
            'id': uuid4(),
            'name': 'Test Entity',
            'type': 'organization',
            'importance': 0.5,
            'mention_count': 1
        }
        
        # Test different property sizes
        property_sizes = [0, 10, 100, 1000]
        
        for prop_count in property_sizes:
            entity = base_entity.copy()
            entity['properties'] = {
                f'prop_{i}': f'value_{i}' * 10
                for i in range(prop_count)
            }
            
            size = sys.getsizeof(entity)
            print(f"\nEntity with {prop_count} properties: {size} bytes")
            
            # Ensure reasonable memory usage
            if prop_count <= 100:
                assert size < 10000, f"Entity too large with {prop_count} properties"
    
    @pytest.mark.asyncio
    async def test_batch_processing_memory(self):
        """Test memory efficiency of batch processing."""
        import gc
        import sys
        
        batch_sizes = [100, 1000]
        
        for batch_size in batch_sizes:
            # Force garbage collection
            gc.collect()
            
            # Create batch
            entities = []
            for i in range(batch_size):
                entities.append({
                    'id': uuid4(),
                    'name': f'Entity_{i}',
                    'type': 'test',
                    'embedding': [0.1] * 384  # Smaller embedding for test
                })
            
            # Measure total size
            total_size = sum(sys.getsizeof(e) for e in entities)
            avg_size = total_size / batch_size
            
            print(f"\nBatch of {batch_size} entities:")
            print(f"  Total size: {total_size / 1024:.2f} KB")
            print(f"  Average per entity: {avg_size:.2f} bytes")
            
            # Clean up
            entities.clear()
            gc.collect()


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-s"])  # -s to see print outputs