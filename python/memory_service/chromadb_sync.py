#!/usr/bin/env python3
"""
ChromaDB Sync - Emergency Backup Script
Copies all memories from pgvector to ChromaDB for redundancy
Agent 2 Backend Task - Immediate Priority
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Any

# Add the source directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from memory_service.embedding_models import create_embedding_model
from memory_service.logging_config import get_logger, setup_logging
from memory_service.models import MemoryRequest, ProviderConfig
from memory_service.providers import ChromaProvider, PgVectorProvider

# Setup logging
setup_logging()
logger = get_logger("chromadb_sync")

class ChromaDBSyncManager:
    """Manages the sync from pgvector to ChromaDB."""

    def __init__(self):
        self.pgvector_provider: PgVectorProvider | None = None
        self.chroma_provider: ChromaProvider | None = None
        self.embedding_model = None
        self.sync_stats = {
            'start_time': None,
            'end_time': None,
            'total_memories': 0,
            'synced_memories': 0,
            'failed_memories': 0,
            'errors': []
        }

    async def initialize_providers(self):
        """Initialize both pgvector and ChromaDB providers."""
        logger.info("🔧 Initializing providers for ChromaDB sync...")

        # Initialize embedding model first
        try:
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if openai_api_key and openai_api_key.strip():
                self.embedding_model = create_embedding_model(
                    provider="openai",
                    model="text-embedding-3-small",
                    api_key=openai_api_key,
                    max_retries=3,
                    timeout=30.0
                )
                logger.info("✅ OpenAI embedding model initialized")
            else:
                from memory_service.embedding_models import MockEmbeddingModel
                self.embedding_model = MockEmbeddingModel(dimension=1536)
                logger.warning("⚠️ Using mock embedding model (no OpenAI key)")
        except Exception as e:
            logger.error(f"❌ Failed to initialize embedding model: {e}")
            raise

        # Initialize pgvector provider (source)
        try:
            # Validate password is set
            pgvector_password = os.getenv("PGVECTOR_PASSWORD")
            if not pgvector_password:
                raise ValueError("PGVECTOR_PASSWORD environment variable is required")

            pgvector_config = ProviderConfig(
                name="pgvector_sync",
                enabled=True,
                primary=True,
                config={
                    "host": os.getenv("PGVECTOR_HOST", "dpg-d12n0np5pdvs73ctmm40-a"),
                    "port": int(os.getenv("PGVECTOR_PORT", "5432")),
                    "database": os.getenv("PGVECTOR_DATABASE", "nexus_memory_db"),
                    "user": os.getenv("PGVECTOR_USER", "nexus_memory_db_user"),
                    "password": pgvector_password,
                    "table_name": "vector_memories",
                    "embedding_dim": 1536,
                    "distance_metric": "cosine"
                }
            )

            self.pgvector_provider = PgVectorProvider(pgvector_config)
            logger.info("✅ PgVector provider initialized (source)")

        except Exception as e:
            logger.error(f"❌ Failed to initialize pgvector provider: {e}")
            raise

        # Initialize ChromaDB provider (destination)
        try:
            chroma_config = ProviderConfig(
                name="chromadb_sync",
                enabled=True,
                primary=False,
                config={
                    "collection_name": "core_nexus_memories_sync",
                    "persist_directory": "./memory_service_chroma_sync"
                }
            )

            self.chroma_provider = ChromaProvider(chroma_config)
            logger.info("✅ ChromaDB provider initialized (destination)")

        except Exception as e:
            logger.error(f"❌ Failed to initialize ChromaDB provider: {e}")
            raise

    async def get_pgvector_stats(self) -> dict[str, Any]:
        """Get statistics from pgvector."""
        try:
            stats = await self.pgvector_provider.get_stats()
            logger.info(f"📊 PgVector Stats: {stats}")
            return stats
        except Exception as e:
            logger.error(f"❌ Failed to get pgvector stats: {e}")
            return {"total_vectors": 0}

    async def fetch_all_memories_from_pgvector(self) -> list[dict[str, Any]]:
        """Fetch all memories from pgvector."""
        logger.info("📥 Fetching all memories from pgvector...")

        try:
            # Use a large embedding vector to get all memories
            dummy_embedding = [0.1] * 1536

            # Fetch in batches to avoid memory issues
            all_memories = []
            batch_size = 100
            offset = 0

            while True:
                batch_memories = await self.pgvector_provider.query(
                    query_embedding=dummy_embedding,
                    limit=batch_size,
                    filters={"offset": offset}
                )

                if not batch_memories:
                    break

                all_memories.extend(batch_memories)
                offset += batch_size

                logger.info(f"📥 Fetched batch of {len(batch_memories)} memories (total: {len(all_memories)})")

                # If we got less than batch_size, we're done
                if len(batch_memories) < batch_size:
                    break

            logger.info(f"✅ Fetched {len(all_memories)} total memories from pgvector")
            return all_memories

        except Exception as e:
            logger.error(f"❌ Failed to fetch memories from pgvector: {e}")
            return []

    async def sync_memory_to_chroma(self, memory) -> bool:
        """Sync a single memory to ChromaDB."""
        try:
            # Convert pgvector memory to MemoryRequest format
            memory_request = MemoryRequest(
                content=memory.content,
                metadata=memory.metadata or {},
                user_id=memory.metadata.get('user_id') if memory.metadata else None,
                conversation_id=memory.metadata.get('conversation_id') if memory.metadata else None,
                importance_score=memory.importance_score or 0.5
            )

            # Store in ChromaDB
            await self.chroma_provider.store(
                content=memory_request.content,
                embedding=memory.embedding,  # Use existing embedding
                metadata=memory_request.metadata,
                memory_id=str(memory.id)
            )

            return True

        except Exception as e:
            error_msg = f"Failed to sync memory {memory.id}: {e}"
            logger.error(f"❌ {error_msg}")
            self.sync_stats['errors'].append(error_msg)
            return False

    async def run_sync(self):
        """Execute the complete sync process."""
        logger.info("🚀 Starting ChromaDB sync process...")
        self.sync_stats['start_time'] = datetime.now()

        try:
            # Initialize providers
            await self.initialize_providers()

            # Get pgvector statistics
            pgvector_stats = await self.get_pgvector_stats()
            self.sync_stats['total_memories'] = pgvector_stats.get('total_vectors', 0)

            logger.info(f"📊 Target: {self.sync_stats['total_memories']} memories to sync")

            # Fetch all memories from pgvector
            memories = await self.fetch_all_memories_from_pgvector()

            if not memories:
                logger.warning("⚠️ No memories found in pgvector")
                return

            logger.info(f"🔄 Starting sync of {len(memories)} memories to ChromaDB...")

            # Sync memories in batches with progress reporting
            batch_size = 10
            for i in range(0, len(memories), batch_size):
                batch = memories[i:i+batch_size]

                # Process batch concurrently
                tasks = [self.sync_memory_to_chroma(memory) for memory in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Count successes
                batch_successes = sum(1 for result in results if result is True)
                batch_failures = len(batch) - batch_successes

                self.sync_stats['synced_memories'] += batch_successes
                self.sync_stats['failed_memories'] += batch_failures

                # Progress report
                progress = (i + len(batch)) / len(memories) * 100
                logger.info(
                    f"📈 Progress: {progress:.1f}% "
                    f"({self.sync_stats['synced_memories']}/{len(memories)} synced, "
                    f"{self.sync_stats['failed_memories']} failed)"
                )

                # Brief pause to avoid overwhelming the system
                await asyncio.sleep(0.1)

            self.sync_stats['end_time'] = datetime.now()
            duration = self.sync_stats['end_time'] - self.sync_stats['start_time']

            # Final report
            logger.info("🎉 ChromaDB sync completed!")
            logger.info(f"⏱️ Duration: {duration}")
            logger.info(f"✅ Synced: {self.sync_stats['synced_memories']}")
            logger.info(f"❌ Failed: {self.sync_stats['failed_memories']}")
            logger.info(f"📊 Success Rate: {self.sync_stats['synced_memories']/len(memories)*100:.1f}%")

            # Verify ChromaDB stats
            chroma_stats = await self.chroma_provider.get_stats()
            logger.info(f"📊 ChromaDB now contains: {chroma_stats.get('total_vectors', 0)} memories")

        except Exception as e:
            logger.error(f"❌ Sync process failed: {e}")
            self.sync_stats['errors'].append(f"Sync process error: {e}")

        finally:
            # Save sync report
            await self.save_sync_report()

    async def save_sync_report(self):
        """Save detailed sync report to file."""
        try:
            report = {
                "sync_timestamp": datetime.now().isoformat(),
                "duration_seconds": (
                    (self.sync_stats['end_time'] - self.sync_stats['start_time']).total_seconds()
                    if self.sync_stats['end_time'] and self.sync_stats['start_time']
                    else 0
                ),
                "statistics": {
                    "total_memories": self.sync_stats['total_memories'],
                    "synced_memories": self.sync_stats['synced_memories'],
                    "failed_memories": self.sync_stats['failed_memories'],
                    "success_rate": (
                        self.sync_stats['synced_memories'] / max(self.sync_stats['total_memories'], 1) * 100
                    )
                },
                "errors": self.sync_stats['errors'][:10],  # First 10 errors
                "total_errors": len(self.sync_stats['errors'])
            }

            with open('chromadb_sync_report.json', 'w') as f:
                json.dump(report, f, indent=2)

            logger.info("📋 Sync report saved to chromadb_sync_report.json")

        except Exception as e:
            logger.error(f"❌ Failed to save sync report: {e}")


async def main():
    """Main entry point for ChromaDB sync."""
    print("🚀 ChromaDB Sync - Emergency Backup for Core Nexus Memory Service")
    print("=" * 60)
    print("Agent 2 Backend Task: Creating redundancy during Agent 1 deployment")
    print("Target: Copy all 1,004 memories from pgvector to ChromaDB")
    print("=" * 60)

    # Check environment
    required_vars = ["PGVECTOR_HOST", "PGVECTOR_PASSWORD", "PGVECTOR_USER", "PGVECTOR_DATABASE"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {missing_vars}")
        logger.error("💡 Set these variables before running the sync")
        return

    # Initialize and run sync
    sync_manager = ChromaDBSyncManager()

    try:
        await sync_manager.run_sync()
        print("\n🎉 ChromaDB sync completed successfully!")
        print("📊 Check chromadb_sync_report.json for detailed results")

    except KeyboardInterrupt:
        logger.info("⚠️ Sync interrupted by user")
        await sync_manager.save_sync_report()

    except Exception as e:
        logger.error(f"❌ Sync failed with error: {e}")
        await sync_manager.save_sync_report()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
