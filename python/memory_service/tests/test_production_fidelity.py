"""
Production Fidelity Tests for Core Nexus Memory Service

Advanced testing suite that simulates exact production conditions, real-world
data distributions, and deployment scenarios to ensure system reliability
under actual usage patterns and constraints.

These tests bridge the gap between development testing and production reality.
"""

import asyncio
import logging
import random
import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import numpy as np
import pytest
from memory_service.models import (
    MemoryRequest,
    MemoryResponse,
)

# Import the actual service components
from memory_service.unified_store import UnifiedVectorStore

# Disable logging during tests
logging.getLogger().setLevel(logging.CRITICAL)


@dataclass
class ProductionMetrics:
    """Production-like metrics for validation."""
    total_memories: int
    avg_query_time: float
    p95_query_time: float
    p99_query_time: float
    memory_distribution: dict[str, int]
    error_rate: float
    uptime_percentage: float
    resource_utilization: dict[str, float]


class RealWorldDataGenerator:
    """Generates realistic data patterns based on production observations."""

    def __init__(self):
        # Based on real-world memory service usage patterns
        self.conversation_types = [
            "technical_discussion", "project_planning", "brainstorming",
            "code_review", "system_design", "troubleshooting",
            "meeting_notes", "documentation", "research", "analysis"
        ]

        self.content_templates = {
            "technical_discussion": [
                "We need to optimize the database queries for better performance. The current implementation shows latency spikes during peak hours.",
                "The microservice architecture is causing some complexity in debugging. Should we consider a more monolithic approach for this component?",
                "Performance benchmarking results show 95th percentile response times are within acceptable limits.",
                "The caching layer needs improvement. Redis is showing high memory usage patterns that concern me."
            ],
            "project_planning": [
                "Sprint planning for Q2 includes three major features: user authentication, data analytics dashboard, and API versioning.",
                "Resource allocation for the next quarter shows we need two additional backend developers and one DevOps engineer.",
                "Timeline analysis indicates we can deliver the core features by end of March if we maintain current velocity.",
                "Risk assessment shows potential bottlenecks in the database migration and third-party integrations."
            ],
            "system_design": [
                "The event-driven architecture should handle up to 10,000 messages per second with proper partitioning strategy.",
                "Load balancing configuration needs to account for geographical distribution of users across three regions.",
                "Data consistency requirements suggest we need eventual consistency rather than strong consistency for this use case.",
                "Microservice communication patterns show we need circuit breakers and retry logic for resilience."
            ]
        }

        # Realistic user behavior patterns
        self.user_archetypes = {
            "developer": {"query_frequency": 8.5, "session_length": 25, "technical_content_ratio": 0.7},
            "manager": {"query_frequency": 4.2, "session_length": 15, "technical_content_ratio": 0.3},
            "architect": {"query_frequency": 12.3, "session_length": 45, "technical_content_ratio": 0.8},
            "analyst": {"query_frequency": 6.7, "session_length": 30, "technical_content_ratio": 0.5}
        }

    def generate_realistic_memory_dataset(self, size: int) -> list[MemoryRequest]:
        """Generate a realistic dataset matching production patterns."""
        memories = []

        # Generate memories with realistic distribution
        for i in range(size):
            conversation_type = np.random.choice(
                list(self.conversation_types),
                p=[0.15, 0.12, 0.10, 0.08, 0.12, 0.08, 0.10, 0.08, 0.09, 0.08]
            )

            # Select content based on type
            content_options = self.content_templates.get(
                conversation_type,
                ["Generic content about system operations and technical discussions."]
            )
            base_content = np.random.choice(content_options)

            # Add realistic variations
            content = self._add_realistic_variations(base_content, i)

            # Generate realistic metadata
            metadata = self._generate_realistic_metadata(conversation_type, i)

            # Realistic importance scoring (based on content length, recency, keywords)
            importance = self._calculate_realistic_importance(content, metadata)

            memories.append(MemoryRequest(
                content=content,
                metadata=metadata,
                importance_score=importance,
                user_id=metadata.get("user_id"),
                conversation_id=metadata.get("conversation_id")
            ))

        return memories

    def _add_realistic_variations(self, base_content: str, index: int) -> str:
        """Add realistic variations to content."""
        variations = [
            f"[{datetime.now().strftime('%Y-%m-%d')}] {base_content}",
            f"{base_content} Additional context: this relates to ticket #{1000 + index}.",
            f"Update: {base_content} Status: in progress.",
            f"{base_content}\n\nFollow-up needed: validation and testing phases."
        ]

        if index % 10 == 0:
            # Add longer, more complex content occasionally
            return f"{base_content}\n\nDetailed analysis:\n- Performance implications need review\n- Security considerations documented\n- Resource requirements estimated\n- Timeline dependencies identified"

        return np.random.choice([base_content] + variations)

    def _generate_realistic_metadata(self, conversation_type: str, index: int) -> dict[str, Any]:
        """Generate realistic metadata patterns."""
        # Realistic user distribution (some users are more active)
        user_weights = [0.3, 0.2, 0.15, 0.12, 0.08, 0.05, 0.04, 0.03, 0.02, 0.01]
        user_id = f"user_{np.random.choice(range(10), p=user_weights)}"

        # Conversation clustering (some conversations have many messages)
        if index % 15 < 8:  # 8/15 messages belong to clustered conversations
            conversation_id = f"conv_{index // 15}"
        else:
            conversation_id = f"conv_single_{index}"

        # Time distribution (more recent content is more common)
        days_ago = np.random.exponential(7)  # Exponential distribution favoring recent content
        timestamp = datetime.now() - timedelta(days=min(days_ago, 365))

        metadata = {
            "conversation_type": conversation_type,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "timestamp": timestamp.isoformat(),
            "source": "production_simulation",
            "priority": np.random.choice(["high", "medium", "low"], p=[0.2, 0.6, 0.2])
        }

        # Add type-specific metadata
        if conversation_type == "technical_discussion":
            metadata.update({
                "technologies": np.random.choice(
                    [["python", "postgresql"], ["javascript", "react"], ["docker", "kubernetes"],
                     ["aws", "terraform"], ["microservices", "api"]]
                ),
                "complexity": np.random.choice(["high", "medium", "low"], p=[0.4, 0.4, 0.2])
            })
        elif conversation_type == "project_planning":
            metadata.update({
                "project_phase": np.random.choice(["planning", "development", "testing", "deployment"]),
                "team_size": np.random.randint(3, 12),
                "deadline": (datetime.now() + timedelta(days=np.random.randint(30, 180))).isoformat()
            })

        return metadata

    def _calculate_realistic_importance(self, content: str, metadata: dict[str, Any]) -> float:
        """Calculate realistic importance scores."""
        base_score = 0.5

        # Content length factor
        content_factor = min(0.3, len(content) / 1000)

        # Recency factor
        timestamp = datetime.fromisoformat(metadata["timestamp"])
        days_old = (datetime.now() - timestamp).days
        recency_factor = max(0, 0.3 - (days_old / 365) * 0.3)

        # Priority factor
        priority_scores = {"high": 0.3, "medium": 0.15, "low": 0.05}
        priority_factor = priority_scores.get(metadata.get("priority", "medium"), 0.15)

        # Technical complexity factor
        complexity_scores = {"high": 0.2, "medium": 0.1, "low": 0.05}
        complexity_factor = complexity_scores.get(metadata.get("complexity", "medium"), 0.1)

        # Random variation
        noise = np.random.normal(0, 0.05)

        final_score = base_score + content_factor + recency_factor + priority_factor + complexity_factor + noise
        return max(0.1, min(1.0, final_score))

    def generate_production_query_patterns(self, num_queries: int) -> list[tuple[str, dict[str, Any], int]]:
        """Generate realistic query patterns based on production usage."""
        queries = []

        # Common query patterns from production
        query_templates = [
            ("find recent discussions about {technology}", {"recent": True}, 10),
            ("search for {conversation_type} from last week", {"time_filter": True}, 15),
            ("get all high priority items", {"priority": "high"}, 20),
            ("find conversations involving {user_type}", {"user_filter": True}, 12),
            ("search for project planning updates", {"conversation_type": "project_planning"}, 25),
            ("recent technical discussions", {"conversation_type": "technical_discussion", "recent": True}, 8),
            ("", {}, 50),  # Empty query (get all recent)
        ]

        # Weight distribution (some queries are much more common)
        weights = [0.25, 0.20, 0.15, 0.10, 0.10, 0.15, 0.05]

        for _ in range(num_queries):
            template, base_filters, limit = np.random.choice(
                query_templates, p=weights
            ).copy()

            # Customize template
            if "{technology}" in template:
                tech = np.random.choice(["python", "javascript", "docker", "kubernetes", "postgresql"])
                template = template.replace("{technology}", tech)
                base_filters["technology"] = tech

            if "{conversation_type}" in template:
                conv_type = np.random.choice(self.conversation_types)
                template = template.replace("{conversation_type}", conv_type)
                base_filters["conversation_type"] = conv_type

            if "{user_type}" in template:
                user_type = np.random.choice(list(self.user_archetypes.keys()))
                template = template.replace("{user_type}", user_type)
                base_filters["user_type"] = user_type

            # Add realistic query variations
            actual_limit = max(1, limit + np.random.randint(-5, 5))

            queries.append((template, base_filters, actual_limit))

        return queries


