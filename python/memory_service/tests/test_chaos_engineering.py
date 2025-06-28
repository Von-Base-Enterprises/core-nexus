"""
Chaos Engineering Tests for Core Nexus Memory Service

Advanced testing suite that simulates real-world failures and system stress
to validate resilience, failover mechanisms, and recovery capabilities.

These tests complement foundational unit tests by providing deep insights
into system behavior under adverse conditions.
"""

import asyncio
import logging
import random
import time
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import numpy as np
import pytest
from src.memory_service.models import (
    MemoryRequest,
    MemoryResponse,
    ProviderConfig,
)

# Import the actual service components
from src.memory_service.unified_store import UnifiedVectorStore

# Disable logging during tests to reduce noise
logging.getLogger().setLevel(logging.CRITICAL)


class ChaosScenario:
    """Context manager for chaos engineering scenarios."""

    def __init__(self, name: str, failure_rate: float = 0.3):
        self.name = name
        self.failure_rate = failure_rate
        self.failures_injected = 0
        self.operations_attempted = 0

    def should_fail(self) -> bool:
        """Determine if this operation should fail based on failure rate."""
        self.operations_attempted += 1
        if random.random() < self.failure_rate:
            self.failures_injected += 1
            return True
        return False

    def get_metrics(self) -> dict[str, Any]:
        """Get failure injection metrics."""
        return {
            "scenario": self.name,
            "operations_attempted": self.operations_attempted,
            "failures_injected": self.failures_injected,
            "actual_failure_rate": self.failures_injected / max(1, self.operations_attempted)
        }


class FailingProvider:
    """Mock provider that fails predictably for chaos testing."""

    def __init__(self, base_provider, chaos_scenario: ChaosScenario):
        self.base_provider = base_provider
        self.chaos = chaos_scenario
        self.name = getattr(base_provider, 'name', 'unknown')
        self.config = getattr(base_provider, 'config', None)
        self.enabled = getattr(base_provider, 'enabled', True)

    async def store(self, content: str, embedding: list[float], metadata: dict[str, Any]):
        if self.chaos.should_fail():
            raise ConnectionError(f"Chaos: {self.name} provider failed during store")
        return await self.base_provider.store(content, embedding, metadata)

    async def query(self, query_embedding: list[float], limit: int, filters: dict[str, Any]):
        if self.chaos.should_fail():
            raise TimeoutError(f"Chaos: {self.name} provider timeout during query")
        return await self.base_provider.query(query_embedding, limit, filters)

    async def health_check(self):
        if self.chaos.should_fail():
            return {"status": "unhealthy", "error": "Chaos-induced failure"}
        return await self.base_provider.health_check()

    async def get_stats(self):
        if self.chaos.should_fail():
            raise Exception(f"Chaos: {self.name} stats unavailable")
        return await self.base_provider.get_stats()


@pytest.fixture
def mock_embedding():
    """Generate a consistent mock embedding vector."""
    return np.random.rand(1536).tolist()


@pytest.fixture
def sample_memories():
    """Generate sample memories for testing."""
    return [
        MemoryRequest(
            content=f"Test memory content {i}",
            metadata={"test_id": i, "importance": random.uniform(0.1, 1.0)},
            user_id=f"user_{i % 3}",
            conversation_id=f"conv_{i // 10}"
        )
        for i in range(50)
    ]


