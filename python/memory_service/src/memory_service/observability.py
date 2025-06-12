"""
OpenTelemetry Observability Configuration

Provides comprehensive instrumentation for the Core Nexus memory service
with distributed tracing, metrics, and correlated logging.
"""

import logging
import os
import time
from typing import Any, Optional

from opentelemetry import trace, metrics, baggage
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.trace import Status, StatusCode

logger = logging.getLogger(__name__)

# Global instances
tracer: Optional[trace.Tracer] = None
meter: Optional[metrics.Meter] = None


class ObservabilityConfig:
    """Configuration for OpenTelemetry observability."""
    
    def __init__(self):
        self.service_name = os.getenv("SERVICE_NAME", "core-nexus-memory")
        self.service_version = os.getenv("SERVICE_VERSION", "1.0.0")
        self.environment = os.getenv("ENVIRONMENT", "production")
        
        # OTLP endpoints
        self.otlp_endpoint = os.getenv("OTLP_ENDPOINT", "localhost:4317")
        self.otlp_headers = os.getenv("OTLP_HEADERS", "")
        
        # Disable OTLP in production if not explicitly configured
        if self.environment == "production" and not os.getenv("OTLP_ENDPOINT"):
            self.otlp_endpoint = None
        
        # Feature flags
        self.enable_tracing = os.getenv("OTEL_TRACING_ENABLED", "true").lower() == "true"
        self.enable_metrics = os.getenv("OTEL_METRICS_ENABLED", "true").lower() == "true"
        self.enable_logging = os.getenv("OTEL_LOGGING_ENABLED", "true").lower() == "true"
        self.enable_console_export = os.getenv("OTEL_CONSOLE_EXPORT", "false").lower() == "true"
        
        # Sampling
        self.trace_sample_rate = float(os.getenv("OTEL_TRACE_SAMPLE_RATE", "1.0"))
        
        # Resource attributes
        self.resource_attributes = {
            SERVICE_NAME: self.service_name,
            SERVICE_VERSION: self.service_version,
            "environment": self.environment,
            "deployment.environment": self.environment,
            "service.namespace": "memory",
            "telemetry.sdk.name": "opentelemetry",
            "telemetry.sdk.language": "python",
        }


def initialize_observability(app=None, config: Optional[ObservabilityConfig] = None):
    """
    Initialize OpenTelemetry instrumentation.
    
    Args:
        app: FastAPI application instance
        config: ObservabilityConfig instance
    """
    global tracer, meter
    
    if not config:
        config = ObservabilityConfig()
    
    # Create resource
    resource = Resource.create(config.resource_attributes)
    
    # Initialize tracing
    if config.enable_tracing:
        tracer_provider = _setup_tracing(config, resource)
        trace.set_tracer_provider(tracer_provider)
        tracer = trace.get_tracer(__name__, config.service_version)
        
        # Set up propagation (B3 format for compatibility)
        set_global_textmap(B3MultiFormat())
        
        logger.info("OpenTelemetry tracing initialized")
    
    # Initialize metrics
    if config.enable_metrics:
        meter_provider = _setup_metrics(config, resource)
        metrics.set_meter_provider(meter_provider)
        meter = metrics.get_meter(__name__, config.service_version)
        
        # Create custom metrics
        _create_custom_metrics()
        
        logger.info("OpenTelemetry metrics initialized")
    
    # Initialize logging
    if config.enable_logging:
        LoggingInstrumentor().instrument(set_logging_format=True)
        logger.info("OpenTelemetry logging initialized")
    
    # Auto-instrument libraries
    _setup_auto_instrumentation(app)
    
    logger.info(f"Observability initialized for {config.service_name} v{config.service_version}")


def _setup_tracing(config: ObservabilityConfig, resource: Resource) -> TracerProvider:
    """Set up distributed tracing with OTLP export."""
    tracer_provider = TracerProvider(resource=resource)
    
    # OTLP exporter for production
    if config.otlp_endpoint:
        # Parse headers from "key1=value1,key2=value2" format to dict
        headers = None
        if config.otlp_headers:
            headers = {}
            for header in config.otlp_headers.split(","):
                if "=" in header:
                    key, value = header.split("=", 1)
                    headers[key.strip()] = value.strip()
        
        otlp_exporter = OTLPSpanExporter(
            endpoint=config.otlp_endpoint,
            headers=headers,
            insecure=True  # For local development
        )
        tracer_provider.add_span_processor(
            BatchSpanProcessor(otlp_exporter)
        )
    
    # Console exporter for debugging
    if config.enable_console_export:
        tracer_provider.add_span_processor(
            BatchSpanProcessor(ConsoleSpanExporter())
        )
    
    return tracer_provider