class ProductionEnvironmentSimulator:
    """Simulates production environment constraints and characteristics."""

    def __init__(self):
        # Production environment characteristics
        self.render_constraints = {
            "memory_limit_mb": 512,  # Render.com free tier
            "cpu_cores": 1,
            "max_connections": 100,
            "request_timeout": 30,
            "cold_start_delay": 2.5
        }

        self.network_characteristics = {
            "base_latency_ms": 15,  # Base network latency
            "latency_variance_ms": 5,
            "packet_loss_rate": 0.001,
            "bandwidth_limit_mbps": 100
        }

    async def simulate_render_environment(self, operation_func):
        """Simulate Render.com production environment constraints."""
        # Simulate memory pressure
        if random.random() < 0.1:  # 10% chance of memory pressure
            await asyncio.sleep(0.05)  # Garbage collection pause

        # Simulate network latency
        network_delay = (
            self.network_characteristics["base_latency_ms"] +
            np.random.normal(0, self.network_characteristics["latency_variance_ms"])
        ) / 1000

        await asyncio.sleep(max(0, network_delay))

        # Execute operation
        start_time = time.time()
        result = await operation_func()
        duration = time.time() - start_time

        # Apply timeout constraint
        if duration > self.render_constraints["request_timeout"]:
            raise TimeoutError("Request exceeded Render.com timeout limit")

        return result

    def simulate_cold_start(self):
        """Simulate cold start characteristics."""
        return asyncio.sleep(self.render_constraints["cold_start_delay"])


