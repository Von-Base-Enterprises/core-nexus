#!/usr/bin/env python3
"""
Ensure pgvector indexes exist on startup.

This script is run before the main application starts to ensure
all required database indexes are created.
"""

import asyncio
import asyncpg
import logging
import os
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def ensure_indexes():
    """Create pgvector indexes if they don't exist."""
    # Get database connection info from environment
    db_config = {
        'host': os.getenv('PGVECTOR_HOST', os.getenv('PGHOST', 'localhost')),
        'port': int(os.getenv('PGVECTOR_PORT', os.getenv('PGPORT', '5432'))),
        'database': os.getenv('PGVECTOR_DATABASE', os.getenv('PGDATABASE', 'core_nexus')),
        'user': os.getenv('PGVECTOR_USER', os.getenv('PGUSER', 'postgres')),
        'password': os.getenv('PGVECTOR_PASSWORD', os.getenv('PGPASSWORD', ''))
    }
    
    if not db_config['password']:
        logger.error("Database password not set. Please set PGVECTOR_PASSWORD or PGPASSWORD.")
        return False
    
    try:
        # Connect to database
        conn = await asyncpg.connect(**db_config)
        logger.info(f"Connected to database {db_config['database']} on {db_config['host']}")
        
        # Check if table exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'vector_memories'
            )
        """)
        
        if not table_exists:
            logger.warning("Table 'vector_memories' does not exist. Skipping index creation.")
            await conn.close()
            return True
        
        # Create indexes
        indexes = [
            {
                'name': 'idx_vector_memories_embedding',
                'sql': """
                    CREATE INDEX IF NOT EXISTS idx_vector_memories_embedding 
                    ON vector_memories 
                    USING ivfflat (embedding vector_cosine_ops) 
                    WITH (lists = 100)
                """
            },
            {
                'name': 'idx_vector_memories_metadata',
                'sql': """
                    CREATE INDEX IF NOT EXISTS idx_vector_memories_metadata 
                    ON vector_memories 
                    USING GIN (metadata)
                """
            },
            {
                'name': 'idx_vector_memories_importance',
                'sql': """
                    CREATE INDEX IF NOT EXISTS idx_vector_memories_importance 
                    ON vector_memories (importance_score DESC)
                """
            },
            {
                'name': 'idx_vector_memories_created_importance',
                'sql': """
                    CREATE INDEX IF NOT EXISTS idx_vector_memories_created_importance 
                    ON vector_memories (created_at DESC, importance_score DESC)
                """
            }
        ]
        
        for index in indexes:
            try:
                await conn.execute(index['sql'])
                logger.info(f"✓ Ensured index: {index['name']}")
            except Exception as e:
                logger.error(f"✗ Failed to create index {index['name']}: {e}")
        
        # Update table statistics
        await conn.execute("ANALYZE vector_memories")
        logger.info("✓ Updated table statistics")
        
        # Verify indexes
        index_count = await conn.fetchval("""
            SELECT COUNT(*) 
            FROM pg_indexes 
            WHERE tablename = 'vector_memories'
        """)
        logger.info(f"Total indexes on vector_memories: {index_count}")
        
        await conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to ensure indexes: {e}")
        return False


def main():
    """Main entry point."""
    success = asyncio.run(ensure_indexes())
    if success:
        logger.info("Index verification completed successfully")
        sys.exit(0)
    else:
        logger.error("Index verification failed")
        sys.exit(1)


if __name__ == "__main__":
    main()