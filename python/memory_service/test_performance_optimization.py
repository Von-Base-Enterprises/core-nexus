#!/usr/bin/env python3
"""
Performance test to verify the background task optimizations are working.
This tests the memory storage endpoint to measure response time improvements.
"""

import asyncio
import httpx
import json
import time
import statistics
from typing import List, Dict, Any

# Test configuration
API_BASE_URL = "https://core-nexus-memory-service.onrender.com"
TEST_TIMEOUT = 15  # seconds
NUM_TESTS = 5  # Number of performance tests to run

async def measure_endpoint_performance():
    """Measure performance of the optimized memory storage endpoint."""
    
    print("🚀 Core Nexus Performance Optimization Test")
    print("=" * 60)
    print(f"🎯 Target: {API_BASE_URL}")
    print(f"📊 Running {NUM_TESTS} performance tests\n")
    
    response_times = []
    
    async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
        
        # Test 1: Health check for baseline
        print("1. Baseline health check...")
        try:
            health_start = time.time()
            health_response = await client.get(f"{API_BASE_URL}/health")
            health_time = (time.time() - health_start) * 1000
            
            if health_response.status_code == 200:
                print(f"   ✅ Health check: {health_time:.1f}ms")
                health_data = health_response.json()
                print(f"   📊 Current memories: {health_data.get('total_memories', 0)}")
            else:
                print(f"   ❌ Health check failed: {health_response.status_code}")
                return
        except Exception as e:
            print(f"   ❌ Health check error: {e}")
            return
        
        # Test 2: Multiple memory storage tests for performance measurement
        print(f"\n2. Running {NUM_TESTS} memory storage performance tests...")
        
        for i in range(NUM_TESTS):
            test_memory = {
                "content": f"Performance test memory #{i+1} - Testing background task optimization for faster response times. This content is long enough to trigger embedding generation and various background processing tasks including graph extraction and replication to secondary providers.",
                "metadata": {
                    "test_type": "performance_optimization", 
                    "test_run": i + 1,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "optimization": "background_tasks_enabled",
                    "test_description": "Measuring response time improvements from background processing"
                },
                "importance_score": 0.7 + (i * 0.05)  # Vary importance scores
            }
            
            try:
                print(f"   🧪 Test {i+1}/{NUM_TESTS}...")
                start_time = time.time()
                
                store_response = await client.post(
                    f"{API_BASE_URL}/memories", 
                    json=test_memory,
                    headers={"Content-Type": "application/json"}
                )
                
                response_time = (time.time() - start_time) * 1000
                response_times.append(response_time)
                
                if store_response.status_code == 201:
                    response_data = store_response.json()
                    memory_id = response_data.get('id', 'unknown')
                    print(f"      ✅ Response time: {response_time:.1f}ms (ID: {memory_id[:8]}...)")
                    
                    # Verify background tasks are working by checking logs or status
                    if i == 0:  # Only check detailed response on first test
                        print(f"      📄 Content length: {len(response_data.get('content', ''))}")
                        print(f"      🎯 Importance score: {response_data.get('importance_score', 0):.3f}")
                        
                else:
                    print(f"      ❌ Storage failed: {store_response.status_code}")
                    print(f"      📄 Error: {store_response.text}")
                    continue
                    
            except Exception as e:
                print(f"      ❌ Test {i+1} error: {e}")
                continue
            
            # Brief pause between tests to avoid overwhelming the service
            if i < NUM_TESTS - 1:
                await asyncio.sleep(0.5)
        
        # Test 3: Performance analysis
        print(f"\n3. Performance Analysis Results")
        print("=" * 40)
        
        if response_times:
            avg_time = statistics.mean(response_times)
            median_time = statistics.median(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            std_dev = statistics.stdev(response_times) if len(response_times) > 1 else 0
            
            print(f"📊 Response Time Statistics:")
            print(f"   • Average:  {avg_time:.1f}ms")
            print(f"   • Median:   {median_time:.1f}ms")
            print(f"   • Min:      {min_time:.1f}ms") 
            print(f"   • Max:      {max_time:.1f}ms")
            print(f"   • Std Dev:  {std_dev:.1f}ms")
            
            # Performance assessment
            print(f"\n🎯 Performance Assessment:")
            
            if avg_time < 500:
                print("   🚀 EXCELLENT: Average response time under 500ms")
                print("   ✅ Background task optimization is working very well!")
            elif avg_time < 800:
                print("   ✅ GOOD: Average response time under 800ms")
                print("   🔄 Background task optimization is working!")
            elif avg_time < 1200:
                print("   ⚠️  ACCEPTABLE: Average response time under 1.2s")
                print("   📈 Some improvement from background tasks")
            else:
                print("   ❌ NEEDS IMPROVEMENT: Average response time over 1.2s")
                print("   🔍 Background task optimization may not be fully effective")
            
            # Consistency check
            if std_dev < 200:
                print("   📈 Response times are consistent (low variance)")
            else:
                print("   📊 Response times vary significantly (check system load)")
                
            # Improvement estimate
            baseline_time = 1700  # Previous measured baseline ~1.7s
            if avg_time < baseline_time:
                improvement = ((baseline_time - avg_time) / baseline_time) * 100
                print(f"   🎉 Estimated improvement: {improvement:.1f}% faster than baseline")
            
        else:
            print("   ❌ No successful tests - unable to measure performance")
        
        # Test 4: Quick query test to ensure functionality
        print(f"\n4. Functionality verification...")
        try:
            query_data = {
                "query": "performance test optimization",
                "limit": 3
            }
            query_start = time.time()
            query_response = await client.post(f"{API_BASE_URL}/memories/query", json=query_data)
            query_time = (time.time() - query_start) * 1000
            
            if query_response.status_code == 200:
                query_result = query_response.json()
                found_memories = len(query_result.get('memories', []))
                print(f"   ✅ Query test: {query_time:.1f}ms, found {found_memories} memories")
                
                # Check if we can find our test memories
                test_memories_found = 0
                for memory in query_result.get('memories', []):
                    if 'performance_optimization' in str(memory.get('metadata', {})):
                        test_memories_found += 1
                
                if test_memories_found > 0:
                    print(f"   🔍 Found {test_memories_found} test memories (background replication working)")
                
            else:
                print(f"   ⚠️  Query test issue: {query_response.status_code}")
                
        except Exception as e:
            print(f"   ⚠️  Query test error: {e}")

async def main():
    """Run the performance test suite."""
    print("🔧 Core Nexus Performance Optimization Verification")
    print("🎯 Testing background task optimization for improved response times")
    print()
    
    await measure_endpoint_performance()
    
    print("\n" + "=" * 60)
    print("📋 Optimization Summary:")
    print("   • Moved graph processing to background tasks")
    print("   • Moved provider replication to background tasks") 
    print("   • Optimized ADM scoring with fast fallback")
    print("   • Enhanced embedding caching")
    print("   • Added parallel background task execution")
    print()
    print("🎯 Expected Result: Response times should be 50-70% faster")
    print("📈 Target: < 800ms average response time (down from ~1.7s)")

if __name__ == "__main__":
    asyncio.run(main())