# GraphRAG Fix Deployment Guide

## Overview

This deployment fixes the critical issue preventing GraphRAG queries from returning results. The root cause was that GraphProvider was generating new memory IDs instead of using the ones from the primary provider (PgVectorProvider), breaking the link between entities and memories.

## Changes Made

### 1. **VectorProvider Interface Update**
- Added optional `memory_id` parameter to the `store()` method
- All providers now accept and use provided memory IDs

### 2. **Provider Implementations Updated**
- **PgVectorProvider**: Uses provided memory_id or generates new
- **ChromaProvider**: Same pattern
- **GraphProvider**: MUST use provided memory_id, throws error if not provided

### 3. **UnifiedVectorStore Fix**
- `_replicate_to_secondaries()` now passes memory_id to secondary providers
- Ensures consistent IDs across all providers

### 4. **Graph Query Endpoint Implementation**
- Properly returns nodes and relationships
- Case-insensitive entity type matching
- Direct SQL queries for better performance

### 5. **Migration Script**
- `migrate_graph_entities.py` to fix existing memories
- Extracts entities and creates proper mappings
- Safe to run multiple times

## Deployment Steps

### Step 1: Deploy Code Changes

```bash
# Add and commit all changes
git add -A
git commit -m "Fix GraphRAG memory-entity mapping issue

- Update VectorProvider interface to accept optional memory_id
- Fix GraphProvider to use provided memory_id from primary provider
- Implement proper graph query endpoint with case-insensitive matching
- Add migration script for existing memories

This fixes the issue where graph queries returned empty results because
entities were linked to non-existent memory IDs."

# Push to trigger auto-deployment
git push origin main
```

### Step 2: Verify Deployment (After ~5 minutes)

```bash
# Test that the fix is deployed
python test_graphrag_fixes.py
```

Change the API_URL in the test script to production URL:
```python
API_URL = "https://core-nexus-memory-service.onrender.com"
```

### Step 3: Run Migration on Production

After verifying the deployment works for NEW memories, run the migration to fix EXISTING memories:

```bash
# Set production environment variables
export PGVECTOR_HOST=<production_host>
export PGVECTOR_DATABASE=<production_db>
export PGVECTOR_USER=<production_user>
export PGVECTOR_PASSWORD=<production_password>

# Run migration
python migrate_graph_entities.py
```

### Step 4: Verify GraphRAG is Fully Functional

```bash
# Test comprehensive GraphRAG functionality
python test_graphrag_complete.py
```

## Expected Results

After deployment:

1. ✅ New memories will have proper entity-memory mappings
2. ✅ Graph queries will return actual nodes and relationships
3. ✅ Entity exploration will show connected memories
4. ✅ Case-insensitive entity type queries will work
5. ✅ After migration, existing entities will be properly linked

## Monitoring

Watch for:
- Graph query response times
- Entity extraction success rate
- Memory-entity mapping creation
- Any errors in logs related to GraphProvider

## Rollback Plan

If issues occur:
1. The changes are backward compatible
2. Primary storage (PgVectorProvider) is unaffected
3. Can disable GraphProvider by setting GRAPH_ENABLED=false
4. No data loss risk - only graph enhancements affected

## Success Metrics

- Graph queries return non-empty results
- Entity exploration shows connected memories
- `/graph/stats` shows growing entity and relationship counts
- Multi-hop queries can traverse entity relationships