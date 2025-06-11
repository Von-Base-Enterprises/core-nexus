# Core Nexus Observability Stack

This directory contains the complete observability infrastructure for the Core Nexus Memory Service, implementing OpenTelemetry-based distributed tracing, metrics, and logging.

## Overview

The observability stack provides:
- **Distributed Tracing**: Track requests across all components
- **Metrics**: Performance metrics and custom business metrics
- **Logging**: Structured, correlated logs with trace IDs
- **Dashboards**: Pre-built Grafana dashboards for monitoring

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│  Core Nexus     │────▶│  OpenTelemetry   │────▶│   Tempo     │
│  Memory Service │     │    Collector     │     │  (Traces)   │
└─────────────────┘     └──────────────────┘     └─────────────┘
                                │                        │
                                ├────────────────────────┤
                                ▼                        ▼
                        ┌─────────────┐          ┌─────────────┐
                        │ Prometheus  │          │   Grafana   │
                        │  (Metrics)  │◀─────────│(Dashboards) │
                        └─────────────┘          └─────────────┘
                                │                        ▲
                                └────────────────────────┘
```

## Quick Start

### 1. Start the Observability Stack

```bash
cd python/memory_service/observability
./start-observability.sh
```

### 2. Configure Core Nexus

Set the following environment variables for the memory service:

```bash
# Enable OpenTelemetry
export OTEL_TRACING_ENABLED=true
export OTEL_METRICS_ENABLED=true
export OTEL_LOGGING_ENABLED=true

# Configure OTLP endpoint
export OTLP_ENDPOINT=localhost:4317

# Optional: Enable console export for debugging
export OTEL_CONSOLE_EXPORT=false

# Service identification
export SERVICE_NAME=core-nexus-memory
export SERVICE_VERSION=1.0.0
export ENVIRONMENT=development
```

### 3. Access Dashboards

- **Grafana**: http://localhost:3000 (admin/admin)
  - Core Nexus Overview Dashboard
  - Vector Operations Dashboard
  - Trace Explorer
- **Prometheus**: http://localhost:9090
- **Tempo**: http://localhost:3200

## Components

### OpenTelemetry Collector
- Receives telemetry data from the application
- Processes and exports to various backends
- Configuration: `otel-collector-config.yaml`

### Grafana Tempo
- Distributed tracing backend
- Stores and queries traces
- Configuration: `tempo-config.yaml`

### Prometheus
- Time-series metrics database
- Scrapes metrics from applications and exporters
- Configuration: `prometheus-config.yml`

### Grafana
- Visualization platform
- Pre-configured datasources and dashboards
- Datasources: `grafana-datasources.yml`
- Dashboards: `dashboards/`

### Loki (Optional)
- Log aggregation system
- Correlates logs with traces
- Configuration: `loki-config.yaml`

## Instrumentation Details

### Automatic Instrumentation
The following libraries are automatically instrumented:
- FastAPI (HTTP endpoints)
- AsyncPG (PostgreSQL queries)
- HTTPX (HTTP client requests)

### Custom Instrumentation

#### Tracing Decorators
```python
from memory_service.observability import trace_operation

@trace_operation("my_operation")
async def my_function():
    # Function is automatically traced
    pass
```

#### Recording Metrics
```python
from memory_service.observability import record_metric

# Record a counter
record_metric("operations_total", 1, {"operation": "store"})

# Record a histogram
record_metric("operation_duration", 123.45, {"operation": "query"})
```

#### Adding Span Attributes
```python
from memory_service.observability import add_span_attributes

add_span_attributes(
    user_id="123",
    operation_type="vector_search",
    result_count=10
)
```

## Key Metrics

### Application Metrics
- `memory_operations_total`: Total memory operations (store/query)
- `memory_operation_duration`: Operation latency histogram
- `vector_search_duration`: Vector similarity search performance
- `vector_search_results`: Number of results returned
- `embedding_generation_duration`: Time to generate embeddings
- `embedding_generation_errors`: Embedding generation failures
- `deduplication_checks`: Number of deduplication checks
- `duplicates_detected`: Number of duplicates found

### Provider-Specific Metrics
- `pgvector.query.duration`: PgVector query latency
- `pgvector.query.results`: Results returned by PgVector
- `pgvector.store.duration`: PgVector store operation latency
- `chromadb.query.duration`: ChromaDB query latency

## Dashboards

### Core Nexus Overview
- Request rates and success rates
- Operation latency (p95/p99)
- Duplicate detection statistics
- Recent traces

### Vector Operations
- PgVector query performance
- Embedding generation metrics
- Provider comparison
- Slow query analysis

## Troubleshooting

### No Traces Appearing
1. Check OTEL_TRACING_ENABLED is set to "true"
2. Verify OTLP_ENDPOINT is correct
3. Check collector logs: `docker-compose logs otel-collector`

### Missing Metrics
1. Ensure the `/metrics` endpoint is accessible
2. Check Prometheus targets: http://localhost:9090/targets
3. Verify scrape configuration in `prometheus-config.yml`

### Performance Issues
1. Check memory limits in docker-compose.yml
2. Monitor collector metrics at http://localhost:8888/metrics
3. Adjust batch processor settings in collector config

## Production Deployment

### Render.com Configuration
Add these environment variables to your Render service:

```yaml
envVars:
  - key: OTEL_TRACING_ENABLED
    value: true
  - key: OTLP_ENDPOINT
    value: your-collector-endpoint:4317
  - key: OTEL_TRACE_SAMPLE_RATE
    value: "0.1"  # Sample 10% of traces in production
```

### Security Considerations
1. Use TLS for OTLP endpoints in production
2. Implement authentication for Grafana
3. Restrict access to metrics endpoints
4. Consider data retention policies

## Advanced Configuration

### Sampling Strategy
Adjust trace sampling in production to reduce overhead:

```yaml
processors:
  probabilistic_sampler:
    sampling_percentage: 10  # Sample 10% of traces
```

### Custom Dashboards
Create new dashboards by:
1. Design in Grafana UI
2. Export JSON
3. Save to `dashboards/` directory
4. Restart Grafana

### Adding New Metrics
1. Define metric in `observability.py`
2. Record metric in application code
3. Add to Prometheus scrape config if needed
4. Create dashboard panel

## Maintenance

### Log Rotation
Configure log rotation for long-running deployments:

```bash
# Add to docker-compose.yml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### Data Retention
Set retention policies:
- Tempo: 48 hours (configurable in tempo-config.yaml)
- Prometheus: 15 days (default)
- Loki: 7 days (configurable)

### Backup
Important data to backup:
- Grafana dashboards (exported JSON)
- Prometheus rules and alerts
- Custom configurations

## Resources

- [OpenTelemetry Python Docs](https://opentelemetry.io/docs/instrumentation/python/)
- [Grafana Tempo Docs](https://grafana.com/docs/tempo/latest/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [Grafana Dashboard Guide](https://grafana.com/docs/grafana/latest/dashboards/)