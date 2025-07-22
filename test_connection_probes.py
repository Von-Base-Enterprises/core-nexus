#!/usr/bin/env python3
"""
Test if the connection pool setup is working for probes.
"""

import asyncio
import asyncpg

DB_URL = "postgresql://nexus_memory_db_user:2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V@dpg-d12n0np5pdvs73ctmm40-a.ohio-postgres.render.com:5432/nexus_memory_db"

async def test_connection_pool_setup():
    """Test if connection pool setup is working"""
    print("🧪 Testing Connection Pool Setup for Probes")
    print("=============================================\n")
    
    async def setup_connection(conn):
        """Setup function to set probes"""
        try:
            await conn.execute("SET ivfflat.probes = 3")
            print("  ✅ Setup function: Set probes=3")
        except Exception as e:
            print(f"  ❌ Setup function error: {e}")
    
    # Create pool with setup function
    print("Creating connection pool with setup function...")
    pool = await asyncpg.create_pool(
        DB_URL,
        min_size=2,
        max_size=5,
        setup=setup_connection
    )
    
    # Test multiple connections from the pool
    print("\nTesting connections from pool:")
    for i in range(3):
        async with pool.acquire() as conn:
            try:
                # Check current probes setting
                probes = await conn.fetchval("SHOW ivfflat.probes")
                print(f"  Connection {i+1}: probes = {probes}")
                
                # Test query performance
                sample = await conn.fetchval("SELECT embedding FROM vector_memories LIMIT 1")
                
                import time
                start = time.perf_counter()
                results = await conn.fetch("""
                    SELECT id, 1 - (embedding <=> $1) AS similarity
                    FROM vector_memories 
                    ORDER BY embedding <=> $1
                    LIMIT 5
                """, sample)
                duration = (time.perf_counter() - start) * 1000
                
                print(f"    Query time: {duration:.1f}ms, Results: {len(results)}")
                
            except Exception as e:
                print(f"  ❌ Connection {i+1} error: {e}")
    
    await pool.close()

async def test_manual_probes_per_query():
    """Test setting probes manually for each query"""
    print("\n🔧 Testing Manual Probes per Query")
    print("===================================\n")
    
    pool = await asyncpg.create_pool(DB_URL, min_size=1, max_size=3)
    
    sample = None
    async with pool.acquire() as conn:
        sample = await conn.fetchval("SELECT embedding FROM vector_memories LIMIT 1")
    
    for probes_val in [1, 3]:
        print(f"Testing with probes={probes_val}:")
        
        async with pool.acquire() as conn:
            try:
                # Set probes for this connection
                await conn.execute(f"SET ivfflat.probes = {probes_val}")
                
                # Verify it was set
                current = await conn.fetchval("SHOW ivfflat.probes")
                print(f"  Set probes={current}")
                
                # Time the query
                import time
                start = time.perf_counter()
                results = await conn.fetch("""
                    SELECT id, 1 - (embedding <=> $1) AS similarity
                    FROM vector_memories 
                    ORDER BY embedding <=> $1
                    LIMIT 10
                """, sample)
                duration = (time.perf_counter() - start) * 1000
                
                print(f"  Query time: {duration:.1f}ms, Results: {len(results)}\n")
                
            except Exception as e:
                print(f"  ❌ Error: {e}\n")
    
    await pool.close()

async def main():
    await test_connection_pool_setup()
    await test_manual_probes_per_query()

if __name__ == "__main__":
    asyncio.run(main())