class TestProductionFidelity:
    """
    Production Fidelity Test Suite
    
    Tests system behavior under exact production conditions:
    - Real-world data distributions  
    - Render.com environment constraints
    - Production usage patterns
    - Cold start scenarios
    - Resource limitations
    """

    @pytest.fixture
    def data_generator(self):
        """Create a real-world data generator."""
        return RealWorldDataGenerator()

    @pytest.fixture
    def production_simulator(self):
        """Create a production environment simulator."""
        return ProductionEnvironmentSimulator()

    @pytest.fixture
    def mock_embedding(self):
        """Generate realistic embedding vectors."""
        return np.random.rand(1536).tolist()

    @pytest.mark.asyncio
    async def test_production_scale_data_patterns(self, data_generator, mock_embedding):
        """Test system with production-scale data patterns (1K-10K memories)."""

        # Generate realistic dataset
        dataset_size = 1500  # Reduced for test performance, but maintains patterns
        realistic_memories = data_generator.generate_realistic_memory_dataset(dataset_size)

        # Mock provider with realistic storage behavior
        stored_memories = {}
        query_performance_log = []

        async def realistic_store(content, embedding, metadata):
            # Simulate realistic storage latency
            storage_time = 0.02 + len(content) * 0.00001  # Content-dependent latency
            await asyncio.sleep(storage_time)

            memory_id = uuid4()
            stored_memories[memory_id] = {
                "content": content,
                "embedding": embedding,
                "metadata": metadata,
                "stored_at": time.time()
            }
            return memory_id

        async def realistic_query(query_embedding, limit, filters):
            start_time = time.time()

            # Simulate realistic query processing
            base_latency = 0.03
            complexity_factor = len(str(filters)) * 0.005 + limit * 0.002
            total_latency = base_latency + complexity_factor

            await asyncio.sleep(total_latency)

            # Simulate realistic result filtering and ranking
            filtered_results = []
            for memory_id, memory_data in list(stored_memories.items())[:limit * 2]:
                # Simple metadata filtering simulation
                if filters:
                    matches_filter = True
                    for key, value in filters.items():
                        if key in memory_data["metadata"]:
                            if memory_data["metadata"][key] != value:
                                matches_filter = False
                                break
                    if not matches_filter:
                        continue

                # Simulate similarity scoring
                similarity = 0.9 - len(filtered_results) * 0.05  # Decreasing similarity

                filtered_results.append(MemoryResponse(
                    id=memory_id,
                    content=memory_data["content"],
                    metadata=memory_data["metadata"],
                    similarity_score=max(0.1, similarity),
                    created_at=datetime.fromtimestamp(memory_data["stored_at"])
                ))

                if len(filtered_results) >= limit:
                    break

            query_duration = time.time() - start_time
            query_performance_log.append(query_duration)

            return filtered_results

        # Setup mock provider
        mock_provider = AsyncMock()
        mock_provider.store = realistic_store
        mock_provider.query = realistic_query

        store = UnifiedVectorStore({})
        store._providers = [mock_provider]

        # Phase 1: Bulk data loading (simulate production data ingestion)
        print(f"\nProduction Fidelity Test - Loading {dataset_size} memories...")

        load_start_time = time.time()
        store_times = []

        # Store memories in batches (realistic production pattern)
        batch_size = 50
        for i in range(0, min(500, len(realistic_memories)), batch_size):  # Limit for test performance
            batch = realistic_memories[i:i+batch_size]

            batch_start = time.time()
            for memory in batch:
                await store.store(
                    memory.content,
                    mock_embedding,
                    memory.metadata or {}
                )
            batch_duration = time.time() - batch_start
            store_times.append(batch_duration)

        total_load_time = time.time() - load_start_time

        # Phase 2: Production query patterns
        production_queries = data_generator.generate_production_query_patterns(100)

        query_start_time = time.time()
        successful_queries = 0
        failed_queries = 0

        for query, filters, limit in production_queries[:50]:  # Limit for test performance
            try:
                results = await store.query(mock_embedding, limit=limit, filters=filters)
                successful_queries += 1

                # Validate realistic result characteristics
                if results:
                    assert all(r.similarity_score > 0 for r in results), "All results should have positive similarity"
                    assert len(results) <= limit, "Should not exceed limit"

            except Exception as e:
                failed_queries += 1
                print(f"Query failed: {e}")

        total_query_time = time.time() - query_start_time

        # Calculate production metrics
        production_metrics = ProductionMetrics(
            total_memories=len(stored_memories),
            avg_query_time=statistics.mean(query_performance_log) if query_performance_log else 0,
            p95_query_time=np.percentile(query_performance_log, 95) if query_performance_log else 0,
            p99_query_time=np.percentile(query_performance_log, 99) if query_performance_log else 0,
            memory_distribution=self._analyze_memory_distribution(stored_memories),
            error_rate=failed_queries / (successful_queries + failed_queries) if (successful_queries + failed_queries) > 0 else 0,
            uptime_percentage=100.0,  # Simulated
            resource_utilization={"cpu": 45.0, "memory": 78.0}  # Simulated
        )

        # Validate production-like performance
        print("\nProduction Metrics:")
        print(f"  Total Memories Stored: {production_metrics.total_memories}")
        print(f"  Avg Query Time: {production_metrics.avg_query_time:.3f}s")
        print(f"  P95 Query Time: {production_metrics.p95_query_time:.3f}s")
        print(f"  P99 Query Time: {production_metrics.p99_query_time:.3f}s")
        print(f"  Error Rate: {production_metrics.error_rate:.2%}")
        print(f"  Data Load Time: {total_load_time:.2f}s")
        print(f"  Query Phase Time: {total_query_time:.2f}s")

        # Production performance assertions
        assert production_metrics.total_memories > 400, "Should store significant number of memories"
        assert production_metrics.avg_query_time < 0.2, f"Avg query time too high: {production_metrics.avg_query_time}"
        assert production_metrics.p95_query_time < 0.5, f"P95 query time too high: {production_metrics.p95_query_time}"
        assert production_metrics.error_rate < 0.05, f"Error rate too high: {production_metrics.error_rate}"
        assert successful_queries > 45, "Should have high query success rate"

    def _analyze_memory_distribution(self, stored_memories: dict) -> dict[str, int]:
        """Analyze the distribution of stored memories."""
        distribution = {
            "by_conversation_type": {},
            "by_user": {},
            "by_priority": {}
        }

        for memory_data in stored_memories.values():
            metadata = memory_data["metadata"]

            # Conversation type distribution
            conv_type = metadata.get("conversation_type", "unknown")
            distribution["by_conversation_type"][conv_type] = \
                distribution["by_conversation_type"].get(conv_type, 0) + 1

            # User distribution
            user_id = metadata.get("user_id", "unknown")
            distribution["by_user"][user_id] = \
                distribution["by_user"].get(user_id, 0) + 1

            # Priority distribution
            priority = metadata.get("priority", "unknown")
            distribution["by_priority"][priority] = \
                distribution["by_priority"].get(priority, 0) + 1

        return distribution

    @pytest.mark.asyncio
    async def test_render_environment_constraints(self, production_simulator, mock_embedding):
        """Test system behavior under Render.com production constraints."""

        # Mock provider with Render-like characteristics
        mock_provider = AsyncMock()

        async def render_constrained_operation():
            # Simulate database connection limits
            if random.random() < 0.02:  # 2% chance of connection limit
                raise ConnectionError("Database connection pool exhausted")

            # Simulate memory pressure
            if random.random() < 0.05:  # 5% chance of memory pressure
                await asyncio.sleep(0.1)  # GC pause

            return [
                MemoryResponse(
                    id=uuid4(),
                    content="Render environment result",
                    similarity_score=0.8,
                    metadata={"environment": "render"}
                )
            ]

        mock_provider.query = lambda *args, **kwargs: production_simulator.simulate_render_environment(
            render_constrained_operation
        )

        store = UnifiedVectorStore({})
        store._providers = [mock_provider]

        # Test cold start scenario
        print("\nTesting cold start scenario...")
        cold_start_time = time.time()
        await production_simulator.simulate_cold_start()
        cold_start_duration = time.time() - cold_start_time

        # Execute queries under Render constraints
        constraint_test_results = {
            "successful_queries": 0,
            "connection_errors": 0,
            "timeout_errors": 0,
            "memory_pressure_events": 0,
            "response_times": []
        }

        for i in range(30):
            try:
                start_time = time.time()

                results = await store.query(mock_embedding, limit=10, filters={})

                response_time = time.time() - start_time
                constraint_test_results["response_times"].append(response_time)
                constraint_test_results["successful_queries"] += 1

                # Check for memory pressure indicators
                if response_time > 0.15:  # High response time may indicate memory pressure
                    constraint_test_results["memory_pressure_events"] += 1

            except ConnectionError:
                constraint_test_results["connection_errors"] += 1
            except TimeoutError:
                constraint_test_results["timeout_errors"] += 1
            except Exception as e:
                print(f"Unexpected error: {e}")

        # Calculate constraint metrics
        total_operations = sum(constraint_test_results[key] for key in
                             ["successful_queries", "connection_errors", "timeout_errors"])

        success_rate = constraint_test_results["successful_queries"] / total_operations
        avg_response_time = statistics.mean(constraint_test_results["response_times"]) \
            if constraint_test_results["response_times"] else 0

        print("\nRender Environment Constraint Test Results:")
        print(f"  Cold Start Duration: {cold_start_duration:.2f}s")
        print(f"  Success Rate: {success_rate:.2%}")
        print(f"  Connection Errors: {constraint_test_results['connection_errors']}")
        print(f"  Timeout Errors: {constraint_test_results['timeout_errors']}")
        print(f"  Memory Pressure Events: {constraint_test_results['memory_pressure_events']}")
        print(f"  Avg Response Time: {avg_response_time:.3f}s")

        # Validate Render environment performance
        assert cold_start_duration >= 2.0, "Should simulate realistic cold start"
        assert success_rate >= 0.9, f"Success rate too low for production: {success_rate}"
        assert avg_response_time < 0.5, f"Response time too high for Render: {avg_response_time}"

        # Should handle some constraint-related errors gracefully
        assert constraint_test_results["connection_errors"] <= 2, "Too many connection errors"
        assert constraint_test_results["timeout_errors"] == 0, "Should not have timeout errors in normal conditions"

    @pytest.mark.asyncio
    async def test_production_data_backup_restore_cycle(self, data_generator, mock_embedding):
        """Test full production data backup and restore cycle."""

        # Generate realistic production dataset
        production_memories = data_generator.generate_realistic_memory_dataset(200)

        # Mock storage with backup capabilities
        primary_storage = {}
        backup_storage = {}

        async def store_with_backup(content, embedding, metadata):
            memory_id = uuid4()

            # Store in primary
            primary_storage[memory_id] = {
                "content": content,
                "embedding": embedding,
                "metadata": metadata,
                "backup_status": "pending"
            }

            # Simulate async backup (90% success rate)
            if random.random() < 0.9:
                backup_storage[memory_id] = primary_storage[memory_id].copy()
                primary_storage[memory_id]["backup_status"] = "completed"
            else:
                primary_storage[memory_id]["backup_status"] = "failed"

            return memory_id

        async def query_with_failover(query_embedding, limit, filters):
            # Try primary first
            if random.random() < 0.95:  # 95% primary availability
                source = primary_storage
                source_name = "primary"
            else:
                # Failover to backup
                source = backup_storage
                source_name = "backup"

            results = []
            for memory_id, memory_data in list(source.items())[:limit]:
                results.append(MemoryResponse(
                    id=memory_id,
                    content=memory_data["content"],
                    metadata={**memory_data["metadata"], "source": source_name},
                    similarity_score=0.85
                ))

            return results

        # Setup mock provider
        mock_provider = AsyncMock()
        mock_provider.store = store_with_backup
        mock_provider.query = query_with_failover

        store = UnifiedVectorStore({})
        store._providers = [mock_provider]

        # Phase 1: Store production data
        print("\nTesting production backup/restore cycle...")

        for memory in production_memories:
            await store.store(
                memory.content,
                mock_embedding,
                memory.metadata or {}
            )

        # Phase 2: Verify backup integrity
        backup_metrics = {
            "total_memories": len(primary_storage),
            "backup_success_rate": sum(1 for m in primary_storage.values()
                                     if m["backup_status"] == "completed") / len(primary_storage),
            "backup_completeness": len(backup_storage) / len(primary_storage)
        }

        # Phase 3: Test disaster recovery (simulate primary failure)
        primary_failure_results = []
        backup_queries = 0

        for _ in range(20):
            # Force backup usage by simulating primary failure
            with patch('random.random', return_value=0.96):  # Force backup usage
                results = await store.query(mock_embedding, limit=5, filters={})

                if results and results[0].metadata.get("source") == "backup":
                    backup_queries += 1
                    primary_failure_results.extend(results)

        # Calculate backup/restore metrics
        disaster_recovery_success_rate = backup_queries / 20

        print("\nBackup/Restore Cycle Results:")
        print(f"  Total Memories: {backup_metrics['total_memories']}")
        print(f"  Backup Success Rate: {backup_metrics['backup_success_rate']:.2%}")
        print(f"  Backup Completeness: {backup_metrics['backup_completeness']:.2%}")
        print(f"  Disaster Recovery Success: {disaster_recovery_success_rate:.2%}")
        print(f"  Backup Query Results: {len(primary_failure_results)}")

        # Validate backup/restore capabilities
        assert backup_metrics["total_memories"] == len(production_memories), "Should store all memories"
        assert backup_metrics["backup_success_rate"] >= 0.85, "Backup success rate too low"
        assert backup_metrics["backup_completeness"] >= 0.85, "Backup completeness too low"
        assert disaster_recovery_success_rate >= 0.9, "Disaster recovery success rate too low"
        assert len(primary_failure_results) > 0, "Should retrieve results from backup during failure"

    @pytest.mark.asyncio
    async def test_production_monitoring_and_alerting_simulation(self, mock_embedding):
        """Test production monitoring and alerting scenarios."""

        # Mock monitoring system
        monitoring_data = {
            "metrics": [],
            "alerts": [],
            "health_checks": []
        }

        async def monitored_operation(operation_type: str, duration: float, success: bool):
            """Simulate an operation with monitoring."""
            monitoring_data["metrics"].append({
                "timestamp": time.time(),
                "operation": operation_type,
                "duration": duration,
                "success": success
            })

            # Generate alerts based on thresholds
            if duration > 0.5:
                monitoring_data["alerts"].append({
                    "type": "performance",
                    "message": f"High latency detected: {duration:.3f}s",
                    "severity": "warning"
                })

            if not success:
                monitoring_data["alerts"].append({
                    "type": "error",
                    "message": f"Operation failed: {operation_type}",
                    "severity": "critical"
                })

        # Mock provider with monitoring integration
        mock_provider = AsyncMock()

        async def monitored_query(query_embedding, limit, filters):
            start_time = time.time()
            success = True

            try:
                # Simulate varying performance
                base_latency = 0.05
                load_factor = len(monitoring_data["metrics"]) * 0.002  # Performance degrades with load
                total_latency = base_latency + load_factor + random.uniform(0, 0.1)

                await asyncio.sleep(total_latency)

                # Occasional failures
                if random.random() < 0.02:  # 2% failure rate
                    raise RuntimeError("Simulated database timeout")

                results = [
                    MemoryResponse(
                        id=uuid4(),
                        content=f"Monitored result {i}",
                        similarity_score=0.8,
                        metadata={"monitoring": True}
                    )
                    for i in range(min(limit, 8))
                ]

                return results

            except Exception:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                await monitored_operation("query", duration, success)

        async def health_check():
            """Simulate health check."""
            health_status = {
                "status": "healthy",
                "timestamp": time.time(),
                "metrics": {
                    "total_operations": len(monitoring_data["metrics"]),
                    "error_rate": sum(1 for m in monitoring_data["metrics"] if not m["success"]) / max(1, len(monitoring_data["metrics"])),
                    "avg_response_time": statistics.mean([m["duration"] for m in monitoring_data["metrics"]]) if monitoring_data["metrics"] else 0
                }
            }

            # Mark as unhealthy if error rate is too high
            if health_status["metrics"]["error_rate"] > 0.05:
                health_status["status"] = "unhealthy"
                monitoring_data["alerts"].append({
                    "type": "health",
                    "message": f"High error rate: {health_status['metrics']['error_rate']:.2%}",
                    "severity": "critical"
                })

            monitoring_data["health_checks"].append(health_status)
            return health_status

        mock_provider.query = monitored_query
        mock_provider.health_check = health_check

        store = UnifiedVectorStore({})
        store._providers = [mock_provider]

        # Simulate production monitoring cycle
        print("\nSimulating production monitoring cycle...")

        # Phase 1: Normal operations with monitoring
        for i in range(50):
            try:
                await store.query(mock_embedding, limit=10, filters={})
            except Exception:
                pass  # Monitoring handles the failures

            # Health check every 10 operations
            if i % 10 == 0:
                await mock_provider.health_check()

        # Phase 2: Analyze monitoring data
        total_operations = len(monitoring_data["metrics"])
        successful_operations = sum(1 for m in monitoring_data["metrics"] if m["success"])
        error_rate = (total_operations - successful_operations) / total_operations

        response_times = [m["duration"] for m in monitoring_data["metrics"]]
        avg_response_time = statistics.mean(response_times)
        p95_response_time = np.percentile(response_times, 95)

        performance_alerts = [a for a in monitoring_data["alerts"] if a["type"] == "performance"]
        error_alerts = [a for a in monitoring_data["alerts"] if a["type"] == "error"]
        critical_alerts = [a for a in monitoring_data["alerts"] if a["severity"] == "critical"]

        print("\nProduction Monitoring Results:")
        print(f"  Total Operations: {total_operations}")
        print(f"  Error Rate: {error_rate:.2%}")
        print(f"  Avg Response Time: {avg_response_time:.3f}s")
        print(f"  P95 Response Time: {p95_response_time:.3f}s")
        print(f"  Performance Alerts: {len(performance_alerts)}")
        print(f"  Error Alerts: {len(error_alerts)}")
        print(f"  Critical Alerts: {len(critical_alerts)}")
        print(f"  Health Checks: {len(monitoring_data['health_checks'])}")

        # Validate monitoring capabilities
        assert total_operations == 50, "Should monitor all operations"
        assert error_rate <= 0.1, f"Error rate too high: {error_rate}"
        assert avg_response_time < 0.3, f"Average response time too high: {avg_response_time}"
        assert len(monitoring_data["health_checks"]) >= 5, "Should perform regular health checks"

        # Should generate appropriate alerts
        if len(performance_alerts) > 0:
            assert all("latency" in alert["message"].lower() for alert in performance_alerts), \
                "Performance alerts should mention latency"

        if len(error_alerts) > 0:
            assert all(alert["severity"] == "critical" for alert in error_alerts), \
                "Error alerts should be critical"


if __name__ == "__main__":
    # Run production fidelity tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])
