"""
Core Monitoring System Tests

Comprehensive validation of the ErrorMonitor class and monitoring system functionality.
Tests error recording, performance tracking, alert generation, and memory management.
"""

import asyncio
import pytest
import time
import logging
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

# Set up test imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from memory_service.monitoring import (
    ErrorMonitor, Alert, AlertSeverity, ErrorCategory, HealthMetrics,
    console_alert_handler, log_alert_handler
)

# Disable logging during tests to reduce noise
logging.getLogger().setLevel(logging.CRITICAL)


class TestErrorMonitorCore:
    """Test core ErrorMonitor functionality."""
    
    @pytest.fixture
    def monitor(self):
        """Create a fresh ErrorMonitor instance for each test."""
        return ErrorMonitor(
            alert_handlers=[],  # No handlers for unit tests
            error_rate_threshold=0.1,  # 10% error rate threshold
            response_time_threshold=2.0,  # 2 second response time threshold
            memory_usage_threshold=0.8   # 80% memory threshold
        )
    
    def test_error_monitor_initialization(self, monitor):
        """Test ErrorMonitor initializes with correct default values."""
        assert monitor.error_rate_threshold == 0.1
        assert monitor.response_time_threshold == 2.0
        assert monitor.memory_usage_threshold == 0.8
        assert len(monitor.error_counts) == 0
        assert len(monitor.active_alerts) == 0
        assert len(monitor.error_history) == 0
        assert monitor._shutdown is False
    
    def test_error_recording_basic(self, monitor):
        """Test basic error recording functionality."""
        test_error = Exception("Test database connection failed")
        
        # Record error
        monitor.record_error(
            error=test_error,
            category=ErrorCategory.PROVIDER_FAILURE,
            provider="pgvector",
            component="unified_store"
        )
        
        # Verify error was recorded
        assert len(monitor.error_history) == 1
        assert monitor.error_counts["provider_failure"] == 1
        
        error_record = monitor.error_history[0]
        assert error_record['error_type'] == 'Exception'
        assert error_record['error_message'] == 'Test database connection failed'
        assert error_record['category'] == 'provider_failure'
        assert error_record['provider'] == 'pgvector'
        assert error_record['component'] == 'unified_store'
        assert isinstance(error_record['timestamp'], datetime)
    
    def test_error_categorization(self, monitor):
        """Test different error categories are properly tracked."""
        errors = [
            (ConnectionError("DB timeout"), ErrorCategory.CONNECTION_POOL, "pgvector"),
            (TimeoutError("Query timeout"), ErrorCategory.TIMEOUT, "chromadb"),
            (ValueError("Invalid auth"), ErrorCategory.AUTHENTICATION, "pinecone"),
            (RuntimeError("Circuit open"), ErrorCategory.CIRCUIT_BREAKER, "pgvector"),
            (MemoryError("Out of memory"), ErrorCategory.MEMORY_LEAK, "system")
        ]
        
        for error, category, provider in errors:
            monitor.record_error(error, category, provider)
        
        # Verify all categories tracked
        assert monitor.error_counts["connection_pool"] == 1
        assert monitor.error_counts["timeout"] == 1
        assert monitor.error_counts["authentication"] == 1
        assert monitor.error_counts["circuit_breaker"] == 1
        assert monitor.error_counts["memory_leak"] == 1
        assert len(monitor.error_history) == 5
    
    def test_request_recording_success(self, monitor):
        """Test successful request recording."""
        # Record successful requests
        monitor.record_request(150.0, success=True, provider="pgvector", operation="store_memory")
        monitor.record_request(75.5, success=True, provider="chromadb", operation="query_memory")
        
        # Verify requests were recorded
        assert len(monitor.request_history) == 2
        assert len(monitor.response_times) == 2
        
        # Check request details
        request1 = monitor.request_history[0]
        assert request1['duration_ms'] == 150.0
        assert request1['success'] is True
        assert request1['provider'] == 'pgvector'
        assert request1['operation'] == 'store_memory'
        
        # Check response times
        assert 150.0 in monitor.response_times
        assert 75.5 in monitor.response_times
    
    def test_request_recording_failure(self, monitor):
        """Test failed request recording."""
        # Record failed requests
        monitor.record_request(5000.0, success=False, provider="pinecone", operation="store_memory")
        monitor.record_request(250.0, success=False, provider="pgvector", operation="query_memory")
        
        # Verify requests were recorded
        assert len(monitor.request_history) == 2
        
        # Check failure details
        failed_requests = [r for r in monitor.request_history if not r['success']]
        assert len(failed_requests) == 2
        assert failed_requests[0]['duration_ms'] == 5000.0
        assert failed_requests[1]['duration_ms'] == 250.0
    
    @pytest.mark.asyncio
    async def test_alert_creation_and_resolution(self, monitor):
        """Test alert creation and resolution functionality."""
        # Create test alert
        alert = await monitor.create_alert(
            severity=AlertSeverity.ERROR,
            category=ErrorCategory.PROVIDER_FAILURE,
            title="PgVector Connection Failed",
            description="Database connection timeout after 30 seconds",
            provider="pgvector",
            metrics={"timeout_duration": 30, "retry_count": 3}
        )
        
        # Verify alert creation
        assert alert.id in monitor.active_alerts
        assert len(monitor.alert_history) == 1
        assert alert.severity == AlertSeverity.ERROR
        assert alert.category == ErrorCategory.PROVIDER_FAILURE
        assert alert.title == "PgVector Connection Failed"
        assert alert.provider == "pgvector"
        assert alert.metrics["timeout_duration"] == 30
        assert alert.resolved is False
        
        # Resolve alert
        await monitor.resolve_alert(alert.id, "Connection restored after database restart")
        
        # Verify resolution
        assert alert.id not in monitor.active_alerts
        assert alert.resolved is True
        assert "Connection restored" in alert.description
    
    def test_circuit_breaker_event_recording(self, monitor):
        """Test circuit breaker event recording."""
        # Record circuit breaker opening
        monitor.record_circuit_breaker_event(
            provider="pgvector",
            old_state="closed",
            new_state="open",
            reason="Failure threshold exceeded: 5 failures"
        )
        
        # Verify event was recorded
        assert len(monitor.circuit_breaker_events) == 1
        
        event = monitor.circuit_breaker_events[0]
        assert event['provider'] == 'pgvector'
        assert event['old_state'] == 'closed'
        assert event['new_state'] == 'open'
        assert event['reason'] == 'Failure threshold exceeded: 5 failures'
        assert isinstance(event['timestamp'], datetime)
    
    @pytest.mark.asyncio
    async def test_health_status_calculation(self, monitor):
        """Test health status calculation with real data."""
        # Add some historical data
        now = datetime.utcnow()
        
        # Add recent successful requests
        for i in range(95):
            monitor.record_request(100.0, success=True, provider="pgvector")
        
        # Add some failed requests
        for i in range(5):
            monitor.record_request(200.0, success=False, provider="pgvector")
            monitor.record_error(
                Exception(f"Test error {i}"),
                ErrorCategory.PROVIDER_FAILURE,
                provider="pgvector"
            )
        
        # Get health status
        health = await monitor.get_health_status()
        
        # Verify health metrics
        assert isinstance(health, HealthMetrics)
        assert health.total_requests == 100
        assert health.total_errors == 5
        assert health.error_rate == 0.05  # 5% error rate
        assert health.avg_response_time > 0
        assert isinstance(health.circuit_breaker_states, dict)
        assert isinstance(health.provider_health, dict)
        assert health.active_alerts == 0  # No alerts created yet
    
    @pytest.mark.asyncio
    async def test_error_summary_generation(self, monitor):
        """Test error summary generation with time filtering."""
        # Add errors over different time periods
        now = datetime.utcnow()
        
        # Recent errors (within 24 hours)
        for i in range(10):
            monitor.record_error(
                Exception(f"Recent error {i}"),
                ErrorCategory.PROVIDER_FAILURE,
                provider="pgvector"
            )
        
        # Older errors (simulate by manipulating timestamp)
        old_error_record = {
            'timestamp': now - timedelta(hours=48),  # 48 hours ago
            'error_type': 'Exception',
            'error_message': 'Old error',
            'category': 'timeout',
            'provider': 'chromadb',
            'component': 'unified_store',
            'metadata': {}
        }
        monitor.error_history.append(old_error_record)
        
        # Get error summary for last 24 hours
        summary = await monitor.get_error_summary(hours=24)
        
        # Verify summary
        assert summary['total_errors'] == 10  # Only recent errors
        assert summary['by_category']['provider_failure'] == 10
        assert summary['by_provider']['pgvector'] == 10
        assert summary['time_period_hours'] == 24
        assert summary['active_alerts'] == 0
    
    def test_memory_leak_prevention(self, monitor):
        """Test that data structures have size limits to prevent memory leaks."""
        # Fill up error history beyond limit
        for i in range(1500):  # More than maxlen=1000
            monitor.record_error(
                Exception(f"Error {i}"),
                ErrorCategory.UNKNOWN
            )
        
        # Verify size is limited
        assert len(monitor.error_history) <= 1000
        
        # Fill up request history beyond limit
        for i in range(15000):  # More than maxlen=10000
            monitor.record_request(100.0, success=True)
        
        # Verify size is limited
        assert len(monitor.request_history) <= 10000
        
        # Fill up response times beyond limit
        for i in range(1500):  # More than maxlen=1000
            monitor.response_times.append(100.0)
        
        # Verify size is limited
        assert len(monitor.response_times) <= 1000


