#!/usr/bin/env python3
"""
Verify if the connection pool probes fix is actually deployed.
"""

import asyncio
import aiohttp
import json
import time

API_URL = "https://core-nexus-memory-service.onrender.com"
API_KEY = "test-key-67890"

async def check_deployment_status():
    """Check if the latest fixes are deployed"""
    print("🚀 Verifying Deployment Status")
    print("==============================\n")
    
    timeout = aiohttp.ClientTimeout(total=30)
    headers = {"X-API-Key": API_KEY}
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        
        # 1. Check health endpoint
        print("1️⃣ Health Check:")
        try:
            async with session.get(f"{API_URL}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"   Status: {data.get('status', 'unknown')}")
                    
                    stats = data.get('stats', {})
                    if stats:
                        print(f"   Total memories: {stats.get('total_memories', 'unknown')}")
                        print(f"   Providers: {list(stats.get('providers', {}).keys())}")
                    else:
                        print("   No stats available")
                else:
                    print(f"   ❌ Health check failed: {response.status}")
        except Exception as e:
            print(f"   ❌ Health check error: {e}")
        
        print()
        
        # 2. Test query performance consistency
        print("2️⃣ Query Performance Test (5 samples):")
        query_times = []
        
        for i in range(5):
            payload = {
                "content": "production test core nexus operational", 
                "limit": 10
            }
            
            start_time = time.perf_counter()
            try:
                async with session.post(
                    f"{API_URL}/memories/query",
                    json=payload,
                    headers=headers
                ) as response:
                    duration = (time.perf_counter() - start_time) * 1000
                    
                    if response.status == 200:
                        data = await response.json()
                        results = len(data.get("memories", []))
                        query_times.append(duration)
                        print(f"   Query {i+1}: {duration:.1f}ms ({results} results)")
                    else:
                        text = await response.text()
                        print(f"   Query {i+1}: ❌ {response.status} - {text[:100]}...")
                        
            except Exception as e:
                print(f"   Query {i+1}: ❌ Error - {e}")
            
            # Rate limit friendly delay
            await asyncio.sleep(2)
        
        print()
        
        # 3. Analyze performance
        if query_times:
            avg_time = sum(query_times) / len(query_times)
            min_time = min(query_times)
            max_time = max(query_times)
            
            print("📊 Performance Analysis:")
            print(f"   Average: {avg_time:.1f}ms")
            print(f"   Range: {min_time:.1f}ms - {max_time:.1f}ms")
            print(f"   Variance: {max_time - min_time:.1f}ms")
            
            # Expected performance with probes fix
            expected_db_time = 95  # Known DB performance with probes=3
            expected_api_overhead = 50  # Reasonable API overhead
            expected_total = expected_db_time + expected_api_overhead
            
            print(f"\n🎯 Expected vs Actual:")
            print(f"   Expected (with probes fix): ~{expected_total}ms")
            print(f"   Actual average: {avg_time:.1f}ms")
            
            if avg_time > expected_total + 50:  # 50ms tolerance
                print(f"   ⚠️  Performance gap: {avg_time - expected_total:.1f}ms")
                print("   This suggests probes fix may not be deployed yet")
                return False
            else:
                print("   ✅ Performance looks good - fix appears deployed")
                return True
        else:
            print("❌ No successful queries - cannot verify performance")
            return False

async def check_render_deployment():
    """Check if we need to trigger a new deployment"""
    print("\n🔄 Deployment Recommendations:")
    
    # This would require Render CLI or checking their API
    print("   If performance is still slow:")
    print("   1. Check Render dashboard for latest deployment")
    print("   2. Manual redeploy may be needed if auto-deploy failed") 
    print("   3. Check Render logs for any deployment errors")
    print("\n   Commands to check:")
    print("   - Git commit hash: 516617c (connection pool fix)")
    print("   - Expected DB performance: ~95ms with probes=3")
    print("   - Expected API performance: ~150ms total")

async def main():
    deployment_looks_good = await check_deployment_status()
    await check_render_deployment()
    
    if not deployment_looks_good:
        print("\n💡 Next Steps:")
        print("   1. Wait a few more minutes for Render auto-deployment")
        print("   2. Or manually trigger deployment from Render dashboard")
        print("   3. Re-run this script to verify after deployment")
    else:
        print("\n🎉 Deployment verification successful!")
        print("   Connection pool probes fix appears to be working.")

if __name__ == "__main__":
    asyncio.run(main())