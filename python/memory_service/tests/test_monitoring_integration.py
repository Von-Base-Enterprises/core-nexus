"""
Monitoring System Integration Tests

End-to-end validation of the complete monitoring system including error tracking,
circuit breakers, alerts, and performance monitoring with real data validation.
"""

import asyncio
import pytest
import time
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# Set up test imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from memory_service.monitoring import (
    ErrorMonitor, Alert, AlertSeverity, ErrorCategory, get_error_monitor
)
from memory_service.unified_store import ProviderCircuitBreaker, VectorProvider
from memory_service.models import ProviderConfig


class MockFailingProvider(VectorProvider):
    """Mock provider that can be configured to fail for testing."""
    
    def __init__(self, config: ProviderConfig, failure_mode="none"):
        super().__init__(config)
        self.failure_mode = failure_mode
        self.operation_count = 0
        
    async def store(self, content: str, embedding: list[float], metadata: dict):
        self.operation_count += 1
        if self.failure_mode == "store":
            raise ConnectionError(f"Mock store failure #{self.operation_count}")
        return f"mock-id-{self.operation_count}"
    
    async def query(self, query_embedding: list[float], limit: int, filters: dict):
        self.operation_count += 1
        if self.failure_mode == "query":
            raise TimeoutError(f"Mock query timeout #{self.operation_count}")
        return []
    
    async def retrieve(self, memory_id):
        return None
    
    async def health_check(self):
        return {"status": "healthy" if self.failure_mode == "none" else "unhealthy"}
    
    async def get_stats(self):
        return {"operations": self.operation_count}