class TestAlertHandlers:
    """Test alert handler functionality."""
    
    @pytest.mark.asyncio
    async def test_console_alert_handler(self, capsys):
        """Test console alert handler output."""
        alert = Alert(
            id=str(uuid4()),
            severity=AlertSeverity.ERROR,
            category=ErrorCategory.PROVIDER_FAILURE,
            title="Test Alert",
            description="This is a test alert for validation",
            timestamp=datetime.utcnow(),
            provider="pgvector"
        )
        
        # Call handler
        await console_alert_handler(alert)
        
        # Capture output
        captured = capsys.readouterr()
        
        # Verify output contains alert information
        assert "🚨 ALERT [ERROR] Test Alert" in captured.out
        assert "Description: This is a test alert for validation" in captured.out
        assert "Provider: pgvector" in captured.out
    
    @pytest.mark.asyncio
    async def test_log_alert_handler(self, caplog):
        """Test log-based alert handler."""
        alert = Alert(
            id=str(uuid4()),
            severity=AlertSeverity.CRITICAL,
            category=ErrorCategory.CIRCUIT_BREAKER,
            title="Circuit Breaker Opened",
            description="Circuit breaker opened due to high failure rate",
            timestamp=datetime.utcnow(),
            provider="pinecone",
            metrics={"failure_count": 5, "threshold": 5}
        )
        
        with caplog.at_level(logging.ERROR):
            await log_alert_handler(alert)
        
        # Verify log entry
        assert len(caplog.records) == 1
        log_record = caplog.records[0]
        assert log_record.levelname == "ERROR"
        assert "ALERT: critical - Circuit Breaker Opened" in log_record.message
        assert log_record.alert_id == alert.id
        assert log_record.provider == "pinecone"


