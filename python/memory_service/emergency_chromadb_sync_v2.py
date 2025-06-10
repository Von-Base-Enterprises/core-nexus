#!/usr/bin/env python3
"""
Emergency ChromaDB Sync v2 - Production Ready
Copies all vectors from pgvector to ChromaDB with progress tracking
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime

import asyncpg
import chromadb
from chromadb.config import Settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("emergency_sync")

# Configuration
BATCH_SIZE = 100
CHECKPOINT_FILE = "chromadb_sync_checkpoint.json"

class EmergencyChromaDBSync:
    def __init__(self):
        self.pg_conn = None
        self.chroma_client = None
        self.collection = None
        self.checkpoint = self.load_checkpoint()
        self.stats = {
            "total_memories": 0,
            "synced": 0,
            "failed": 0,
            "skipped": 0,
            "start_time": datetime.now().isoformat()
        }

    def load_checkpoint(self) -> dict:
        """Load sync checkpoint if exists"""
        if os.path.exists(CHECKPOINT_FILE):
            with open(CHECKPOINT_FILE) as f:
                logger.info(f"📂 Loaded checkpoint from {CHECKPOINT_FILE}")
                return json.load(f)
        return {"last_synced_id": None, "synced_ids": []}

    def save_checkpoint(self):
        """Save current sync progress"""
        with open(CHECKPOINT_FILE, 'w') as f:
            json.dump(self.checkpoint, f)
        logger.info(f"💾 Checkpoint saved: {self.stats['synced']} memories synced")

    async def connect_postgres(self):
        """Connect to PostgreSQL/pgvector"""
        pg_password = os.getenv("PGVECTOR_PASSWORD", "2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V")
        pg_host = os.getenv("PGVECTOR_HOST", "dpg-d12n0np5pdvs73ctmm40-a.ohio-postgres.render.com")
        pg_database = os.getenv("PGVECTOR_DATABASE", "nexus_memory_db")
        pg_user = os.getenv("PGVECTOR_USER", "nexus_memory_db_user")

        conn_string = f"postgresql://{pg_user}:{pg_password}@{pg_host}:5432/{pg_database}"

        logger.info("🔌 Connecting to PostgreSQL...")
        self.pg_conn = await asyncpg.connect(conn_string)

        # Get total count
        self.stats["total_memories"] = await self.pg_conn.fetchval(
            "SELECT COUNT(*) FROM vector_memories"
        )
        logger.info(f"✅ Connected to PostgreSQL. Found {self.stats['total_memories']} memories")

    def connect_chromadb(self):
        """Connect to ChromaDB"""
        logger.info("🔌 Connecting to ChromaDB...")

        # Use production ChromaDB URL if available
        chroma_host = os.getenv("CHROMA_HOST", "localhost")
        chroma_port = os.getenv("CHROMA_PORT", "8000")

        if chroma_host != "localhost":
            # Production mode - connect to remote ChromaDB
            self.chroma_client = chromadb.HttpClient(
                host=chroma_host,
                port=int(chroma_port),
                settings=Settings(anonymized_telemetry=False)
            )
            logger.info(f"Connected to remote ChromaDB at {chroma_host}:{chroma_port}")
        else:
            # Local mode - use persistent client
            persist_dir = "./memory_service_chroma"
            os.makedirs(persist_dir, exist_ok=True)

            self.chroma_client = chromadb.PersistentClient(
                path=persist_dir,
                settings=Settings(anonymized_telemetry=False)
            )
            logger.info(f"Connected to local ChromaDB at {persist_dir}")

        # Get or create collection
        try:
            self.collection = self.chroma_client.get_collection("memories")
            existing_count = self.collection.count()
            logger.info(f"✅ Using existing collection. Current vectors: {existing_count}")
        except Exception:
            self.collection = self.chroma_client.create_collection(
                name="memories",
                metadata={"description": "Core Nexus memory vectors"}
            )
            logger.info("✅ Created new ChromaDB collection")

    async def fetch_memories_batch(self, offset: int, limit: int) -> list[dict]:
        """Fetch a batch of memories from pgvector"""
        query = """
            SELECT
                id,
                content,
                embedding,
                metadata,
                created_at,
                updated_at
            FROM vector_memories
            ORDER BY created_at ASC
            LIMIT $1 OFFSET $2
        """

        rows = await self.pg_conn.fetch(query, limit, offset)

        memories = []
        for row in rows:
            # Convert embedding from pgvector format to list
            embedding_str = row['embedding']
            if isinstance(embedding_str, str):
                # Parse pgvector string format [0.1,0.2,...]
                embedding_str = embedding_str.strip('[]')
                embedding = [float(x) for x in embedding_str.split(',')]
            else:
                embedding = list(row['embedding'])

            memories.append({
                'id': str(row['id']),
                'content': row['content'],
                'embedding': embedding,
                'metadata': row['metadata'] or {},
                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
            })

        return memories

    def sync_batch_to_chromadb(self, memories: list[dict]) -> dict[str, int]:
        """Sync a batch of memories to ChromaDB"""
        results = {"success": 0, "failed": 0, "skipped": 0}

        # Check which memories already exist
        [m['id'] for m in memories]

        # Skip if already synced (based on checkpoint)
        new_memories = []
        for memory in memories:
            if memory['id'] not in self.checkpoint['synced_ids']:
                new_memories.append(memory)
            else:
                results['skipped'] += 1

        if not new_memories:
            return results

        # Prepare batch for ChromaDB
        ids = []
        embeddings = []
        documents = []
        metadatas = []

        for memory in new_memories:
            ids.append(memory['id'])
            embeddings.append(memory['embedding'])
            documents.append(memory['content'])

            # Prepare metadata
            metadata = memory['metadata'].copy() if memory['metadata'] else {}
            metadata['created_at'] = memory['created_at']
            metadata['updated_at'] = memory['updated_at']
            metadata['synced_from'] = 'pgvector'
            metadata['sync_time'] = datetime.now().isoformat()

            metadatas.append(metadata)

        # Add to ChromaDB
        try:
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )

            # Update checkpoint
            self.checkpoint['synced_ids'].extend(ids)
            self.checkpoint['last_synced_id'] = ids[-1]

            results['success'] = len(ids)
            logger.info(f"✅ Synced {len(ids)} memories to ChromaDB")

        except Exception as e:
            logger.error(f"❌ Failed to sync batch: {e}")
            results['failed'] = len(ids)

        return results

    async def run_sync(self):
        """Run the complete sync process"""
        logger.info("🚀 Starting Emergency ChromaDB Sync")
        logger.info("="*60)

        # Connect to databases
        await self.connect_postgres()
        self.connect_chromadb()

        # Sync in batches
        offset = 0
        batch_num = 0

        while offset < self.stats['total_memories']:
            batch_num += 1
            logger.info(f"\n📦 Processing batch {batch_num} (offset: {offset})")

            # Fetch batch from pgvector
            memories = await self.fetch_memories_batch(offset, BATCH_SIZE)

            if not memories:
                break

            # Sync to ChromaDB
            results = self.sync_batch_to_chromadb(memories)

            # Update stats
            self.stats['synced'] += results['success']
            self.stats['failed'] += results['failed']
            self.stats['skipped'] += results['skipped']

            # Save checkpoint every batch
            self.save_checkpoint()

            # Progress report
            progress = (offset + len(memories)) / self.stats['total_memories'] * 100
            logger.info(f"📊 Progress: {progress:.1f}% ({self.stats['synced']}/{self.stats['total_memories']})")

            offset += BATCH_SIZE

            # Small delay to avoid overwhelming the system
            await asyncio.sleep(0.1)

        # Final verification
        await self.verify_sync()

        # Cleanup
        await self.pg_conn.close()

        # Final report
        self.print_final_report()

    async def verify_sync(self):
        """Verify the sync was successful"""
        logger.info("\n🔍 Verifying sync...")

        # Check ChromaDB count
        chroma_count = self.collection.count()
        pg_count = self.stats['total_memories']

        logger.info(f"📊 pgvector memories: {pg_count}")
        logger.info(f"📊 ChromaDB vectors: {chroma_count}")

        if chroma_count >= pg_count - self.stats['failed']:
            logger.info("✅ Sync verification PASSED!")
        else:
            logger.warning(f"⚠️ Sync verification warning: ChromaDB has {chroma_count} vectors, expected ~{pg_count}")

    def print_final_report(self):
        """Print final sync report"""
        duration = (datetime.now() - datetime.fromisoformat(self.stats['start_time'])).total_seconds()

        print("\n" + "="*60)
        print("🎉 EMERGENCY CHROMADB SYNC COMPLETE!")
        print("="*60)
        print(f"Total memories in pgvector: {self.stats['total_memories']}")
        print(f"Successfully synced: {self.stats['synced']}")
        print(f"Failed: {self.stats['failed']}")
        print(f"Skipped (already synced): {self.stats['skipped']}")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Rate: {self.stats['synced']/duration:.1f} memories/second")
        print("="*60)

        # Save final stats
        with open('chromadb_sync_report.json', 'w') as f:
            json.dump({
                'stats': self.stats,
                'duration_seconds': duration,
                'timestamp': datetime.now().isoformat(),
                'success': self.stats['failed'] == 0
            }, f, indent=2)

        print("📋 Full report saved to chromadb_sync_report.json")


async def main():
    """Main entry point"""
    syncer = EmergencyChromaDBSync()

    try:
        await syncer.run_sync()

        # Remove checkpoint file on successful completion
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
            logger.info("🧹 Cleaned up checkpoint file")

    except KeyboardInterrupt:
        logger.warning("\n⚠️ Sync interrupted! Run again to resume from checkpoint.")
    except Exception as e:
        logger.error(f"❌ Sync failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("🚨 EMERGENCY CHROMADB SYNC")
    print("This will copy all vectors from pgvector to ChromaDB")
    print("="*60)

    asyncio.run(main())
