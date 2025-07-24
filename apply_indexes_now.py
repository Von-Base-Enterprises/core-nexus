#!/usr/bin/env python3
"""
Apply pgvector indexes to production database immediately.
"""

import asyncio
import asyncpg
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def apply_indexes():
    """Apply indexes to production database."""
    # Production connection details
    conn_string = (
        "postgresql://nexus_memory_db_user:2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V@"
        "dpg-d12n0np5pdvs73ctmm40-a.ohio-postgres.render.com:5432/nexus_memory_db"
    )
    
    logger.info("Connecting to production database...")
    
    try:
        conn = await asyncpg.connect(conn_string)
        logger.info("✅ Connected successfully")
        
        # Check current indexes
        logger.info("\nChecking existing indexes...")
        existing_indexes = await conn.fetch("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename = 'vector_memories'
        """)
        
        logger.info(f"Found {len(existing_indexes)} existing indexes:")
        for idx in existing_indexes:
            logger.info(f"  - {idx['indexname']}")
        
        # Create indexes
        indexes_to_create = [
            ("idx_vector_memories_embedding", """
                CREATE INDEX IF NOT EXISTS idx_vector_memories_embedding 
                ON vector_memories 
                USING ivfflat (embedding vector_cosine_ops) 
                WITH (lists = 100)
            """),
            ("idx_vector_memories_metadata", """
                CREATE INDEX IF NOT EXISTS idx_vector_memories_metadata 
                ON vector_memories 
                USING GIN (metadata)
            """),
            ("idx_vector_memories_importance", """
                CREATE INDEX IF NOT EXISTS idx_vector_memories_importance 
                ON vector_memories (importance_score DESC)
            """),
            ("idx_vector_memories_created_importance", """
                CREATE INDEX IF NOT EXISTS idx_vector_memories_created_importance 
                ON vector_memories (created_at DESC, importance_score DESC)
            """)
        ]
        
        logger.info("\n🔧 Creating indexes...")
        for index_name, create_sql in indexes_to_create:
            try:
                logger.info(f"Creating {index_name}...")
                await conn.execute(create_sql)
                logger.info(f"✅ {index_name} created successfully")
            except Exception as e:
                logger.error(f"❌ Failed to create {index_name}: {e}")
        
        # Update statistics
        logger.info("\nUpdating table statistics...")
        await conn.execute("ANALYZE vector_memories")
        logger.info("✅ Statistics updated")
        
        # Verify indexes
        logger.info("\n📊 Verifying indexes...")
        final_indexes = await conn.fetch("""
            SELECT 
                indexname,
                pg_size_pretty(pg_relation_size(indexname::regclass)) as size
            FROM pg_indexes 
            WHERE tablename = 'vector_memories'
            ORDER BY indexname
        """)
        
        logger.info(f"\nFinal index count: {len(final_indexes)}")
        for idx in final_indexes:
            logger.info(f"  - {idx['indexname']} (size: {idx['size']})")
        
        # Check if the critical IVFFlat index exists
        has_ivfflat = any(idx['indexname'] == 'idx_vector_memories_embedding' for idx in final_indexes)
        
        if has_ivfflat:
            logger.info("\n✅ SUCCESS! IVFFlat index created - queries should be fast now!")
        else:
            logger.warning("\n⚠️ WARNING: IVFFlat index may not have been created properly")
        
        await conn.close()
        return has_ivfflat
        
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        return False


def main():
    """Main entry point."""
    success = asyncio.run(apply_indexes())
    
    if success:
        print("\n🎉 Indexes applied successfully!")
        print("Run 'python3 python/memory_service/test_query_fix.py' to verify performance")
        return 0
    else:
        print("\n❌ Failed to apply indexes properly")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())