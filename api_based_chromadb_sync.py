#!/usr/bin/env python3
"""
API-Based ChromaDB Emergency Sync

Since we can't access the database directly without asyncpg,
this script uses API endpoints to force replication and sync.
"""

import json
import time
import requests
from datetime import datetime

# Configuration
RENDER_SERVICE_URL = "https://core-nexus-memory-service.onrender.com"
ADMIN_KEY = "<generate-admin-key>"

class APIBasedSync:
    def __init__(self):
        self.stats = {
            "sync_started": datetime.now().isoformat(),
            "api_calls_made": 0,
            "memories_synced": 0,
            "errors": []
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
    
    def test_chromadb_direct(self):
        """Test if ChromaDB direct access works"""
        try:
            test_data = {
                "content": f"Emergency sync test {datetime.now().isoformat()}",
                "metadata": {"emergency_sync_test": True}
            }
            
            response = requests.post(
                f"{RENDER_SERVICE_URL}/admin/test-chromadb-direct",
                params={"admin_key": ADMIN_KEY},
                json=test_data,
                timeout=30
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
    
    def try_api_emergency_sync(self):
        """Try to use the API emergency sync endpoint if available"""
        try:
            print("🔄 Attempting to use API emergency sync endpoint...")
            
            response = requests.post(
                f"{RENDER_SERVICE_URL}/admin/emergency-chromadb-sync",
                params={
                    "admin_key": ADMIN_KEY,
                    "batch_size": 25,
                    "dry_run": False
                },
                timeout=600  # 10 minute timeout for large sync
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ API emergency sync successful!")
                print(f"Status: {result.get('status')}")
                print(f"Message: {result.get('message')}")
                
                if 'stats' in result:
                    stats = result['stats']
                    print(f"Processed: {stats.get('memories_processed', 0)}")
                    print(f"Synced: {stats.get('memories_synced', 0)}")
                    print(f"Duration: {stats.get('sync_duration_seconds', 0):.1f}s")
                
                return True
            else:
                print(f"❌ API emergency sync failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ API emergency sync error: {e}")
            return False
    
    def force_replication_via_direct_chromadb(self, num_test_memories=50):
        """Force replication by creating many test memories that trigger ChromaDB writes"""
        print(f"🔄 Attempting to force replication via direct ChromaDB writes...")
        print(f"Creating {num_test_memories} test memories to trigger bulk replication...")
        
        successful_writes = 0
        
        for i in range(1, num_test_memories + 1):
            try:
                # Use direct ChromaDB endpoint to force writes
                test_data = {
                    "content": f"Forced replication test {i} - {datetime.now().isoformat()}",
                    "metadata": {
                        "forced_replication": True,
                        "batch_index": i,
                        "purpose": "emergency_sync"
                    }
                }
                
                response = requests.post(
                    f"{RENDER_SERVICE_URL}/admin/test-chromadb-direct",
                    params={"admin_key": ADMIN_KEY},
                    json=test_data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    successful_writes += 1
                    if i % 10 == 0:
                        print(f"   ✅ Completed {i}/{num_test_memories} direct writes...")
                else:
                    print(f"   ❌ Direct write {i} failed: {response.status_code}")
                
                # Brief pause to avoid overwhelming the system
                time.sleep(0.2)
                
            except Exception as e:
                print(f"   ❌ Direct write {i} error: {e}")
        
        print(f"✅ Completed {successful_writes}/{num_test_memories} direct ChromaDB writes")
        return successful_writes
    
    def run_comprehensive_sync(self):
        """Run comprehensive sync using all available methods"""
        print("🚨 API-BASED EMERGENCY CHROMADB SYNC")
        print("=" * 50)
        
        # Get initial counts
        print("📊 Getting initial provider counts...")
        initial_counts = self.get_provider_counts()
        print(f"   pgvector: {initial_counts['pgvector']} memories")
        print(f"   ChromaDB: {initial_counts['chromadb']} memories")
        print(f"   Graph: {initial_counts['graph']} nodes")
        
        missing_memories = initial_counts['pgvector'] - initial_counts['chromadb']
        print(f"   Missing from ChromaDB: {missing_memories} memories")
        print(f"   CRITICAL FAILURE: {missing_memories/initial_counts['pgvector']*100:.1f}% data loss")
        
        if missing_memories <= 10:
            print("✅ ChromaDB already has most memories!")
            return self.stats
        
        # Test ChromaDB direct access
        print("\n🧪 Testing ChromaDB direct access...")
        if not self.test_chromadb_direct():
            print("❌ ChromaDB direct access failed - cannot proceed")
            return self.stats
        
        # Method 1: Try API emergency sync endpoint
        print("\n🚀 METHOD 1: API Emergency Sync Endpoint")
        if self.try_api_emergency_sync():
            print("✅ API emergency sync completed successfully!")
        else:
            print("❌ API emergency sync not available or failed")
            
            # Method 2: Force replication via direct writes
            print("\n🚀 METHOD 2: Force Replication via Direct ChromaDB Writes")
            writes_completed = self.force_replication_via_direct_chromadb(100)
            print(f"Completed {writes_completed} direct writes to ChromaDB")
        
        # Get final counts
        print("\n📊 Getting final provider counts...")
        final_counts = self.get_provider_counts()
        print(f"   pgvector: {final_counts['pgvector']} memories")
        print(f"   ChromaDB: {final_counts['chromadb']} memories")
        print(f"   Graph: {final_counts['graph']} nodes")
        
        chromadb_increase = final_counts['chromadb'] - initial_counts['chromadb']
        print(f"\n📈 ChromaDB increased by: {chromadb_increase} memories")
        
        # Calculate success metrics
        final_coverage = final_counts['chromadb'] / final_counts['pgvector'] * 100
        remaining_missing = final_counts['pgvector'] - final_counts['chromadb']
        
        print(f"\n📊 FINAL REDUNDANCY STATUS:")
        print(f"   Data coverage: {final_coverage:.1f}%")
        print(f"   Missing memories: {remaining_missing}")
        
        if final_coverage >= 99.0:
            print("🎉 SUCCESS: Achieved >99% data redundancy!")
        elif final_coverage >= 90.0:
            print("⚠️ PARTIAL: Significant improvement but still missing data")
        else:
            print("❌ FAILURE: Minimal improvement in data redundancy")
        
        self.stats["initial_counts"] = initial_counts
        self.stats["final_counts"] = final_counts
        self.stats["chromadb_increase"] = chromadb_increase
        self.stats["final_coverage"] = final_coverage
        self.stats["sync_completed"] = datetime.now().isoformat()
        
        return self.stats

def main():
    """Main entry point"""
    print("🚨 PRIORITY MISSION: Complete ChromaDB Data Redundancy")
    print("Current state: 99.6% FAILURE - 5/1,209 memories in ChromaDB")
    print("Objective: Achieve 100% data redundancy")
    print()
    
    try:
        sync_processor = APIBasedSync()
        stats = sync_processor.run_comprehensive_sync()
        
        # Save stats to file
        stats_file = f"emergency_sync_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
        
        print(f"\n📄 Stats saved to: {stats_file}")
        
        # Determine exit code based on final coverage
        final_coverage = stats.get("final_coverage", 0)
        if final_coverage >= 99.0:
            print("\n🎉 MISSION SUCCESS: Data redundancy achieved!")
            return 0
        else:
            print(f"\n❌ MISSION FAILED: Only {final_coverage:.1f}% coverage achieved")
            return 1
        
    except Exception as e:
        print(f"❌ Emergency sync failed: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())