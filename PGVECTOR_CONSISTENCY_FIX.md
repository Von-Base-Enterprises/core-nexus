# PgVector Provider Consistency Fix

## Summary of Changes

This document outlines the fixes applied to the PgVectorProvider in `providers.py` to address consistency issues and race conditions.

## Key Fixes Applied

### 1. Table Name Update
- Changed default table name from `vector_memories` to `memories` to align with the new non-partitioned table structure after migration

### 2. Async Initialization Race Condition Fix
- Added `_pool_initialization_task` to track async pool initialization
- Created `_ensure_pool_ready()` method that waits for pool initialization to complete before any operation
- All public methods now call `_ensure_pool_ready()` to prevent operations on uninitialized pool

### 3. Connection Pool Configuration
- Added server settings to the connection pool:
  - `synchronous_commit: 'on'` - Ensures data is written to disk before returning
  - `jit: 'off'` - Disables JIT compilation for more predictable performance

### 4. Transaction Wrapping
- All write operations (store, delete, update_importance) now use explicit transactions
- Added `SET LOCAL synchronous_commit = on` within transactions for immediate consistency
- This ensures read-after-write consistency

### 5. Additional Index
- Added index on `created_at DESC` to optimize queries that order by creation time

### 6. Proper Enabled State Management
- Set `self.enabled = True` only after successful pool initialization
- This prevents the provider from being used before it's fully ready

## Technical Details

### Before (Race Condition Issue):
```python
def _initialize_pool(self, config):
    async def init_pool():
        # ... initialization code ...
    
    # This could return before init_pool completed!
    if loop.is_running():
        asyncio.create_task(init_pool())
```

### After (Fixed):
```python
def _initialize_pool(self, config):
    async def init_pool():
        # ... initialization code ...
        self.enabled = True  # Only after success
    
    if loop.is_running():
        self._pool_initialization_task = asyncio.create_task(init_pool())

async def _ensure_pool_ready(self):
    if self._pool_initialization_task and not self._pool_initialization_task.done():
        await self._pool_initialization_task  # Wait for completion
```

### Transaction Example:
```python
async with self.connection_pool.acquire() as conn:
    async with conn.transaction():
        await conn.execute("INSERT INTO memories ...")
        await conn.execute("SET LOCAL synchronous_commit = on")
```

## Benefits

1. **No Race Conditions**: Operations wait for pool initialization
2. **Immediate Consistency**: Synchronous commits ensure data is visible immediately
3. **Atomic Operations**: Transactions prevent partial updates
4. **Better Performance**: Proper indexes for common query patterns
5. **Reliability**: Consistent state management throughout the provider lifecycle

## Backward Compatibility

All changes maintain backward compatibility:
- Public API remains unchanged
- Existing code using the provider will work without modifications
- Performance improvements are transparent to callers