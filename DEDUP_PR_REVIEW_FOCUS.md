# Deduplication PR Review Focus Areas

Based on the existing code, the deduplication system is already partially implemented. Here's what I'll focus on when reviewing the PR:

## 1. Missing Implementation - `deduplication.py`

The PR should include the actual `DeduplicationService` class that's imported in `unified_store.py`:
```python
from .deduplication import DeduplicationService, DeduplicationMode
```

### Expected Structure:
```python
class DeduplicationMode(Enum):
    OFF = "off"
    LOG_ONLY = "log_only"  # Detect but don't prevent
    ACTIVE = "active"      # Prevent duplicates
    STRICT = "strict"      # Aggressive deduplication

class DeduplicationResult:
    is_duplicate: bool
    confidence_score: float
    decision: DeduplicationMode
    reason: str
    existing_memory: Optional[MemoryResponse]
    content_hash: str
    similarity_score: Optional[float]

class DeduplicationService:
    async def check_duplicate(content: str, metadata: dict) -> DeduplicationResult
    async def get_stats() -> dict
    async def mark_false_positive(memory_id: UUID, actual_id: UUID) -> None
    async def cleanup_old_hashes(days: int) -> int
```

## 2. Critical Implementation Details

### Hash Calculation
- Should use SHA256 (matches DB function)
- Must handle Unicode normalization
- Consider whitespace/case sensitivity options

### Similarity Checking
- Vector similarity for semantic duplicates
- Threshold configuration (default 0.95)
- Performance optimization for large datasets

### Transaction Safety
```python
async def check_duplicate(self, content: str, metadata: dict) -> DeduplicationResult:
    # Must be wrapped in transaction to prevent race conditions
    async with self.connection.transaction(isolation='read_committed'):
        # 1. Calculate hash
        # 2. Check exact matches
        # 3. Check vector similarity if enabled
        # 4. Record decision
```

## 3. Performance Considerations

### Expected Overhead:
- Hash calculation: ~1-2ms
- DB lookup: ~5-10ms  
- Vector similarity (if enabled): ~50-100ms
- **Total**: <150ms added to write operations

### Optimization Requirements:
- Index usage verification
- Connection pool management
- Caching for recent checks
- Batch processing support

## 4. Configuration Validation

```python
# Environment variables
DEDUPLICATION_MODE = "active"  # off, log_only, active, strict
DEDUP_SIMILARITY_THRESHOLD = "0.95"  # 0.0-1.0
DEDUP_EXACT_MATCH_ONLY = "false"  # Skip vector similarity
DEDUP_HASH_ALGORITHM = "sha256"  # Future: blake3, xxhash
```

## 5. Error Handling

The service must gracefully handle:
- Hash calculation failures
- Database connection issues
- Vector similarity timeouts
- Invalid configuration

## 6. Testing Requirements

### Unit Tests:
```python
# test_deduplication.py
async def test_exact_duplicate_detection()
async def test_similarity_threshold()
async def test_whitespace_handling()
async def test_unicode_normalization()
async def test_concurrent_duplicates()
async def test_mode_transitions()
```

### Integration Tests:
- With real PostgreSQL
- With vector operations
- With high concurrency
- With large content

## 7. Migration Safety

For existing deployments:
1. Default mode must be "off"
2. Backfill should be optional
3. No breaking changes to API
4. Gradual rollout path

## 8. Monitoring & Metrics

The implementation should track:
- Duplicate detection rate
- False positive rate
- Performance impact
- Storage savings
- Error rates

## Review Checklist Summary

When the PR arrives, I'll verify:

✅ **Core Functionality**
- [ ] DeduplicationService class complete
- [ ] All modes implemented correctly
- [ ] Hash calculation matches DB function
- [ ] Similarity checking works

✅ **Performance**
- [ ] < 150ms overhead on writes
- [ ] Indexes used efficiently
- [ ] No connection pool exhaustion
- [ ] Handles 100+ concurrent checks

✅ **Safety**
- [ ] Transaction isolation correct
- [ ] Race conditions handled
- [ ] Graceful error handling
- [ ] No data loss scenarios

✅ **Operations**
- [ ] Feature flag works
- [ ] Monitoring in place
- [ ] Rollback possible
- [ ] Documentation complete

## Expected PR Structure

```
python/memory_service/src/memory_service/
├── deduplication.py          # NEW - Main implementation
├── dedup_strategies.py       # NEW - Different detection strategies
├── tests/
│   ├── test_deduplication.py # NEW - Comprehensive tests
│   └── test_dedup_perf.py    # NEW - Performance tests
└── docs/
    └── deduplication.md      # NEW - Usage documentation
```

I'm ready to review the PR with this focus!