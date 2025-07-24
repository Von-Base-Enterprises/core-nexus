#!/bin/bash
# Production migration script for GraphRAG memory-entity mappings

echo "🔧 GraphRAG Production Migration Script"
echo "======================================"
echo ""
echo "This script will:"
echo "1. Connect to production database"
echo "2. Extract entities from ALL existing memories"
echo "3. Create proper memory-entity mappings"
echo "4. Fix the 155 orphaned entities"
echo ""
echo "⚠️  IMPORTANT: Set these environment variables first:"
echo "   export PGVECTOR_HOST=<production_host>"
echo "   export PGVECTOR_PORT=<production_port>"
echo "   export PGVECTOR_DATABASE=<production_db>"
echo "   export PGVECTOR_USER=<production_user>"
echo "   export PGVECTOR_PASSWORD=<production_password>"
echo ""

# Check if environment variables are set
if [ -z "$PGVECTOR_PASSWORD" ]; then
    echo "❌ ERROR: PGVECTOR_PASSWORD not set"
    echo "Please set the production database credentials first"
    exit 1
fi

echo "Database configuration:"
echo "Host: ${PGVECTOR_HOST:-localhost}"
echo "Port: ${PGVECTOR_PORT:-5432}"
echo "Database: ${PGVECTOR_DATABASE:-nexus_memory_db}"
echo "User: ${PGVECTOR_USER:-nexus_memory_db_user}"
echo ""

read -p "Continue with migration? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Migration cancelled"
    exit 1
fi

echo ""
echo "Starting migration..."
echo ""

# Run the migration script
cd python/memory_service
python3 migrate_graph_entities.py

echo ""
echo "Migration complete!"
echo ""
echo "Next steps:"
echo "1. Test entity exploration: python3 test_graphrag_production.py"
echo "2. Verify memories are connected to entities"
echo "3. Test multi-hop queries"