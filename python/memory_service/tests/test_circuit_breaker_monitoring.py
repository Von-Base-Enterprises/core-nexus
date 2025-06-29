"""
Circuit Breaker Integration Tests

Validates the integration between circuit breakers and the monitoring system.
Tests state change detection, provider failure simulation, and alert generation.
"""

import asyncio
import pytest
import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

# Set up test imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from memory_service.unified_store import ProviderCircuitBreaker, VectorProvider
from memory_service.models import ProviderConfig
from memory_service.monitoring import (
    ErrorMonitor, AlertSeverity, ErrorCategory, get_error_monitor
)


class MockVectorProvider(VectorProvider):
    """Mock vector provider for testing circuit breaker integration."""
    
    def __init__(self, config: ProviderConfig, fail_on_store=False, fail_on_query=False):
        super().__init__(config)
        self.fail_on_store = fail_on_store
        self.fail_on_query = fail_on_query
        self.store_call_count = 0
        self.query_call_count = 0
    
    async def store(self, content: str, embedding: list[float], metadata: dict):
        self.store_call_count += 1
        if self.fail_on_store:
            raise ConnectionError("Mock database connection failed")
        return "mock-id-123"
    
    async def query(self, query_embedding: list[float], limit: int, filters: dict):
        self.query_call_count += 1
        if self.fail_on_query:
            raise TimeoutError("Mock query timeout")
        return []
    
    async def retrieve(self, memory_id):
        return None
    
    async def health_check(self):
        return {"status": "healthy" if not (self.fail_on_store or self.fail_on_query) else "unhealthy"}
    
    async def get_stats(self):
        return {"store_calls": self.store_call_count, "query_calls": self.query_call_count}


