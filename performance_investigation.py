#!/usr/bin/env python3
"""
Performance Discrepancy Investigation & Optimization

Investigates the critical performance discrepancy between expected 92% improvement 
and observed -12.8% degradation, then optimizes for production deployment.
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
import random

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PerformanceInvestigator:
    """Comprehensive performance investigation and optimization system."""
    
    def __init__(self):
        """Initialize the performance investigator."""
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
                max_size=8,
                command_timeout=60
            )
            
            async with self.connection_pool.acquire() as conn:
                # Get detailed database info
                db_version = await conn.fetchval("SELECT version()")
                vector_extension = await conn.fetchval(
                    "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
                )
                
                logger.info(f"✅ Connected to PostgreSQL: {db_version.split()[1]}")
                logger.info(f"✅ pgvector extension: v{vector_extension}")
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            raise
    
    async def check_migration_status(self) -> Dict[str, Any]:
        """Check the current migration status and data availability."""
        logger.info("📊 Checking migration status...")
        
        async with self.connection_pool.acquire() as conn:
            try:
                # Get vector counts
                original_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM vector_memories WHERE embedding IS NOT NULL"
                )
                
                optimized_total = await conn.fetchval(
                    "SELECT COUNT(*) FROM vector_memories_optimized"
                )
                
                optimized_migrated = await conn.fetchval(
                    "SELECT COUNT(*) FROM vector_memories_optimized WHERE migration_status IN ('migrated', 'verified')"
                )
                
                # Get migration progress
                progress_info = await conn.fetchrow(
                    "SELECT * FROM migration_progress ORDER BY created_at DESC LIMIT 1"
                )
                
                # Get recent batch info
                recent_batches = await conn.fetch("""
                    SELECT batch_number, status, migrated_vectors, failed_vectors, completed_at
                    FROM migration_batches 
                    ORDER BY batch_number DESC 
                    LIMIT 5
                """)
                
                migration_status = {
                    'original_vectors': original_count,
                    'optimized_total': optimized_total,
                    'optimized_migrated': optimized_migrated,
                    'migration_percentage': (optimized_migrated / original_count * 100) if original_count > 0 else 0,
                    'progress_info': dict(progress_info) if progress_info else None,
                    'recent_batches': [dict(batch) for batch in recent_batches]
                }
                
                logger.info(f"✅ Migration Status: {optimized_migrated}/{original_count} vectors ({migration_status['migration_percentage']:.1f}%)")
                
                return migration_status
                
            except Exception as e:
                logger.error(f"❌ Failed to check migration status: {e}")
                raise
    
    async def analyze_hnsw_index_performance(self) -> Dict[str, Any]:
        """Analyze HNSW index statistics and performance characteristics."""
        logger.info("🔍 Analyzing HNSW index performance...")
        
        async with self.connection_pool.acquire() as conn:
            try:
                # Get index information
                index_info = await conn.fetch("""
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        indexdef
                    FROM pg_indexes 
                    WHERE tablename IN ('vector_memories', 'vector_memories_optimized')
                    AND indexname LIKE '%hnsw%'
                """)
                
                # Get index usage statistics
                index_stats = await conn.fetch("""
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        idx_scan,
                        idx_tup_read,
                        idx_tup_fetch
                    FROM pg_stat_user_indexes 
                    WHERE tablename IN ('vector_memories', 'vector_memories_optimized')
                    AND indexname LIKE '%hnsw%'
                """)
                
                # Get table statistics
                table_stats = await conn.fetch("""
                    SELECT 
                        schemaname,
                        tablename,
                        n_tup_ins,
                        n_tup_upd,
                        n_tup_del,
                        n_live_tup,
                        n_dead_tup,
                        last_vacuum,
                        last_autovacuum,
                        last_analyze,
                        last_autoanalyze
                    FROM pg_stat_user_tables 
                    WHERE tablename IN ('vector_memories', 'vector_memories_optimized')
                """)
                
                # Test index selectivity with various ef_search values
                selectivity_tests = []
                test_vector = [0.1] * 1536
                test_vector_str = '[' + ','.join(map(str, test_vector)) + ']'
                
                # Test different ef_search values (HNSW search parameter)
                for ef_search in [10, 40, 64, 100, 200]:
                    try:
                        # Set ef_search parameter
                        await conn.execute(f"SET hnsw.ef_search = {ef_search}")
                        
                        # Test query performance
                        start_time = time.perf_counter()
                        results = await conn.fetch("""
                            SELECT id, embedding <=> $1::vector as distance
                            FROM vector_memories_optimized
                            WHERE migration_status IN ('migrated', 'verified')
                            ORDER BY embedding <=> $1::vector
                            LIMIT 10
                        """, test_vector_str)
                        latency_ms = (time.perf_counter() - start_time) * 1000
                        
                        selectivity_tests.append({
                            'ef_search': ef_search,
                            'latency_ms': latency_ms,
                            'results_count': len(results)
                        })
                        
                        logger.info(f"   ef_search={ef_search}: {latency_ms:.2f}ms")
                        
                    except Exception as e:
                        logger.warning(f"⚠️ ef_search={ef_search} test failed: {e}")
                
                # Reset ef_search to default
                await conn.execute("RESET hnsw.ef_search")
                
                analysis = {
                    'index_info': [dict(idx) for idx in index_info],
                    'index_statistics': [dict(stat) for stat in index_stats],
                    'table_statistics': [dict(stat) for stat in table_stats],
                    'selectivity_tests': selectivity_tests,
                    'optimal_ef_search': min(selectivity_tests, key=lambda x: x['latency_ms'])['ef_search'] if selectivity_tests else None
                }
                
                logger.info(f"✅ HNSW Analysis: Optimal ef_search = {analysis['optimal_ef_search']}")
                
                return analysis
                
            except Exception as e:
                logger.error(f"❌ HNSW index analysis failed: {e}")
                raise
    
    async def comprehensive_query_testing(self) -> Dict[str, Any]:
        """Test performance with diverse query patterns and sizes."""
        logger.info("🧪 Running comprehensive query testing...")
        
        async with self.connection_pool.acquire() as conn:
            try:
                # Test different query patterns
                test_scenarios = [
                    {'name': 'small_result_set', 'limit': 5, 'iterations': 20},
                    {'name': 'medium_result_set', 'limit': 20, 'iterations': 15},
                    {'name': 'large_result_set', 'limit': 50, 'iterations': 10},
                ]
                
                # Generate diverse test vectors
                test_vectors = []
                
                # Random vectors
                for i in range(5):
                    random_vector = np.random.normal(0, 0.1, 1536).astype(np.float32)
                    random_vector = random_vector / np.linalg.norm(random_vector)  # Normalize
                    test_vectors.append(('[' + ','.join(map(str, random_vector)) + ']', f'random_{i}'))
                
                # Get some actual vectors from optimized table for realistic queries
                try:
                    actual_vectors = await conn.fetch("""
                        SELECT embedding
                        FROM vector_memories_optimized
                        WHERE migration_status IN ('migrated', 'verified')
                        ORDER BY RANDOM()
                        LIMIT 3
                    """)
                    
                    for i, row in enumerate(actual_vectors):
                        if row['embedding']:
                            embedding_list = list(row['embedding'])
                            embedding_str = '[' + ','.join(map(str, embedding_list)) + ']'
                            test_vectors.append((embedding_str, f'actual_{i}'))
                            
                except Exception as e:
                    logger.warning(f"⚠️ Could not get actual vectors: {e}")
                
                results = {}
                
                for scenario in test_scenarios:
                    logger.info(f"🔬 Testing {scenario['name']} (limit={scenario['limit']})...")
                    
                    original_times = []
                    optimized_times = []
                    
                    for iteration in range(scenario['iterations']):
                        # Choose a random test vector
                        test_vector, vector_type = random.choice(test_vectors)
                        
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
                            logger.warning(f"⚠️ Original table query failed: {e}")
                        
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
                            logger.warning(f"⚠️ Optimized table query failed: {e}")
                    
                    # Calculate statistics
                    scenario_results = {
                        'scenario': scenario['name'],
                        'limit': scenario['limit'],
                        'iterations': scenario['iterations'],
                        'original_table': {
                            'avg_latency_ms': statistics.mean(original_times) if original_times else 0,
                            'min_latency_ms': min(original_times) if original_times else 0,
                            'max_latency_ms': max(original_times) if original_times else 0,
                            'std_dev_ms': statistics.stdev(original_times) if len(original_times) > 1 else 0,
                            'successful_queries': len(original_times)
                        },
                        'optimized_table': {
                            'avg_latency_ms': statistics.mean(optimized_times) if optimized_times else 0,
                            'min_latency_ms': min(optimized_times) if optimized_times else 0,
                            'max_latency_ms': max(optimized_times) if optimized_times else 0,
                            'std_dev_ms': statistics.stdev(optimized_times) if len(optimized_times) > 1 else 0,
                            'successful_queries': len(optimized_times)
                        }
                    }
                    
                    # Calculate improvement
                    if original_times and optimized_times:
                        avg_improvement = ((statistics.mean(original_times) - statistics.mean(optimized_times)) 
                                         / statistics.mean(original_times) * 100)
                        scenario_results['performance_improvement_percent'] = avg_improvement
                        scenario_results['speedup_factor'] = statistics.mean(original_times) / statistics.mean(optimized_times)
                    
                    results[scenario['name']] = scenario_results
                    
                    logger.info(f"   📊 {scenario['name']}: {scenario_results.get('performance_improvement_percent', 0):.1f}% improvement")
                
                return results
                
            except Exception as e:
                logger.error(f"❌ Comprehensive query testing failed: {e}")
                raise
    
    async def database_configuration_analysis(self) -> Dict[str, Any]:
        """Analyze PostgreSQL configuration for vector workloads."""
        logger.info("⚙️ Analyzing database configuration...")
        
        async with self.connection_pool.acquire() as conn:
            try:
                # Get relevant PostgreSQL settings
                important_settings = [
                    'shared_buffers',
                    'effective_cache_size',
                    'maintenance_work_mem',
                    'work_mem',
                    'random_page_cost',
                    'seq_page_cost',
                    'cpu_tuple_cost',
                    'cpu_index_tuple_cost',
                    'max_parallel_workers_per_gather',
                    'hnsw.ef_search'
                ]
                
                config_info = {}
                for setting in important_settings:
                    try:
                        value = await conn.fetchval(f"SHOW {setting}")
                        config_info[setting] = value
                    except Exception as e:
                        logger.warning(f"⚠️ Could not get {setting}: {e}")
                
                # Get memory and resource info
                memory_info = await conn.fetchrow("""
                    SELECT 
                        pg_size_pretty(pg_database_size(current_database())) as database_size,
                        pg_size_pretty(pg_total_relation_size('vector_memories')) as original_table_size,
                        pg_size_pretty(pg_total_relation_size('vector_memories_optimized')) as optimized_table_size
                """)
                
                analysis = {
                    'postgresql_settings': config_info,
                    'database_sizes': dict(memory_info) if memory_info else {},
                    'recommendations': []
                }
                
                # Generate recommendations
                if 'work_mem' in config_info:
                    work_mem_val = config_info['work_mem']
                    if 'MB' in work_mem_val and int(work_mem_val.replace('MB', '')) < 64:
                        analysis['recommendations'].append({
                            'setting': 'work_mem',
                            'current': work_mem_val,
                            'recommended': '64MB',
                            'reason': 'Vector operations benefit from larger work_mem'
                        })
                
                if 'hnsw.ef_search' in config_info:
                    ef_search = config_info['hnsw.ef_search']
                    if ef_search == '40':  # Default value
                        analysis['recommendations'].append({
                            'setting': 'hnsw.ef_search',
                            'current': ef_search,
                            'recommended': '64',
                            'reason': 'Higher ef_search may improve recall for vector queries'
                        })
                
                logger.info(f"✅ Database analysis: {len(analysis['recommendations'])} optimization recommendations")
                
                return analysis
                
            except Exception as e:
                logger.error(f"❌ Database configuration analysis failed: {e}")
                raise
    
    async def optimize_hnsw_parameters(self, optimal_ef_search: int = None) -> Dict[str, Any]:
        """Optimize HNSW parameters based on analysis results."""
        logger.info("🔧 Optimizing HNSW parameters...")
        
        async with self.connection_pool.acquire() as conn:
            try:
                optimization_results = {}
                
                # Test current performance
                test_vector = [0.1] * 1536
                test_vector_str = '[' + ','.join(map(str, test_vector)) + ']'
                
                # Baseline performance
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
                optimization_results['baseline_results'] = len(baseline_results)
                
                # Apply optimal ef_search if provided
                if optimal_ef_search:
                    logger.info(f"🔧 Setting optimal ef_search = {optimal_ef_search}")
                    await conn.execute(f"SET hnsw.ef_search = {optimal_ef_search}")
                    
                    # Test optimized performance
                    start_time = time.perf_counter()
                    optimized_results = await conn.fetch("""
                        SELECT id, embedding <=> $1::vector as distance
                        FROM vector_memories_optimized
                        WHERE migration_status IN ('migrated', 'verified')
                        ORDER BY embedding <=> $1::vector
                        LIMIT 20
                    """, test_vector_str)
                    optimized_latency = (time.perf_counter() - start_time) * 1000
                    
                    optimization_results['optimized_latency_ms'] = optimized_latency
                    optimization_results['optimized_results'] = len(optimized_results)
                    optimization_results['latency_improvement_percent'] = (
                        (baseline_latency - optimized_latency) / baseline_latency * 100
                    )
                    optimization_results['ef_search_applied'] = optimal_ef_search
                
                # Check if index needs rebuilding (if very poor performance)
                if baseline_latency > 500:  # If baseline is very slow
                    logger.info("🔧 Index may need rebuilding - checking index status...")
                    
                    # Check index bloat
                    index_info = await conn.fetchrow("""
                        SELECT 
                            pg_size_pretty(pg_relation_size('idx_vector_memories_optimized_embedding_hnsw')) as index_size,
                            pg_stat_get_numscans('idx_vector_memories_optimized_embedding_hnsw'::regclass) as scans
                    """)
                    
                    optimization_results['index_info'] = dict(index_info) if index_info else {}
                    optimization_results['rebuild_recommended'] = baseline_latency > 500
                
                logger.info(f"✅ HNSW optimization complete: {optimization_results.get('latency_improvement_percent', 0):.1f}% improvement")
                
                return optimization_results
                
            except Exception as e:
                logger.error(f"❌ HNSW optimization failed: {e}")
                raise
    
    async def run_final_performance_validation(self) -> Dict[str, Any]:
        """Run final comprehensive performance validation."""
        logger.info("🏁 Running final performance validation...")
        
        async with self.connection_pool.acquire() as conn:
            try:
                # Large-scale performance test
                test_queries = 50
                test_vector = [0.1] * 1536
                test_vector_str = '[' + ','.join(map(str, test_vector)) + ']'
                
                # Test original table
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
                    
                    if (i + 1) % 10 == 0:
                        logger.info(f"   Original table: {i + 1}/{test_queries} queries completed")
                
                # Test optimized table
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
                    
                    if (i + 1) % 10 == 0:
                        logger.info(f"   Optimized table: {i + 1}/{test_queries} queries completed")
                
                # Calculate comprehensive statistics
                validation_results = {
                    'test_queries': test_queries,
                    'original_table': {
                        'avg_latency_ms': statistics.mean(original_times),
                        'median_latency_ms': statistics.median(original_times),
                        'p95_latency_ms': sorted(original_times)[int(0.95 * len(original_times))],
                        'min_latency_ms': min(original_times),
                        'max_latency_ms': max(original_times),
                        'std_dev_ms': statistics.stdev(original_times)
                    },
                    'optimized_table': {
                        'avg_latency_ms': statistics.mean(optimized_times),
                        'median_latency_ms': statistics.median(optimized_times),
                        'p95_latency_ms': sorted(optimized_times)[int(0.95 * len(optimized_times))],
                        'min_latency_ms': min(optimized_times),
                        'max_latency_ms': max(optimized_times),
                        'std_dev_ms': statistics.stdev(optimized_times)
                    }
                }
                
                # Calculate improvements
                avg_improvement = ((validation_results['original_table']['avg_latency_ms'] - 
                                  validation_results['optimized_table']['avg_latency_ms']) / 
                                 validation_results['original_table']['avg_latency_ms'] * 100)
                
                p95_improvement = ((validation_results['original_table']['p95_latency_ms'] - 
                                  validation_results['optimized_table']['p95_latency_ms']) / 
                                 validation_results['original_table']['p95_latency_ms'] * 100)
                
                validation_results['performance_metrics'] = {
                    'avg_improvement_percent': avg_improvement,
                    'p95_improvement_percent': p95_improvement,
                    'speedup_factor': (validation_results['original_table']['avg_latency_ms'] / 
                                     validation_results['optimized_table']['avg_latency_ms']),
                    'consistency_improvement': (validation_results['original_table']['std_dev_ms'] / 
                                              validation_results['optimized_table']['std_dev_ms'])
                }
                
                logger.info(f"✅ Final validation: {avg_improvement:.1f}% avg improvement, {p95_improvement:.1f}% P95 improvement")
                
                return validation_results
                
            except Exception as e:
                logger.error(f"❌ Final performance validation failed: {e}")
                raise
    
    async def run_complete_investigation(self) -> Dict[str, Any]:
        """Run complete performance investigation and optimization."""
        start_time = time.time()
        logger.info("🚀 Starting comprehensive performance investigation...")
        
        try:
            # Connect to database
            await self.connect_to_database()
            
            # Phase 1: Root Cause Analysis
            logger.info("\n" + "="*60)
            logger.info("PHASE 1: ROOT CAUSE ANALYSIS")
            logger.info("="*60)
            
            migration_status = await self.check_migration_status()
            hnsw_analysis = await self.analyze_hnsw_index_performance()
            query_testing = await self.comprehensive_query_testing()
            db_config_analysis = await self.database_configuration_analysis()
            
            # Phase 2: Performance Optimization
            logger.info("\n" + "="*60)
            logger.info("PHASE 2: PERFORMANCE OPTIMIZATION")
            logger.info("="*60)
            
            optimal_ef_search = hnsw_analysis.get('optimal_ef_search')
            optimization_results = await self.optimize_hnsw_parameters(optimal_ef_search)
            
            # Phase 3: Comprehensive Validation
            logger.info("\n" + "="*60)
            logger.info("PHASE 3: COMPREHENSIVE VALIDATION")
            logger.info("="*60)
            
            final_validation = await self.run_final_performance_validation()
            
            # Compile comprehensive results
            investigation_results = {
                'investigation_metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'duration_seconds': time.time() - start_time,
                    'investigation_type': 'performance_discrepancy_resolution'
                },
                'migration_status': migration_status,
                'hnsw_analysis': hnsw_analysis,
                'query_testing_results': query_testing,
                'database_configuration': db_config_analysis,
                'optimization_results': optimization_results,
                'final_validation': final_validation,
                'executive_summary': self._generate_executive_summary(
                    migration_status, hnsw_analysis, query_testing, 
                    optimization_results, final_validation
                )
            }
            
            logger.info(f"🎉 Investigation completed in {time.time() - start_time:.1f} seconds")
            
            return investigation_results
            
        except Exception as e:
            logger.error(f"❌ Performance investigation failed: {e}")
            raise
        finally:
            if self.connection_pool:
                await self.connection_pool.close()
    
    def _generate_executive_summary(self, migration_status, hnsw_analysis, query_testing, 
                                  optimization_results, final_validation) -> Dict[str, Any]:
        """Generate executive summary of investigation findings."""
        
        # Determine root cause
        migration_complete = migration_status['migration_percentage'] > 80
        index_optimized = optimization_results.get('latency_improvement_percent', 0) > 0
        final_performance = final_validation['performance_metrics']['avg_improvement_percent']
        
        # Determine status
        if final_performance > 70:
            status = "EXCELLENT"
            recommendation = "DEPLOY IMMEDIATELY"
        elif final_performance > 40:
            status = "GOOD"
            recommendation = "DEPLOY WITH MONITORING"
        elif final_performance > 0:
            status = "MARGINAL"
            recommendation = "INVESTIGATE FURTHER"
        else:
            status = "POOR"
            recommendation = "DO NOT DEPLOY"
        
        # Key findings
        key_findings = []
        
        if not migration_complete:
            key_findings.append(f"Migration only {migration_status['migration_percentage']:.1f}% complete")
        
        if index_optimized:
            key_findings.append(f"HNSW optimization improved performance by {optimization_results['latency_improvement_percent']:.1f}%")
        
        if final_performance > 0:
            key_findings.append(f"Final optimization achieves {final_performance:.1f}% improvement")
        else:
            key_findings.append(f"Performance is {abs(final_performance):.1f}% worse than baseline")
        
        return {
            'status': status,
            'recommendation': recommendation,
            'final_performance_improvement': final_performance,
            'migration_completion': migration_status['migration_percentage'],
            'key_findings': key_findings,
            'root_causes_identified': [
                "Migration incomplete" if not migration_complete else "Migration complete",
                "HNSW parameters suboptimal" if not index_optimized else "HNSW parameters optimized",
                "Index needs more data" if migration_status['optimized_migrated'] < 1000 else "Sufficient data available"
            ]
        }
    
    def save_investigation_results(self, results: Dict[str, Any], filename: str = None):
        """Save investigation results to file."""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"performance_investigation_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            logger.info(f"💾 Investigation results saved to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"❌ Failed to save investigation results: {e}")
            raise

async def main():
    """Main execution."""
    print("🔍 Core Nexus Performance Investigation")
    print("=" * 45)
    print("Investigating Performance Discrepancy & Optimization")
    print()
    
    try:
        investigator = PerformanceInvestigator()
        results = await investigator.run_complete_investigation()
        
        # Save results
        filename = investigator.save_investigation_results(results)
        
        # Print comprehensive summary
        print("\n" + "="*60)
        print("🏆 PERFORMANCE INVESTIGATION RESULTS")
        print("="*60)
        
        summary = results['executive_summary']
        migration = results['migration_status']
        final = results['final_validation']['performance_metrics']
        
        print(f"📊 EXECUTIVE SUMMARY")
        print("=" * 25)
        print(f"✅ Status: {summary['status']}")
        print(f"✅ Recommendation: {summary['recommendation']}")
        print(f"✅ Final Performance: {summary['final_performance_improvement']:.1f}% improvement")
        print(f"✅ Migration Progress: {summary['migration_completion']:.1f}% complete")
        
        print(f"\n📈 DETAILED PERFORMANCE METRICS")
        print("=" * 35)
        orig = results['final_validation']['original_table']
        opt = results['final_validation']['optimized_table']
        
        print(f"🔍 Original Table (19k+ D):")
        print(f"   Average: {orig['avg_latency_ms']:.2f}ms")
        print(f"   P95: {orig['p95_latency_ms']:.2f}ms")
        print(f"   Std Dev: {orig['std_dev_ms']:.2f}ms")
        
        print(f"\n🔍 Optimized Table (1,536D):")
        print(f"   Average: {opt['avg_latency_ms']:.2f}ms")
        print(f"   P95: {opt['p95_latency_ms']:.2f}ms")
        print(f"   Std Dev: {opt['std_dev_ms']:.2f}ms")
        
        print(f"\n🚀 PERFORMANCE IMPROVEMENTS")
        print("=" * 30)
        print(f"📈 Average Improvement: {final['avg_improvement_percent']:.1f}%")
        print(f"📈 P95 Improvement: {final['p95_improvement_percent']:.1f}%")
        print(f"📈 Speedup Factor: {final['speedup_factor']:.2f}x")
        print(f"📈 Consistency: {final['consistency_improvement']:.2f}x better")
        
        print(f"\n🔍 KEY FINDINGS")
        print("=" * 20)
        for i, finding in enumerate(summary['key_findings'], 1):
            print(f"{i}. {finding}")
        
        print(f"\n🛠️ OPTIMIZATION APPLIED")
        print("=" * 25)
        if 'optimization_results' in results and results['optimization_results']:
            opt_res = results['optimization_results']
            if 'ef_search_applied' in opt_res:
                print(f"✅ HNSW ef_search optimized: {opt_res['ef_search_applied']}")
                print(f"✅ Optimization improvement: {opt_res.get('latency_improvement_percent', 0):.1f}%")
            else:
                print("⚠️ No HNSW optimization applied")
        
        print(f"\n💾 Complete investigation: {filename}")
        
        # Final recommendation
        if summary['status'] in ['EXCELLENT', 'GOOD']:
            print(f"\n🚀 RECOMMENDATION: {summary['recommendation']}")
            print("✅ Performance discrepancy resolved")
            print("✅ Ready for production deployment")
        else:
            print(f"\n⚠️ RECOMMENDATION: {summary['recommendation']}")
            print("❌ Performance issues require further investigation")
        
    except Exception as e:
        logger.error(f"❌ Performance investigation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())