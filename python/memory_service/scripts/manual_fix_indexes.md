# Manual Index Creation for Production

## Quick Fix (Copy and Paste)

Connect to your production database and run these commands:

```sql
-- 1. Create IVFFlat index for vector similarity search
CREATE INDEX IF NOT EXISTS idx_vector_memories_embedding 
ON vector_memories 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- 2. Create GIN index for metadata filtering
CREATE INDEX IF NOT EXISTS idx_vector_memories_metadata 
ON vector_memories 
USING GIN (metadata);

-- 3. Create index for importance score sorting
CREATE INDEX IF NOT EXISTS idx_vector_memories_importance 
ON vector_memories (importance_score DESC);

-- 4. Create composite index for common query patterns
CREATE INDEX IF NOT EXISTS idx_vector_memories_created_importance 
ON vector_memories (created_at DESC, importance_score DESC);

-- 5. Update table statistics
ANALYZE vector_memories;

-- 6. Verify indexes were created
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'vector_memories'
ORDER BY indexname;
```

## Expected Output

You should see at least 4 indexes after running the commands:
- idx_vector_memories_embedding (IVFFlat index)
- idx_vector_memories_metadata (GIN index)
- idx_vector_memories_importance
- idx_vector_memories_created_importance

## Connection Command

```bash
# Replace with your actual connection details from Render dashboard
psql postgresql://nexus_memory_db_user:YOUR_PASSWORD@dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com:5432/nexus_memory_db
```

## Alternative: Run the fix script

```bash
# From the project root
psql $DATABASE_URL < python/memory_service/fix_pgvector_queries.sql
```