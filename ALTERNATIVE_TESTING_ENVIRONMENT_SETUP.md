# Alternative Testing Environment Setup Guide
**Date**: June 22, 2025  
**Project**: Core Nexus PGVector Performance Optimization  
**Purpose**: Independent testing environment for optimization validation  

## 🎯 Overview

**COMPLETE LOCAL POSTGRESQL + PGVECTOR TESTING ENVIRONMENT**

This guide provides multiple approaches to set up a production-like testing environment for validating the optimization system independently of production credentials.

## 🐳 Option 1: Docker-Based Environment (Recommended)

### Quick Setup with Docker Compose

#### 1. Create Docker Compose Configuration
```yaml
# docker-compose.testing.yml
version: '3.8'

services:
  postgres-testing:
    image: pgvector/pgvector:pg15
    container_name: nexus-postgres-testing
    environment:
      POSTGRES_DB: nexus_memory_db
      POSTGRES_USER: nexus_memory_db_user
      POSTGRES_PASSWORD: testing_password_123
      # PostgreSQL optimization settings
      POSTGRES_INITDB_ARGS: "--auth-host=md5 --auth-local=md5"
    ports:
      - "5433:5432"  # Use different port to avoid conflicts
    volumes:
      - ./testing_data:/var/lib/postgresql/data
      - ./init-testing-db.sql:/docker-entrypoint-initdb.d/init-db.sql
    command: >
      postgres
      -c shared_buffers=256MB
      -c work_mem=16MB
      -c maintenance_work_mem=64MB
      -c random_page_cost=1.1
      -c seq_page_cost=1.0
      -c jit=off
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U nexus_memory_db_user -d nexus_memory_db"]
      interval: 10s
      timeout: 5s
      retries: 5

  nexus-api-testing:
    build: 
      context: ./python/memory_service
      dockerfile: Dockerfile
    container_name: nexus-api-testing
    environment:
      PGVECTOR_HOST: postgres-testing
      PGVECTOR_PORT: 5432
      PGVECTOR_DATABASE: nexus_memory_db
      PGVECTOR_USER: nexus_memory_db_user
      PGVECTOR_PASSWORD: testing_password_123
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      LOG_LEVEL: DEBUG
    ports:
      - "8001:8000"  # Use different port for testing
    depends_on:
      postgres-testing:
        condition: service_healthy
    volumes:
      - ./python/memory_service:/app
```

#### 2. Create Testing Database Initialization Script
```sql
-- init-testing-db.sql
-- Initialize testing database with pgvector extension

-- Create the vector extension
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS hstore;

-- Create the vector_memories table
CREATE TABLE IF NOT EXISTS vector_memories (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create initial index for testing
CREATE INDEX IF NOT EXISTS vector_memories_embedding_idx 
ON vector_memories USING hnsw (embedding vector_cosine_ops);

-- Insert sample test data
INSERT INTO vector_memories (content, embedding) VALUES 
('Sample vector memory for testing optimization performance', array_fill(0.1, ARRAY[1536])::vector),
('Another test vector for performance benchmarking', array_fill(0.2, ARRAY[1536])::vector),
('Performance testing vector with different values', array_fill(0.3, ARRAY[1536])::vector);

-- Generate additional test vectors for realistic performance testing
DO $$
DECLARE
    i INTEGER;
    test_embedding vector(1536);
BEGIN
    FOR i IN 1..1000 LOOP
        -- Generate pseudo-random vector for testing
        SELECT array_agg(random())::vector INTO test_embedding 
        FROM generate_series(1, 1536);
        
        INSERT INTO vector_memories (content, embedding) VALUES 
        (format('Generated test vector %s for performance optimization testing', i), test_embedding);
    END LOOP;
END $$;

-- Create indexes for performance comparison
CREATE INDEX CONCURRENTLY IF NOT EXISTS vector_memories_content_idx ON vector_memories(content);
CREATE INDEX CONCURRENTLY IF NOT EXISTS vector_memories_created_at_idx ON vector_memories(created_at);
```

#### 3. Environment Configuration for Testing
```bash
# Create .env.testing file
cat > .env.testing << 'EOF'
# Testing Environment Configuration
PGVECTOR_HOST=localhost
PGVECTOR_PORT=5433
PGVECTOR_DATABASE=nexus_memory_db
PGVECTOR_USER=nexus_memory_db_user
PGVECTOR_PASSWORD=testing_password_123

# API Configuration
API_HOST=0.0.0.0
API_PORT=8001
LOG_LEVEL=DEBUG

# OpenAI Configuration (use your actual key)
OPENAI_API_KEY=your_openai_api_key_here

# Testing-specific settings
ENABLE_DEBUG_ENDPOINTS=true
CACHE_TTL=60
MAX_QUERY_LIMIT=1000
EOF
```