class TestMonitoringUnderLoad:
    """Test monitoring system under load conditions."""
    
    @pytest.fixture
    def monitor(self):
        """Create monitor with realistic thresholds for load testing."""
        return ErrorMonitor(
            alert_handlers=[],
            error_rate_threshold=0.05,  # 5% error rate
            response_time_threshold=1.0,  # 1 second
            memory_usage_threshold=0.9   # 90% memory
        )
    
    @pytest.mark.asyncio
    async def test_high_volume_error_recording(self, monitor):
        """Test error recording under high volume."""
        start_time = time.time()
        
        # Record 1000 errors rapidly
        for i in range(1000):
            monitor.record_error(
                Exception(f"Load test error {i}"),
                ErrorCategory.PROVIDER_FAILURE if i % 2 == 0 else ErrorCategory.TIMEOUT,
                provider="pgvector" if i % 3 == 0 else "chromadb"
            )
        
        recording_time = time.time() - start_time
        
        # Verify performance and accuracy
        assert recording_time < 1.0  # Should complete in under 1 second
        assert len(monitor.error_history) == 1000
        assert monitor.error_counts["provider_failure"] == 500
        assert monitor.error_counts["timeout"] == 500
    
    @pytest.mark.asyncio
    async def test_concurrent_monitoring_operations(self, monitor):
        """Test concurrent monitoring operations for thread safety."""
        
        async def record_errors():
            for i in range(100):
                monitor.record_error(Exception(f"Concurrent error {i}"), ErrorCategory.PROVIDER_FAILURE)
                await asyncio.sleep(0.001)  # Small delay to allow interleaving
        
        async def record_requests():
            for i in range(100):
                monitor.record_request(50.0 + i, success=(i % 10 != 0))  # 10% failure rate
                await asyncio.sleep(0.001)
        
        async def record_circuit_events():
            for i in range(50):
                monitor.record_circuit_breaker_event(
                    provider=f"provider_{i % 3}",
                    old_state="closed",
                    new_state="open",
                    reason=f"Test event {i}"
                )
                await asyncio.sleep(0.002)
        
        # Run all operations concurrently
        await asyncio.gather(
            record_errors(),
            record_requests(),
            record_circuit_events()
        )
        
        # Verify all data was recorded correctly
        assert len(monitor.error_history) == 100
        assert len(monitor.request_history) == 100
        assert len(monitor.circuit_breaker_events) == 50
        assert monitor.error_counts["provider_failure"] == 100
    
    @pytest.mark.asyncio
    async def test_error_rate_threshold_detection(self, monitor):
        """Test automatic error rate threshold detection and alerting."""
        # Set up mock alert handler to capture alerts
        captured_alerts = []
        
        async def capture_alert(alert):
            captured_alerts.append(alert)
        
        monitor.alert_handlers.append(capture_alert)
        
        # Record requests with high error rate (20% failures)
        for i in range(100):
            success = i % 5 != 0  # 20% failure rate (above 5% threshold)
            monitor.record_request(100.0, success=success)
            if not success:
                monitor.record_error(Exception(f"Failure {i}"), ErrorCategory.PROVIDER_FAILURE)
        
        # Trigger threshold check
        await monitor._check_error_rate_threshold()
        
        # Verify alert was generated
        assert len(captured_alerts) >= 1
        error_rate_alerts = [a for a in captured_alerts if "High Error Rate" in a.title]
        assert len(error_rate_alerts) >= 1
        
        alert = error_rate_alerts[0]
        assert alert.severity == AlertSeverity.ERROR
        assert alert.category == ErrorCategory.PERFORMANCE
        assert "20.0%" in alert.title or "0.2" in alert.description


