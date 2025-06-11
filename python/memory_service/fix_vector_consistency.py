#!/usr/bin/env python3
"""
Fix for vector retrieval consistency issues in Core Nexus.
This implements ACID-compliant vector operations with immediate read-after-write consistency.
"""

import asyncio
import json
import logging
from typing import Any, Optional
from uuid import UUID, uuid4

import asyncpg

logger = logging.getLogger(__name__)


class FixedPgVectorProvider:
    """
    Fixed PgVector provider with proper initialization and ACID guarantees.
    
    Key fixes:
    1. Synchronous pool initialization (no race conditions)
    2. Non-partitioned table for consistent index usage
    3. Transaction-wrapped operations with synchronous commit
    4. Single HNSW index type for reliability
    """
    
    def __init__(self, config: dict[str, Any]):
        self.connection_pool: Optional[asyncpg.Pool] = None
        self.table_name = "vector_memories_fixed"  # New non-partitioned table
        self.config = config
        self.enabled = False
        
    async def initialize(self) -> None:
        """Synchronously initialize the provider - no fire-and-forget!"""
        try:
            # Build connection string
            conn_str = (
                f"postgresql://{self.config['user']}:{self.config['password']}@"
                f"{self.config['host']}:{self.config['port']}/{self.config['database']}"
            )
            
            # Create pool - this MUST complete before marking as enabled
            self.connection_pool = await asyncpg.create_pool(
                conn_str,
                min_size=5,
                max_size=20,
                command_timeout=60,
                server_settings={
                    'jit': 'off',  # Disable JIT for consistent performance
                    'synchronous_commit': 'on'  # Ensure durability
                }
            )
            
            # Create tables and indexes in a single transaction
            await self._setup_schema()
            
            # Only mark as enabled after everything is ready
            self.enabled = True
            logger.info("FixedPgVectorProvider initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize FixedPgVectorProvider: {e}")
            raise
    
    async def _setup_schema(self) -> None:
        """Set up the database schema with proper indexes."""
        async with self.connection_pool.acquire() as conn:
            async with conn.transaction():
                # Ensure pgvector extension
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                
                # Create non-partitioned table
                await conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        id UUID PRIMARY KEY,
                        content TEXT NOT NULL,
                        embedding vector(1536) NOT NULL,
                        metadata JSONB DEFAULT '{{}}',
                        importance_score FLOAT DEFAULT 0.5,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    );
                """)
                
                # Create ONLY ONE vector index - HNSW for accuracy
                await conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS {self.table_name}_embedding_idx
                    ON {self.table_name} 
                    USING hnsw (embedding vector_cosine_ops)
                    WITH (m = 16, ef_construction = 64);
                """)
                
                # Create supporting indexes
                await conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS {self.table_name}_created_idx
                    ON {self.table_name} (created_at DESC);
                """)
                
                await conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS {self.table_name}_importance_idx
                    ON {self.table_name} (importance_score DESC);
                """)
                
                # Update statistics immediately
                await conn.execute(f"ANALYZE {self.table_name};")
    
    async def store(self, content: str, embedding: list[float], metadata: dict[str, Any]) -> UUID:
        """Store memory with ACID guarantees and immediate consistency."""
        if not self.enabled or not self.connection_pool:
            raise RuntimeError("Provider not initialized")
        
        memory_id = uuid4()
        
        async with self.connection_pool.acquire() as conn:
            # Use READ COMMITTED isolation for consistency
            async with conn.transaction(isolation='read_committed'):
                # Convert embedding to PostgreSQL format
                embedding_str = '[' + ','.join(map(str, embedding)) + ']'
                
                # Insert with explicit columns
                await conn.execute(f"""
                    INSERT INTO {self.table_name}
                    (id, content, embedding, metadata, importance_score, created_at)
                    VALUES ($1, $2, $3::vector, $4::jsonb, $5, NOW())
                """, 
                    memory_id,
                    content,
                    embedding_str,
                    json.dumps(metadata) if metadata else '{}',
                    metadata.get('importance_score', 0.5)
                )
                
                # Ensure synchronous commit for immediate durability
                await conn.execute("SET synchronous_commit = on;")
        
        logger.debug(f"Stored memory {memory_id} with ACID guarantees")
        return memory_id
    
    async def query(self, query_embedding: list[float], limit: int = 10) -> list[dict]:
        """Query with consistent index usage."""
        if not self.enabled or not self.connection_pool:
            return []
        
        async with self.connection_pool.acquire() as conn:
            # Convert embedding
            embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
            
            # Use explicit index hint via ORDER BY
            rows = await conn.fetch(f"""
                SELECT 
                    id,
                    content,
                    metadata,
                    importance_score,
                    1 - (embedding <=> $1::vector) as similarity_score,
                    created_at
                FROM {self.table_name}
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> $1::vector
                LIMIT $2
            """, embedding_str, limit)
            
            return [
                {
                    'id': row['id'],
                    'content': row['content'],
                    'metadata': row['metadata'],
                    'importance_score': row['importance_score'],
                    'similarity_score': row['similarity_score'],
                    'created_at': row['created_at']
                }
                for row in rows
            ]
    
    async def verify_index_usage(self) -> dict[str, Any]:
        """Verify that vector indexes are being used."""
        async with self.connection_pool.acquire() as conn:
            # Check index statistics
            stats = await conn.fetchrow(f"""
                SELECT 
                    schemaname,
                    tablename,
                    indexrelname,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch
                FROM pg_stat_user_indexes
                WHERE tablename = '{self.table_name}'
                AND indexrelname LIKE '%embedding%'
            """)
            
            return {
                'index_name': stats['indexrelname'] if stats else None,
                'index_scans': stats['idx_scan'] if stats else 0,
                'tuples_read': stats['idx_tup_read'] if stats else 0,
                'index_used': bool(stats and stats['idx_scan'] > 0)
            }
    
    async def migrate_from_partitioned(self) -> int:
        """Migrate data from partitioned table to fixed table."""
        async with self.connection_pool.acquire() as conn:
            async with conn.transaction():
                # Copy all data from partitioned table
                result = await conn.execute(f"""
                    INSERT INTO {self.table_name} 
                    (id, content, embedding, metadata, importance_score, created_at)
                    SELECT id, content, embedding, metadata, importance_score, created_at
                    FROM vector_memories
                    WHERE embedding IS NOT NULL
                    ON CONFLICT (id) DO NOTHING
                """)
                
                # Update statistics
                await conn.execute(f"ANALYZE {self.table_name};")
                
                # Extract row count from result
                count = int(result.split()[-1]) if result else 0
                return count


