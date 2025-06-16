#!/usr/bin/env python3
"""
Run database migrations for Core Nexus Memory Service
This script applies migrations in order and tracks their execution
"""

import asyncio
import asyncpg
import os
import sys
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_migrations():
    """Run all pending migrations"""
    # Get database connection from environment
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        # Build from individual components
        host = os.getenv('PGVECTOR_HOST', os.getenv('POSTGRES_HOST', 'localhost'))
        port = int(os.getenv('PGVECTOR_PORT', os.getenv('POSTGRES_PORT', '5432')))
        database = os.getenv('PGVECTOR_DATABASE', os.getenv('POSTGRES_DB', 'core_nexus'))
        user = os.getenv('PGVECTOR_USER', os.getenv('POSTGRES_USER', 'postgres'))
        password = os.getenv('PGVECTOR_PASSWORD', os.getenv('POSTGRES_PASSWORD', ''))
        
        if not password:
            logger.error("No database password found in environment")
            return False
            
        database_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    try:
        # Connect to database
        conn = await asyncpg.connect(database_url)
        logger.info("Connected to database")
        
        # Get migration files
        migrations_dir = Path(__file__).parent / 'migrations'
        if not migrations_dir.exists():
            logger.warning("No migrations directory found")
            return True
            
        migration_files = sorted(migrations_dir.glob('*.sql'))
        
        if not migration_files:
            logger.info("No migration files found")
            return True
        
        # Apply each migration
        for migration_file in migration_files:
            migration_name = migration_file.stem
            
            # Check if already applied
            try:
                result = await conn.fetchval(
                    "SELECT 1 FROM schema_migrations WHERE version = $1",
                    migration_name
                )
                if result:
                    logger.info(f"Migration {migration_name} already applied, skipping")
                    continue
            except Exception:
                # Table might not exist yet
                pass
            
            # Run migration
            logger.info(f"Applying migration: {migration_name}")
            try:
                migration_sql = migration_file.read_text()
                await conn.execute(migration_sql)
                logger.info(f"✅ Migration {migration_name} completed successfully")
            except Exception as e:
                logger.error(f"❌ Migration {migration_name} failed: {e}")
                await conn.close()
                return False
        
        await conn.close()
        logger.info("All migrations completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to run migrations: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_migrations())
    sys.exit(0 if success else 1)