#### 4. Launch Testing Environment
```bash
# Start the testing environment
docker-compose -f docker-compose.testing.yml up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 30

# Verify database connectivity
docker exec nexus-postgres-testing psql -U nexus_memory_db_user -d nexus_memory_db -c "SELECT COUNT(*) FROM vector_memories;"

# Verify API connectivity
curl http://localhost:8001/health

echo "Testing environment ready!"
```

## 🖥️ Option 2: Native Installation (Advanced)

### Ubuntu/Debian Installation

#### 1. Install PostgreSQL and pgvector
```bash
# Install PostgreSQL 15
sudo apt update
sudo apt install -y postgresql-15 postgresql-15-dev

# Install build dependencies for pgvector
sudo apt install -y git build-essential

# Install pgvector extension
cd /tmp
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install

# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### 2. Configure Testing Database
```bash
# Create testing database and user
sudo -u postgres psql << 'EOF'
CREATE DATABASE nexus_memory_db_testing;
CREATE USER nexus_memory_db_user WITH PASSWORD 'testing_password_123';
GRANT ALL PRIVILEGES ON DATABASE nexus_memory_db_testing TO nexus_memory_db_user;
ALTER USER nexus_memory_db_user CREATEDB;
EOF

# Configure PostgreSQL for vector operations
sudo tee -a /etc/postgresql/15/main/postgresql.conf << 'EOF'

# Vector optimization settings
shared_buffers = 256MB
work_mem = 16MB  
maintenance_work_mem = 64MB
random_page_cost = 1.1
seq_page_cost = 1.0
jit = off

# Connection settings
max_connections = 100
EOF

# Restart PostgreSQL
sudo systemctl restart postgresql
```

#### 3. Initialize Testing Data
```bash
# Run initialization script
sudo -u postgres psql -d nexus_memory_db_testing -f init-testing-db.sql
```

## 🚀 Option 3: Quick Validation Script

### Automated Testing Environment Setup
```bash
#!/bin/bash
# setup_testing_environment.sh

set -e

echo "=== Setting up Alternative Testing Environment ==="

# Check if Docker is available
if command -v docker >/dev/null 2>&1; then
    echo "✅ Docker found - using Docker-based setup"
    
    # Create testing directory
    mkdir -p testing_environment
    cd testing_environment
    
    # Create docker-compose file
    cat > docker-compose.testing.yml << 'EOF'
version: '3.8'
services:
  postgres-testing:
    image: pgvector/pgvector:pg15
    container_name: nexus-postgres-testing
    environment:
      POSTGRES_DB: nexus_memory_db
      POSTGRES_USER: nexus_memory_db_user
      POSTGRES_PASSWORD: testing_password_123
    ports:
      - "5433:5432"
    volumes:
      - ./testing_data:/var/lib/postgresql/data
    command: >
      postgres
      -c shared_buffers=256MB
      -c work_mem=16MB
      -c maintenance_work_mem=64MB
      -c random_page_cost=1.1
      -c seq_page_cost=1.0
      -c jit=off
