#!/bin/bash

# Start Observability Stack for Core Nexus Memory Service
# This script starts the complete observability stack including:
# - OpenTelemetry Collector
# - Grafana Tempo (Distributed Tracing)
# - Prometheus (Metrics)
# - Grafana (Visualization)
# - Loki (Logs)

echo "🚀 Starting Core Nexus Observability Stack..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Navigate to observability directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Create required directories
echo "📁 Creating required directories..."
mkdir -p dashboards
mkdir -p prometheus-data
mkdir -p tempo-data
mkdir -p grafana-data
mkdir -p loki-data

# Set permissions (important for Linux/Mac)
chmod -R 777 prometheus-data tempo-data grafana-data loki-data

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose down

# Pull latest images
echo "📥 Pulling latest images..."
docker-compose pull

# Start the stack
echo "🎯 Starting observability stack..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service health
echo "🏥 Checking service health..."
services=("otel-collector:13133" "prometheus:9090" "tempo:3200" "grafana:3000" "loki:3100")

for service in "${services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port/health" | grep -q "200\|204"; then
        echo "✅ $name is healthy on port $port"
    else
        echo "⚠️  $name might not be ready yet on port $port"
    fi
done

echo ""
echo "🎉 Observability stack is starting up!"
echo ""
echo "📊 Access points:"
echo "  - Grafana:        http://localhost:3000 (admin/admin)"
echo "  - Prometheus:     http://localhost:9090"
echo "  - Tempo:          http://localhost:3200"
echo "  - Loki:           http://localhost:3100"
echo "  - OTLP Collector: localhost:4317 (gRPC), localhost:4318 (HTTP)"
echo ""
echo "📝 To view logs:"
echo "  docker-compose logs -f [service-name]"
echo ""
echo "🛑 To stop the stack:"
echo "  docker-compose down"
echo ""
echo "🔄 To restart a service:"
echo "  docker-compose restart [service-name]"