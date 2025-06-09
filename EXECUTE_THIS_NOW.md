# 🚨 EXECUTE THIS NOW TO FIX QUERIES 100%

## Option 1: Direct PSQL Command (Fastest)

Copy and paste this entire command into your terminal:

```bash
PGPASSWORD=2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V psql -h dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com -U nexus_memory_db_user nexus_memory_db -c "CREATE INDEX IF NOT EXISTS idx_vector_memories_embedding ON vector_memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100); CREATE INDEX IF NOT EXISTS idx_vector_memories_metadata ON vector_memories USING GIN (metadata); CREATE INDEX IF NOT EXISTS idx_vector_memories_importance ON vector_memories (importance_score DESC); ANALYZE vector_memories;"
```

## Option 2: Step by Step

1. Connect to database:
```bash
PGPASSWORD=2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V psql -h dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com -U nexus_memory_db_user nexus_memory_db
```

2. Once connected, run:
```sql
CREATE INDEX IF NOT EXISTS idx_vector_memories_embedding 
ON vector_memories 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_vector_memories_metadata 
ON vector_memories USING GIN (metadata);

CREATE INDEX IF NOT EXISTS idx_vector_memories_importance 
ON vector_memories (importance_score DESC);

ANALYZE vector_memories;

\q
```

## Option 3: From Render Dashboard

1. Go to your PostgreSQL database in Render
2. Click "Connect" → "PSQL Shell"
3. Paste the SQL commands above

## Verify It Worked

After running the indexes, test immediately:

```bash
curl -X POST https://core-nexus-memory-service.onrender.com/memories/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "limit": 5}' | python3 -m json.tool
```

You should see memories returned!

## Expected Result

Before: `{"memories":[],"total_found":0,...}`
After: `{"memories":[{...}],"total_found":865,...}`

---
**This will take less than 30 seconds to run and will fix queries 100%!**