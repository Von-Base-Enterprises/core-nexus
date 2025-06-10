#!/usr/bin/env python3
"""
Test PgVectorProvider initialization with production settings
"""

import asyncio
import os

from src.memory_service.models import ProviderConfig
from src.memory_service.providers import PgVectorProvider


async def test_init():
    """Test provider initialization"""

    # Set environment variables
    os.environ['PGVECTOR_HOST'] = 'dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com'
    os.environ['PGVECTOR_PORT'] = '5432'
    os.environ['PGVECTOR_DATABASE'] = 'nexus_memory_db'
    os.environ['PGVECTOR_USER'] = 'nexus_memory_db_user'
    os.environ['PGVECTOR_PASSWORD'] = '2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V'
    os.environ['PGPASSWORD'] = '2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V'

    config = ProviderConfig(
        name="pgvector",
        enabled=True,
        primary=False,
        config={
            "host": os.getenv("PGVECTOR_HOST"),
            "port": int(os.getenv("PGVECTOR_PORT", "5432")),
            "database": os.getenv("PGVECTOR_DATABASE"),
            "user": os.getenv("PGVECTOR_USER"),
            "password": os.getenv("PGPASSWORD") or os.getenv("PGVECTOR_PASSWORD"),
            "table_name": "vector_memories",
            "embedding_dim": 1536,
            "distance_metric": "cosine"
        }
    )

    print("Configuration:")
    for key, value in config.config.items():
        if key == 'password':
            print(f"  {key}: {'SET' if value else 'NOT SET'}")
        else:
            print(f"  {key}: {value}")

    try:
        print("\nInitializing PgVectorProvider...")
        provider = PgVectorProvider(config)

        # Wait a moment for async initialization
        await asyncio.sleep(2)

        print(f"Provider enabled: {provider.enabled}")
        print(f"Connection pool: {'READY' if provider.connection_pool else 'NOT READY'}")

        if provider.enabled and provider.connection_pool:
            # Test connection
            async with provider.connection_pool.acquire() as conn:
                count = await conn.fetchval("SELECT COUNT(*) FROM vector_memories")
                print(f"✓ Connection successful! Found {count} memories")
        else:
            print("✗ Provider not initialized properly")

    except Exception as e:
        print(f"✗ Initialization failed: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_init())
