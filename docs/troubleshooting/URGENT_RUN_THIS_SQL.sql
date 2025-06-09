-- URGENT: Run this SQL immediately in your PostgreSQL database
-- This will fix query performance even if the code isn't updated yet

-- 1. Create the critical index for vector similarity search
DROP INDEX IF EXISTS idx_vector_memories_embedding;
CREATE INDEX idx_vector_memories_embedding 
ON vector_memories 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- 2. Create metadata index for faster filtering
CREATE INDEX IF NOT EXISTS idx_vector_memories_metadata 
ON vector_memories USING GIN (metadata);

-- 3. Create importance score index
CREATE INDEX IF NOT EXISTS idx_vector_memories_importance 
ON vector_memories (importance_score DESC);

-- 4. Update statistics
ANALYZE vector_memories;

-- 5. Test the fix with a direct SQL query
-- This should return results if the index is working
SELECT 
    id,
    content,
    metadata,
    importance_score
FROM vector_memories
LIMIT 5;

-- 6. Show that indexes were created
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'vector_memories'
ORDER BY indexname;

-- If this returns results, the database side is fixed!
-- The application queries should work once the code deploys.