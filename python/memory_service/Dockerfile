# Core Nexus Memory Service Production Dockerfile
# Optimized for performance with all vector providers

FROM python:3.11-slim as builder

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY example_usage.py .

# Production stage
FROM python:3.11-slim as production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && adduser --disabled-password --gecos '' --shell /bin/bash memoryuser

# Copy from builder
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app .

# Create necessary directories
RUN mkdir -p /app/chroma_db /app/logs && \
    chown -R memoryuser:memoryuser /app

# Switch to non-root user
USER memoryuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Environment variables
ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    CHROMA_DB_PATH=/app/chroma_db \
    LOG_LEVEL=INFO

# Expose port
EXPOSE 8000

# Start command
CMD ["python", "-m", "uvicorn", "memory_service.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]