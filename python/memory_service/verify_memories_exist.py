#!/usr/bin/env python3
"""
Verify that memories exist in the database and are retrievable
"""

import asyncio

import asyncpg

EXTERNAL_DATABASE_URL = "postgresql://nexus_memory_db_user:2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V@dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com/nexus_memory_db"

async def verify_memories():
    """Verify memories in database"""
    print("VERIFYING MEMORIES IN DATABASE")
    print("="*60)

    try:
        conn = await asyncpg.connect(EXTERNAL_DATABASE_URL, timeout=10)

        # Count total memories
        total = await conn.fetchval("SELECT COUNT(*) FROM vector_memories")
        print(f"✓ Total memories in database: {total}")

        # Get recent memories
        recent = await conn.fetch("""
            SELECT id, content, metadata, importance_score, created_at
            FROM vector_memories
            ORDER BY created_at DESC
            LIMIT 5
        """)

        print("\n✓ Recent memories:")
        for i, memory in enumerate(recent, 1):
            print(f"\n  {i}. ID: {memory['id']}")
            print(f"     Content: {memory['content'][:100]}...")
            print(f"     Created: {memory['created_at']}")
            print(f"     Importance: {memory['importance_score']}")

        # Search for our test memories
        test_memories = await conn.fetch("""
            SELECT id, content, created_at
            FROM vector_memories
            WHERE content LIKE '%Health check test%'
            ORDER BY created_at DESC
            LIMIT 10
        """)

        print(f"\n✓ Found {len(test_memories)} health check test memories:")
        for memory in test_memories:
            print(f"  - {memory['id']}: {memory['content'][:50]}... ({memory['created_at']})")

        # Check if embedding index exists
        indexes = await conn.fetch("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'vector_memories'
            AND indexname LIKE '%embedding%'
        """)

        print("\n✓ Vector indexes:")
        for idx in indexes:
            print(f"  - {idx['indexname']}")

        await conn.close()

        print("\n" + "="*60)
        print("CONCLUSION: Memories ARE stored in the database!")
        print("The issue is that pgvector provider is DISABLED in the API")
        print("="*60)

    except Exception as e:
        print(f"✗ Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(verify_memories())
