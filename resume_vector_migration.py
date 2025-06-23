#!/usr/bin/env python3
"""
Resume Vector Migration
Completes the vector dimension optimization migration from 19k+ dimensions to 1,536D.
"""

import asyncio
import asyncpg
import json
import logging
import os
import sys
import time
import openai
from datetime import datetime
from typing import Dict, List, Any, Optional
import uuid

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VectorMigrationResumer:
    """Resumes the vector dimension optimization migration."""
    
    def __init__(self):
        """Initialize the migration resumer."""
        self.connection_pool = None
        
        # Database configuration
        self.db_config = {
            'host': os.getenv('PGVECTOR_HOST', 'dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com'),
            'port': int(os.getenv('PGVECTOR_PORT', '5432')),
            'database': os.getenv('PGVECTOR_DATABASE', 'nexus_memory_db'),
            'user': os.getenv('PGVECTOR_USER', 'nexus_memory_db_user'),
            'password': os.getenv('PGVECTOR_PASSWORD')
        }
        
        if not self.db_config['password']:
            print("❌ PGVECTOR_PASSWORD environment variable is required")
            print("Please set the password to continue with migration.")
            sys.exit(1)
        
        # OpenAI configuration
        openai.api_key = os.getenv('OPENAI_API_KEY')
        if not openai.api_key:
            print("❌ OPENAI_API_KEY environment variable is required") 
            sys.exit(1)
        
        # Migration configuration
        self.batch_size = 25  # Based on previous successful batches
        self.max_retries = 3
        self.retry_delay = 5
    
    async def connect_to_database(self):
        """Connect to the production database."""
        logger.info("🔌 Connecting to production database...")
        
        conn_str = (
            f"postgresql://{self.db_config['user']}:{self.db_config['password']}@"
            f"{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
        )
        
        self.connection_pool = await asyncpg.create_pool(
            conn_str,
            min_size=2,
            max_size=5,
            command_timeout=60
        )
        
        logger.info("✅ Database connection established")
    
    async def assess_migration_state(self) -> Dict[str, Any]:
        """Assess the current state of the migration."""
        logger.info("📊 Assessing current migration state...")
        
        async with self.connection_pool.acquire() as conn:
            # Check original table
            original_count = await conn.fetchval(
                "SELECT COUNT(*) FROM vector_memories WHERE embedding IS NOT NULL"
            )
            
            # Check optimized table  
            try:
                optimized_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM vector_memories_optimized WHERE embedding IS NOT NULL"
                )
            except Exception:
                optimized_count = 0
            
            # Check migration progress
            try:
                progress = await conn.fetchrow(
                    "SELECT * FROM migration_progress ORDER BY created_at DESC LIMIT 1"
                )
            except Exception:
                progress = None
            
            # Get unmigrated vectors (vectors in original but not in optimized)
            unmigrated_query = """
            SELECT id, content, embedding 
            FROM vector_memories vm
            WHERE vm.embedding IS NOT NULL 
                AND NOT EXISTS (
                    SELECT 1 FROM vector_memories_optimized vmo 
                    WHERE vmo.id = vm.id
                )
            ORDER BY vm.created_at
            """
            
            unmigrated_vectors = await conn.fetch(unmigrated_query)
            
            state = {
                'original_count': original_count,
                'optimized_count': optimized_count,
                'unmigrated_count': len(unmigrated_vectors),
                'unmigrated_vectors': unmigrated_vectors,
                'progress': progress
            }
            
            logger.info(f"📈 Migration State:")
            logger.info(f"   Original vectors: {original_count}")
            logger.info(f"   Optimized vectors: {optimized_count}")
            logger.info(f"   Unmigrated vectors: {len(unmigrated_vectors)}")
            
            if progress:
                progress_pct = (optimized_count / original_count * 100) if original_count > 0 else 0
                logger.info(f"   Progress: {progress_pct:.1f}%")
            
            return state
    
    async def create_embedding(self, text: str) -> List[float]:
        """Create a 1,536-dimensional embedding using OpenAI."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai.api_key)
            
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding creation failed: {e}")
            raise
    
    async def migrate_batch(self, vectors: List[Dict], batch_number: int) -> Dict[str, Any]:
        """Migrate a batch of vectors."""
        batch_id = str(uuid.uuid4())
        batch_start = time.time()
        
        logger.info(f"🚀 Starting batch {batch_number} with {len(vectors)} vectors")
        
        async with self.connection_pool.acquire() as conn:
            # Create batch record
            await conn.execute("""
                INSERT INTO migration_batches 
                (batch_id, batch_number, total_vectors, status, started_at)
                VALUES ($1, $2, $3, 'in_progress', NOW())
            """, batch_id, batch_number, len(vectors))
            
            successful_migrations = 0
            failed_migrations = 0
            
            for vector in vectors:
                try:
                    # Skip vectors with content too large for OpenAI
                    content = vector['content']
                    if len(content) > 300000:  # Skip very large content
                        logger.warning(f"   ⚠️  Skipping vector {vector['id']} - content too large ({len(content)} chars)")
                        failed_migrations += 1
                        continue
                    
                    # Create new embedding
                    new_embedding = await self.create_embedding(content)
                    
                    # Insert into optimized table with proper vector format
                    await conn.execute("""
                        INSERT INTO vector_memories_optimized 
                        (id, content, embedding, metadata, migration_status, migration_timestamp, migration_batch_id)
                        VALUES ($1, $2, $3::vector, $4::jsonb, 'migrated', NOW(), $5)
                        ON CONFLICT (id) DO UPDATE SET
                            content = EXCLUDED.content,
                            embedding = EXCLUDED.embedding,
                            migration_status = 'migrated',
                            migration_timestamp = NOW()
                    """, 
                    vector['id'], 
                    content, 
                    str(new_embedding),  # Convert to string for vector type
                    '{}',  # metadata as JSON string
                    batch_id
                    )
                    
                    successful_migrations += 1
                    logger.info(f"   ✅ Migrated vector {vector['id']}")
                    
                    # Rate limiting - small delay between API calls
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"   ❌ Failed to migrate vector {vector['id']}: {e}")
                    failed_migrations += 1
            
            # Update batch record
            batch_duration = time.time() - batch_start
            success_rate = successful_migrations / len(vectors) if len(vectors) > 0 else 0
            
            await conn.execute("""
                UPDATE migration_batches 
                SET migrated_vectors = $1, 
                    failed_vectors = $2,
                    status = $3,
                    completed_at = NOW()
                WHERE batch_id = $4
            """, 
            successful_migrations, 
            failed_migrations,
            'completed' if failed_migrations == 0 else 'failed',
            batch_id
            )
            
            # Update overall progress
            await conn.execute("""
                UPDATE migration_progress 
                SET total_vectors_migrated = total_vectors_migrated + $1,
                    completed_batches = completed_batches + 1
                WHERE id IN (SELECT id FROM migration_progress ORDER BY created_at DESC LIMIT 1)
            """, successful_migrations)
            
            batch_result = {
                'batch_id': batch_id,
                'batch_number': batch_number,
                'successful_migrations': successful_migrations,
                'failed_migrations': failed_migrations,
                'success_rate': success_rate,
                'duration_seconds': batch_duration
            }
            
            logger.info(f"✅ Batch {batch_number} completed: {successful_migrations}/{len(vectors)} successful ({success_rate:.1%})")
            
            return batch_result
    
    async def resume_migration(self):
        """Resume the vector migration process."""
        logger.info("🔄 Starting vector migration resume...")
        
        # Assess current state
        state = await self.assess_migration_state()
        
        if state['unmigrated_count'] == 0:
            logger.info("🎉 Migration already complete!")
            return
        
        unmigrated_vectors = state['unmigrated_vectors']
        logger.info(f"📋 Resuming migration for {len(unmigrated_vectors)} vectors")
        
        # Process in batches
        total_batches = (len(unmigrated_vectors) + self.batch_size - 1) // self.batch_size
        batch_results = []
        
        # Get the next batch number
        async with self.connection_pool.acquire() as conn:
            last_batch_num = await conn.fetchval(
                "SELECT COALESCE(MAX(batch_number), 0) FROM migration_batches"
            )
        
        start_batch_num = last_batch_num + 1
        
        for i in range(0, len(unmigrated_vectors), self.batch_size):
            batch_number = start_batch_num + (i // self.batch_size)
            batch_vectors = unmigrated_vectors[i:i + self.batch_size]
            
            try:
                batch_result = await self.migrate_batch(batch_vectors, batch_number)
                batch_results.append(batch_result)
                
                logger.info(f"📊 Progress: {len(batch_results)}/{total_batches} batches completed")
                
            except Exception as e:
                logger.error(f"❌ Batch {batch_number} failed: {e}")
                break
        
        # Final assessment
        final_state = await self.assess_migration_state()
        
        total_successful = sum(r['successful_migrations'] for r in batch_results)
        total_failed = sum(r['failed_migrations'] for r in batch_results)
        
        logger.info(f"\n🎯 Migration Resume Complete!")
        logger.info(f"   Vectors processed: {total_successful + total_failed}")
        logger.info(f"   Successful: {total_successful}")
        logger.info(f"   Failed: {total_failed}")
        logger.info(f"   Final optimized count: {final_state['optimized_count']}")
        logger.info(f"   Remaining unmigrated: {final_state['unmigrated_count']}")
        
        if final_state['unmigrated_count'] == 0:
            logger.info("🚀 MIGRATION COMPLETE! All vectors have been optimized.")
        
        # Save results (exclude non-serializable data)
        results = {
            'timestamp': datetime.now().isoformat(),
            'migration_resumed': True,
            'batches_processed': len(batch_results),
            'total_successful': total_successful,
            'total_failed': total_failed,
            'final_state': {
                'original_count': final_state['original_count'],
                'optimized_count': final_state['optimized_count'],
                'unmigrated_count': final_state['unmigrated_count']
            },
            'batch_results': batch_results
        }
        
        results_file = f"migration_resume_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"📄 Results saved to: {results_file}")
        
        return results

async def main():
    """Main function to resume the migration."""
    migrator = VectorMigrationResumer()
    
    try:
        await migrator.connect_to_database()
        results = await migrator.resume_migration()
        
        print("\n" + "="*60)
        print("MIGRATION RESUME COMPLETED")
        print("="*60)
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)
    finally:
        if migrator.connection_pool:
            await migrator.connection_pool.close()

if __name__ == "__main__":
    asyncio.run(main())