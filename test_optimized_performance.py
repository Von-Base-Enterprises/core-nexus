#!/usr/bin/env python3
"""
Test Optimized Performance
Direct database test to verify the optimization improvements.
"""

import asyncio
import asyncpg
import os
import time
import statistics

async def test_performance():
    """Test query performance on both tables."""
    
    db_config = {
        'host': 'dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com',
        'port': 5432,
        'database': 'nexus_memory_db',
        'user': 'nexus_memory_db_user',
        'password': os.getenv('PGVECTOR_PASSWORD')
    }
    
    conn = await asyncpg.connect(**db_config)
    
    try:
        print("🔬 PERFORMANCE TESTING: Original vs Optimized Vectors")
        print("="*60)
        
        # Test 1: Count vectors
        print("\n📊 Vector Counts:")
        original_count = await conn.fetchval("SELECT COUNT(*) FROM vector_memories WHERE embedding IS NOT NULL")
        optimized_count = await conn.fetchval("SELECT COUNT(*) FROM vector_memories_optimized WHERE embedding IS NOT NULL") 
        print(f"   Original table: {original_count} vectors")
        print(f"   Optimized table: {optimized_count} vectors")
        
        # Test 2: Sample content comparison
        print("\n📄 Sample Content Verification:")
        original_sample = await conn.fetchrow("SELECT id, content FROM vector_memories WHERE embedding IS NOT NULL LIMIT 1")
        optimized_sample = await conn.fetchrow("SELECT id, content FROM vector_memories_optimized WHERE id = $1", original_sample['id'])
        
        if optimized_sample:
            print(f"   ✅ Content preserved: {original_sample['content'][:100]}...")
            content_match = original_sample['content'] == optimized_sample['content']
            print(f"   ✅ Content integrity: {'PASS' if content_match else 'FAIL'}")
        else:
            print(f"   ❌ Vector {original_sample['id']} not found in optimized table")
        
        # Test 3: Query performance comparison
        print("\n⚡ Query Performance Test:")
        
        # Get a test vector for similarity search
        test_vector_row = await conn.fetchrow("SELECT embedding FROM vector_memories_optimized WHERE embedding IS NOT NULL LIMIT 1")
        test_vector = test_vector_row['embedding']
        
        # Test original table performance
        original_times = []
        for i in range(5):
            start_time = time.time()
            try:
                result = await conn.fetch("""
                    SELECT id, content, embedding <-> $1 as distance 
                    FROM vector_memories 
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <-> $1 
                    LIMIT 10
                """, test_vector)
                end_time = time.time()
                original_times.append((end_time - start_time) * 1000)  # Convert to ms
            except Exception as e:
                print(f"   ❌ Original table query failed: {e}")
                original_times.append(float('inf'))
        
        # Test optimized table performance  
        optimized_times = []
        for i in range(5):
            start_time = time.time()
            try:
                result = await conn.fetch("""
                    SELECT id, content, embedding <-> $1 as distance 
                    FROM vector_memories_optimized 
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <-> $1 
                    LIMIT 10
                """, test_vector)
                end_time = time.time()
                optimized_times.append((end_time - start_time) * 1000)  # Convert to ms
            except Exception as e:
                print(f"   ❌ Optimized table query failed: {e}")
                optimized_times.append(float('inf'))
        
        # Calculate and display results
        original_avg = statistics.mean([t for t in original_times if t != float('inf')])
        optimized_avg = statistics.mean([t for t in optimized_times if t != float('inf')])
        
        print(f"\n📈 PERFORMANCE RESULTS:")
        print(f"   Original table average: {original_avg:.1f}ms")
        print(f"   Optimized table average: {optimized_avg:.1f}ms")
        
        if original_avg != float('inf') and optimized_avg != float('inf'):
            improvement = ((original_avg - optimized_avg) / original_avg) * 100
            speedup = original_avg / optimized_avg
            print(f"   🚀 Performance improvement: {improvement:.1f}%")
            print(f"   🚀 Speedup factor: {speedup:.1f}x")
            
            if improvement > 50:
                print(f"   ✅ SIGNIFICANT IMPROVEMENT ACHIEVED!")
            elif improvement > 0:
                print(f"   ✅ Performance improvement confirmed")
            else:
                print(f"   ⚠️  Expected improvement not detected")
        
        # Test 4: Storage efficiency
        print(f"\n💾 Storage Efficiency:")
        original_size = await conn.fetchval("SELECT pg_size_pretty(pg_total_relation_size('vector_memories'))")
        optimized_size = await conn.fetchval("SELECT pg_size_pretty(pg_total_relation_size('vector_memories_optimized'))")
        
        print(f"   Original table size: {original_size}")
        print(f"   Optimized table size: {optimized_size}")
        
        # Test 5: Vector dimensions verification
        print(f"\n🔍 Vector Dimensions:")
        try:
            original_dims = await conn.fetchval("SELECT array_length(embedding, 1) FROM vector_memories WHERE embedding IS NOT NULL LIMIT 1")
            optimized_dims = await conn.fetchval("SELECT array_length(embedding, 1) FROM vector_memories_optimized WHERE embedding IS NOT NULL LIMIT 1")
            
            print(f"   Original dimensions: {original_dims}")
            print(f"   Optimized dimensions: {optimized_dims}")
            
            if optimized_dims == 1536:
                print(f"   ✅ Dimension optimization confirmed!")
            else:
                print(f"   ❌ Unexpected dimensions in optimized table")
                
        except Exception as e:
            print(f"   ⚠️  Dimension check failed: {e}")
        
        print(f"\n" + "="*60)
        print("🎯 OPTIMIZATION TEST COMPLETE")
        
        if optimized_count == original_count and improvement > 0:
            print("✅ Vector dimension optimization successful!")
        else:
            print("⚠️  Some issues detected - review results above")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    if not os.getenv('PGVECTOR_PASSWORD'):
        print("❌ PGVECTOR_PASSWORD environment variable required")
    else:
        asyncio.run(test_performance())