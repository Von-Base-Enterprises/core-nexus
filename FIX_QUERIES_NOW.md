# 🚨 EMERGENCY FIX: Queries Returning Empty Results

## Quick Fix Steps (Do This NOW)

### Step 1: Get Your Database Connection

1. Go to Render Dashboard
2. Click on your PostgreSQL database
3. Find "PSQL Command" and copy it
4. It looks like: `psql postgresql://user:password@host:5432/database`

### Step 2: Connect and Run Fix

```bash
# 1. Paste your PSQL command in terminal
psql postgresql://nexus_memory_db_user:YOUR_PASSWORD@dpg-YOUR_ID.oregon-postgres.render.com:5432/nexus_memory_db

# 2. Once connected, check current state
\dt vector_memories;
SELECT COUNT(*) FROM vector_memories;

# 3. Create the missing index (THIS IS THE FIX)
CREATE INDEX IF NOT EXISTS idx_vector_memories_embedding 
ON vector_memories 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

# 4. Also create metadata index
CREATE INDEX IF NOT EXISTS idx_vector_memories_metadata 
ON vector_memories 
USING GIN (metadata);

# 5. Update statistics
ANALYZE vector_memories;

# 6. Exit
\q
```

### Step 3: Test It Works

```bash
# Test query endpoint (should return results now!)
curl -X POST https://core-nexus-memory-service.onrender.com/memories/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "limit": 5}' | jq
```

## Alternative: Run Full Fix Script

If you want to run all optimizations at once:

```bash
# 1. Save this SQL locally
cat > fix_queries.sql << 'EOF'
-- Emergency fix for pgvector queries
CREATE EXTENSION IF NOT EXISTS vector;

-- Main fix: Create vector index
CREATE INDEX IF NOT EXISTS idx_vector_memories_embedding 
ON vector_memories 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Supporting indexes
CREATE INDEX IF NOT EXISTS idx_vector_memories_metadata 
ON vector_memories USING GIN (metadata);

CREATE INDEX IF NOT EXISTS idx_vector_memories_importance 
ON vector_memories (importance_score DESC);

-- Update statistics
ANALYZE vector_memories;

-- Verify it worked
SELECT COUNT(*) as total_memories FROM vector_memories;
SELECT indexname FROM pg_indexes WHERE tablename = 'vector_memories';
EOF

# 2. Run it
psql YOUR_CONNECTION_STRING < fix_queries.sql
```

## Expected Result

Before fix:
```json
{
  "memories": [],
  "total_found": 0
}
```

After fix:
```json
{
  "memories": [
    {
      "id": "...",
      "content": "...",
      "similarity_score": 0.89
    }
  ],
  "total_found": 245
}
```

## If Still Not Working

Check these:
1. Is pgvector extension installed? `CREATE EXTENSION IF NOT EXISTS vector;`
2. Are there actually memories? `SELECT COUNT(*) FROM vector_memories;`
3. Check for errors: `SELECT * FROM vector_memories LIMIT 1;`

---
**This should fix it in 5 minutes!**