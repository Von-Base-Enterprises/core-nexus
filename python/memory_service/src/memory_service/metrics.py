"""
Prometheus metrics for Core Nexus Memory Service
"""

import logging
import time
from functools import wraps
from typing import Any

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
)

logger = logging.getLogger(__name__)

# Core API metrics
REQUEST_COUNT = Counter(
    'core_nexus_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_LATENCY = Histogram(
    'core_nexus_request_latency_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint']
)

# Memory service specific metrics
MEMORY_OPERATIONS = Counter(
    'core_nexus_memory_operations_total',
    'Total memory operations',
    ['operation', 'provider', 'status']
)

MEMORY_QUERY_LATENCY = Histogram(
    'core_nexus_memory_query_seconds',
    'Memory query latency in seconds',
    ['provider', 'query_type']
)

MEMORY_COUNT = Gauge(
    'core_nexus_memories_stored_total',
    'Total number of memories stored'
)

PROVIDER_HEALTH = Gauge(
    'core_nexus_provider_health',
    'Provider health status (1=healthy, 0=unhealthy)',
    ['provider_name']
)

# Vector operations
VECTOR_SIMILARITY_SCORES = Histogram(
    'core_nexus_similarity_scores',
    'Distribution of similarity scores',
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0]
)

EMBEDDING_GENERATION_TIME = Histogram(
    'core_nexus_embedding_generation_seconds',
    'Time to generate embeddings',
    ['provider']
)

# ADM scoring metrics
ADM_SCORES = Histogram(
    'core_nexus_adm_scores',
    'Distribution of ADM importance scores',
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

# Database connection pool metrics
DB_POOL_SIZE = Gauge(
    'core_nexus_db_pool_size',
    'Database connection pool size'
)

DB_POOL_USED = Gauge(
    'core_nexus_db_pool_used',
    'Database connections currently in use'
)

DB_QUERY_TIME = Histogram(
    'core_nexus_db_query_seconds',
    'Database query execution time',
    ['query_type']
)

# Service info
SERVICE_INFO = Info(
    'core_nexus_service_info',
    'Service version and configuration information'
)

# Uptime tracking
SERVICE_START_TIME = Gauge(
    'core_nexus_service_start_time_seconds',
    'Unix timestamp when the service started'
)

def record_request(method: str, endpoint: str, status_code: int):
    """Record HTTP request metrics"""
    REQUEST_COUNT.labels(
        method=method,
        endpoint=endpoint,
        status_code=status_code
    ).inc()

def time_request(method: str, endpoint: str):
    """Decorator to time HTTP requests"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                REQUEST_LATENCY.labels(
                    method=method,
                    endpoint=endpoint
                ).observe(time.time() - start_time)
        return wrapper
    return decorator

def record_memory_operation(operation: str, provider: str, status: str):
    """Record memory operation metrics"""
    MEMORY_OPERATIONS.labels(
        operation=operation,
        provider=provider,
        status=status
    ).inc()

def time_memory_query(provider: str, query_type: str):
    """Decorator to time memory queries"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                MEMORY_QUERY_LATENCY.labels(
                    provider=provider,
                    query_type=query_type
                ).observe(time.time() - start_time)
        return wrapper
    return decorator

def update_memory_count(count: int):
    """Update total memory count"""
    MEMORY_COUNT.set(count)

def update_provider_health(provider_name: str, is_healthy: bool):
    """Update provider health status"""
    PROVIDER_HEALTH.labels(provider_name=provider_name).set(1 if is_healthy else 0)

def record_similarity_score(score: float):
    """Record similarity score for analysis"""
    VECTOR_SIMILARITY_SCORES.observe(score)

def record_adm_score(score: float):
    """Record ADM importance score"""
    ADM_SCORES.observe(score)

def time_embedding_generation(provider: str):
    """Decorator to time embedding generation"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                EMBEDDING_GENERATION_TIME.labels(
                    provider=provider
                ).observe(time.time() - start_time)
        return wrapper
    return decorator

def update_db_pool_metrics(pool_size: int, used_connections: int):
    """Update database pool metrics"""
    DB_POOL_SIZE.set(pool_size)
    DB_POOL_USED.set(used_connections)

def time_db_query(query_type: str):
    """Decorator to time database queries"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                DB_QUERY_TIME.labels(
                    query_type=query_type
                ).observe(time.time() - start_time)
        return wrapper
    return decorator

def set_service_info(version: str, config: dict[str, Any]):
    """Set service information metrics"""
    info_dict = {
        'version': version,
        'providers': ','.join(config.get('providers', [])),
        'environment': config.get('environment', 'unknown')
    }
    SERVICE_INFO.info(info_dict)

def set_service_start_time():
    """Set service start time"""
    SERVICE_START_TIME.set_to_current_time()

def get_metrics() -> str:
    """Get Prometheus metrics in text format"""
    return generate_latest()

class MetricsCollector:
    """Centralized metrics collection and reporting"""

    def __init__(self):
        self.start_time = time.time()
        set_service_start_time()

    async def collect_service_metrics(self, unified_store) -> dict[str, Any]:
        """Collect comprehensive service metrics"""
        try:
            # Get memory count
            if unified_store:
                stats = await unified_store.get_stats()
                update_memory_count(stats.get('total_memories', 0))

                # Update provider health
                providers = stats.get('providers', {})
                for provider_name, provider_info in providers.items():
                    is_healthy = provider_info.get('status') == 'healthy'
                    update_provider_health(provider_name, is_healthy)

            # Calculate uptime
            uptime_seconds = time.time() - self.start_time

            return {
                'uptime_seconds': uptime_seconds,
                'metrics_collected': True
            }
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return {
                'uptime_seconds': time.time() - self.start_time,
                'metrics_collected': False,
                'error': str(e)
            }

# Global metrics collector instance
metrics_collector = MetricsCollector()
