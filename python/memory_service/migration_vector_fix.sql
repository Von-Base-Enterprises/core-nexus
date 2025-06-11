-- =====================================================
-- PRODUCTION-SAFE VECTOR TABLE MIGRATION SCRIPT
-- Migrates from partitioned to non-partitioned structure
-- 
-- IMPORTANT: This migration is designed for zero data loss
-- and includes verification steps and rollback procedures
-- =====================================================

-- Start transaction for atomicity
BEGIN;

-- Set appropriate lock timeout to prevent long waits
SET lock_timeout = '10s';
SET statement_timeout = '30min';  -- Allow enough time for large data migrations

-- =====================================================
-- STEP 1: Pre-migration verification
-- =====================================================

-- Check current state and record it
DO $$
DECLARE
    partition_count INTEGER;
    total_records INTEGER;
    has_embeddings INTEGER;
BEGIN
    -- Count partitions
    SELECT COUNT(*) INTO partition_count
    FROM pg_tables 
    WHERE tablename LIKE 'vector_memories_%' 
    AND schemaname = 'public';
    
    -- Count total records
    SELECT COUNT(*) INTO total_records 
    FROM vector_memories;
    
    -- Count records with embeddings
    SELECT COUNT(*) INTO has_embeddings 
    FROM vector_memories 
    WHERE embedding IS NOT NULL;
    
    RAISE NOTICE 'Pre-migration state:';
    RAISE NOTICE '  - Partitions: %', partition_count;
    RAISE NOTICE '  - Total records: %', total_records;
    RAISE NOTICE '  - Records with embeddings: %', has_embeddings;
    
    -- Store counts for verification
    INSERT INTO system_metrics (metric_name, metric_value, metadata)
    VALUES 
        ('migration_start_partitions', partition_count, '{"migration": "vector_fix"}'),
        ('migration_start_records', total_records, '{"migration": "vector_fix"}'),
        ('migration_start_embeddings', has_embeddings, '{"migration": "vector_fix"}');
END $$;

-- =====================================================
-- STEP 2: Create new non-partitioned table
-- =====================================================

-- Create new table with same structure but without partitioning
CREATE TABLE IF NOT EXISTS vector_memories_new (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    user_id TEXT,
    conversation_id TEXT,
    importance_score FLOAT DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT NOW(),
    last_accessed TIMESTAMP DEFAULT NOW(),
    access_count INTEGER DEFAULT 0
);

-- =====================================================
-- STEP 3: Copy all data from partitioned table
-- =====================================================

-- Copy data in batches to avoid memory issues
DO $$
DECLARE
    batch_size INTEGER := 10000;
    offset_val INTEGER := 0;
    rows_copied INTEGER;
    total_copied INTEGER := 0;
BEGIN
    LOOP
        -- Copy batch
        INSERT INTO vector_memories_new 
        SELECT * FROM vector_memories 
        ORDER BY created_at, id  -- Ensure consistent ordering
        LIMIT batch_size 
        OFFSET offset_val;
        
        GET DIAGNOSTICS rows_copied = ROW_COUNT;
        
        EXIT WHEN rows_copied = 0;
        
        total_copied := total_copied + rows_copied;
        offset_val := offset_val + batch_size;
        
        -- Progress reporting
        IF total_copied % 50000 = 0 THEN
            RAISE NOTICE 'Copied % records...', total_copied;
        END IF;
    END LOOP;
    
    RAISE NOTICE 'Total records copied: %', total_copied;
    
    -- Store count for verification
    INSERT INTO system_metrics (metric_name, metric_value, metadata)
    VALUES ('migration_copied_records', total_copied, '{"migration": "vector_fix"}');
END $$;

-- =====================================================
-- STEP 4: Verify data integrity
-- =====================================================

DO $$
DECLARE
    old_count INTEGER;
    new_count INTEGER;
    old_embeddings INTEGER;
    new_embeddings INTEGER;
    sample_match BOOLEAN;
