#!/usr/bin/env python3
"""
Apply PGVector Performance Optimizations
Implements the comprehensive optimization plan from research.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Add the memory service to the path
sys.path.append(str(Path(__file__).parent / "python" / "memory_service" / "src"))

import asyncpg
from memory_service.config import DatabaseConfig
from memory_service.performance_monitor import VectorPerformanceMonitor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def connect_to_database():
    """Connect to the PostgreSQL database."""
    try:
        # Use environment variables or config
        host = os.getenv("PGVECTOR_HOST", DatabaseConfig.HOST)
        port = os.getenv("PGVECTOR_PORT", DatabaseConfig.PORT)
        database = os.getenv("PGVECTOR_DATABASE", DatabaseConfig.DATABASE)
        user = os.getenv("PGVECTOR_USER", DatabaseConfig.USER)
        password = os.getenv("PGVECTOR_PASSWORD", DatabaseConfig.PASSWORD)
        
        if not password:
            logger.error("PGVECTOR_PASSWORD environment variable must be set")
            return None
            
        conn_str = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        
        # Create connection pool with optimized settings
        pool = await asyncpg.create_pool(
            conn_str,
            min_size=5,
            max_size=20,
            command_timeout=30,
            server_settings={
                'jit': 'on',
                'work_mem': '32MB',
                'statement_timeout': '30s'
            }
        )
        
        logger.info("Connected to PostgreSQL database")
        return pool
        
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return None


async def run_migration(pool: asyncpg.Pool, migration_file: str):
    """Run a migration file."""
    logger.info(f"Running migration: {migration_file}")
    
    try:
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        async with pool.acquire() as conn:
            # Split the migration into individual statements
            # (PostgreSQL doesn't support multiple statements in one execute)
            statements = migration_sql.split(';')
            
            for statement in statements:
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    try:
                        await conn.execute(statement)
                    except Exception as e:
                        if "already exists" in str(e).lower():
                            logger.warning(f"Skipping existing object: {e}")
                        else:
                            logger.error(f"Migration statement failed: {e}")
                            logger.error(f"Statement: {statement[:100]}...")
        
        logger.info(f"Migration {migration_file} completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Migration {migration_file} failed: {e}")
        return False


async def benchmark_current_performance(pool: asyncpg.Pool):
    """Benchmark current performance before and after optimizations."""
    logger.info("Running performance benchmark...")
    
    try:
        monitor = VectorPerformanceMonitor(pool, "vector_memories")
        results = await monitor.run_comprehensive_benchmark(
            num_queries=50,
            concurrent_queries=10
        )
        
        # Save results
        timestamp = int(results["timestamp"])
        results_file = f"performance_results_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        # Print summary
        summary = results.get("summary", {})
        key_metrics = summary.get("key_metrics", {})
        
        logger.info("=== PERFORMANCE BENCHMARK RESULTS ===")
        logger.info(f"Performance Grade: {summary.get('performance_grade', 'Unknown')}")
        logger.info(f"P95 Latency: {key_metrics.get('p95_latency_ms', 0):.1f}ms (target: <20ms)")
        logger.info(f"Throughput: {key_metrics.get('throughput_qps', 0):.1f} QPS (target: >100 QPS)")
        logger.info(f"Error Rate: {key_metrics.get('error_rate_percent', 0):.1f}% (target: <1%)")
        
        # Print recommendations
        recommendations = summary.get("recommendations", [])
        if recommendations:
            logger.info("Recommendations:")
            for i, rec in enumerate(recommendations, 1):
                logger.info(f"  {i}. {rec}")
        
        logger.info(f"Full results saved to: {results_file}")
        return results
        
    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        return None


async def verify_optimizations(pool: asyncpg.Pool):
    """Verify that optimizations have been applied correctly."""
    logger.info("Verifying optimizations...")
    
    try:
        async with pool.acquire() as conn:
            # Check HNSW index exists
            hnsw_index = await conn.fetchval("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'vector_memories' 
                AND indexdef LIKE '%hnsw%'
                LIMIT 1
            """)
            
            if hnsw_index:
                logger.info(f"✅ HNSW index found: {hnsw_index}")
            else:
                logger.warning("❌ HNSW index not found")
            
            # Check HNSW parameters
            try:
                ef_search = await conn.fetchval("SHOW hnsw.ef_search")
                logger.info(f"✅ HNSW ef_search: {ef_search}")
            except:
                logger.warning("❌ Could not retrieve HNSW ef_search parameter")
            
            # Check work_mem setting
            work_mem = await conn.fetchval("SHOW work_mem")
            logger.info(f"✅ work_mem: {work_mem}")
            
            # Check table statistics
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as vector_count,
                    pg_size_pretty(pg_total_relation_size('vector_memories')) as table_size
                FROM vector_memories
            """)
            
            if stats:
                logger.info(f"✅ Table stats: {stats['vector_count']} vectors, {stats['table_size']}")
            
            logger.info("Optimization verification completed")
            return True
            
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False


async def main():
    """Main optimization application workflow."""
    logger.info("=== PGVector Performance Optimization Tool ===")
    logger.info("Based on 2025 research for sub-20ms query latency")
    
    # Connect to database
    pool = await connect_to_database()
    if not pool:
        logger.error("Failed to connect to database. Exiting.")
        return 1
    
    try:
        # 1. Benchmark current performance
        logger.info("\n1. Benchmarking current performance...")
        baseline_results = await benchmark_current_performance(pool)
        
        # 2. Apply PostgreSQL optimizations
        logger.info("\n2. Applying PostgreSQL optimizations...")
        postgres_migration = "python/memory_service/migrations/003_optimize_postgresql_for_vectors.sql"
        if os.path.exists(postgres_migration):
            success = await run_migration(pool, postgres_migration)
            if not success:
                logger.warning("PostgreSQL optimization migration failed")
        else:
            logger.warning(f"Migration file not found: {postgres_migration}")
        
        # 3. Apply HNSW optimizations
        logger.info("\n3. Applying HNSW index optimizations...")
        hnsw_migration = "python/memory_service/migrations/004_optimize_hnsw_parameters.sql"
        if os.path.exists(hnsw_migration):
            success = await run_migration(pool, hnsw_migration)
            if not success:
                logger.warning("HNSW optimization migration failed")
        else:
            logger.warning(f"Migration file not found: {hnsw_migration}")
        
        # 4. Verify optimizations
        logger.info("\n4. Verifying optimizations...")
        await verify_optimizations(pool)
        
        # 5. Benchmark optimized performance
        logger.info("\n5. Benchmarking optimized performance...")
        optimized_results = await benchmark_current_performance(pool)
        
        # 6. Compare results
        if baseline_results and optimized_results:
            logger.info("\n=== PERFORMANCE COMPARISON ===")
            
            baseline_p95 = baseline_results.get("summary", {}).get("key_metrics", {}).get("p95_latency_ms", 0)
            optimized_p95 = optimized_results.get("summary", {}).get("key_metrics", {}).get("p95_latency_ms", 0)
            
            baseline_qps = baseline_results.get("summary", {}).get("key_metrics", {}).get("throughput_qps", 0)
            optimized_qps = optimized_results.get("summary", {}).get("key_metrics", {}).get("throughput_qps", 0)
            
            if baseline_p95 > 0:
                latency_improvement = ((baseline_p95 - optimized_p95) / baseline_p95) * 100
                logger.info(f"P95 Latency: {baseline_p95:.1f}ms → {optimized_p95:.1f}ms ({latency_improvement:+.1f}%)")
            
            if baseline_qps > 0:
                throughput_improvement = ((optimized_qps - baseline_qps) / baseline_qps) * 100
                logger.info(f"Throughput: {baseline_qps:.1f} → {optimized_qps:.1f} QPS ({throughput_improvement:+.1f}%)")
            
            # Check if targets are met
            if optimized_p95 < 20:
                logger.info("🎯 P95 LATENCY TARGET MET (<20ms)!")
            else:
                logger.info(f"⚠️  P95 latency still above target: {optimized_p95:.1f}ms (target: <20ms)")
            
            if optimized_qps > 100:
                logger.info("🎯 THROUGHPUT TARGET MET (>100 QPS)!")
            else:
                logger.info(f"⚠️  Throughput still below target: {optimized_qps:.1f} QPS (target: >100 QPS)")
        
        logger.info("\n=== OPTIMIZATION COMPLETE ===")
        logger.info("Next steps:")
        logger.info("1. Monitor performance in production")
        logger.info("2. Consider pgvectorscale for further improvements")
        logger.info("3. Implement query result caching")
        logger.info("4. Tune ef_search parameter based on workload")
        
        return 0
        
    except Exception as e:
        logger.error(f"Optimization process failed: {e}")
        return 1
        
    finally:
        if pool:
            await pool.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)