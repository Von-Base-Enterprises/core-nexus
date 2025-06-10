#!/usr/bin/env python3
"""
Test zero vector behavior in pgvector
"""

import asyncio

import asyncpg

EXTERNAL_DATABASE_URL = "postgresql://nexus_memory_db_user:2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V@dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com/nexus_memory_db"

async def test_zero_vector():
    """Test how pgvector handles zero vector queries"""
    print("TESTING ZERO VECTOR BEHAVIOR")
    print("="*60)

    conn = await asyncpg.connect(EXTERNAL_DATABASE_URL, timeout=10)

    # Create a zero vector
    zero_vector = '[' + ','.join(['0.0'] * 1536) + ']'

    print("1. Testing cosine similarity with zero vector...")
    try:
        # This query should fail or return no results
        result = await conn.fetch("""
            SELECT 
                id,
                content,
                1 - (embedding <=> $1::vector) as similarity_score
            FROM vector_memories
            ORDER BY embedding <=> $1::vector
            LIMIT 5
        """, zero_vector)

        print(f"✓ Query succeeded, returned {len(result)} rows")
        for row in result:
            print(f"  - {row['content'][:50]}... (similarity: {row['similarity_score']})")

    except Exception as e:
        print(f"✗ Query failed: {str(e)}")

    print("\n2. Testing alternative: Query without vector similarity...")
    try:
        # Query without using vector similarity
        result = await conn.fetch("""
            SELECT 
                id,
                content,
                importance_score,
                created_at
            FROM vector_memories
            ORDER BY created_at DESC
            LIMIT 5
        """)

        print(f"✓ Query succeeded, returned {len(result)} rows")
        for row in result:
            print(f"  - {row['content'][:50]}... (created: {row['created_at']})")

    except Exception as e:
        print(f"✗ Query failed: {str(e)}")

    print("\n3. Testing with a non-zero vector...")
    try:
        # Create a vector with small non-zero values
        small_vector = '[' + ','.join(['0.001'] * 1536) + ']'

        result = await conn.fetch("""
            SELECT 
                id,
                content,
                1 - (embedding <=> $1::vector) as similarity_score
            FROM vector_memories
            ORDER BY embedding <=> $1::vector
            LIMIT 5
        """, small_vector)

        print(f"✓ Query succeeded, returned {len(result)} rows")
        for row in result:
            print(f"  - {row['content'][:50]}... (similarity: {row['similarity_score']:.4f})")

    except Exception as e:
        print(f"✗ Query failed: {str(e)}")

    await conn.close()

    print("\n" + "="*60)
    print("CONCLUSION:")
    print("The zero vector approach doesn't work with cosine similarity!")
    print("For empty queries, we need a different strategy.")

if __name__ == "__main__":
    asyncio.run(test_zero_vector())
