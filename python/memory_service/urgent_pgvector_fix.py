#!/usr/bin/env python3
"""
URGENT: Fix pgvector connection and verify data persistence
"""

import asyncio
from datetime import datetime

import asyncpg

# Database credentials from Render
EXTERNAL_DATABASE_URL = "postgresql://nexus_memory_db_user:2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V@dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com/nexus_memory_db"
INTERNAL_DATABASE_URL = "postgresql://nexus_memory_db_user:2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V@dpg-d12n0np5pdvs73ctmm40-a/nexus_memory_db"

async def test_connection(db_url, label):
    """Test database connection"""
    print(f"\n{'='*60}")
    print(f"Testing {label} connection...")
    print(f"{'='*60}")

    try:
        conn = await asyncpg.connect(db_url, timeout=10)
        print(f"✓ Connected successfully to {label}")

        # Test basic query
        version = await conn.fetchval("SELECT version()")
        print(f"✓ PostgreSQL version: {version[:50]}...")

        await conn.close()
        return True
    except Exception as e:
        print(f"✗ Connection failed: {str(e)}")
        return False

async def check_pgvector_extension(db_url):
    """Check if pgvector extension is installed"""
    print("\nChecking pgvector extension...")

    try:
        conn = await asyncpg.connect(db_url, timeout=10)

        # Check if extension exists
        result = await conn.fetchrow(
            "SELECT * FROM pg_extension WHERE extname = 'vector'"
        )

        if result:
            print(f"✓ pgvector extension is installed (version: {result['extversion']})")
        else:
            print("✗ pgvector extension NOT found")
            print("  Attempting to create extension...")
            try:
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
                print("✓ pgvector extension created successfully")
            except Exception as e:
                print(f"✗ Failed to create extension: {str(e)}")

        await conn.close()
        return bool(result)
    except Exception as e:
        print(f"✗ Extension check failed: {str(e)}")
        return False

