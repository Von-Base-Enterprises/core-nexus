#!/usr/bin/env python3
"""
Test if probes setting is being applied in API queries.
"""

import json
import urllib.request
import time
import asyncpg
import asyncio

async def test_direct_db_with_probes():
    """Test database queries directly with different probes settings."""
    db_url = (
        "postgresql://nexus_memory_db_user:2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V@"
        "dpg-d12n0np5pdvs73ctmm40-a.ohio-postgres.render.com:5432/nexus_memory_db"
    )
    
    print("🔍 Testing direct database queries with probes settings...")
    
    conn = await asyncpg.connect(db_url)
    
    # Get a sample embedding
    sample_embedding = await conn.fetchval("""
        SELECT embedding::text
        FROM vector_memories
        WHERE embedding IS NOT NULL
        LIMIT 1
    """)
    
    # Test with probes=1 (default)
    print("\n1. Testing with default probes (should be slow):")
    try:
        # Check current setting
        try:
            current = await conn.fetchval("SHOW ivfflat.probes")
            print(f"   Current probes: {current}")
        except:
            print("   Cannot read probes setting")
        
        times = []
        for i in range(3):
            start = time.time()
            await conn.fetch("""
                SELECT id FROM vector_memories
                ORDER BY embedding <=> $1::vector
                LIMIT 10
            """, sample_embedding)
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)
        
        avg_time = sum(times) / len(times)
        print(f"   Average query time: {avg_time:.1f}ms")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test with probes=3
    print("\n2. Testing with probes=3 (should be faster):")
    try:
        # Try to set probes
        try:
            await conn.execute("SET ivfflat.probes = 3")
            print("   Successfully set probes=3")
            current = await conn.fetchval("SHOW ivfflat.probes")
            print(f"   Verified probes: {current}")
        except Exception as e:
            print(f"   Cannot set probes: {e}")
        
        times = []
        for i in range(3):
            start = time.time()
            await conn.fetch("""
                SELECT id FROM vector_memories
                ORDER BY embedding <=> $1::vector
                LIMIT 10
            """, sample_embedding)
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)
        
        avg_time = sum(times) / len(times)
        print(f"   Average query time: {avg_time:.1f}ms")
    except Exception as e:
        print(f"   Error: {e}")
    
    await conn.close()


def test_api_performance():
    """Test API performance to see if probes is being applied."""
    print("\n📊 Testing API performance...")
    
    api_url = "https://core-nexus-memory-service.onrender.com"
    api_key = "dev-key-12345"
    
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key
    }
    
    # Test queries
    queries = ["pgvector optimization", "memory service", "Core Nexus"]
    
    for query in queries:
        data = json.dumps({
            "query": query,
            "limit": 10
        }).encode('utf-8')
        
        req = urllib.request.Request(
            f"{api_url}/memories/query",
            data=data,
            headers=headers,
            method="POST"
        )
        
        try:
            start = time.time()
            response = urllib.request.urlopen(req)
            elapsed = (time.time() - start) * 1000
            
            result = json.loads(response.read().decode('utf-8'))
            query_time = result.get('query_time_ms', 0)
            
            print(f"\nQuery: '{query}'")
            print(f"  Total time: {elapsed:.1f}ms")
            print(f"  Query time (reported): {query_time:.1f}ms")
            print(f"  Network overhead: {elapsed - query_time:.1f}ms")
            
        except Exception as e:
            print(f"Error querying '{query}': {e}")


async def main():
    # Test direct database
    await test_direct_db_with_probes()
    
    # Test API
    test_api_performance()
    
    print("\n📝 Summary:")
    print("If probes setting is working, you should see:")
    print("- Direct DB queries faster with probes=3")
    print("- API query times around 100-150ms (not 400+ms)")


if __name__ == "__main__":
    asyncio.run(main())