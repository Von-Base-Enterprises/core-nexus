# 🚀 Run GraphRAG Migration NOW

## Quick Start (Copy-Paste Commands)

### Step 1: Get Your Database Password
1. Go to https://dashboard.render.com
2. Find your PostgreSQL database service
3. Copy the password from the connection info

### Step 2: Set Environment Variables
```bash
# Copy and paste this block, replacing YOUR_PASSWORD_HERE with your actual password
export PGVECTOR_HOST=dpg-d12n0np5pdvs73ctmm40-a
export PGVECTOR_PORT=5432
export PGVECTOR_DATABASE=nexus_memory_db
export PGVECTOR_USER=nexus_memory_db_user
export PGVECTOR_PASSWORD=YOUR_PASSWORD_HERE
```

### Step 3: Run Migration
```bash
# From core-nexus directory
cd /mnt/c/Users/Tyvon/Dev/core-nexus
./run_production_migration.sh
```

When prompted "Continue with migration? (y/n)", type `y` and press Enter.

### Step 4: Verify Success
```bash
# Test that it worked
python3 test_graphrag_production.py
```

## What to Expect

### During Migration:
- Progress updates every 10 memories
- Total time: ~2-5 minutes (depends on memory count)
- Final statistics showing:
  - Memories processed
  - New entities found
  - Mappings created

### After Migration:
- Von Base Enterprises: Should show 25+ memories (not 0)
- Core Nexus: Should show 20+ memories (not 0)
- Multi-hop queries: Will return connected entities

## If Something Goes Wrong

### Error: "PGVECTOR_PASSWORD not set"
→ You forgot to set the password in Step 2

### Error: "Connection refused"
→ Check the PGVECTOR_HOST is correct

### Migration runs but entities still show 0 memories
→ Check the migration output for errors
→ Run `python3 verify_graphrag_status.py` to diagnose

## Success Indicators

✅ Migration shows "Mappings created: 100+" 
✅ Test script shows "Entity has connected memories"
✅ Multi-hop queries return results

## Next Steps After Success

1. Try entity exploration: `/graph/explore/Von Base Enterprises`
2. Test multi-hop queries with your data
3. Monitor new memories being processed with GraphRAG

---

**Ready? Get your password from Render and run the commands above!**