BEGIN
    -- Compare counts
    SELECT COUNT(*) INTO old_count FROM vector_memories;
    SELECT COUNT(*) INTO new_count FROM vector_memories_new;
    
    SELECT COUNT(*) INTO old_embeddings FROM vector_memories WHERE embedding IS NOT NULL;
    SELECT COUNT(*) INTO new_embeddings FROM vector_memories_new WHERE embedding IS NOT NULL;
    
    -- Verify counts match
    IF old_count != new_count THEN
        RAISE EXCEPTION 'Record count mismatch! Old: %, New: %', old_count, new_count;
    END IF;
    
    IF old_embeddings != new_embeddings THEN
        RAISE EXCEPTION 'Embedding count mismatch! Old: %, New: %', old_embeddings, new_embeddings;
    END IF;
    
    -- Spot check some records
    SELECT EXISTS (
        SELECT 1 
        FROM vector_memories v1 
        JOIN vector_memories_new v2 ON v1.id = v2.id
        WHERE v1.content != v2.content 
        OR v1.embedding IS DISTINCT FROM v2.embedding
        OR v1.metadata::text != v2.metadata::text
        LIMIT 1
    ) INTO sample_match;
    
    IF sample_match THEN
        RAISE EXCEPTION 'Data integrity check failed! Some records do not match.';
    END IF;
    
    RAISE NOTICE 'Data integrity verified: % records migrated successfully', new_count;
END $$;

-- =====================================================
-- STEP 5: Create all necessary indexes
-- =====================================================

-- Create HNSW index for vector similarity (most important for query performance)
CREATE INDEX idx_vector_memories_new_embedding_hnsw 
    ON vector_memories_new USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Alternative: Create IVFFlat index (comment out HNSW above and use this if preferred)
-- CREATE INDEX idx_vector_memories_new_embedding_ivfflat
--     ON vector_memories_new USING ivfflat (embedding vector_cosine_ops)
--     WITH (lists = 100);

-- Create all other indexes
CREATE INDEX idx_vector_memories_new_user_id 
    ON vector_memories_new (user_id);
CREATE INDEX idx_vector_memories_new_conversation_id 
    ON vector_memories_new (conversation_id);
CREATE INDEX idx_vector_memories_new_importance 
    ON vector_memories_new (importance_score DESC);
CREATE INDEX idx_vector_memories_new_created_at 
    ON vector_memories_new (created_at DESC);
CREATE INDEX idx_vector_memories_new_last_accessed 
    ON vector_memories_new (last_accessed DESC);

-- Compound indexes for common query patterns
CREATE INDEX idx_vector_memories_new_user_time 
    ON vector_memories_new (user_id, created_at DESC);
CREATE INDEX idx_vector_memories_new_conversation_time 
    ON vector_memories_new (conversation_id, created_at DESC);

-- JSONB index for metadata queries
CREATE INDEX idx_vector_memories_new_metadata_gin 
    ON vector_memories_new USING gin (metadata);

-- Update table statistics
ANALYZE vector_memories_new;

-- =====================================================
-- STEP 6: Update foreign key references
-- =====================================================

-- Temporarily disable foreign key checks
SET session_replication_role = 'replica';

-- Update memory_evolution table reference
ALTER TABLE memory_evolution 
    DROP CONSTRAINT IF EXISTS memory_evolution_memory_id_fkey;

-- Update memory_entity_map table reference
ALTER TABLE memory_entity_map 
    DROP CONSTRAINT IF EXISTS memory_entity_map_memory_id_fkey;

-- Re-enable foreign key checks
SET session_replication_role = 'origin';

-- =====================================================
-- STEP 7: Perform the table swap
-- =====================================================

-- Rename tables
ALTER TABLE vector_memories RENAME TO vector_memories_old_partitioned;
ALTER TABLE vector_memories_new RENAME TO vector_memories;

-- Rename indexes to match expected names
ALTER INDEX idx_vector_memories_new_embedding_hnsw RENAME TO vector_memories_embedding_hnsw_idx;
ALTER INDEX idx_vector_memories_new_user_id RENAME TO vector_memories_user_id_idx;
ALTER INDEX idx_vector_memories_new_conversation_id RENAME TO vector_memories_conversation_id_idx;
ALTER INDEX idx_vector_memories_new_importance RENAME TO vector_memories_importance_idx;
ALTER INDEX idx_vector_memories_new_created_at RENAME TO vector_memories_created_at_idx;
ALTER INDEX idx_vector_memories_new_last_accessed RENAME TO vector_memories_last_accessed_idx;
ALTER INDEX idx_vector_memories_new_user_time RENAME TO vector_memories_user_time_idx;
ALTER INDEX idx_vector_memories_new_conversation_time RENAME TO vector_memories_conversation_time_idx;
ALTER INDEX idx_vector_memories_new_metadata_gin RENAME TO vector_memories_metadata_gin_idx;

-- =====================================================
-- STEP 8: Re-establish foreign key constraints
-- =====================================================

ALTER TABLE memory_evolution 
    ADD CONSTRAINT memory_evolution_memory_id_fkey 
    FOREIGN KEY (memory_id) REFERENCES vector_memories(id) ON DELETE CASCADE;

