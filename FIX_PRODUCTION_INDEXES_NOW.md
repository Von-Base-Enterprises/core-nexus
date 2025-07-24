# 🚨 URGENT: Fix Production Query Performance

## The Issue
Production queries are taking 755ms average (should be <100ms) because pgvector indexes are missing.

## Quick Fix (5 minutes)

### Step 1: Get Database Connection
1. Go to https://dashboard.render.com/
2. Click on **core-nexus-memory-service**
3. Go to **Environment** tab
4. Find **DATABASE_URL** and click the eye icon to reveal it
5. Copy the entire connection string

### Step 2: Connect to Database
```bash
# In your terminal, paste the DATABASE_URL you copied:
export DATABASE_URL="postgresql://nexus_memory_db_user:YOUR_PASSWORD@dpg-XXX.oregon-postgres.render.com:5432/nexus_memory_db"

# Connect to the database
psql $DATABASE_URL
```

### Step 3: Create Indexes (Copy & Paste This)
```sql
-- Create pgvector indexes to fix performance
CREATE INDEX IF NOT EXISTS idx_vector_memories_embedding 
ON vector_memories 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_vector_memories_metadata 
ON vector_memories 
USING GIN (metadata);

CREATE INDEX IF NOT EXISTS idx_vector_memories_importance 
ON vector_memories (importance_score DESC);

CREATE INDEX IF NOT EXISTS idx_vector_memories_created_importance 
ON vector_memories (created_at DESC, importance_score DESC);

-- Update statistics
ANALYZE vector_memories;

-- Verify indexes were created
\di vector_memories

-- Exit
\q
```

### Step 4: Verify Performance
```bash
# Test query performance
python3 python/memory_service/test_query_fix.py
```

## Expected Results
- Query times should drop from 755ms to <100ms
- Empty queries: ~50ms
- Vector searches: ~80-100ms

## Why This Happened
The automated index creation in the startup script may have failed due to timing or permissions. This manual fix ensures the indexes are created properly.

## Long-term Fix
The `scripts/startup.sh` already includes index creation, but we may need to:
1. Add better error handling
2. Add retry logic
3. Ensure proper permissions

---
**Time Required**: 5 minutes
**Impact**: 7-10x performance improvement
**Risk**: None (indexes are non-destructive)