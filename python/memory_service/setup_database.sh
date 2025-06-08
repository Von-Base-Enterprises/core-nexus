#!/bin/bash
# Setup script for Render PostgreSQL with pgvector

echo "🚀 Setting up Core Nexus PostgreSQL database with pgvector..."

# Database connection details
export PGPASSWORD="your_pgvector_password_here"
DB_HOST="dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com"
DB_USER="nexus_memory_db_user"
DB_NAME="nexus_memory_db"

# Run the initialization SQL
echo "📦 Installing pgvector extension and creating tables..."
psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -f init_pgvector.sql

if [ $? -eq 0 ]; then
    echo "✅ Database setup complete!"
    echo ""
    echo "📊 Checking setup..."
    psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "\dx" -c "\dt" -c "\di"
else
    echo "❌ Database setup failed!"
    exit 1
fi

echo ""
echo "🎉 Your PostgreSQL database is ready for Core Nexus!"