ALTER TABLE memory_entity_map 
    ADD CONSTRAINT memory_entity_map_memory_id_fkey 
    FOREIGN KEY (memory_id) REFERENCES vector_memories(id) ON DELETE CASCADE;

-- =====================================================
-- STEP 9: Final verification
-- =====================================================

DO $$
DECLARE
    final_count INTEGER;
    index_count INTEGER;
    can_query BOOLEAN;
BEGIN
    -- Verify record count
    SELECT COUNT(*) INTO final_count FROM vector_memories;
    RAISE NOTICE 'Final record count: %', final_count;
    
    -- Verify indexes exist
    SELECT COUNT(*) INTO index_count 
    FROM pg_indexes 
    WHERE tablename = 'vector_memories';
    RAISE NOTICE 'Indexes created: %', index_count;
    
    -- Test a simple query
    BEGIN
        PERFORM * FROM vector_memories LIMIT 1;
        can_query := TRUE;
    EXCEPTION WHEN OTHERS THEN
        can_query := FALSE;
    END;
    
    IF NOT can_query THEN
        RAISE EXCEPTION 'Cannot query new table!';
    END IF;
    
    RAISE NOTICE 'Migration completed successfully!';
    
    -- Record success
    INSERT INTO system_metrics (metric_name, metric_value, metadata)
    VALUES ('migration_completed', 1, '{"migration": "vector_fix", "final_count": ' || final_count || '}');
END $$;

-- =====================================================
-- COMMIT THE TRANSACTION
-- =====================================================

COMMIT;

-- =====================================================
-- POST-MIGRATION CLEANUP (Run separately after verification)
-- =====================================================

-- After confirming the migration is successful, run these commands:
/*
-- Drop old partitioned table and all partitions
DROP TABLE IF EXISTS vector_memories_old_partitioned CASCADE;

-- Update any views that might reference the old structure
DROP VIEW IF EXISTS memory_performance_summary CASCADE;
DROP VIEW IF EXISTS top_accessed_memories CASCADE;

-- Recreate views with new table
CREATE OR REPLACE VIEW memory_performance_summary AS
SELECT 
    DATE(created_at) as date,
    COUNT(*) as memories_created,
    AVG(importance_score) as avg_importance,
    COUNT(DISTINCT user_id) as active_users,
    COUNT(DISTINCT conversation_id) as active_conversations
FROM vector_memories 
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;

CREATE OR REPLACE VIEW top_accessed_memories AS
SELECT 
    id,
    content,
    access_count,
    importance_score,
    last_accessed,
    user_id
FROM vector_memories 
WHERE access_count > 0
ORDER BY access_count DESC, importance_score DESC
LIMIT 100;

-- Vacuum to reclaim space
VACUUM FULL ANALYZE vector_memories;
*/

-- =====================================================
-- ROLLBACK PROCEDURE (If needed)
-- =====================================================

/*
-- If something goes wrong and you need to rollback:

BEGIN;

-- Rename tables back
ALTER TABLE vector_memories RENAME TO vector_memories_failed;
ALTER TABLE vector_memories_old_partitioned RENAME TO vector_memories;

-- Restore foreign key constraints
ALTER TABLE memory_evolution 
    DROP CONSTRAINT IF EXISTS memory_evolution_memory_id_fkey;
ALTER TABLE memory_evolution 
    ADD CONSTRAINT memory_evolution_memory_id_fkey 
    FOREIGN KEY (memory_id) REFERENCES vector_memories(id) ON DELETE CASCADE;

ALTER TABLE memory_entity_map 
    DROP CONSTRAINT IF EXISTS memory_entity_map_memory_id_fkey;
ALTER TABLE memory_entity_map 
    ADD CONSTRAINT memory_entity_map_memory_id_fkey 
    FOREIGN KEY (memory_id) REFERENCES vector_memories(id) ON DELETE CASCADE;

-- Drop failed migration table
DROP TABLE IF EXISTS vector_memories_failed CASCADE;

COMMIT;
*/

-- =====================================================
-- PERFORMANCE TESTING QUERIES
-- =====================================================

/*
-- After migration, test these queries to ensure performance:

-- 1. Test vector similarity search
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, content, 1 - (embedding <=> embedding) as similarity
FROM vector_memories
WHERE embedding IS NOT NULL
ORDER BY embedding <=> embedding
LIMIT 10;

-- 2. Test metadata filtering
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM vector_memories
WHERE metadata @> '{"type": "important"}'
LIMIT 10;

-- 3. Test user-based queries
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM vector_memories
WHERE user_id = 'test_user'
ORDER BY created_at DESC
LIMIT 20;

-- 4. Verify index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename = 'vector_memories'
ORDER BY idx_scan DESC;
*/