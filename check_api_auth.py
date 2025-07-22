#!/usr/bin/env python3
"""
Check API authentication and current probes setting.
"""

import asyncio
import asyncpg
import aiohttp
import json

DB_URL = "postgresql://nexus_memory_db_user:2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V@dpg-d12n0np5pdvs73ctmm40-a.ohio-postgres.render.com:5432/nexus_memory_db"
API_URL = "https://core-nexus-memory-service.onrender.com"

async def check_probes_setting():
    """Check current probes setting in database"""
    print("🔧 Checking current probes setting...")
    
    conn = await asyncpg.connect(DB_URL)
    
    try:
        # Check current probes
        probes = await conn.fetchval("SHOW ivfflat.probes")
        print(f"  Current probes: {probes}")
        
        # Test setting probes
        await conn.execute("SET ivfflat.probes = 3")
        new_probes = await conn.fetchval("SHOW ivfflat.probes")
        print(f"  After setting to 3: {new_probes}")
        
        # Check if we can query indexes
        try:
            indexes = await conn.fetch("""
                SELECT indexname, pg_size_pretty(pg_relation_size(indexname::regclass)) as size
                FROM pg_indexes 
                WHERE tablename = 'vector_memories' AND indexname LIKE '%embedding%'
            """)
            print("  Vector indexes:")
            for idx in indexes:
                print(f"    {idx['indexname']}: {idx['size']}")
        except Exception as e:
            print(f"  Could not check indexes: {e}")
            
    except Exception as e:
        print(f"❌ Probes check failed: {e}")
    
    await conn.close()

async def test_api_endpoints():
    """Test API endpoints to understand auth requirements"""
    print("\n🌐 Testing API endpoints...")
    
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        
        # Test 1: Health check (should not need auth)
        print("  1️⃣ Health check:")
        try:
            async with session.get(f"{API_URL}/health") as response:
                text = await response.text()
                print(f"    Status: {response.status}")
                if response.status == 200:
                    data = json.loads(text)
                    print(f"    Status: {data.get('status', 'unknown')}")
                    print(f"    Stats: {data.get('stats', {})}")
                else:
                    print(f"    Error: {text}")
        except Exception as e:
            print(f"    ❌ Failed: {e}")
        
        # Test 2: Query endpoint without auth
        print("  2️⃣ Query without auth:")
        try:
            payload = {"content": "test query", "limit": 5}
            async with session.post(f"{API_URL}/memories/query", json=payload) as response:
                text = await response.text()
                print(f"    Status: {response.status}")
                print(f"    Response: {text[:200]}...")
        except Exception as e:
            print(f"    ❌ Failed: {e}")
        
        # Test 3: Query with Bearer token
        print("  3️⃣ Query with Bearer token:")
        try:
            payload = {"content": "test query", "limit": 5}
            headers = {"Authorization": "Bearer test"}
            async with session.post(f"{API_URL}/memories/query", json=payload, headers=headers) as response:
                text = await response.text()
                print(f"    Status: {response.status}")
                if response.status == 200:
                    data = json.loads(text)
                    print(f"    Results: {len(data.get('memories', []))} memories found")
                else:
                    print(f"    Response: {text[:200]}...")
        except Exception as e:
            print(f"    ❌ Failed: {e}")
        
        # Test 4: Different auth patterns
        print("  4️⃣ Query with API key:")
        try:
            payload = {"content": "test query", "limit": 5}
            headers = {"X-API-Key": "test", "Authorization": "test"}
            async with session.post(f"{API_URL}/memories/query", json=payload, headers=headers) as response:
                text = await response.text()
                print(f"    Status: {response.status}")
                if response.status == 200:
                    data = json.loads(text)
                    print(f"    Results: {len(data.get('memories', []))} memories found")
                else:
                    print(f"    Response: {text[:200]}...")
        except Exception as e:
            print(f"    ❌ Failed: {e}")

async def test_direct_query_with_probes():
    """Test direct database query with different probes values"""
    print("\n🔍 Testing direct queries with probes...")
    
    conn = await asyncpg.connect(DB_URL)
    
    # Get sample embedding
    sample = await conn.fetchval("SELECT embedding FROM vector_memories LIMIT 1")
    
    for probes in [1, 2, 3]:
        print(f"  Testing probes={probes}:")
        
        try:
            # Set probes
            await conn.execute(f"SET ivfflat.probes = {probes}")
            
            # Time the query
            import time
            start = time.perf_counter()
            results = await conn.fetch("""
                SELECT id, content, 1 - (embedding <=> $1) AS similarity
                FROM vector_memories 
                ORDER BY embedding <=> $1
                LIMIT 10
            """, sample)
            duration = (time.perf_counter() - start) * 1000
            
            print(f"    Duration: {duration:.1f}ms, Results: {len(results)}")
            
        except Exception as e:
            print(f"    ❌ Failed: {e}")
    
    await conn.close()

async def main():
    await check_probes_setting()
    await test_api_endpoints()
    await test_direct_query_with_probes()

if __name__ == "__main__":
    asyncio.run(main())