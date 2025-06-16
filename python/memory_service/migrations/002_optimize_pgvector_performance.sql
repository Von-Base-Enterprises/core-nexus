-- Migration 002: Optimize pgvector performance with HNSW index
-- This migration upgrades from ivfflat to HNSW index for better query performance
-- Current production average: 919ms -> Expected after migration: <50ms

BEGIN;

-- Log migration start
DO $$
BEGIN
    RAISE NOTICE 'Starting pgvector performance optimization migration...';
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
    
    IF NOT hnsw_exists THEN
        RAISE EXCEPTION 'HNSW index creation failed';
    END IF;
    
    IF NOT composite_exists THEN
        RAISE WARNING 'Composite index creation failed - queries with user filters may be slower';
    END IF;
    
    RAISE NOTICE 'Migration completed successfully. HNSW index is active.';
END $$;

-- Record migration completion
INSERT INTO schema_migrations (version, applied_at) 
VALUES ('002_optimize_pgvector_performance', NOW())
ON CONFLICT (version) DO NOTHING;

COMMIT;