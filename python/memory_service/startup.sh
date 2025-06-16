#!/bin/bash
# Startup script for Core Nexus Memory Service
# Runs migrations before starting the API server

set -e

echo "Starting Core Nexus Memory Service..."

# Run database migrations
echo "Running database migrations..."
python /app/run_migrations.py

if [ $? -ne 0 ]; then
    echo "Migration failed, exiting..."
    exit 1
fi

echo "Migrations completed successfully"

# Start the API server
echo "Starting API server..."
exec python -m uvicorn memory_service.api:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WORKERS:-4}