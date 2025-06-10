"""
Usage Tracking Middleware

Real-time usage tracking and analytics for the Core Nexus Memory Service.
Collects performance metrics, user patterns, and system intelligence data.
"""

import asyncio
import json
import logging
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


@dataclass
class UsageEvent:
    """Individual usage event data."""
    timestamp: datetime
    event_type: str  # 'api_request', 'memory_store', 'memory_query', 'health_check'
    endpoint: str
    method: str
    user_id: str | None
    response_time_ms: float
    status_code: int
    request_size_bytes: int
    response_size_bytes: int
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return asdict(self)


@dataclass
class PerformanceMetrics:
    """Aggregated performance metrics."""
    total_requests: int
    avg_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    error_rate: float
    requests_per_minute: float
    memory_operations_per_minute: float
    unique_users_last_hour: int


class UsageCollector:
    """
    Collects and aggregates usage data for analytics.

    Provides real-time insights into system performance and user behavior.
    """

    def __init__(self, max_events: int = 10000, unified_store=None):
        self.max_events = max_events
        self.events: list[UsageEvent] = []
        self.unified_store = unified_store

        # Performance tracking
        self.response_times: list[float] = []
        self.request_counts_by_minute: dict[str, int] = {}
        self.error_counts: dict[str, int] = {}
        self.user_activity: dict[str, datetime] = {}

        # Memory-specific metrics
        self.memory_operations: dict[str, int] = {
            'stores': 0,
            'queries': 0,
            'health_checks': 0
        }

        # System learning data
        self.learning_events: list[dict[str, Any]] = []

    async def record_event(self, event: UsageEvent):
        """Record a usage event and update metrics."""
        try:
            # Add to events list
            self.events.append(event)

            # Maintain max events limit
            if len(self.events) > self.max_events:
                self.events = self.events[-self.max_events:]

            # Update performance metrics
            self._update_performance_metrics(event)

            # Update memory operation counts
            self._update_memory_metrics(event)

            # Track user activity
            if event.user_id:
                self.user_activity[event.user_id] = event.timestamp

            # Store learning data for evolution
            if event.event_type in ['memory_store', 'memory_query']:
                await self._record_learning_event(event)

        except Exception as e:
            logger.error(f"Failed to record usage event: {e}")

    def _update_performance_metrics(self, event: UsageEvent):
        """Update aggregated performance metrics."""
        # Response time tracking
        self.response_times.append(event.response_time_ms)
        if len(self.response_times) > 1000:  # Keep last 1000 for percentiles
            self.response_times = self.response_times[-1000:]

        # Request counting by minute
        minute_key = event.timestamp.strftime('%Y-%m-%d %H:%M')
        self.request_counts_by_minute[minute_key] = self.request_counts_by_minute.get(minute_key, 0) + 1

        # Error tracking
        if event.status_code >= 400:
            error_key = f"{event.status_code}_{event.endpoint}"
            self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1

    def _update_memory_metrics(self, event: UsageEvent):
        """Update memory-specific operation metrics."""
        if 'memory' in event.endpoint.lower():
            if event.method == 'POST' and 'memories' in event.endpoint:
                self.memory_operations['stores'] += 1
            elif 'query' in event.endpoint.lower():
                self.memory_operations['queries'] += 1
        elif 'health' in event.endpoint.lower():
            self.memory_operations['health_checks'] += 1

    async def _record_learning_event(self, event: UsageEvent):
        """Record events that contribute to system learning."""
        try:
            learning_data = {
                'timestamp': event.timestamp.isoformat(),
                'operation_type': event.event_type,
                'performance': event.response_time_ms,
                'success': event.status_code < 400,
                'user_context': event.user_id,
                'metadata': event.metadata
            }

            self.learning_events.append(learning_data)

            # Keep last 500 learning events
            if len(self.learning_events) > 500:
                self.learning_events = self.learning_events[-500:]

            # Store in unified store for long-term learning
            if self.unified_store and event.status_code < 400:
                await self._store_system_learning_memory(learning_data)

        except Exception as e:
            logger.warning(f"Failed to record learning event: {e}")

    async def _store_system_learning_memory(self, learning_data: dict[str, Any]):
        """Store system learning data as memory for self-evolution."""
        try:
            from .models import MemoryRequest

            # Create system learning memory
            content = f"SYSTEM_LEARNING: {learning_data['operation_type']} operation "
            content += f"completed in {learning_data['performance']:.1f}ms "
            content += f"({'success' if learning_data['success'] else 'failure'})"

            memory_request = MemoryRequest(
                content=content,
                metadata={
                    **learning_data,
                    'type': 'system_learning',
                    'category': 'performance',
                    'importance_score': 0.3,  # Lower importance for system data
                    'user_id': 'system',
                    'conversation_id': 'system_learning'
                }
            )

            # Store without blocking the API response
            asyncio.create_task(self.unified_store.store_memory(memory_request))

        except Exception as e:
            logger.warning(f"Failed to store system learning memory: {e}")

    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        try:
            if not self.response_times:
                return PerformanceMetrics(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0)

            # Calculate percentiles
            sorted_times = sorted(self.response_times)
            p95_idx = int(len(sorted_times) * 0.95)
            p99_idx = int(len(sorted_times) * 0.99)

            avg_response_time = sum(self.response_times) / len(self.response_times)
            p95_response_time = sorted_times[p95_idx] if p95_idx < len(sorted_times) else 0
            p99_response_time = sorted_times[p99_idx] if p99_idx < len(sorted_times) else 0

            # Calculate rates
            total_requests = len(self.events)
            total_errors = sum(self.error_counts.values())
            error_rate = total_errors / total_requests if total_requests > 0 else 0

            # Recent activity (last hour)
            now = datetime.utcnow()
            recent_events = [e for e in self.events if (now - e.timestamp).seconds < 3600]
            requests_per_minute = len(recent_events) / 60 if recent_events else 0

            memory_ops_recent = sum(
                1 for e in recent_events
                if e.event_type in ['memory_store', 'memory_query']
            )
            memory_ops_per_minute = memory_ops_recent / 60 if recent_events else 0

            # Unique users last hour
            unique_users = len({
                e.user_id for e in recent_events
                if e.user_id and e.user_id != 'system'
            })

            return PerformanceMetrics(
                total_requests=total_requests,
                avg_response_time_ms=avg_response_time,
                p95_response_time_ms=p95_response_time,
                p99_response_time_ms=p99_response_time,
                error_rate=error_rate,
                requests_per_minute=requests_per_minute,
                memory_operations_per_minute=memory_ops_per_minute,
                unique_users_last_hour=unique_users
            )

        except Exception as e:
            logger.error(f"Failed to calculate performance metrics: {e}")
            return PerformanceMetrics(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0)

    def get_usage_patterns(self) -> dict[str, Any]:
        """Analyze usage patterns for insights."""
        try:
            patterns = {
                'peak_hours': self._analyze_peak_hours(),
                'popular_endpoints': self._analyze_popular_endpoints(),
                'user_behavior': self._analyze_user_behavior(),
                'error_patterns': self._analyze_error_patterns(),
                'performance_trends': self._analyze_performance_trends()
            }

            return patterns

        except Exception as e:
            logger.error(f"Failed to analyze usage patterns: {e}")
            return {}

    def _analyze_peak_hours(self) -> dict[str, int]:
        """Analyze peak usage hours."""
        hour_counts = {}
        for event in self.events:
            hour = event.timestamp.hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1

        return dict(sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:5])

    def _analyze_popular_endpoints(self) -> dict[str, int]:
        """Analyze most popular endpoints."""
        endpoint_counts = {}
        for event in self.events:
            endpoint_counts[event.endpoint] = endpoint_counts.get(event.endpoint, 0) + 1

        return dict(sorted(endpoint_counts.items(), key=lambda x: x[1], reverse=True)[:10])

    def _analyze_user_behavior(self) -> dict[str, Any]:
        """Analyze user behavior patterns."""
        user_stats = {}
        for event in self.events:
            if event.user_id and event.user_id != 'system':
                if event.user_id not in user_stats:
                    user_stats[event.user_id] = {
                        'total_requests': 0,
                        'memory_operations': 0,
                        'avg_response_time': 0,
                        'last_activity': event.timestamp
                    }

                stats = user_stats[event.user_id]
                stats['total_requests'] += 1
                if event.event_type in ['memory_store', 'memory_query']:
                    stats['memory_operations'] += 1
                stats['avg_response_time'] = (
                    stats['avg_response_time'] * (stats['total_requests'] - 1) +
                    event.response_time_ms
                ) / stats['total_requests']

                if event.timestamp > stats['last_activity']:
                    stats['last_activity'] = event.timestamp

        return {
            'total_users': len(user_stats),
            'active_users_last_hour': len([
                u for u, s in user_stats.items()
                if (datetime.utcnow() - s['last_activity']).seconds < 3600
            ]),
            'top_users': dict(sorted(
                user_stats.items(),
                key=lambda x: x[1]['total_requests'],
                reverse=True
            )[:5])
        }

    def _analyze_error_patterns(self) -> dict[str, Any]:
        """Analyze error patterns for debugging."""
        return {
            'total_errors': sum(self.error_counts.values()),
            'error_breakdown': dict(sorted(
                self.error_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]),
            'error_rate_by_hour': {}  # TODO: Implement hourly error rates
        }

    def _analyze_performance_trends(self) -> dict[str, Any]:
        """Analyze performance trends over time."""
        if len(self.response_times) < 10:
            return {'status': 'insufficient_data'}

        # Simple trend analysis (last 100 vs previous 100)
        recent_times = self.response_times[-100:]
        previous_times = self.response_times[-200:-100] if len(self.response_times) >= 200 else []

        recent_avg = sum(recent_times) / len(recent_times)
        previous_avg = sum(previous_times) / len(previous_times) if previous_times else recent_avg

        trend = 'improving' if recent_avg < previous_avg else 'degrading' if recent_avg > previous_avg else 'stable'

        return {
            'trend': trend,
            'recent_avg_ms': recent_avg,
            'previous_avg_ms': previous_avg,
            'improvement_pct': ((previous_avg - recent_avg) / previous_avg * 100) if previous_avg > 0 else 0
        }

    def export_events(self, format: str = 'json', limit: int | None = None) -> str:
        """Export usage events for analysis."""
        try:
            events_to_export = self.events[-limit:] if limit else self.events

            if format.lower() == 'json':
                return json.dumps([e.to_dict() for e in events_to_export], default=str, indent=2)
            elif format.lower() == 'csv':
                # TODO: Implement CSV export
                return "CSV export not yet implemented"
            else:
                raise ValueError(f"Unsupported export format: {format}")

        except Exception as e:
            logger.error(f"Failed to export events: {e}")
            return json.dumps({'error': str(e)})


class UsageTrackingMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for automatic usage tracking.

    Captures all API requests and responses for analytics.
    """

    def __init__(self, app, usage_collector: UsageCollector):
        super().__init__(app)
        self.usage_collector = usage_collector

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and track usage."""
        start_time = time.time()

        # Extract user ID from headers or request
        user_id = self._extract_user_id(request)

        # Get request size
        request_size = len(await self._get_body_size(request))

        try:
            # Process request
            response = await call_next(request)

            # Calculate response time
            response_time_ms = (time.time() - start_time) * 1000

            # Get response size
            response_size = self._get_response_size(response)

            # Determine event type
            event_type = self._determine_event_type(request.url.path, request.method)

            # Create usage event
            event = UsageEvent(
                timestamp=datetime.utcnow(),
                event_type=event_type,
                endpoint=request.url.path,
                method=request.method,
                user_id=user_id,
                response_time_ms=response_time_ms,
                status_code=response.status_code,
                request_size_bytes=request_size,
                response_size_bytes=response_size,
                metadata={
                    'query_params': dict(request.query_params),
                    'user_agent': request.headers.get('user-agent', ''),
                    'ip_address': self._get_client_ip(request)
                }
            )

            # Record event (non-blocking)
            asyncio.create_task(self.usage_collector.record_event(event))

            return response

        except Exception as e:
            # Record error event
            response_time_ms = (time.time() - start_time) * 1000

            error_event = UsageEvent(
                timestamp=datetime.utcnow(),
                event_type='api_error',
                endpoint=request.url.path,
                method=request.method,
                user_id=user_id,
                response_time_ms=response_time_ms,
                status_code=500,
                request_size_bytes=request_size,
                response_size_bytes=0,
                metadata={
                    'error': str(e),
                    'query_params': dict(request.query_params)
                }
            )

            asyncio.create_task(self.usage_collector.record_event(error_event))
            raise

    def _extract_user_id(self, request: Request) -> str | None:
        """Extract user ID from request headers or auth."""
        # Check various common headers
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            user_id = request.headers.get('Authorization', '').split('user:')[-1] if 'user:' in request.headers.get('Authorization', '') else None

        return user_id

    async def _get_body_size(self, request: Request) -> int:
        """Estimate request body size."""
        try:
            content_length = request.headers.get('content-length')
            return int(content_length) if content_length else 0
        except Exception:
            return 0

    def _get_response_size(self, response: Response) -> int:
        """Estimate response size."""
        try:
            content_length = response.headers.get('content-length')
            return int(content_length) if content_length else 0
        except Exception:
            return 0

    def _determine_event_type(self, path: str, method: str) -> str:
        """Determine the type of event based on path and method."""
        if 'health' in path.lower():
            return 'health_check'
        elif 'memories' in path.lower():
            if method == 'POST':
                return 'memory_store'
            elif 'query' in path.lower():
                return 'memory_query'
            else:
                return 'memory_operation'
        elif 'dashboard' in path.lower() or 'metrics' in path.lower():
            return 'analytics_request'
        else:
            return 'api_request'

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        # Check various headers for real IP
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()

        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip

        return request.client.host if request.client else 'unknown'
