#!/usr/bin/env python3
"""
Diagnose API overhead vs direct database queries.

Current situation:
- Direct DB queries: 96ms with probes=3
- API queries: 340-636ms 
- Gap: 250+ms of overhead

This script will measure each component to find the bottleneck.
"""

import asyncio
import asyncpg
import time
import statistics
import json
import aiohttp
from typing import List, Dict, Any

# Test configurations
DB_URL = "postgresql://nexus_memory_db_user:2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V@dpg-d12n0np5pdvs73ctmm40-a.ohio-postgres.render.com:5432/nexus_memory_db"
API_URL = "https://core-nexus-memory-service.onrender.com"

# Test embedding (same one used in previous tests)
TEST_EMBEDDING = [
    0.1, -0.2, 0.3, -0.4, 0.5, -0.6, 0.7, -0.8, 0.9, -0.1,
    0.2, -0.3, 0.4, -0.5, 0.6, -0.7, 0.8, -0.9, 0.1, -0.2,
    0.3, -0.4, 0.5, -0.6, 0.7, -0.8, 0.9, -0.1, 0.2, -0.3,
    0.4, -0.5, 0.6, -0.7, 0.8, -0.9, 0.1, -0.2, 0.3, -0.4,
    0.5, -0.6, 0.7, -0.8, 0.9, -0.1, 0.2, -0.3, 0.4, -0.5
]

async def test_raw_db_query():
    """Test direct database query with timing breakdown"""
    print("🔍 Testing raw database query performance...")
    
    # Connection time
    start_time = time.perf_counter()
    conn = await asyncpg.connect(DB_URL)
    connect_time = (time.perf_counter() - start_time) * 1000
    
    # Setup time (probes setting)
    start_time = time.perf_counter()
    await conn.execute("SET ivfflat.probes = 3")
    setup_time = (time.perf_counter() - start_time) * 1000
    
    # Get a real embedding to use for testing
    start_time = time.perf_counter()
    sample = await conn.fetchval("SELECT embedding FROM vector_memories LIMIT 1")
    sample_time = (time.perf_counter() - start_time) * 1000
    
    # Query time
    start_time = time.perf_counter()
    results = await conn.fetch("""
        SELECT 
            id, content, metadata, 
            1 - (embedding <=> $1) AS similarity
        FROM vector_memories 
        ORDER BY embedding <=> $1
        LIMIT 10
    """, sample)
    query_time = (time.perf_counter() - start_time) * 1000
    
    # Close time
    start_time = time.perf_counter()
    await conn.close()
    close_time = (time.perf_counter() - start_time) * 1000
    
    return {
        "connect_time": connect_time,
        "setup_time": setup_time,
        "sample_time": sample_time,
        "query_time": query_time,
        "close_time": close_time,
        "total_time": connect_time + setup_time + sample_time + query_time + close_time,
        "result_count": len(results)
    }

async def test_pooled_db_query():
    """Test database query using connection pool (simulates provider behavior)"""
    print("🔍 Testing pooled database query...")
    
    # Create pool time
    start_time = time.perf_counter()
    
    async def setup_connection(conn):
        await conn.execute("SET ivfflat.probes = 3")
    
    pool = await asyncpg.create_pool(
        DB_URL,
        min_size=1,
        max_size=5,
        setup=setup_connection
    )
    pool_create_time = (time.perf_counter() - start_time) * 1000
    
    # Get a sample embedding first
    async with pool.acquire() as conn:
        sample = await conn.fetchval("SELECT embedding FROM vector_memories LIMIT 1")
    
    # Pool acquire time + query time
    start_time = time.perf_counter()
    async with pool.acquire() as conn:
        acquire_time = (time.perf_counter() - start_time) * 1000
        
        # Query time
        start_time = time.perf_counter()
        results = await conn.fetch("""
            SELECT 
                id, content, metadata, 
                1 - (embedding <=> $1) AS similarity
            FROM vector_memories 
            ORDER BY embedding <=> $1
            LIMIT 10
        """, sample)
        query_time = (time.perf_counter() - start_time) * 1000
    
    # Pool close time
    start_time = time.perf_counter()
    await pool.close()
    close_time = (time.perf_counter() - start_time) * 1000
    
    return {
        "pool_create_time": pool_create_time,
        "acquire_time": acquire_time,
        "query_time": query_time,
        "close_time": close_time,
        "total_time": pool_create_time + acquire_time + query_time + close_time,
        "result_count": len(results)
    }

async def test_api_query():
    """Test full API query with timing breakdown"""
    print("🔍 Testing API query performance...")
    
    # Prepare request
    payload = {
        "content": "test query for performance analysis",
        "limit": 10
    }
    
    # HTTP request time
    start_time = time.perf_counter()
    
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{API_URL}/memories/query",
                json=payload,
                headers={"Authorization": "Bearer test"}  # Use test token
            ) as response:
                response_time = (time.perf_counter() - start_time) * 1000
                
                # JSON parsing time
                start_time = time.perf_counter()
                data = await response.json()
                parse_time = (time.perf_counter() - start_time) * 1000
                
                return {
                    "response_time": response_time,
                    "parse_time": parse_time,
                    "total_time": response_time + parse_time,
                    "status_code": response.status,
                    "result_count": len(data.get("memories", [])) if response.status == 200 else 0,
                    "success": response.status == 200
                }
    
    except Exception as e:
        return {
            "error": str(e),
            "success": False,
            "total_time": 0
        }

