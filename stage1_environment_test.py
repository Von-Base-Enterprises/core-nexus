#!/usr/bin/env python3
"""
Stage 1: Environment & Baseline Establishment Test

Tests database connectivity and establishes real baseline performance.
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

# Add the memory service to the path
sys.path.append(str(Path(__file__).parent / "python" / "memory_service" / "src"))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_database_connectivity():
    """Test database connection and basic functionality."""
    logger.info("Testing database connectivity...")
    
    test_result = {
        "test_name": "database_connectivity",
        "start_time": time.time(),
        "status": "running"
    }
    
    try:
        # Check environment variables
        password = os.getenv("PGVECTOR_PASSWORD") or os.getenv("PGPASSWORD")
        
        if not password:
            test_result.update({
                "status": "failed",
                "error": "No database password found. Set PGVECTOR_PASSWORD environment variable.",
                "suggestions": [
                    "export PGVECTOR_PASSWORD='your_password'",
                    "Or check if PGPASSWORD is set",
                    "Contact team for production database credentials"
                ]
            })
            return test_result
        
        # Try to import memory service components
        try:
            from memory_service.config import DatabaseConfig
            from memory_service.performance_monitor import VectorPerformanceMonitor
            logger.info("✅ Memory service imports successful")
        except ImportError as e:
            test_result.update({
                "status": "failed",
                "error": f"Memory service import failed: {e}",
                "suggestions": [
                    "Run: pip install -r requirements.txt",
                    "Check if all dependencies are installed",
                    "Verify Python path includes memory service"
                ]
            })
            return test_result
        
        # Test database connection
        import asyncpg
        
        host = os.getenv("PGVECTOR_HOST", DatabaseConfig.HOST)
        port = os.getenv("PGVECTOR_PORT", DatabaseConfig.PORT)
        database = os.getenv("PGVECTOR_DATABASE", DatabaseConfig.DATABASE)
        user = os.getenv("PGVECTOR_USER", DatabaseConfig.USER)
        
        conn_str = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        logger.info(f"Connecting to: {user}@{host}:{port}/{database}")
        
        # Create test connection
        conn = await asyncpg.connect(conn_str, command_timeout=10)
        
        # Test basic queries
        version = await conn.fetchval("SELECT version()")
        vector_extension = await conn.fetchval("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        
        # Test vector_memories table access
        table_info = await conn.fetchrow("""
            SELECT 
                COUNT(*) as vector_count,
                pg_size_pretty(pg_total_relation_size('vector_memories')) as table_size
            FROM vector_memories
        """)
        
        await conn.close()
        
        test_result.update({
            "status": "passed",
            "database_info": {
                "version": version,
                "vector_extension": vector_extension,
                "connection_successful": True
            },
            "table_info": dict(table_info) if table_info else {},
            "connection_string": f"{user}@{host}:{port}/{database}"
        })
        
        logger.info("✅ Database connectivity test passed")
        
    except Exception as e:
        test_result.update({
            "status": "failed",
            "error": str(e),
            "suggestions": [
                "Check if PGVECTOR_PASSWORD is correct",
                "Verify network connectivity to database",
                "Check if database server is running",
                "Confirm database and table exist"
            ]
        })
        logger.error(f"❌ Database connectivity test failed: {e}")
    
    test_result["duration"] = time.time() - test_result["start_time"]
    return test_result

async def establish_real_baseline():
    """Establish real performance baseline by measuring current system."""
    logger.info("Establishing real performance baseline...")
    
    test_result = {
        "test_name": "baseline_establishment",
        "start_time": time.time(),
        "status": "running"
    }
    
    try:
        from memory_service.config import DatabaseConfig
        from memory_service.performance_monitor import VectorPerformanceMonitor
        import asyncpg
        
        # Check credentials
        password = os.getenv("PGVECTOR_PASSWORD") or os.getenv("PGPASSWORD")
        if not password:
            test_result.update({
                "status": "skipped",
                "reason": "No database credentials available"
            })
            return test_result
        
        # Create connection pool
        host = os.getenv("PGVECTOR_HOST", DatabaseConfig.HOST)
        port = os.getenv("PGVECTOR_PORT", DatabaseConfig.PORT)
        database = os.getenv("PGVECTOR_DATABASE", DatabaseConfig.DATABASE)
        user = os.getenv("PGVECTOR_USER", DatabaseConfig.USER)
        
        conn_str = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        
        pool = await asyncpg.create_pool(
            conn_str,
            min_size=2,
            max_size=5,
            command_timeout=30
        )
        
        # Run baseline performance test
        monitor = VectorPerformanceMonitor(pool, "vector_memories")
        
        logger.info("Running baseline performance measurement...")
        baseline_results = await monitor.run_comprehensive_benchmark(
            num_queries=20,  # Reasonable test size
            concurrent_queries=5
        )
        
        await pool.close()
        
        # Extract key metrics
        single_perf = baseline_results.get("single_query_performance", {})
        concurrent_perf = baseline_results.get("concurrent_performance", {})
        db_stats = baseline_results.get("database_stats", {})
        
        key_metrics = {
            "avg_latency_ms": single_perf.get("avg_latency_ms", 0),
            "p95_latency_ms": single_perf.get("p95_latency_ms", 0),
            "p99_latency_ms": single_perf.get("p99_latency_ms", 0),
            "throughput_qps": concurrent_perf.get("throughput_qps", 0),
            "error_rate": single_perf.get("error_rate", 0),
            "vector_count": db_stats.get("total_vectors", 0),
            "table_size": db_stats.get("table_size", "unknown")
        }
        
        test_result.update({
            "status": "passed",
            "baseline_metrics": key_metrics,
            "full_results": baseline_results,
            "improvement_opportunity": {
                "current_p95_latency": key_metrics["p95_latency_ms"],
                "target_p95_latency": 20,
                "potential_improvement": f"{((key_metrics['p95_latency_ms'] - 20) / key_metrics['p95_latency_ms'] * 100):.1f}%" if key_metrics["p95_latency_ms"] > 20 else "Already optimized"
            }
        })
        
        logger.info(f"✅ Baseline established - P95 latency: {key_metrics['p95_latency_ms']:.1f}ms")
        
    except Exception as e:
        test_result.update({
            "status": "failed",
            "error": str(e)
        })
        logger.error(f"❌ Baseline establishment failed: {e}")
    
    test_result["duration"] = time.time() - test_result["start_time"]
    return test_result

async def validate_monitoring_system():
    """Validate performance monitoring system with real data."""
    logger.info("Validating monitoring system with real data...")
    
    test_result = {
        "test_name": "monitoring_validation", 
        "start_time": time.time(),
        "status": "running"
    }
    
    try:
        # Import and test monitoring components
        from memory_service.performance_monitor import VectorPerformanceMonitor, PerformanceMetrics, QueryResult
        
        # Check if all required classes exist
        validation_checks = {
            "VectorPerformanceMonitor_available": VectorPerformanceMonitor is not None,
            "PerformanceMetrics_available": PerformanceMetrics is not None,
            "QueryResult_available": QueryResult is not None
        }
        
        # If we have database access, test with real data
        password = os.getenv("PGVECTOR_PASSWORD") or os.getenv("PGPASSWORD")
        if password:
            try:
                import asyncpg
                from memory_service.config import DatabaseConfig
                
                host = os.getenv("PGVECTOR_HOST", DatabaseConfig.HOST)
                port = os.getenv("PGVECTOR_PORT", DatabaseConfig.PORT)
                database = os.getenv("PGVECTOR_DATABASE", DatabaseConfig.DATABASE)
                user = os.getenv("PGVECTOR_USER", DatabaseConfig.USER)
                
                conn_str = f"postgresql://{user}:{password}@{host}:{port}/{database}"
                
                pool = await asyncpg.create_pool(
                    conn_str,
                    min_size=1,
                    max_size=2,
                    command_timeout=15
                )
                
                monitor = VectorPerformanceMonitor(pool)
                
                # Test quick benchmark
                quick_results = await monitor.run_comprehensive_benchmark(
                    num_queries=5,
                    concurrent_queries=2
                )
                
                await pool.close()
                
                validation_checks["real_data_test"] = True
                validation_checks["benchmark_structure_valid"] = all(
                    key in quick_results for key in 
                    ["timestamp", "single_query_performance", "summary"]
                )
                
            except Exception as e:
                validation_checks["real_data_test"] = False
                validation_checks["real_data_error"] = str(e)
        else:
            validation_checks["real_data_test"] = False
            validation_checks["no_credentials"] = True
        
        test_result.update({
            "status": "passed" if all(v for k, v in validation_checks.items() if not k.endswith("_error") and not k.endswith("no_credentials")) else "passed_with_warnings",
            "validation_checks": validation_checks,
            "monitoring_system_ready": all(validation_checks[k] for k in ["VectorPerformanceMonitor_available", "PerformanceMetrics_available", "QueryResult_available"])
        })
        
        logger.info("✅ Monitoring system validation completed")
        
    except Exception as e:
        test_result.update({
            "status": "failed",
            "error": str(e)
        })
        logger.error(f"❌ Monitoring system validation failed: {e}")
    
    test_result["duration"] = time.time() - test_result["start_time"]
    return test_result

async def document_environment():
    """Document current environment configuration for rollback reference."""
    logger.info("Documenting current environment configuration...")
    
    test_result = {
        "test_name": "environment_documentation",
        "start_time": time.time(),
        "status": "running"
    }
    
    try:
        env_documentation = {
            "system_info": {
                "python_version": sys.version,
                "working_directory": os.getcwd(),
                "timestamp": time.time()
            },
            "environment_variables": {
                "PGVECTOR_HOST": os.getenv("PGVECTOR_HOST", "not_set"),
                "PGVECTOR_PORT": os.getenv("PGVECTOR_PORT", "not_set"),
                "PGVECTOR_DATABASE": os.getenv("PGVECTOR_DATABASE", "not_set"),
                "PGVECTOR_USER": os.getenv("PGVECTOR_USER", "not_set"),
                "PGVECTOR_PASSWORD": "***REDACTED***" if os.getenv("PGVECTOR_PASSWORD") else "not_set"
            },
            "dependency_status": {},
            "database_config": {}
        }
        
        # Test key dependencies
        dependencies_to_test = [
            "fastapi", "uvicorn", "asyncpg", "pgvector", "numpy", "openai"
        ]
        
        for dep in dependencies_to_test:
            try:
                __import__(dep)
                env_documentation["dependency_status"][dep] = "available"
            except ImportError:
                env_documentation["dependency_status"][dep] = "missing"
        
        # Get database configuration if possible
        password = os.getenv("PGVECTOR_PASSWORD") or os.getenv("PGPASSWORD")
        if password:
            try:
                from memory_service.config import DatabaseConfig
                import asyncpg
                
                host = os.getenv("PGVECTOR_HOST", DatabaseConfig.HOST)
                port = os.getenv("PGVECTOR_PORT", DatabaseConfig.PORT)
                database = os.getenv("PGVECTOR_DATABASE", DatabaseConfig.DATABASE)
                user = os.getenv("PGVECTOR_USER", DatabaseConfig.USER)
                
                conn = await asyncpg.connect(
                    f"postgresql://{user}:{password}@{host}:{port}/{database}",
                    command_timeout=10
                )
                
                # Get current database configuration
                db_config_queries = {
                    "work_mem": "SHOW work_mem",
                    "shared_buffers": "SHOW shared_buffers", 
                    "random_page_cost": "SHOW random_page_cost",
                    "jit": "SHOW jit"
                }
                
                for setting, query in db_config_queries.items():
                    try:
                        value = await conn.fetchval(query)
                        env_documentation["database_config"][setting] = value
                    except Exception:
                        env_documentation["database_config"][setting] = "unable_to_query"
                
                # Check for HNSW settings
                try:
                    ef_search = await conn.fetchval("SHOW hnsw.ef_search")
                    env_documentation["database_config"]["hnsw_ef_search"] = ef_search
                except Exception:
                    env_documentation["database_config"]["hnsw_ef_search"] = "not_available"
                
                await conn.close()
                
            except Exception as e:
                env_documentation["database_config"]["error"] = str(e)
        
        # Save documentation to file
        with open("stage1_environment_snapshot.json", "w") as f:
            json.dump(env_documentation, f, indent=2, default=str)
        
        test_result.update({
            "status": "passed",
            "documentation": env_documentation,
            "documentation_file": "stage1_environment_snapshot.json"
        })
        
        logger.info("✅ Environment documentation completed")
        
    except Exception as e:
        test_result.update({
            "status": "failed",
            "error": str(e)
        })
        logger.error(f"❌ Environment documentation failed: {e}")
    
    test_result["duration"] = time.time() - test_result["start_time"]
    return test_result

async def main():
    """Main Stage 1 testing function."""
    logger.info("=== STAGE 1: Environment & Baseline Establishment ===")
    start_time = time.time()
    
    # Run all Stage 1 tests
    results = {
        "stage": "Stage 1: Environment & Baseline Establishment",
        "start_time": start_time,
        "tests": {}
    }
    
    # Test 1: Database Connectivity
    results["tests"]["database_connectivity"] = await test_database_connectivity()
    
    # Test 2: Real Baseline Establishment
    results["tests"]["baseline_establishment"] = await establish_real_baseline()
    
    # Test 3: Monitoring System Validation  
    results["tests"]["monitoring_validation"] = await validate_monitoring_system()
    
    # Test 4: Environment Documentation
    results["tests"]["environment_documentation"] = await document_environment()
    
    # Generate summary
    total_tests = len(results["tests"])
    passed_tests = sum(1 for test in results["tests"].values() if test.get("status") == "passed")
    failed_tests = sum(1 for test in results["tests"].values() if test.get("status") == "failed")
    skipped_tests = sum(1 for test in results["tests"].values() if test.get("status") == "skipped")
    
    results["summary"] = {
        "total_duration": time.time() - start_time,
        "total_tests": total_tests,
        "passed": passed_tests,
        "failed": failed_tests,
        "skipped": skipped_tests,
        "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
        "stage_1_ready": (passed_tests >= 3 and failed_tests == 0)  # At least 3 core tests must pass
    }
    
    # Print summary
    logger.info("=== STAGE 1 SUMMARY ===")
    logger.info(f"Passed: {passed_tests}/{total_tests}")
    logger.info(f"Failed: {failed_tests}")
    logger.info(f"Skipped: {skipped_tests}")
    logger.info(f"Success Rate: {results['summary']['success_rate']:.1%}")
    logger.info(f"Duration: {results['summary']['total_duration']:.2f}s")
    
    if results["summary"]["stage_1_ready"]:
        logger.info("✅ STAGE 1 READY - Proceed to Stage 2: PostgreSQL Configuration")
    else:
        logger.info("❌ STAGE 1 NOT READY - Address failing tests before proceeding")
    
    # Save results
    with open("stage1_test_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info("Results saved to stage1_test_results.json")
    return results

if __name__ == "__main__":
    asyncio.run(main())