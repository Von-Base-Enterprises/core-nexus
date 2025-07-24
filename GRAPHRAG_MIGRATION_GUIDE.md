# GraphRAG Migration Guide - Production

## Current Status (July 21, 2025)

GraphRAG infrastructure is **fully operational** but needs migration to connect existing memories to entities.

### What's Working ✅
- Entity extraction from new memories
- Relationship detection between entities
- Graph traversal queries
- 161 entities and 41 relationships already in graph

### What Needs Migration ❌
- Memory-entity mappings for existing memories
- The `memory_entity_map` table is empty
- Entities exist but aren't linked to their source memories

## Migration Steps

### 1. Set Production Credentials

```bash
# Get these from Render dashboard
export PGVECTOR_HOST=<your-render-postgres-host>
export PGVECTOR_PORT=5432
export PGVECTOR_DATABASE=nexus_memory_db
export PGVECTOR_USER=nexus_memory_db_user
export PGVECTOR_PASSWORD=<your-postgres-password>
```

### 2. Run the Migration

```bash
# From the core-nexus directory
./run_production_migration.sh
```

The migration will:
- Process all existing memories in batches
- Extract entities from each memory's content
- Create proper memory-entity mappings
- Link the 161 existing entities to their source memories

### 3. Verify Success

```bash
# Test that GraphRAG is fully working
python3 test_graphrag_production.py
```

Expected results:
- Von Base Enterprises: Should show 20+ connected memories
- Core Nexus: Should show 10+ connected memories
- Multi-hop queries: Should return connected entities

### 4. Monitor Performance

After migration, check:
- API response times (should remain under 200ms)
- Memory usage (migration adds minimal overhead)
- Graph query performance (optimized indexes in place)

## What the Migration Does

1. **Scans all memories** in `vector_memories` table
2. **Extracts entities** using simple pattern matching (same as GraphProvider)
3. **Creates mappings** in `memory_entity_map` table
4. **Updates mention counts** for existing entities
5. **Verifies results** with sample queries

## Safety Features

- Non-destructive: Only adds mappings, doesn't modify existing data
- Idempotent: Can be run multiple times safely (ON CONFLICT DO NOTHING)
- Batched processing: Prevents memory overload
- Progress logging: Shows status every 10 memories

## Troubleshooting

### If migration fails:
1. Check database credentials
2. Verify network connectivity to Render
3. Check logs for specific errors

### If entities still show 0 memories:
1. Verify migration completed without errors
2. Check `memory_entity_map` table has entries
3. Run verification script again

### Performance issues:
1. Migration processes 100 memories at a time
2. Total time depends on number of memories
3. Can be interrupted and resumed safely

## Post-Migration Benefits

Once migration is complete, Core Nexus will support:

1. **Entity Exploration**: `/graph/explore/{entity}` returns all related memories
2. **Multi-hop Reasoning**: Traverse relationships to find connected information
3. **Knowledge Graph Queries**: Complex queries across entity relationships
4. **Enhanced Search**: Graph context improves semantic search results

## Next Steps After Migration

1. Test multi-hop queries with real use cases
2. Monitor graph growth as new memories are added
3. Consider adding more sophisticated entity extraction
4. Explore graph visualization options