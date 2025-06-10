#!/usr/bin/env python3
"""Emergency script to fix Core Nexus database indexes"""

import asyncio

import asyncpg


async def fix_database():
    # Database connection info
    DATABASE_URL = "postgresql://nexus_memory_db_user:2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V@dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com/nexus_memory_db"

    print("🔧 Connecting to Core Nexus database...")

    try:
        # Connect to database
        conn = await asyncpg.connect(DATABASE_URL)
        print("✅ Connected successfully!")

        # Create the critical vector index
        print("\n📊 Creating vector similarity index...")
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_vector_memories_embedding 
            ON vector_memories 
            USING ivfflat (embedding vector_cosine_ops) 
            WITH (lists = 100)
        """)
        print("✅ Vector index created!")

        # Create metadata index
        print("\n📊 Creating metadata index...")
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_vector_memories_metadata 
            ON vector_memories USING GIN (metadata)
        """)
        print("✅ Metadata index created!")

        # Create importance score index
        print("\n📊 Creating importance score index...")
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_vector_memories_importance 
            ON vector_memories (importance_score DESC)
        """)
        print("✅ Importance index created!")

        # Update statistics
        print("\n📊 Updating table statistics...")
        await conn.execute("ANALYZE vector_memories")
        print("✅ Statistics updated!")

        # Verify indexes
        print("\n🔍 Verifying indexes...")
        indexes = await conn.fetch("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename = 'vector_memories'
            ORDER BY indexname
        """)

        print("\n📋 Indexes created:")
        for idx in indexes:
            print(f"   - {idx['indexname']}")

        # Test query
        print("\n🧪 Testing vector query...")
        count = await conn.fetchval("SELECT COUNT(*) FROM vector_memories")
        print(f"✅ Total memories in database: {count}")

        await conn.close()

        print("\n🎉 SUCCESS! Database indexes created!")
        print("✅ Queries should now work properly!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

    return True

if __name__ == "__main__":
    success = asyncio.run(fix_database())
    if success:
        print("\n🚀 Now test the API:")
        print('curl -X POST https://core-nexus-memory-service.onrender.com/memories/query -H "Content-Type: application/json" -d \'{"query": "test", "limit": 5}\'')
