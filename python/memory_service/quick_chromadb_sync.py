#!/usr/bin/env python3
"""
Quick ChromaDB Sync - Emergency Backup
Simplified version using direct database access for immediate execution
Agent 2 Backend Task - Immediate Priority
"""

import asyncio
import json
import os
import time
from datetime import datetime
from typing import Any

import asyncpg
import requests

# Production configuration
RENDER_POSTGRES_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{os.getenv('PGVECTOR_USER', 'nexus_memory_db_user')}:"
    f"{os.getenv('PGVECTOR_PASSWORD')}@"
    f"{os.getenv('PGVECTOR_HOST', 'dpg-d12n0np5pdvs73ctmm40-a')}:"
    f"{os.getenv('PGVECTOR_PORT', '5432')}/"
    f"{os.getenv('PGVECTOR_DATABASE', 'nexus_memory_db')}"
)

CORE_NEXUS_API = "https://core-nexus-memory-service.onrender.com"

class QuickSyncManager:
    """Simplified sync manager for immediate execution."""

    def __init__(self):
        self.stats = {
            'start_time': datetime.now(),
            'memories_fetched': 0,
            'memories_synced': 0,
            'errors': []
        }

    async def fetch_all_memories_from_postgres(self) -> list[dict[str, Any]]:
        """Fetch all memories directly from PostgreSQL."""
        print("📥 Connecting to PostgreSQL to fetch memories...")

        try:
            conn = await asyncpg.connect(RENDER_POSTGRES_URL)

            # Get total count first
            count_query = "SELECT COUNT(*) FROM vector_memories"
            total_count = await conn.fetchval(count_query)
            print(f"📊 Total memories in pgvector: {total_count}")

            # Fetch all memory data
            fetch_query = """
                SELECT
                    id,
                    content,
                    embedding,
                    metadata,
                    user_id,
                    conversation_id,
                    importance_score,
                    created_at
                FROM vector_memories
                ORDER BY created_at DESC
            """

            rows = await conn.fetch(fetch_query)
            await conn.close()

            memories = []
            for row in rows:
                memory = {
                    'id': str(row['id']),
                    'content': row['content'],
                    'embedding': list(row['embedding']) if row['embedding'] else None,
                    'metadata': dict(row['metadata']) if row['metadata'] else {},
                    'user_id': row['user_id'],
                    'conversation_id': row['conversation_id'],
                    'importance_score': float(row['importance_score']) if row['importance_score'] else 0.5,
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None
                }
                memories.append(memory)

            self.stats['memories_fetched'] = len(memories)
            print(f"✅ Fetched {len(memories)} memories from pgvector")
            return memories

        except Exception as e:
            error_msg = f"Failed to fetch from PostgreSQL: {e}"
            print(f"❌ {error_msg}")
            self.stats['errors'].append(error_msg)
            return []

    def store_memory_via_api(self, memory: dict[str, Any]) -> bool:
        """Store a single memory via Core Nexus API."""
        try:
            # Prepare memory request
            memory_request = {
                "content": memory['content'],
                "metadata": memory['metadata'],
                "user_id": memory['user_id'],
                "conversation_id": memory['conversation_id'],
                "importance_score": memory['importance_score']
            }

            # Add original ID to metadata for tracking
            memory_request['metadata']['original_id'] = memory['id']
            memory_request['metadata']['sync_source'] = 'pgvector'
            memory_request['metadata']['sync_timestamp'] = datetime.now().isoformat()

            # POST to memory API
            response = requests.post(
                f"{CORE_NEXUS_API}/memories",
                json=memory_request,
                timeout=30
            )

            if response.status_code == 200:
                return True
            else:
                error_msg = f"API error {response.status_code}: {response.text[:100]}"
                self.stats['errors'].append(error_msg)
                return False

        except Exception as e:
            error_msg = f"Failed to store memory {memory['id']}: {e}"
            self.stats['errors'].append(error_msg)
            return False

    async def sync_memories_batch(self, memories: list[dict[str, Any]], batch_size: int = 5):
        """Sync memories in batches to avoid overwhelming the API."""
        total = len(memories)

        for i in range(0, total, batch_size):
            batch = memories[i:i+batch_size]

            print(f"🔄 Syncing batch {i//batch_size + 1} ({len(batch)} memories)...")

            # Process batch (sequential to avoid rate limits)
            for memory in batch:
                success = self.store_memory_via_api(memory)
                if success:
                    self.stats['memories_synced'] += 1

                # Brief pause between requests
                time.sleep(0.2)

            # Progress report
            progress = min(i + batch_size, total) / total * 100
            print(f"📈 Progress: {progress:.1f}% ({self.stats['memories_synced']}/{total} synced)")

            # Longer pause between batches
            if i + batch_size < total:
                await asyncio.sleep(1)

    async def verify_sync_status(self):
        """Verify how many memories are now in the system."""
        try:
            response = requests.get(f"{CORE_NEXUS_API}/memories/stats", timeout=10)
            if response.status_code == 200:
                stats = response.json()
                print(f"📊 Memory Service Stats: {stats}")
                return stats
        except Exception as e:
            print(f"⚠️ Could not verify sync status: {e}")
        return None

    async def run_sync(self):
        """Execute the complete sync process."""
        print("🚀 Starting Quick ChromaDB Sync...")
        print("🎯 Copying all memories from pgvector to ChromaDB via API")

        # Check if API is accessible
        try:
            response = requests.get(f"{CORE_NEXUS_API}/health", timeout=10)
            if response.status_code != 200:
                print(f"❌ Core Nexus API not accessible: {response.status_code}")
                return
            print("✅ Core Nexus API is accessible")
        except Exception as e:
            print(f"❌ Cannot reach Core Nexus API: {e}")
            return

        # Fetch all memories from pgvector
        memories = await self.fetch_all_memories_from_postgres()
        if not memories:
            print("❌ No memories to sync")
            return

        # Sync memories in batches
        await self.sync_memories_batch(memories)

        # Final verification
        await self.verify_sync_status()

        # Calculate final stats
        duration = datetime.now() - self.stats['start_time']
        success_rate = (self.stats['memories_synced'] / self.stats['memories_fetched']) * 100

        print("\n🎉 Quick ChromaDB Sync Complete!")
        print(f"⏱️ Duration: {duration}")
        print(f"📊 Fetched: {self.stats['memories_fetched']} memories")
        print(f"✅ Synced: {self.stats['memories_synced']} memories")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        print(f"❌ Errors: {len(self.stats['errors'])}")

        # Save detailed report
        with open('quick_sync_report.json', 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'duration_seconds': duration.total_seconds(),
                'stats': self.stats,
                'errors': self.stats['errors'][:10]  # First 10 errors
            }, f, indent=2)

        print("📋 Detailed report saved to quick_sync_report.json")


async def main():
    """Main entry point."""
    print("=" * 60)
    print("🚀 QUICK CHROMADB SYNC - EMERGENCY BACKUP")
    print("Agent 2 Backend Task: Creating redundancy NOW")
    print("Target: Copy all 1,004 memories from pgvector to ChromaDB")
    print("=" * 60)

    # Check environment
    if not os.getenv("PGVECTOR_PASSWORD"):
        print("❌ PGVECTOR_PASSWORD environment variable required")
        return 1

    sync_manager = QuickSyncManager()
    await sync_manager.run_sync()
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
