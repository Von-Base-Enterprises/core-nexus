# CRITICAL FIX REQUIRED - pgvector Index Creation Failing

## Problem Identified
pgvector is disabled because the index creation is failing with:
```
ERROR: memory required is 61 MB, maintenance_work_mem is 16 MB
```

## Option 1: Quick Fix via SQL (Recommended)
Run these commands in your PostgreSQL client:

```sql
-- Connect to database
psql postgresql://nexus_memory_db_user:2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V@dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com/nexus_memory_db

-- Increase memory for this session
SET maintenance_work_mem = '128MB';

-- Create the index
CREATE INDEX IF NOT EXISTS idx_vector_memories_embedding 
ON vector_memories 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

## Option 2: Alternative Fix - Reduce Index Lists
If you can't increase memory, modify the API code to use fewer lists:

In `providers.py` line 295-298, change:
```python
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100)
```

To:
```python
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 10)
```

This will use less memory but may be slightly slower for queries.

## Option 3: Contact Render Support
Ask them to increase `maintenance_work_mem` to at least 64MB for your PostgreSQL instance.

## After Fixing
1. The index will be created successfully
2. Restart your Core Nexus service
3. pgvector will initialize properly
4. All 1,019 memories will be accessible

## Verification
After applying the fix and restarting:
```bash
curl https://core-nexus-memory-service.onrender.com/health | grep pgvector
# Should show: "pgvector":{"status":"healthy"

curl -X POST https://core-nexus-memory-service.onrender.com/memories/query \
  -H "Content-Type: application/json" \
  -d '{"query": "", "limit": 1}'
# Should show: "total_found": 1019
```