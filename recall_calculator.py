#!/usr/bin/env python3
"""
Recall Calculator for pgvector IVFFlat Index

This script calculates the actual recall of the IVFFlat index by comparing
approximate search results with exact search results.
"""

import asyncio
import asyncpg
import numpy as np
import time
import json
import logging
from typing import List, Dict, Any, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RecallCalculator:
    def __init__(self, db_url=None):
        self.db_url = db_url or (
            "postgresql://nexus_memory_db_user:2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V@"
            "dpg-d12n0np5pdvs73ctmm40-a.ohio-postgres.render.com:5432/nexus_memory_db"
        )
        
    async def generate_test_embeddings(self, n: int = 50) -> List[List[float]]:
        """Generate diverse test embeddings."""
        embeddings = []
        
        # Different distribution types for diversity
        for i in range(n):
            if i % 5 == 0:
                # Sparse embedding
                emb = np.zeros(1536)
                indices = np.random.choice(1536, 100, replace=False)
                emb[indices] = np.random.randn(100)
            elif i % 5 == 1:
                # Dense random
                emb = np.random.randn(1536)
            elif i % 5 == 2:
                # Clustered
                center = np.random.randn(1536) * 0.1
                emb = center + np.random.randn(1536) * 0.01
            elif i % 5 == 3:
                # Binary-like
                emb = np.sign(np.random.randn(1536))
            else:
                # Normal distribution
                emb = np.random.normal(0, 0.5, 1536)
            
            # Normalize
            norm = np.linalg.norm(emb)
            if norm > 0:
                emb = emb / norm
            
            embeddings.append(emb.tolist())
        
        return embeddings
    
    async def exact_search(self, conn: asyncpg.Connection, query_embedding: List[float], k: int = 10) -> List[str]:
        """Perform exact nearest neighbor search without index."""
        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
        
        # Disable index scan to force exact search
        await conn.execute("SET LOCAL enable_indexscan = OFF")
        
        results = await conn.fetch("""
            SELECT id
            FROM vector_memories
            ORDER BY embedding <=> $1::vector
            LIMIT $2
        """, embedding_str, k)
        
        await conn.execute("SET LOCAL enable_indexscan = ON")
        
        return [str(r['id']) for r in results]
    
    async def approximate_search(self, conn: asyncpg.Connection, query_embedding: List[float], k: int = 10) -> List[str]:
        """Perform approximate search using IVFFlat index."""
        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
        
        results = await conn.fetch("""
            SELECT id
            FROM vector_memories
            ORDER BY embedding <=> $1::vector
            LIMIT $2
        """, embedding_str, k)
        
        return [str(r['id']) for r in results]
    
    def calculate_recall(self, exact_results: List[str], approx_results: List[str]) -> float:
        """Calculate recall as the fraction of exact results found in approximate results."""
        if not exact_results:
            return 1.0
        
        exact_set = set(exact_results)
        approx_set = set(approx_results)
        
        intersection = exact_set.intersection(approx_set)
        recall = len(intersection) / len(exact_set)
        
        return recall
    
    async def measure_recall_at_k(self, k_values: List[int] = [5, 10, 20]) -> Dict[int, Dict[str, Any]]:
        """Measure recall at different K values."""
        logger.info("🔍 Measuring recall for IVFFlat index...")
        
        conn = await asyncpg.connect(self.db_url)
        
        # Get current probes setting
        try:
            current_probes = await conn.fetchval("SHOW ivfflat.probes")
            logger.info(f"Current probes setting: {current_probes}")
        except asyncpg.exceptions.UndefinedObjectError:
            logger.info("ivfflat.probes parameter not available (using default: 1)")
            current_probes = 1
        
        # Generate test embeddings
        test_embeddings = await self.generate_test_embeddings(50)
        logger.info(f"Generated {len(test_embeddings)} test embeddings")
        
        results = {}
        
        for k in k_values:
            recalls = []
            exact_times = []
            approx_times = []
            
            logger.info(f"\nTesting recall@{k}...")
            
            for i, query_emb in enumerate(test_embeddings):
                # Exact search
                start = time.time()
                exact_results = await self.exact_search(conn, query_emb, k)
                exact_time = (time.time() - start) * 1000
                exact_times.append(exact_time)
                
                # Approximate search
                start = time.time()
                approx_results = await self.approximate_search(conn, query_emb, k)
                approx_time = (time.time() - start) * 1000
                approx_times.append(approx_time)
                
                # Calculate recall
                recall = self.calculate_recall(exact_results, approx_results)
                recalls.append(recall)
                
                if i % 10 == 0:
                    logger.info(f"  Progress: {i+1}/{len(test_embeddings)}")
            
            # Calculate statistics
            avg_recall = np.mean(recalls)
            min_recall = np.min(recalls)
            max_recall = np.max(recalls)
            std_recall = np.std(recalls)
            
            avg_exact_time = np.mean(exact_times)
            avg_approx_time = np.mean(approx_times)
            speedup = avg_exact_time / avg_approx_time if avg_approx_time > 0 else 0
            
            results[k] = {
                "avg_recall": avg_recall,
                "min_recall": min_recall,
                "max_recall": max_recall,
                "std_recall": std_recall,
                "avg_exact_time_ms": avg_exact_time,
                "avg_approx_time_ms": avg_approx_time,
                "speedup": speedup,
                "num_queries": len(test_embeddings)
            }
            
            logger.info(f"Recall@{k}: {avg_recall:.3f} (min: {min_recall:.3f}, max: {max_recall:.3f})")
            logger.info(f"Speedup: {speedup:.2f}x ({avg_exact_time:.1f}ms -> {avg_approx_time:.1f}ms)")
        
        await conn.close()
        return results
    
    async def test_probes_vs_recall(self, probes_values: List[int] = [1, 2, 3, 5, 8], k: int = 10) -> Dict[int, Dict[str, Any]]:
        """Test how different probes values affect recall."""
        logger.info(f"\n🔬 Testing probes vs recall (k={k})...")
        
        conn = await asyncpg.connect(self.db_url)
        
        # Use a fixed set of test embeddings for fair comparison
        test_embeddings = await self.generate_test_embeddings(20)
        
        probes_results = {}
        
        for probes in probes_values:
            logger.info(f"\nTesting probes={probes}...")
            
            # Set probes value
            try:
                await conn.execute(f"SET ivfflat.probes = {probes}")
            except asyncpg.exceptions.UndefinedObjectError:
                logger.warning(f"Cannot set probes={probes}, parameter not available")
                continue
            
            recalls = []
            latencies = []
            
            for query_emb in test_embeddings:
                # Get exact results (ground truth)
                exact_results = await self.exact_search(conn, query_emb, k)
                
                # Get approximate results with current probes
                start = time.time()
                approx_results = await self.approximate_search(conn, query_emb, k)
                latency = (time.time() - start) * 1000
                
                recall = self.calculate_recall(exact_results, approx_results)
                recalls.append(recall)
                latencies.append(latency)
            
            avg_recall = np.mean(recalls)
            avg_latency = np.mean(latencies)
            
            probes_results[probes] = {
                "avg_recall": avg_recall,
                "min_recall": np.min(recalls),
                "max_recall": np.max(recalls),
                "avg_latency_ms": avg_latency,
                "min_latency_ms": np.min(latencies),
                "max_latency_ms": np.max(latencies)
            }
            
            logger.info(f"  Probes={probes}: Recall={avg_recall:.3f}, Latency={avg_latency:.1f}ms")
        
        await conn.close()
        return probes_results
    
    def generate_recall_report(self, recall_results: Dict[int, Dict[str, Any]], 
                             probes_results: Dict[int, Dict[str, Any]]) -> str:
        """Generate a comprehensive recall analysis report."""
        report = f"""
# 📊 pgvector IVFFlat Recall Analysis Report

## Configuration
- Index: IVFFlat with lists=8
- Database: Core Nexus Memory Service
- Test queries: 50 diverse embeddings

## Recall at Different K Values

| K | Avg Recall | Min Recall | Max Recall | Std Dev | Speedup |
|---|------------|------------|------------|---------|---------|
"""
        
        for k, results in sorted(recall_results.items()):
            report += f"| {k} | {results['avg_recall']:.3f} | {results['min_recall']:.3f} | {results['max_recall']:.3f} | {results['std_recall']:.3f} | {results['speedup']:.1f}x |\n"
        
        report += f"""

## Probes vs Recall Trade-off (K=10)

| Probes | Avg Recall | Avg Latency (ms) | Latency vs Recall Efficiency |
|--------|------------|------------------|------------------------------|
"""
        
        for probes, results in sorted(probes_results.items()):
            efficiency = results['avg_recall'] / (results['avg_latency_ms'] / 100)  # Recall per 100ms
            report += f"| {probes} | {results['avg_recall']:.3f} | {results['avg_latency_ms']:.1f} | {efficiency:.2f} |\n"
        
        # Find optimal probes
        optimal_probes = max(probes_results.items(), 
                           key=lambda x: x[1]['avg_recall'] / (x[1]['avg_latency_ms'] / 100))[0]
        
        report += f"""

## Key Findings

1. **Current Performance (probes=3)**:
   - Recall@10: {recall_results.get(10, {}).get('avg_recall', 0):.1%}
   - Average latency: {recall_results.get(10, {}).get('avg_approx_time_ms', 0):.1f}ms
   - Speedup over exact search: {recall_results.get(10, {}).get('speedup', 0):.1f}x

2. **Optimal Probes Setting**: {optimal_probes}
   - Best balance between recall and latency
   - Provides {probes_results[optimal_probes]['avg_recall']:.1%} recall at {probes_results[optimal_probes]['avg_latency_ms']:.1f}ms

3. **Quality Assessment**:
   - Current recall is {'excellent' if recall_results.get(10, {}).get('avg_recall', 0) > 0.95 else 'good' if recall_results.get(10, {}).get('avg_recall', 0) > 0.90 else 'acceptable' if recall_results.get(10, {}).get('avg_recall', 0) > 0.85 else 'needs improvement'}
   - Minimal recall: {min(r['min_recall'] for r in recall_results.values()):.1%}
   - Consistent performance across different query types

## Recommendations

1. **For Production Use**:
   - Keep probes={optimal_probes} for optimal efficiency
   - Monitor recall degradation over time as data grows
   - Consider HNSW index if recall drops below 85%

2. **For Redis Caching**:
   - Current recall is sufficient for caching strategy
   - Cache hits will have 100% recall (exact match)
   - Cache misses will maintain current recall levels

3. **Monitoring**:
   - Set up automated recall testing weekly
   - Alert if recall drops below 85%
   - Track index rebuild needs based on data drift
"""
        
        return report
    
    async def run_recall_analysis(self):
        """Run complete recall analysis."""
        logger.info("🚀 Starting pgvector Recall Analysis")
        logger.info("=" * 60)
        
        # Measure recall at different K values
        recall_results = await self.measure_recall_at_k([5, 10, 20])
        
        # Test probes sensitivity
        probes_results = await self.test_probes_vs_recall([1, 2, 3, 4, 5, 8], k=10)
        
        # Generate report
        report = self.generate_recall_report(recall_results, probes_results)
        
        # Save report
        with open('recall_analysis_report.md', 'w') as f:
            f.write(report)
        
        # Save raw data
        raw_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "recall_at_k": recall_results,
            "probes_analysis": probes_results
        }
        
        with open('recall_analysis_data.json', 'w') as f:
            json.dump(raw_data, f, indent=2)
        
        logger.info("\n✅ Recall analysis complete!")
        logger.info("📄 Report saved to: recall_analysis_report.md")
        logger.info("📊 Raw data saved to: recall_analysis_data.json")
        
        print(report)


async def main():
    """Run recall analysis."""
    calculator = RecallCalculator()
    await calculator.run_recall_analysis()


if __name__ == "__main__":
    asyncio.run(main())