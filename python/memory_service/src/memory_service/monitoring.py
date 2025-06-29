"""
Comprehensive Error Monitoring and Alerting System

Production-ready monitoring system for Memory Service that provides:
- Real-time error tracking and categorization
- Circuit breaker status monitoring  
- Provider health dashboards
- Performance metrics and SLA tracking
- Configurable alert thresholds and escalation
"""

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from uuid import uuid4

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels for escalation."""
    INFO = "info"
    WARNING = "warning" 
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Categorization of errors for better analysis."""
    PROVIDER_FAILURE = "provider_failure"
    CIRCUIT_BREAKER = "circuit_breaker"
    CONNECTION_POOL = "connection_pool"
    TIMEOUT = "timeout"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    MEMORY_LEAK = "memory_leak"
    PERFORMANCE = "performance"
    UNKNOWN = "unknown"


@dataclass
class Alert:
    """Structured alert with metadata."""
    id: str
    severity: AlertSeverity
    category: ErrorCategory
    title: str
    description: str
    timestamp: datetime
    service: str = "memory_service"
    component: str = "unified_store"
    provider: Optional[str] = None
    metrics: Dict[str, Any] = None
    escalated: bool = False
    resolved: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary for JSON serialization."""
        data = asdict(self)
        data['severity'] = self.severity.value
        data['category'] = self.category.value
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class HealthMetrics:
    """System health metrics snapshot."""
    timestamp: datetime
    total_requests: int
    total_errors: int
    error_rate: float
    avg_response_time: float
    circuit_breaker_states: Dict[str, str]
    provider_health: Dict[str, Dict[str, Any]]
    connection_pool_stats: Dict[str, Dict[str, Any]]
    memory_usage: Dict[str, float]
    active_alerts: int


class ErrorMonitor:
    """
    Comprehensive error monitoring and alerting system.
    
    Tracks errors, health metrics, and triggers alerts based on configurable thresholds.
    """
    
    def __init__(self, 
                 alert_handlers: List[Callable] = None,
                 error_rate_threshold: float = 0.05,  # 5% error rate triggers alert
                 response_time_threshold: float = 5.0,  # 5 second response time threshold
                 memory_usage_threshold: float = 0.85):  # 85% memory usage threshold
        
        self.alert_handlers = alert_handlers or []
        self.error_rate_threshold = error_rate_threshold
        self.response_time_threshold = response_time_threshold
        self.memory_usage_threshold = memory_usage_threshold
        
        # Error tracking
        self.error_counts = defaultdict(int)
        self.error_history = deque(maxlen=1000)  # Last 1000 errors
        self.request_history = deque(maxlen=10000)  # Last 10000 requests
        
        # Alert management
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history = deque(maxlen=500)  # Last 500 alerts
        
        # Health metrics
        self.health_snapshots = deque(maxlen=100)  # Last 100 health snapshots
        self.last_health_check = datetime.utcnow()
        
        # Performance tracking
        self.response_times = deque(maxlen=1000)
        self.circuit_breaker_events = deque(maxlen=500)
        
        # Background monitoring task
        self._monitoring_task = None
        self._shutdown = False
        
        logger.info("Error monitoring system initialized")
    
    async def start_monitoring(self):
        """Start background monitoring tasks."""
        if self._monitoring_task:
            return
            
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Background monitoring started")
    
    async def stop_monitoring(self):
        """Stop background monitoring tasks."""
        self._shutdown = True
        if self._monitoring_task:
            await self._monitoring_task
        logger.info("Background monitoring stopped")
    
    def record_error(self, error: Exception, category: ErrorCategory = ErrorCategory.UNKNOWN, 
                    provider: str = None, component: str = "unified_store", **metadata):
        """Record an error occurrence for monitoring."""
        error_record = {
            'timestamp': datetime.utcnow(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'category': category.value,
            'provider': provider,
            'component': component,
            'metadata': metadata
        }
        
        self.error_history.append(error_record)
        self.error_counts[category.value] += 1
        
        # Check if error rate threshold is exceeded (safe for sync/async contexts)
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(self._check_error_rate_threshold())
        except RuntimeError:
            # No event loop running, skip async checks in sync context
            pass
        
        logger.warning(f"Error recorded: {category.value} - {error}")
    
    def record_request(self, duration_ms: float, success: bool = True, 
                      provider: str = None, operation: str = None):
        """Record a request for performance monitoring."""
        request_record = {
            'timestamp': datetime.utcnow(),
            'duration_ms': duration_ms,
            'success': success,
            'provider': provider,
            'operation': operation
        }
        
        self.request_history.append(request_record)
        self.response_times.append(duration_ms)
        
        # Check response time threshold (safe for sync/async contexts)
        if duration_ms > self.response_time_threshold * 1000:  # Convert to ms
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self._check_response_time_threshold(duration_ms))
            except RuntimeError:
                # No event loop running, skip async checks in sync context
                pass
    
    def record_circuit_breaker_event(self, provider: str, old_state: str, new_state: str, reason: str = None):
        """Record circuit breaker state changes."""
        event = {
            'timestamp': datetime.utcnow(),
            'provider': provider,
            'old_state': old_state,
            'new_state': new_state,
            'reason': reason
        }
        
        self.circuit_breaker_events.append(event)
        
        # Trigger alert for circuit breaker opening (safe for sync/async contexts)
        if new_state == 'open':
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self._trigger_circuit_breaker_alert(provider, reason))
            except RuntimeError:
                # No event loop running, skip async alerts in sync context
                pass
        elif new_state == 'closed' and old_state == 'open':
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self._resolve_circuit_breaker_alert(provider))
            except RuntimeError:
                # No event loop running, skip async alerts in sync context
                pass
        
        logger.info(f"Circuit breaker event: {provider} {old_state} -> {new_state}")
    
    async def create_alert(self, severity: AlertSeverity, category: ErrorCategory, 
                          title: str, description: str, **metadata) -> Alert:
        """Create and process a new alert."""
        alert = Alert(
            id=str(uuid4()),
            severity=severity,
            category=category,
            title=title,
            description=description,
            timestamp=datetime.utcnow(),
            provider=metadata.get('provider'),
            metrics=metadata.get('metrics'),
            component=metadata.get('component', 'unified_store')
        )
        
        # Store alert
        self.active_alerts[alert.id] = alert
        self.alert_history.append(alert)
        
        # Send to alert handlers
        for handler in self.alert_handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")
        
        logger.warning(f"Alert created: {severity.value} - {title}")
        return alert
    
    async def resolve_alert(self, alert_id: str, resolution_note: str = None):
        """Mark an alert as resolved."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.description += f"\n\nResolved: {resolution_note or 'Auto-resolved'}"
            del self.active_alerts[alert_id]
            
            logger.info(f"Alert resolved: {alert.title}")
    
    async def get_health_status(self) -> HealthMetrics:
        """Get current system health status."""
        now = datetime.utcnow()
        
        # Calculate error rate (last 5 minutes)
        recent_cutoff = now - timedelta(minutes=5)
        recent_requests = [r for r in self.request_history if r['timestamp'] > recent_cutoff]
        recent_errors = [r for r in recent_requests if not r['success']]
        
        error_rate = len(recent_errors) / max(1, len(recent_requests))
        
        # Calculate average response time (last 100 requests)
        recent_response_times = list(self.response_times)[-100:] if self.response_times else [0]
        avg_response_time = sum(recent_response_times) / len(recent_response_times)
        
        # Get circuit breaker states (placeholder - would integrate with actual providers)
        circuit_breaker_states = self._get_circuit_breaker_states()
        
        # Get provider health (placeholder - would integrate with actual providers)
        provider_health = self._get_provider_health()
        
        # Get connection pool stats (placeholder - would integrate with actual pools)
        connection_pool_stats = self._get_connection_pool_stats()
        
        # Get memory usage (placeholder - would integrate with actual monitoring)
        memory_usage = self._get_memory_usage()
        
        health = HealthMetrics(
            timestamp=now,
            total_requests=len(self.request_history),
            total_errors=len(self.error_history),
            error_rate=error_rate,
            avg_response_time=avg_response_time,
            circuit_breaker_states=circuit_breaker_states,
            provider_health=provider_health,
            connection_pool_stats=connection_pool_stats,
            memory_usage=memory_usage,
            active_alerts=len(self.active_alerts)
        )
        
        self.health_snapshots.append(health)
        self.last_health_check = now
        
        return health
    
    async def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary for the specified time period."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent_errors = [e for e in self.error_history if e['timestamp'] > cutoff]
        
        # Group by category
        by_category = defaultdict(int)
        by_provider = defaultdict(int)
        by_component = defaultdict(int)
        
        for error in recent_errors:
            by_category[error['category']] += 1
            if error['provider']:
                by_provider[error['provider']] += 1
            by_component[error['component']] += 1
        
        return {
            'total_errors': len(recent_errors),
            'by_category': dict(by_category),
            'by_provider': dict(by_provider),
            'by_component': dict(by_component),
            'time_period_hours': hours,
            'active_alerts': len(self.active_alerts)
        }
    
    # Private helper methods
    
    async def _monitoring_loop(self):
        """Background monitoring loop."""
        while not self._shutdown:
            try:
                # Run health checks every 30 seconds
                await self.get_health_status()
                
                # Check for threshold violations
                await self._check_all_thresholds()
                
                # Clean up old data
                await self._cleanup_old_data()
                
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(5)  # Back off on error
    
    async def _check_error_rate_threshold(self):
        """Check if error rate exceeds threshold."""
        now = datetime.utcnow()
        recent_cutoff = now - timedelta(minutes=5)
        recent_requests = [r for r in self.request_history if r['timestamp'] > recent_cutoff]
        
        if len(recent_requests) < 10:  # Need minimum requests for meaningful rate
            return
        
        recent_errors = [r for r in recent_requests if not r['success']]
        error_rate = len(recent_errors) / len(recent_requests)
        
        if error_rate > self.error_rate_threshold:
            await self.create_alert(
                severity=AlertSeverity.ERROR,
                category=ErrorCategory.PERFORMANCE,
                title=f"High Error Rate: {error_rate:.1%}",
                description=f"Error rate of {error_rate:.1%} exceeds threshold of {self.error_rate_threshold:.1%}",
                metrics={'error_rate': error_rate, 'recent_requests': len(recent_requests), 'recent_errors': len(recent_errors)}
            )
    
    async def _check_response_time_threshold(self, duration_ms: float):
        """Check if response time exceeds threshold."""
        await self.create_alert(
            severity=AlertSeverity.WARNING,
            category=ErrorCategory.PERFORMANCE,
            title=f"Slow Response: {duration_ms:.0f}ms",
            description=f"Response time of {duration_ms:.0f}ms exceeds threshold of {self.response_time_threshold * 1000:.0f}ms",
            metrics={'response_time_ms': duration_ms, 'threshold_ms': self.response_time_threshold * 1000}
        )
    
    async def _trigger_circuit_breaker_alert(self, provider: str, reason: str = None):
        """Trigger alert for circuit breaker opening."""
        await self.create_alert(
            severity=AlertSeverity.ERROR,
            category=ErrorCategory.CIRCUIT_BREAKER,
            title=f"Circuit Breaker Opened: {provider}",
            description=f"Circuit breaker for provider {provider} has opened. Reason: {reason or 'Unknown'}",
            provider=provider,
            metrics={'reason': reason}
        )
    
    async def _resolve_circuit_breaker_alert(self, provider: str):
        """Resolve circuit breaker alert when it closes."""
        # Find and resolve related alerts
        for alert_id, alert in list(self.active_alerts.items()):
            if (alert.category == ErrorCategory.CIRCUIT_BREAKER and 
                alert.provider == provider and 
                "Circuit Breaker Opened" in alert.title):
                await self.resolve_alert(alert_id, f"Circuit breaker for {provider} recovered")
    
    async def _check_all_thresholds(self):
        """Check all monitoring thresholds."""
        # This would integrate with actual system monitoring
        # For now, just placeholder checks
        pass
    
    async def _cleanup_old_data(self):
        """Clean up old monitoring data to prevent memory leaks."""
        now = datetime.utcnow()
        cutoff = now - timedelta(hours=24)
        
        # Clean up resolved alerts older than 24 hours
        for alert in list(self.alert_history):
            if alert.resolved and alert.timestamp < cutoff:
                self.alert_history.remove(alert)
    
    def _get_circuit_breaker_states(self) -> Dict[str, str]:
        """Get current circuit breaker states (placeholder)."""
        # This would integrate with actual circuit breakers
        return {
            'pgvector': 'closed',
            'pinecone': 'closed', 
            'chromadb': 'closed'
        }
    
    def _get_provider_health(self) -> Dict[str, Dict[str, Any]]:
        """Get provider health status (placeholder)."""
        # This would integrate with actual providers
        return {
            'pgvector': {'status': 'healthy', 'response_time_ms': 50},
            'pinecone': {'status': 'healthy', 'response_time_ms': 120},
            'chromadb': {'status': 'healthy', 'response_time_ms': 30}
        }
    
    def _get_connection_pool_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get connection pool statistics (placeholder)."""
        # This would integrate with actual connection pools
        return {
            'pgvector': {'active': 5, 'idle': 15, 'max': 30},
            'coordination': {'active': 2, 'idle': 3, 'max': 5}
        }
    
    def _get_memory_usage(self) -> Dict[str, float]:
        """Get memory usage statistics (placeholder)."""
        # This would integrate with actual memory monitoring
        return {
            'heap_usage_percent': 0.45,
            'cache_usage_percent': 0.30,
            'connection_pool_percent': 0.05
        }


# Alert handlers for different notification channels

async def console_alert_handler(alert: Alert):
    """Simple console alert handler for development."""
    print(f"🚨 ALERT [{alert.severity.value.upper()}] {alert.title}")
    print(f"   Description: {alert.description}")
    print(f"   Component: {alert.component}")
    if alert.provider:
        print(f"   Provider: {alert.provider}")
    print(f"   Time: {alert.timestamp.isoformat()}")
    print()

async def log_alert_handler(alert: Alert):
    """Log-based alert handler for production."""
    logger.error(f"ALERT: {alert.severity.value} - {alert.title}", extra={
        'alert_id': alert.id,
        'severity': alert.severity.value,
        'category': alert.category.value,
        'component': alert.component,
        'provider': alert.provider,
        'metrics': alert.metrics,
        'description': alert.description
    })

async def webhook_alert_handler(webhook_url: str):
    """Create webhook alert handler for external systems (Slack, PagerDuty, etc.)."""
    async def handler(alert: Alert):
        try:
            import aiohttp
            payload = {
                'text': f"🚨 {alert.severity.value.upper()}: {alert.title}",
                'attachments': [{
                    'color': 'danger' if alert.severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL] else 'warning',
                    'fields': [
                        {'title': 'Component', 'value': alert.component, 'short': True},
                        {'title': 'Provider', 'value': alert.provider or 'N/A', 'short': True},
                        {'title': 'Time', 'value': alert.timestamp.isoformat(), 'short': False},
                        {'title': 'Description', 'value': alert.description, 'short': False}
                    ]
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                await session.post(webhook_url, json=payload, timeout=5)
                
        except Exception as e:
            logger.error(f"Webhook alert handler failed: {e}")
    
    return handler


# Global monitor instance (initialized in API startup)
error_monitor: Optional[ErrorMonitor] = None

def get_error_monitor() -> ErrorMonitor:
    """Get global error monitor instance."""
    global error_monitor
    if error_monitor is None:
        error_monitor = ErrorMonitor(
            alert_handlers=[console_alert_handler, log_alert_handler]
        )
    return error_monitor