class TestChaosEngineering:
    """
    Chaos Engineering Test Suite
    
    Tests system resilience under various failure scenarios including:
    - Partial provider failures
    - Network partitions
    - Resource exhaustion
    - Concurrent load with failures
    """

    @pytest.mark.asyncio
    async def test_partial_provider_failure_resilience(self, realistic_pgvector_provider, realistic_chromadb_provider, mock_embedding, sample_memories):
        """Test system behavior when 1 of 3 providers fails intermittently."""

        # Create chaos scenario with 30% failure rate
        chaos = ChaosScenario("partial_provider_failure", failure_rate=0.3)

        # Create a third provider for testing
        third_provider_config = ProviderConfig(
            name="test_provider",
            enabled=True,
            primary=False,
            config={"test": True}
        )
        third_provider = AsyncMock()
        third_provider.name = "test_provider"
        third_provider.config = third_provider_config
        third_provider.enabled = True

        # Wrap one provider with chaos
        failing_pgvector = FailingProvider(realistic_pgvector_provider, chaos)

        # Configure providers - use realistic ones 
        providers = [failing_pgvector, realistic_chromadb_provider, third_provider]

        # Create store with proper provider configuration
        with patch('src.memory_service.unified_store.ImportanceScoring') as mock_importance:
            store = UnifiedVectorStore(
                providers=providers,
                embedding_model=AsyncMock(),
                adm_enabled=False
            )

            successful_stores = 0
            failed_stores = 0

            # Attempt to store multiple memories
            for memory in sample_memories[:20]:
                try:
                    # Use the store_memory method for proper API compatibility
                    await store.store_memory(memory)
                    successful_stores += 1
                except Exception as e:
                    failed_stores += 1
                    # Should not fail if other providers are working
                    assert "Chaos" not in str(e), f"System should have failed over, but got: {e}"

            # Verify resilience metrics
            metrics = chaos.get_metrics()
            assert successful_stores > 0, "System should remain operational despite failures"
            assert metrics["failures_injected"] > 0, "Chaos should have injected failures"

            # At least 70% of operations should succeed due to failover
            success_rate = successful_stores / (successful_stores + failed_stores)
            assert success_rate >= 0.7, f"Success rate {success_rate} too low for failover system"

    @pytest.mark.asyncio
    async def test_network_partition_simulation(self, realistic_pgvector_provider, realistic_chromadb_provider, mock_embedding):
        """Simulate network partitions during database operations."""

        chaos = ChaosScenario("network_partition", failure_rate=0.5)

        # Create failing provider that simulates network issues
        failing_provider = FailingProvider(realistic_pgvector_provider, chaos)

        # Create store with mixed providers (one failing, one stable)
        providers = [failing_provider, realistic_chromadb_provider]

        with patch('src.memory_service.unified_store.ImportanceScoring') as mock_importance:
            store = UnifiedVectorStore(
                providers=providers,
                embedding_model=AsyncMock(),
                adm_enabled=False
            )

            # Test query resilience during network issues
            successful_queries = 0
            network_failures = 0

            for _ in range(30):
                try:
                    # Use mock query request
                    from src.memory_service.models import QueryRequest
                    query_request = QueryRequest(query="test network partition", limit=10)
                    results = await store.query_memories(query_request)
                    successful_queries += 1
                except (ConnectionError, TimeoutError) as e:
                    network_failures += 1
                    # System should handle gracefully through failover
                    await asyncio.sleep(0.01)  # Brief pause to simulate retry delay

            metrics = chaos.get_metrics()
            assert network_failures > 0, "Should have experienced network failures"
            assert successful_queries > 0, "Should have some successful queries"

            # Verify failure rate aligns with chaos scenario
            expected_failures = metrics["operations_attempted"] * chaos.failure_rate
            assert abs(network_failures - expected_failures) < 5, "Failure rate should match chaos scenario"

    @pytest.mark.asyncio
    async def test_memory_pressure_during_operations(self, realistic_pgvector_provider, sample_memories, mock_embedding):
        """Test behavior under memory pressure conditions."""

        # Simulate memory pressure by creating large objects
        memory_hogs = []

        async def create_memory_pressure():
            """Create memory pressure in background."""
            for _ in range(100):
                # Create large numpy arrays to consume memory
                memory_hogs.append(np.random.rand(10000, 100))
                await asyncio.sleep(0.001)

        # Start memory pressure task
        pressure_task = asyncio.create_task(create_memory_pressure())

        try:
            # Test operations under memory pressure with realistic provider
            providers = [realistic_pgvector_provider]

            with patch('src.memory_service.unified_store.ImportanceScoring') as mock_importance:
                store = UnifiedVectorStore(
                    providers=providers,
                    embedding_model=AsyncMock(),
                    adm_enabled=False
                )

                start_time = time.time()
                successful_ops = 0

                # Perform operations while memory is under pressure
                for memory in sample_memories[:15]:
                    try:
                        await store.store_memory(memory)
                        successful_ops += 1
                    except MemoryError:
                        # Memory errors are acceptable under pressure
                        pass
                    except Exception as e:
                        # Other errors should not occur
                        pytest.fail(f"Unexpected error under memory pressure: {e}")

            operation_duration = time.time() - start_time

            # Operations should complete within reasonable time even under pressure
            assert operation_duration < 5.0, f"Operations took too long under memory pressure: {operation_duration}s"
            assert successful_ops > 0, "Should complete some operations despite memory pressure"

        finally:
            pressure_task.cancel()
            # Clean up memory
            memory_hogs.clear()

    @pytest.mark.asyncio
    async def test_concurrent_load_with_provider_failures(self, realistic_pgvector_provider, mock_embedding):
        """Test system under concurrent load while providers fail and recover."""

        chaos = ChaosScenario("concurrent_load_failures", failure_rate=0.4)

        # Create multiple mock providers with different failure patterns
        providers = []
        for i in range(3):
            mock_provider = AsyncMock()
            mock_provider.name = f"provider_{i}"

            async def flaky_operation(*args, **kwargs):
                if chaos.should_fail():
                    raise RuntimeError(f"Provider {i} temporary failure")
                await asyncio.sleep(random.uniform(0.001, 0.01))  # Simulate realistic latency
                return uuid4() if 'store' in str(args) else []

            mock_provider.store = flaky_operation
            mock_provider.query = flaky_operation
            providers.append(mock_provider)

        # Create store with realistic provider configuration
        with patch('src.memory_service.unified_store.ImportanceScoring') as mock_importance:
            store = UnifiedVectorStore(
                providers=[realistic_pgvector_provider],
                embedding_model=AsyncMock(),
                adm_enabled=False
            )
        store._providers = providers

        # Concurrent task function
        async def concurrent_operations(worker_id: int, operation_count: int):
            results = {"success": 0, "failures": 0, "errors": []}

            for i in range(operation_count):
                try:
                    if i % 2 == 0:
                        # Store operation
                        await store.store(
                            f"Worker {worker_id} content {i}",
                            mock_embedding,
                            {"worker_id": worker_id, "op_id": i}
                        )
                    else:
                        # Query operation
                        await store.query(mock_embedding, limit=5, filters={})

                    results["success"] += 1

                except Exception as e:
                    results["failures"] += 1
                    results["errors"].append(str(e))

            return results

        # Launch concurrent workers
        num_workers = 20
        ops_per_worker = 10

        start_time = time.time()
        tasks = [
            asyncio.create_task(concurrent_operations(i, ops_per_worker))
            for i in range(num_workers)
        ]

        # Wait for all tasks to complete
        worker_results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.time() - start_time

        # Analyze results
        total_success = sum(r["success"] for r in worker_results if isinstance(r, dict))
        total_failures = sum(r["failures"] for r in worker_results if isinstance(r, dict))
        total_operations = total_success + total_failures

        chaos_metrics = chaos.get_metrics()

        # Validate concurrent performance under chaos
        assert total_success > 0, "Should have some successful operations"
        assert total_operations == num_workers * ops_per_worker, "Should account for all operations"

        # Performance should be reasonable despite failures
        avg_ops_per_second = total_operations / total_duration
        assert avg_ops_per_second > 50, f"Too slow under concurrent load: {avg_ops_per_second} ops/sec"

        # Success rate should be reasonable with failover
        success_rate = total_success / total_operations
        assert success_rate >= 0.6, f"Success rate too low: {success_rate}"

        print("\nConcurrent Load Test Results:")
        print(f"  Total Operations: {total_operations}")
        print(f"  Success Rate: {success_rate:.2%}")
        print(f"  Duration: {total_duration:.2f}s")
        print(f"  Throughput: {avg_ops_per_second:.1f} ops/sec")
        print(f"  Chaos Metrics: {chaos_metrics}")

    @pytest.mark.asyncio
    async def test_data_corruption_recovery(self, realistic_pgvector_provider, mock_embedding):
        """Test recovery from corrupted embeddings and metadata."""

        chaos = ChaosScenario("data_corruption", failure_rate=0.2)

        # Mock provider that occasionally returns corrupted data
        mock_provider = AsyncMock()

        async def corrupted_query(*args, **kwargs):
            if chaos.should_fail():
                # Return corrupted data
                return [
                    MemoryResponse(
                        id=uuid4(),
                        content="corrupted content",
                        embedding=None,  # Missing embedding
                        metadata={"corrupted": True, "invalid_field": object()},  # Invalid metadata
                        similarity_score=float('inf')  # Invalid similarity
                    )
                ]
            else:
                # Return valid data
                return [
                    MemoryResponse(
                        id=uuid4(),
                        content="valid content",
                        embedding=mock_embedding,
                        metadata={"valid": True},
                        similarity_score=0.85
                    )
                ]

        mock_provider.query = corrupted_query

        # Create store with realistic provider configuration
        with patch('src.memory_service.unified_store.ImportanceScoring') as mock_importance:
            store = UnifiedVectorStore(
                providers=[realistic_pgvector_provider],
                embedding_model=AsyncMock(),
                adm_enabled=False
            )
        store._providers = [mock_provider]

        # Test query resilience with corrupted data
        valid_results = 0
        corrupted_results = 0

        for _ in range(25):
            try:
                results = await store.query(mock_embedding, limit=5, filters={})

                # Validate results for corruption
                for result in results:
                    if hasattr(result, 'metadata') and result.metadata.get('corrupted'):
                        corrupted_results += 1
                        # System should handle corrupted data gracefully
                        assert result.similarity_score != float('inf'), "Should sanitize invalid similarity scores"
                    else:
                        valid_results += 1
                        assert result.similarity_score <= 1.0, "Valid similarity score"
                        assert result.embedding is not None, "Valid embedding"

            except Exception as e:
                # Should not raise unhandled exceptions for corruption
                pytest.fail(f"Unhandled corruption error: {e}")

        chaos_metrics = chaos.get_metrics()
        assert corrupted_results > 0, "Should have encountered corrupted data"
        assert valid_results > 0, "Should have some valid results"

        print("\nData Corruption Test Results:")
        print(f"  Valid Results: {valid_results}")
        print(f"  Corrupted Results: {corrupted_results}")
        print(f"  Chaos Metrics: {chaos_metrics}")

    @pytest.mark.asyncio
    async def test_time_synchronization_issues(self, realistic_pgvector_provider, mock_embedding):
        """Test behavior when system clocks are out of sync."""

        # Mock time functions with drift
        original_time = time.time
        time_drift = 0

        def drifted_time():
            nonlocal time_drift
            time_drift += random.uniform(-0.1, 0.1)  # Random drift
            return original_time() + time_drift

        with patch('time.time', side_effect=drifted_time):
            mock_provider = AsyncMock()
            mock_provider.store.return_value = uuid4()

            # Create store with realistic provider configuration
            with patch('src.memory_service.unified_store.ImportanceScoring') as mock_importance:
                store = UnifiedVectorStore(
                    providers=[realistic_pgvector_provider],
                    embedding_model=AsyncMock(),
                    adm_enabled=False
                )

                # Test operations with time drift
                timestamps = []

                for i in range(10):
                    start_time = time.time()
                    request = MemoryRequest(
                        content=f"Content {i}",
                        metadata={"timestamp": start_time}
                    )
                    await store.store_memory(request)
                    end_time = time.time()

                    # Track timestamp consistency
                    timestamps.append((start_time, end_time, end_time - start_time))
                    await asyncio.sleep(0.01)

                # Validate time handling
                durations = [duration for _, _, duration in timestamps]

                # Should handle time drift gracefully
                assert all(d >= 0 for d in durations), "Should handle negative time deltas"
                assert all(d < 1.0 for d in durations), "Operations should complete quickly"

                # Check for time consistency issues
                time_inconsistencies = sum(1 for start, end, _ in timestamps if end < start)
                assert time_inconsistencies == 0, f"Found {time_inconsistencies} time inconsistencies"


