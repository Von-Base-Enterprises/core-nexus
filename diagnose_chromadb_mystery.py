#!/usr/bin/env python3
"""
Diagnose ChromaDB replication mystery with targeted analysis
Graph replication works, ChromaDB doesn't - why?
"""

import asyncio
import json
import httpx
import time
from datetime import datetime

async def comprehensive_replication_analysis():
    """Comprehensive analysis to solve the ChromaDB mystery"""
    print("🔍 COMPREHENSIVE CHROMADB REPLICATION ANALYSIS")
    print("=" * 70)
    
    print("🎯 OBSERVED PATTERN:")
    print("   ✅ pgvector: Receives all new memories (primary working)")
    print("   ✅ graph: Successfully replicates (+1 node)")
    print("   ❌ ChromaDB: Completely silent (0 vectors)")
    print("   📊 This suggests selective replication failure")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        
        # Test 1: Create multiple memories to observe pattern
        print(f"\n📝 TEST 1: Creating 3 memories to observe replication pattern")
        baseline_response = await client.get("https://core-nexus-memory-service.onrender.com/health")
        baseline = baseline_response.json()
        
        baseline_pgvector = baseline["providers"]["pgvector"]["details"]["details"]["total_vectors"]
        baseline_chromadb = baseline["providers"]["chromadb"]["details"]["details"]["total_vectors"] 
        baseline_graph = baseline["providers"]["graph"]["details"]["details"]["graph_nodes"]
        
        print(f"   Baseline - pgvector: {baseline_pgvector}, ChromaDB: {baseline_chromadb}, graph: {baseline_graph}")
        
        # Create test memories
        test_results = []
        for i in range(3):
            test_data = {
                "content": f"Replication diagnostic test {i+1} - {datetime.now().isoformat()}",
                "metadata": {
                    "diagnostic_test": i+1,
                    "purpose": "replication_analysis"
                }
            }
            
            response = await client.post(
                "https://core-nexus-memory-service.onrender.com/memories",
                json=test_data
            )
            
            if response.status_code == 200:
                result = response.json()
                test_results.append({
                    "test": i+1,
                    "id": result["id"],
                    "success": True
                })
                print(f"   ✅ Test {i+1}: {result['id']}")
            else:
                test_results.append({
                    "test": i+1,
                    "success": False,
                    "error": response.status_code
                })
                print(f"   ❌ Test {i+1}: Failed with {response.status_code}")
            
            await asyncio.sleep(2)  # Wait for replication
        
        # Check final counts
        final_response = await client.get("https://core-nexus-memory-service.onrender.com/health")
        final = final_response.json()
        
        final_pgvector = final["providers"]["pgvector"]["details"]["details"]["total_vectors"]
        final_chromadb = final["providers"]["chromadb"]["details"]["details"]["total_vectors"]
        final_graph = final["providers"]["graph"]["details"]["details"]["graph_nodes"]
        
        print(f"\n📊 REPLICATION ANALYSIS RESULTS:")
        print(f"   pgvector: {baseline_pgvector} → {final_pgvector} (+{final_pgvector - baseline_pgvector})")
        print(f"   ChromaDB: {baseline_chromadb} → {final_chromadb} (+{final_chromadb - baseline_chromadb})")
        print(f"   graph: {baseline_graph} → {final_graph} (+{final_graph - baseline_graph})")
        
        # Test 2: Analyze provider health details
        print(f"\n🔍 TEST 2: Provider health analysis")
        chromadb_health = final["providers"]["chromadb"]
        print(f"   ChromaDB Status: {chromadb_health['status']}")
        print(f"   ChromaDB Details: {json.dumps(chromadb_health['details'], indent=4)}")
        
        # Test 3: Memory search to confirm storage
        print(f"\n🔍 TEST 3: Memory search verification")
        search_response = await client.get(
            "https://core-nexus-memory-service.onrender.com/memories",
            params={"limit": 5}
        )
        
        if search_response.status_code == 200:
            search_data = search_response.json()
            print(f"   ✅ Retrieved {len(search_data['memories'])} recent memories")
            for i, memory in enumerate(search_data['memories'][:3]):
                if 'diagnostic_test' in memory.get('metadata', {}):
                    print(f"      Test memory {i+1}: {memory['id']} - stored in pgvector")
        
        return {
            "pgvector_delta": final_pgvector - baseline_pgvector,
            "chromadb_delta": final_chromadb - baseline_chromadb,
            "graph_delta": final_graph - baseline_graph,
            "test_results": test_results
        }

async def diagnose_root_cause(analysis_results):
    """Diagnose the root cause based on analysis results"""
    print(f"\n🎯 ROOT CAUSE DIAGNOSIS:")
    
    pgvector_delta = analysis_results["pgvector_delta"]
    chromadb_delta = analysis_results["chromadb_delta"]
    graph_delta = analysis_results["graph_delta"]
    
    if pgvector_delta > 0 and graph_delta > 0 and chromadb_delta == 0:
        print(f"🔧 DIAGNOSIS: Selective Replication Failure")
        print(f"   ✅ Primary storage (pgvector) working perfectly")
        print(f"   ✅ Graph replication working")
        print(f"   ❌ ChromaDB replication specifically broken")
        print()
        print(f"🎯 POSSIBLE ROOT CAUSES:")
        print(f"   1. ChromaDB provider disabled during replication")
        print(f"   2. ChromaDB store() method throwing silent exceptions")
        print(f"   3. ChromaDB not in secondary providers list")
        print(f"   4. Async executor issue in ChromaDB provider")
        print(f"   5. Directory permissions issue despite health check")
        print()
        print(f"🔧 RECOMMENDED SOLUTION:")
        print(f"   1. Check replication logs for ChromaDB store() calls")
        print(f"   2. Add direct ChromaDB test endpoint")
        print(f"   3. Force a single memory sync to ChromaDB")
        print(f"   4. Once fixed, bulk sync all 1,178 memories")
        
    elif pgvector_delta == 0:
        print(f"❌ DIAGNOSIS: Primary storage failure")
        print(f"   Memories not being created at all")
        
    else:
        print(f"🤔 DIAGNOSIS: Unexpected pattern")
        print(f"   Need deeper investigation")

async def main():
    """Run comprehensive ChromaDB replication diagnosis"""
    print("🚨 CHROMADB REPLICATION MYSTERY SOLVER")
    print("Objective: Understand why graph replicates but ChromaDB doesn't")
    print()
    
    start_time = time.time()
    
    # Run analysis
    analysis_results = await comprehensive_replication_analysis()
    
    # Diagnose root cause
    await diagnose_root_cause(analysis_results)
    
    duration = time.time() - start_time
    print(f"\n⏱️ Analysis completed in {duration:.1f} seconds")
    print(f"\n🎯 NEXT STEP: Create direct ChromaDB test endpoint to bypass replication")

if __name__ == "__main__":
    asyncio.run(main())