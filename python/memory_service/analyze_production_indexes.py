#!/usr/bin/env python3
"""
Analyze production pgvector indexes against best practices.
Based on official pgvector documentation and real-world GitHub issues.
"""

import asyncio
import asyncpg
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def analyze_indexes():
    """Analyze current index configuration and provide recommendations."""
    conn_string = (
        "postgresql://nexus_memory_db_user:2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V@"
        "dpg-d12n0np5pdvs73ctmm40-a.ohio-postgres.render.com:5432/nexus_memory_db"
    )
    
    logger.info("🔍 Analyzing Production pgvector Indexes")
    logger.info("=" * 60)
    
    try:
        conn = await asyncpg.connect(conn_string)
        
        # 1. Get table statistics
        table_stats = await conn.fetchrow("""
            SELECT 
                COUNT(*) as row_count,
                pg_size_pretty(pg_total_relation_size('vector_memories')) as table_size,
                (SELECT COUNT(*) FROM pg_indexes WHERE tablename = 'vector_memories') as index_count
            FROM vector_memories
        """)
        
        logger.info(f"\n📊 Table Statistics:")
        logger.info(f"  Rows: {table_stats['row_count']:,}")
        logger.info(f"  Table Size: {table_stats['table_size']}")
        logger.info(f"  Index Count: {table_stats['index_count']}")
        
        # 2. Get detailed index information
        indexes = await conn.fetch("""
            SELECT 
                indexname,
                indexdef,
                pg_size_pretty(pg_relation_size(indexname::regclass)) as size
            FROM pg_indexes 
            WHERE tablename = 'vector_memories'
            AND indexname LIKE '%embedding%'
            ORDER BY indexname
        """)
        
        logger.info(f"\n🔧 Vector Indexes Found:")
        ivfflat_indexes = []
        hnsw_indexes = []
        
        for idx in indexes:
            logger.info(f"\n  Index: {idx['indexname']}")
            logger.info(f"  Size: {idx['size']}")
            logger.info(f"  Definition: {idx['indexdef'][:100]}...")
            
            if 'ivfflat' in idx['indexdef']:
                ivfflat_indexes.append(idx)
            elif 'hnsw' in idx['indexdef']:
                hnsw_indexes.append(idx)
        
        # 3. Analyze IVFFlat configuration
        if ivfflat_indexes:
            logger.info(f"\n📈 IVFFlat Index Analysis:")
            for idx in ivfflat_indexes:
                # Extract lists parameter from definition
                import re
                lists_match = re.search(r'lists = (\d+)', idx['indexdef'])
                lists = int(lists_match.group(1)) if lists_match else None
                
                if lists:
                    row_count = table_stats['row_count']
                    optimal_lists = max(1, row_count // 1000) if row_count < 1000000 else int(row_count ** 0.5)
                    
                    logger.info(f"\n  Index: {idx['indexname']}")
                    logger.info(f"  Current lists: {lists}")
                    logger.info(f"  Optimal lists (rows/1000): {optimal_lists}")
                    logger.info(f"  Ratio: {lists/optimal_lists:.1f}x")
                    
                    if lists > optimal_lists * 10:
                        logger.warning(f"  ⚠️ WARNING: Too many lists! May cause poor performance")
                        logger.info(f"  Recommendation: Recreate with lists = {optimal_lists}")
                    
                    # Recommended probes
                    recommended_probes = max(1, int(lists ** 0.5))
                    logger.info(f"  Recommended probes: {recommended_probes}")
        
        # 4. Check current probes setting
        probes_setting = await conn.fetchval("SHOW ivfflat.probes")
        logger.info(f"\n⚙️ Current Session Settings:")
        logger.info(f"  ivfflat.probes: {probes_setting} (default is 1)")
        
        # 5. Test index usage with EXPLAIN
        logger.info(f"\n🔬 Testing Index Usage:")
        
        # Generate a sample embedding (1536 dimensions)
        sample_embedding = '[' + ','.join(['0.1'] * 1536) + ']'
        
        explain_result = await conn.fetch(f"""
            EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
            SELECT id, content
            FROM vector_memories
            ORDER BY embedding <=> '{sample_embedding}'::vector
            LIMIT 10
        """)
        
        plan = json.loads(explain_result[0]['QUERY PLAN'])
        execution_time = plan[0]['Execution Time']
        
        # Check if index is being used
        plan_text = json.dumps(plan, indent=2)
        using_index = 'Index Scan' in plan_text or 'ivfflat' in plan_text
        
        logger.info(f"  Using Index: {'✅ YES' if using_index else '❌ NO'}")
        logger.info(f"  Execution Time: {execution_time:.2f}ms")
        
        # 6. Check for common issues
        logger.info(f"\n⚠️ Common Issues Check:")
        
        # Check if table was empty when index was created
        oldest_row = await conn.fetchval("SELECT MIN(created_at) FROM vector_memories")
        logger.info(f"  Oldest row: {oldest_row}")
        
        # Check for NULL embeddings
        null_count = await conn.fetchval("SELECT COUNT(*) FROM vector_memories WHERE embedding IS NULL")
        if null_count > 0:
            logger.warning(f"  ❌ Found {null_count} rows with NULL embeddings!")
        else:
            logger.info(f"  ✅ No NULL embeddings found")
        
        # 7. Recommendations
        logger.info(f"\n📋 Recommendations:")
        
        row_count = table_stats['row_count']
        if row_count < 10000:
            optimal_lists = max(5, row_count // 200)  # More aggressive for small datasets
            optimal_probes = max(3, int(optimal_lists ** 0.5))
            
            logger.info(f"\n  For {row_count:,} rows:")
            logger.info(f"  1. Recreate index with lists = {optimal_lists}")
            logger.info(f"  2. Set ivfflat.probes = {optimal_probes} in queries")
            logger.info(f"  3. Consider HNSW for better accuracy on small datasets")
            
            logger.info(f"\n  SQL to fix:")
            logger.info(f"  ```sql")
            logger.info(f"  -- Drop old index")
            logger.info(f"  DROP INDEX IF EXISTS idx_vector_memories_embedding;")
            logger.info(f"  ")
            logger.info(f"  -- Create optimized index")
            logger.info(f"  CREATE INDEX idx_vector_memories_embedding")
            logger.info(f"  ON vector_memories")
            logger.info(f"  USING ivfflat (embedding vector_cosine_ops)")
            logger.info(f"  WITH (lists = {optimal_lists});")
            logger.info(f"  ")
            logger.info(f"  -- Set probes for session")
            logger.info(f"  SET ivfflat.probes = {optimal_probes};")
            logger.info(f"  ```")
        
        await conn.close()
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False

async def main():
    await analyze_indexes()

if __name__ == "__main__":
    asyncio.run(main())