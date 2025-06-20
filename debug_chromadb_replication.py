#!/usr/bin/env python3
"""
Debug ChromaDB replication failure after directory fix
This will test the exact replication scenario to identify remaining issues
"""

import asyncio
import json
import sys
import time
from datetime import datetime

async def test_chromadb_replication_scenario():
    """Test the exact replication scenario and capture detailed errors"""
    print("🔍 DEBUGGING CHROMADB REPLICATION FAILURE")
    print("=" * 60)
    
    # Test 1: Create a memory and check detailed logging
    print("📝 Creating test memory to trigger replication...")
    
    import httpx
    async with httpx.AsyncClient(timeout=30.0) as client:
        test_data = {
            "content": f"ChromaDB replication debug test - {datetime.now().isoformat()}",
            "metadata": {
                "debug_test": True,
                "timestamp": datetime.now().isoformat(),
                "purpose": "replication_debugging"
            }
        }
        
        # Create memory
        response = await client.post(
            "https://core-nexus-memory-service.onrender.com/memories",
            json=test_data
        )
        
        if response.status_code == 200:
            result = response.json()
            memory_id = result["id"]
            print(f"✅ Memory created: {memory_id}")
        else:
            print(f"❌ Memory creation failed: {response.status_code}")
            return False
        
        # Wait a moment for replication to attempt
        await asyncio.sleep(3)
        
        # Check health status
        health_response = await client.get("https://core-nexus-memory-service.onrender.com/health")
        if health_response.status_code == 200:
            health = health_response.json()
            pgvector_count = health["providers"]["pgvector"]["details"]["details"]["total_vectors"]
            chromadb_count = health["providers"]["chromadb"]["details"]["details"]["total_vectors"]
            
            print(f"📊 POST-REPLICATION COUNTS:")
            print(f"   pgvector: {pgvector_count} vectors")
            print(f"   ChromaDB: {chromadb_count} vectors")
            
            if chromadb_count > 0:
                print(f"🎉 SUCCESS: ChromaDB replication is working!")
                return True
            else:
                print(f"❌ FAILURE: ChromaDB still has 0 vectors after replication attempt")
                
                # Try to get more detailed error information
                print(f"\n🔍 DETAILED HEALTH CHECK:")
                chromadb_details = health["providers"]["chromadb"]
                print(f"   ChromaDB Status: {chromadb_details['status']}")
                print(f"   ChromaDB Details: {json.dumps(chromadb_details['details'], indent=2)}")
                
                return False
        else:
            print(f"❌ Health check failed: {health_response.status_code}")
            return False

async def test_chromadb_direct_write():
    """Test if we can write directly to ChromaDB via API to isolate the issue"""
    print(f"\n🧪 TESTING DIRECT CHROMADB WRITE VIA SERVICE")
    print("=" * 60)
    
    # This would require a special endpoint that bypasses replication
    # and writes directly to ChromaDB for testing
    print("⚠️ Direct ChromaDB write test requires special debug endpoint")
    print("   This would help isolate if the issue is in:")
    print("   1. ChromaDB initialization/configuration")
    print("   2. Replication logic execution")
    print("   3. Provider routing/selection")
    
    return None

async def analyze_replication_pattern():
    """Analyze the replication pattern to identify potential issues"""
    print(f"\n📈 ANALYZING REPLICATION PATTERN")
    print("=" * 60)
    
    import httpx
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get current counts
        print("📊 Getting baseline counts...")
        health_response = await client.get("https://core-nexus-memory-service.onrender.com/health")
        if health_response.status_code == 200:
            health = health_response.json()
            baseline_pgvector = health["providers"]["pgvector"]["details"]["details"]["total_vectors"]
            baseline_chromadb = health["providers"]["chromadb"]["details"]["details"]["total_vectors"]
            
            print(f"   Baseline - pgvector: {baseline_pgvector}, ChromaDB: {baseline_chromadb}")
            
            # Create multiple test memories
            print(f"\n📝 Creating 3 test memories to observe pattern...")
            for i in range(3):
                test_data = {
                    "content": f"Replication pattern test {i+1} - {datetime.now().isoformat()}",
                    "metadata": {"pattern_test": i+1, "batch": "replication_analysis"}
                }
                
                response = await client.post(
                    "https://core-nexus-memory-service.onrender.com/memories",
                    json=test_data
                )
                
                if response.status_code == 200:
                    print(f"   ✅ Test memory {i+1} created")
                else:
                    print(f"   ❌ Test memory {i+1} failed: {response.status_code}")
                
                # Brief delay between creates
                await asyncio.sleep(1)
            
            # Check final counts
            await asyncio.sleep(2)  # Wait for replication attempts
            
            final_health = await client.get("https://core-nexus-memory-service.onrender.com/health")
            if final_health.status_code == 200:
                final_data = final_health.json()
                final_pgvector = final_data["providers"]["pgvector"]["details"]["details"]["total_vectors"]
                final_chromadb = final_data["providers"]["chromadb"]["details"]["details"]["total_vectors"]
                
                print(f"\n📊 FINAL RESULTS:")
                print(f"   pgvector: {baseline_pgvector} → {final_pgvector} (+{final_pgvector - baseline_pgvector})")
                print(f"   ChromaDB: {baseline_chromadb} → {final_chromadb} (+{final_chromadb - baseline_chromadb})")
                
                if final_pgvector > baseline_pgvector and final_chromadb == baseline_chromadb:
                    print(f"\n🎯 PATTERN IDENTIFIED:")
                    print(f"   ✅ pgvector receives new memories (primary working)")
                    print(f"   ❌ ChromaDB receives nothing (replication completely broken)")
                    print(f"   📋 Issue is in the _replicate_to_secondaries method")
                elif final_pgvector == baseline_pgvector:
                    print(f"\n🎯 PATTERN IDENTIFIED:")
                    print(f"   ❌ No memories created at all (API issue)")
                else:
                    print(f"\n🎯 UNEXPECTED PATTERN:")
                    print(f"   Investigation needed")
                
                return final_pgvector - baseline_pgvector, final_chromadb - baseline_chromadb
        
        return None, None

async def main():
    """Run comprehensive ChromaDB replication debugging"""
    print("🚨 CHROMADB REPLICATION DEBUG SESSION")
    print("Objective: Identify why ChromaDB has 0 vectors despite fixed directory")
    print()
    
    start_time = time.time()
    
    # Test 1: Single memory replication test
    replication_works = await test_chromadb_replication_scenario()
    
    # Test 2: Pattern analysis
    pgvector_delta, chromadb_delta = await analyze_replication_pattern()
    
    # Test 3: Direct write test (conceptual)
    await test_chromadb_direct_write()
    
    print(f"\n📋 DEBUGGING SUMMARY:")
    print(f"  Replication Test: {'✅ WORKING' if replication_works else '❌ BROKEN'}")
    if pgvector_delta is not None:
        print(f"  Pattern Analysis: pgvector +{pgvector_delta}, ChromaDB +{chromadb_delta}")
    
    duration = time.time() - start_time
    print(f"  Debug Duration: {duration:.1f} seconds")
    
    if not replication_works:
        print(f"\n🔧 NEXT STEPS:")
        print(f"  1. Check if deployment actually picked up directory fix")
        print(f"  2. Examine if ChromaDB provider is actually in secondary providers list")
        print(f"  3. Look for silent failures in ChromaDB writes")
        print(f"  4. Consider if there's an async/await issue in replication")
        print(f"  5. Verify ChromaDB collection initialization")

if __name__ == "__main__":
    asyncio.run(main())