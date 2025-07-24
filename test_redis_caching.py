#!/usr/bin/env python3
"""
Test Redis caching implementation for Core Nexus Memory Service.

This script tests:
1. Redis connection and fallback to in-memory cache
2. Cache hit/miss behavior  
3. JSON serialization for Redis
4. Performance improvement with caching
"""

import asyncio
import time
import os
import sys
import aiohttp
import json
from typing import Dict, Any

# Test configurations
API_URL = "https://core-nexus-memory-service.onrender.com"
LOCAL_API_URL = "http://localhost:8000"
API_KEY = "test-key-67890"

# Test queries for caching
TEST_QUERIES = [
    "production test core nexus operational",
    "von base enterprises development team",
    "ai systems artificial intelligence",
    "database performance optimization",
    "vector search similarity"
]

async def test_cache_implementation():
    """Test the cache implementation directly"""
    print("🧪 Testing Cache Implementation")
    print("================================\n")
    
    # Test in-memory cache fallback (no Redis)
    print("1️⃣ Testing in-memory cache (no Redis)...")
    os.environ.pop('REDIS_URL', None)  # Remove Redis URL
    
    try:
        # Import the UnifiedVectorStore to test cache initialization
        sys.path.append('/mnt/c/Users/Tyvon/Dev/core-nexus/python/memory_service/src')
        from memory_service.unified_store import UnifiedVectorStore
        
        # Test with minimal providers (empty for this test)
        store = UnifiedVectorStore([], embedding_model=None, adm_enabled=False)
        
        print(f"   Cache type: {store._cache_type}")
        print(f"   Cache initialized: {store.query_cache is not None}")
        
        # Test cache operations
        test_key = "test_cache_key"
        test_data = {"test": "data", "timestamp": time.time()}
        
        # Test set
        store._set_cached_result(test_key, test_data)
        print("   ✅ Cache set operation successful")
        
        # Test get
        cached_data = store._get_cached_result(test_key)
        if cached_data and cached_data.get("test") == "data":
            print("   ✅ Cache get operation successful")
        else:
            print("   ❌ Cache get operation failed")
            
    except Exception as e:
        print(f"   ❌ Cache test failed: {e}")
    
    print()

async def test_api_caching_behavior(api_url: str):
    """Test caching behavior through API calls"""
    print(f"🚀 Testing API Caching at {api_url}")
    print("=" * 60)
    
    headers = {"X-API-Key": API_KEY}
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        
        for i, query in enumerate(TEST_QUERIES, 1):
            print(f"\n{i}️⃣ Testing query: '{query[:40]}...'")
            
            # First request (should be cache miss)
            print("   First request (cache miss):")
            start_time = time.perf_counter()
            
            try:
                async with session.post(
                    f"{api_url}/memories/query",
                    json={"content": query, "limit": 5},
                    headers=headers
                ) as response:
                    first_duration = (time.perf_counter() - start_time) * 1000
                    
                    if response.status == 200:
                        data = await response.json()
                        results_count = len(data.get("memories", []))
                        print(f"     ✅ {first_duration:.1f}ms ({results_count} results)")
                    else:
                        print(f"     ❌ {response.status}: {await response.text()}")
                        continue
                        
            except Exception as e:
                print(f"     ❌ Error: {e}")
                continue
            
            # Small delay to ensure different timestamp
            await asyncio.sleep(0.1)
            
            # Second request (should be cache hit if Redis working)
            print("   Second request (potential cache hit):")
            start_time = time.perf_counter()
            
            try:
                async with session.post(
                    f"{api_url}/memories/query",
                    json={"content": query, "limit": 5},
                    headers=headers
                ) as response:
                    second_duration = (time.perf_counter() - start_time) * 1000
                    
                    if response.status == 200:
                        data = await response.json()
                        results_count = len(data.get("memories", []))
                        
                        # Check for cache hit (significant speed improvement)
                        if second_duration < first_duration * 0.5:  # >50% faster
                            cache_status = "🎯 CACHE HIT"
                        else:
                            cache_status = "⏳ No cache hit"
                            
                        improvement = ((first_duration - second_duration) / first_duration) * 100
                        print(f"     ✅ {second_duration:.1f}ms ({results_count} results) - {cache_status}")
                        print(f"     📊 Performance: {improvement:+.1f}% change")
                    else:
                        print(f"     ❌ {response.status}: {await response.text()}")
                        
            except Exception as e:
                print(f"     ❌ Error: {e}")
            
            # Rate limit friendly delay
            await asyncio.sleep(1)

async def test_health_check_cache_info(api_url: str):
    """Check health endpoint for cache information"""
    print(f"\n🏥 Health Check - Cache Info")
    print("============================")
    
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"{api_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    
                    cache_size = data.get("cache_size", "unknown")
                    cache_type = data.get("cache_type", "unknown")
                    
                    print(f"   Cache Type: {cache_type}")
                    print(f"   Cache Size: {cache_size} entries")
                    
                    if cache_type == "redis":
                        print("   ✅ Redis caching ACTIVE")
                    elif cache_type == "memory":
                        print("   ⚠️ In-memory cache fallback")
                    else:
                        print("   ❓ Unknown cache type")
                else:
                    print(f"   ❌ Health check failed: {response.status}")
                    
    except Exception as e:
        print(f"   ❌ Health check error: {e}")

async def main():
    """Run comprehensive caching tests"""
    print("🔬 Core Nexus Redis Caching Test Suite")
    print("======================================")
    print(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test 1: Direct cache implementation
    await test_cache_implementation()
    
    # Test 2: API caching behavior (production)
    await test_api_caching_behavior(API_URL)
    
    # Test 3: Health check cache info
    await test_health_check_cache_info(API_URL)
    
    # Test 4: Local testing if available
    print(f"\n🏠 Testing Local Instance (if running)")
    print("=====================================")
    try:
        await test_health_check_cache_info(LOCAL_API_URL)
        await test_api_caching_behavior(LOCAL_API_URL)
    except Exception as e:
        print(f"   ❌ Local instance not available: {e}")
    
    print("\n" + "="*60)
    print("🎯 Test Summary:")
    print("   - Check cache_type in health checks")
    print("   - Look for significant speed improvements in second requests")  
    print("   - Cache hits should be <50ms, cache misses ~165ms")
    print("   - Redis deployment success = cache_type: 'redis'")

if __name__ == "__main__":
    asyncio.run(main())