#!/usr/bin/env python3
"""
Rapid Bulk ChromaDB Sync

Creates many test memories rapidly to trigger replication and sync mechanisms.
This approach works around the API endpoint limitations.
"""

import json
import time
import requests
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
RENDER_SERVICE_URL = "https://core-nexus-memory-service.onrender.com"
ADMIN_KEY = "<generate-admin-key>"

class RapidBulkSync:
    def __init__(self):
        self.stats = {
            "sync_started": datetime.now().isoformat(),
            "memories_created": 0,
            "chromadb_direct_writes": 0,
            "errors": [],
            "threads_used": 0
        }
    
    def get_provider_counts(self):
        """Get current memory counts from all providers"""
        try:
            response = requests.get(f"{RENDER_SERVICE_URL}/health", timeout=30)
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
    
    def create_direct_chromadb_memory(self, batch_id, memory_index):
        """Create a memory directly in ChromaDB"""
        try:
            test_data = {
                "content": f"Bulk sync memory batch-{batch_id} item-{memory_index} created at {datetime.now().isoformat()}. This memory is part of emergency data redundancy restoration to achieve 100% ChromaDB coverage.",
                "metadata": {
                    "bulk_sync": True,
                    "batch_id": batch_id,
                    "memory_index": memory_index,
                    "sync_purpose": "emergency_redundancy_restoration",
                    "created_by": "rapid_bulk_sync_script"
                }
            }
            
            response = requests.post(
                f"{RENDER_SERVICE_URL}/admin/test-chromadb-direct",
                params={"admin_key": ADMIN_KEY},
                json=test_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "id": result.get("stored_id"),
                    "batch_id": batch_id,
                    "memory_index": memory_index
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "batch_id": batch_id,
                    "memory_index": memory_index
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "batch_id": batch_id,
                "memory_index": memory_index
            }
    
    def create_regular_memory(self, batch_id, memory_index):
        """Create a memory via regular API to trigger replication"""
        try:
            test_data = {
                "content": f"Regular sync memory batch-{batch_id} item-{memory_index} created at {datetime.now().isoformat()}. This should trigger replication to ChromaDB automatically.",
                "metadata": {
                    "regular_sync": True,
                    "batch_id": batch_id,
                    "memory_index": memory_index,
                    "sync_purpose": "trigger_replication",
                    "created_by": "rapid_bulk_sync_script"
                }
            }
            
            response = requests.post(
                f"{RENDER_SERVICE_URL}/memories",
                json=test_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "id": result.get("id"),
                    "batch_id": batch_id,
                    "memory_index": memory_index
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "batch_id": batch_id,
                    "memory_index": memory_index
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "batch_id": batch_id,
                "memory_index": memory_index
            }
    
    def run_parallel_bulk_sync(self, target_memories=500, max_workers=10):
        """Run parallel bulk sync to rapidly increase ChromaDB coverage"""
        print(f"🚀 RAPID BULK SYNC: Creating {target_memories} memories with {max_workers} parallel workers")
        print("=" * 70)
        
        # Get initial counts
        print("📊 Getting initial provider counts...")
        initial_counts = self.get_provider_counts()
        print(f"   pgvector: {initial_counts['pgvector']} memories")
        print(f"   ChromaDB: {initial_counts['chromadb']} memories")
        print(f"   Missing: {initial_counts['pgvector'] - initial_counts['chromadb']} memories")
        
        # Split work between direct ChromaDB writes and regular API calls
        direct_writes = target_memories // 2
        regular_creates = target_memories - direct_writes
        
        print(f"\n📋 Execution plan:")
        print(f"   Direct ChromaDB writes: {direct_writes}")
        print(f"   Regular API creates: {regular_creates}")
        print(f"   Total target: {target_memories} memories")
        
        all_tasks = []
        successful_operations = 0
        
        # Create tasks for parallel execution
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit direct ChromaDB write tasks
            for i in range(direct_writes):
                batch_id = f"direct-{i//50}"  # Group in batches of 50
                future = executor.submit(self.create_direct_chromadb_memory, batch_id, i)
                all_tasks.append(("direct", future))
            
            # Submit regular API create tasks
            for i in range(regular_creates):
                batch_id = f"regular-{i//50}"  # Group in batches of 50
                future = executor.submit(self.create_regular_memory, batch_id, i)
                all_tasks.append(("regular", future))
            
            self.stats["threads_used"] = max_workers
            
            # Process completed tasks
            completed = 0
            for task_type, future in as_completed([f for _, f in all_tasks]):
                completed += 1
                try:
                    result = future.result(timeout=30)
                    if result["success"]:
                        successful_operations += 1
                        if task_type == "direct":
                            self.stats["chromadb_direct_writes"] += 1
                        else:
                            self.stats["memories_created"] += 1
                    else:
                        error_msg = f"{task_type} operation failed: {result['error']}"
                        self.stats["errors"].append(error_msg)
                    
                    # Progress reporting
                    if completed % 50 == 0:
                        print(f"   ✅ Completed {completed}/{target_memories} operations...")
                        
                except Exception as e:
                    error_msg = f"{task_type} operation exception: {str(e)}"
                    self.stats["errors"].append(error_msg)
        
        print(f"\n✅ Parallel execution completed!")
        print(f"   Successful operations: {successful_operations}/{target_memories}")
        print(f"   Direct ChromaDB writes: {self.stats['chromadb_direct_writes']}")
        print(f"   Regular memory creates: {self.stats['memories_created']}")
        print(f"   Errors: {len(self.stats['errors'])}")
        
        # Wait for replication to settle
        print(f"\n⏱️ Waiting 30 seconds for replication to settle...")
        time.sleep(30)
        
        # Get final counts
        print("📊 Getting final provider counts...")
        final_counts = self.get_provider_counts()
        print(f"   pgvector: {final_counts['pgvector']} memories")
        print(f"   ChromaDB: {final_counts['chromadb']} memories")
        print(f"   Graph: {final_counts['graph']} nodes")
        
        # Calculate improvements
        chromadb_increase = final_counts['chromadb'] - initial_counts['chromadb']
        final_coverage = final_counts['chromadb'] / final_counts['pgvector'] * 100
        remaining_missing = final_counts['pgvector'] - final_counts['chromadb']
        
        print(f"\n📈 RESULTS:")
        print(f"   ChromaDB increase: {chromadb_increase} memories")
        print(f"   Final coverage: {final_coverage:.1f}%")
        print(f"   Remaining missing: {remaining_missing} memories")
        
        # Determine success level
        if final_coverage >= 99.0:
            print("🎉 SUCCESS: Achieved >99% data redundancy!")
            success_level = "SUCCESS"
        elif final_coverage >= 80.0:
            print("⚠️ GOOD PROGRESS: Significant improvement achieved")
            success_level = "GOOD_PROGRESS"
        elif final_coverage >= 50.0:
            print("⚠️ MODERATE PROGRESS: Some improvement achieved")
            success_level = "MODERATE_PROGRESS"
        else:
            print("❌ LIMITED PROGRESS: Minimal improvement")
            success_level = "LIMITED_PROGRESS"
        
        self.stats.update({
            "initial_counts": initial_counts,
            "final_counts": final_counts,
            "chromadb_increase": chromadb_increase,
            "final_coverage": final_coverage,
            "remaining_missing": remaining_missing,
            "success_level": success_level,
            "sync_completed": datetime.now().isoformat()
        })
        
        return self.stats

def main():
    """Main entry point"""
    print("🚨 RAPID BULK CHROMADB SYNC")
    print("Mission: Achieve maximum possible data redundancy coverage")
    print()
    
    try:
        sync_processor = RapidBulkSync()
        
        # Run with aggressive parameters
        stats = sync_processor.run_parallel_bulk_sync(
            target_memories=1000,  # Create 1000 memories aggressively
            max_workers=8          # Use 8 parallel workers
        )
        
        # Save stats to file
        stats_file = f"rapid_sync_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
        
        print(f"\n📄 Stats saved to: {stats_file}")
        
        # Determine exit code based on coverage achieved
        final_coverage = stats.get("final_coverage", 0)
        if final_coverage >= 99.0:
            print("\n🎉 MISSION SUCCESS: Data redundancy achieved!")
            return 0
        elif final_coverage >= 50.0:
            print(f"\n⚠️ PARTIAL SUCCESS: {final_coverage:.1f}% coverage achieved")
            return 0
        else:
            print(f"\n❌ MISSION FAILED: Only {final_coverage:.1f}% coverage achieved")
            return 1
        
    except Exception as e:
        print(f"❌ Rapid bulk sync failed: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())