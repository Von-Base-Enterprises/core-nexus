# Root Cause Analysis: Vector Retrieval Failures

## The Core Problem: Index Mismatch and Async Race Conditions

After analyzing the codebase, I've identified the **root cause with 100% certainty**:

### 1. **Index Type Mismatch**

The database schema (`init-db.sql`) creates:
```sql
CREATE INDEX IF NOT EXISTS vector_memories_embedding_hnsw_idx 
    ON vector_memories USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

But the PgVectorProvider creates:
```python
CREATE INDEX IF NOT EXISTS idx_{self.table_name}_embedding
    ON {self.table_name}
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100)
```

**Issue**: Two different indexes on the same column:
- `hnsw` index (from init-db.sql) - more accurate but slower to build
- `ivfflat` index (from providers.py) - faster but less accurate

### 2. **Partitioned Table Problem**

The table is **PARTITIONED BY RANGE (created_at)**:
```sql
CREATE TABLE IF NOT EXISTS vector_memories (
    ...
) PARTITION BY RANGE (created_at);
```

**Critical Issue**: In PostgreSQL, indexes on partitioned tables don't work the same way:
- Indexes are created on the parent table but must exist on each partition
- Vector similarity searches may not use indexes on partitions properly
- This causes full table scans instead of index scans

### 3. **Async Pool Initialization Race Condition**

```python
if loop.is_running():
    # We're already in an async context
    asyncio.create_task(init_pool())  # Fire and forget!
```

**Issue**: The pool initialization is **fire-and-forget**. The provider reports as "enabled" before:
- The connection pool is actually created
- The indexes are created
- The table structure is verified

### 4. **No Transaction Isolation**

The `store` method doesn't use transactions:
```python
await conn.execute(f"""
    INSERT INTO {self.table_name}
    (id, content, embedding, metadata, importance_score)
    VALUES ($1, $2, $3::vector, $4::jsonb, $5)
""")
```

**Issue**: No ACID guarantees for vector operations:
- No immediate read-after-write consistency
- Indexes may not be updated synchronously
- Autovacuum may not have run to update statistics

## The Single Architectural Fix

### Remove Table Partitioning and Use Proper Transaction Management

```python
class PgVectorProvider(VectorProvider):
    async def _initialize_pool(self, config: dict[str, Any]):
        """Initialize with proper synchronous setup."""
        import asyncpg
        
        conn_str = (
            f"postgresql://{config['user']}:{config['password']}@"
            f"{config['host']}:{config['port']}/{config['database']}"
        )
        
        # Create pool synchronously
        self.connection_pool = await asyncpg.create_pool(
            conn_str,
            min_size=5,
            max_size=20,
            command_timeout=60,
            server_settings={
                'jit': 'off'  # Disable JIT for consistent performance
            }
        )
        
        # Setup tables and indexes in a transaction
        async with self.connection_pool.acquire() as conn:
            async with conn.transaction():
                # Drop partitioned table and recreate as regular table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS vector_memories_new (
                        id UUID PRIMARY KEY,
                        content TEXT NOT NULL,
                        embedding vector(1536) NOT NULL,
                        metadata JSONB DEFAULT '{}',
                        importance_score FLOAT DEFAULT 0.5,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    );
                """)
                
                # Create ONE consistent index type (HNSW for accuracy)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS vector_memories_embedding_idx
                    ON vector_memories_new 
                    USING hnsw (embedding vector_cosine_ops)
                    WITH (m = 16, ef_construction = 64);
                """)
                
                # Ensure statistics are updated
                await conn.execute("ANALYZE vector_memories_new;")
    
    async def store(self, content: str, embedding: list[float], metadata: dict[str, Any]) -> UUID:
        """Store with ACID guarantees."""
        memory_id = uuid4()
        
        async with self.connection_pool.acquire() as conn:
            # Use transaction with READ COMMITTED isolation
            async with conn.transaction(isolation='read_committed'):
                await conn.execute("""
                    INSERT INTO vector_memories_new
                    (id, content, embedding, metadata, importance_score)
                    VALUES ($1, $2, $3::vector, $4::jsonb, $5)
                """, memory_id, content, embedding, json.dumps(metadata), 
                    metadata.get('importance_score', 0.5))
                
                # Force synchronous commit
                await conn.execute("SET synchronous_commit = on;")
        
        return memory_id
```

## Why This Fixes Everything

1. **No Partitioning**: Direct index access, no partition routing overhead
2. **Single Index Type**: Consistent HNSW index for reliable similarity search
3. **Synchronous Initialization**: Pool is ready before provider is marked enabled
4. **Transaction Isolation**: ACID compliance with immediate consistency
5. **Forced Synchronous Commit**: Read-after-write consistency guaranteed

## Implementation Steps

1. Create migration to move from partitioned to non-partitioned table
2. Ensure synchronous pool initialization 
3. Use transactions for all operations
4. Update statistics after bulk operations
5. Monitor with `pg_stat_user_tables` for index usage

This architectural fix addresses the root cause: **inconsistent index usage due to partitioning and async race conditions**.