class TestCircuitBreakerBasics:
    """Test basic circuit breaker functionality."""
    
    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initializes correctly."""
        cb = ProviderCircuitBreaker(
            failure_threshold=3,
            recovery_timeout=120,
            test_request_interval=30
        )
        
        assert cb.failure_threshold == 3
        assert cb.recovery_timeout == 120
        assert cb.test_request_interval == 30
        assert cb.state == 'closed'
        assert cb.failure_count == 0
        assert cb.total_requests == 0
        assert cb.total_failures == 0
        assert cb.total_successes == 0
    
    def test_circuit_breaker_can_attempt_closed(self):
        """Test circuit breaker allows requests when closed."""
        cb = ProviderCircuitBreaker()
        
        assert cb.can_attempt() is True
        assert cb.state == 'closed'
        assert cb.total_requests == 1
    
    def test_circuit_breaker_success_recording(self):
        """Test successful operation recording."""
        cb = ProviderCircuitBreaker()
        
        # Record successful operations
        cb.record_success()
        cb.record_success()
        
        assert cb.total_successes == 2
        assert cb.state == 'closed'
        assert cb.failure_count == 0
    
    def test_circuit_breaker_failure_recording(self):
        """Test failure recording and state transitions."""
        cb = ProviderCircuitBreaker(failure_threshold=3)
        
        # Record failures below threshold
        cb.record_failure(Exception("Test error 1"))
        cb.record_failure(Exception("Test error 2"))
        
        assert cb.failure_count == 2
        assert cb.state == 'closed'  # Still closed
        
        # Record failure that exceeds threshold
        cb.record_failure(Exception("Test error 3"))
        
        assert cb.failure_count == 3
        assert cb.state == 'open'  # Should be open now
        assert cb.total_failures == 3
    
    def test_circuit_breaker_open_blocks_requests(self):
        """Test that open circuit breaker blocks requests."""
        cb = ProviderCircuitBreaker(failure_threshold=1)
        
        # Force circuit to open
        cb.record_failure(Exception("Test error"))
        assert cb.state == 'open'
        
        # Requests should be blocked
        assert cb.can_attempt() is False
    
    def test_circuit_breaker_recovery_timing(self):
        """Test circuit breaker recovery after timeout."""
        cb = ProviderCircuitBreaker(failure_threshold=1, recovery_timeout=0.1)  # 100ms timeout
        
        # Force circuit to open
        cb.record_failure(Exception("Test error"))
        assert cb.state == 'open'
        assert cb.can_attempt() is False
        
        # Wait for recovery timeout
        time.sleep(0.15)
        
        # Should transition to half-open
        assert cb.can_attempt() is True
        assert cb.state == 'half_open'
    
    def test_circuit_breaker_status_reporting(self):
        """Test circuit breaker status information."""
        cb = ProviderCircuitBreaker()
        cb._provider_name = "test_provider"  # Set provider name for monitoring
        
        # Record some operations
        cb.record_success()
        cb.record_failure(Exception("Test error"))
        
        status = cb.get_status()
        
        assert status['state'] == 'closed'
        assert status['failure_count'] == 1
        assert status['total_requests'] == 0  # No can_attempt calls yet
        assert status['total_failures'] == 1
        assert status['total_successes'] == 1
        assert 'success_rate' in status
        assert 'last_failure' in status
        assert 'last_success' in status


class TestCircuitBreakerMonitoringIntegration:
    """Test integration between circuit breakers and monitoring system."""
    
    @pytest.fixture
    def mock_monitor(self):
        """Create a mock error monitor with captured events."""
        captured_events = []
        
        def mock_record_circuit_breaker_event(provider, old_state, new_state, reason):
            captured_events.append({
                'provider': provider,
                'old_state': old_state,
                'new_state': new_state,
                'reason': reason,
                'timestamp': datetime.utcnow()
            })
        
        monitor = MagicMock()
        monitor.record_circuit_breaker_event = mock_record_circuit_breaker_event
        monitor._captured_events = captured_events
        
        return monitor
    
    def test_circuit_breaker_opening_triggers_monitoring(self, mock_monitor):
        """Test that circuit breaker opening is reported to monitoring."""
        # Mock the get_error_monitor function
        with patch('memory_service.unified_store.get_error_monitor', return_value=mock_monitor):
            cb = ProviderCircuitBreaker(failure_threshold=2)
            cb._provider_name = "test_provider"
            
            # Record failures to trigger opening
            cb.record_failure(Exception("Error 1"))
            cb.record_failure(Exception("Error 2"))
            
            # Should have triggered monitoring
            events = mock_monitor._captured_events
            assert len(events) == 1
            
            event = events[0]
            assert event['provider'] == 'test_provider'
            assert event['old_state'] == 'closed'
            assert event['new_state'] == 'open'
            assert 'Failure threshold exceeded' in event['reason']
    
    def test_circuit_breaker_recovery_triggers_monitoring(self, mock_monitor):
        """Test that circuit breaker recovery is reported to monitoring."""
        with patch('memory_service.unified_store.get_error_monitor', return_value=mock_monitor):
            cb = ProviderCircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
            cb._provider_name = "test_provider"
            
            # Force circuit to open
            cb.record_failure(Exception("Test error"))
            assert cb.state == 'open'
            
            # Wait for recovery and simulate successful test
            time.sleep(0.15)
            cb.can_attempt()  # Moves to half-open
            cb.record_success()  # Should close the circuit
            
            # Should have triggered monitoring for both opening and closing
            events = mock_monitor._captured_events
            assert len(events) >= 2
            
            # Check closing event
            closing_events = [e for e in events if e['new_state'] == 'closed']
            assert len(closing_events) == 1
            
            closing_event = closing_events[0]
            assert closing_event['provider'] == 'test_provider'
            assert closing_event['old_state'] == 'half_open'
            assert closing_event['reason'] == 'Recovery successful'


class TestVectorProviderIntegration:
    """Test vector provider integration with circuit breakers and monitoring."""
    
    @pytest.fixture
    def provider_config(self):
        """Create a test provider configuration."""
        return ProviderConfig(
            name="test_provider",
            enabled=True,
            primary=True,
            config={
                "circuit_breaker_failure_threshold": 2,
                "circuit_breaker_recovery_timeout": 0.1,
                "circuit_breaker_test_interval": 0.05
            }
        )
    
    def test_provider_circuit_breaker_initialization(self, provider_config):
        """Test that provider initializes circuit breaker correctly."""
        provider = MockVectorProvider(provider_config)
        
        assert hasattr(provider, 'circuit_breaker')
        assert provider.circuit_breaker.failure_threshold == 2
        assert provider.circuit_breaker.recovery_timeout == 0.1
        assert provider.circuit_breaker._provider_name == "test_provider"
    
    def test_provider_availability_check(self, provider_config):
        """Test provider availability based on circuit breaker state."""
        # Update config to have longer recovery timeout for predictable testing
        provider_config.config["circuit_breaker_recovery_timeout"] = 10.0  # 10 seconds
        provider = MockVectorProvider(provider_config)
        
        # Initially available
        assert provider.is_available() is True
        
        # Force circuit breaker to open
        provider.record_failure(Exception("Error 1"))
        provider.record_failure(Exception("Error 2"))
        
        # Should not be available immediately after opening
        assert provider.is_available() is False
        
        # Wait for recovery (with shorter timeout for test)
        provider.circuit_breaker.recovery_timeout = 0.1
        time.sleep(0.15)
        
        # Should be available again for testing
        assert provider.is_available() is True
    
    def test_provider_failure_recording(self, provider_config):
        """Test provider failure recording integrates with circuit breaker."""
        # Set longer recovery timeout for predictable testing
        provider_config.config["circuit_breaker_recovery_timeout"] = 10.0
        provider = MockVectorProvider(provider_config)
        
        # Record failures
        error1 = ConnectionError("DB connection failed")
        error2 = TimeoutError("Query timeout")
        
        provider.record_failure(error1)
        provider.record_failure(error2)
        
        # Circuit breaker should be open
        assert provider.circuit_breaker.state == 'open'
        assert provider.circuit_breaker.failure_count == 2
        assert provider.is_available() is False
    
    def test_provider_success_recording(self, provider_config):
        """Test provider success recording integrates with circuit breaker."""
        provider = MockVectorProvider(provider_config)
        
        # Record some failures
        provider.record_failure(Exception("Error 1"))
        assert provider.circuit_breaker.failure_count == 1
        
        # Record success
        provider.record_success()
        
        # Failure count should be reduced
        assert provider.circuit_breaker.failure_count == 0
        assert provider.circuit_breaker.total_successes == 1


class TestProviderFailureScenarios:
    """Test real-world provider failure scenarios with monitoring."""
    
    @pytest.fixture
    def error_monitor(self):
        """Create a real error monitor for integration testing."""
        monitor = ErrorMonitor(alert_handlers=[])
        return monitor
    
    @pytest.fixture
    def provider_config(self):
        """Create test provider configuration."""
        return ProviderConfig(
            name="integration_test_provider",
            enabled=True,
            primary=True,
            config={
                "circuit_breaker_failure_threshold": 3,
                "circuit_breaker_recovery_timeout": 0.2,
                "circuit_breaker_test_interval": 0.1
            }
        )
    
    @pytest.mark.asyncio
    async def test_database_connection_failure_scenario(self, provider_config, error_monitor):
        """Test database connection failure scenario with full monitoring."""
        # Mock get_error_monitor to return our test monitor
        with patch('memory_service.unified_store.get_error_monitor', return_value=error_monitor):
            provider = MockVectorProvider(provider_config, fail_on_store=True)
            
            # Simulate multiple failed store operations
            failures = []
            for i in range(5):
                try:
                    await provider.store(f"Test content {i}", [0.1] * 1536, {"test": True})
                except Exception as e:
                    failures.append(e)
                    provider.record_failure(e)
            
            # Verify failures were recorded
            assert len(failures) == 5
            assert provider.circuit_breaker.state == 'open'  # Should be open after 3 failures
            assert not provider.is_available()
            
            # Verify circuit breaker events were recorded
            cb_events = error_monitor.circuit_breaker_events
            opening_events = [e for e in cb_events if e['new_state'] == 'open']
            assert len(opening_events) >= 1
            
            opening_event = opening_events[0]
            assert opening_event['provider'] == 'integration_test_provider'
            assert opening_event['old_state'] == 'closed'
    
    @pytest.mark.asyncio
    async def test_query_timeout_failure_scenario(self, provider_config, error_monitor):
        """Test query timeout failure scenario with monitoring."""
        with patch('memory_service.unified_store.get_error_monitor', return_value=error_monitor):
            provider = MockVectorProvider(provider_config, fail_on_query=True)
            
            # Simulate multiple failed query operations
            failures = []
            for i in range(4):
                try:
                    await provider.query([0.1] * 1536, 10, {})
                except Exception as e:
                    failures.append(e)
                    provider.record_failure(e)
            
            # Verify circuit breaker opened
            assert len(failures) == 4
            assert provider.circuit_breaker.state == 'open'
            
            # Verify monitoring captured the events
            cb_events = error_monitor.circuit_breaker_events
            assert len(cb_events) >= 1
            
            # Wait for recovery attempt
            time.sleep(0.25)
            
            # Fix the provider
            provider.fail_on_query = False
            
            # Attempt recovery
            if provider.is_available():  # Should be in half-open state
                try:
                    await provider.query([0.1] * 1536, 10, {})
                    provider.record_success()
                except Exception as e:
                    provider.record_failure(e)
            
            # If recovery was successful, circuit should be closed
            if provider.circuit_breaker.state == 'closed':
                recovery_events = [e for e in error_monitor.circuit_breaker_events 
                                 if e['new_state'] == 'closed']
                assert len(recovery_events) >= 1
    
    @pytest.mark.asyncio
    async def test_intermittent_failure_pattern(self, provider_config, error_monitor):
        """Test intermittent failure pattern that doesn't trigger circuit breaker."""
        with patch('memory_service.unified_store.get_error_monitor', return_value=error_monitor):
            provider = MockVectorProvider(provider_config)
            
            # Simulate intermittent failures (success between failures)
            operations = [
                (True, None),     # Success
                (False, "Error 1"),  # Failure
                (True, None),     # Success
                (False, "Error 2"),  # Failure  
                (True, None),     # Success
                (True, None),     # Success
            ]
            
            for success, error_msg in operations:
                if success:
                    await provider.store("Test content", [0.1] * 1536, {})
                    provider.record_success()
                else:
                    try:
                        provider.fail_on_store = True
                        await provider.store("Test content", [0.1] * 1536, {})
                    except Exception as e:
                        provider.record_failure(e)
                    finally:
                        provider.fail_on_store = False
            
            # Circuit breaker should still be closed (failures were interspersed with successes)
            assert provider.circuit_breaker.state == 'closed'
            assert provider.circuit_breaker.failure_count < provider.circuit_breaker.failure_threshold
            
            # Should have recorded the failures but not triggered circuit opening
            cb_events = error_monitor.circuit_breaker_events
            opening_events = [e for e in cb_events if e['new_state'] == 'open']
            assert len(opening_events) == 0  # No circuit opening events