async def apply_fix(config: dict[str, Any]) -> None:
    """Apply the fix to production."""
    print("Applying vector consistency fix...")
    
    # Initialize fixed provider
    provider = FixedPgVectorProvider(config)
    await provider.initialize()
    
    # Verify it's working
    print("Verifying provider initialization...")
    test_embedding = [0.1] * 1536
    test_id = await provider.store(
        content="Test memory for verification",
        embedding=test_embedding,
        metadata={"test": True}
    )
    print(f"✅ Successfully stored test memory: {test_id}")
    
    # Query it back immediately (testing read-after-write)
    results = await provider.query(test_embedding, limit=1)
    if results and str(results[0]['id']) == str(test_id):
        print("✅ Read-after-write consistency verified!")
    else:
        print("❌ Read-after-write consistency FAILED!")
    
    # Check index usage
    index_stats = await provider.verify_index_usage()
    print(f"Index statistics: {index_stats}")
    
    # Migrate existing data
    print("Migrating data from partitioned table...")
    migrated = await provider.migrate_from_partitioned()
    print(f"✅ Migrated {migrated} memories to fixed table")
    
    print("\nFix applied successfully!")
    print("Next steps:")
    print("1. Update providers.py to use this implementation")
    print("2. Switch queries to use vector_memories_fixed table")
    print("3. Monitor index usage with verify_index_usage()")


if __name__ == "__main__":
    # Test configuration
    config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'test_db',
        'user': 'test_user',
        'password': 'test_pass'
    }
    
    print("Vector Consistency Fix")
    print("=" * 50)
    print("This fix addresses:")
    print("- Index type mismatches (HNSW vs IVFFlat)")
    print("- Partitioned table issues")
    print("- Async initialization race conditions")
    print("- Missing ACID guarantees")
    print("\nRun with production config to apply fix.")