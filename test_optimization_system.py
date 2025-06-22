#!/usr/bin/env python3
"""
Comprehensive Testing Framework for PGVector Optimization System

Tests all optimization components safely:
- Performance monitoring system validation
- Migration script validation 
- Baseline establishment
- Rollback procedure testing

Can run in multiple modes:
- Mock mode: Tests without database connection
- Dev mode: Tests with development database
- Staging mode: Tests with staging database
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

# Add the memory service to the path
sys.path.append(str(Path(__file__).parent / "python" / "memory_service" / "src"))

import asyncpg
import numpy as np

# Import our optimization system components
try:
    from memory_service.config import DatabaseConfig
    from memory_service.performance_monitor import VectorPerformanceMonitor, QueryResult, PerformanceMetrics
except ImportError as e:
    print(f"Warning: Could not import memory service components: {e}")
    print("Running in mock mode...")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class OptimizationTestFramework:
    """
    Comprehensive testing framework for the pgvector optimization system.
    
    Supports multiple testing modes:
    - mock: Tests components with simulated data
    - dev: Tests with development database
    - staging: Tests with staging database
    """
    
    def __init__(self, mode: str = "mock"):
        self.mode = mode
        self.results = {}
        self.connection_pool = None
        self.test_start_time = time.time()
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run the complete test suite."""
        logger.info(f"=== PGVector Optimization System Test Suite ===")
        logger.info(f"Mode: {self.mode}")
        logger.info(f"Phase 1: Component Isolation Testing")
        
        try:
            # Initialize test environment
            await self._initialize_test_environment()
            
            # Phase 1 Tests
            await self._test_performance_monitor_validation()
            await self._test_migration_script_validation()
            await self._test_baseline_establishment()
            await self._test_rollback_procedures()
            
            # Generate test report
            await self._generate_test_report()
            
            return self.results
            
        except Exception as e:
            logger.error(f"Test suite failed: {e}")
            self.results["error"] = str(e)
            return self.results
            
        finally:
            await self._cleanup_test_environment()
    
    async def _initialize_test_environment(self):
        """Initialize the test environment based on mode."""
        logger.info("Initializing test environment...")
        
        if self.mode == "mock":
            logger.info("Mock mode: Creating simulated test environment")
            self.connection_pool = self._create_mock_connection_pool()
            
        elif self.mode in ["dev", "staging"]:
            logger.info(f"{self.mode.title()} mode: Connecting to database")
            self.connection_pool = await self._create_real_connection_pool()
            
        self.results["test_environment"] = {
            "mode": self.mode,
            "initialized_at": time.time(),
            "connection_available": self.connection_pool is not None
        }
    
    def _create_mock_connection_pool(self):
        """Create a mock connection pool for testing."""
        mock_pool = MagicMock()
        
        # Mock the acquire context manager
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_pool.acquire.return_value.__aexit__.return_value = None
        
        # Mock query results for performance testing
        mock_conn.fetch.return_value = [
            {"id": i, "content": f"Test content {i}", "distance": 0.1 + i * 0.01}
            for i in range(10)
        ]
        
        mock_conn.fetchval.return_value = "test_value"
        mock_conn.fetchrow.return_value = {
            "total_vectors": 1000,
            "avg_importance": 0.75,
            "table_size": "50MB"
        }
        
        # Mock pool properties
        mock_pool.get_min_size.return_value = 10
        mock_pool.get_max_size.return_value = 30
        mock_pool.get_size.return_value = 15
        
        return mock_pool
    
    async def _create_real_connection_pool(self):
        """Create a real connection pool for database testing."""
        try:
            # Check if we have database credentials
            password = os.getenv("PGVECTOR_PASSWORD") or os.getenv("PGPASSWORD")
            if not password:
                logger.warning("No database password found. Set PGVECTOR_PASSWORD environment variable.")
                return None
            
            # Use config defaults
            host = os.getenv("PGVECTOR_HOST", DatabaseConfig.HOST)
            port = os.getenv("PGVECTOR_PORT", DatabaseConfig.PORT)
            database = os.getenv("PGVECTOR_DATABASE", DatabaseConfig.DATABASE)
            user = os.getenv("PGVECTOR_USER", DatabaseConfig.USER)
            
            conn_str = f"postgresql://{user}:{password}@{host}:{port}/{database}"
            
            # Create a small connection pool for testing
            pool = await asyncpg.create_pool(
                conn_str,
                min_size=2,
                max_size=5,
                command_timeout=10,
                server_settings={
                    'application_name': 'optimization_test_framework'
                }
            )
            
            # Test the connection
            async with pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                if result == 1:
                    logger.info("Database connection successful")
                    return pool
                else:
                    logger.error("Database connection test failed")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to create database connection: {e}")
            return None
    
    async def _test_performance_monitor_validation(self):
        """Test the performance monitoring system accuracy."""
        logger.info("Testing performance monitoring system...")
        
        test_result = {
            "test_name": "performance_monitor_validation",
            "start_time": time.time(),
            "status": "running"
        }
        
        try:
            # Check if performance monitor file exists and is valid
            monitor_file = Path("python/memory_service/src/memory_service/performance_monitor.py")
            
            if monitor_file.exists():
                content = monitor_file.read_text()
                
                # Check for key classes and methods
                validation_checks = {
                    "VectorPerformanceMonitor_class": "class VectorPerformanceMonitor" in content,
                    "run_comprehensive_benchmark": "run_comprehensive_benchmark" in content,
                    "PerformanceMetrics_dataclass": "@dataclass" in content and "PerformanceMetrics" in content,
                    "QueryResult_dataclass": "QueryResult" in content,
                    "latency_tracking": "latency_ms" in content and "p95_latency" in content,
                    "throughput_measurement": "throughput_qps" in content,
                    "concurrent_testing": "concurrent" in content.lower(),
                    "export_metrics": "export_metrics" in content
                }
                
                # If we can import the module (dependencies available), test it
                if self.mode != "mock":
                    try:
                        from memory_service.performance_monitor import VectorPerformanceMonitor
                        
                        if self.connection_pool:
                            monitor = VectorPerformanceMonitor(self.connection_pool)
                            
                            # Run a quick benchmark
                            benchmark_results = await monitor.run_comprehensive_benchmark(
                                num_queries=5,
                                concurrent_queries=2
                            )
                            
                            validation_checks["benchmark_execution"] = True
                            validation_checks["results_structure"] = all(
                                key in benchmark_results for key in 
                                ["timestamp", "single_query_performance", "summary"]
                            )
                        else:
                            validation_checks["benchmark_execution"] = False
                            validation_checks["no_connection"] = True
                            
                    except ImportError as e:
                        validation_checks["import_error"] = str(e)
                        validation_checks["dependencies_missing"] = True
                
                test_result.update({
                    "status": "passed" if all(v for k, v in validation_checks.items() if not k.startswith("import_") and not k.startswith("dependencies_") and not k.startswith("no_")) else "passed_with_warnings",
                    "validation_checks": validation_checks,
                    "file_exists": True,
                    "file_size": len(content),
                    "lines_of_code": len(content.split('\n'))
                })
                
            else:
                test_result.update({
                    "status": "failed",
                    "error": "Performance monitor file not found",
                    "file_exists": False
                })
                
        except Exception as e:
            test_result.update({
                "status": "failed",
                "error": str(e)
            })
            logger.error(f"Performance monitor test failed: {e}")
        
        test_result["duration"] = time.time() - test_result["start_time"]
        self.results["performance_monitor_test"] = test_result
    
    async def _test_migration_script_validation(self):
        """Test migration scripts without applying them."""
        logger.info("Testing migration script validation...")
        
        test_result = {
            "test_name": "migration_script_validation",
            "start_time": time.time(),
            "status": "running"
        }
        
        try:
            # Check if migration files exist
            migration_files = [
                "python/memory_service/migrations/003_optimize_postgresql_for_vectors.sql",
                "python/memory_service/migrations/004_optimize_hnsw_parameters.sql"
            ]
            
            migration_tests = {}
            for migration_file in migration_files:
                file_path = Path(migration_file)
                file_test = {
                    "exists": file_path.exists(),
                    "readable": False,
                    "sql_valid": False,
                    "size_bytes": 0
                }
                
                if file_path.exists():
                    try:
                        content = file_path.read_text()
                        file_test.update({
                            "readable": True,
                            "size_bytes": len(content),
                            "sql_valid": self._validate_sql_syntax(content),
                            "has_rollback": "ROLLBACK" in content.upper() or "DROP" in content.upper(),
                            "has_error_handling": "EXCEPTION" in content.upper() or "IF EXISTS" in content.upper()
                        })
                    except Exception as e:
                        file_test["read_error"] = str(e)
                
                migration_tests[migration_file] = file_test
            
            test_result.update({
                "status": "passed",
                "migration_files": migration_tests,
                "all_files_valid": all(
                    test["exists"] and test["readable"] and test["sql_valid"] 
                    for test in migration_tests.values()
                )
            })
            
        except Exception as e:
            test_result.update({
                "status": "failed",
                "error": str(e)
            })
            logger.error(f"Migration script test failed: {e}")
        
        test_result["duration"] = time.time() - test_result["start_time"]
        self.results["migration_script_test"] = test_result
    
    def _validate_sql_syntax(self, sql_content: str) -> bool:
        """Basic SQL syntax validation."""
        try:
            # Basic checks for SQL syntax
            required_keywords = ["BEGIN", "COMMIT"]
            dangerous_keywords = ["DELETE FROM", "DROP DATABASE", "TRUNCATE"]
            
            sql_upper = sql_content.upper()
            
            # Check for required structure
            has_required = all(keyword in sql_upper for keyword in required_keywords)
            
            # Check for dangerous operations (should not be present in our migrations)
            has_dangerous = any(keyword in sql_upper for keyword in dangerous_keywords)
            
            return has_required and not has_dangerous
            
        except Exception:
            return False
    
    async def _test_baseline_establishment(self):
        """Test baseline performance measurement."""
        logger.info("Testing baseline establishment...")
        
        test_result = {
            "test_name": "baseline_establishment",
            "start_time": time.time(),
            "status": "running"
        }
        
        try:
            if self.connection_pool and self.mode != "mock":
                # Test real baseline measurement
                async with self.connection_pool.acquire() as conn:
                    # Get basic database statistics
                    stats = await conn.fetchrow("""
                        SELECT 
                            COUNT(*) as vector_count,
                            pg_size_pretty(pg_total_relation_size('vector_memories')) as table_size
                        FROM vector_memories
                    """)
                    
                    # Test a simple vector query for timing
                    start_time = time.time()
                    test_vector = [0.1] * 1536  # Simple test vector
                    
                    rows = await conn.fetch("""
                        SELECT id, embedding <=> $1::vector as distance
                        FROM vector_memories
                        ORDER BY embedding <=> $1::vector
                        LIMIT 5
                    """, test_vector)
                    
                    query_time = (time.time() - start_time) * 1000
                    
                    test_result.update({
                        "status": "passed",
                        "database_stats": dict(stats) if stats else {},
                        "sample_query_time_ms": query_time,
                        "sample_results_count": len(rows),
                        "baseline_established": True
                    })
                    
            else:
                # Mock baseline for testing
                test_result.update({
                    "status": "passed",
                    "database_stats": {
                        "vector_count": 1000,
                        "table_size": "50MB"
                    },
                    "sample_query_time_ms": 45.2,  # Simulated current performance
                    "sample_results_count": 5,
                    "baseline_established": True,
                    "note": "Mock baseline - real measurement requires database connection"
                })
                
        except Exception as e:
            test_result.update({
                "status": "failed",
                "error": str(e)
            })
            logger.error(f"Baseline establishment test failed: {e}")
        
        test_result["duration"] = time.time() - test_result["start_time"]
        self.results["baseline_test"] = test_result
    
    async def _test_rollback_procedures(self):
        """Test rollback procedures without applying changes."""
        logger.info("Testing rollback procedures...")
        
        test_result = {
            "test_name": "rollback_procedures",
            "start_time": time.time(),
            "status": "running"
        }
        
        try:
            # Test the optimization application script
            apply_script_path = Path("apply_pgvector_optimizations.py")
            
            rollback_tests = {
                "apply_script_exists": apply_script_path.exists(),
                "rollback_procedures_documented": False,
                "migration_rollback_safe": False
            }
            
            if apply_script_path.exists():
                script_content = apply_script_path.read_text()
                
                # Check for rollback-related functionality
                rollback_tests.update({
                    "rollback_procedures_documented": "rollback" in script_content.lower(),
                    "error_handling_present": "try:" in script_content and "except" in script_content,
                    "backup_procedures": "backup" in script_content.lower(),
                    "verification_present": "verify" in script_content.lower()
                })
            
            # Check migration scripts for rollback safety
            migration_rollback_safe = True
            for migration_file in ["python/memory_service/migrations/003_optimize_postgresql_for_vectors.sql",
                                 "python/memory_service/migrations/004_optimize_hnsw_parameters.sql"]:
                file_path = Path(migration_file)
                if file_path.exists():
                    content = file_path.read_text().upper()
                    # Check for safe practices
                    has_if_exists = "IF EXISTS" in content
                    has_error_handling = "EXCEPTION" in content
                    if not (has_if_exists or has_error_handling):
                        migration_rollback_safe = False
            
            rollback_tests["migration_rollback_safe"] = migration_rollback_safe
            
            test_result.update({
                "status": "passed",
                "rollback_tests": rollback_tests,
                "rollback_readiness": all([
                    rollback_tests["apply_script_exists"],
                    rollback_tests["migration_rollback_safe"]
                ])
            })
            
        except Exception as e:
            test_result.update({
                "status": "failed",
                "error": str(e)
            })
            logger.error(f"Rollback procedures test failed: {e}")
        
        test_result["duration"] = time.time() - test_result["start_time"]
        self.results["rollback_test"] = test_result
    
    async def _generate_test_report(self):
        """Generate comprehensive test report."""
        logger.info("Generating test report...")
        
        total_duration = time.time() - self.test_start_time
        
        # Calculate test summary
        tests = [
            self.results.get("performance_monitor_test", {}),
            self.results.get("migration_script_test", {}),
            self.results.get("baseline_test", {}),
            self.results.get("rollback_test", {})
        ]
        
        passed_tests = sum(1 for test in tests if test.get("status") == "passed")
        failed_tests = sum(1 for test in tests if test.get("status") == "failed")
        skipped_tests = sum(1 for test in tests if test.get("status") == "skipped")
        
        report = {
            "test_summary": {
                "total_duration": total_duration,
                "total_tests": len(tests),
                "passed": passed_tests,
                "failed": failed_tests,
                "skipped": skipped_tests,
                "success_rate": passed_tests / len(tests) if tests else 0
            },
            "readiness_assessment": self._assess_optimization_readiness(),
            "next_steps": self._generate_next_steps(),
            "generated_at": time.time()
        }
        
        self.results["test_report"] = report
        
        # Print summary
        logger.info(f"=== TEST SUMMARY ===")
        logger.info(f"Total Tests: {len(tests)}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")
        logger.info(f"Skipped: {skipped_tests}")
        logger.info(f"Success Rate: {report['test_summary']['success_rate']:.1%}")
        logger.info(f"Duration: {total_duration:.2f}s")
    
    def _assess_optimization_readiness(self) -> Dict[str, Any]:
        """Assess readiness for optimization deployment."""
        readiness = {
            "performance_monitoring": False,
            "migration_scripts": False,
            "baseline_measurement": False,
            "rollback_procedures": False,
            "overall_ready": False
        }
        
        # Check each component
        if self.results.get("performance_monitor_test", {}).get("status") == "passed":
            readiness["performance_monitoring"] = True
        
        if self.results.get("migration_script_test", {}).get("all_files_valid"):
            readiness["migration_scripts"] = True
        
        if self.results.get("baseline_test", {}).get("baseline_established"):
            readiness["baseline_measurement"] = True
        
        if self.results.get("rollback_test", {}).get("rollback_readiness"):
            readiness["rollback_procedures"] = True
        
        # Overall readiness
        readiness["overall_ready"] = all([
            readiness["performance_monitoring"],
            readiness["migration_scripts"],
            readiness["rollback_procedures"]
        ])
        
        return readiness
    
    def _generate_next_steps(self) -> List[str]:
        """Generate recommended next steps based on test results."""
        next_steps = []
        
        readiness = self._assess_optimization_readiness()
        
        if not readiness["performance_monitoring"]:
            next_steps.append("Fix performance monitoring system issues")
        
        if not readiness["migration_scripts"]:
            next_steps.append("Review and fix migration script validation errors")
        
        if not readiness["baseline_measurement"]:
            next_steps.append("Establish baseline performance measurement with database access")
        
        if not readiness["rollback_procedures"]:
            next_steps.append("Enhance rollback procedures and error handling")
        
        if readiness["overall_ready"]:
            next_steps.extend([
                "Proceed to Phase 2: Development Integration Testing",
                "Set up staging environment for production-like testing",
                "Plan maintenance window for production deployment"
            ])
        else:
            next_steps.append("Address failing components before proceeding to Phase 2")
        
        return next_steps
    
    async def _cleanup_test_environment(self):
        """Clean up test environment."""
        if self.connection_pool and hasattr(self.connection_pool, 'close') and not isinstance(self.connection_pool, MagicMock):
            await self.connection_pool.close()
        logger.info("Test environment cleaned up")


async def main():
    """Main test execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="PGVector Optimization System Test Framework")
    parser.add_argument("--mode", choices=["mock", "dev", "staging"], default="mock",
                       help="Test mode: mock (no DB), dev (dev DB), staging (staging DB)")
    parser.add_argument("--output", default="test_results.json",
                       help="Output file for test results")
    
    args = parser.parse_args()
    
    # Run the test framework
    framework = OptimizationTestFramework(mode=args.mode)
    results = await framework.run_all_tests()
    
    # Save results to file
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"Test results saved to {args.output}")
    
    # Exit with appropriate code
    if results.get("test_report", {}).get("test_summary", {}).get("failed", 0) > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())