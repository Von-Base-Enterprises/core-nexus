#!/usr/bin/env python3
"""
Database State Validator
Check current state of vector migration and system status.
"""

import asyncio
import asyncpg
import os
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def validate_database_state():
    """Check current state of the database and migration."""
    
    # Database connection parameters
    db_config = {
        'host': os.getenv('PGVECTOR_HOST', 'dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com'),
        'port': int(os.getenv('PGVECTOR_PORT', '5432')),
        'database': os.getenv('PGVECTOR_DATABASE', 'nexus_memory_db'),
        'user': os.getenv('PGVECTOR_USER', 'nexus_memory_db_user'),
        'password': os.getenv('PGVECTOR_PASSWORD')
    }
    
    if not db_config['password']:
        logger.error("PGVECTOR_PASSWORD environment variable is required")
        return
    
    connection = None
    try:
        # Connect to database
        logger.info("Connecting to production database...")
        connection = await asyncpg.connect(**db_config)
        
        print("\n" + "="*60)
        print("CORE NEXUS DATABASE STATE VALIDATION")
        print("="*60)
        
        # 1. Check original vector_memories table
        logger.info("Checking original vector_memories table...")
        original_count = await connection.fetchval(
            "SELECT COUNT(*) FROM vector_memories WHERE embedding IS NOT NULL"
        )
        
        # Get sample dimension from original table
        original_dimensions = await connection.fetchval(
            "SELECT array_length(embedding, 1) FROM vector_memories WHERE embedding IS NOT NULL LIMIT 1"
        )
        
        print(f"\n📊 ORIGINAL TABLE (vector_memories):")
        print(f"   Vectors with embeddings: {original_count}")
        print(f"   Vector dimensions: {original_dimensions}")
        
        # 2. Check optimized table exists and count
        logger.info("Checking optimized vector_memories_optimized table...")
        try:
            optimized_count = await connection.fetchval(
                "SELECT COUNT(*) FROM vector_memories_optimized WHERE embedding IS NOT NULL"
            )
            
            optimized_dimensions = await connection.fetchval(
                "SELECT array_length(embedding, 1) FROM vector_memories_optimized WHERE embedding IS NOT NULL LIMIT 1"
            )
            
            print(f"\n🚀 OPTIMIZED TABLE (vector_memories_optimized):")
            print(f"   Vectors with embeddings: {optimized_count}")
            print(f"   Vector dimensions: {optimized_dimensions}")
            
        except Exception as e:
            print(f"\n❌ OPTIMIZED TABLE: Not found or error - {e}")
            optimized_count = 0
            optimized_dimensions = None
        
        # 3. Check migration progress
        logger.info("Checking migration progress...")
        try:
            migration_progress = await connection.fetchrow(
                "SELECT * FROM migration_progress ORDER BY created_at DESC LIMIT 1"
            )
            
            if migration_progress:
                print(f"\n📈 MIGRATION PROGRESS:")
                print(f"   Status: {migration_progress['migration_status']}")
                print(f"   Total to migrate: {migration_progress['total_vectors_to_migrate']}")
                print(f"   Total migrated: {migration_progress['total_vectors_migrated']}")
                progress_pct = (migration_progress['total_vectors_migrated'] / migration_progress['total_vectors_to_migrate'] * 100) if migration_progress['total_vectors_to_migrate'] > 0 else 0
                print(f"   Progress: {progress_pct:.1f}%")
                
                remaining = migration_progress['total_vectors_to_migrate'] - migration_progress['total_vectors_migrated']
                print(f"   Remaining vectors: {remaining}")
            else:
                print(f"\n❌ MIGRATION PROGRESS: No tracking data found")
                
        except Exception as e:
            print(f"\n❌ MIGRATION PROGRESS: Error - {e}")
        
        # 4. Check recent migration batches
        logger.info("Checking recent migration batches...")
        try:
            recent_batches = await connection.fetch(
                "SELECT batch_number, status, total_vectors, migrated_vectors, failed_vectors FROM migration_batches ORDER BY batch_number DESC LIMIT 5"
            )
            
            if recent_batches:
                print(f"\n📦 RECENT MIGRATION BATCHES:")
                for batch in recent_batches:
                    success_rate = (batch['migrated_vectors'] / batch['total_vectors'] * 100) if batch['total_vectors'] > 0 else 0
                    print(f"   Batch {batch['batch_number']}: {batch['status']} - {batch['migrated_vectors']}/{batch['total_vectors']} vectors ({success_rate:.1f}% success)")
            else:
                print(f"\n❌ MIGRATION BATCHES: No batch data found")
                
        except Exception as e:
            print(f"\n❌ MIGRATION BATCHES: Error - {e}")
        
        # 5. Summary analysis
        print(f"\n" + "="*60)
        print("ANALYSIS SUMMARY")
        print("="*60)
        
        if original_dimensions and original_dimensions > 1536:
            dimension_ratio = original_dimensions / 1536
            print(f"✅ DIMENSION MISMATCH CONFIRMED:")
            print(f"   Original: {original_dimensions}D vs Target: 1,536D")
            print(f"   Inefficiency ratio: {dimension_ratio:.1f}x")
            print(f"   Optimization potential: {((dimension_ratio - 1) / dimension_ratio * 100):.1f}% improvement")
        
        if optimized_count > 0:
            migration_pct = (optimized_count / original_count * 100) if original_count > 0 else 0
            remaining_vectors = original_count - optimized_count
            print(f"\n✅ MIGRATION STATE:")
            print(f"   Migration completion: {migration_pct:.1f}%")
            print(f"   Vectors migrated: {optimized_count}")
            print(f"   Vectors remaining: {remaining_vectors}")
            print(f"   Ready to resume: {'YES' if remaining_vectors > 0 else 'COMPLETE'}")
        else:
            print(f"\n❌ MIGRATION STATE: No optimized vectors found")
        
        # Current system performance baseline
        print(f"\n📊 CURRENT PERFORMANCE OPPORTUNITY:")
        if original_dimensions:
            storage_reduction = ((original_dimensions - 1536) / original_dimensions * 100)
            print(f"   Storage reduction potential: {storage_reduction:.1f}%")
            print(f"   Query performance potential: ~{original_dimensions//1536}x faster")
            print(f"   Memory efficiency gain: ~{original_dimensions//1536}x")
            
        print(f"\n" + "="*60)
        
    except Exception as e:
        logger.error(f"Database validation failed: {e}")
        print(f"\n❌ DATABASE VALIDATION FAILED: {e}")
        
    finally:
        if connection:
            await connection.close()

if __name__ == "__main__":
    asyncio.run(validate_database_state())