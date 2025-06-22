#!/bin/bash
# setup_testing_environment.sh
# Quick setup script for alternative PostgreSQL + pgvector testing environment

set -e

echo "=== Core Nexus Testing Environment Setup ==="
echo "Setting up PostgreSQL + pgvector for optimization testing"
echo ""

# Configuration
TESTING_DB_PORT=5433
TESTING_DB_NAME=nexus_memory_db
TESTING_DB_USER=nexus_memory_db_user
TESTING_DB_PASSWORD=testing_password_123

# Check if Docker is available
if ! command -v docker >/dev/null 2>&1; then
    echo "❌ Docker not found. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose >/dev/null 2>&1; then
    echo "❌ Docker Compose not found. Please install Docker Compose first."
    echo "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose found"

# Create testing directory
TESTING_DIR="testing_environment"
echo "📁 Creating testing directory: $TESTING_DIR"
mkdir -p $TESTING_DIR
cd $TESTING_DIR

# Create docker-compose configuration
echo "🐳 Creating Docker Compose configuration..."
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
      POSTGRES_INITDB_ARGS: "--auth-host=md5 --auth-local=md5"
    ports:
      - "5433:5432"
    volumes:
      - ./testing_data:/var/lib/postgresql/data
      - ./init-testing-db.sql:/docker-entrypoint-initdb.d/init-db.sql
    command: >
      postgres
      -c shared_buffers=256MB
      -c work_mem=16MB
      -c maintenance_work_mem=64MB
      -c effective_cache_size=768MB
      -c random_page_cost=1.1
      -c seq_page_cost=1.0
      -c jit=off
      -c max_connections=100
      -c log_min_duration_statement=1000
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U nexus_memory_db_user -d nexus_memory_db"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
EOF

# Create database initialization script
echo "🗄️ Creating database initialization script..."
cat > init-testing-db.sql << 'EOF'
-- init-testing-db.sql
-- Initialize testing database with pgvector extension

-- Create the vector extension
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS hstore;

