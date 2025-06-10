#!/usr/bin/env python3
"""
Check database schema to understand table structure
"""

import asyncio
import asyncpg
import os

async def check_schema():
    connection_string = (
        f"postgresql://{os.getenv('PGVECTOR_USER', 'nexus_memory_db_user')}:"
        f"{os.getenv('PGVECTOR_PASSWORD')}@"
        f"{os.getenv('PGVECTOR_HOST')}:"
        f"{os.getenv('PGVECTOR_PORT', '5432')}/"
        f"{os.getenv('PGVECTOR_DATABASE', 'nexus_memory_db')}"
    )
    
    conn = await asyncpg.connect(connection_string)
    
    # Get column information
    columns = await conn.fetch("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'memories'
        ORDER BY ordinal_position
    """)
    
    print("📊 Table 'memories' columns:")
    for col in columns:
        print(f"  - {col['column_name']} ({col['data_type']})")
    
    # Check if graph tables exist
    graph_tables = await conn.fetch("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name LIKE 'graph%'
    """)
    
    print("\n📊 Graph tables:")
    for table in graph_tables:
        print(f"  - {table['table_name']}")
    
    # Get sample memory
    sample = await conn.fetchrow("SELECT * FROM memories LIMIT 1")
    if sample:
        print("\n📝 Sample memory structure:")
        for key, value in dict(sample).items():
            print(f"  - {key}: {str(value)[:50]}...")
    
    await conn.close()

asyncio.run(check_schema())