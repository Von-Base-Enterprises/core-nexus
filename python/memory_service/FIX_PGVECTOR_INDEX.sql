-- URGENT FIX: Increase maintenance_work_mem and create the index

-- Connect to the database using the external URL:
-- psql postgresql://nexus_memory_db_user:2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V@dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com/nexus_memory_db

-- Step 1: Temporarily increase maintenance_work_mem for this session
SET maintenance_work_mem = '128MB';

-- Step 2: Create the missing index
CREATE INDEX IF NOT EXISTS idx_vector_memories_embedding 
ON vector_memories 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Step 3: Verify the index was created
\di idx_vector_memories_embedding

-- Step 4: Test that vector queries work
SELECT COUNT(*) FROM vector_memories;

-- Optional: For a permanent fix, the database admin should increase maintenance_work_mem globally:
-- ALTER SYSTEM SET maintenance_work_mem = '128MB';
-- SELECT pg_reload_conf();