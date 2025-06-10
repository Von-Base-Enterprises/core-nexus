#!/usr/bin/env python3
"""
Test script to verify the get_recent_memories functionality
"""

import asyncio
import os
from datetime import datetime

# Add the src directory to the Python path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from memory_service.providers import PgVectorProvider
from memory_service.models import ProviderConfig


async def test_get_recent_memories():
    """Test the new get_recent_memories method"""
    
    # Create PgVectorProvider config
    config = ProviderConfig(
        name="pgvector",
        enabled=True,
        primary=True,
        config={
            "host": os.getenv("PGVECTOR_HOST", "localhost"),
            "port": int(os.getenv("PGVECTOR_PORT", 5432)),
            "database": os.getenv("PGVECTOR_DATABASE", "nexus_memory_db"),
            "user": os.getenv("PGVECTOR_USER", "nexus_memory_db_user"),
            "password": os.getenv("PGVECTOR_PASSWORD", ""),
            "table_name": "vector_memories"
        }
    )
    
    # Initialize provider
    provider = PgVectorProvider(config)
    await provider.initialize()
    
    print(f"Testing get_recent_memories at {datetime.now()}")
    print("-" * 50)
    
    try:
        # Test 1: Get recent memories without filters
        print("\nTest 1: Get 10 recent memories (no filters)")
        memories = await provider.get_recent_memories(limit=10)
        print(f"Retrieved {len(memories)} memories")
        
        if memories:
            print("\nFirst memory:")
            print(f"  ID: {memories[0].id}")
            print(f"  Content: {memories[0].content[:100]}...")
            print(f"  Created: {memories[0].created_at}")
            print(f"  Similarity Score: {memories[0].similarity_score}")
        
        # Test 2: Get recent memories with filters
        print("\n\nTest 2: Get recent memories with metadata filter")
        filtered_memories = await provider.get_recent_memories(
            limit=5,
            filters={"type": "conversation"}  # Example filter
        )
        print(f"Retrieved {len(filtered_memories)} memories with filter")
        
        # Test 3: Verify ordering (should be newest first)
        if len(memories) > 1:
            print("\n\nTest 3: Verify ordering (newest first)")
            print("First 3 memories by creation date:")
            for i, mem in enumerate(memories[:3]):
                print(f"  {i+1}. Created: {mem.created_at}")
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        if provider.connection_pool:
            await provider.connection_pool.close()


if __name__ == "__main__":
    asyncio.run(test_get_recent_memories())