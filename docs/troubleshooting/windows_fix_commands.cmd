@echo off
REM Windows batch file to fix Core Nexus queries
echo.
echo ===== Core Nexus Query Fix for Windows =====
echo.

REM Set database connection variables
set PGHOST=dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com
set PGPORT=5432
set PGDATABASE=nexus_memory_db
set PGUSER=nexus_memory_db_user
set PGPASSWORD=2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V

echo Step 1: Testing current query status...
curl -X POST https://core-nexus-memory-service.onrender.com/memories/query -H "Content-Type: application/json" -d "{\"query\": \"test\", \"limit\": 5}"

echo.
echo Step 2: If you have psql installed, run this:
echo psql -h %PGHOST% -p %PGPORT% -U %PGUSER% -d %PGDATABASE%
echo.
echo Then paste this SQL:
echo CREATE INDEX IF NOT EXISTS idx_vector_memories_embedding ON vector_memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
echo.

echo Step 3: Test if it worked:
timeout /t 2 >nul
curl -X POST https://core-nexus-memory-service.onrender.com/memories/query -H "Content-Type: application/json" -d "{\"query\": \"test\", \"limit\": 5}"

pause