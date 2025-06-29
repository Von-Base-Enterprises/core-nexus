"""
Monitoring API Endpoint Tests

Comprehensive validation of all monitoring API endpoints including health status,
error summaries, alerts, alert resolution, and circuit breaker status.
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

# Set up test imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from memory_service.api import app
from memory_service.monitoring import (
    ErrorMonitor, Alert, AlertSeverity, ErrorCategory, HealthMetrics
)
from memory_service.unified_store import UnifiedVectorStore, ProviderCircuitBreaker
from memory_service.models import ProviderConfig


# Use FastAPI's TestClient directly for compatibility


class TestMonitoringHealthEndpoint:
    """Test /monitoring/health endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_monitor(self):
        """Mock error monitor with test data."""
        monitor = MagicMock()
        
        # Mock health status
        health = HealthMetrics(
            timestamp=datetime.utcnow(),
            total_requests=1500,
            total_errors=45,
            error_rate=0.03,  # 3% error rate
            avg_response_time=125.5,
            circuit_breaker_states={
                'pgvector': 'closed',
                'chromadb': 'closed',
                'pinecone': 'open'
            },
            provider_health={
                'pgvector': {'status': 'healthy', 'response_time_ms': 85},
                'chromadb': {'status': 'healthy', 'response_time_ms': 65},
                'pinecone': {'status': 'degraded', 'response_time_ms': 250}
            },
            connection_pool_stats={
                'pgvector': {'active': 8, 'idle': 12, 'max': 30},
                'coordination': {'active': 2, 'idle': 3, 'max': 5}
            },
            memory_usage={
                'heap_usage_percent': 0.45,
                'cache_usage_percent': 0.32,
                'connection_pool_percent': 0.08
            },
            active_alerts=2
        )
        
        async def mock_get_health_status():
            return health
        
        monitor.get_health_status = mock_get_health_status
        return monitor
    
    def test_health_endpoint_success(self, client, mock_monitor):
        """Test successful health endpoint response."""
        with patch('memory_service.api.get_error_monitor', return_value=mock_monitor):
            response = client.get("/monitoring/health")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert 'timestamp' in data
            assert data['total_requests'] == 1500
            assert data['total_errors'] == 45
            assert data['error_rate'] == 0.03
            assert data['avg_response_time_ms'] == 125.5
            assert data['active_alerts'] == 2
            assert data['overall_health'] == 'degraded'  # Due to active alerts
            
            # Verify circuit breaker states
            cb_states = data['circuit_breaker_states']
            assert cb_states['pgvector'] == 'closed'
            assert cb_states['pinecone'] == 'open'
            
            # Verify provider health
            provider_health = data['provider_health']
            assert provider_health['pgvector']['status'] == 'healthy'
            assert provider_health['pinecone']['status'] == 'degraded'
    
    def test_health_endpoint_healthy_status(self, client):
        """Test health endpoint with healthy status."""
        # Mock healthy monitor
        monitor = MagicMock()
        health = HealthMetrics(
            timestamp=datetime.utcnow(),
            total_requests=1000,
            total_errors=5,
            error_rate=0.005,  # 0.5% error rate (healthy)
            avg_response_time=95.0,
            circuit_breaker_states={'pgvector': 'closed'},
            provider_health={'pgvector': {'status': 'healthy'}},
            connection_pool_stats={},
            memory_usage={},
            active_alerts=0  # No active alerts
        )
        
        async def mock_get_health_status():
            return health
        
        monitor.get_health_status = mock_get_health_status
        
        with patch('memory_service.api.get_error_monitor', return_value=monitor):
            response = client.get("/monitoring/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data['overall_health'] == 'healthy'  # Low error rate and no alerts
    
    def test_health_endpoint_error(self, client):
        """Test health endpoint error handling."""
        # Mock monitor that raises exception
        monitor = MagicMock()
        
        async def mock_get_health_status():
            raise Exception("Monitoring system failure")
        
        monitor.get_health_status = mock_get_health_status
        
        with patch('memory_service.api.get_error_monitor', return_value=monitor):
            response = client.get("/monitoring/health")
            
            assert response.status_code == 500
            data = response.json()
            assert 'error' in data
            assert 'Failed to get monitoring health status' in data['error']


class TestMonitoringErrorsEndpoint:
    """Test /monitoring/errors endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_monitor(self):
        """Mock error monitor with error summary data."""
        monitor = MagicMock()
        
        async def mock_get_error_summary(hours):
            return {
                'total_errors': 125,
                'by_category': {
                    'provider_failure': 45,
                    'timeout': 30,
                    'circuit_breaker': 25,
                    'connection_pool': 15,
                    'validation': 10
                },
                'by_provider': {
                    'pgvector': 55,
                    'chromadb': 35,
                    'pinecone': 35
                },
                'by_component': {
                    'unified_store': 85,
                    'coordination_engine': 25,
                    'api': 15
                },
                'time_period_hours': hours,
                'active_alerts': 3
            }
        
        monitor.get_error_summary = mock_get_error_summary
        return monitor
    
    def test_errors_endpoint_default_period(self, client, mock_monitor):
        """Test errors endpoint with default 24-hour period."""
        with patch('memory_service.api.get_error_monitor', return_value=mock_monitor):
            response = client.get("/monitoring/errors")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert data['total_errors'] == 125
            assert data['time_period_hours'] == 24  # Default
            assert data['active_alerts'] == 3
            
            # Verify categorization
            by_category = data['by_category']
            assert by_category['provider_failure'] == 45
            assert by_category['timeout'] == 30
            assert by_category['circuit_breaker'] == 25
            
            # Verify provider breakdown
            by_provider = data['by_provider']
            assert by_provider['pgvector'] == 55
            assert by_provider['chromadb'] == 35
            assert by_provider['pinecone'] == 35
    
    def test_errors_endpoint_custom_period(self, client, mock_monitor):
        """Test errors endpoint with custom time period."""
        with patch('memory_service.api.get_error_monitor', return_value=mock_monitor):
            response = client.get("/monitoring/errors?hours=72")
            
            assert response.status_code == 200
            data = response.json()
            assert data['time_period_hours'] == 72
    
    def test_errors_endpoint_validation(self, client, mock_monitor):
        """Test errors endpoint parameter validation."""
        with patch('memory_service.api.get_error_monitor', return_value=mock_monitor):
            # Test minimum hours validation
            response = client.get("/monitoring/errors?hours=0")
            assert response.status_code == 422  # Validation error
            
            # Test maximum hours validation
            response = client.get("/monitoring/errors?hours=200")
            assert response.status_code == 422  # Validation error (max 168)
    
    def test_errors_endpoint_error(self, client):
        """Test errors endpoint error handling."""
        monitor = MagicMock()
        
        async def mock_get_error_summary(hours):
            raise Exception("Error summary generation failed")
        
        monitor.get_error_summary = mock_get_error_summary
        
        with patch('memory_service.api.get_error_monitor', return_value=monitor):
            response = client.get("/monitoring/errors")
            
            assert response.status_code == 500
            data = response.json()
            assert 'error' in data


class TestMonitoringAlertsEndpoint:
    """Test /monitoring/alerts endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_monitor(self):
        """Mock error monitor with alerts data."""
        monitor = MagicMock()
        
        # Create test alerts
        active_alert1 = Alert(
            id="alert-1",
            severity=AlertSeverity.ERROR,
            category=ErrorCategory.CIRCUIT_BREAKER,
            title="Circuit Breaker Opened: pgvector",
            description="Circuit breaker opened due to high failure rate",
            timestamp=datetime.utcnow(),
            provider="pgvector"
        )
        
        active_alert2 = Alert(
            id="alert-2",
            severity=AlertSeverity.WARNING,
            category=ErrorCategory.PERFORMANCE,
            title="High Response Time: 2500ms",
            description="Response time exceeds threshold",
            timestamp=datetime.utcnow() - timedelta(minutes=15),
            provider="chromadb"
        )
        
        resolved_alert = Alert(
            id="alert-3",
            severity=AlertSeverity.CRITICAL,
            category=ErrorCategory.PROVIDER_FAILURE,
            title="Database Connection Failed",
            description="All database connections failed",
            timestamp=datetime.utcnow() - timedelta(hours=2),
            resolved=True
        )
        
        monitor.active_alerts = {
            "alert-1": active_alert1,
            "alert-2": active_alert2
        }
        
        monitor.alert_history = [active_alert1, active_alert2, resolved_alert]
        
        return monitor
    
    def test_alerts_endpoint_success(self, client, mock_monitor):
        """Test successful alerts endpoint response."""
        with patch('memory_service.api.get_error_monitor', return_value=mock_monitor):
            response = client.get("/monitoring/alerts")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert 'active_alerts' in data
            assert 'recent_alerts' in data
            assert 'active_count' in data
            assert 'total_alerts_today' in data
            
            # Verify active alerts
            assert data['active_count'] == 2
            active_alerts = data['active_alerts']
            assert len(active_alerts) == 2
            
            # Verify alert structure
            alert1 = active_alerts[0]
            assert alert1['severity'] == 'error'
            assert alert1['category'] == 'circuit_breaker'
            assert alert1['title'] == 'Circuit Breaker Opened: pgvector'
            assert alert1['provider'] == 'pgvector'
            assert alert1['resolved'] is False
            
            # Verify recent alerts include both active and resolved
            recent_alerts = data['recent_alerts']
            assert len(recent_alerts) == 3  # All alerts in history
    
    def test_alerts_endpoint_empty(self, client):
        """Test alerts endpoint with no alerts."""
        monitor = MagicMock()
        monitor.active_alerts = {}
        monitor.alert_history = []
        
        with patch('memory_service.api.get_error_monitor', return_value=monitor):
            response = client.get("/monitoring/alerts")
            
            assert response.status_code == 200
            data = response.json()
            assert data['active_count'] == 0
            assert len(data['active_alerts']) == 0
            assert len(data['recent_alerts']) == 0
    
    def test_alerts_endpoint_error(self, client):
        """Test alerts endpoint error handling."""
        monitor = MagicMock()
        monitor.active_alerts = None  # Simulate error condition
        
        with patch('memory_service.api.get_error_monitor', return_value=monitor):
            response = client.get("/monitoring/alerts")
            
            assert response.status_code == 500
            data = response.json()
            assert 'error' in data


class TestMonitoringAlertResolutionEndpoint:
    """Test /monitoring/alerts/{alert_id}/resolve endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_monitor(self):
        """Mock error monitor with resolvable alert."""
        monitor = MagicMock()
        
        # Create test alert
        test_alert = Alert(
            id="test-alert-123",
            severity=AlertSeverity.ERROR,
            category=ErrorCategory.CIRCUIT_BREAKER,
            title="Test Alert",
            description="Test alert for resolution",
            timestamp=datetime.utcnow()
        )
        
        monitor.active_alerts = {"test-alert-123": test_alert}
        
        async def mock_resolve_alert(alert_id, resolution_note):
            if alert_id in monitor.active_alerts:
                del monitor.active_alerts[alert_id]
                return True
            return False
        
        monitor.resolve_alert = mock_resolve_alert
        return monitor
    
    def test_resolve_alert_success(self, client, mock_monitor):
        """Test successful alert resolution."""
        with patch('memory_service.api.get_error_monitor', return_value=mock_monitor):
            response = client.post(
                "/monitoring/alerts/test-alert-123/resolve",
                params={"resolution_note": "Issue resolved by restart"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data['success'] is True
            assert 'Alert test-alert-123 resolved successfully' in data['message']
            assert data['resolution_note'] == 'Issue resolved by restart'
            
            # Verify alert was removed from active alerts
            assert "test-alert-123" not in mock_monitor.active_alerts
    
    def test_resolve_alert_not_found(self, client, mock_monitor):
        """Test resolving non-existent alert."""
        with patch('memory_service.api.get_error_monitor', return_value=mock_monitor):
            response = client.post("/monitoring/alerts/nonexistent-alert/resolve")
            
            assert response.status_code == 404
            data = response.json()
            assert data['detail'] == 'Alert not found'
    
    def test_resolve_alert_no_note(self, client, mock_monitor):
        """Test resolving alert without resolution note."""
        with patch('memory_service.api.get_error_monitor', return_value=mock_monitor):
            response = client.post("/monitoring/alerts/test-alert-123/resolve")
            
            assert response.status_code == 200
            data = response.json()
            assert data['resolution_note'] is None
    
    def test_resolve_alert_error(self, client):
        """Test alert resolution error handling."""
        monitor = MagicMock()
        
        async def mock_resolve_alert(alert_id, resolution_note):
            raise Exception("Resolution failed")
        
        monitor.resolve_alert = mock_resolve_alert
        monitor.active_alerts = {"test-alert": MagicMock()}
        
        with patch('memory_service.api.get_error_monitor', return_value=monitor):
            response = client.post("/monitoring/alerts/test-alert/resolve")
            
            assert response.status_code == 500
            data = response.json()
            assert 'error' in data


class TestMonitoringCircuitBreakersEndpoint:
    """Test /monitoring/circuit-breakers endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_store(self):
        """Mock unified store with circuit breaker data."""
        store = MagicMock()
        
        # Mock providers with circuit breakers
        pgvector_provider = MagicMock()
        pgvector_cb = MagicMock()
        pgvector_cb.get_status.return_value = {
            'state': 'closed',
            'failure_count': 1,
            'total_requests': 1000,
            'total_failures': 15,
            'total_successes': 985,
            'success_rate': 0.985
        }
        pgvector_provider.get_circuit_breaker_status.return_value = {
            'provider': 'pgvector',
            'enabled': True,
            'state': 'closed',
            'failure_count': 1,
            'total_requests': 1000,
            'total_failures': 15,
            'total_successes': 985,
            'success_rate': 0.985
        }
        pgvector_provider.circuit_breaker = pgvector_cb
        
        chromadb_provider = MagicMock()
        chromadb_cb = MagicMock() 
        chromadb_provider.get_circuit_breaker_status.return_value = {
            'provider': 'chromadb',
            'enabled': True,
            'state': 'open',
            'failure_count': 5,
            'total_requests': 500,
            'total_failures': 45,
            'total_successes': 455,
            'success_rate': 0.91
        }
        chromadb_provider.circuit_breaker = chromadb_cb
        
        store.providers = {
            'pgvector': pgvector_provider,
            'chromadb': chromadb_provider
        }
        
        return store
    
    @pytest.fixture
    def mock_monitor(self):
        """Mock error monitor with circuit breaker events."""
        monitor = MagicMock()
        
        # Mock recent circuit breaker events
        monitor.circuit_breaker_events = [
            {
                'timestamp': datetime.utcnow() - timedelta(minutes=5),
                'provider': 'chromadb',
                'old_state': 'closed',
                'new_state': 'open',
                'reason': 'Failure threshold exceeded'
            },
            {
                'timestamp': datetime.utcnow() - timedelta(minutes=30),
                'provider': 'pgvector',
                'old_state': 'open',
                'new_state': 'closed',
                'reason': 'Recovery successful'
            }
        ]
        
        return monitor
    
    def test_circuit_breakers_endpoint_success(self, client, mock_store, mock_monitor):
        """Test successful circuit breakers endpoint."""
        with patch('memory_service.api.get_error_monitor', return_value=mock_monitor), \
             patch('memory_service.api.get_store', return_value=mock_store):
            
            response = client.get("/monitoring/circuit-breakers")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert 'circuit_breakers' in data
            assert 'recent_events' in data
            assert 'overall_status' in data
            
            # Verify circuit breaker data
            cb_data = data['circuit_breakers']
            assert 'pgvector' in cb_data
            assert 'chromadb' in cb_data
            
            pgvector_cb = cb_data['pgvector']
            assert pgvector_cb['provider'] == 'pgvector'
            assert pgvector_cb['state'] == 'closed'
            assert pgvector_cb['success_rate'] == 0.985
            
            chromadb_cb = cb_data['chromadb']
            assert chromadb_cb['provider'] == 'chromadb'
            assert chromadb_cb['state'] == 'open'
            
            # Verify overall status (degraded due to open circuit)
            assert data['overall_status'] == 'degraded'
            
            # Verify recent events
            events = data['recent_events']
            assert len(events) == 2
            
            recent_event = events[0]
            assert recent_event['provider'] == 'chromadb'
            assert recent_event['old_state'] == 'closed'
            assert recent_event['new_state'] == 'open'
    
    def test_circuit_breakers_endpoint_all_healthy(self, client, mock_monitor):
        """Test circuit breakers endpoint with all circuits closed."""
        # Mock store with all healthy providers
        store = MagicMock()
        
        healthy_provider = MagicMock()
        healthy_provider.get_circuit_breaker_status.return_value = {
            'provider': 'pgvector',
            'state': 'closed'
        }
        healthy_provider.circuit_breaker = MagicMock()
        
        store.providers = {'pgvector': healthy_provider}
        
        with patch('memory_service.api.get_error_monitor', return_value=mock_monitor), \
             patch('memory_service.api.get_store', return_value=store):
            
            response = client.get("/monitoring/circuit-breakers")
            
            assert response.status_code == 200
            data = response.json()
            assert data['overall_status'] == 'healthy'  # All circuits closed
    
    def test_circuit_breakers_endpoint_error(self, client):
        """Test circuit breakers endpoint error handling."""
        with patch('memory_service.api.get_error_monitor', side_effect=Exception("Monitor failure")):
            response = client.get("/monitoring/circuit-breakers")
            
            assert response.status_code == 500
            data = response.json()
            assert 'error' in data


class TestMonitoringEndpointsIntegration:
    """Integration tests for monitoring endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_monitoring_endpoints_consistency(self, client):
        """Test that monitoring endpoints return consistent data."""
        # This test would verify that data across different endpoints is consistent
        # For example, error counts in /monitoring/health should match /monitoring/errors
        
        # Mock consistent monitoring data
        monitor = MagicMock()
        
        # Health data
        health = HealthMetrics(
            timestamp=datetime.utcnow(),
            total_requests=1000,
            total_errors=50,
            error_rate=0.05,
            avg_response_time=150.0,
            circuit_breaker_states={'pgvector': 'closed'},
            provider_health={},
            connection_pool_stats={},
            memory_usage={},
            active_alerts=1
        )
        
        # Error summary data that should match health data
        error_summary = {
            'total_errors': 50,  # Should match health.total_errors
            'by_category': {'provider_failure': 30, 'timeout': 20},
            'by_provider': {'pgvector': 50},
            'by_component': {'unified_store': 50},
            'time_period_hours': 24,
            'active_alerts': 1  # Should match health.active_alerts
        }
        
        async def mock_get_health_status():
            return health
        
        async def mock_get_error_summary(hours):
            return error_summary
        
        monitor.get_health_status = mock_get_health_status
        monitor.get_error_summary = mock_get_error_summary
        
        with patch('memory_service.api.get_error_monitor', return_value=monitor):
            # Get health data
            health_response = client.get("/monitoring/health")
            assert health_response.status_code == 200
            health_data = health_response.json()
            
            # Get error data
            errors_response = client.get("/monitoring/errors")
            assert errors_response.status_code == 200
            errors_data = errors_response.json()
            
            # Verify consistency
            assert health_data['total_errors'] == errors_data['total_errors']
            assert health_data['active_alerts'] == errors_data['active_alerts']
    
    def test_monitoring_endpoints_performance(self, client):
        """Test that monitoring endpoints respond quickly."""
        monitor = MagicMock()
        
        # Mock quick responses
        async def mock_get_health_status():
            return HealthMetrics(
                timestamp=datetime.utcnow(),
                total_requests=100,
                total_errors=5,
                error_rate=0.05,
                avg_response_time=100.0,
                circuit_breaker_states={},
                provider_health={},
                connection_pool_stats={},
                memory_usage={},
                active_alerts=0
            )
        
        monitor.get_health_status = mock_get_health_status
        
        with patch('memory_service.api.get_error_monitor', return_value=monitor):
            start_time = time.time()
            response = client.get("/monitoring/health")
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            assert response.status_code == 200
            assert response_time < 100  # Should respond in under 100ms


if __name__ == "__main__":
    # Run tests with detailed output
    pytest.main([__file__, "-v", "--tb=short"])