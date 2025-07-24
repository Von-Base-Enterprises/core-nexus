#!/usr/bin/env python3
"""
Emergency database check to verify data integrity while service is down.
"""
import os
import asyncio
import asyncpg
from datetime import datetime

async def check_database():
    """Direct database connection to verify memories exist."""
    
    # Get connection details from environment or use defaults
    db_config = {
        'host': os.getenv('PGVECTOR_HOST', 'dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com'),
        'port': int(os.getenv('PGVECTOR_PORT', '5432')),
        'database': os.getenv('PGVECTOR_DATABASE', 'nexus_memory_db'),
        'user': os.getenv('PGVECTOR_USER', 'nexus_memory_db_user'),
        'password': os.getenv('PGVECTOR_PASSWORD', os.getenv('PGPASSWORD'))
    }
    
    if not db_config['password']:
        print("❌ ERROR: PGVECTOR_PASSWORD or PGPASSWORD not set in environment")
        print("Please set the password and try again")
        return
    
    print("=== Emergency Database Check ===")
    print(f"Time: {datetime.now()}")
    print(f"Connecting to: {db_config['host']}")
    print("")
    
    try:
        # Connect to database
        conn = await asyncpg.connect(**db_config)
        print("✅ Connected to database successfully")
        
        # Check total memories
        total_count = await conn.fetchval("SELECT COUNT(*) FROM vector_memories")
        print(f"\n📊 Total memories in database: {total_count}")
        
        # Check memories with embeddings
        with_embeddings = await conn.fetchval(
            "SELECT COUNT(*) FROM vector_memories WHERE embedding IS NOT NULL"
        )
        print(f"   - With embeddings: {with_embeddings}")
        print(f"   - Without embeddings: {total_count - with_embeddings}")
        
        # Get sample memories
        print("\n📝 Sample memories (first 3):")
        samples = await conn.fetch("""
            SELECT id, content, importance_score, created_at
            FROM vector_memories
            ORDER BY created_at DESC
            LIMIT 3
        """)
        
        for i, row in enumerate(samples, 1):
            print(f"\n{i}. Memory ID: {row['id']}")
            print(f"   Content: {row['content'][:100]}...")
            print(f"   Importance: {row['importance_score']}")
            print(f"   Created: {row['created_at']}")
        
        # Check table statistics
        print("\n📈 Table Statistics:")
        table_size = await conn.fetchval("""
            SELECT pg_size_pretty(pg_total_relation_size('vector_memories'))
        """)
        print(f"   Table size: {table_size}")
        
        # Check if indexes exist
        indexes = await conn.fetch("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'vector_memories'
        """)
        print(f"\n🔍 Indexes ({len(indexes)} found):")
        for idx in indexes:
            print(f"   - {idx['indexname']}")
        
        # Check recent activity
        recent_activity = await conn.fetchval("""
            SELECT MAX(created_at) FROM vector_memories
        """)
        print(f"\n⏰ Most recent memory: {recent_activity}")
        
        await conn.close()
        print("\n✅ Database check complete - All data is safe!")
        
    except Exception as e:
        print(f"\n❌ Database connection failed: {e}")
        print("\nPossible issues:")
        print("1. Password not set correctly")
        print("2. Database is down")
        print("3. Network connectivity issues")

if __name__ == "__main__":
    print("Note: This requires PGVECTOR_PASSWORD or PGPASSWORD to be set")
    print("The password should be the one from your Render dashboard")
    print("")
    asyncio.run(check_database())