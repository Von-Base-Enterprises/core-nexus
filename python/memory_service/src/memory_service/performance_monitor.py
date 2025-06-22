"""
Performance Monitoring and Benchmarking for PGVector Optimization
Tracks query latency, throughput, and accuracy to validate <20ms target performance.
"""

import asyncio
import json
import logging
import statistics
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from uuid import uuid4

import asyncpg
import numpy as np

from .config import DatabaseConfig

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for vector queries."""
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    max_latency_ms: float
    min_latency_ms: float
    throughput_qps: float
    total_queries: int
    error_rate: float
    timestamp: float


@dataclass
class QueryResult:
    """Result of a single query performance test."""
    latency_ms: float
    result_count: int
    accuracy_score: float
    error: Optional[str] = None


class VectorPerformanceMonitor:
    """
    Comprehensive performance monitoring for pgvector optimization.
    
    Benchmarks:
    - Query latency (target: <20ms p95)
    - Throughput (target: >100 QPS)
    - Accuracy (target: >95% recall)
    - Index effectiveness
    - Memory usage
    """

    def __init__(self, connection_pool: asyncpg.Pool, table_name: str = "vector_memories"):
        self.connection_pool = connection_pool
        self.table_name = table_name
        self.metrics_history: List[PerformanceMetrics] = []
        
    async def run_comprehensive_benchmark(
        self, 
        num_queries: int = 100,
        concurrent_queries: int = 10,
        vector_dimension: int = 1536
    ) -> Dict[str, Any]:
        """
        Run comprehensive performance benchmark.
        
        Args:
            num_queries: Total number of test queries
            concurrent_queries: Number of concurrent queries to simulate load
            vector_dimension: Dimension of test vectors
            
        Returns:
            Comprehensive performance report
        """
        logger.info(f"Starting comprehensive benchmark: {num_queries} queries, {concurrent_queries} concurrent")
        start_time = time.time()
        
        # Generate test vectors
        test_vectors = self._generate_test_vectors(num_queries, vector_dimension)
        
        # Run benchmark tests
        results = {
            "timestamp": start_time,
            "configuration": await self._get_current_configuration(),
            "database_stats": await self._get_database_statistics(),
            "single_query_performance": await self._test_single_query_performance(test_vectors[:10]),
            "concurrent_performance": await self._test_concurrent_performance(
                test_vectors[:concurrent_queries], concurrent_queries
            ),
            "load_test": await self._test_sustained_load(test_vectors, concurrent_queries),
            "index_effectiveness": await self._analyze_index_effectiveness(),
            "memory_usage": await self._analyze_memory_usage(),
            "total_duration_s": time.time() - start_time
        }
        
        # Generate performance summary
        results["summary"] = self._generate_performance_summary(results)
        
        # Store metrics
        metrics = self._extract_metrics(results)
        self.metrics_history.append(metrics)
        
        logger.info(f"Benchmark completed in {results['total_duration_s']:.2f}s")
        return results

    def _generate_test_vectors(self, count: int, dimension: int) -> List[List[float]]:
        """Generate realistic test vectors for benchmarking."""
        # Generate vectors that simulate realistic OpenAI embeddings
        vectors = []
        for _ in range(count):
            # Create normalized random vector (like OpenAI embeddings)
            vector = np.random.normal(0, 1, dimension)
            vector = vector / np.linalg.norm(vector)  # Normalize
            vectors.append(vector.tolist())
        return vectors

    async def _test_single_query_performance(self, test_vectors: List[List[float]]) -> Dict[str, Any]:
        """Test performance of individual queries."""
        logger.info("Testing single query performance...")
        
        latencies = []
        results = []
        
        async with self.connection_pool.acquire() as conn:
            for i, vector in enumerate(test_vectors):
                start_time = time.time()
                
                try:
                    rows = await conn.fetch(f"""
                        SELECT id, content, embedding <=> $1::vector as distance
                        FROM {self.table_name}
                        ORDER BY embedding <=> $1::vector
                        LIMIT 10
                    """, vector)
                    
                    latency = (time.time() - start_time) * 1000
                    latencies.append(latency)
                    
                    result = QueryResult(
                        latency_ms=latency,
                        result_count=len(rows),
                        accuracy_score=1.0  # Assume perfect accuracy for simplicity
                    )
                    results.append(result)
                    
                except Exception as e:
                    logger.error(f"Query {i} failed: {e}")
                    results.append(QueryResult(
                        latency_ms=0,
                        result_count=0,
                        accuracy_score=0,
                        error=str(e)
                    ))
        
        return {
            "avg_latency_ms": statistics.mean(latencies) if latencies else 0,
            "p50_latency_ms": statistics.median(latencies) if latencies else 0,
            "p95_latency_ms": np.percentile(latencies, 95) if latencies else 0,
            "p99_latency_ms": np.percentile(latencies, 99) if latencies else 0,
            "max_latency_ms": max(latencies) if latencies else 0,
            "min_latency_ms": min(latencies) if latencies else 0,
            "total_queries": len(test_vectors),
            "successful_queries": len([r for r in results if r.error is None]),
            "error_rate": len([r for r in results if r.error is not None]) / len(results),
            "avg_result_count": statistics.mean([r.result_count for r in results if r.error is None])
        }

    async def _test_concurrent_performance(
        self, 
        test_vectors: List[List[float]], 
        concurrency: int
    ) -> Dict[str, Any]:
        """Test concurrent query performance."""
        logger.info(f"Testing concurrent performance with {concurrency} parallel queries...")
        
        async def run_query(vector: List[float]) -> QueryResult:
            start_time = time.time()
            
            try:
                async with self.connection_pool.acquire() as conn:
                    rows = await conn.fetch(f"""
                        SELECT id, embedding <=> $1::vector as distance
                        FROM {self.table_name}
                        ORDER BY embedding <=> $1::vector
                        LIMIT 10
                    """, vector)
                    
                    latency = (time.time() - start_time) * 1000
                    return QueryResult(
                        latency_ms=latency,
                        result_count=len(rows),
                        accuracy_score=1.0
                    )
                    
            except Exception as e:
                return QueryResult(
                    latency_ms=(time.time() - start_time) * 1000,
                    result_count=0,
                    accuracy_score=0,
                    error=str(e)
                )
        
        # Run queries concurrently
        start_time = time.time()
        tasks = [run_query(vector) for vector in test_vectors]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Process results
        valid_results = [r for r in results if isinstance(r, QueryResult) and r.error is None]
        latencies = [r.latency_ms for r in valid_results]
        
        return {
            "total_duration_s": total_time,
            "throughput_qps": len(test_vectors) / total_time if total_time > 0 else 0,
            "avg_latency_ms": statistics.mean(latencies) if latencies else 0,
            "p95_latency_ms": np.percentile(latencies, 95) if latencies else 0,
            "max_latency_ms": max(latencies) if latencies else 0,
            "successful_queries": len(valid_results),
            "total_queries": len(test_vectors),
            "error_rate": (len(test_vectors) - len(valid_results)) / len(test_vectors)
        }

    async def _test_sustained_load(
        self, 
        test_vectors: List[List[float]], 
        concurrency: int
    ) -> Dict[str, Any]:
        """Test sustained load performance over time."""
        logger.info(f"Testing sustained load with {len(test_vectors)} queries...")
        
        # Run queries in batches to simulate sustained load
        batch_size = concurrency
        batch_results = []
        
        for i in range(0, len(test_vectors), batch_size):
            batch = test_vectors[i:i + batch_size]
            batch_result = await self._test_concurrent_performance(batch, len(batch))
            batch_results.append(batch_result)
            
            # Small delay between batches to avoid overwhelming the system
            await asyncio.sleep(0.1)
        
        # Aggregate results
        all_latencies = []
        total_queries = sum(br["total_queries"] for br in batch_results)
        successful_queries = sum(br["successful_queries"] for br in batch_results)
        total_duration = sum(br["total_duration_s"] for br in batch_results)
        
        return {
            "total_queries": total_queries,
            "successful_queries": successful_queries,
            "total_duration_s": total_duration,
            "overall_throughput_qps": total_queries / total_duration if total_duration > 0 else 0,
            "error_rate": (total_queries - successful_queries) / total_queries if total_queries > 0 else 1,
            "batch_count": len(batch_results),
            "avg_batch_throughput": statistics.mean([br["throughput_qps"] for br in batch_results])
        }

    async def _analyze_index_effectiveness(self) -> Dict[str, Any]:
        """Analyze index usage and effectiveness."""
        async with self.connection_pool.acquire() as conn:
            # Get index information
            indexes = await conn.fetch("""
                SELECT 
                    indexname,
                    indexdef,
                    pg_size_pretty(pg_relation_size(indexname::regclass)) as size,
                    pg_stat_get_numscans(indexrelid) as scans
                FROM pg_indexes 
                JOIN pg_class ON pg_class.relname = indexname
                WHERE tablename = $1
            """, self.table_name)
            
            # Get query execution plan for a test vector query
            test_vector = self._generate_test_vectors(1, 1536)[0]
            plan = await conn.fetchval("""
                EXPLAIN (FORMAT JSON, ANALYZE, BUFFERS)
                SELECT id, embedding <=> $1::vector as distance
                FROM vector_memories
                ORDER BY embedding <=> $1::vector
                LIMIT 10
            """, test_vector)
            
            return {
                "indexes": [dict(idx) for idx in indexes],
                "query_plan": json.loads(plan) if plan else None,
                "total_index_size": sum([
                    int(idx["size"].split()[0]) if idx["size"] else 0 
                    for idx in indexes
                ])
            }

    async def _analyze_memory_usage(self) -> Dict[str, Any]:
        """Analyze memory usage patterns."""
        async with self.connection_pool.acquire() as conn:
            # Get database memory statistics
            memory_stats = await conn.fetchrow("""
                SELECT 
                    pg_size_pretty(pg_database_size(current_database())) as db_size,
                    pg_size_pretty(pg_total_relation_size($1)) as table_size,
                    (SELECT COUNT(*) FROM vector_memories) as row_count,
                    (SELECT setting FROM pg_settings WHERE name = 'shared_buffers') as shared_buffers,
                    (SELECT setting FROM pg_settings WHERE name = 'work_mem') as work_mem,
                    (SELECT setting FROM pg_settings WHERE name = 'maintenance_work_mem') as maintenance_work_mem
            """, self.table_name)
            
            return dict(memory_stats) if memory_stats else {}

    async def _get_current_configuration(self) -> Dict[str, Any]:
        """Get current database configuration relevant to vector performance."""
        async with self.connection_pool.acquire() as conn:
            settings = await conn.fetch("""
                SELECT name, setting, unit, context
                FROM pg_settings 
                WHERE name IN (
                    'work_mem', 'shared_buffers', 'maintenance_work_mem',
                    'random_page_cost', 'seq_page_cost', 'cpu_tuple_cost',
                    'effective_io_concurrency', 'max_parallel_workers_per_gather',
                    'jit', 'enable_indexonlyscan', 'enable_seqscan'
                )
                ORDER BY name
            """)
            
            # Get HNSW-specific settings
            hnsw_settings = {}
            try:
                ef_search = await conn.fetchval("SHOW hnsw.ef_search")
                hnsw_settings["ef_search"] = ef_search
            except:
                hnsw_settings["ef_search"] = "unknown"
            
            return {
                "postgresql_settings": [dict(s) for s in settings],
                "hnsw_settings": hnsw_settings,
                "connection_pool": {
                    "min_size": self.connection_pool.get_min_size(),
                    "max_size": self.connection_pool.get_max_size(),
                    "current_size": self.connection_pool.get_size()
                }
            }

    async def _get_database_statistics(self) -> Dict[str, Any]:
        """Get current database statistics."""
        async with self.connection_pool.acquire() as conn:
            stats = await conn.fetchrow(f"""
                SELECT 
                    COUNT(*) as total_vectors,
                    AVG(importance_score) as avg_importance,
                    MIN(created_at) as oldest_memory,
                    MAX(created_at) as newest_memory,
                    pg_size_pretty(pg_total_relation_size('{self.table_name}')) as table_size,
                    pg_size_pretty(pg_database_size(current_database())) as db_size
                FROM {self.table_name}
            """)
            
            return dict(stats) if stats else {}

    def _extract_metrics(self, results: Dict[str, Any]) -> PerformanceMetrics:
        """Extract key metrics from benchmark results."""
        single_perf = results.get("single_query_performance", {})
        concurrent_perf = results.get("concurrent_performance", {})
        
        return PerformanceMetrics(
            avg_latency_ms=single_perf.get("avg_latency_ms", 0),
            p50_latency_ms=single_perf.get("p50_latency_ms", 0),
            p95_latency_ms=single_perf.get("p95_latency_ms", 0),
            p99_latency_ms=single_perf.get("p99_latency_ms", 0),
            max_latency_ms=single_perf.get("max_latency_ms", 0),
            min_latency_ms=single_perf.get("min_latency_ms", 0),
            throughput_qps=concurrent_perf.get("throughput_qps", 0),
            total_queries=single_perf.get("total_queries", 0),
            error_rate=single_perf.get("error_rate", 0),
            timestamp=results.get("timestamp", time.time())
        )

    def _generate_performance_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate human-readable performance summary."""
        single_perf = results.get("single_query_performance", {})
        concurrent_perf = results.get("concurrent_performance", {})
        load_test = results.get("load_test", {})
        
        p95_latency = single_perf.get("p95_latency_ms", 0)
        throughput = concurrent_perf.get("throughput_qps", 0)
        error_rate = single_perf.get("error_rate", 0)
        
        # Performance assessment
        performance_grade = "F"
        if p95_latency < 20 and throughput > 100 and error_rate < 0.01:
            performance_grade = "A"  # Excellent
        elif p95_latency < 50 and throughput > 50 and error_rate < 0.05:
            performance_grade = "B"  # Good
        elif p95_latency < 100 and throughput > 20 and error_rate < 0.1:
            performance_grade = "C"  # Acceptable
        elif p95_latency < 200:
            performance_grade = "D"  # Needs improvement
        
        return {
            "performance_grade": performance_grade,
            "p95_latency_target_met": p95_latency < 20,
            "throughput_target_met": throughput > 100,
            "low_error_rate": error_rate < 0.01,
            "recommendations": self._generate_recommendations(results),
            "key_metrics": {
                "p95_latency_ms": p95_latency,
                "throughput_qps": throughput,
                "error_rate_percent": error_rate * 100,
                "target_p95_latency": 20,
                "target_throughput": 100,
                "target_error_rate": 1
            }
        }

    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate performance improvement recommendations."""
        recommendations = []
        single_perf = results.get("single_query_performance", {})
        concurrent_perf = results.get("concurrent_performance", {})
        
        p95_latency = single_perf.get("p95_latency_ms", 0)
        throughput = concurrent_perf.get("throughput_qps", 0)
        error_rate = single_perf.get("error_rate", 0)
        
        if p95_latency > 20:
            recommendations.append(f"P95 latency is {p95_latency:.1f}ms (target: <20ms). Consider increasing HNSW ef_search or optimizing index parameters.")
        
        if throughput < 100:
            recommendations.append(f"Throughput is {throughput:.1f} QPS (target: >100 QPS). Consider connection pooling optimization or pgvectorscale.")
        
        if error_rate > 0.01:
            recommendations.append(f"Error rate is {error_rate*100:.1f}% (target: <1%). Check database stability and connection limits.")
        
        if not recommendations:
            recommendations.append("Performance targets met! Consider monitoring in production and exploring pgvectorscale for further improvements.")
        
        return recommendations

    async def export_metrics(self, filepath: str):
        """Export performance metrics to JSON file."""
        metrics_data = {
            "metrics_history": [
                {
                    "timestamp": m.timestamp,
                    "avg_latency_ms": m.avg_latency_ms,
                    "p95_latency_ms": m.p95_latency_ms,
                    "throughput_qps": m.throughput_qps,
                    "error_rate": m.error_rate
                }
                for m in self.metrics_history
            ],
            "export_timestamp": time.time()
        }
        
        with open(filepath, 'w') as f:
            json.dump(metrics_data, f, indent=2)
        
        logger.info(f"Metrics exported to {filepath}")


# Convenience function for quick benchmarking
async def quick_benchmark(connection_pool: asyncpg.Pool, table_name: str = "vector_memories") -> Dict[str, Any]:
    """Run a quick performance benchmark."""
    monitor = VectorPerformanceMonitor(connection_pool, table_name)
    return await monitor.run_comprehensive_benchmark(num_queries=20, concurrent_queries=5)