#!/usr/bin/env python3
"""
Simple Baseline Metrics Capture for Core Nexus Memory Service

A rate-limit aware version that captures essential baseline metrics.
"""

import asyncio
import asyncpg
import json
import time
import statistics
from datetime import datetime
import urllib.request
import urllib.error
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleBaselineMetrics:
    def __init__(self, api_url="https://core-nexus-memory-service.onrender.com", 
                 api_key="dev-key-12345",
                 db_url=None):
        self.api_url = api_url
        self.api_key = api_key
        self.db_url = db_url or (
            "postgresql://nexus_memory_db_user:2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V@"
            "dpg-d12n0np5pdvs73ctmm40-a.ohio-postgres.render.com:5432/nexus_memory_db"
        )
        
    def make_api_request(self, query: str, limit: int = 10) -> dict:
        """Make API request with rate limit handling."""
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
        
        max_retries = 3
        for retry in range(max_retries):
            try:
                start_time = time.time()
                response = urllib.request.urlopen(req)
                latency_ms = (time.time() - start_time) * 1000
                
                result = json.loads(response.read().decode('utf-8'))
                result['latency_ms'] = latency_ms
                
                return result
            except urllib.error.HTTPError as e:
                if e.code == 429:  # Rate limit
                    wait_time = min(2 ** retry, 10)  # Exponential backoff
                    logger.warning(f"Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"API request failed: {e}")
                    return None
        
        return None
    
    async def test_probes_latency(self):
        """Test latency with different probes settings."""
        logger.info("\n🔬 Testing probes impact on latency...")
        
        conn = await asyncpg.connect(self.db_url)
        results = {}
        
        # Use a real embedding from the database for realistic testing
        sample_embedding = await conn.fetchval("""
            SELECT embedding::text
            FROM vector_memories
            WHERE embedding IS NOT NULL
            LIMIT 1
        """)
        
        if not sample_embedding:
            logger.error("No embeddings found in database")
            await conn.close()
            return results
        
        for probes in [1, 2, 3, 4, 5]:
            logger.info(f"Testing probes={probes}")
            
            # Set probes value
            await conn.execute(f"SET ivfflat.probes = {probes}")
            
            # Run 5 test queries
            latencies = []
            for i in range(5):
                start_time = time.time()
                await conn.fetch("""
                    SELECT id, content
                    FROM vector_memories
                    ORDER BY embedding <=> $1::vector
                    LIMIT 10
                """, sample_embedding)
                latency = (time.time() - start_time) * 1000
                latencies.append(latency)
                
                # Small delay to avoid overloading
                await asyncio.sleep(0.1)
            
            avg_latency = statistics.mean(latencies)
            results[probes] = {
                "avg_latency_ms": avg_latency,
                "min_latency_ms": min(latencies),
                "max_latency_ms": max(latencies),
                "samples": len(latencies)
            }
            
            logger.info(f"  Probes={probes}: {avg_latency:.1f}ms average")
        
        await conn.close()
        return results
    
    async def capture_api_baseline(self):
        """Capture baseline metrics through API with rate limit awareness."""
        logger.info("\n📊 Capturing API baseline metrics...")
        
        # Small set of representative queries
        test_queries = [
            "pgvector optimization",
            "memory service performance", 
            "Core Nexus architecture",
            "vector search",
            "",  # Empty query
            "test query latency",
            "production deployment"
        ]
        
        latencies = []
        results_counts = []
        
        for i, query in enumerate(test_queries):
            logger.info(f"Testing query {i+1}/{len(test_queries)}: '{query[:30]}...'")
            
            # Test each query 3 times
            query_latencies = []
            for j in range(3):
                result = self.make_api_request(query, limit=10)
                
                if result:
                    query_latencies.append(result['latency_ms'])
                    if j == 0:  # Count results only once
                        results_counts.append(len(result.get('memories', [])))
                
                # Rate limit aware delay
                await asyncio.sleep(2)  # 2 seconds between requests
            
            if query_latencies:
                avg_latency = statistics.mean(query_latencies)
                latencies.extend(query_latencies)
                logger.info(f"  Average latency: {avg_latency:.1f}ms")
        
        # Calculate statistics
        if latencies:
            latency_sorted = sorted(latencies)
            n = len(latency_sorted)
            
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "total_queries": len(test_queries) * 3,
                "successful_queries": len(latencies),
                "latency": {
                    "mean": statistics.mean(latencies),
                    "median": statistics.median(latencies),
                    "p90": latency_sorted[int(n*0.90)] if n > 0 else 0,
                    "p95": latency_sorted[int(n*0.95)] if n > 0 else 0,
                    "min": min(latencies),
                    "max": max(latencies)
                },
                "results": {
                    "avg_results_per_query": statistics.mean(results_counts) if results_counts else 0,
                    "min_results": min(results_counts) if results_counts else 0,
                    "max_results": max(results_counts) if results_counts else 0
                }
            }
            
            return metrics
        
        return None
    
    async def capture_db_stats(self):
        """Capture database statistics."""
        logger.info("\n📈 Capturing database statistics...")
        
        conn = await asyncpg.connect(self.db_url)
        
        # Get basic stats
        total_memories = await conn.fetchval("SELECT COUNT(*) FROM vector_memories")
        
        # Get index info
        index_info = await conn.fetch("""
            SELECT 
                indexname,
                pg_size_pretty(pg_relation_size(indexname::regclass)) as size
            FROM pg_indexes 
            WHERE tablename = 'vector_memories'
            AND indexname LIKE '%embedding%'
        """)
        
        # Get current settings
        current_probes = await conn.fetchval("SHOW ivfflat.probes")
        
        await conn.close()
        
        return {
            "total_memories": total_memories,
            "indexes": [{"name": idx['indexname'], "size": idx['size']} for idx in index_info],
            "current_probes": int(current_probes)
        }
    
    def generate_simple_report(self, api_metrics, probes_results, db_stats):
        """Generate a simple baseline report."""
        report = f"""
# 📊 Core Nexus Simple Baseline Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 🗄️ Database Status
- Total memories: {db_stats['total_memories']:,}
- Current probes setting: {db_stats['current_probes']}
- Indexes: {len(db_stats['indexes'])}

## 📈 Current Performance (API)
- Average latency: {api_metrics['latency']['mean']:.1f}ms
- Median latency: {api_metrics['latency']['median']:.1f}ms
- P90 latency: {api_metrics['latency']['p90']:.1f}ms
- P95 latency: {api_metrics['latency']['p95']:.1f}ms
- Min/Max: {api_metrics['latency']['min']:.1f}ms / {api_metrics['latency']['max']:.1f}ms

## 🔬 Probes Sensitivity (Direct DB)
| Probes | Avg Latency | Min | Max |
|--------|-------------|-----|-----|
"""
        
        for probes, results in sorted(probes_results.items()):
            report += f"| {probes} | {results['avg_latency_ms']:.1f}ms | {results['min_latency_ms']:.1f}ms | {results['max_latency_ms']:.1f}ms |\n"
        
        # Find optimal probes based on latency
        optimal_probes = 3  # Current setting
        if probes_results:
            # Find probes with best latency under 150ms
            for p in sorted(probes_results.keys()):
                if probes_results[p]['avg_latency_ms'] < 150:
                    optimal_probes = p
                    break
        
        report += f"""

## 🎯 Key Findings

1. **Current State**:
   - API latency averaging {api_metrics['latency']['mean']:.0f}ms
   - Using probes={db_stats['current_probes']} (optimal: {optimal_probes})
   - {api_metrics['successful_queries']} successful queries tested

2. **Performance Target**:
   - Current P95: {api_metrics['latency']['p95']:.0f}ms
   - Target: <100ms
   - Gap: {max(0, api_metrics['latency']['p95'] - 100):.0f}ms improvement needed

3. **Next Steps**:
   - Implement Redis caching to reduce P50 by ~50%
   - Target 40% cache hit rate
   - Expected P95 after caching: ~{api_metrics['latency']['p95'] * 0.6:.0f}ms

## 📝 Baseline Established
This baseline will be used to measure the effectiveness of Redis caching implementation.
"""
        
        return report
    
    async def run_simple_baseline(self):
        """Run simplified baseline capture."""
        logger.info("🚀 Starting Simple Baseline Capture")
        logger.info("=" * 60)
        
        try:
            # 1. Capture DB stats
            db_stats = await self.capture_db_stats()
            logger.info(f"✅ Database has {db_stats['total_memories']:,} memories")
            
            # 2. Test probes sensitivity
            probes_results = await self.test_probes_latency()
            
            # 3. Capture API baseline (rate-limit aware)
            api_metrics = await self.capture_api_baseline()
            
            if api_metrics:
                # 4. Generate report
                report = self.generate_simple_report(api_metrics, probes_results, db_stats)
                
                # Save report
                with open('simple_baseline_report.md', 'w') as f:
                    f.write(report)
                
                # Save raw data
                raw_data = {
                    "timestamp": datetime.now().isoformat(),
                    "api_metrics": api_metrics,
                    "probes_results": probes_results,
                    "db_stats": db_stats
                }
                
                with open('simple_baseline_data.json', 'w') as f:
                    json.dump(raw_data, f, indent=2)
                
                logger.info("\n✅ Baseline capture complete!")
                logger.info("📄 Report saved to: simple_baseline_report.md")
                logger.info("📊 Data saved to: simple_baseline_data.json")
                
                print(report)
            else:
                logger.error("Failed to capture API metrics")
                
        except Exception as e:
            logger.error(f"Baseline capture failed: {e}")
            raise


async def main():
    """Run simple baseline metrics capture."""
    metrics = SimpleBaselineMetrics()
    await metrics.run_simple_baseline()


if __name__ == "__main__":
    asyncio.run(main())