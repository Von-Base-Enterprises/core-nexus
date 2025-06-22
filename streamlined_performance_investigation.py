#!/usr/bin/env python3
"""
Streamlined Performance Investigation

Focused investigation of the performance discrepancy with corrected SQL queries.
"""

import asyncio
import asyncpg
import json
import logging
import numpy as np
import os
import sys
import time
import statistics
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StreamlinedInvestigator:
    """Streamlined performance investigator with corrected queries."""
    
    def __init__(self):
        """Initialize the investigator."""
        self.connection_pool = None
        
        # Database configuration
        self.db_config = {
            'host': os.getenv('PGVECTOR_HOST', 'dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com'),
            'port': int(os.getenv('PGVECTOR_PORT', '5432')),
            'database': os.getenv('PGVECTOR_DATABASE', 'nexus_memory_db'),
            'user': os.getenv('PGVECTOR_USER', 'nexus_memory_db_user'),
            'password': os.getenv('PGVECTOR_PASSWORD')
        }
        
        if not self.db_config['password']:
            raise ValueError("PGVECTOR_PASSWORD environment variable must be set")
    
    async def connect_to_database(self):
        """Connect to the production database."""
        try:
            logger.info("🔌 Connecting to production database...")
            
            conn_str = (
                f"postgresql://{self.db_config['user']}:{self.db_config['password']}@"
                f"{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
            )
            
            self.connection_pool = await asyncpg.create_pool(
                conn_str,
                min_size=2,
                max_size=5,
                command_timeout=60
            )
            
            async with self.connection_pool.acquire() as conn:
                db_version = await conn.fetchval("SELECT version()")
                logger.info(f"✅ Connected to PostgreSQL: {db_version.split()[1]}")
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            raise
    
    async def check_migration_status(self) -> Dict[str, Any]:
        """Check migration status and data availability."""
        logger.info("📊 Checking migration status...")
        
        async with self.connection_pool.acquire() as conn:
            try:
                # Get vector counts
                original_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM vector_memories WHERE embedding IS NOT NULL"
                )
                
                optimized_migrated = await conn.fetchval(
                    "SELECT COUNT(*) FROM vector_memories_optimized WHERE migration_status IN ('migrated', 'verified')"
                )
                
                # Get sample of dimensions from optimized vectors
                sample_optimized = await conn.fetch("""
                    SELECT id, content, LENGTH(content) as content_length
                    FROM vector_memories_optimized 
                    WHERE migration_status IN ('migrated', 'verified')
                    LIMIT 5
                """)
                
                migration_status = {
                    'original_vectors': original_count,
                    'optimized_migrated': optimized_migrated,
                    'migration_percentage': (optimized_migrated / original_count * 100) if original_count > 0 else 0,
                    'sample_optimized_vectors': [dict(row) for row in sample_optimized]
                }
                
                logger.info(f"✅ Migration: {optimized_migrated}/{original_count} vectors ({migration_status['migration_percentage']:.1f}%)")
                
                return migration_status
                
            except Exception as e:
                logger.error(f"❌ Failed to check migration status: {e}")
                raise
    
    async def test_hnsw_parameters(self) -> Dict[str, Any]:
        """Test different HNSW parameters for optimization."""
        logger.info("🔧 Testing HNSW parameters...")
        
        async with self.connection_pool.acquire() as conn:
            try:
                # Create test vector
                test_vector = [0.1] * 1536
                test_vector_str = '[' + ','.join(map(str, test_vector)) + ']'
                
                # Test different ef_search values
                ef_search_tests = []
                
                for ef_search in [10, 20, 40, 64, 100]:
                    try:
                        # Set ef_search parameter
                        await conn.execute(f"SET hnsw.ef_search = {ef_search}")
                        
                        # Run multiple queries to get average
                        times = []
                        for _ in range(5):
                            start_time = time.perf_counter()
                            results = await conn.fetch("""
                                SELECT id, embedding <=> $1::vector as distance
                                FROM vector_memories_optimized
                                WHERE migration_status IN ('migrated', 'verified')
                                ORDER BY embedding <=> $1::vector
                                LIMIT 10
                            """, test_vector_str)
                            latency_ms = (time.perf_counter() - start_time) * 1000
                            times.append(latency_ms)
                        
                        avg_latency = statistics.mean(times)
                        ef_search_tests.append({
                            'ef_search': ef_search,
                            'avg_latency_ms': avg_latency,
                            'results_count': len(results)
                        })
                        
                        logger.info(f"   ef_search={ef_search}: {avg_latency:.2f}ms avg")
                        
                    except Exception as e:
                        logger.warning(f"⚠️ ef_search={ef_search} test failed: {e}")
                
                # Find optimal ef_search
                optimal_test = min(ef_search_tests, key=lambda x: x['avg_latency_ms']) if ef_search_tests else None
                
                # Reset to default
                await conn.execute("RESET hnsw.ef_search")
                
                return {
                    'ef_search_tests': ef_search_tests,
                    'optimal_ef_search': optimal_test['ef_search'] if optimal_test else None,
                    'optimal_latency_ms': optimal_test['avg_latency_ms'] if optimal_test else None
                }
                
            except Exception as e:
                logger.error(f"❌ HNSW parameter testing failed: {e}")
                raise
    
    async def comprehensive_performance_test(self) -> Dict[str, Any]:
        """Run comprehensive performance comparison."""
        logger.info("🧪 Running comprehensive performance test...")
        
        async with self.connection_pool.acquire() as conn:
            try:
                # Create diverse test vectors
                test_vectors = []
                
                # Random normalized vectors
                for i in range(3):
                    random_vector = np.random.normal(0, 0.1, 1536).astype(np.float32)
                    random_vector = random_vector / np.linalg.norm(random_vector)
                    test_vectors.append('[' + ','.join(map(str, random_vector)) + ']')
                
                # Get some actual production vectors for realistic tests
                try:
                    actual_vectors = await conn.fetch("""
                        SELECT embedding
                        FROM vector_memories_optimized
                        WHERE migration_status IN ('migrated', 'verified')
                        ORDER BY RANDOM()
                        LIMIT 3
                    """)
                    
                    for row in actual_vectors:
                        if row['embedding']:
                            embedding_list = list(row['embedding'])
                            test_vectors.append('[' + ','.join(map(str, embedding_list)) + ']')
                            
                except Exception as e:
                    logger.warning(f"⚠️ Could not get actual vectors: {e}")
                
                # Test different result set sizes
                test_scenarios = [
                    {'name': 'small', 'limit': 5, 'iterations': 15},
                    {'name': 'medium', 'limit': 20, 'iterations': 10},
                    {'name': 'large', 'limit': 50, 'iterations': 5}
                ]
                
                results = {}
                
                for scenario in test_scenarios:
                    logger.info(f"🔬 Testing {scenario['name']} queries (limit={scenario['limit']})...")
                    
                    original_times = []
                    optimized_times = []
                    
                    for iteration in range(scenario['iterations']):
                        test_vector = test_vectors[iteration % len(test_vectors)]
                        
                        # Test original table
                        try:
                            start_time = time.perf_counter()
                            original_results = await conn.fetch("""
                                SELECT id, embedding <=> $1::vector as distance
                                FROM vector_memories
                                WHERE embedding IS NOT NULL
                                ORDER BY embedding <=> $1::vector
                                LIMIT $2
                            """, test_vector, scenario['limit'])
                            original_time = (time.perf_counter() - start_time) * 1000
                            original_times.append(original_time)
                            
                        except Exception as e:
                            logger.warning(f"⚠️ Original query failed: {e}")
                        
                        # Test optimized table
                        try:
                            start_time = time.perf_counter()
                            optimized_results = await conn.fetch("""
                                SELECT id, embedding <=> $1::vector as distance
                                FROM vector_memories_optimized
                                WHERE migration_status IN ('migrated', 'verified')
                                ORDER BY embedding <=> $1::vector
                                LIMIT $2
                            """, test_vector, scenario['limit'])
                            optimized_time = (time.perf_counter() - start_time) * 1000
                            optimized_times.append(optimized_time)
                            
                        except Exception as e:
                            logger.warning(f"⚠️ Optimized query failed: {e}")
                    
                    # Calculate scenario results
                    if original_times and optimized_times:
                        avg_improvement = ((statistics.mean(original_times) - statistics.mean(optimized_times)) 
                                         / statistics.mean(original_times) * 100)
                        
                        results[scenario['name']] = {
                            'limit': scenario['limit'],
                            'original_avg_ms': statistics.mean(original_times),
                            'optimized_avg_ms': statistics.mean(optimized_times),
                            'improvement_percent': avg_improvement,
                            'speedup_factor': statistics.mean(original_times) / statistics.mean(optimized_times),
                            'original_queries': len(original_times),
                            'optimized_queries': len(optimized_times)
                        }
                        
                        logger.info(f"   📊 {scenario['name']}: {avg_improvement:.1f}% improvement")
                
                return results
                
            except Exception as e:
                logger.error(f"❌ Comprehensive performance test failed: {e}")
                raise
    
    async def apply_optimizations(self, optimal_ef_search: int = None) -> Dict[str, Any]:
        """Apply performance optimizations."""
        logger.info("🔧 Applying performance optimizations...")
        
        async with self.connection_pool.acquire() as conn:
            try:
                optimization_results = {}
                
                # Get baseline performance
                test_vector = [0.1] * 1536
                test_vector_str = '[' + ','.join(map(str, test_vector)) + ']'
                
                # Baseline test
                start_time = time.perf_counter()
                baseline_results = await conn.fetch("""
                    SELECT id, embedding <=> $1::vector as distance
                    FROM vector_memories_optimized
                    WHERE migration_status IN ('migrated', 'verified')
                    ORDER BY embedding <=> $1::vector
                    LIMIT 20
                """, test_vector_str)
                baseline_latency = (time.perf_counter() - start_time) * 1000
                
                optimization_results['baseline_latency_ms'] = baseline_latency
                
                # Apply optimal ef_search if available
                if optimal_ef_search:
                    logger.info(f"🔧 Applying optimal ef_search = {optimal_ef_search}")
                    await conn.execute(f"SET hnsw.ef_search = {optimal_ef_search}")
                    
                    # Test optimized performance
                    optimized_times = []
                    for _ in range(5):
                        start_time = time.perf_counter()
                        results = await conn.fetch("""
                            SELECT id, embedding <=> $1::vector as distance
                            FROM vector_memories_optimized
                            WHERE migration_status IN ('migrated', 'verified')
                            ORDER BY embedding <=> $1::vector
                            LIMIT 20
                        """, test_vector_str)
                        optimized_times.append((time.perf_counter() - start_time) * 1000)
                    
                    optimized_latency = statistics.mean(optimized_times)
                    improvement = ((baseline_latency - optimized_latency) / baseline_latency * 100)
                    
                    optimization_results.update({
                        'optimized_latency_ms': optimized_latency,
                        'improvement_percent': improvement,
                        'ef_search_applied': optimal_ef_search
                    })
                    
                    logger.info(f"✅ Optimization: {improvement:.1f}% improvement with ef_search={optimal_ef_search}")
                
                return optimization_results
                
            except Exception as e:
                logger.error(f"❌ Optimization application failed: {e}")
                raise
    
    async def final_validation_test(self) -> Dict[str, Any]:
        """Run final large-scale validation test."""
        logger.info("🏁 Running final validation test...")
        
        async with self.connection_pool.acquire() as conn:
            try:
                # Large-scale test with 30 queries
                test_queries = 30
                test_vector = [0.1] * 1536
                test_vector_str = '[' + ','.join(map(str, test_vector)) + ']'
                
                # Test original table
                logger.info("   Testing original table...")
                original_times = []
                for i in range(test_queries):
                    start_time = time.perf_counter()
                    results = await conn.fetch("""
                        SELECT id, embedding <=> $1::vector as distance
                        FROM vector_memories
                        WHERE embedding IS NOT NULL
                        ORDER BY embedding <=> $1::vector
                        LIMIT 10
                    """, test_vector_str)
                    latency = (time.perf_counter() - start_time) * 1000
                    original_times.append(latency)
                
                # Test optimized table
                logger.info("   Testing optimized table...")
                optimized_times = []
                for i in range(test_queries):
                    start_time = time.perf_counter()
                    results = await conn.fetch("""
                        SELECT id, embedding <=> $1::vector as distance
                        FROM vector_memories_optimized
                        WHERE migration_status IN ('migrated', 'verified')
                        ORDER BY embedding <=> $1::vector
                        LIMIT 10
                    """, test_vector_str)
                    latency = (time.perf_counter() - start_time) * 1000
                    optimized_times.append(latency)
                
                # Calculate comprehensive statistics
                avg_improvement = ((statistics.mean(original_times) - statistics.mean(optimized_times)) 
                                 / statistics.mean(original_times) * 100)
                
                p95_original = sorted(original_times)[int(0.95 * len(original_times))]
                p95_optimized = sorted(optimized_times)[int(0.95 * len(optimized_times))]
                p95_improvement = ((p95_original - p95_optimized) / p95_original * 100)
                
                validation_results = {
                    'test_queries': test_queries,
                    'original_table': {
                        'avg_latency_ms': statistics.mean(original_times),
                        'p95_latency_ms': p95_original,
                        'min_latency_ms': min(original_times),
                        'max_latency_ms': max(original_times)
                    },
                    'optimized_table': {
                        'avg_latency_ms': statistics.mean(optimized_times),
                        'p95_latency_ms': p95_optimized,
                        'min_latency_ms': min(optimized_times),
                        'max_latency_ms': max(optimized_times)
                    },
                    'performance_metrics': {
                        'avg_improvement_percent': avg_improvement,
                        'p95_improvement_percent': p95_improvement,
                        'speedup_factor': statistics.mean(original_times) / statistics.mean(optimized_times)
                    }
                }
                
                logger.info(f"✅ Final validation: {avg_improvement:.1f}% avg improvement")
                
                return validation_results
                
            except Exception as e:
                logger.error(f"❌ Final validation test failed: {e}")
                raise
    
    async def run_investigation(self) -> Dict[str, Any]:
        """Run complete streamlined investigation."""
        start_time = time.time()
        logger.info("🚀 Starting streamlined performance investigation...")
        
        try:
            await self.connect_to_database()
            
            # Phase 1: Status and Analysis
            logger.info("\n📊 PHASE 1: MIGRATION STATUS & ANALYSIS")
            migration_status = await self.check_migration_status()
            
            # Phase 2: HNSW Optimization
            logger.info("\n🔧 PHASE 2: HNSW PARAMETER OPTIMIZATION")
            hnsw_tests = await self.test_hnsw_parameters()
            
            # Phase 3: Performance Testing
            logger.info("\n🧪 PHASE 3: COMPREHENSIVE PERFORMANCE TESTING")
            perf_tests = await self.comprehensive_performance_test()
            
            # Phase 4: Apply Optimizations
            logger.info("\n⚙️ PHASE 4: APPLYING OPTIMIZATIONS")
            optimizations = await self.apply_optimizations(hnsw_tests.get('optimal_ef_search'))
            
            # Phase 5: Final Validation
            logger.info("\n🏁 PHASE 5: FINAL VALIDATION")
            final_validation = await self.final_validation_test()
            
            # Generate summary
            summary = self._generate_summary(migration_status, hnsw_tests, perf_tests, optimizations, final_validation)
            
            results = {
                'timestamp': datetime.now().isoformat(),
                'duration_seconds': time.time() - start_time,
                'migration_status': migration_status,
                'hnsw_optimization': hnsw_tests,
                'performance_tests': perf_tests,
                'optimizations_applied': optimizations,
                'final_validation': final_validation,
                'executive_summary': summary
            }
            
            logger.info(f"🎉 Investigation completed in {time.time() - start_time:.1f} seconds")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Investigation failed: {e}")
            raise
        finally:
            if self.connection_pool:
                await self.connection_pool.close()
    
    def _generate_summary(self, migration, hnsw, perf_tests, optimizations, final) -> Dict[str, Any]:
        """Generate executive summary."""
        
        migration_complete = migration['migration_percentage'] >= 80
        final_improvement = final['performance_metrics']['avg_improvement_percent']
        
        # Determine status
        if final_improvement > 70:
            status = "EXCELLENT"
            recommendation = "DEPLOY IMMEDIATELY"
        elif final_improvement > 40:
            status = "GOOD" 
            recommendation = "DEPLOY WITH MONITORING"
        elif final_improvement > 10:
            status = "MODERATE"
            recommendation = "PROCEED WITH CAUTION"
        else:
            status = "NEEDS_IMPROVEMENT"
            recommendation = "INVESTIGATE FURTHER"
        
        return {
            'status': status,
            'recommendation': recommendation,
            'final_performance_improvement': final_improvement,
            'migration_completion_percent': migration['migration_percentage'],
            'migration_complete': migration_complete,
            'hnsw_optimized': hnsw.get('optimal_ef_search') is not None,
            'key_findings': [
                f"Migration {migration['migration_percentage']:.1f}% complete",
                f"Final performance improvement: {final_improvement:.1f}%",
                f"HNSW optimization: {optimizations.get('improvement_percent', 0):.1f}% additional improvement"
            ]
        }