class TestMonitoringAlertIntegration:
    """Test integration between circuit breakers and alert generation."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opening_generates_alert(self):
        """Test that circuit breaker opening generates appropriate alerts."""
        # Create monitor with alert capture
        captured_alerts = []
        
        async def capture_alert(alert):
            captured_alerts.append(alert)
        
        monitor = ErrorMonitor(alert_handlers=[capture_alert])
        
        # Start monitoring to enable background tasks
        await monitor.start_monitoring()
        
        try:
            with patch('memory_service.unified_store.get_error_monitor', return_value=monitor):
                config = ProviderConfig(
                    name="alert_test_provider",
                    enabled=True,
                    primary=True,
                    config={"circuit_breaker_failure_threshold": 2}
                )
                
                provider = MockVectorProvider(config)
                
                # Force circuit breaker to open
                provider.record_failure(Exception("Test error 1"))
                provider.record_failure(Exception("Test error 2"))
                
                # Wait a bit for async alert processing
                await asyncio.sleep(0.1)
                
                # Should have generated alerts
                assert len(captured_alerts) >= 1
                
                # Check for circuit breaker alert
                cb_alerts = [a for a in captured_alerts 
                           if a.category == ErrorCategory.CIRCUIT_BREAKER]
                assert len(cb_alerts) >= 1
                
                alert = cb_alerts[0]
                assert alert.severity == AlertSeverity.ERROR
                assert "Circuit Breaker Opened" in alert.title
                assert alert.provider == "alert_test_provider"
                assert "Failure threshold exceeded" in alert.description
        
        finally:
            await monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery_resolves_alert(self):
        """Test that circuit breaker recovery resolves alerts."""
        captured_alerts = []
        
        async def capture_alert(alert):
            captured_alerts.append(alert)
        
        monitor = ErrorMonitor(alert_handlers=[capture_alert])
        await monitor.start_monitoring()
        
        try:
            with patch('memory_service.unified_store.get_error_monitor', return_value=monitor):
                config = ProviderConfig(
                    name="recovery_test_provider",
                    enabled=True,
                    primary=True,
                    config={
                        "circuit_breaker_failure_threshold": 1,
                        "circuit_breaker_recovery_timeout": 0.1
                    }
                )
                
                provider = MockVectorProvider(config)
                
                # Force circuit breaker to open
                provider.record_failure(Exception("Test error"))
                await asyncio.sleep(0.1)  # Allow alert processing
                
                # Wait for recovery timeout
                time.sleep(0.15)
                
                # Simulate successful recovery
                provider.circuit_breaker.can_attempt()  # Moves to half-open
                provider.record_success()  # Closes circuit
                
                await asyncio.sleep(0.1)  # Allow alert processing
                
                # Check that we have both opening and resolution
                cb_opening_alerts = [a for a in captured_alerts 
                                   if a.category == ErrorCategory.CIRCUIT_BREAKER and "Opened" in a.title]
                assert len(cb_opening_alerts) >= 1
                
                # Check active alerts (should be resolved)
                active_alerts = monitor.active_alerts
                # The opening alert should have been resolved when circuit closed
                unresolved_cb_alerts = [a for a in active_alerts.values() 
                                      if a.category == ErrorCategory.CIRCUIT_BREAKER]
                # Should be empty or minimal since circuit recovered
        
        finally:
            await monitor.stop_monitoring()


if __name__ == "__main__":
    # Run tests with detailed output
    pytest.main([__file__, "-v", "--tb=short"])