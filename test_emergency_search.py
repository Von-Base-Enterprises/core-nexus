#!/usr/bin/env python3

import asyncio
import asyncpg
import os
import json
from datetime import datetime

async def test_emergency_search():
    """Test the emergency search logic to find the issue."""
    
    # Database connection parameters
    config = {
        'host': 'dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com',
        'port': 5432,
        'database': 'nexus_memory_db',
        'user': 'nexus_memory_db_user',
        'password': os.getenv('PGVECTOR_PASSWORD')
    }
    
    if not config['password']:
        print("ERROR: PGVECTOR_PASSWORD environment variable not set")
        return
    
    try:
        # Create connection
        conn = await asyncpg.connect(**config)
        
        print("=== Emergency Search Debug ===")
        
        # Test 1: Check table existence and schema
        table_info = await conn.fetch("""
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_name = 'vector_memories' 
               OR table_name LIKE '%memor%'
               OR table_name LIKE '%vector%'
            ORDER BY table_schema, table_name
        """)
        
        print(f"Tables found: {[(t['table_schema'], t['table_name']) for t in table_info]}")
        
        # Test 2: Check total count 
        total_count = await conn.fetchval("SELECT COUNT(*) FROM public.vector_memories")
        print(f"Total rows in vector_memories: {total_count}")
        
        # Test 3: Check content column values
        content_stats = await conn.fetch("""
            SELECT 
                COUNT(*) as total,
                COUNT(content) as content_not_null,
                COUNT(CASE WHEN content IS NOT NULL AND content != '' THEN 1 END) as content_not_empty
            FROM public.vector_memories
        """)
        
        print(f"Content stats: {dict(content_stats[0])}")
        
        # Test 4: Check sample content values
        sample_content = await conn.fetch("""
            SELECT content, length(content) as content_length
            FROM public.vector_memories 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        
        print("Sample content values:")
        for row in sample_content:
            content = row['content']
            length = row['content_length']
            print(f"  Length: {length}, Content: {repr(content[:100])}...")
        
        # Test 5: Try the exact emergency search query
        print(f"\n=== Testing Emergency Search Query ===")
        rows = await conn.fetch("""
            SELECT 
                id, 
                content, 
                metadata, 
                importance_score,
                created_at
            FROM public.vector_memories
            WHERE content IS NOT NULL
            ORDER BY created_at DESC
            LIMIT $1
        """, 5)
        
        print(f"Emergency search returned {len(rows)} rows")
        
        # Test 6: Try without WHERE clause
        rows_no_filter = await conn.fetch("""
            SELECT 
                id, 
                content, 
                metadata, 
                importance_score,
                created_at
            FROM public.vector_memories
            ORDER BY created_at DESC
            LIMIT $1
        """, 5)
        
        print(f"Query without WHERE clause returned {len(rows_no_filter)} rows")
        
        # Test 7: Check for any rows with content issues
        problem_rows = await conn.fetch("""
            SELECT COUNT(*) as count, 
                   content IS NULL as is_null,
                   content = '' as is_empty,
                   length(content) as len
            FROM public.vector_memories
            GROUP BY content IS NULL, content = '', length(content)
            ORDER BY count DESC
        """)
        
        print(f"\nContent analysis:")
        for row in problem_rows:
            print(f"  Count: {row['count']}, NULL: {row['is_null']}, Empty: {row['is_empty']}, Length: {row['len']}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals():
            await conn.close()

if __name__ == "__main__":
    asyncio.run(test_emergency_search())