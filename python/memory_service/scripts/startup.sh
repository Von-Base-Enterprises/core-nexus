#!/bin/bash
#
# Startup script for Core Nexus Memory Service
# Ensures database indexes exist before starting the application
#

set -e  # Exit on error

echo "Starting Core Nexus Memory Service..."
echo "Startup time: $(date)"

# Debug environment variables
echo "=== Environment Variable Check ==="
echo "RENDER: ${RENDER:-NOT_SET}"
echo "PORT: ${PORT:-NOT_SET}"
echo "OPENAI_API_KEY: ${OPENAI_API_KEY:+SET}"
echo "GEMINI_API_KEY: ${GEMINI_API_KEY:+SET}"
echo "GRAPH_ENABLED: ${GRAPH_ENABLED:-NOT_SET}"
echo "PGVECTOR_HOST: ${PGVECTOR_HOST:-NOT_SET}"
echo "Total env vars: $(env | wc -l)"

# Check specific Render variables
echo ""
echo "=== Render Platform Check ==="
if [ -n "$RENDER" ]; then
    echo "✅ Running on Render platform"
    echo "Service Name: ${RENDER_SERVICE_NAME:-unknown}"
    echo "Service ID: ${RENDER_SERVICE_ID:-unknown}"
else
    echo "❌ NOT running on Render platform"
fi

# Check if build verification file exists
if [ -f "build_verification.json" ]; then
    echo ""
    echo "=== Build Verification ==="
    cat build_verification.json
fi

echo "================================="

# Ensure indexes exist
echo "Checking database indexes..."
python scripts/ensure_indexes.py

if [ $? -eq 0 ]; then
    echo "Database indexes verified successfully"
else
    echo "Warning: Database index verification failed, but continuing..."
fi

# Start the application with environment preservation
echo "Starting API server..."
exec env uvicorn src.memory_service.api:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WORKERS:-1}