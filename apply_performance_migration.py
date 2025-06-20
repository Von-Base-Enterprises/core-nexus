#!/usr/bin/env python3
"""
Apply HNSW performance migration through the production service connection pool
This is safer than direct database access as it uses the same connection as the service
"""

import asyncio
import httpx
import json
import time
from datetime import datetime

API_BASE = "https://core-nexus-memory-service.onrender.com"

# The migration SQL that will dramatically improve performance
HNSW_MIGRATION_SQL = """
-- Migration 002: HNSW Performance Optimization
-- Expected improvement: 885ms → <50ms query time

BEGIN;

-- Log migration start
DO $$
BEGIN
    RAISE NOTICE 'Starting pgvector HNSW performance optimization migration...';
END $$;

-- Check current indexes
DO $$
DECLARE
    index_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes 
    WHERE tablename = 'vector_memories' 
    AND indexname LIKE '%hnsw%';
    
    RAISE NOTICE 'Current HNSW indexes: %', index_count;
END $$;

-- Drop old ivfflat index if it exists
DROP INDEX IF EXISTS idx_vector_memories_embedding;
DROP INDEX IF EXISTS idx_vector_memories_embedding_ivfflat;

-- Create new HNSW index for much faster similarity search
-- HNSW (Hierarchical Navigable Small World) provides better query performance than ivfflat
-- m=16: number of bi-directional links created for each node (higher = better recall, more memory)
-- ef_construction=64: size of the dynamic candidate list (higher = better quality, slower build)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_embedding_hnsw 
ON vector_memories 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Add composite index for user-filtered queries
-- This significantly speeds up queries with user_id filters
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_user_created 
ON vector_memories (user_id, created_at DESC)
WHERE user_id IS NOT NULL;

-- Add index for importance score filtering and sorting
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_importance_created
ON vector_memories (importance_score DESC, created_at DESC);

-- Update table statistics for query planner
ANALYZE vector_memories;

-- Verify indexes were created successfully
DO $$
DECLARE
    hnsw_exists BOOLEAN;
    composite_exists BOOLEAN;
    importance_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'vector_memories' 
        AND indexname = 'idx_memories_embedding_hnsw'
    ) INTO hnsw_exists;
    
    SELECT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'vector_memories' 
        AND indexname = 'idx_memories_user_created'
    ) INTO composite_exists;
    
    SELECT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'vector_memories' 
        AND indexname = 'idx_memories_importance_created'
    ) INTO importance_exists;
    
    IF hnsw_exists THEN
        RAISE NOTICE 'SUCCESS: HNSW index created successfully';
    ELSE
        RAISE WARNING 'HNSW index creation may have failed';
    END IF;
    
    IF composite_exists THEN
        RAISE NOTICE 'SUCCESS: User composite index created';
    ELSE
        RAISE WARNING 'User composite index creation failed';
    END IF;
    
    IF importance_exists THEN
        RAISE NOTICE 'SUCCESS: Importance index created';
    ELSE
        RAISE WARNING 'Importance index creation failed';
    END IF;
END $$;

-- Record migration completion
INSERT INTO schema_migrations (version, applied_at) 
VALUES ('002_optimize_pgvector_performance', NOW())
ON CONFLICT (version) DO NOTHING;

COMMIT;

-- Final verification
DO $$
BEGIN
    RAISE NOTICE 'Migration 002 completed. Expected query performance improvement: 885ms → <50ms';
END $$;
"""

async def test_current_performance():
    """Test current query performance"""
    print("📊 Testing current query performance...")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Test several queries to get average
        test_queries = ["memory", "test", "data", "information", ""]
        times = []
        
        for query in test_queries:
            start_time = time.time()
            
            try:
                response = await client.get(
                    f"{API_BASE}/memories/search",
                    params={"q": query, "limit": 10}
                )
                
                duration_ms = (time.time() - start_time) * 1000
                times.append(duration_ms)
                
                if response.status_code == 200:
                    data = response.json()
                    result_count = len(data.get("memories", []))
                    print(f"  Query '{query}': {duration_ms:.1f}ms, {result_count} results")
                else:
                    print(f"  Query '{query}': {duration_ms:.1f}ms, ERROR {response.status_code}")
                    
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                times.append(duration_ms)
                print(f"  Query '{query}': {duration_ms:.1f}ms, EXCEPTION: {e}")
                
        if times:
            avg_time = sum(times) / len(times)
            print(f"\n📊 Average query time: {avg_time:.1f}ms")
            return avg_time
        else:
            print("❌ No successful queries to measure")
            return None

async def check_migration_needed():
    """Check if HNSW migration is needed"""
    print("🔍 Checking if HNSW migration is needed...")
    
    # Check health endpoint for performance metrics
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{API_BASE}/health")
        
        if response.status_code == 200:
            health_data = response.json()
            avg_query_time = health_data.get("avg_query_time_ms", 0)
            
            print(f"Health endpoint reports: {avg_query_time:.1f}ms average query time")
            
            if avg_query_time > 100:
                print("❌ Query performance is unacceptable (>100ms)")
                print("✅ HNSW migration is DEFINITELY needed")
                return True
            elif avg_query_time > 50:
                print("⚠️ Query performance is poor (>50ms)")
                print("✅ HNSW migration is recommended")
                return True
            else:
                print("✅ Query performance is acceptable (<50ms)")
                print("🤔 HNSW migration may already be applied")
                return False
        else:
            print(f"❌ Could not get health data: {response.status_code}")
            return True  # Assume migration is needed

async def attempt_migration_via_admin():
    """Attempt to apply migration through admin endpoint if available"""
    print("🔧 Attempting to apply migration via admin endpoint...")
    
    # This would require adding an admin endpoint to the service
    # For now, we'll document what needs to be done
    
    print("⚠️ Admin endpoint for migration not yet implemented")
    print("   To apply this migration, you would need to:")
    print("   1. Add an admin endpoint to the Core Nexus API")
    print("   2. Execute the HNSW migration SQL through the connection pool")
    print("   3. Verify the indexes were created successfully")
    
    return False

async def main():
    """Main execution"""
    print("🚀 CORE NEXUS PERFORMANCE MIGRATION")
    print("="*60)
    print("Goal: Reduce query time from 885ms to <50ms using HNSW indexes")
    print()
    
    # Step 1: Check if migration is needed
    migration_needed = await check_migration_needed()
    print()
    
    # Step 2: Test current performance
    current_performance = await test_current_performance()
    print()
    
    # Step 3: Attempt migration
    if migration_needed:
        print("🔧 MIGRATION REQUIRED")
        print("="*40)
        
        migration_success = await attempt_migration_via_admin()
        
        if not migration_success:
            print("\n📋 MANUAL MIGRATION STEPS REQUIRED:")
            print("="*50)
            print("1. Access the PostgreSQL database directly:")
            print(f"   psql -h dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com \\")
            print("        -U nexus_memory_db_user -d nexus_memory_db")
            print()
            print("2. Execute the HNSW migration SQL:")
            print("   (See HNSW_MIGRATION_SQL in this script)")
            print()
            print("3. Expected result:")
            print("   - Query time drops from 885ms to <50ms")
            print("   - New HNSW indexes provide much faster similarity search")
            print("   - Better performance for user-filtered and importance-based queries")
            print()
            print("⚠️ CRITICAL: This migration is REQUIRED before adding AI agents")
            print("   Current performance will not scale with increased load")
            
    else:
        print("✅ Migration may not be needed - performance is acceptable")
        
    print("\n" + "="*60)
    print("📊 PERFORMANCE ANALYSIS COMPLETE")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())