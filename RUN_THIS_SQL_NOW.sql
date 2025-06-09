-- THE CODE IS FIXED! NOW CREATE THE INDEX TO MAKE QUERIES WORK
-- Run this IMMEDIATELY in your PostgreSQL database

-- This is the ONLY thing preventing queries from working now!

CREATE INDEX IF NOT EXISTS idx_vector_memories_embedding 
ON vector_memories 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Also run these for better performance:
CREATE INDEX IF NOT EXISTS idx_vector_memories_metadata 
ON vector_memories USING GIN (metadata);

CREATE INDEX IF NOT EXISTS idx_vector_memories_importance 
ON vector_memories (importance_score DESC);

ANALYZE vector_memories;

-- Test it worked:
SELECT COUNT(*) as total_memories FROM vector_memories;

-- Once you run this, queries will immediately start returning results!