-- Migration 003: Fix table name mismatch
-- The provider defaults to 'memories' but config specifies 'vector_memories'
-- This creates indexes on the correct table

BEGIN;

-- Log migration start
DO $$
BEGIN
    RAISE NOTICE 'Fixing table name mismatch...';
    
    -- Check which table has data
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'memories') THEN
        RAISE NOTICE 'Found memories table';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'vector_memories') THEN
        RAISE NOTICE 'Found vector_memories table';
    END IF;
END $$;

-- Drop indexes from wrong table if they exist
DROP INDEX IF EXISTS idx_memories_embedding_hnsw;
DROP INDEX IF EXISTS idx_memories_user_created;
DROP INDEX IF EXISTS idx_memories_importance_created;

-- Create HNSW index on the correct table (vector_memories)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_vector_memories_embedding_hnsw 
ON vector_memories 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Create composite indexes on the correct table
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_vector_memories_user_created 
ON vector_memories (user_id, created_at DESC)
WHERE user_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_vector_memories_importance_created
ON vector_memories (importance_score DESC, created_at DESC);

-- Update statistics
ANALYZE vector_memories;

-- Verify indexes were created
DO $$
DECLARE
    index_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes 
    WHERE tablename = 'vector_memories' 
    AND indexname LIKE '%hnsw%';
    
    IF index_count > 0 THEN
        RAISE NOTICE 'HNSW index created successfully on vector_memories table';
    ELSE
        RAISE EXCEPTION 'Failed to create HNSW index on vector_memories';
    END IF;
END $$;

-- Record migration
INSERT INTO schema_migrations (version, applied_at) 
VALUES ('003_fix_table_name_mismatch', NOW())
ON CONFLICT (version) DO NOTHING;

COMMIT;