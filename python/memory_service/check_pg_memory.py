#!/usr/bin/env python3
"""
Check PostgreSQL Memory Configuration
Specifically checks memory settings that could impact vector operations
"""

import asyncio
import asyncpg


async def check_pg_memory():
    """Check PostgreSQL memory configuration"""
    try:
        conn = await asyncpg.connect(
            host="dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com",
            port=5432,
            database="nexus_memory_db",
            user="nexus_memory_db_user",
            password="2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V",
            timeout=10
        )
        
        print("=== POSTGRESQL MEMORY CONFIGURATION ===")
        
        # Get memory-related settings
        memory_settings = await conn.fetch("""
            SELECT name, setting, unit, context, short_desc 
            FROM pg_settings 
            WHERE name IN (
                'shared_buffers',
                'work_mem', 
                'maintenance_work_mem',
                'effective_cache_size',
                'max_connections',
                'wal_buffers',
                'temp_buffers',
                'random_page_cost',
                'seq_page_cost'
            )
            ORDER BY name;
        """)
        
        total_memory_mb = 0
        
        for setting in memory_settings:
            name, value, unit, context, desc = setting
            unit_str = f' {unit}' if unit else ''
            
            # Convert to MB for easier understanding
            mb_value = None
            if unit == '8kB':
                mb_value = int(value) * 8 / 1024
            elif unit == 'kB':
                mb_value = int(value) / 1024
            elif unit == 'MB':
                mb_value = int(value)
                
            print(f'{name}: {value}{unit_str}', end='')
            if mb_value is not None:
                print(f' ({mb_value:.1f} MB)')
                if name in ['shared_buffers', 'work_mem', 'maintenance_work_mem']:
                    total_memory_mb += mb_value
            else:
                print()
            print(f'  {desc}')
            print()
        
        print(f'ESTIMATED CORE MEMORY ALLOCATION: {total_memory_mb:.1f} MB')
        print()
        
        # Get buffer statistics
        buffer_stats = await conn.fetchrow("""
            SELECT 
                buffers_alloc,
                buffers_backend,
                buffers_clean,
                buffers_checkpoint,
                buffers_backend_fsync
            FROM pg_stat_bgwriter;
        """)
        
        print("=== BUFFER STATISTICS ===")
        print(f'Total buffers allocated: {buffer_stats["buffers_alloc"]:,}')
        print(f'Backend buffers written: {buffer_stats["buffers_backend"]:,}')
        print(f'Clean buffers written: {buffer_stats["buffers_clean"]:,}')
        print(f'Checkpoint buffers written: {buffer_stats["buffers_checkpoint"]:,}')
        print(f'Backend fsync calls: {buffer_stats["buffers_backend_fsync"]:,}')
        print()
        
        # Get current memory usage
        memory_stats = await conn.fetchrow("""
            SELECT 
                (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') as active_connections,
                (SELECT count(*) FROM pg_stat_activity) as total_connections,
                pg_size_pretty(pg_database_size(current_database())) as db_size
        """)
        
        print("=== CURRENT USAGE ===")
        print(f'Database size: {memory_stats["db_size"]}')
        print(f'Active connections: {memory_stats["active_connections"]}')
        print(f'Total connections: {memory_stats["total_connections"]}')
        print()
        
        # Check for vector operations memory usage
        vector_stats = await conn.fetchrow("""
            SELECT 
                COUNT(*) as total_vectors,
                COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as vectors_with_embeddings,
                pg_size_pretty(pg_total_relation_size('vector_memories')) as table_size,
                pg_size_pretty(pg_relation_size('vector_memories')) as data_size,
                pg_size_pretty(pg_total_relation_size('vector_memories') - pg_relation_size('vector_memories')) as index_size
            FROM vector_memories;
        """)
        
        print("=== VECTOR TABLE ANALYSIS ===")
        print(f'Total vector records: {vector_stats["total_vectors"]:,}')
        print(f'Records with embeddings: {vector_stats["vectors_with_embeddings"]:,}')
        print(f'Table total size: {vector_stats["table_size"]}')
        print(f'Data size: {vector_stats["data_size"]}')
        print(f'Index size: {vector_stats["index_size"]}')
        print()
        
        # Check HNSW index stats
        index_stats = await conn.fetch("""
            SELECT 
                indexname,
                pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size
            FROM pg_indexes 
            WHERE tablename = 'vector_memories' AND indexdef LIKE '%hnsw%';
        """)
        
        if index_stats:
            print("=== HNSW INDEX SIZES ===")
            for idx in index_stats:
                print(f'{idx["indexname"]}: {idx["index_size"]}')
        print()
        
        await conn.close()
        print("✓ Memory analysis complete")
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(check_pg_memory())