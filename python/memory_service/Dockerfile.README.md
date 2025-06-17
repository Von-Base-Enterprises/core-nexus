# Docker Configuration Guide

## Available Dockerfiles

### 1. Dockerfile (Main)
The primary production Dockerfile with full monitoring and observability stack.
- **Use for**: Production deployments with Prometheus/Grafana
- **Size**: ~1.2GB
- **Features**: Full monitoring, health checks, metrics endpoint

### 2. Dockerfile.keepalive
Optimized for Render.com deployments to prevent cold starts.
- **Use for**: Render.com deployments
- **Size**: ~1.2GB
- **Features**: Keep-alive worker, connection pool warming

### 3. Dockerfile.minimal
Lightweight version without monitoring stack.
- **Use for**: Development, testing, resource-constrained environments
- **Size**: ~800MB
- **Features**: Core API only, no monitoring

## Which to Use?

```bash
# Production with monitoring
docker build -f Dockerfile -t core-nexus:latest .

# Render.com deployment
docker build -f Dockerfile.keepalive -t core-nexus:render .

# Development/testing
docker build -f Dockerfile.minimal -t core-nexus:dev .
```

## Future Consolidation

Consider using build args to maintain a single Dockerfile:
```dockerfile
ARG INCLUDE_MONITORING=true
ARG RENDER_OPTIMIZED=false
```