async def check_tables(db_url):
    """Check if required tables exist"""
    print("\nChecking database tables...")

    try:
        conn = await asyncpg.connect(db_url, timeout=10)

        # Get all tables
        tables = await conn.fetch("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)

        print(f"Found {len(tables)} tables:")
        for table in tables:
            print(f"  - {table['tablename']}")

        # Check specifically for memories table
        memories_exists = any(t['tablename'] == 'memories' for t in tables)
        vector_memories_exists = any(t['tablename'] == 'vector_memories' for t in tables)

        if memories_exists:
            print("✓ 'memories' table exists")
        if vector_memories_exists:
            print("✓ 'vector_memories' table exists")

        if not memories_exists and not vector_memories_exists:
            print("✗ No memory storage tables found!")

        await conn.close()
        return memories_exists or vector_memories_exists
    except Exception as e:
        print(f"✗ Table check failed: {str(e)}")
        return False

async def test_vector_operations(db_url):
    """Test vector storage and retrieval"""
    print("\nTesting vector operations...")

    try:
        conn = await asyncpg.connect(db_url, timeout=10)

        # Check which table to use
        tables = await conn.fetch("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename IN ('memories', 'vector_memories')
        """)

        if not tables:
            print("✗ No memory tables found")
            await conn.close()
            return False

        table_name = tables[0]['tablename']
        print(f"Using table: {table_name}")

        # Get table structure
        columns = await conn.fetch(f"""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position
        """)

        print(f"\nTable structure for {table_name}:")
        for col in columns:
            print(f"  - {col['column_name']}: {col['data_type']}")

        # Test vector operations if embedding column exists
        has_embedding = any(col['column_name'] == 'embedding' for col in columns)
        if has_embedding:
            print("\n✓ Table has embedding column")

            # Count existing records
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            print(f"Current record count: {count}")

            # Try to retrieve a sample
            if count > 0:
                sample = await conn.fetchrow(f"""
                    SELECT id, content,
                           CASE WHEN embedding IS NULL THEN 'NULL'
                                ELSE 'Vector[' || array_length(embedding::float[], 1)::text || ']'
                           END as embedding_info
                    FROM {table_name}
                    LIMIT 1
                """)
                print("\nSample record:")
                print(f"  ID: {sample['id']}")
                print(f"  Content: {sample['content'][:50]}...")
                print(f"  Embedding: {sample['embedding_info']}")
        else:
            print("✗ No embedding column found")

        await conn.close()
        return True
    except Exception as e:
        print(f"✗ Vector operations test failed: {str(e)}")
        return False

async def update_environment_recommendation():
    """Provide environment variable recommendations"""
    print("\n" + "="*60)
    print("ENVIRONMENT VARIABLE RECOMMENDATIONS")
    print("="*60)

    print("\nAdd these to your Render environment variables:")
    print(f"DATABASE_URL={INTERNAL_DATABASE_URL}")
    print("PGVECTOR_HOST=dpg-d12n0np5pdvs73ctmm40-a")
    print("PGVECTOR_PORT=5432")
    print("PGVECTOR_DATABASE=nexus_memory_db")
    print("PGVECTOR_USER=nexus_memory_db_user")
    print("PGVECTOR_PASSWORD=2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V")
    print("PGPASSWORD=2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V")
    print("ENABLE_PGVECTOR=true")

async def create_fix_script():
    """Create a script to fix the API to include verification"""
    print("\n" + "="*60)
    print("CREATING API FIX FOR DATA VERIFICATION")
    print("="*60)

    fix_content = '''# API Fix for Data Verification

## Add this to the memory creation endpoint in api.py:

```python
@app.post("/memories", response_model=MemoryResponse)
async def create_memory(
    request: MemoryRequest,
    store: UnifiedVectorStore = Depends(get_store)
):
    """Store a memory with verification"""
    try:
        # Store the memory
        memory_result = await store.add(
            content=request.content,
            metadata=request.metadata,
            importance_score=request.importance_score,
            user_id=request.user_id,
            conversation_id=request.conversation_id
        )

        # CRITICAL: Verify the memory was actually stored
        verification_start = time.time()
        max_retries = 3
        verified = False

        for attempt in range(max_retries):
            if attempt > 0:
                await asyncio.sleep(0.5)  # Brief wait between retries

            # Try to retrieve the memory
            search_results = await store.search(
                query="",  # Empty query to get all
                limit=100,
                min_similarity=0.0
            )

            # Check if our memory is in the results
            for result in search_results:
                if result.get("id") == memory_result["id"]:
                    verified = True
                    break

            if verified:
                break

        if not verified:
            # Memory creation failed - data not persisted
            logger.error(f"Memory {memory_result['id']} created but not retrievable")
            raise HTTPException(
                status_code=500,
                detail="Memory storage verification failed - data not persisted"
            )

        logger.info(f"Memory {memory_result['id']} created and verified in {(time.time() - verification_start)*1000:.0f}ms")

        return MemoryResponse(**memory_result)

    except Exception as e:
        logger.error(f"Memory creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```
'''

    with open("/mnt/c/Users/Tyvon/core-nexus/python/memory_service/FIX_API_VERIFICATION.md", "w") as f:
        f.write(fix_content)

    print("✓ Created FIX_API_VERIFICATION.md with verification code")

async def main():
    """Run all diagnostic steps"""
    print("URGENT PGVECTOR FIX DIAGNOSTIC")
    print(f"Timestamp: {datetime.now().isoformat()}")

    # Test external connection
    external_ok = await test_connection(EXTERNAL_DATABASE_URL, "EXTERNAL")

    # If external works, run diagnostics
    if external_ok:
        db_url = EXTERNAL_DATABASE_URL

        # Check pgvector
        await check_pgvector_extension(db_url)

        # Check tables
        await check_tables(db_url)

        # Test vector operations
        await test_vector_operations(db_url)

    # Test internal connection (for production use)
    # Note: This will likely fail from local environment
    await test_connection(INTERNAL_DATABASE_URL, "INTERNAL")

    # Provide recommendations
    await update_environment_recommendation()

    # Create API fix
    await create_fix_script()

    print("\n" + "="*60)
    print("DIAGNOSTIC COMPLETE")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