EOF
    
    # Start testing database
    docker-compose -f docker-compose.testing.yml up -d
    
    # Wait for database to be ready
    echo "Waiting for database to start..."
    sleep 20
    
    # Create testing data
    docker exec nexus-postgres-testing psql -U nexus_memory_db_user -d nexus_memory_db -c "
        CREATE EXTENSION IF NOT EXISTS vector;
        CREATE TABLE IF NOT EXISTS vector_memories (
            id SERIAL PRIMARY KEY,
            content TEXT NOT NULL,
            embedding vector(1536),
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        -- Insert test data
        INSERT INTO vector_memories (content, embedding) 
        SELECT 
            format('Test vector %s for optimization validation', i),
            array_agg(random())::vector
        FROM generate_series(1, 1000) i, generate_series(1, 1536);
        
        CREATE INDEX vector_memories_embedding_idx 
        ON vector_memories USING hnsw (embedding vector_cosine_ops);
    "
    
    echo "✅ Docker testing environment ready!"
    echo "Database: localhost:5433"
    echo "Credentials: nexus_memory_db_user / testing_password_123"
    
else
    echo "❌ Docker not found - please install Docker or use native installation"
    exit 1
fi
```

## 🧪 Testing the Optimization System

### Environment Configuration for Testing
```bash
# Set testing environment variables
export PGVECTOR_HOST=localhost
export PGVECTOR_PORT=5433
export PGVECTOR_DATABASE=nexus_memory_db
export PGVECTOR_USER=nexus_memory_db_user
export PGVECTOR_PASSWORD=testing_password_123
export LOG_LEVEL=DEBUG
```

### Run Optimization System Tests
```bash
# Test performance monitoring system
cd /mnt/c/Users/Tyvon/core-nexus
python3 -c "
import asyncio
import sys
sys.path.append('python/memory_service/src')
from memory_service.performance_monitor import VectorPerformanceMonitor
from memory_service.config import DatabaseConfig
import asyncpg

async def test_environment():
    print('Testing database connectivity...')
    try:
        conn_str = f'postgresql://{DatabaseConfig.USER}:{DatabaseConfig.PASSWORD}@{DatabaseConfig.HOST}:{DatabaseConfig.PORT}/{DatabaseConfig.DATABASE}'
        conn = await asyncpg.connect(conn_str)
        
        # Test vector query
        result = await conn.fetchval('SELECT COUNT(*) FROM vector_memories')
        print(f'✅ Database connected - {result} vectors available')
        
        await conn.close()
        print('✅ Testing environment ready for optimization validation')
        
    except Exception as e:
        print(f'❌ Database connection failed: {e}')

asyncio.run(test_environment())
"

# Run rapid baseline on testing environment
python3 rapid_production_baseline.py

# Test optimization deployment (config phase only)
python3 apply_pgvector_optimizations.py --phase=config --dry-run
```

### Performance Comparison Testing
```bash
# Test current performance
echo "=== Testing BEFORE Optimization ==="
python3 -c "
import asyncio
import sys
sys.path.append('python/memory_service/src')
from memory_service.performance_monitor import VectorPerformanceMonitor

async def baseline_test():
    monitor = VectorPerformanceMonitor()
    results = await monitor.run_quick_benchmark()
    print(f'Baseline P95 Latency: {results.get(\"p95_latency_ms\", \"unknown\")}ms')

asyncio.run(baseline_test())
"

# Apply optimizations to testing environment
echo "=== Applying Optimizations ==="
python3 apply_pgvector_optimizations.py --phase=config
python3 apply_pgvector_optimizations.py --phase=index

# Test optimized performance  
echo "=== Testing AFTER Optimization ==="
python3 -c "
import asyncio
import sys
sys.path.append('python/memory_service/src')
from memory_service.performance_monitor import VectorPerformanceMonitor

async def optimized_test():
    monitor = VectorPerformanceMonitor()
    results = await monitor.run_quick_benchmark()
    print(f'Optimized P95 Latency: {results.get(\"p95_latency_ms\", \"unknown\")}ms')

asyncio.run(optimized_test())
"
```

## 📊 Testing Environment Benefits

### Advantages of Alternative Testing
- ✅ **Independent Validation**: Test optimization system without production dependencies
- ✅ **Risk-Free Testing**: Validate all components before production deployment
- ✅ **Performance Validation**: Measure optimization effectiveness in controlled environment
- ✅ **Documentation**: Generate comprehensive deployment procedures
- ✅ **Team Training**: Practice deployment process with stakeholders

### Expected Testing Results
- **Baseline Performance**: Establish unoptimized performance metrics
- **Optimization Impact**: Measure improvement from each optimization phase
- **Deployment Validation**: Confirm all scripts and procedures work correctly
- **Rollback Testing**: Validate emergency rollback procedures

### Testing Success Criteria
- [ ] **Database Connectivity**: Successful connection to testing PostgreSQL
- [ ] **Vector Operations**: Working vector similarity search  
- [ ] **Performance Baseline**: Measurable latency and throughput metrics
- [ ] **Optimization Deployment**: Successful application of config and index optimizations
- [ ] **Performance Improvement**: Documented improvement in testing environment

## 🔄 Cleanup and Maintenance

### Docker Environment Cleanup
```bash
# Stop and remove testing environment
docker-compose -f docker-compose.testing.yml down

# Remove testing data (optional)
sudo rm -rf testing_data/

# Remove testing images (optional)
docker rmi pgvector/pgvector:pg15
```

### Native Installation Cleanup
```bash
# Remove testing database
sudo -u postgres psql -c "DROP DATABASE nexus_memory_db_testing;"
sudo -u postgres psql -c "DROP USER nexus_memory_db_user;"

# Revert PostgreSQL configuration (optional)
sudo systemctl stop postgresql
# Edit /etc/postgresql/15/main/postgresql.conf to remove testing settings
sudo systemctl start postgresql
```

## 🎯 Next Steps After Testing Environment Setup

### Immediate Actions
1. **Validate Environment**: Confirm database connectivity and vector operations
2. **Run Baseline Tests**: Establish performance metrics in testing environment
3. **Test Optimization Scripts**: Validate all deployment procedures
4. **Document Results**: Generate comprehensive testing report

### Documentation Generated
- **Performance Baseline**: Testing environment performance metrics
- **Optimization Effectiveness**: Measured improvement from optimizations
- **Deployment Procedures**: Validated step-by-step deployment guide
- **Team Training Materials**: Hands-on experience with optimization system

---

## 🎯 EXPECTED OUTCOME

**Within 2-4 hours, you will have:**
1. **Fully Functional Testing Environment** with PostgreSQL + pgvector
2. **Validated Optimization System** with measured performance improvements
3. **Comprehensive Documentation** of deployment procedures
4. **Team Training Platform** for stakeholder coordination

**This alternative environment provides complete independence from production credentials while validating the entire optimization system.**

**TESTING ENVIRONMENT STATUS: READY FOR SETUP** 🚀