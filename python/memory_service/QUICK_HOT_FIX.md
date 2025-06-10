# Quick Hot Fix for Empty Query Bug

If you need to deploy immediately and can't make the comprehensive changes, here's a one-line fix:

## Option 1: One-Line Fix (Quickest)

In `unified_store.py`, find line 243:
```python
query_embedding = [0.0] * 1536  # Use zero vector for "get all" queries
```

Change to:
```python
query_embedding = [0.001] * 1536  # Small non-zero vector to avoid NaN
```

This works because:
- Small non-zero values avoid the division by zero
- Returns memories sorted by similarity (though all will be similar)
- No other code changes needed

## Option 2: Minimal Fix (Better)

In `unified_store.py`, replace the empty query section (around line 242-246) with:

```python
if not request.query or request.query.strip() == "":
    # For empty queries, use a random vector to get diverse results
    import random
    random.seed(42)  # Consistent results
    query_embedding = [random.uniform(0.001, 0.01) for _ in range(1536)]
    logger.info("Empty query - using random vector for diverse results")
else:
    query_embedding = await self._generate_embedding(request.query)
```

## Testing the Fix

After deploying either fix:

```bash
# Test empty query
curl -X POST https://core-nexus-memory-service.onrender.com/memories/query \
  -H "Content-Type: application/json" \
  -d '{"query": "", "limit": 5}'

# Should return memories (not 0)
```

## Which Fix to Use?

- **One-Line Fix**: Use if you need to deploy in next 5 minutes
- **Minimal Fix**: Use if you have 10 minutes, gives better results
- **Comprehensive Fix**: Use from FIX_EMPTY_QUERY_BUG.py for best solution

The one-line fix will get the system working immediately!