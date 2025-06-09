-- EMERGENCY FIX FOR EMPTY QUERY RESULTS
-- Run this immediately in production to fix queries

-- 1. Ensure vector extension is enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. THIS IS THE MAIN FIX - Create the vector similarity index
-- Without this index, queries return empty results!
DROP INDEX IF EXISTS idx_vector_memories_embedding;
CREATE INDEX idx_vector_memories_embedding 
ON vector_memories 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- 3. Create supporting indexes
CREATE INDEX IF NOT EXISTS idx_vector_memories_metadata 
ON vector_memories USING GIN (metadata);

CREATE INDEX IF NOT EXISTS idx_vector_memories_importance 
ON vector_memories (importance_score DESC);

-- 4. Force statistics update
ANALYZE vector_memories;
VACUUM ANALYZE vector_memories;

-- 5. Verify the fix
SELECT 
    'Total memories:' as metric, 
    COUNT(*)::text as value 
FROM vector_memories
UNION ALL
SELECT 
    'Indexes created:' as metric,
    COUNT(*)::text as value
FROM pg_indexes 
WHERE tablename = 'vector_memories'
UNION ALL
SELECT
    'Vector index exists:' as metric,
    CASE WHEN EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'vector_memories' 
        AND indexname = 'idx_vector_memories_embedding'
    ) THEN 'YES - Queries should work now!' 
    ELSE 'NO - Index creation failed!' 
    END as value;