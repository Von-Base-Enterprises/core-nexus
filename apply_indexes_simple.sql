-- Core Nexus Production Index Fix
-- Run this to improve query performance from 755ms to <100ms

-- 1. Create IVFFlat index for vector similarity (THIS IS THE CRITICAL ONE)
CREATE INDEX IF NOT EXISTS idx_vector_memories_embedding 
ON vector_memories 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- 2. Create metadata index for filtering
CREATE INDEX IF NOT EXISTS idx_vector_memories_metadata 
ON vector_memories 
USING GIN (metadata);

-- 3. Create importance score index
CREATE INDEX IF NOT EXISTS idx_vector_memories_importance 
ON vector_memories (importance_score DESC);

-- 4. Create composite index for sorting
CREATE INDEX IF NOT EXISTS idx_vector_memories_created_importance 
ON vector_memories (created_at DESC, importance_score DESC);

-- 5. Update table statistics
ANALYZE vector_memories;

-- 6. Show all indexes (should see 4+ indexes)
SELECT 
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) as size
FROM pg_indexes 
WHERE tablename = 'vector_memories'
ORDER BY indexname;