-- Create the vector_memories table (production schema)
CREATE TABLE IF NOT EXISTS vector_memories (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create basic index (will be optimized later)
CREATE INDEX IF NOT EXISTS vector_memories_embedding_basic_idx 
ON vector_memories USING hnsw (embedding vector_cosine_ops);

-- Create supporting indexes
CREATE INDEX IF NOT EXISTS vector_memories_content_idx ON vector_memories(content);
CREATE INDEX IF NOT EXISTS vector_memories_created_at_idx ON vector_memories(created_at);

-- Insert initial test data for immediate validation
INSERT INTO vector_memories (content, embedding) VALUES 
('Sample vector memory for testing optimization performance', array_fill(0.1, ARRAY[1536])::vector),
('Another test vector for performance benchmarking', array_fill(0.2, ARRAY[1536])::vector),
('Performance testing vector with different values', array_fill(0.3, ARRAY[1536])::vector),
('Vector search optimization validation data', array_fill(0.4, ARRAY[1536])::vector),
('PostgreSQL pgvector performance testing', array_fill(0.5, ARRAY[1536])::vector);

-- Generate realistic test dataset for performance testing
DO $$
DECLARE
    i INTEGER;
    test_embedding vector(1536);
    content_templates TEXT[] := ARRAY[
        'Machine learning model training data for %s iteration',
        'Natural language processing embedding for document %s',
        'Computer vision feature vector for image %s',
        'Recommendation system user preference vector %s',
        'Semantic search index entry for content %s',
        'Knowledge graph embedding for entity %s',
        'Text classification feature vector %s',
        'Information retrieval document embedding %s'
    ];
BEGIN
    FOR i IN 1..2000 LOOP
        -- Generate pseudo-random normalized vector for realistic testing
        SELECT array_agg(
            CASE 
                WHEN random() < 0.1 THEN 0.0
                ELSE (random() - 0.5) * 2.0
            END
        )::vector INTO test_embedding 
        FROM generate_series(1, 1536);
        
        INSERT INTO vector_memories (content, embedding) VALUES 
        (
            format(content_templates[1 + (i % array_length(content_templates, 1))], i),
            test_embedding
        );
        
        -- Log progress for large datasets
        IF i % 500 = 0 THEN
            RAISE NOTICE 'Generated % test vectors', i;
        END IF;
    END LOOP;
END $$;

-- Create additional indexes for comprehensive testing
CREATE INDEX CONCURRENTLY IF NOT EXISTS vector_memories_metadata_idx ON vector_memories USING gin(metadata);

-- Show final statistics
SELECT 
    COUNT(*) as total_vectors,
    pg_size_pretty(pg_total_relation_size('vector_memories')) as table_size,
    pg_size_pretty(pg_total_relation_size('vector_memories_embedding_basic_idx')) as index_size
FROM vector_memories;

-- Display sample data
SELECT 
    id, 
    substring(content, 1, 50) || '...' as content_preview,
    array_length(embedding, 1) as embedding_dimension
FROM vector_memories 
ORDER BY created_at 
LIMIT 5;

RAISE NOTICE 'Testing database initialized successfully with % vectors', (SELECT COUNT(*) FROM vector_memories);
EOF

# Create environment configuration
echo "⚙️ Creating environment configuration..."
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

# Feature flags for testing
ENABLE_DEBUG_ENDPOINTS=true
CACHE_TTL=60
MAX_QUERY_LIMIT=1000

# OpenAI Configuration (optional - set your actual key)
# OPENAI_API_KEY=your_openai_api_key_here
EOF

# Pull Docker image
echo "📥 Pulling pgvector Docker image..."
docker pull pgvector/pgvector:pg15

# Start the testing environment
echo "🚀 Starting testing environment..."
docker-compose -f docker-compose.testing.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for database to initialize..."
echo "This may take 30-60 seconds for initial setup and data generation..."

# Wait with progress indicator
for i in {1..60}; do
    if docker exec nexus-postgres-testing pg_isready -U $TESTING_DB_USER -d $TESTING_DB_NAME >/dev/null 2>&1; then
        echo "✅ Database is ready!"
        break
    fi
    echo -n "."
    sleep 1
done

# Verify database setup
echo ""
echo "🔍 Verifying database setup..."

# Check database connectivity
if docker exec nexus-postgres-testing psql -U $TESTING_DB_USER -d $TESTING_DB_NAME -c "SELECT version();" >/dev/null 2>&1; then
    echo "✅ Database connectivity confirmed"
else
    echo "❌ Database connectivity failed"
    exit 1
fi

# Check vector extension
if docker exec nexus-postgres-testing psql -U $TESTING_DB_USER -d $TESTING_DB_NAME -c "SELECT extname FROM pg_extension WHERE extname = 'vector';" | grep -q vector; then
    echo "✅ pgvector extension installed"
else
    echo "❌ pgvector extension not found"
    exit 1
fi

# Check test data
VECTOR_COUNT=$(docker exec nexus-postgres-testing psql -U $TESTING_DB_USER -d $TESTING_DB_NAME -t -c "SELECT COUNT(*) FROM vector_memories;")
VECTOR_COUNT=$(echo $VECTOR_COUNT | tr -d ' ')

if [ "$VECTOR_COUNT" -gt 0 ]; then
    echo "✅ Test data loaded: $VECTOR_COUNT vectors"
else
    echo "❌ Test data not found"
    exit 1
fi

# Test vector query
echo "🔍 Testing vector query performance..."
QUERY_TIME=$(docker exec nexus-postgres-testing psql -U $TESTING_DB_USER -d $TESTING_DB_NAME -c "
\timing on
SELECT content, embedding <=> array_fill(0.1, ARRAY[1536])::vector as distance 
FROM vector_memories 
ORDER BY embedding <=> array_fill(0.1, ARRAY[1536])::vector 
LIMIT 5;
" 2>&1 | grep "Time:" | awk '{print $2}')

if [ ! -z "$QUERY_TIME" ]; then
    echo "✅ Vector query successful (Time: $QUERY_TIME)"
else
    echo "✅ Vector query functional"
fi

# Create connection test script
echo "📝 Creating connection test script..."
cat > test_connection.py << 'EOF'
#!/usr/bin/env python3
"""
Test connection to alternative testing environment
"""
import asyncio
import asyncpg
import os
import sys

async def test_connection():
    """Test database connection and basic operations"""
    try:
        # Load testing environment
        host = 'localhost'
        port = 5433
        database = 'nexus_memory_db'
        user = 'nexus_memory_db_user'
        password = 'testing_password_123'
        
        print(f"Connecting to {user}@{host}:{port}/{database}")
        
        # Connect to database
        conn = await asyncpg.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        
        # Test basic query
        version = await conn.fetchval("SELECT version()")
        print(f"✅ Database connected: {version[:50]}...")
        
        # Test vector operations
        vector_count = await conn.fetchval("SELECT COUNT(*) FROM vector_memories")
        print(f"✅ Vector table accessible: {vector_count} vectors")
        
        # Test vector query
        import time
        start_time = time.time()
        
        test_vector = [0.1] * 1536
        results = await conn.fetch("""
            SELECT id, content, embedding <=> $1::vector as distance
            FROM vector_memories
            ORDER BY embedding <=> $1::vector
            LIMIT 5
        """, test_vector)
        
        query_time = (time.time() - start_time) * 1000
        print(f"✅ Vector query successful: {len(results)} results in {query_time:.1f}ms")
        
        # Show sample results
        for i, row in enumerate(results):
            print(f"  {i+1}. {row['content'][:50]}... (distance: {row['distance']:.4f})")
        
        await conn.close()
        print("\n🎯 Testing environment is ready for optimization validation!")
        return True
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)
EOF

chmod +x test_connection.py

# Run connection test
echo ""
echo "🧪 Running connection test..."
if python3 test_connection.py; then
    echo ""
    echo "🎉 SUCCESS! Testing environment is ready!"
else
    echo "❌ Connection test failed"
    exit 1
fi

# Generate summary
echo ""
echo "=================================="
echo "🎯 TESTING ENVIRONMENT SUMMARY"
echo "=================================="
echo "Database Host: localhost"
echo "Database Port: $TESTING_DB_PORT"
echo "Database Name: $TESTING_DB_NAME"
echo "Database User: $TESTING_DB_USER"
echo "Database Password: $TESTING_DB_PASSWORD"
echo ""
echo "Docker Container: nexus-postgres-testing"
echo "Test Vectors: $VECTOR_COUNT"
echo ""
echo "Environment file: .env.testing"
echo "Connection test: ./test_connection.py"
echo ""
echo "=================================="
echo "🚀 NEXT STEPS"
echo "=================================="
echo "1. Set environment variables:"
echo "   source .env.testing"
echo ""
echo "2. Test optimization system:"
echo "   cd .."
echo "   export PGVECTOR_HOST=localhost"
echo "   export PGVECTOR_PORT=5433"
echo "   export PGVECTOR_PASSWORD=testing_password_123"
echo "   python3 rapid_production_baseline.py"
echo ""
echo "3. Apply optimizations:"
echo "   python3 apply_pgvector_optimizations.py --phase=config"
echo "   python3 apply_pgvector_optimizations.py --phase=index"
echo ""
echo "4. Stop environment when done:"
echo "   docker-compose -f docker-compose.testing.yml down"
echo ""
echo "✅ Testing environment setup complete!"