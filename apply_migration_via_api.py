#!/usr/bin/env python3
"""
Apply HNSW migration through the Core Nexus API
This uses the existing database connection pool for safe execution
"""

import asyncio
import json
import httpx
import time

API_BASE = "https://core-nexus-memory-service.onrender.com"

MIGRATION_ENDPOINT_CODE = '''
@app.post("/admin/migrate/hnsw-performance")
async def apply_hnsw_migration(
    admin_key: str = None,
    store: UnifiedVectorStore = Depends(get_store)
):
    """Apply HNSW performance migration to improve query speed"""
    # Simple admin check (you can implement proper auth later)
    if not admin_key:
        raise HTTPException(status_code=401, detail="Admin key required")
    
    try:
        # Get pgvector provider
        pgvector = store.providers.get('pgvector')
        if not pgvector or not pgvector.enabled:
            raise HTTPException(status_code=503, detail="pgvector not available")
        
        # Get connection pool
        pool = pgvector.connection_pool
        if not pool:
            raise HTTPException(status_code=503, detail="Database pool not available")
        
        migration_sql = """
        -- Migration 002: HNSW Performance Optimization
        BEGIN;
        
        -- Drop old indexes
        DROP INDEX IF EXISTS idx_vector_memories_embedding;
        DROP INDEX IF EXISTS idx_vector_memories_embedding_ivfflat;
        
        -- Create HNSW index
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
        
        -- Update statistics
        ANALYZE vector_memories;
        
        COMMIT;
        """
        
        async with pool.acquire() as conn:
            await conn.execute(migration_sql)
        
        return {
            "status": "success", 
            "message": "HNSW migration applied successfully",
            "expected_improvement": "Query time should drop from 885ms to <50ms"
        }
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")
'''

async def test_performance_before_after():
    """Test query performance before and after migration"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("📊 Testing query performance...")
        
        # Test query performance
        test_queries = [
            "",  # Empty query
            "memory",  # Simple query  
            "test data"  # Another query
        ]
        
        for query in test_queries:
            start_time = time.time()
            
            try:
                response = await client.get(
                    f"{API_BASE}/memories/search",
                    params={"q": query, "limit": 10}
                )
                
                duration = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    data = response.json()
                    result_count = len(data.get("memories", []))
                    print(f"  Query '{query}': {duration:.1f}ms, {result_count} results")
                else:
                    print(f"  Query '{query}': {duration:.1f}ms, ERROR {response.status_code}")
                    
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                print(f"  Query '{query}': {duration:.1f}ms, EXCEPTION: {e}")

async def check_current_indexes():
    """Check what indexes currently exist"""
    print("\n🔍 Checking current database indexes...")
    
    # This would require database access - for now just check API health
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{API_BASE}/health")
            if response.status_code == 200:
                data = response.json()
                pgvector_status = data.get("providers", {}).get("pgvector", {})
                print(f"PgVector status: {pgvector_status.get('status', 'unknown')}")
                total_vectors = pgvector_status.get("details", {}).get("details", {}).get("total_vectors", 0)
                print(f"Total vectors: {total_vectors}")
            else:
                print(f"Health check failed: {response.status_code}")
        except Exception as e:
            print(f"Health check error: {e}")

async def main():
    """Main execution"""
    print("🚀 Core Nexus HNSW Performance Migration")
    print("=" * 50)
    
    # Check current state
    await check_current_indexes()
    
    # Test current performance
    print("\n📊 Testing CURRENT performance...")
    await test_performance_before_after()
    
    print("\n" + "=" * 50)
    print("⚠️  MIGRATION READY")
    print("=" * 50)
    print("The migration script is prepared.")
    print("To apply the migration, you need to:")
    print("1. Add the migration endpoint to the API")
    print("2. Call the endpoint with admin credentials")
    print("3. Monitor the results")
    print("\nExpected improvement: 885ms → <50ms queries")

if __name__ == "__main__":
    asyncio.run(main())