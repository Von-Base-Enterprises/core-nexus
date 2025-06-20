#!/usr/bin/env python3
"""
Apply HNSW migration using direct asyncpg connection
This bypasses the service dependency issues
"""

import asyncio
import asyncpg
import os
from datetime import datetime

# Database connection details (from render.yaml)
DB_HOST = "dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com"
DB_PORT = 5432
DB_NAME = "nexus_memory_db"
DB_USER = "nexus_memory_db_user"
# Password needs to be provided via environment variable

MIGRATION_SQL = """
-- HNSW Performance Migration - 510ms → <50ms target
BEGIN;

DO $$
BEGIN
    RAISE NOTICE '🚀 Starting HNSW performance migration at %', NOW();
END $$;

-- Check current table size
DO $$
DECLARE
    row_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO row_count FROM vector_memories;
    RAISE NOTICE '📊 Indexing % memories', row_count;
END $$;

-- Drop old indexes
DROP INDEX IF EXISTS idx_vector_memories_embedding;
DROP INDEX IF EXISTS idx_vector_memories_embedding_ivfflat;

-- Create HNSW index (the key performance improvement)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_embedding_hnsw 
ON vector_memories 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Additional performance indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_user_created 
ON vector_memories (user_id, created_at DESC)
WHERE user_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_importance_created
ON vector_memories (importance_score DESC, created_at DESC);

-- Update table statistics
ANALYZE vector_memories;

-- Verify success
DO $$
DECLARE
    hnsw_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'vector_memories' 
        AND indexname = 'idx_memories_embedding_hnsw'
    ) INTO hnsw_exists;
    
    IF hnsw_exists THEN
        RAISE NOTICE '✅ HNSW index created successfully';
    ELSE
        RAISE WARNING '❌ HNSW index creation failed';
    END IF;
END $$;

-- Record migration
INSERT INTO schema_migrations (version, applied_at) 
VALUES ('002_optimize_pgvector_performance', NOW())
ON CONFLICT (version) DO NOTHING;

COMMIT;

DO $$
BEGIN
    RAISE NOTICE '🎉 Migration complete! Expected: 510ms → <50ms queries';
END $$;
"""

async def apply_migration():
    """Apply the HNSW migration directly"""
    print("🚀 HNSW MIGRATION - DIRECT DATABASE CONNECTION")
    print("="*60)
    
    # Check for password
    db_password = os.getenv("PGVECTOR_PASSWORD")
    if not db_password:
        print("❌ PGVECTOR_PASSWORD environment variable required")
        print("   This migration requires direct database access")
        print("   Alternative: Apply via production database admin tools")
        return False
        
    try:
        # Build connection string
        conn_string = f"postgresql://{DB_USER}:{db_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require"
        
        print("🔌 Connecting to production database...")
        conn = await asyncpg.connect(conn_string)
        
        # Check current state
        memory_count = await conn.fetchval("SELECT COUNT(*) FROM vector_memories")
        print(f"📊 Found {memory_count} memories to index")
        
        # Check existing indexes
        existing_indexes = await conn.fetch("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename = 'vector_memories'
            ORDER BY indexname
        """)
        
        print(f"Current indexes: {[idx['indexname'] for idx in existing_indexes]}")
        
        print("\n🔧 Applying HNSW migration...")
        print("⏳ This will take 2-5 minutes for index creation...")
        
        # Execute migration
        await conn.execute(MIGRATION_SQL)
        
        print("✅ Migration executed successfully!")
        
        # Verify results
        hnsw_indexes = await conn.fetch("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename = 'vector_memories' 
            AND indexname LIKE '%hnsw%'
        """)
        
        print(f"✅ HNSW indexes created: {[idx['indexname'] for idx in hnsw_indexes]}")
        
        await conn.close()
        print("🎉 MIGRATION COMPLETE!")
        return True
        
    except asyncpg.exceptions.ConnectionError as e:
        print(f"❌ Database connection failed: {e}")
        print("   Check network access and credentials")
        return False
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

async def test_performance():
    """Test performance after migration"""
    print("\n📊 Testing performance improvement...")
    
    import httpx
    import time
    
    # Wait for changes to take effect
    print("⏳ Waiting 30 seconds for indexes to be fully active...")
    await asyncio.sleep(30)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Test via health endpoint which includes query performance
            response = await client.get("https://core-nexus-memory-service.onrender.com/health")
            
            if response.status_code == 200:
                health_data = response.json()
                avg_query_time = health_data.get("avg_query_time_ms", 0)
                
                print(f"📊 Current average query time: {avg_query_time:.1f}ms")
                
                if avg_query_time < 50:
                    print("🎉 EXCELLENT: Target achieved (<50ms)!")
                elif avg_query_time < 100:
                    print("✅ GREAT: Significant improvement achieved!")
                elif avg_query_time < 300:
                    print("📈 GOOD: Performance improved substantially")
                else:
                    print("⚠️ MODERATE: Some improvement, may need additional optimization")
                    
                return avg_query_time
            else:
                print(f"❌ Health check failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Performance test failed: {e}")
            
    return None

async def main():
    """Main execution"""
    print("⚡ CRITICAL PERFORMANCE MIGRATION")
    print("This is the single highest-impact fix for Core Nexus performance")
    print()
    
    # Try to apply migration
    success = await apply_migration()
    
    if success:
        # Test the results
        avg_time = await test_performance()
        
        if avg_time and avg_time < 100:
            print(f"\n🎉 MISSION ACCOMPLISHED!")
            print(f"Performance: 510ms → {avg_time:.1f}ms")
            print("System is now ready for high-scale operations!")
        else:
            print(f"\n✅ MIGRATION APPLIED")
            print("Performance verification recommended")
            
    else:
        print("\n📋 MIGRATION NOT APPLIED")
        print("Manual database access required")
        print("\nAlternative approaches:")
        print("1. Use pgAdmin or psql with production credentials")
        print("2. Apply via Render.com database console")
        print("3. Create admin endpoint in the service")
        print("\nSQL to execute:")
        print("See MIGRATION_SQL in this script")

if __name__ == "__main__":
    asyncio.run(main())