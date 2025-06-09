# 🚨 IMMEDIATE FIX - Run ONE of these options:

## Option 1: PowerShell (Windows)
```powershell
# Run this in PowerShell
$env:PGPASSWORD = "2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V"
psql -h dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com -U nexus_memory_db_user nexus_memory_db -c "CREATE INDEX IF NOT EXISTS idx_vector_memories_embedding ON vector_memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);"
```

## Option 2: Command Prompt (Windows)
```cmd
set PGPASSWORD=2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V
psql -h dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com -U nexus_memory_db_user nexus_memory_db -c "CREATE INDEX IF NOT EXISTS idx_vector_memories_embedding ON vector_memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);"
```

## Option 3: Git Bash / WSL / Linux / Mac
```bash
PGPASSWORD=2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V psql -h dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com -U nexus_memory_db_user nexus_memory_db -c "CREATE INDEX IF NOT EXISTS idx_vector_memories_embedding ON vector_memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);"
```

## Option 4: Render Dashboard (Easiest!)
1. Go to: https://dashboard.render.com/
2. Click on your PostgreSQL database
3. Click "Connect" button
4. Choose "PSQL Shell"
5. Paste this SQL:
```sql
CREATE INDEX IF NOT EXISTS idx_vector_memories_embedding 
ON vector_memories 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);
```

## Option 5: Use a PostgreSQL GUI
Use any PostgreSQL client (pgAdmin, DBeaver, TablePlus, etc.) with:
- Host: dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com
- Port: 5432
- Database: nexus_memory_db
- Username: nexus_memory_db_user
- Password: 2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V

Then run the CREATE INDEX command.

## Verify It Worked
After running ANY of the above, test with PowerShell:
```powershell
Invoke-RestMethod -Uri "https://core-nexus-memory-service.onrender.com/memories/query" -Method Post -Headers @{"Content-Type"="application/json"} -Body '{"query":"test","limit":5}' | ConvertTo-Json
```

Or with curl:
```bash
curl -X POST https://core-nexus-memory-service.onrender.com/memories/query -H "Content-Type: application/json" -d '{"query":"test","limit":5}'
```

**The index creation takes less than 30 seconds and will fix queries IMMEDIATELY!**