class TestProductionScenarios:
    """Test monitoring system with production-like scenarios."""
    
    @pytest.fixture
    def production_monitor(self):
        """Create monitor configured for production scenarios."""
        captured_alerts = []
        
        async def capture_alert(alert):
            captured_alerts.append(alert)
        
        monitor = ErrorMonitor(
            alert_handlers=[capture_alert],
            error_rate_threshold=0.02,  # 2% error rate (strict)
            response_time_threshold=0.5,  # 500ms response time
            memory_usage_threshold=0.85   # 85% memory
        )
        monitor._captured_alerts = captured_alerts  # Store for test access
        return monitor
    
    @pytest.mark.asyncio
    async def test_database_outage_simulation(self, production_monitor):
        """Simulate database outage and verify monitoring response."""
        # Simulate normal operation
        for i in range(50):
            production_monitor.record_request(100.0, success=True, provider="pgvector")
        
        # Simulate database outage (all requests fail)
        for i in range(20):
            production_monitor.record_request(5000.0, success=False, provider="pgvector")
            production_monitor.record_error(
                ConnectionError("Database connection refused"),
                ErrorCategory.CONNECTION_POOL,
                provider="pgvector"
            )
        
        # Trigger threshold checks
        await production_monitor._check_error_rate_threshold()
        
        # Verify monitoring detected the outage
        health = await production_monitor.get_health_status()
        assert health.error_rate > 0.2  # High error rate during outage
        
        # Verify alerts were generated
        alerts = production_monitor._captured_alerts
        assert len(alerts) > 0
        
        # Check for error rate alert
        error_rate_alerts = [a for a in alerts if "High Error Rate" in a.title]
        assert len(error_rate_alerts) > 0
    
    @pytest.mark.asyncio
    async def test_performance_degradation_detection(self, production_monitor):
        """Test detection of gradual performance degradation."""
        # Normal performance baseline
        for i in range(100):
            production_monitor.record_request(150.0, success=True, provider="pgvector")
        
        # Gradual performance degradation
        for i in range(50):
            slow_time = 150.0 + (i * 20)  # Gradually increasing response time
            production_monitor.record_request(slow_time, success=True, provider="pgvector")
            
            # Check if we hit slow response threshold
            if slow_time > production_monitor.response_time_threshold * 1000:
                await production_monitor._check_response_time_threshold(slow_time)
        
        # Verify performance issues were detected
        alerts = production_monitor._captured_alerts
        slow_response_alerts = [a for a in alerts if "Slow Response" in a.title]
        assert len(slow_response_alerts) > 0
        
        # Verify response time tracking
        health = await production_monitor.get_health_status()
        assert health.avg_response_time > 300  # Should show degraded performance (adjusted for actual data)


if __name__ == "__main__":
    # Run tests with detailed output
    pytest.main([__file__, "-v", "--tb=short"])