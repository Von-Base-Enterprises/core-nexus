#!/usr/bin/env python3
"""
Test PostgreSQL memory settings and index creation capability
"""

import asyncio
from datetime import datetime

import asyncpg

EXTERNAL_DATABASE_URL = "postgresql://nexus_memory_db_user:2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V@dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com/nexus_memory_db"

async def test_memory_settings():
    """Test PostgreSQL memory configuration"""
    print("POSTGRESQL MEMORY CONFIGURATION TEST")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("="*60)

    try:
        conn = await asyncpg.connect(EXTERNAL_DATABASE_URL, timeout=10)
        print("✓ Connected successfully")

        # Check key memory settings
        print("\nMemory Settings:")
        memory_settings = [
            'maintenance_work_mem',
            'work_mem',
            'shared_buffers',
            'effective_cache_size',
            'max_connections',
            'max_worker_processes'
        ]

        for setting in memory_settings:
            value = await conn.fetchval(f"SHOW {setting}")
            print(f"  {setting}: {value}")

        # Check if we can increase maintenance_work_mem temporarily
        print("\nTesting temporary memory increase...")
        try:
            await conn.execute("SET maintenance_work_mem = '128MB'")
            new_value = await conn.fetchval("SHOW maintenance_work_mem")
            print(f"✓ Successfully set maintenance_work_mem to: {new_value}")
        except Exception as e:
            print(f"✗ Failed to set maintenance_work_mem: {e}")

        # Check existing indexes
        print("\nExisting indexes on vector_memories:")
        indexes = await conn.fetch("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'vector_memories'
            ORDER BY indexname
        """)

        for idx in indexes:
            print(f"  - {idx['indexname']}")
            if 'embedding' in idx['indexname']:
                print(f"    Definition: {idx['indexdef'][:100]}...")

        # Check if the problematic index exists
        embedding_index_exists = any('embedding' in idx['indexname'] and 'ivfflat' in idx['indexdef']
                                   for idx in indexes)

        if not embedding_index_exists:
            print("\n⚠️  The ivfflat embedding index is MISSING!")
            print("\nAttempting to create index with increased memory...")

            try:
                # Set higher memory for this session
                await conn.execute("SET maintenance_work_mem = '128MB'")

                # Try to create the index
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_vector_memories_embedding
                    ON vector_memories
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100)
                """)
                print("✓ Index created successfully!")

            except Exception as e:
                print(f"✗ Index creation failed: {e}")

                # Try with fewer lists
                print("\nTrying with fewer lists (10 instead of 100)...")
                try:
                    await conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_vector_memories_embedding_small
                        ON vector_memories
                        USING ivfflat (embedding vector_cosine_ops)
                        WITH (lists = 10)
                    """)
                    print("✓ Smaller index created successfully!")
                except Exception as e2:
                    print(f"✗ Smaller index also failed: {e2}")
        else:
            print("\n✓ The embedding index already EXISTS!")

        # Test vector operations
        print("\nTesting vector operations...")
        count = await conn.fetchval("SELECT COUNT(*) FROM vector_memories")
        print(f"✓ Total memories: {count}")

        # Test a vector query
        try:
            result = await conn.fetchval("""
                SELECT COUNT(*) FROM vector_memories
                WHERE embedding IS NOT NULL
            """)
            print(f"✓ Memories with embeddings: {result}")
        except Exception as e:
            print(f"✗ Vector query failed: {e}")

        await conn.close()

    except Exception as e:
        print(f"✗ Connection failed: {str(e)}")

    print("\n" + "="*60)
    print("RECOMMENDATIONS:")
    print("="*60)
    print("1. If maintenance_work_mem is still 16MB, contact Render support")
    print("2. If index creation still fails, reduce 'lists' parameter")
    print("3. After creating index, restart Core Nexus service")
    print("4. The service should then show pgvector as 'healthy'")

if __name__ == "__main__":
    asyncio.run(test_memory_settings())
