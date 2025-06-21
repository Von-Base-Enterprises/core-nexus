#!/usr/bin/env python3
"""
Simple ChromaDB Sync Script using API calls only

Uses the memory service API to force synchronization by creating memories
that will trigger replication to ChromaDB.
"""

import json
import time
import requests
from datetime import datetime

# Configuration
RENDER_SERVICE_URL = "https://core-nexus-memory-service.onrender.com"
ADMIN_KEY = "<generate-admin-key>"

class SimpleChromaDBSync:
    def __init__(self):
        self.stats = {
            "sync_started": datetime.now().isoformat(),
            "test_memories_created": 0,
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
                "content": f"Direct sync test {datetime.now().isoformat()}",
                "metadata": {"direct_sync_test": True}
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
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ ChromaDB direct test error: {e}")
            return False
    
    def create_test_memory(self, index):
        """Create a test memory to trigger replication"""
        try:
            memory_data = {
                "content": f"Sync verification memory {index} - {datetime.now().isoformat()}",
                "metadata": {
                    "sync_test": True,
                    "sync_index": index,
                    "purpose": "verify_replication_working"
                }
            }
            
            response = requests.post(
                f"{RENDER_SERVICE_URL}/memories",
                json=memory_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Created test memory {index}: {result.get('id')}")
                self.stats["test_memories_created"] += 1
                return True
            else:
                print(f"❌ Failed to create test memory {index}: {response.status_code}")
                return False
                
        except Exception as e:
            error_msg = f"Failed to create test memory {index}: {str(e)}"
            print(f"❌ {error_msg}")
            self.stats["errors"].append(error_msg)
            return False
    
    def run_replication_test(self, num_test_memories=5):
        """Run replication test by creating new memories"""
        print("🔄 SIMPLE CHROMADB REPLICATION TEST")
        print("=" * 50)
        
        # Get initial counts
        print("📊 Getting initial provider counts...")
        initial_counts = self.get_provider_counts()
        print(f"   pgvector: {initial_counts['pgvector']} memories")
        print(f"   ChromaDB: {initial_counts['chromadb']} memories")
        print(f"   Graph: {initial_counts['graph']} nodes")
        
        missing_memories = initial_counts['pgvector'] - initial_counts['chromadb']
        print(f"   Missing from ChromaDB: {missing_memories} memories")
        
        # Test ChromaDB direct access
        print("\n🧪 Testing ChromaDB direct access...")
        if not self.test_chromadb_direct():
            print("❌ ChromaDB direct access failed - cannot proceed")
            return self.stats
        
        # Create test memories to verify replication
        print(f"\n🚀 Creating {num_test_memories} test memories to verify replication...")
        
        for i in range(1, num_test_memories + 1):
            print(f"\n📝 Creating test memory {i}/{num_test_memories}...")
            success = self.create_test_memory(i)
            
            if success:
                # Wait for replication
                print("   ⏱️ Waiting 5 seconds for replication...")
                time.sleep(5)
                
                # Check if replication worked
                current_counts = self.get_provider_counts()
                print(f"   📊 Current counts: pgvector={current_counts['pgvector']}, ChromaDB={current_counts['chromadb']}")
                
                if current_counts['chromadb'] > initial_counts['chromadb']:
                    print(f"   ✅ ChromaDB replication working! (+{current_counts['chromadb'] - initial_counts['chromadb']})")
                else:
                    print(f"   ❌ ChromaDB replication not working (still {current_counts['chromadb']})")
        
        # Get final counts
        print("\n📊 Getting final provider counts...")
        final_counts = self.get_provider_counts()
        print(f"   pgvector: {final_counts['pgvector']} memories")
        print(f"   ChromaDB: {final_counts['chromadb']} memories")
        print(f"   Graph: {final_counts['graph']} nodes")
        
        chromadb_increase = final_counts['chromadb'] - initial_counts['chromadb']
        print(f"\n📈 ChromaDB increased by: {chromadb_increase} memories")
        
        if chromadb_increase >= num_test_memories:
            print("🎉 SUCCESS: Replication is working correctly!")
        elif chromadb_increase > 0:
            print("⚠️ PARTIAL: Some replication working but not all memories")
        else:
            print("❌ FAILURE: No replication detected")
        
        self.stats["initial_counts"] = initial_counts
        self.stats["final_counts"] = final_counts
        self.stats["chromadb_increase"] = chromadb_increase
        self.stats["sync_completed"] = datetime.now().isoformat()
        
        return self.stats

def main():
    """Main entry point"""
    print("🔧 Simple ChromaDB Sync and Replication Test")
    print("This script tests if replication is working by creating new memories")
    print()
    
    try:
        sync_processor = SimpleChromaDBSync()
        stats = sync_processor.run_replication_test(num_test_memories=3)
        
        # Save stats to file
        stats_file = f"replication_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
        
        print(f"\n📄 Stats saved to: {stats_file}")
        
        return 0 if len(stats["errors"]) == 0 else 1
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())