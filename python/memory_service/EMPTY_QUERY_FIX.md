# Empty Query Fix for Memory Service

## Problem Description

Users reported that memories were appearing "lost" when using empty queries to retrieve all memories. The issue was caused by the pgvector extension's handling of zero vectors in similarity calculations, which would return no results even when memories existed in the database.

## Root Cause

When an empty query was submitted:
1. The system generated a zero vector `[0.0] * 1536` for the embedding
2. This zero vector was used in pgvector's cosine similarity calculation
3. The cosine similarity between any vector and a zero vector is undefined/NaN
4. This caused pgvector to return no results, making memories appear lost

## Solution Implemented

### 1. Added `get_recent_memories` method to PgVectorProvider

A new method was added that bypasses vector similarity entirely for empty queries:

```python
async def get_recent_memories(self, limit: int, filters: dict[str, Any] | None = None) -> list[MemoryResponse]:
    """
    Get recent memories without vector similarity search.
    
    This method bypasses the vector similarity calculation entirely,
    returning memories ordered by creation date (newest first).
    Perfect for "get all" queries where relevance isn't needed.
    """
```

This method:
- Queries the database directly without vector operations
- Returns memories ordered by creation date (newest first)
- Supports metadata filtering
- Sets similarity_score to 1.0 since no similarity is calculated

### 2. Modified UnifiedVectorStore to use the new method

The `_query_provider` method was updated to detect empty queries and route them appropriately:

```python
async def _query_provider(self, provider: VectorProvider, query_embedding: list[float],
                         request: QueryRequest) -> list[MemoryResponse]:
    """Query a single provider."""
    # Check if this is an empty query (zero vector)
    if all(v == 0.0 for v in query_embedding):
        # Use get_recent_memories if available (currently only PgVectorProvider)
        if hasattr(provider, 'get_recent_memories'):
            logger.info(f"Using get_recent_memories for empty query on {provider.name}")
            return await provider.get_recent_memories(request.limit * 2, request.filters)
    
    # Otherwise use regular vector similarity query
    return await provider.query(query_embedding, request.limit * 2, request.filters)
```

## Files Modified

1. `/mnt/c/Users/Tyvon/core-nexus/python/memory_service/src/memory_service/providers.py`
   - Added `get_recent_memories` method to PgVectorProvider class

2. `/mnt/c/Users/Tyvon/core-nexus/python/memory_service/src/memory_service/unified_store.py`
   - Modified `_query_provider` to detect and handle empty queries

## Testing

Two test scripts were created:

1. `test_get_recent_memories.py` - Tests the new method directly
2. `verify_empty_query_fix.py` - Comprehensive verification of the fix

## Deployment Notes

This fix:
- Is backward compatible
- Requires no database changes
- Improves performance for "get all" queries by avoiding unnecessary vector calculations
- Only affects pgvector provider (ChromaDB and Pinecone continue using their existing logic)

## User Impact

Users will now be able to:
- Retrieve all memories using empty queries
- See memories ordered by creation date (newest first)
- Experience faster "get all" queries since vector similarity is bypassed
- Continue using search queries normally with vector similarity

## Future Improvements

Consider adding:
1. Similar optimization for ChromaDB and Pinecone providers
2. Pagination support for large result sets
3. Additional sorting options (by importance, by date range, etc.)