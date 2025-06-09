-- Core Nexus pgvector Query Performance Fix
-- This script fixes the empty query results issue and optimizes performance
-- Run this in production after connecting via PSQL

-- 1. Create proper indexes for vector similarity search
-- Using IVFFlat for better performance with cosine distance
CREATE INDEX IF NOT EXISTS idx_vector_memories_embedding 
ON vector_memories 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- 2. Create index on metadata for faster filtering
CREATE INDEX IF NOT EXISTS idx_vector_memories_metadata 
ON vector_memories 
USING GIN (metadata);

-- 3. Create index on importance score for ranking
CREATE INDEX IF NOT EXISTS idx_vector_memories_importance 
ON vector_memories (importance_score DESC);

-- 4. Create composite index for common query patterns
CREATE INDEX IF NOT EXISTS idx_vector_memories_created_importance 
ON vector_memories (created_at DESC, importance_score DESC);

-- 5. Update table statistics for query planner
ANALYZE vector_memories;

-- 6. Optimize PostgreSQL settings for vector operations
-- These need to be run by a superuser or configured in postgresql.conf
-- ALTER SYSTEM SET work_mem = '256MB';
-- ALTER SYSTEM SET maintenance_work_mem = '1GB';
-- ALTER SYSTEM SET max_parallel_workers_per_gather = 4;
-- ALTER SYSTEM SET effective_cache_size = '4GB';
-- SELECT pg_reload_conf();

-- 7. Verify indexes were created
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'vector_memories'
ORDER BY indexname;

-- 8. Check table statistics
SELECT 
    schemaname,
    tablename,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes,
    n_live_tup as live_tuples,
    n_dead_tup as dead_tuples,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE tablename = 'vector_memories';

-- 9. Test query performance
EXPLAIN (ANALYZE, BUFFERS) 
SELECT 
    id, 
    content, 
    1 - (embedding <=> '[0.1, 0.2, ...]'::vector) as similarity
FROM vector_memories
ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 10;

-- Note: Replace '[0.1, 0.2, ...]' with an actual 1536-dimension vector for testing