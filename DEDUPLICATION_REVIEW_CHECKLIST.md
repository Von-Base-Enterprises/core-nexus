# Deduplication PR Review Checklist

## Pre-Review Observations

I can see that deduplication infrastructure is already partially in place:
- `unified_store.py` imports `DeduplicationService` and `DeduplicationMode`
- `init-db.sql` has deduplication tables already created
- Environment variable controls: `DEDUPLICATION_MODE`, `DEDUP_SIMILARITY_THRESHOLD`

## Critical Review Points

### 1. **Database Schema Compatibility** ✓
- [ ] Verify all SQL migrations are included
- [ ] Check if existing tables need updates
- [ ] Ensure triggers don't conflict with existing operations
- [ ] Verify indexes are appropriate for performance

Current tables I see:
- `memory_content_hashes` - For exact duplicate detection
- `deduplication_reviews` - For tracking decisions
- `deduplication_metrics` - For monitoring (partitioned)

### 2. **Performance Impact** 🔍
- [ ] Hash calculation overhead on every insert
- [ ] Impact on write performance
- [ ] Index usage for duplicate checks
- [ ] Connection pool usage during checks

### 3. **Code Integration Points** 📝
- [ ] `DeduplicationService` class implementation
- [ ] Integration in `store_memory()` method
- [ ] Error handling for dedup failures
- [ ] Statistics tracking integration

### 4. **Configuration & Feature Flags** ⚙️
- [ ] Environment variable validation
- [ ] Default values are safe (currently "off")
- [ ] Mode options: off, passive, active, strict
- [ ] Threshold ranges (0.0 - 1.0)

### 5. **Backward Compatibility** 🔄
- [ ] Existing memories without hashes
- [ ] API response format unchanged
- [ ] No breaking changes to store/query
- [ ] Graceful degradation if disabled

### 6. **Edge Cases to Test** 🧪
```python
# Empty content
{"content": "", "metadata": {}}

# Whitespace variations
{"content": "Hello World"} vs {"content": "Hello  World"}

# Case sensitivity
{"content": "Test"} vs {"content": "test"}

# Unicode normalization
{"content": "café"} vs {"content": "café"}  # Different unicode forms

# Metadata differences with same content
{"content": "Same", "metadata": {"v": 1}} vs {"content": "Same", "metadata": {"v": 2}}
```

### 7. **Concurrency Safety** 🔒
- [ ] Race conditions during duplicate check
- [ ] Transaction isolation level
- [ ] Unique constraint handling
- [ ] Async operation safety

### 8. **Monitoring & Observability** 📊
- [ ] Metrics collection working
- [ ] Logging at appropriate levels
- [ ] Performance counters updated
- [ ] Dedup decisions tracked

### 9. **Failure Modes** ⚠️
- [ ] What if hash calculation fails?
- [ ] What if similarity check times out?
- [ ] Database constraint violations
- [ ] Service initialization failures

### 10. **Security Considerations** 🔐
- [ ] Hash collision possibilities
- [ ] Information leakage in logs
- [ ] Metadata privacy preserved
- [ ] No timing attacks possible

## Required Tests Before Merge

### Functional Tests
```bash
# 1. Store identical content twice
curl -X POST .../memories -d '{"content": "Duplicate test"}'
curl -X POST .../memories -d '{"content": "Duplicate test"}'
# Should return same ID or handle per mode

# 2. Store similar content
curl -X POST .../memories -d '{"content": "The quick brown fox"}'
curl -X POST .../memories -d '{"content": "The quick brown foxes"}'
# Should detect based on threshold

# 3. Verify stats endpoint
curl .../memories/stats
# Should show duplicates_prevented count
```

### Performance Tests
```bash
# Measure impact on write performance
# Before: ~1000ms per write
# After: Should be < 1200ms (20% overhead max)
```

### Load Tests
```python
# Concurrent duplicate checks
async def concurrent_duplicates():
    tasks = []
    for i in range(50):
        tasks.append(store_memory("Same content"))
    results = await asyncio.gather(*tasks)
    # Should handle gracefully, only store once
```

## Merge Criteria

### Must Have ✅
1. All existing tests pass
2. No performance regression > 20%
3. Feature flag works (can disable)
4. No data loss scenarios
5. Backward compatible

### Should Have 📋
1. Metrics dashboard ready
2. Documentation updated
3. Admin endpoints for management
4. Bulk dedup for existing data

### Nice to Have 🎁
1. UI for reviewing duplicates
2. Configurable strategies
3. Smart metadata merging
4. Similarity explanations

## Post-Merge Monitoring

1. **First Hour**
   - Error rate stays below 0.1%
   - Write latency < 1200ms p99
   - No connection pool exhaustion

2. **First Day**
   - Dedup rate matches expectations
   - No memory leaks
   - Stats tracking accurately

3. **First Week**
   - Review false positive rate
   - Tune similarity threshold
   - Analyze performance impact

## Rollback Plan

If issues arise:
1. Set `DEDUPLICATION_MODE=off`
2. Restart service
3. Optional: Drop dedup tables if needed
4. Monitor for recovery

## Questions for PR Author

1. How are existing memories without hashes handled?
2. What's the performance impact on write operations?
3. How does it handle concurrent duplicate submissions?
4. Can we tune the similarity algorithm?
5. Is there a bulk dedup tool for existing data?

## Ready to Review! 🚀

When the PR arrives, I'll check each item and ensure it's production-ready.