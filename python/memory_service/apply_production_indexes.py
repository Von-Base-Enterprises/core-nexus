#!/usr/bin/env python3
"""
Apply pgvector indexes to production database via Render API.
"""

import json
import subprocess
import sys


def get_database_info(api_key, service_id):
    """Get database connection info from Render."""
    cmd = [
        "curl", "-s", "--request", "GET",
        "--url", f"https://api.render.com/v1/services/{service_id}",
        "--header", "Accept: application/json",
        "--header", f"Authorization: Bearer {api_key}"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error getting service info: {result.stderr}")
        return None
    
    try:
        data = json.loads(result.stdout)
        return data
    except json.JSONDecodeError:
        print(f"Error parsing response: {result.stdout}")
        return None


def get_postgres_services(api_key):
    """List all PostgreSQL services."""
    cmd = [
        "curl", "-s", "--request", "GET",
        "--url", "https://api.render.com/v1/services?limit=100",
        "--header", "Accept: application/json",
        "--header", f"Authorization: Bearer {api_key}"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error listing services: {result.stderr}")
        return []
    
    try:
        data = json.loads(result.stdout)
        postgres_services = [
            s for s in data 
            if s.get('type') == 'postgres' or 'postgres' in s.get('name', '').lower()
        ]
        return postgres_services
    except json.JSONDecodeError:
        print(f"Error parsing response: {result.stdout}")
        return []


def main():
    """Apply indexes to production database."""
    api_key = "rnd_qmKWEjuHcQ6fddsmXuRxvodE9O4T"
    
    print("🔍 Finding PostgreSQL database...")
    
    # List all services to find the database
    postgres_services = get_postgres_services(api_key)
    
    if not postgres_services:
        print("❌ No PostgreSQL services found")
        return 1
    
    print(f"\nFound {len(postgres_services)} PostgreSQL service(s):")
    for svc in postgres_services:
        print(f"  - {svc.get('name')} (ID: {svc.get('id')})")
    
    # Look for the nexus_memory_db
    nexus_db = None
    for svc in postgres_services:
        if 'nexus' in svc.get('name', '').lower() or 'memory' in svc.get('name', '').lower():
            nexus_db = svc
            break
    
    if not nexus_db:
        print("\n⚠️ Could not find nexus_memory_db automatically")
        print("Please check the Render dashboard for the correct database ID")
        return 1
    
    print(f"\n✅ Found database: {nexus_db.get('name')}")
    
    # Create the index creation SQL
    index_sql = """
-- Create pgvector indexes for Core Nexus
-- This fixes the query performance issue

-- 1. Create IVFFlat index for vector similarity search
CREATE INDEX IF NOT EXISTS idx_vector_memories_embedding 
ON vector_memories 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- 2. Create GIN index for metadata filtering
CREATE INDEX IF NOT EXISTS idx_vector_memories_metadata 
ON vector_memories 
USING GIN (metadata);

-- 3. Create index for importance score sorting
CREATE INDEX IF NOT EXISTS idx_vector_memories_importance 
ON vector_memories (importance_score DESC);

-- 4. Create composite index for common query patterns
CREATE INDEX IF NOT EXISTS idx_vector_memories_created_importance 
ON vector_memories (created_at DESC, importance_score DESC);

-- 5. Update table statistics
ANALYZE vector_memories;

-- 6. Show created indexes
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'vector_memories'
ORDER BY indexname;
"""
    
    # Save SQL to file
    with open('apply_indexes.sql', 'w') as f:
        f.write(index_sql)
    
    print("\n📝 Index creation SQL saved to apply_indexes.sql")
    print("\n🚀 To apply indexes, run:")
    print(f"  1. Go to https://dashboard.render.com/")
    print(f"  2. Find database: {nexus_db.get('name')}")
    print(f"  3. Click 'Connect' > 'External Connection'")
    print(f"  4. Copy the connection string")
    print(f"  5. Run: psql $CONNECTION_STRING < apply_indexes.sql")
    
    # Also try to get the connection details
    db_details = get_database_info(api_key, nexus_db.get('id'))
    if db_details:
        # Don't print sensitive connection strings, just confirm we can access it
        print(f"\n✅ Database details retrieved successfully")
        print("   Use the Render dashboard to get the connection string securely")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())