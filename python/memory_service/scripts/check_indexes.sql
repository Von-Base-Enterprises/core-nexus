-- Check pgvector indexes on production database
-- Run this to verify indexes were created

-- 1. List all indexes on vector_memories table
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'vector_memories'
ORDER BY indexname;

-- 2. Check index usage statistics
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE tablename = 'vector_memories'
ORDER BY idx_scan DESC;

-- 3. Check table statistics
SELECT 
    n_live_tup as live_rows,
    n_dead_tup as dead_rows,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE tablename = 'vector_memories';

-- 4. Check if pgvector extension is installed
SELECT 
    extname,
    extversion
FROM pg_extension
WHERE extname = 'vector';

-- Expected output should show:
-- idx_vector_memories_embedding (IVFFlat index)
-- idx_vector_memories_metadata (GIN index)
-- idx_vector_memories_importance
-- idx_vector_memories_created_importance