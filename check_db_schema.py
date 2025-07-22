#!/usr/bin/env python3
"""
Check actual database schema and vector format.
"""

import asyncio
import asyncpg

DB_URL = "postgresql://nexus_memory_db_user:2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V@dpg-d12n0np5pdvs73ctmm40-a.ohio-postgres.render.com:5432/nexus_memory_db"

async def check_schema():
    """Check database schema and sample data"""
    conn = await asyncpg.connect(DB_URL)
    
    print("🔍 Database Schema Analysis")
    print("===========================\n")
    
    # Check table structure
    schema = await conn.fetch("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'vector_memories'
        ORDER BY ordinal_position
    """)
    
    print("📋 Table Structure:")
    for col in schema:
        print(f"  {col['column_name']}: {col['data_type']} {'(nullable)' if col['is_nullable'] == 'YES' else '(not null)'}")
    
    print()
    
    # Check index details
    indexes = await conn.fetch("""
        SELECT 
            i.relname AS index_name,
            pg_size_pretty(pg_relation_size(i.oid)) AS size,
            am.amname AS type,
            idx.indoption,
            pg_get_indexdef(idx.indexrelid) AS definition
        FROM pg_index idx
        JOIN pg_class i ON i.oid = idx.indexrelid
        JOIN pg_class t ON t.oid = idx.indrelid
        JOIN pg_am am ON i.relam = am.oid
        WHERE t.relname = 'vector_memories'
    """)
    
    print("📊 Indexes:")
    for idx in indexes:
        print(f"  {idx['index_name']} ({idx['type']}): {idx['size']}")
        print(f"    Definition: {idx['definition']}")
    
    print()
    
    # Check sample data
    sample = await conn.fetchrow("""
        SELECT id, content, embedding, metadata, created_at
        FROM vector_memories 
        LIMIT 1
    """)
    
    if sample:
        print("📝 Sample Record:")
        print(f"  ID: {sample['id']}")
        print(f"  Content: {sample['content'][:100]}...")
        print(f"  Embedding type: {type(sample['embedding'])}")
        print(f"  Embedding dimensions: {len(sample['embedding']) if sample['embedding'] else 'None'}")
        if sample['embedding']:
            print(f"  First 5 values: {sample['embedding'][:5]}")
        print(f"  Metadata: {sample['metadata']}")
        print(f"  Created: {sample['created_at']}")
    
    print()
    
    # Check current probes setting
    try:
        probes = await conn.fetchval("SHOW ivfflat.probes")
        print(f"🔧 Current probes setting: {probes}")
    except Exception as e:
        print(f"❌ Could not check probes: {e}")
    
    # Check index stats
    try:
        stats = await conn.fetchrow("""
            SELECT 
                schemaname,
                tablename,
                indexname,
                idx_tup_read,
                idx_tup_fetch
            FROM pg_stat_user_indexes
            WHERE tablename = 'vector_memories'
        """)
        if stats:
            print(f"📈 Index Usage: read={stats['idx_tup_read']}, fetch={stats['idx_tup_fetch']}")
    except Exception as e:
        print(f"❌ Could not get index stats: {e}")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(check_schema())