# URGENT: Fix pgvector in Production

## THE PROBLEM
- Database has 1,018 memories and is working perfectly
- But pgvector provider is DISABLED in the API
- This is why queries return 0 memories

## IMMEDIATE ACTION - Add These Environment Variables in Render Dashboard:

```bash
# CRITICAL - ADD THIS ONE (the code checks for PGPASSWORD)
PGPASSWORD=2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V

# These are already set correctly:
PGVECTOR_HOST=dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com
PGVECTOR_PORT=5432
PGVECTOR_DATABASE=nexus_memory_db
PGVECTOR_USER=nexus_memory_db_user
PGVECTOR_PASSWORD=2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V

# Also ensure these are set
DATABASE_URL=postgresql://nexus_memory_db_user:2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V@dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com/nexus_memory_db
ENABLE_PGVECTOR=true
```

## VERIFICATION STEPS:

1. Add the environment variables above in Render dashboard
2. Restart the service
3. Check health endpoint - pgvector should show "healthy"
4. Query memories - should return 1,018 memories

## TEST COMMANDS:

```bash
# Check health (pgvector should be "healthy" not "disabled")
curl https://core-nexus-memory-service.onrender.com/health

# Query all memories (should return 1,018)
curl -X POST https://core-nexus-memory-service.onrender.com/memories/query \
  -H "Content-Type: application/json" \
  -d '{"query": "", "limit": 1}'

# Search test memories
curl -X POST https://core-nexus-memory-service.onrender.com/memories/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Health check test", "limit": 5}'
```

## EXPECTED RESULTS:
- Health check shows pgvector: "healthy"
- Empty query returns total_found: 1018
- Search finds the test memories we created