def _setup_metrics(config: ObservabilityConfig, resource: Resource) -> MeterProvider:
    """Set up metrics with Prometheus and OTLP export."""
    # Prometheus exporter for scraping
    prometheus_reader = PrometheusMetricReader()
    
    readers = [prometheus_reader]
    
    # OTLP exporter for push-based metrics
    if config.otlp_endpoint:
        # Parse headers from "key1=value1,key2=value2" format to dict
        headers = None
        if config.otlp_headers:
            headers = {}
            for header in config.otlp_headers.split(","):
                if "=" in header:
                    key, value = header.split("=", 1)
                    headers[key.strip()] = value.strip()
        
        otlp_exporter = OTLPMetricExporter(
            endpoint=config.otlp_endpoint,
            headers=headers,
            insecure=True
        )
        periodic_reader = PeriodicExportingMetricReader(
            exporter=otlp_exporter,
            export_interval_millis=60000  # Export every minute
        )
        readers.append(periodic_reader)
    
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=readers
    )
    
    return meter_provider


def _setup_auto_instrumentation(app=None):
    """Set up automatic instrumentation for libraries."""
    # FastAPI
    if app:
        FastAPIInstrumentor.instrument_app(app)
    
    # AsyncPG (PostgreSQL)
    AsyncPGInstrumentor().instrument()
    
    # HTTPX (HTTP client)
    HTTPXClientInstrumentor().instrument()


def _create_custom_metrics():
    """Create custom metrics for Core Nexus."""
    global meter
    
    if not meter:
        return
    
    # Memory operation metrics
    meter.create_counter(
        name="memory_operations_total",
        description="Total number of memory operations",
        unit="operations"
    )
    
    meter.create_histogram(
        name="memory_operation_duration",
        description="Duration of memory operations",
        unit="ms"
    )
    
    # Vector search metrics
    meter.create_histogram(
        name="vector_search_duration",
        description="Duration of vector similarity searches",
        unit="ms"
    )
    
    meter.create_histogram(
        name="vector_search_results",
        description="Number of results returned by vector search",
        unit="results"
    )
    
    # Embedding metrics
    meter.create_histogram(
        name="embedding_generation_duration",
        description="Time to generate embeddings",
        unit="ms"
    )
    
    meter.create_counter(
        name="embedding_generation_errors",
        description="Number of embedding generation errors",
        unit="errors"
    )
    
    # Deduplication metrics
    meter.create_counter(
        name="deduplication_checks",
        description="Number of deduplication checks performed",
        unit="checks"
    )
    
    meter.create_counter(
        name="duplicates_detected",
        description="Number of duplicates detected",
        unit="duplicates"
    )


# Tracing decorators and utilities
def trace_operation(operation_name: str, attributes: Optional[dict] = None):
    """
    Decorator to trace a function/method execution.
    
    Args:
        operation_name: Name of the operation being traced
        attributes: Optional attributes to add to the span
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            if not tracer:
                return await func(*args, **kwargs)
            
            with tracer.start_as_current_span(operation_name) as span:
                # Add attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                # Add function info
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        
        def sync_wrapper(*args, **kwargs):
            if not tracer:
                return func(*args, **kwargs)
            
            with tracer.start_as_current_span(operation_name) as span:
                # Add attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                # Add function info
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                
                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def record_metric(metric_name: str, value: float, attributes: Optional[dict] = None):
    """Record a metric value."""
    if not meter:
        return
    
    # Get or create the metric
    # This is simplified - in practice, you'd cache these
    if "duration" in metric_name:
        metric = meter.create_histogram(metric_name)
    elif "total" in metric_name or "count" in metric_name:
        metric = meter.create_counter(metric_name)
    else:
        metric = meter.create_gauge(metric_name)
    
    # Record value
    if hasattr(metric, 'add'):
        metric.add(value, attributes or {})
    elif hasattr(metric, 'record'):
        metric.record(value, attributes or {})


def get_current_trace_id() -> Optional[str]:
    """Get the current trace ID for correlation."""
    span = trace.get_current_span()
    if span and span.is_recording():
        trace_id = span.get_span_context().trace_id
        return format(trace_id, '032x')
    return None


def add_span_attributes(**kwargs):
    """Add attributes to the current span."""
    span = trace.get_current_span()
    if span and span.is_recording():
        for key, value in kwargs.items():
            span.set_attribute(key, value)


def create_span_with_baggage(name: str, attributes: dict, baggage_items: dict):
    """Create a span with baggage for context propagation."""
    if not tracer:
        return None
    
    # Set baggage
    for key, value in baggage_items.items():
        baggage.set_baggage(key, value)
    
    # Create span
    span = tracer.start_span(name)
    for key, value in attributes.items():
        span.set_attribute(key, value)
    
    return span


# Middleware for request tracing
class TraceRequestMiddleware:
    """Middleware to add request-specific tracing context."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, request, call_next):
        # Get or create trace context
        trace_id = get_current_trace_id()
        
        # Add to request state
        request.state.trace_id = trace_id
        
        # Process request
        start_time = time.time()
        response = await call_next(request)
        duration = (time.time() - start_time) * 1000
        
        # Add trace ID to response headers
        if trace_id:
            response.headers["X-Trace-ID"] = trace_id
        
        # Record request metrics
        if meter:
            record_metric(
                "http_request_duration",
                duration,
                {
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code
                }
            )
        
        return response