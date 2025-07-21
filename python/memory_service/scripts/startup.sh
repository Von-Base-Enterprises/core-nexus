#!/bin/bash
#
# Startup script for Core Nexus Memory Service
# Ensures database indexes exist before starting the application
#

set -e  # Exit on error

echo "Starting Core Nexus Memory Service..."

# Ensure indexes exist
echo "Checking database indexes..."
python scripts/ensure_indexes.py

if [ $? -eq 0 ]; then
    echo "Database indexes verified successfully"
else
    echo "Warning: Database index verification failed, but continuing..."
fi

# Start the application
echo "Starting API server..."
exec uvicorn src.memory_service.api:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WORKERS:-1}