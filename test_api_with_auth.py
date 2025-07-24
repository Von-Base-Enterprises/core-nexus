#!/usr/bin/env python3
"""
Test API with correct authentication and measure performance.
"""

import asyncio
import aiohttp
import json
import time
import statistics

API_URL = "https://core-nexus-memory-service.onrender.com"
API_KEY = "test-key-67890"  # Working API key from auth config

async def test_single_api_query():
    """Test a single API query with timing"""
    
    payload = {
        "content": "production test core nexus operational",
        "limit": 10
    }
    
    headers = {"X-API-Key": API_KEY}
    
    timeout = aiohttp.ClientTimeout(total=30)
    start_time = time.perf_counter()
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(
            f"{API_URL}/memories/query",
            json=payload,
            headers=headers
        ) as response:
            response_time = (time.perf_counter() - start_time) * 1000
            
            if response.status == 200:
                data = await response.json()
                return {
                    "success": True,
                    "response_time": response_time,
                    "results": len(data.get("memories", [])),
                    "status_code": response.status
                }
            else:
                text = await response.text()
                return {
                    "success": False,
                    "response_time": response_time,
                    "error": text,
                    "status_code": response.status
                }

async def test_api_performance():
    """Test API performance with multiple queries"""
    print("🚀 Testing API Performance with Correct Auth")
    print("=============================================\n")
    
    results = []
    
    print("Running 10 API queries...")
    for i in range(10):
        result = await test_single_api_query()
        results.append(result)
        
        status = "✅" if result['success'] else "❌"
        print(f"Query {i+1}: {result['response_time']:.1f}ms {status}")
        
        # Rate limit friendly delay
        await asyncio.sleep(1)
    
    print()
    
    # Analyze successful results
    successful = [r for r in results if r['success']]
    
    if successful:
        times = [r['response_time'] for r in successful]
        
        print("📊 Performance Summary:")
        print(f"  Successful queries: {len(successful)}/{len(results)}")
        print(f"  Average latency: {statistics.mean(times):.1f}ms")
        print(f"  Median latency: {statistics.median(times):.1f}ms")
        print(f"  Min latency: {min(times):.1f}ms")
        print(f"  Max latency: {max(times):.1f}ms")
        
        if len(times) >= 5:
            times_sorted = sorted(times)
            p90_idx = int(0.9 * len(times_sorted))
            p95_idx = int(0.95 * len(times_sorted))
            print(f"  P90 latency: {times_sorted[p90_idx]:.1f}ms")
            print(f"  P95 latency: {times_sorted[p95_idx]:.1f}ms")
        
        print(f"\n🎯 Target Analysis:")
        print(f"  Target: <100ms")
        under_100 = len([t for t in times if t < 100])
        print(f"  Queries under 100ms: {under_100}/{len(times)} ({under_100/len(times)*100:.1f}%)")
        
        if statistics.mean(times) > 100:
            overhead = statistics.mean(times) - 96  # Our known DB query time
            print(f"  Estimated API overhead: ~{overhead:.1f}ms")
        
    else:
        print("❌ No successful queries - authentication or API issues")
        for result in results:
            if not result['success']:
                print(f"  Error: {result.get('error', 'Unknown error')}")

async def main():
    await test_api_performance()

if __name__ == "__main__":
    asyncio.run(main())