async def run_comprehensive_analysis():
    """Run comprehensive performance analysis"""
    print("📊 Running comprehensive API overhead analysis...\n")
    
    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tests": {}
    }
    
    # Test 1: Raw DB queries (5 samples)
    print("1️⃣ Raw Database Queries")
    raw_db_results = []
    for i in range(5):
        result = await test_raw_db_query()
        raw_db_results.append(result)
        print(f"   Sample {i+1}: {result['total_time']:.1f}ms (query: {result['query_time']:.1f}ms)")
        await asyncio.sleep(0.5)  # Brief pause
    
    results["tests"]["raw_db"] = {
        "samples": raw_db_results,
        "avg_total": statistics.mean([r['total_time'] for r in raw_db_results]),
        "avg_query": statistics.mean([r['query_time'] for r in raw_db_results]),
        "avg_connect": statistics.mean([r['connect_time'] for r in raw_db_results]),
    }
    
    print(f"   Average: {results['tests']['raw_db']['avg_total']:.1f}ms\n")
    
    # Test 2: Pooled DB queries (5 samples)  
    print("2️⃣ Pooled Database Queries")
    pooled_db_results = []
    for i in range(5):
        result = await test_pooled_db_query()
        pooled_db_results.append(result)
        print(f"   Sample {i+1}: {result['total_time']:.1f}ms (query: {result['query_time']:.1f}ms)")
        await asyncio.sleep(0.5)
    
    results["tests"]["pooled_db"] = {
        "samples": pooled_db_results,
        "avg_total": statistics.mean([r['total_time'] for r in pooled_db_results]),
        "avg_query": statistics.mean([r['query_time'] for r in pooled_db_results]),
        "avg_acquire": statistics.mean([r['acquire_time'] for r in pooled_db_results]),
    }
    
    print(f"   Average: {results['tests']['pooled_db']['avg_total']:.1f}ms\n")
    
    # Test 3: API queries (5 samples)
    print("3️⃣ Full API Queries")
    api_results = []
    for i in range(5):
        result = await test_api_query()
        api_results.append(result)
        status = "✅" if result['success'] else "❌"
        print(f"   Sample {i+1}: {result['total_time']:.1f}ms {status}")
        await asyncio.sleep(2)  # Rate limit friendly
    
    successful_api = [r for r in api_results if r['success']]
    if successful_api:
        results["tests"]["api"] = {
            "samples": api_results,
            "successful_samples": len(successful_api),
            "avg_total": statistics.mean([r['total_time'] for r in successful_api]),
            "avg_response": statistics.mean([r['response_time'] for r in successful_api]),
        }
        print(f"   Average (successful): {results['tests']['api']['avg_total']:.1f}ms\n")
    else:
        results["tests"]["api"] = {"error": "No successful API requests"}
        print("   ❌ No successful API requests\n")
    
    return results

async def analyze_overhead(results):
    """Analyze where the overhead is coming from"""
    print("🔬 Overhead Analysis\n")
    
    raw_db = results["tests"]["raw_db"]["avg_query"]
    pooled_db = results["tests"]["pooled_db"]["avg_query"] 
    
    print(f"Raw DB query time: {raw_db:.1f}ms")
    print(f"Pooled DB query time: {pooled_db:.1f}ms")
    print(f"Pool overhead: +{pooled_db - raw_db:.1f}ms\n")
    
    if "api" in results["tests"] and "avg_total" in results["tests"]["api"]:
        api_total = results["tests"]["api"]["avg_total"]
        
        print(f"Full API time: {api_total:.1f}ms")
        print(f"API overhead over pooled DB: +{api_total - pooled_db:.1f}ms")
        
        # Breakdown
        overhead_components = {
            "Database query": pooled_db,
            "HTTP + Processing": api_total - pooled_db,
            "Total": api_total
        }
        
        print("\nOverhead breakdown:")
        for component, time_ms in overhead_components.items():
            percentage = (time_ms / api_total) * 100 if api_total > 0 else 0
            print(f"  {component}: {time_ms:.1f}ms ({percentage:.1f}%)")
    else:
        print("❌ Could not compare with API (no successful requests)")

async def main():
    """Main diagnostic function"""
    print("🩺 API Overhead Diagnostic Tool")
    print("===============================\n")
    
    results = await run_comprehensive_analysis()
    await analyze_overhead(results)
    
    # Save detailed results
    with open('api_overhead_analysis.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: api_overhead_analysis.json")
    
    # Quick summary
    print("\n📋 Quick Summary:")
    if "api" in results["tests"] and "avg_total" in results["tests"]["api"]:
        db_time = results["tests"]["pooled_db"]["avg_query"]
        api_time = results["tests"]["api"]["avg_total"]
        overhead = api_time - db_time
        
        print(f"  Database: {db_time:.1f}ms")
        print(f"  Full API: {api_time:.1f}ms") 
        print(f"  Overhead: {overhead:.1f}ms ({(overhead/api_time)*100:.1f}%)")
        
        if overhead > 200:
            print("\n⚠️  High overhead detected! Potential issues:")
            print("   - Authentication/middleware processing")
            print("   - JSON serialization overhead")
            print("   - Connection pool configuration") 
            print("   - Network latency")
    else:
        print("  ❌ Could not complete API analysis")

if __name__ == "__main__":
    asyncio.run(main())