#!/usr/bin/env python3
"""
Production Database Optimization Coordinator

Coordinates safe production database optimization with comprehensive team coordination,
monitoring, and safety procedures.

Phase A: Secure Production Access & Preparation
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add the memory service to the path
sys.path.append(str(Path(__file__).parent / "python" / "memory_service" / "src"))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProductionOptimizationCoordinator:
    """
    Coordinates production database optimization with comprehensive safety measures.
    """
    
    def __init__(self):
        self.start_time = time.time()
        self.phase = "Phase A: Preparation"
        self.results = {
            "coordination_session": {
                "start_time": self.start_time,
                "phase": self.phase,
                "coordinator_version": "1.0.0"
            }
        }
    
    async def execute_phase_a_preparation(self) -> Dict[str, Any]:
        """Execute Phase A: Secure Production Access & Preparation."""
        logger.info("=== PHASE A: SECURE PRODUCTION ACCESS & PREPARATION ===")
        logger.info("Goal: Establish safe, monitored access to production database")
        
        try:
            # Step 1: Credential Management
            await self._coordinate_credential_acquisition()
            
            # Step 2: Read-Only Validation
            await self._perform_read_only_validation()
            
            # Step 3: Baseline Establishment
            await self._establish_production_baseline()
            
            # Step 4: Team Coordination
            await self._coordinate_team_scheduling()
            
            # Generate Phase A Summary
            await self._generate_phase_a_summary()
            
            return self.results
            
        except Exception as e:
            logger.error(f"Phase A execution failed: {e}")
            self.results["phase_a_error"] = str(e)
            return self.results
    
    async def _coordinate_credential_acquisition(self):
        """Coordinate with DevOps team for production database access."""
        logger.info("Step 1: Coordinating credential acquisition...")
        
        credential_info = {
            "step": "credential_acquisition",
            "start_time": time.time(),
            "status": "coordinating"
        }
        
        try:
            # Check current credential status
            password = os.getenv("PGVECTOR_PASSWORD") or os.getenv("PGPASSWORD")
            
            if password:
                credential_info.update({
                    "status": "credentials_available",
                    "source": "environment_variable",
                    "ready_for_testing": True
                })
                logger.info("✅ Production credentials already available")
            else:
                # Generate coordination instructions
                coordination_plan = {
                    "required_credential": "PGVECTOR_PASSWORD",
                    "target_database": {
                        "host": "dpg-d12n0np5pdvs73ctmm40-a",
                        "port": 5432,
                        "database": "nexus_memory_db",
                        "user": "nexus_memory_db_user"
                    },
                    "coordination_steps": [
                        "Contact DevOps team for production database password",
                        "Verify password is for read/write optimization access",
                        "Confirm backup procedures are current and tested",
                        "Coordinate maintenance window scheduling"
                    ],
                    "security_requirements": [
                        "Password should be provided securely (not in plaintext)",
                        "Access should be limited to optimization period",
                        "All operations should be logged and monitored",
                        "Rollback procedures must be tested and ready"
                    ],
                    "team_contacts": [
                        "DevOps team: Database credentials and backup verification",
                        "Database team: Schema modification permissions",
                        "Product team: Maintenance window coordination",
                        "Engineering team: Code review and rollback procedures"
                    ]
                }
                
                credential_info.update({
                    "status": "coordination_required",
                    "coordination_plan": coordination_plan,
                    "ready_for_testing": False
                })
                
                logger.info("❌ Production credentials required")
                logger.info("Coordination plan generated for team coordination")
                
                # Save coordination plan for team reference
                with open("production_coordination_plan.json", "w") as f:
                    json.dump(coordination_plan, f, indent=2, default=str)
                
                logger.info("📋 Coordination plan saved to production_coordination_plan.json")
            
        except Exception as e:
            credential_info.update({
                "status": "failed",
                "error": str(e)
            })
            logger.error(f"Credential coordination failed: {e}")
        
        credential_info["duration"] = time.time() - credential_info["start_time"]
        self.results["credential_acquisition"] = credential_info
    
    async def _perform_read_only_validation(self):
        """Test database connectivity with monitoring-only operations."""
        logger.info("Step 2: Performing read-only validation...")
        
        validation_info = {
            "step": "read_only_validation",
            "start_time": time.time(),
            "status": "testing"
        }
        
        try:
            # Check if credentials are available
            password = os.getenv("PGVECTOR_PASSWORD") or os.getenv("PGPASSWORD")
            
            if not password:
                validation_info.update({
                    "status": "skipped",
                    "reason": "No production credentials available",
                    "next_action": "Complete credential acquisition first"
                })
                logger.info("⏭️  Read-only validation skipped - credentials required")
                self.results["read_only_validation"] = validation_info
                return
            
            # Import required components
            from memory_service.config import DatabaseConfig
            import asyncpg
            
            # Test production database connectivity
            conn_str = f"postgresql://{DatabaseConfig.USER}:{DatabaseConfig.PASSWORD}@{DatabaseConfig.HOST}:{DatabaseConfig.PORT}/{DatabaseConfig.DATABASE}"
            logger.info(f"Testing connection to: {DatabaseConfig.USER}@{DatabaseConfig.HOST}:{DatabaseConfig.PORT}/{DatabaseConfig.DATABASE}")
            
            conn = await asyncpg.connect(conn_str, command_timeout=15)
            
            # Read-only validation tests
            validation_tests = {
                "basic_connectivity": False,
                "vector_extension": False,
                "table_access": False,
                "sample_query": False,
                "current_configuration": False
            }
            
            # Test 1: Basic connectivity
            version = await conn.fetchval("SELECT version()")
            validation_tests["basic_connectivity"] = bool(version)
            logger.info(f"✅ Connected to: {version[:50]}...")
            
            # Test 2: Vector extension
            vector_ext = await conn.fetchval("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            validation_tests["vector_extension"] = bool(vector_ext)
            logger.info(f"✅ Vector extension: {vector_ext}")
            
            # Test 3: Table access
            table_count = await conn.fetchval("SELECT COUNT(*) FROM vector_memories")
            table_size = await conn.fetchval("SELECT pg_size_pretty(pg_total_relation_size('vector_memories'))")
            validation_tests["table_access"] = True
            logger.info(f"✅ vector_memories: {table_count} records, {table_size}")
            
            # Test 4: Sample vector query
            start_time = time.time()
            test_vector = [0.1] * 1536
            rows = await conn.fetch("""
                SELECT id, embedding <=> $1::vector as distance
                FROM vector_memories
                ORDER BY embedding <=> $1::vector
                LIMIT 5
            """, test_vector)
            query_time = (time.time() - start_time) * 1000
            validation_tests["sample_query"] = True
            logger.info(f"✅ Sample query: {len(rows)} results in {query_time:.1f}ms")
            
            # Test 5: Current configuration
            current_config = {}
            config_queries = {
                "work_mem": "SHOW work_mem",
                "shared_buffers": "SHOW shared_buffers",
                "random_page_cost": "SHOW random_page_cost",
                "jit": "SHOW jit"
            }
            
            for setting, query in config_queries.items():
                try:
                    value = await conn.fetchval(query)
                    current_config[setting] = value
                except Exception:
                    current_config[setting] = "unable_to_query"
            
            # Try to get HNSW settings
            try:
                ef_search = await conn.fetchval("SHOW hnsw.ef_search")
                current_config["hnsw_ef_search"] = ef_search
            except Exception:
                current_config["hnsw_ef_search"] = "not_available_or_default"
            
            validation_tests["current_configuration"] = True
            
            await conn.close()
            
            validation_info.update({
                "status": "passed",
                "validation_tests": validation_tests,
                "production_metrics": {
                    "database_version": version,
                    "vector_extension": vector_ext,
                    "table_records": table_count,
                    "table_size": table_size,
                    "sample_query_ms": query_time
                },
                "current_configuration": current_config,
                "ready_for_baseline": True
            })
            
            logger.info("✅ Read-only validation successful")
            logger.info(f"🎯 Current sample query time: {query_time:.1f}ms")
            
        except Exception as e:
            validation_info.update({
                "status": "failed",
                "error": str(e),
                "ready_for_baseline": False
            })
            logger.error(f"Read-only validation failed: {e}")
        
        validation_info["duration"] = time.time() - validation_info["start_time"]
        self.results["read_only_validation"] = validation_info
    
    async def _establish_production_baseline(self):
        """Comprehensive performance measurement of current production system."""
        logger.info("Step 3: Establishing production baseline...")
        
        baseline_info = {
            "step": "baseline_establishment",
            "start_time": time.time(),
            "status": "measuring"
        }
        
        try:
            # Check prerequisites
            if not self.results.get("read_only_validation", {}).get("ready_for_baseline"):
                baseline_info.update({
                    "status": "skipped",
                    "reason": "Read-only validation not successful",
                    "next_action": "Complete read-only validation first"
                })
                logger.info("⏭️  Baseline establishment skipped - validation required")
                self.results["baseline_establishment"] = baseline_info
                return
            
            # Import performance monitoring system
            from memory_service.config import DatabaseConfig
            from memory_service.performance_monitor import VectorPerformanceMonitor
            import asyncpg
            
            # Create production connection pool
            conn_str = f"postgresql://{DatabaseConfig.USER}:{DatabaseConfig.PASSWORD}@{DatabaseConfig.HOST}:{DatabaseConfig.PORT}/{DatabaseConfig.DATABASE}"
            
            pool = await asyncpg.create_pool(
                conn_str,
                min_size=3,
                max_size=8,
                command_timeout=30,
                server_settings={
                    'application_name': 'production_baseline_measurement'
                }
            )
            
            # Run comprehensive baseline measurement
            monitor = VectorPerformanceMonitor(pool, "vector_memories")
            
            logger.info("Running production baseline measurement (may take 2-3 minutes)...")
            baseline_results = await monitor.run_comprehensive_benchmark(
                num_queries=50,  # Reasonable production test
                concurrent_queries=8
            )
            
            await pool.close()
            
            # Extract key baseline metrics
            single_perf = baseline_results.get("single_query_performance", {})
            concurrent_perf = baseline_results.get("concurrent_performance", {})
            db_stats = baseline_results.get("database_stats", {})
            
            production_baseline = {
                "measurement_timestamp": time.time(),
                "key_metrics": {
                    "avg_latency_ms": single_perf.get("avg_latency_ms", 0),
                    "p50_latency_ms": single_perf.get("p50_latency_ms", 0),
                    "p95_latency_ms": single_perf.get("p95_latency_ms", 0),
                    "p99_latency_ms": single_perf.get("p99_latency_ms", 0),
                    "max_latency_ms": single_perf.get("max_latency_ms", 0),
                    "throughput_qps": concurrent_perf.get("throughput_qps", 0),
                    "error_rate": single_perf.get("error_rate", 0)
                },
                "database_info": {
                    "total_vectors": db_stats.get("total_vectors", 0),
                    "table_size": db_stats.get("table_size", "unknown"),
                    "database_size": db_stats.get("db_size", "unknown")
                },
                "optimization_opportunity": {
                    "current_p95_latency": single_perf.get("p95_latency_ms", 0),
                    "target_p95_latency": 20,
                    "potential_improvement": self._calculate_improvement_potential(single_perf.get("p95_latency_ms", 0)),
                    "current_throughput": concurrent_perf.get("throughput_qps", 0),
                    "target_throughput": 100
                }
            }
            
            # Save detailed baseline results
            baseline_timestamp = int(time.time())
            baseline_filename = f"production_baseline_{baseline_timestamp}.json"
            
            with open(baseline_filename, "w") as f:
                json.dump(baseline_results, f, indent=2, default=str)
            
            baseline_info.update({
                "status": "completed",
                "production_baseline": production_baseline,
                "detailed_results_file": baseline_filename,
                "ready_for_optimization": True
            })
            
            # Log key findings
            p95 = production_baseline["key_metrics"]["p95_latency_ms"]
            qps = production_baseline["key_metrics"]["throughput_qps"]
            
            logger.info("✅ Production baseline established")
            logger.info(f"🎯 Current P95 Latency: {p95:.1f}ms (target: <20ms)")
            logger.info(f"🎯 Current Throughput: {qps:.1f} QPS (target: >100 QPS)")
            
            if p95 > 20:
                improvement = production_baseline["optimization_opportunity"]["potential_improvement"]
                logger.info(f"🚀 Optimization Opportunity: {improvement}")
            else:
                logger.info("✨ System already performing at target latency!")
            
        except Exception as e:
            baseline_info.update({
                "status": "failed",
                "error": str(e),
                "ready_for_optimization": False
            })
            logger.error(f"Baseline establishment failed: {e}")
        
        baseline_info["duration"] = time.time() - baseline_info["start_time"]
        self.results["baseline_establishment"] = baseline_info
    
    def _calculate_improvement_potential(self, current_p95: float) -> str:
        """Calculate potential improvement from optimization."""
        if current_p95 <= 20:
            return "Already at target performance"
        
        improvement_percent = ((current_p95 - 20) / current_p95) * 100
        return f"{improvement_percent:.1f}% latency reduction possible"
    
    async def _coordinate_team_scheduling(self):
        """Schedule maintenance windows with all stakeholders."""
        logger.info("Step 4: Coordinating team scheduling...")
        
        scheduling_info = {
            "step": "team_coordination",
            "start_time": time.time(),
            "status": "planning"
        }
        
        try:
            # Check if we have baseline data to inform scheduling
            baseline_available = self.results.get("baseline_establishment", {}).get("ready_for_optimization", False)
            
            # Generate scheduling coordination plan
            maintenance_plan = {
                "optimization_phases": {
                    "phase_b": {
                        "name": "Stage 2-3: Low-Risk Configuration Optimization",
                        "duration": "2-3 hours",
                        "risk_level": "low",
                        "requirements": [
                            "Development window during low traffic",
                            "Real-time monitoring capability",
                            "Database team on standby"
                        ]
                    },
                    "phase_c": {
                        "name": "Stage 4: HNSW Index Optimization",
                        "duration": "3-4 hours",
                        "risk_level": "medium-high",
                        "requirements": [
                            "Dedicated maintenance window",
                            "All stakeholders available",
                            "Recent backup verification",
                            "Rollback procedures tested"
                        ]
                    }
                },
                "team_coordination": {
                    "devops_team": [
                        "Database backup verification",
                        "Monitoring dashboard setup",
                        "Rollback procedure validation"
                    ],
                    "database_team": [
                        "Index optimization review",
                        "Performance monitoring during changes",
                        "Emergency rollback support"
                    ],
                    "product_team": [
                        "Maintenance window approval",
                        "User communication planning",
                        "Success criteria validation"
                    ],
                    "engineering_team": [
                        "Code review of optimization scripts",
                        "Testing procedure validation",
                        "Post-optimization monitoring"
                    ]
                },
                "scheduling_recommendations": {
                    "phase_b_timing": "During low-traffic hours (typically 2-5 AM UTC)",
                    "phase_c_timing": "Dedicated maintenance window (weekend preferred)",
                    "preparation_time": "1 week advance notice for all teams",
                    "monitoring_period": "24-48 hours post-optimization monitoring"
                }
            }
            
            # Add baseline-specific recommendations if available
            if baseline_available:
                baseline_metrics = self.results["baseline_establishment"]["production_baseline"]["key_metrics"]
                
                maintenance_plan["baseline_informed_planning"] = {
                    "current_performance": {
                        "p95_latency_ms": baseline_metrics["p95_latency_ms"],
                        "throughput_qps": baseline_metrics["throughput_qps"]
                    },
                    "optimization_urgency": "high" if baseline_metrics["p95_latency_ms"] > 100 else "medium",
                    "expected_impact": self._calculate_improvement_potential(baseline_metrics["p95_latency_ms"])
                }
            
            # Save scheduling plan
            with open("maintenance_scheduling_plan.json", "w") as f:
                json.dump(maintenance_plan, f, indent=2, default=str)
            
            scheduling_info.update({
                "status": "plan_generated",
                "maintenance_plan": maintenance_plan,
                "coordination_files": [
                    "maintenance_scheduling_plan.json",
                    "production_coordination_plan.json"
                ],
                "next_actions": [
                    "Review maintenance plan with all teams",
                    "Schedule Phase B optimization window",
                    "Prepare monitoring and rollback procedures",
                    "Schedule Phase C dedicated maintenance window"
                ]
            })
            
            logger.info("✅ Team coordination plan generated")
            logger.info("📋 Maintenance scheduling plan saved to maintenance_scheduling_plan.json")
            
        except Exception as e:
            scheduling_info.update({
                "status": "failed",
                "error": str(e)
            })
            logger.error(f"Team coordination failed: {e}")
        
        scheduling_info["duration"] = time.time() - scheduling_info["start_time"]
        self.results["team_coordination"] = scheduling_info
    
    async def _generate_phase_a_summary(self):
        """Generate comprehensive Phase A summary and next steps."""
        logger.info("Generating Phase A completion summary...")
        
        phase_a_duration = time.time() - self.start_time
        
        # Assess Phase A completion status
        steps_completed = 0
        steps_total = 4
        
        for step in ["credential_acquisition", "read_only_validation", "baseline_establishment", "team_coordination"]:
            if self.results.get(step, {}).get("status") in ["passed", "completed", "plan_generated", "credentials_available"]:
                steps_completed += 1
        
        completion_rate = steps_completed / steps_total
        phase_a_status = "completed" if completion_rate >= 0.75 else "partial" if completion_rate >= 0.5 else "blocked"
        
        # Generate next steps based on completion status
        next_steps = []
        if self.results.get("credential_acquisition", {}).get("status") == "coordination_required":
            next_steps.append("Coordinate with DevOps team for PGVECTOR_PASSWORD")
        
        if self.results.get("read_only_validation", {}).get("ready_for_baseline"):
            next_steps.append("Production database access validated - ready for optimization")
        
        if self.results.get("baseline_establishment", {}).get("ready_for_optimization"):
            next_steps.append("Baseline established - proceed to Phase B optimization")
        
        if self.results.get("team_coordination", {}).get("status") == "plan_generated":
            next_steps.append("Review maintenance plans with teams and schedule optimization windows")
        
        summary = {
            "phase_a_completion": {
                "status": phase_a_status,
                "completion_rate": completion_rate,
                "steps_completed": steps_completed,
                "steps_total": steps_total,
                "duration": phase_a_duration
            },
            "readiness_assessment": {
                "credentials_ready": self.results.get("credential_acquisition", {}).get("ready_for_testing", False),
                "database_validated": self.results.get("read_only_validation", {}).get("ready_for_baseline", False),
                "baseline_established": self.results.get("baseline_establishment", {}).get("ready_for_optimization", False),
                "team_coordinated": self.results.get("team_coordination", {}).get("status") == "plan_generated"
            },
            "next_steps": next_steps,
            "phase_b_readiness": phase_a_status == "completed"
        }
        
        self.results["phase_a_summary"] = summary
        
        # Log summary
        logger.info("=== PHASE A COMPLETION SUMMARY ===")
        logger.info(f"Status: {phase_a_status.upper()}")
        logger.info(f"Completion: {steps_completed}/{steps_total} steps ({completion_rate:.1%})")
        logger.info(f"Duration: {phase_a_duration:.1f} seconds")
        
        if summary["phase_b_readiness"]:
            logger.info("✅ READY FOR PHASE B: Stage 2-3 Low-Risk Optimizations")
        else:
            logger.info("⏳ Complete remaining Phase A steps before proceeding")
            for step in next_steps:
                logger.info(f"  • {step}")

async def main():
    """Main coordination execution function."""
    coordinator = ProductionOptimizationCoordinator()
    
    try:
        results = await coordinator.execute_phase_a_preparation()
        
        # Save complete results
        results_timestamp = int(time.time())
        results_filename = f"phase_a_results_{results_timestamp}.json"
        
        with open(results_filename, "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Phase A results saved to {results_filename}")
        
        # Return appropriate exit code
        phase_a_ready = results.get("phase_a_summary", {}).get("phase_b_readiness", False)
        return 0 if phase_a_ready else 1
        
    except Exception as e:
        logger.error(f"Phase A coordination failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)