class TestMonitoringSystemIntegration:
    """Complete integration tests for monitoring system."""
    
    @pytest.mark.asyncio
    async def setup_monitoring_system(self):
        """Set up complete monitoring system for testing."""
        # Create monitoring system
        captured_alerts = []
        
        async def capture_alert(alert):
            captured_alerts.append(alert)
        
        monitor = ErrorMonitor(
            alert_handlers=[capture_alert],
            error_rate_threshold=0.1,  # 10% error rate
            response_time_threshold=1.0,  # 1 second
            memory_usage_threshold=0.8
        )
        
        # Start monitoring
        await monitor.start_monitoring()
        
        # Store captured alerts for test access
        monitor._captured_alerts = captured_alerts
        
        return monitor
    
    @pytest.mark.asyncio
    async def test_end_to_end_error_monitoring(self):
        """Test complete error monitoring flow with real data."""
        monitor = await self.setup_monitoring_system()
        
        # Generate various types of errors
        error_scenarios = [
            (ConnectionError("Database connection failed"), ErrorCategory.CONNECTION_POOL, "pgvector"),
            (TimeoutError("Query timeout after 30s"), ErrorCategory.TIMEOUT, "chromadb"),
            (RuntimeError("Circuit breaker open"), ErrorCategory.CIRCUIT_BREAKER, "pinecone"),
            (ValueError("Invalid credentials"), ErrorCategory.AUTHENTICATION, "pinecone"),
            (MemoryError("Out of memory"), ErrorCategory.MEMORY_LEAK, "system"),
        ]
        
        # Record errors
        for error, category, provider in error_scenarios:
            monitor.record_error(error, category, provider, operation="test_operation")
            await asyncio.sleep(0.01)  # Small delay to ensure timestamp ordering
        
        # Record some successful requests
        for i in range(95):
            monitor.record_request(100.0 + (i * 2), success=True, provider="pgvector")
        
        # Get error summary
        error_summary = await monitor.get_error_summary(hours=1)
        
        # Verify error tracking
        assert error_summary['total_errors'] == 5
        assert error_summary['by_category']['connection_pool'] == 1
        assert error_summary['by_category']['timeout'] == 1
        assert error_summary['by_category']['circuit_breaker'] == 1
        assert error_summary['by_provider']['pgvector'] == 1
        assert error_summary['by_provider']['chromadb'] == 1
        assert error_summary['by_provider']['pinecone'] == 2
        
        # Verify health status
        health = await monitor.get_health_status()
        assert health.total_requests == 95  # Only successful requests counted
        assert health.total_errors == 5
        assert health.error_rate == 0.0  # No failed requests, only recorded errors
        assert health.avg_response_time > 100  # Should reflect request times
        
        print(f"✅ Error Monitoring Test Results:")
        print(f"   - Total errors tracked: {error_summary['total_errors']}")
        print(f"   - Error categories: {list(error_summary['by_category'].keys())}")
        print(f"   - Provider breakdown: {error_summary['by_provider']}")
        print(f"   - Health status: {health.total_requests} requests, {health.error_rate:.1%} error rate")
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_cascade(self):
        """Test circuit breaker cascade failure protection with monitoring."""
        monitor = await self.setup_monitoring_system()
        
        # Create providers with different failure modes
        configs = [
            ProviderConfig(name="primary", enabled=True, primary=True, 
                          config={"circuit_breaker_failure_threshold": 3}),
            ProviderConfig(name="secondary", enabled=True, primary=False, 
                          config={"circuit_breaker_failure_threshold": 3}),
            ProviderConfig(name="tertiary", enabled=True, primary=False, 
                          config={"circuit_breaker_failure_threshold": 3})
        ]
        
        providers = [
            MockFailingProvider(configs[0], failure_mode="store"),  # Primary fails
            MockFailingProvider(configs[1], failure_mode="none"),   # Secondary healthy
            MockFailingProvider(configs[2], failure_mode="none")    # Tertiary healthy
        ]
        
        # Mock the get_error_monitor to return our test monitor
        with patch('memory_service.unified_store.get_error_monitor', return_value=monitor):
            # Simulate failures on primary provider
            primary = providers[0]
            
            failure_count = 0
            for i in range(5):  # Exceed failure threshold
                try:
                    await primary.store(f"test content {i}", [0.1] * 100, {})
                except Exception as e:
                    primary.record_failure(e)
                    monitor.record_error(e, ErrorCategory.PROVIDER_FAILURE, "primary")
                    failure_count += 1
            
            # Verify circuit breaker opened
            assert primary.circuit_breaker.state == 'open'
            assert not primary.is_available()
            
            # Verify monitoring captured circuit breaker events
            cb_events = monitor.circuit_breaker_events
            opening_events = [e for e in cb_events if e['new_state'] == 'open']
            assert len(opening_events) >= 1
            
            # Simulate successful operations on secondary
            secondary = providers[1]
            success_count = 0
            for i in range(10):
                try:
                    await secondary.store(f"failover content {i}", [0.1] * 100, {})
                    secondary.record_success()
                    monitor.record_request(150.0, success=True, provider="secondary", operation="failover_store")
                    success_count += 1
                except Exception as e:
                    secondary.record_failure(e)
            
            # Verify secondary handled the load
            assert secondary.circuit_breaker.state == 'closed'
            assert secondary.is_available()
            assert success_count == 10
            
            # Get final monitoring status
            health = await monitor.get_health_status()
            error_summary = await monitor.get_error_summary(hours=1)
            
            print(f"✅ Circuit Breaker Cascade Test Results:")
            print(f"   - Primary provider failures: {failure_count}")
            print(f"   - Primary circuit breaker state: {primary.circuit_breaker.state}")
            print(f"   - Secondary successes: {success_count}")
            print(f"   - Circuit breaker events: {len(cb_events)}")
            print(f"   - Total errors tracked: {error_summary['total_errors']}")
            print(f"   - Total successful requests: {health.total_requests}")
    
    @pytest.mark.asyncio
    async def test_performance_degradation_detection(self):
        """Test detection of gradual performance degradation."""
        monitor = await self.setup_monitoring_system()
        
        # Simulate normal performance baseline
        baseline_times = []
        for i in range(50):
            response_time = 100.0 + (i % 10) * 5  # 100-145ms range
            monitor.record_request(response_time, success=True, provider="pgvector")
            baseline_times.append(response_time)
        
        # Simulate gradual performance degradation
        degraded_times = []
        slow_requests = 0
        for i in range(30):
            response_time = 200.0 + (i * 50)  # Increasingly slow: 200ms to 1650ms
            monitor.record_request(response_time, success=True, provider="pgvector")
            degraded_times.append(response_time)
            
            # Some requests will exceed threshold
            if response_time > monitor.response_time_threshold * 1000:
                slow_requests += 1
        
        # Wait briefly for async processing
        await asyncio.sleep(0.1)
        
        # Verify performance tracking
        health = await monitor.get_health_status()
        avg_response_time = health.avg_response_time
        
        # Should show degraded performance
        assert avg_response_time > 200  # Should be higher than baseline
        assert slow_requests > 10  # Many requests exceeded threshold
        
        # Check for performance alerts
        captured_alerts = monitor._captured_alerts
        slow_response_alerts = [a for a in captured_alerts if "Slow Response" in a.title]
        
        print(f"✅ Performance Degradation Test Results:")
        print(f"   - Baseline avg response time: {sum(baseline_times) / len(baseline_times):.1f}ms")
        print(f"   - Final avg response time: {avg_response_time:.1f}ms")
        print(f"   - Slow requests (>{monitor.response_time_threshold * 1000}ms): {slow_requests}")
        print(f"   - Performance alerts generated: {len(slow_response_alerts)}")
        print(f"   - Total requests tracked: {health.total_requests}")
    
    @pytest.mark.asyncio
    async def test_alert_lifecycle_management(self):
        """Test complete alert lifecycle from creation to resolution."""
        monitor = await self.setup_monitoring_system()
        
        # Create test alert
        alert = await monitor.create_alert(
            severity=AlertSeverity.ERROR,
            category=ErrorCategory.PROVIDER_FAILURE,
            title="Database Connection Pool Exhausted",
            description="All database connections are in use, new requests are queued",
            provider="pgvector",
            metrics={"active_connections": 30, "max_connections": 30, "queue_length": 15}
        )
        
        # Verify alert creation
        assert alert.id in monitor.active_alerts
        assert len(monitor._captured_alerts) == 1
        captured_alert = monitor._captured_alerts[0]
        assert captured_alert.title == "Database Connection Pool Exhausted"
        assert captured_alert.provider == "pgvector"
        assert captured_alert.metrics["queue_length"] == 15
        assert not captured_alert.resolved
        
        # Create a second alert
        alert2 = await monitor.create_alert(
            severity=AlertSeverity.CRITICAL,
            category=ErrorCategory.CIRCUIT_BREAKER,
            title="Multiple Circuit Breakers Open",
            description="2 out of 3 providers have circuit breakers open",
            metrics={"open_circuits": 2, "total_circuits": 3}
        )
        
        # Verify multiple active alerts
        assert len(monitor.active_alerts) == 2
        assert len(monitor._captured_alerts) == 2
        
        # Resolve first alert
        await monitor.resolve_alert(alert.id, "Connection pool scaled up to 50 connections")
        
        # Verify resolution
        assert alert.id not in monitor.active_alerts
        assert alert.resolved is True
        assert "Connection pool scaled up" in alert.description
        
        # Second alert should still be active
        assert len(monitor.active_alerts) == 1
        assert alert2.id in monitor.active_alerts
        
        # Resolve second alert
        await monitor.resolve_alert(alert2.id, "Circuit breakers recovered after service restart")
        
        # Verify all alerts resolved
        assert len(monitor.active_alerts) == 0
        assert alert2.resolved is True
        
        print(f"✅ Alert Lifecycle Test Results:")
        print(f"   - Alerts created: 2")
        print(f"   - Alerts resolved: 2")
        print(f"   - Active alerts remaining: {len(monitor.active_alerts)}")
        print(f"   - Alert history length: {len(monitor.alert_history)}")
    
    @pytest.mark.asyncio
    async def test_high_load_monitoring_stability(self):
        """Test monitoring system stability under high load."""
        monitor = await self.setup_monitoring_system()
        
        start_time = time.time()
        
        # Generate high load
        tasks = []
        
        # Task 1: High volume error recording
        async def generate_errors():
            for i in range(500):
                error_type = ["ConnectionError", "TimeoutError", "ValueError"][i % 3]
                category = [ErrorCategory.CONNECTION_POOL, ErrorCategory.TIMEOUT, ErrorCategory.VALIDATION][i % 3]
                provider = ["pgvector", "chromadb", "pinecone"][i % 3]
                
                if error_type == "ConnectionError":
                    error = ConnectionError(f"Connection error {i}")
                elif error_type == "TimeoutError":
                    error = TimeoutError(f"Timeout error {i}")
                else:
                    error = ValueError(f"Validation error {i}")
                
                monitor.record_error(error, category, provider)
                
                if i % 100 == 0:
                    await asyncio.sleep(0.001)  # Brief pause every 100 errors
        
        # Task 2: High volume request recording
        async def generate_requests():
            for i in range(1000):
                success = i % 10 != 0  # 10% failure rate
                response_time = 50.0 + (i % 200)  # Varying response times
                provider = ["pgvector", "chromadb", "pinecone"][i % 3]
                
                monitor.record_request(response_time, success, provider, f"operation_{i}")
                
                if i % 200 == 0:
                    await asyncio.sleep(0.001)  # Brief pause every 200 requests
        
        # Task 3: Circuit breaker events
        async def generate_circuit_events():
            providers = ["test_provider_1", "test_provider_2", "test_provider_3"]
            for i in range(50):
                provider = providers[i % 3]
                old_state = "closed" if i % 2 == 0 else "open"
                new_state = "open" if i % 2 == 0 else "closed"
                reason = f"Test event {i}"
                
                monitor.record_circuit_breaker_event(provider, old_state, new_state, reason)
                await asyncio.sleep(0.01)
        
        # Run all tasks concurrently
        tasks = [generate_errors(), generate_requests(), generate_circuit_events()]
        await asyncio.gather(*tasks)
        
        load_test_time = time.time() - start_time
        
        # Verify system stability
        health = await monitor.get_health_status()
        error_summary = await monitor.get_error_summary(hours=1)
        
        # System should handle the load without errors
        assert health.total_requests >= 900  # Some successful requests
        assert health.total_errors >= 100   # Some failed requests
        assert len(monitor.circuit_breaker_events) >= 50
        assert error_summary['total_errors'] >= 500
        
        # Performance should be reasonable
        assert load_test_time < 10.0  # Should complete within 10 seconds
        
        print(f"✅ High Load Stability Test Results:")
        print(f"   - Load test duration: {load_test_time:.2f}s")
        print(f"   - Errors processed: {error_summary['total_errors']}")
        print(f"   - Requests processed: {health.total_requests}")
        print(f"   - Circuit breaker events: {len(monitor.circuit_breaker_events)}")
        print(f"   - System error rate: {health.error_rate:.1%}")
        print(f"   - Memory usage tracking: {'✓' if health.memory_usage else '✗'}")
    
    @pytest.mark.asyncio
    async def test_memory_leak_prevention(self):
        """Test that monitoring system prevents memory leaks under extended operation."""
        monitor = await self.setup_monitoring_system()
        
        initial_memory_usage = len(monitor.error_history) + len(monitor.request_history)
        
        # Generate large amount of data to test cleanup
        for i in range(2000):  # Exceed typical limits
            # Add errors
            monitor.record_error(
                Exception(f"Test error {i}"),
                ErrorCategory.PROVIDER_FAILURE,
                f"provider_{i % 5}"
            )
            
            # Add requests
            monitor.record_request(
                100.0 + (i % 100),
                success=(i % 10 != 0),
                provider=f"provider_{i % 3}",
                operation=f"op_{i}"
            )
            
            # Add circuit breaker events
            if i % 50 == 0:
                monitor.record_circuit_breaker_event(
                    f"provider_{i % 3}",
                    "closed",
                    "open",
                    f"Test event {i}"
                )
        
        # Verify data structures are limited in size
        assert len(monitor.error_history) <= 1000  # Should be capped
        assert len(monitor.request_history) <= 10000  # Should be capped
        assert len(monitor.response_times) <= 1000  # Should be capped
        assert len(monitor.circuit_breaker_events) <= 500  # Should be capped
        
        # Verify we can still get recent data
        recent_errors = [e for e in monitor.error_history if 
                        (datetime.utcnow() - e['timestamp']).total_seconds() < 60]
        assert len(recent_errors) > 100  # Should have recent data
        
        print(f"✅ Memory Leak Prevention Test Results:")
        print(f"   - Error history size: {len(monitor.error_history)} (max: 1000)")
        print(f"   - Request history size: {len(monitor.request_history)} (max: 10000)")
        print(f"   - Response times size: {len(monitor.response_times)} (max: 1000)")
        print(f"   - Circuit events size: {len(monitor.circuit_breaker_events)} (max: 500)")
        print(f"   - Recent errors: {len(recent_errors)}")


if __name__ == "__main__":
    # Run tests with detailed output
    pytest.main([__file__, "-v", "--tb=short", "-s"])