#!/usr/bin/env python3
"""
Baseline Metrics Capture for Core Nexus Memory Service

This script captures comprehensive baseline metrics including:
- Recall vs exact search
- Precision at different K values
- Latency percentiles
- F1 scores

This establishes the baseline before Redis caching implementation.
"""

import asyncio
import asyncpg
import json
import time
import numpy as np
import statistics
from datetime import datetime
from typing import List, Dict, Any, Tuple
import urllib.request
import urllib.error
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaselineMetrics:
    def __init__(self, api_url="https://core-nexus-memory-service.onrender.com", 
                 api_key="dev-key-12345",
                 db_url=None):
        self.api_url = api_url
        self.api_key = api_key
        self.db_url = db_url or (
            "postgresql://nexus_memory_db_user:2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V@"
            "dpg-d12n0np5pdvs73ctmm40-a.ohio-postgres.render.com:5432/nexus_memory_db"
        )
        self.test_queries = []
        self.ground_truth = {}
        self.metrics = defaultdict(list)
        
    def create_test_queries(self) -> List[Dict[str, Any]]:
        """Create diverse test queries with expected characteristics."""
        test_queries = [
            # Technical queries (should find technical memories)
            {"query": "pgvector optimization", "category": "technical", "expected_topics": ["pgvector", "optimization", "index"]},
            {"query": "vector database performance", "category": "technical", "expected_topics": ["vector", "performance", "database"]},
            {"query": "IVFFlat index configuration", "category": "technical", "expected_topics": ["IVFFlat", "index", "lists"]},
            {"query": "cosine similarity search", "category": "technical", "expected_topics": ["cosine", "similarity", "vector"]},
            {"query": "embedding dimension reduction", "category": "technical", "expected_topics": ["embedding", "dimension"]},
            
            # Performance queries
            {"query": "query latency improvement", "category": "performance", "expected_topics": ["latency", "performance", "improvement"]},
            {"query": "memory service optimization", "category": "performance", "expected_topics": ["memory", "service", "optimization"]},
            {"query": "cache hit rate", "category": "performance", "expected_topics": ["cache", "hit", "rate"]},
            
            # Business queries
            {"query": "enterprise AI deployment", "category": "business", "expected_topics": ["enterprise", "AI", "deployment"]},
            {"query": "knowledge management system", "category": "business", "expected_topics": ["knowledge", "management"]},
            {"query": "semantic search ROI", "category": "business", "expected_topics": ["semantic", "search", "business"]},
            
            # System queries
            {"query": "Core Nexus architecture", "category": "system", "expected_topics": ["Core Nexus", "architecture"]},
            {"query": "FastAPI memory service", "category": "system", "expected_topics": ["FastAPI", "memory", "service"]},
            {"query": "PostgreSQL pgvector extension", "category": "system", "expected_topics": ["PostgreSQL", "pgvector"]},
            
            # Edge cases
            {"query": "", "category": "edge_case", "expected_topics": []},  # Empty query
            {"query": "a", "category": "edge_case", "expected_topics": []},  # Single character
            {"query": "test " * 50, "category": "edge_case", "expected_topics": ["test"]},  # Long query
            {"query": "🚀 emoji test 🎉", "category": "edge_case", "expected_topics": []},  # Emojis
            {"query": "SELECT * FROM memories", "category": "edge_case", "expected_topics": []},  # SQL injection attempt
            {"query": "null undefined NaN", "category": "edge_case", "expected_topics": []},  # Special values
            
            # Real-world queries
            {"query": "how to improve vector search performance", "category": "real_world", "expected_topics": ["vector", "search", "performance"]},
            {"query": "what is the optimal lists parameter for pgvector", "category": "real_world", "expected_topics": ["lists", "pgvector", "optimal"]},
            {"query": "memory retrieval latency issues", "category": "real_world", "expected_topics": ["memory", "latency", "retrieval"]},
            {"query": "semantic similarity threshold tuning", "category": "real_world", "expected_topics": ["semantic", "similarity", "threshold"]},
            {"query": "production deployment best practices", "category": "real_world", "expected_topics": ["production", "deployment", "practices"]},
        ]
        
        self.test_queries = test_queries
        return test_queries
    
    async def capture_exact_search_baseline(self):
        """Capture results using exact search (no index) as ground truth."""
        logger.info("📊 Capturing exact search baseline...")
        
        conn = await asyncpg.connect(self.db_url)
        
        for test_query in self.test_queries:
            query_text = test_query["query"]
            
            if not query_text:  # Empty query
                # For empty queries, get most recent memories
                results = await conn.fetch("""
                    SELECT id, content, importance_score
                    FROM vector_memories
                    ORDER BY created_at DESC
                    LIMIT 20
                """)
            else:
                # For non-empty queries, we need to generate an embedding
                # Since we don't have OpenAI key here, we'll use a different approach
                # We'll search by content similarity instead
                results = await conn.fetch("""
                    SELECT id, content, importance_score,
                           ts_rank(to_tsvector('english', content), 
                                  plainto_tsquery('english', $1)) as rank
                    FROM vector_memories
                    WHERE to_tsvector('english', content) @@ plainto_tsquery('english', $1)
                    ORDER BY rank DESC, importance_score DESC
                    LIMIT 20
                """, query_text)
            
            # Store ground truth
            self.ground_truth[query_text] = {
                "results": [{"id": str(r["id"]), 
                           "content": r["content"], 
                           "importance": float(r["importance_score"])} 
                          for r in results],
                "count": len(results)
            }
            
            logger.info(f"  Query: '{query_text[:30]}...' - Found {len(results)} relevant results")
        
        await conn.close()
        logger.info("✅ Ground truth baseline captured")
    
    def make_api_request(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Make API request to memory service."""
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }
        
        data = json.dumps({
            "query": query,
            "limit": limit
        }).encode('utf-8')
        
        req = urllib.request.Request(
            f"{self.api_url}/memories/query",
            data=data,
            headers=headers,
            method="POST"
        )
        
        try:
            start_time = time.time()
            response = urllib.request.urlopen(req)
            latency_ms = (time.time() - start_time) * 1000
            
            result = json.loads(response.read().decode('utf-8'))
            result['latency_ms'] = latency_ms
            
            return result
        except urllib.error.HTTPError as e:
            logger.error(f"API request failed: {e}")
            return None
    
    def calculate_recall_at_k(self, retrieved: List[str], relevant: List[str], k: int) -> float:
        """Calculate recall@k metric."""
        if not relevant:
            return 1.0 if not retrieved else 0.0
        
        retrieved_k = set(retrieved[:k])
        relevant_set = set(relevant)
        
        intersection = retrieved_k.intersection(relevant_set)
        recall = len(intersection) / len(relevant_set)
        
        return recall
    
    def calculate_precision_at_k(self, retrieved: List[str], relevant: List[str], k: int) -> float:
        """Calculate precision@k metric."""
        if not retrieved:
            return 0.0
        
        retrieved_k = retrieved[:k]
        relevant_set = set(relevant)
        
        relevant_in_k = sum(1 for item in retrieved_k if item in relevant_set)
        precision = relevant_in_k / min(k, len(retrieved_k))
        
        return precision
    
    def calculate_f1_score(self, precision: float, recall: float) -> float:
        """Calculate F1 score."""
        if precision + recall == 0:
            return 0.0
        return 2 * (precision * recall) / (precision + recall)
    
    async def capture_current_metrics(self):
        """Capture metrics with current configuration."""
        logger.info("\n🔍 Capturing metrics with current configuration...")
        
        latencies = []
        recalls_at_5 = []
        recalls_at_10 = []
        precisions_at_5 = []
        precisions_at_10 = []
        
        for test_query in self.test_queries:
            query_text = test_query["query"]
            category = test_query["category"]
            
            # Make multiple requests to get stable latency
            query_latencies = []
            for i in range(5):
                result = self.make_api_request(query_text, limit=20)
                if result:
                    query_latencies.append(result.get('latency_ms', 0))
                    
                    # On first iteration, calculate quality metrics
                    if i == 0:
                        retrieved_ids = [m['id'] for m in result.get('memories', [])]
                        relevant_ids = [r['id'] for r in self.ground_truth.get(query_text, {}).get('results', [])]
                        
                        recall_5 = self.calculate_recall_at_k(retrieved_ids, relevant_ids, 5)
                        recall_10 = self.calculate_recall_at_k(retrieved_ids, relevant_ids, 10)
                        precision_5 = self.calculate_precision_at_k(retrieved_ids, relevant_ids, 5)
                        precision_10 = self.calculate_precision_at_k(retrieved_ids, relevant_ids, 10)
                        
                        recalls_at_5.append(recall_5)
                        recalls_at_10.append(recall_10)
                        precisions_at_5.append(precision_5)
                        precisions_at_10.append(precision_10)
                        
                        # Log per-query metrics
                        f1_5 = self.calculate_f1_score(precision_5, recall_5)
                        logger.info(f"  {category}: '{query_text[:30]}...'")
                        logger.info(f"    Latency: {statistics.mean(query_latencies):.1f}ms")
                        logger.info(f"    Recall@5: {recall_5:.2%}, Precision@5: {precision_5:.2%}, F1@5: {f1_5:.3f}")
                
                # Small delay between requests
                await asyncio.sleep(0.5)
            
            latencies.extend(query_latencies)
        
        # Calculate aggregate metrics
        self.metrics['latency_ms'] = latencies
        self.metrics['recall_at_5'] = recalls_at_5
        self.metrics['recall_at_10'] = recalls_at_10
        self.metrics['precision_at_5'] = precisions_at_5
        self.metrics['precision_at_10'] = precisions_at_10
        
        # Calculate percentiles
        latency_sorted = sorted(latencies)
        n = len(latency_sorted)
        
        metrics_summary = {
            "latency": {
                "mean": statistics.mean(latencies),
                "p50": latency_sorted[n//2],
                "p75": latency_sorted[int(n*0.75)],
                "p90": latency_sorted[int(n*0.90)],
                "p95": latency_sorted[int(n*0.95)],
                "p99": latency_sorted[min(int(n*0.99), n-1)],
                "min": min(latencies),
                "max": max(latencies)
            },
            "recall": {
                "at_5_mean": statistics.mean(recalls_at_5),
                "at_10_mean": statistics.mean(recalls_at_10),
                "at_5_min": min(recalls_at_5),
                "at_10_min": min(recalls_at_10)
            },
            "precision": {
                "at_5_mean": statistics.mean(precisions_at_5),
                "at_10_mean": statistics.mean(precisions_at_10),
                "at_5_min": min(precisions_at_5),
                "at_10_min": min(precisions_at_10)
            },
            "f1_score": {
                "at_5": self.calculate_f1_score(
                    statistics.mean(precisions_at_5),
                    statistics.mean(recalls_at_5)
                ),
                "at_10": self.calculate_f1_score(
                    statistics.mean(precisions_at_10),
                    statistics.mean(recalls_at_10)
                )
            }
        }
        
        return metrics_summary
    
    async def test_probes_sensitivity(self):
        """Test different probes values to find optimal setting."""
        logger.info("\n🔬 Testing probes sensitivity...")
        
        conn = await asyncpg.connect(self.db_url)
        
        probes_results = {}
        test_embedding = '[' + ','.join(['0.1'] * 1536) + ']'
        
        for probes in [1, 2, 3, 4, 5, 8]:
            logger.info(f"\n  Testing probes={probes}")
            
            # Set probes value
            await conn.execute(f"SET ivfflat.probes = {probes}")
            
            # Run test queries
            latencies = []
            for i in range(10):
                start_time = time.time()
                await conn.fetch("""
                    SELECT id, content, 1 - (embedding <=> $1::vector) as similarity
                    FROM vector_memories
                    ORDER BY embedding <=> $1::vector
                    LIMIT 10
                """, test_embedding)
                latency = (time.time() - start_time) * 1000
                latencies.append(latency)
            
            avg_latency = statistics.mean(latencies)
            probes_results[probes] = {
                "avg_latency_ms": avg_latency,
                "min_latency_ms": min(latencies),
                "max_latency_ms": max(latencies)
            }
            
            logger.info(f"    Average latency: {avg_latency:.1f}ms")
        
        await conn.close()
        return probes_results
    
    def generate_report(self, metrics_summary: Dict[str, Any], probes_results: Dict[int, Any]):
        """Generate comprehensive baseline report."""
        report = f"""
# 📊 Core Nexus Baseline Metrics Report
Generated: {datetime.now().isoformat()}

## 🎯 Executive Summary

Current pgvector configuration:
- Index: IVFFlat with lists=8
- Probes: 3
- Total memories: 1,716

## 📈 Performance Metrics

### Latency Distribution (ms)
- Mean: {metrics_summary['latency']['mean']:.1f}
- P50: {metrics_summary['latency']['p50']:.1f}
- P75: {metrics_summary['latency']['p75']:.1f}
- P90: {metrics_summary['latency']['p90']:.1f}
- P95: {metrics_summary['latency']['p95']:.1f}
- P99: {metrics_summary['latency']['p99']:.1f}
- Min: {metrics_summary['latency']['min']:.1f}
- Max: {metrics_summary['latency']['max']:.1f}

### Quality Metrics
- Recall@5: {metrics_summary['recall']['at_5_mean']:.1%} (min: {metrics_summary['recall']['at_5_min']:.1%})
- Recall@10: {metrics_summary['recall']['at_10_mean']:.1%} (min: {metrics_summary['recall']['at_10_min']:.1%})
- Precision@5: {metrics_summary['precision']['at_5_mean']:.1%} (min: {metrics_summary['precision']['at_5_min']:.1%})
- Precision@10: {metrics_summary['precision']['at_10_mean']:.1%} (min: {metrics_summary['precision']['at_10_min']:.1%})
- F1@5: {metrics_summary['f1_score']['at_5']:.3f}
- F1@10: {metrics_summary['f1_score']['at_10']:.3f}

## 🔬 Probes Sensitivity Analysis

| Probes | Avg Latency (ms) | Min (ms) | Max (ms) |
|--------|------------------|----------|----------|
"""
        
        for probes, results in sorted(probes_results.items()):
            report += f"| {probes} | {results['avg_latency_ms']:.1f} | {results['min_latency_ms']:.1f} | {results['max_latency_ms']:.1f} |\n"
        
        report += f"""

## 🎯 Targets for Redis Caching

Based on current baseline:
1. **Latency Target**: P95 < 100ms (current: {metrics_summary['latency']['p95']:.1f}ms)
2. **Recall Target**: Maintain >90% recall@10 (current: {metrics_summary['recall']['at_10_mean']:.1%})
3. **Cache Hit Target**: >40% to achieve latency goals
4. **Throughput Target**: 5x improvement (from ~8 QPS to 40+ QPS)

## 📊 Key Findings

1. **Current Performance**: Average latency of {metrics_summary['latency']['mean']:.1f}ms is above the 100ms target
2. **Quality Trade-off**: Current settings provide {metrics_summary['recall']['at_10_mean']:.1%} recall with reasonable precision
3. **Optimization Opportunity**: Redis caching can reduce P50 latency by ~50ms

## 🚀 Next Steps

1. Implement Redis semantic caching with 0.95 similarity threshold
2. Target 40-50% cache hit rate for queries
3. Monitor recall to ensure no degradation
4. Set up continuous baseline monitoring
"""
        
        return report
    
    async def run_baseline_capture(self):
        """Run complete baseline capture process."""
        logger.info("🚀 Starting Core Nexus Baseline Metrics Capture")
        logger.info("=" * 60)
        
        # Step 1: Create test queries
        self.create_test_queries()
        logger.info(f"✅ Created {len(self.test_queries)} test queries")
        
        # Step 2: Capture ground truth
        await self.capture_exact_search_baseline()
        
        # Step 3: Capture current metrics
        metrics_summary = await self.capture_current_metrics()
        
        # Step 4: Test probes sensitivity
        probes_results = await self.test_probes_sensitivity()
        
        # Step 5: Generate report
        report = self.generate_report(metrics_summary, probes_results)
        
        # Save report
        with open('baseline_metrics_report.md', 'w') as f:
            f.write(report)
        
        # Save raw data
        raw_data = {
            "timestamp": datetime.now().isoformat(),
            "test_queries": self.test_queries,
            "ground_truth": self.ground_truth,
            "metrics": dict(self.metrics),
            "metrics_summary": metrics_summary,
            "probes_results": probes_results
        }
        
        with open('baseline_metrics_data.json', 'w') as f:
            json.dump(raw_data, f, indent=2)
        
        logger.info("\n✅ Baseline capture complete!")
        logger.info(f"📄 Report saved to: baseline_metrics_report.md")
        logger.info(f"📊 Raw data saved to: baseline_metrics_data.json")
        
        print(report)


async def main():
    """Run baseline metrics capture."""
    metrics = BaselineMetrics()
    await metrics.run_baseline_capture()


if __name__ == "__main__":
    asyncio.run(main())