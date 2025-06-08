#!/bin/bash
set -e

echo "🎯 Core Nexus Memory Service - Step 1 Minimal Deployment"
echo "========================================================"
echo ""

# Check if we're in the right directory
if [ ! -f "docker-compose.minimal.yml" ]; then
    echo "❌ Error: Must run from memory_service directory"
    echo "Please cd to python/memory_service/ and try again"
    exit 1
fi

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed or not running"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: docker-compose is not installed"
    exit 1
fi

echo "✅ Prerequisites check passed"
echo ""

# Clean up any existing containers (optional)
echo "🧹 Cleaning up any existing containers..."
docker-compose -f docker-compose.minimal.yml down --volumes 2>/dev/null || true
echo ""

# Build the minimal image
echo "🔨 Building minimal Docker image..."
docker-compose -f docker-compose.minimal.yml build --no-cache
echo ""

# Start services
echo "🚀 Starting minimal production services..."
docker-compose -f docker-compose.minimal.yml up -d
echo ""

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
timeout=60
counter=0
while ! docker-compose -f docker-compose.minimal.yml exec -T postgres pg_isready -U core_nexus > /dev/null 2>&1; do
    if [ $counter -ge $timeout ]; then
        echo "❌ PostgreSQL failed to start within $timeout seconds"
        echo "Showing logs:"
        docker-compose -f docker-compose.minimal.yml logs postgres
        exit 1
    fi
    echo "  Waiting for PostgreSQL... ($counter/$timeout)"
    sleep 2
    counter=$((counter + 2))
done
echo "✅ PostgreSQL is ready"
echo ""

# Wait for Memory Service to be ready
echo "⏳ Waiting for Memory Service to be ready..."
timeout=90
counter=0
while ! curl -s http://localhost:8000/health > /dev/null 2>&1; do
    if [ $counter -ge $timeout ]; then
        echo "❌ Memory Service failed to start within $timeout seconds"
        echo "Showing logs:"
        docker-compose -f docker-compose.minimal.yml logs memory_service
        exit 1
    fi
    echo "  Waiting for Memory Service... ($counter/$timeout)"
    sleep 3
    counter=$((counter + 3))
done
echo "✅ Memory Service is ready"
echo ""

# Run Step 1 validation
echo "🧪 Running Step 1 validation tests..."
python3 validate_step1.py

# Check if validation passed
if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Step 1 Deployment SUCCESSFUL!"
    echo ""
    echo "📊 Access Points:"
    echo "  - API: http://localhost:8000"
    echo "  - API Docs: http://localhost:8000/docs"
    echo "  - Health Check: http://localhost:8000/health"
    echo ""
    echo "📋 Useful Commands:"
    echo "  - View logs: docker-compose -f docker-compose.minimal.yml logs -f"
    echo "  - Stop services: docker-compose -f docker-compose.minimal.yml down"
    echo "  - View containers: docker-compose -f docker-compose.minimal.yml ps"
    echo ""
    echo "✅ Ready to proceed to Step 2: Add monitoring and metrics!"
else
    echo ""
    echo "❌ Step 1 Deployment FAILED!"
    echo "Check logs with: docker-compose -f docker-compose.minimal.yml logs"
    exit 1
fi