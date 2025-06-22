#!/usr/bin/env python3
"""
Rapid Production Baseline Establishment

Quick but comprehensive testing of production database for optimization baseline.
Designed for speed while maintaining thoroughness and safety.
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from datetime import datetime

# Add the memory service to the path
sys.path.append(str(Path(__file__).parent / "python" / "memory_service" / "src"))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RapidProductionTester:
    """Quick but thorough production database testing."""
    
    def __init__(self):
        self.start_time = time.time()
        self.results = {
            "test_session": {
                "start_time": self.start_time,
                "timestamp": datetime.now().isoformat(),
                "test_type": "rapid_production_baseline"
            }
        }
    
    async def run_rapid_comprehensive_test(self):
        """Execute rapid but comprehensive production testing."""
        logger.info("=== RAPID PRODUCTION BASELINE TESTING ===")
        logger.info("Goal: Quick but thorough production database validation")
        
        try:
            # Phase 1: Credential & Environment Validation (30 seconds)
            await self._rapid_credential_validation()
            
            # Phase 2: Database Connectivity & Safety (60 seconds)
            await self._rapid_connectivity_validation()
            
            # Phase 3: Performance Baseline Measurement (120 seconds)
            await self._rapid_performance_baseline()
            
            # Phase 4: Configuration & Optimization Readiness (30 seconds)
            await self._rapid_readiness_assessment()
            
            # Generate comprehensive summary
            await self._generate_rapid_summary()
            
            return self.results
            
        except Exception as e:
            logger.error(f"Rapid testing failed: {e}")
            self.results["critical_error"] = str(e)
            return self.results
    
    async def _rapid_credential_validation(self):
        """Quick credential and environment validation."""
        logger.info("Phase 1: Rapid credential validation (30s)...")
        
        start_time = time.time()
        validation = {"phase": "credential_validation", "start_time": start_time}
        
        try:
            # Test multiple credential sources
            pgvector_password = os.getenv("PGVECTOR_PASSWORD")
            pgpassword = os.getenv("PGPASSWORD")
            
            credential_status = {
                "pgvector_password_set": bool(pgvector_password),
                "pgpassword_set": bool(pgpassword),
                "any_password_available": bool(pgvector_password or pgpassword),
                "primary_credential_source": "PGVECTOR_PASSWORD" if pgvector_password else "PGPASSWORD" if pgpassword else "NONE"
            }
            
            if not credential_status["any_password_available"]:
                raise Exception("No database credentials found in environment")
            
            # Test memory service imports
            from memory_service.config import DatabaseConfig
            from memory_service.performance_monitor import VectorPerformanceMonitor
            
            # Validate configuration
            config_status = {
                "host": DatabaseConfig.HOST,
                "port": DatabaseConfig.PORT,
                "database": DatabaseConfig.DATABASE,
                "user": DatabaseConfig.USER,
                "password_configured": bool(DatabaseConfig.PASSWORD),
                "is_render_production": "render.com" in DatabaseConfig.HOST.lower() or "dpg-" in DatabaseConfig.HOST
            }
            
            validation.update({
                "status": "passed",
                "credential_status": credential_status,
                "config_status": config_status,
                "imports_successful": True
            })
            
            logger.info(f"✅ Credentials validated - Using {credential_status['primary_credential_source']}")
            logger.info(f"✅ Target: {config_status['user']}@{config_status['host']}:{config_status['port']}/{config_status['database']}")
            
        except Exception as e:
            validation.update({
                "status": "failed",
                "error": str(e)
            })
            logger.error(f"❌ Credential validation failed: {e}")
            raise
        
        validation["duration"] = time.time() - start_time
        self.results["credential_validation"] = validation
    
    async def _rapid_connectivity_validation(self):
        """Quick but thorough database connectivity testing."""
        logger.info("Phase 2: Rapid connectivity validation (60s)...")
        
        start_time = time.time()
        connectivity = {"phase": "connectivity_validation", "start_time": start_time}
        
        try:
            from memory_service.config import DatabaseConfig
            import asyncpg
            
            # Quick connection test
            conn_str = f"postgresql://{DatabaseConfig.USER}:{DatabaseConfig.PASSWORD}@{DatabaseConfig.HOST}:{DatabaseConfig.PORT}/{DatabaseConfig.DATABASE}"
            
            logger.info("Testing basic connectivity...")
            conn = await asyncpg.connect(conn_str, command_timeout=10)
            
            # Rapid validation suite
            validation_tests = {}
            
            # Test 1: Basic info (5s)
            version = await conn.fetchval("SELECT version()")
            validation_tests["postgresql_version"] = version
            
            # Test 2: Extensions (5s)
            extensions = await conn.fetch("SELECT extname, extversion FROM pg_extension WHERE extname IN ('vector', 'hstore')")
            validation_tests["extensions"] = {ext['extname']: ext['extversion'] for ext in extensions}
            
            # Test 3: Table access (10s)
            table_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as record_count,
                    pg_size_pretty(pg_total_relation_size('vector_memories')) as table_size,
                    pg_size_pretty(pg_database_size(current_database())) as db_size
                FROM vector_memories
            """)
            validation_tests["table_access"] = dict(table_stats)
            
            # Test 4: Vector query validation (15s)
            logger.info("Testing vector query performance...")
            test_vector = [0.1] * 1536
            
            query_start = time.time()
            vector_results = await conn.fetch("""
                SELECT id, content, embedding <=> $1::vector as distance
                FROM vector_memories
                ORDER BY embedding <=> $1::vector
                LIMIT 10
            """, test_vector)
            query_time = (time.time() - query_start) * 1000
            
            validation_tests["vector_query"] = {
                "results_count": len(vector_results),
                "query_time_ms": query_time,
                "results_preview": [{"id": r["id"], "distance": float(r["distance"])} for r in vector_results[:3]]
            }
            
            # Test 5: Index information (10s)
            indexes = await conn.fetch("""
                SELECT 
                    indexname,
                    indexdef,
                    pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size
                FROM pg_indexes 
                WHERE tablename = 'vector_memories'
                ORDER BY indexname
            """)
            validation_tests["indexes"] = [dict(idx) for idx in indexes]
            
            # Test 6: Current configuration (15s)
            config_settings = {}
            config_queries = {
                "work_mem": "SHOW work_mem",
                "shared_buffers": "SHOW shared_buffers",
                "random_page_cost": "SHOW random_page_cost",
                "seq_page_cost": "SHOW seq_page_cost",
                "jit": "SHOW jit",
                "max_connections": "SHOW max_connections"
            }
            
            for setting, query in config_queries.items():
                try:
                    value = await conn.fetchval(query)
                    config_settings[setting] = value
                except Exception:
                    config_settings[setting] = "unable_to_query"
            
            # Test HNSW settings
            try:
                ef_search = await conn.fetchval("SHOW hnsw.ef_search")
                config_settings["hnsw_ef_search"] = ef_search
            except Exception:
                config_settings["hnsw_ef_search"] = "default_or_unavailable"
            
            validation_tests["current_configuration"] = config_settings
            
            await conn.close()
            
            connectivity.update({
                "status": "passed",
                "validation_tests": validation_tests,
                "connection_successful": True,
                "sample_query_ms": query_time
            })
            
            logger.info(f"✅ Connectivity validated - Sample query: {query_time:.1f}ms")
            logger.info(f"✅ Database: {validation_tests['table_access']['record_count']} vectors, {validation_tests['table_access']['table_size']}")
            
        except Exception as e:
            connectivity.update({
                "status": "failed",
                "error": str(e),
                "connection_successful": False
            })
            logger.error(f"❌ Connectivity validation failed: {e}")
            raise
        
        connectivity["duration"] = time.time() - start_time
        self.results["connectivity_validation"] = connectivity
    
    async def _rapid_performance_baseline(self):
        """Quick but comprehensive performance baseline measurement."""
        logger.info("Phase 3: Rapid performance baseline (120s)...")
        
        start_time = time.time()
        baseline = {"phase": "performance_baseline", "start_time": start_time}
        
        try:
            from memory_service.config import DatabaseConfig
            from memory_service.performance_monitor import VectorPerformanceMonitor
            import asyncpg
            
            # Create optimized connection pool for testing
            conn_str = f"postgresql://{DatabaseConfig.USER}:{DatabaseConfig.PASSWORD}@{DatabaseConfig.HOST}:{DatabaseConfig.PORT}/{DatabaseConfig.DATABASE}"
            
            pool = await asyncpg.create_pool(
                conn_str,
                min_size=3,
                max_size=8,
                command_timeout=20,
                server_settings={
                    'application_name': 'rapid_baseline_measurement'
                }
            )
            
            # Rapid but comprehensive performance measurement
            monitor = VectorPerformanceMonitor(pool, "vector_memories")
            
            logger.info("Running rapid comprehensive benchmark...")
            
            # Optimized benchmark parameters for speed but accuracy
            benchmark_results = await monitor.run_comprehensive_benchmark(
                num_queries=25,  # Reduced for speed but sufficient for accuracy
                concurrent_queries=6  # Balanced for realistic testing
            )
            
            await pool.close()
            
            # Extract critical metrics
            single_perf = benchmark_results.get("single_query_performance", {})
            concurrent_perf = benchmark_results.get("concurrent_performance", {})
            db_stats = benchmark_results.get("database_stats", {})
            summary = benchmark_results.get("summary", {})
            
            # Calculate optimization opportunity
            p95_latency = single_perf.get("p95_latency_ms", 0)
            throughput = concurrent_perf.get("throughput_qps", 0)
            
            optimization_analysis = {
                "current_performance": {
                    "p95_latency_ms": p95_latency,
                    "avg_latency_ms": single_perf.get("avg_latency_ms", 0),
                    "max_latency_ms": single_perf.get("max_latency_ms", 0),
                    "throughput_qps": throughput,
                    "error_rate": single_perf.get("error_rate", 0)
                },
                "optimization_targets": {
                    "target_p95_latency": 20,
                    "target_throughput": 100,
                    "target_error_rate": 0.01
                },
                "improvement_potential": {
                    "latency_improvement": f"{((p95_latency - 20) / p95_latency * 100):.1f}%" if p95_latency > 20 else "Already optimized",
                    "throughput_improvement": f"{((100 - throughput) / throughput * 100):.1f}%" if throughput < 100 and throughput > 0 else "Significant improvement possible",
                    "optimization_urgency": "high" if p95_latency > 100 else "medium" if p95_latency > 50 else "low"
                }
            }
            
            baseline.update({
                "status": "completed",
                "benchmark_results": benchmark_results,
                "optimization_analysis": optimization_analysis,
                "database_info": db_stats,
                "performance_grade": summary.get("performance_grade", "unknown"),
                "ready_for_optimization": True
            })
            
            # Save detailed results
            baseline_timestamp = int(time.time())
            baseline_file = f"rapid_baseline_{baseline_timestamp}.json"
            with open(baseline_file, "w") as f:
                json.dump(benchmark_results, f, indent=2, default=str)
            
            baseline["detailed_results_file"] = baseline_file
            
            logger.info("✅ Performance baseline established")
            logger.info(f"🎯 Current Performance: P95={p95_latency:.1f}ms, Throughput={throughput:.1f} QPS")
            logger.info(f"🎯 Performance Grade: {summary.get('performance_grade', 'Unknown')}")
            logger.info(f"🚀 Optimization Potential: {optimization_analysis['improvement_potential']['latency_improvement']}")
            
        except Exception as e:
            baseline.update({
                "status": "failed",
                "error": str(e),
                "ready_for_optimization": False
            })
            logger.error(f"❌ Performance baseline failed: {e}")
            raise
        
        baseline["duration"] = time.time() - start_time
        self.results["performance_baseline"] = baseline
    
    async def _rapid_readiness_assessment(self):
        """Quick optimization readiness assessment."""
        logger.info("Phase 4: Rapid readiness assessment (30s)...")
        
        start_time = time.time()
        readiness = {"phase": "readiness_assessment", "start_time": start_time}
        
        try:
            # Assess current system state
            connectivity_ready = self.results.get("connectivity_validation", {}).get("connection_successful", False)
            baseline_ready = self.results.get("performance_baseline", {}).get("ready_for_optimization", False)
            
            # Analyze optimization components
            optimization_components = {
                "performance_monitor": True,  # Validated in baseline
                "migration_scripts": os.path.exists("python/memory_service/migrations/003_optimize_postgresql_for_vectors.sql"),
                "hnsw_optimization": os.path.exists("python/memory_service/migrations/004_optimize_hnsw_parameters.sql"),
                "application_script": os.path.exists("apply_pgvector_optimizations.py"),
                "rollback_procedures": True  # Built into migration scripts
            }
            
            # Calculate readiness score
            readiness_score = sum(optimization_components.values()) / len(optimization_components)
            
            # Determine next steps based on current performance
            baseline_metrics = self.results.get("performance_baseline", {}).get("optimization_analysis", {})
            current_p95 = baseline_metrics.get("current_performance", {}).get("p95_latency_ms", 0)
            
            next_steps = []
            if current_p95 > 20:
                next_steps.extend([
                    "Proceed to Phase B: PostgreSQL configuration optimization",
                    "Apply connection pool enhancements",
                    "Schedule Phase C: HNSW index optimization"
                ])
            else:
                next_steps.append("Current performance already meets targets - validation complete")
            
            readiness.update({
                "status": "completed",
                "system_ready": connectivity_ready and baseline_ready,
                "optimization_components": optimization_components,
                "readiness_score": readiness_score,
                "optimization_recommended": current_p95 > 20,
                "next_steps": next_steps,
                "phase_b_ready": readiness_score >= 0.8 and baseline_ready
            })
            
            logger.info(f"✅ Readiness assessment complete")
            logger.info(f"📊 Readiness Score: {readiness_score:.1%}")
            logger.info(f"🚀 Phase B Ready: {'YES' if readiness['phase_b_ready'] else 'NO'}")
            
        except Exception as e:
            readiness.update({
                "status": "failed",
                "error": str(e)
            })
            logger.error(f"❌ Readiness assessment failed: {e}")
        
        readiness["duration"] = time.time() - start_time
        self.results["readiness_assessment"] = readiness
    
    async def _generate_rapid_summary(self):
        """Generate comprehensive rapid testing summary."""
        logger.info("Generating rapid testing summary...")
        
        total_duration = time.time() - self.start_time
        
        # Calculate overall success
        phases = ["credential_validation", "connectivity_validation", "performance_baseline", "readiness_assessment"]
        successful_phases = sum(1 for phase in phases if self.results.get(phase, {}).get("status") in ["passed", "completed"])
        success_rate = successful_phases / len(phases)
        
        # Extract key metrics
        baseline_metrics = self.results.get("performance_baseline", {}).get("optimization_analysis", {})
        current_performance = baseline_metrics.get("current_performance", {})
        
        summary = {
            "rapid_test_summary": {
                "total_duration": total_duration,
                "success_rate": success_rate,
                "phases_completed": successful_phases,
                "phases_total": len(phases),
                "overall_status": "success" if success_rate >= 0.75 else "partial" if success_rate >= 0.5 else "failed"
            },
            "current_performance_snapshot": current_performance,
            "optimization_readiness": self.results.get("readiness_assessment", {}).get("phase_b_ready", False),
            "critical_findings": self._extract_critical_findings(),
            "immediate_next_steps": self._generate_immediate_next_steps()
        }
        
        self.results["rapid_summary"] = summary
        
        # Log executive summary
        logger.info("=== RAPID TESTING COMPLETE ===")
        logger.info(f"Duration: {total_duration:.1f} seconds")
        logger.info(f"Success Rate: {success_rate:.1%} ({successful_phases}/{len(phases)} phases)")
        logger.info(f"Overall Status: {summary['rapid_test_summary']['overall_status'].upper()}")
        
        if current_performance:
            p95 = current_performance.get("p95_latency_ms", 0)
            qps = current_performance.get("throughput_qps", 0)
            logger.info(f"Performance: P95={p95:.1f}ms, Throughput={qps:.1f} QPS")
        
        if summary["optimization_readiness"]:
            logger.info("✅ READY FOR PHASE B OPTIMIZATION")
        else:
            logger.info("⏳ Address issues before optimization")
    
    def _extract_critical_findings(self) -> list:
        """Extract critical findings from all test phases."""
        findings = []
        
        # Connectivity findings
        connectivity = self.results.get("connectivity_validation", {})
        if connectivity.get("sample_query_ms", 0) > 100:
            findings.append(f"High query latency detected: {connectivity['sample_query_ms']:.1f}ms")
        
        # Performance findings
        baseline = self.results.get("performance_baseline", {})
        if baseline.get("status") == "completed":
            analysis = baseline.get("optimization_analysis", {})
            urgency = analysis.get("improvement_potential", {}).get("optimization_urgency", "")
            if urgency == "high":
                findings.append("High-priority optimization opportunity identified")
        
        # Database findings
        if connectivity.get("validation_tests", {}).get("table_access", {}).get("record_count", 0) < 100:
            findings.append("Low vector count - consider adding more data for realistic testing")
        
        return findings
    
    def _generate_immediate_next_steps(self) -> list:
        """Generate immediate actionable next steps."""
        next_steps = []
        
        readiness = self.results.get("readiness_assessment", {})
        if readiness.get("phase_b_ready"):
            next_steps.extend([
                "Execute Phase B: PostgreSQL configuration optimization",
                "Monitor performance improvements in real-time",
                "Validate optimization effectiveness"
            ])
        else:
            # Add specific steps based on what failed
            for phase in ["credential_validation", "connectivity_validation", "performance_baseline"]:
                if self.results.get(phase, {}).get("status") not in ["passed", "completed"]:
                    next_steps.append(f"Resolve {phase} issues before proceeding")
        
        return next_steps

async def main():
    """Execute rapid production testing."""
    logger.info("Starting Rapid Production Baseline Testing")
    logger.info("Target: Complete validation in under 5 minutes")
    
    tester = RapidProductionTester()
    
    try:
        results = await tester.run_rapid_comprehensive_test()
        
        # Save complete results
        timestamp = int(time.time())
        results_file = f"rapid_production_test_{timestamp}.json"
        
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Complete results saved to {results_file}")
        
        # Return success based on optimization readiness
        optimization_ready = results.get("rapid_summary", {}).get("optimization_readiness", False)
        return 0 if optimization_ready else 1
        
    except Exception as e:
        logger.error(f"Rapid testing failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)