class TestFailoverMechanisms:
    """Test advanced failover and recovery scenarios."""

    @pytest.mark.asyncio
    async def test_cascading_provider_failures(self, realistic_pgvector_provider, mock_embedding):
        """Test system behavior when providers fail in cascade."""

        providers = []
        chaos_scenarios = []

        # Create 3 providers with increasing failure rates
        for i, failure_rate in enumerate([0.3, 0.5, 0.8]):
            chaos = ChaosScenario(f"cascade_failure_{i}", failure_rate=failure_rate)
            chaos_scenarios.append(chaos)

            mock_provider = AsyncMock()
            mock_provider.name = f"provider_{i}"

            # Create failing provider
            failing_provider = FailingProvider(mock_provider, chaos)
            providers.append(failing_provider)

        # Create store with realistic provider configuration
        with patch('src.memory_service.unified_store.ImportanceScoring') as mock_importance:
            store = UnifiedVectorStore(
                providers=[realistic_pgvector_provider],
                embedding_model=AsyncMock(),
                adm_enabled=False
            )
        store._providers = providers

        # Test operations as failures cascade
        operations_results = []

        for i in range(30):
            try:
                result = await store.store(
                    f"Content {i}",
                    mock_embedding,
                    {"operation_id": i}
                )
                operations_results.append(("success", result))

            except Exception as e:
                operations_results.append(("failure", str(e)))

        # Analyze cascade behavior
        successes = [r for r in operations_results if r[0] == "success"]
        failures = [r for r in operations_results if r[0] == "failure"]

        # Should maintain some level of service even with cascading failures
        success_rate = len(successes) / len(operations_results)

        print("\nCascading Failure Test Results:")
        print(f"  Success Rate: {success_rate:.2%}")
        print(f"  Total Operations: {len(operations_results)}")

        for i, chaos in enumerate(chaos_scenarios):
            metrics = chaos.get_metrics()
            print(f"  Provider {i}: {metrics}")

        # Should maintain at least minimal service
        assert success_rate > 0.1, f"Success rate too low during cascade: {success_rate}"

    @pytest.mark.asyncio
    async def test_provider_recovery_patterns(self, realistic_pgvector_provider, mock_embedding):
        """Test how the system recovers when failed providers come back online."""

        # Create a provider that fails then recovers
        recovery_chaos = ChaosScenario("recovery_pattern", failure_rate=1.0)  # Start with 100% failure

        mock_provider = AsyncMock()
        failing_provider = FailingProvider(mock_provider, recovery_chaos)

        # Create store with realistic provider configuration
        with patch('src.memory_service.unified_store.ImportanceScoring') as mock_importance:
            store = UnifiedVectorStore(
                providers=[realistic_pgvector_provider],
                embedding_model=AsyncMock(),
                adm_enabled=False
            )
        store._providers = [failing_provider]

        phase_results = []

        # Phase 1: All operations should fail
        phase1_failures = 0
        for i in range(5):
            try:
                await store.store(f"Content {i}", mock_embedding, {})
            except Exception:
                phase1_failures += 1

        phase_results.append(("full_failure", phase1_failures, 5))

        # Phase 2: Gradual recovery (reduce failure rate)
        recovery_chaos.failure_rate = 0.5
        phase2_successes = 0
        phase2_failures = 0

        for i in range(10):
            try:
                await store.store(f"Recovery content {i}", mock_embedding, {})
                phase2_successes += 1
            except Exception:
                phase2_failures += 1

        phase_results.append(("partial_recovery", phase2_successes, phase2_successes + phase2_failures))

        # Phase 3: Full recovery
        recovery_chaos.failure_rate = 0.0
        phase3_successes = 0

        for i in range(5):
            try:
                await store.store(f"Full recovery content {i}", mock_embedding, {})
                phase3_successes += 1
            except Exception:
                pass

        phase_results.append(("full_recovery", phase3_successes, 5))

        # Validate recovery pattern
        print("\nProvider Recovery Test Results:")
        for phase, successes, total in phase_results:
            success_rate = successes / total
            print(f"  {phase}: {success_rate:.2%} success rate ({successes}/{total})")

        # Phase 1 should have high failure rate
        assert phase_results[0][1] >= 4, "Should fail during full failure phase"

        # Phase 2 should show partial recovery
        assert phase_results[1][1] > 0, "Should show some recovery"

        # Phase 3 should show full recovery
        assert phase_results[2][1] >= 4, "Should fully recover"


if __name__ == "__main__":
    # Run chaos engineering tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])
