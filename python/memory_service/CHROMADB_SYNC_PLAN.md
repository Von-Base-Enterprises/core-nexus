# 🚨 Emergency ChromaDB Sync Plan

## Critical Situation
- **pgvector**: 1,004 memories (primary storage)
- **ChromaDB**: 0 vectors (backup storage)
- **Risk**: Total data loss if pgvector fails

## 4-Step Emergency Sync Plan

### STEP 1: Install ChromaDB Dependencies (15 minutes)
```bash
cd python/memory_service
poetry add chromadb

# Or add to pyproject.toml:
# chromadb = "^0.4.0"
```

### STEP 2: Run Emergency Sync Script (30 minutes)
```bash
# Set environment variables
export PGVECTOR_PASSWORD="2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V"
export PGVECTOR_HOST="dpg-d12n0np5pdvs73ctmm40-a.ohio-postgres.render.com"
export PGVECTOR_DATABASE="nexus_memory_db"
export PGVECTOR_USER="nexus_memory_db_user"

# Run the sync
poetry run python emergency_chromadb_sync_v2.py
```

**Features:**
- Batch processing (100 memories at a time)
- Checkpoint system (resume if interrupted)
- Progress tracking
- Verification after sync

### STEP 3: Verify Sync Success (10 minutes)
```python
# Check ChromaDB has all vectors
import chromadb
client = chromadb.PersistentClient(path="./memory_service_chroma")
collection = client.get_collection("memories")
print(f"ChromaDB vectors: {collection.count()}")  # Should be 1,004
```

### STEP 4: Set Up Automatic Sync (45 minutes)

Create `auto_sync_service.py`:
```python
"""
Automatic sync service - runs every 5 minutes
Syncs new memories from pgvector to ChromaDB
"""

import asyncio
import asyncpg
import chromadb
from datetime import datetime, timedelta
import logging

class AutoSyncService:
    def __init__(self):
        self.last_sync = datetime.now()
        
    async def sync_new_memories(self):
        """Sync memories created since last sync"""
        # Connect to both databases
        pg_conn = await self.connect_postgres()
        chroma_collection = self.connect_chromadb()
        
        # Get new memories since last sync
        new_memories = await pg_conn.fetch("""
            SELECT * FROM vector_memories 
            WHERE created_at > $1
            ORDER BY created_at ASC
        """, self.last_sync)
        
        if new_memories:
            # Sync to ChromaDB
            self.sync_batch_to_chromadb(new_memories, chroma_collection)
            logging.info(f"Synced {len(new_memories)} new memories")
        
        self.last_sync = datetime.now()
        await pg_conn.close()
    
    async def run_forever(self):
        """Run sync every 5 minutes"""
        while True:
            try:
                await self.sync_new_memories()
            except Exception as e:
                logging.error(f"Sync failed: {e}")
            
            await asyncio.sleep(300)  # 5 minutes

# Run as a service
if __name__ == "__main__":
    service = AutoSyncService()
    asyncio.run(service.run_forever())
```

## Implementation Timeline

| Step | Time | Action |
|------|------|--------|
| 1 | 0-15 min | Install ChromaDB |
| 2 | 15-45 min | Run emergency sync |
| 3 | 45-55 min | Verify all vectors copied |
| 4 | 55-120 min | Set up automatic sync |

## Success Metrics

✅ ChromaDB has 1,004 vectors (matches pgvector)
✅ All memory embeddings preserved
✅ Automatic sync prevents future divergence
✅ Backup system fully operational

## Why This Matters

1. **Data Safety**: Currently all eggs in one basket (pgvector)
2. **Redundancy**: ChromaDB provides backup if pgvector fails
3. **Performance**: Can load-balance queries between systems
4. **Migration**: Easy to switch providers if needed

## Quick Alternative

If time is critical, use the existing sync scripts:
```bash
# Option 1: Direct sync
poetry run python quick_chromadb_sync.py

# Option 2: API-based sync  
poetry run python emergency_chromadb_sync.py

# Option 3: Full-featured sync
poetry run python chromadb_sync.py
```

All three scripts exist and can populate ChromaDB immediately!

---

**Priority**: 🔴 CRITICAL  
**Risk**: Total data loss if pgvector fails  
**Solution**: Run emergency sync NOW  
**Time Required**: 2 hours total