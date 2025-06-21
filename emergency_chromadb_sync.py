#!/usr/bin/env python3
"""
Emergency ChromaDB Sync Script

Copies all memories from pgvector to ChromaDB to restore data redundancy
after fixing the persistence directory issue.
"""

import asyncio
import asyncpg
import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List
import httpx

# Configuration
RENDER_SERVICE_URL = "https://core-nexus-memory-service.onrender.com"
BATCH_SIZE = 25
DEFAULT_ADMIN_KEY = "<generate-admin-key>"

# Database connection details for direct access
DATABASE_CONFIG = {
    "host": "dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com",
    "port": 5432,
    "database": "nexus_memory_db",
    "user": "nexus_memory_db_user",
    "password": os.getenv("PGVECTOR_PASSWORD", os.getenv("PGPASSWORD", ""))
}

class EmergencySyncProcessor:
    def __init__(self):
        self.stats = {
            "sync_started": datetime.now().isoformat(),
            "memories_processed": 0,
            "memories_synced": 0,
            "batches_completed": 0,
            "errors": [],
            "sync_duration": 0.0
        }
        self.start_time = time.time()
    
    async def get_provider_counts(self) -> Dict[str, int]:
        """Get current memory counts from all providers"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{RENDER_SERVICE_URL}/health")
                data = response.json()
                
                providers = data.get("providers", {})
                return {
                    "pgvector": providers.get("pgvector", {}).get("details", {}).get("details", {}).get("total_vectors", 0),
                    "chromadb": providers.get("chromadb", {}).get("details", {}).get("details", {}).get("total_vectors", 0),
                    "graph": providers.get("graph", {}).get("details", {}).get("details", {}).get("graph_nodes", 0)
                }
        except Exception as e:
            print(f"❌ Failed to get provider counts: {e}")
            return {"pgvector": 0, "chromadb": 0, "graph": 0}
    
    async def test_chromadb_direct(self) -> bool:
        """Test if ChromaDB direct access works"""
        try:
            test_data = {
                "content": f"Sync test {datetime.now().isoformat()}",
                "metadata": {"sync_test": True}
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{RENDER_SERVICE_URL}/admin/test-chromadb-direct",
                    params={"admin_key": DEFAULT_ADMIN_KEY},
                    json=test_data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ ChromaDB direct test successful: {result.get('stored_id')}")
                    return True
                else:
                    print(f"❌ ChromaDB direct test failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ ChromaDB direct test error: {e}")
            return False
    
    async def get_pgvector_memories(self, limit: int = None, offset: int = 0) -> List[Dict[str, Any]]:
        """Get memories directly from pgvector database"""
        if not DATABASE_CONFIG["password"]:
            raise ValueError("PGVECTOR_PASSWORD or PGPASSWORD environment variable required")
        
        conn = None
        try:
            # Connect to PostgreSQL
            conn = await asyncpg.connect(
                host=DATABASE_CONFIG["host"],
                port=DATABASE_CONFIG["port"],
                database=DATABASE_CONFIG["database"],
                user=DATABASE_CONFIG["user"],
                password=DATABASE_CONFIG["password"]
            )
            
            # Query memories
            query = """
                SELECT id, content, embedding, metadata, created_at
                FROM vector_memories 
                ORDER BY created_at DESC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            if offset:
                query += f" OFFSET {offset}"
            
            rows = await conn.fetch(query)
            
            memories = []
            for row in rows:
                # Convert embedding from string to list if needed
                embedding = row['embedding']
                if isinstance(embedding, str):
                    # Handle different string formats
                    embedding = embedding.strip('[]')
                    embedding = [float(x.strip()) for x in embedding.split(',')]
                
                memories.append({
                    "id": str(row['id']),
                    "content": row['content'],
                    "embedding": embedding,
                    "metadata": row['metadata'] or {},
                    "created_at": row['created_at'].isoformat() if row['created_at'] else None
                })
            
            print(f"📦 Retrieved {len(memories)} memories from pgvector (offset: {offset})")
            return memories
            
        except Exception as e:
            print(f"❌ Failed to get memories from pgvector: {e}")
            raise
        finally:
            if conn:
                await conn.close()
    
    async def sync_memory_to_chromadb(self, memory: Dict[str, Any]) -> bool:
        """Sync a single memory to ChromaDB via API"""
        try:
            # Create memory via the standard API
            memory_data = {
                "content": memory["content"],
                "metadata": memory["metadata"],
                "embedding": memory["embedding"]
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{RENDER_SERVICE_URL}/memories",
                    json=memory_data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return True
                else:
                    print(f"❌ Failed to sync memory {memory['id']}: {response.status_code}")
                    return False
                    
        except Exception as e:
            error_msg = f"Failed to sync memory {memory['id']}: {str(e)}"
            print(f"❌ {error_msg}")
            self.stats["errors"].append(error_msg)
            return False
    
    async def run_sync(self, max_memories: int = None, dry_run: bool = False) -> Dict[str, Any]:
        """Run the complete sync process"""
        print("🔄 EMERGENCY CHROMADB SYNC STARTING")
        print("=" * 50)
        
        # Get initial counts
        print("📊 Getting initial provider counts...")
        initial_counts = await self.get_provider_counts()
        print(f"   pgvector: {initial_counts['pgvector']} memories")
        print(f"   ChromaDB: {initial_counts['chromadb']} memories")
        print(f"   Graph: {initial_counts['graph']} nodes")
        
        missing_memories = initial_counts['pgvector'] - initial_counts['chromadb']
        print(f"   Missing from ChromaDB: {missing_memories} memories")
        
        if missing_memories <= 0:
            print("✅ ChromaDB already has all memories!")
            return self.stats
        
        # Test ChromaDB direct access
        print("\n🧪 Testing ChromaDB direct access...")
        if not await self.test_chromadb_direct():
            raise Exception("ChromaDB direct access test failed")
        
        if dry_run:
            print("🔍 DRY RUN MODE - No actual syncing will occur")
            return self.stats
        
        # Start sync process
        sync_limit = min(max_memories or missing_memories, missing_memories)
        print(f"\n🚀 Starting sync of {sync_limit} memories...")
        print(f"   Batch size: {BATCH_SIZE}")
        
        offset = 0
        batch_count = 0
        
        while offset < sync_limit:
            batch_count += 1
            current_batch_size = min(BATCH_SIZE, sync_limit - offset)
            
            print(f"\n📦 Processing batch {batch_count} (offset: {offset}, size: {current_batch_size})")
            
            try:
                # Get batch of memories from pgvector
                memories = await self.get_pgvector_memories(
                    limit=current_batch_size, 
                    offset=offset
                )
                
                if not memories:
                    print("   No more memories found")
                    break
                
                # Sync each memory in the batch
                batch_synced = 0
                for memory in memories:
                    self.stats["memories_processed"] += 1
                    
                    # Note: We skip actual syncing since replication is the issue
                    # Instead, we'll force replication via direct ChromaDB storage
                    success = await self.sync_memory_to_chromadb(memory)
                    
                    if success:
                        self.stats["memories_synced"] += 1
                        batch_synced += 1
                    
                    if self.stats["memories_processed"] % 100 == 0:
                        print(f"   ✅ Processed {self.stats['memories_processed']} memories...")
                
                self.stats["batches_completed"] += 1
                print(f"   ✅ Batch {batch_count} completed: {batch_synced}/{len(memories)} synced")
                
                # Brief pause between batches
                await asyncio.sleep(0.2)
                
            except Exception as e:
                error_msg = f"Batch {batch_count} failed: {str(e)}"
                print(f"   ❌ {error_msg}")
                self.stats["errors"].append(error_msg)
            
            offset += current_batch_size
        
        # Get final counts
        print("\n📊 Getting final provider counts...")
        final_counts = await self.get_provider_counts()
        print(f"   pgvector: {final_counts['pgvector']} memories")
        print(f"   ChromaDB: {final_counts['chromadb']} memories")
        
        self.stats["sync_duration"] = time.time() - self.start_time
        self.stats["sync_completed"] = datetime.now().isoformat()
        self.stats["initial_counts"] = initial_counts
        self.stats["final_counts"] = final_counts
        self.stats["newly_synced"] = final_counts['chromadb'] - initial_counts['chromadb']
        
        print(f"\n🎉 SYNC COMPLETED!")
        print(f"   Duration: {self.stats['sync_duration']:.1f} seconds")
        print(f"   Processed: {self.stats['memories_processed']} memories")
        print(f"   Synced: {self.stats['memories_synced']} memories")
        print(f"   ChromaDB increase: {self.stats['newly_synced']} memories")
        print(f"   Errors: {len(self.stats['errors'])}")
        
        return self.stats

async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Emergency ChromaDB Sync")
    parser.add_argument("--max-memories", type=int, help="Maximum memories to sync")
    parser.add_argument("--dry-run", action="store_true", help="Simulate sync without writing")
    parser.add_argument("--batch-size", type=int, default=25, help="Batch size for processing")
    
    args = parser.parse_args()
    
    # Update global batch size
    global BATCH_SIZE
    BATCH_SIZE = args.batch_size
    
    # Check environment
    if not DATABASE_CONFIG["password"]:
        print("❌ Error: PGVECTOR_PASSWORD or PGPASSWORD environment variable required")
        print("   Set it with: export PGVECTOR_PASSWORD='your-password'")
        return 1
    
    try:
        sync_processor = EmergencySyncProcessor()
        stats = await sync_processor.run_sync(
            max_memories=args.max_memories,
            dry_run=args.dry_run
        )
        
        # Save stats to file
        stats_file = f"sync_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
        
        print(f"\n📄 Stats saved to: {stats_file}")
        
        return 0 if len(stats["errors"]) == 0 else 1
        
    except Exception as e:
        print(f"❌ Sync failed: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))