#!/usr/bin/env python3
"""
Safe ChromaDB sync using the same configuration as the production service
This uses the existing provider setup to avoid configuration issues
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime

# Add the source directory to the path
sys.path.insert(0, '/mnt/c/Users/Tyvon/core-nexus/python/memory_service/src')

from memory_service.config import config
from memory_service.providers import PgVectorProvider, ChromaProvider
from memory_service.models import ProviderConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("safe_sync")

class SafeChromaDBSync:
    def __init__(self):
        self.stats = {
            "total_memories": 0,
            "synced": 0,
            "failed": 0,
            "start_time": datetime.now().isoformat()
        }

    async def run_sync(self):
        """Run the sync using existing provider configuration"""
        logger.info("🚀 Starting Safe ChromaDB Sync")
        logger.info("="*60)
        
        try:
            # Initialize pgvector provider using production config
            pg_config = ProviderConfig(
                name="pgvector",
                enabled=True,
                primary=True,
                config={
                    "host": config.database.HOST,
                    "port": config.database.PORT,
                    "database": config.database.DATABASE,
                    "user": config.database.USER,
                    "password": config.database.PASSWORD,
                    "pool_min_size": config.database.POOL_MIN_SIZE,
                    "pool_max_size": config.database.POOL_MAX_SIZE,
                    "table_name": config.database.TABLE_NAME,
                }
            )
            
            logger.info("🔌 Initializing pgvector provider...")
            pg_provider = PgVectorProvider(pg_config)
            await pg_provider.initialize()
            
            # Get total count
            self.stats["total_memories"] = await self._get_memory_count(pg_provider)
            logger.info(f"📊 Found {self.stats['total_memories']} memories in pgvector")
            
            # Initialize ChromaDB provider
            chroma_config = ProviderConfig(
                name="chromadb",
                enabled=True,
                primary=False,
                config={
                    "persist_dir": config.providers.CHROMADB_PERSIST_DIR,
                    "collection_name": config.providers.CHROMADB_COLLECTION,
                }
            )
            
            logger.info("🔌 Initializing ChromaDB provider...")
            chroma_provider = ChromaProvider(chroma_config)
            await chroma_provider.initialize()
            
            # Check ChromaDB current state
            chroma_stats = await chroma_provider.get_stats()
            current_chroma_count = chroma_stats.get("total_vectors", 0)
            logger.info(f"📊 ChromaDB currently has {current_chroma_count} vectors")
            
            if current_chroma_count >= self.stats["total_memories"]:
                logger.info("✅ ChromaDB already synchronized!")
                return
            
            # Sync memories in batches
            batch_size = 100
            offset = current_chroma_count  # Resume from where we left off
            
            while offset < self.stats["total_memories"]:
                logger.info(f"📦 Processing batch starting at {offset}")
                
                # Get batch of memories from pgvector
                memories = await self._get_memories_batch(pg_provider, offset, batch_size)
                
                if not memories:
                    break
                
                # Sync to ChromaDB
                success_count = await self._sync_batch_to_chroma(chroma_provider, memories)
                
                self.stats["synced"] += success_count
                self.stats["failed"] += len(memories) - success_count
                
                offset += batch_size
                
                # Progress report
                progress = min(offset / self.stats["total_memories"] * 100, 100)
                logger.info(f"📊 Progress: {progress:.1f}% ({self.stats['synced']}/{self.stats['total_memories']})")
                
                # Small delay
                await asyncio.sleep(0.1)
            
            # Final verification
            final_chroma_stats = await chroma_provider.get_stats()
            final_count = final_chroma_stats.get("total_vectors", 0)
            
            logger.info(f"\n✅ Sync complete!")
            logger.info(f"pgvector: {self.stats['total_memories']} memories")
            logger.info(f"ChromaDB: {final_count} vectors")
            logger.info(f"Successfully synced: {self.stats['synced']}")
            logger.info(f"Failed: {self.stats['failed']}")
            
            await pg_provider.close()
            await chroma_provider.close()
            
        except Exception as e:
            logger.error(f"❌ Sync failed: {e}")
            raise

    async def _get_memory_count(self, provider):
        """Get total memory count from pgvector"""
        async with provider.connection_pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM vector_memories")

    async def _get_memories_batch(self, provider, offset, limit):
        """Get a batch of memories from pgvector"""
        query = """
            SELECT id, content, embedding, metadata, created_at, updated_at
            FROM vector_memories
            ORDER BY created_at ASC
            LIMIT $1 OFFSET $2
        """
        
        async with provider.connection_pool.acquire() as conn:
            rows = await conn.fetch(query, limit, offset)
            
        memories = []
        for row in rows:
            # Convert embedding
            embedding = list(row['embedding']) if row['embedding'] else []
            
            memories.append({
                'id': str(row['id']),
                'content': row['content'],
                'embedding': embedding,
                'metadata': dict(row['metadata']) if row['metadata'] else {},
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            })
            
        return memories

    async def _sync_batch_to_chroma(self, chroma_provider, memories):
        """Sync a batch of memories to ChromaDB"""
        success_count = 0
        
        for memory in memories:
            try:
                await chroma_provider.store(
                    content=memory['content'],
                    embedding=memory['embedding'],
                    metadata={
                        **memory['metadata'],
                        'id': memory['id'],
                        'created_at': memory['created_at'].isoformat() if memory['created_at'] else None,
                        'updated_at': memory['updated_at'].isoformat() if memory['updated_at'] else None,
                        'synced_at': datetime.now().isoformat()
                    }
                )
                success_count += 1
                
            except Exception as e:
                logger.error(f"Failed to sync memory {memory['id']}: {e}")
        
        return success_count

async def main():
    """Main entry point"""
    # Validate configuration
    try:
        config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    
    syncer = SafeChromaDBSync()
    
    try:
        await syncer.run_sync()
        logger.info("🎉 ChromaDB sync completed successfully!")
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Sync interrupted!")
    except Exception as e:
        logger.error(f"❌ Sync failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())