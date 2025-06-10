#!/usr/bin/env python3
"""
Test pgvector connection with exact production environment variables
"""

import asyncio

import asyncpg


async def test_connection():
    """Test connection with production settings"""

    # Production settings from debug endpoint
    host = "dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com"
    port = 5432
    database = "nexus_memory_db"
    user = "nexus_memory_db_user"
    password = "2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V"

    print("Testing connection to pgvector:")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  Database: {database}")
    print(f"  User: {user}")
    print()

    # Test direct connection
    try:
        print("Attempting direct connection...")
        conn = await asyncpg.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            timeout=10
        )
        print("✓ Direct connection successful!")

        # Test query
        count = await conn.fetchval("SELECT COUNT(*) FROM vector_memories")
        print(f"✓ Query successful - found {count} memories")

        await conn.close()

    except Exception as e:
        print(f"✗ Connection failed: {str(e)}")
        print(f"  Error type: {type(e).__name__}")

    # Test with connection string
    try:
        print("\nTesting with connection string...")
        conn_str = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        conn = await asyncpg.connect(conn_str, timeout=10)
        print("✓ Connection string successful!")
        await conn.close()

    except Exception as e:
        print(f"✗ Connection string failed: {str(e)}")

    # Check what might be different in production
    print("\nPossible issues:")
    print("1. Check if PGPASSWORD env var is also needed")
    print("2. Check if there's a firewall blocking the connection")
    print("3. Check if SSL is required (add ?sslmode=require)")
    print("4. Check if the service was restarted after env vars were added")

if __name__ == "__main__":
    asyncio.run(test_connection())