async def main():
    """Main execution."""
    print("🔍 Streamlined Performance Investigation")
    print("=" * 45)
    print("Investigating and Resolving Performance Issues")
    print()
    
    try:
        investigator = StreamlinedInvestigator()
        results = await investigator.run_investigation()
        
        # Print results
        print("\n" + "="*50)
        print("🏆 INVESTIGATION RESULTS")
        print("="*50)
        
        summary = results['executive_summary']
        migration = results['migration_status']
        final = results['final_validation']
        
        print(f"📊 EXECUTIVE SUMMARY")
        print("=" * 25)
        print(f"✅ Status: {summary['status']}")
        print(f"✅ Recommendation: {summary['recommendation']}")
        print(f"✅ Migration Progress: {summary['migration_completion_percent']:.1f}%")
        print(f"✅ Final Performance: {summary['final_performance_improvement']:.1f}% improvement")
        
        print(f"\n📈 PERFORMANCE COMPARISON")
        print("=" * 30)
        orig = final['original_table']
        opt = final['optimized_table']
        metrics = final['performance_metrics']
        
        print(f"🔍 Original Table:")
        print(f"   Average: {orig['avg_latency_ms']:.2f}ms")
        print(f"   P95: {orig['p95_latency_ms']:.2f}ms")
        
        print(f"\n🔍 Optimized Table:")
        print(f"   Average: {opt['avg_latency_ms']:.2f}ms")
        print(f"   P95: {opt['p95_latency_ms']:.2f}ms")
        
        print(f"\n🚀 IMPROVEMENTS")
        print("=" * 20)
        print(f"📈 Average: {metrics['avg_improvement_percent']:.1f}%")
        print(f"📈 P95: {metrics['p95_improvement_percent']:.1f}%")
        print(f"📈 Speedup: {metrics['speedup_factor']:.2f}x")
        
        if 'hnsw_optimization' in results and results['hnsw_optimization'].get('optimal_ef_search'):
            print(f"\n🔧 HNSW OPTIMIZATION")
            print("=" * 25)
            hnsw = results['hnsw_optimization']
            print(f"✅ Optimal ef_search: {hnsw['optimal_ef_search']}")
            print(f"✅ Optimized latency: {hnsw['optimal_latency_ms']:.2f}ms")
        
        print(f"\n🎯 KEY FINDINGS")
        print("=" * 20)
        for i, finding in enumerate(summary['key_findings'], 1):
            print(f"{i}. {finding}")
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"performance_investigation_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Full results saved to: {filename}")
        
        if summary['status'] in ['EXCELLENT', 'GOOD']:
            print(f"\n🚀 CONCLUSION: PERFORMANCE ISSUE RESOLVED!")
            print(f"✅ Ready for production deployment")
        else:
            print(f"\n⚠️ CONCLUSION: FURTHER INVESTIGATION NEEDED")
            print(f"❌ Performance needs additional optimization")
        
    except Exception as e:
        logger.error(f"❌ Investigation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())