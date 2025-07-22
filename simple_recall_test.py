#!/usr/bin/env python3
"""
Simple Recall Test for pgvector

Tests the recall of the current IVFFlat index configuration.
"""

import asyncio
import asyncpg
import numpy as np
import time
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_recall():
    """Test recall by comparing a few queries with and without index."""
    db_url = (
        "postgresql://nexus_memory_db_user:2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V@"
        "dpg-d12n0np5pdvs73ctmm40-a.ohio-postgres.render.com:5432/nexus_memory_db"
    )
    
    logger.info("🔍 Testing pgvector recall...")
    conn = await asyncpg.connect(db_url)
    
    # Get a sample embedding from the database
    sample_row = await conn.fetchrow("""
        SELECT id, embedding::text
        FROM vector_memories
        WHERE embedding IS NOT NULL
        LIMIT 1
    """)
    
    if not sample_row:
        logger.error("No embeddings found")
        await conn.close()
        return
    
    sample_embedding = sample_row['embedding']
    logger.info(f"Using embedding from memory ID: {sample_row['id']}")
    
    # Test 1: Exact search (no index)
    logger.info("\n1. Testing exact search (index disabled)...")
    await conn.execute("SET LOCAL enable_indexscan = OFF")
    
    start = time.time()
    exact_results = await conn.fetch("""
        SELECT id, content
        FROM vector_memories
        ORDER BY embedding <=> $1::vector
        LIMIT 10
    """, sample_embedding)
    exact_time = (time.time() - start) * 1000
    
    exact_ids = [str(r['id']) for r in exact_results]
    logger.info(f"  Found {len(exact_ids)} results in {exact_time:.1f}ms")
    
    # Test 2: Approximate search (with index)
    logger.info("\n2. Testing approximate search (index enabled)...")
    await conn.execute("SET LOCAL enable_indexscan = ON")
    
    start = time.time()
    approx_results = await conn.fetch("""
        SELECT id, content
        FROM vector_memories
        ORDER BY embedding <=> $1::vector
        LIMIT 10
    """, sample_embedding)
    approx_time = (time.time() - start) * 1000
    
    approx_ids = [str(r['id']) for r in approx_results]
    logger.info(f"  Found {len(approx_ids)} results in {approx_time:.1f}ms")
    
    # Calculate recall
    matches = sum(1 for aid in approx_ids if aid in exact_ids)
    recall = matches / len(exact_ids) if exact_ids else 1.0
    
    logger.info(f"\n📊 Results:")
    logger.info(f"  Recall: {recall:.1%} ({matches}/{len(exact_ids)} matches)")
    logger.info(f"  Speedup: {exact_time/approx_time:.1f}x")
    logger.info(f"  Exact search: {exact_time:.1f}ms")
    logger.info(f"  Approx search: {approx_time:.1f}ms")
    
    # Test 3: Check if results are in the same order
    order_matches = sum(1 for i, aid in enumerate(approx_ids) if i < len(exact_ids) and aid == exact_ids[i])
    order_accuracy = order_matches / min(len(exact_ids), len(approx_ids))
    logger.info(f"  Order accuracy: {order_accuracy:.1%}")
    
    # Test 4: Multiple queries
    logger.info("\n3. Testing with multiple random queries...")
    recalls = []
    speedups = []
    
    for i in range(5):
        # Get a random embedding
        random_row = await conn.fetchrow("""
            SELECT embedding::text
            FROM vector_memories
            WHERE embedding IS NOT NULL
            ORDER BY RANDOM()
            LIMIT 1
        """)
        
        if random_row:
            test_embedding = random_row['embedding']
            
            # Exact search
            await conn.execute("SET LOCAL enable_indexscan = OFF")
            start = time.time()
            exact_results = await conn.fetch("""
                SELECT id FROM vector_memories
                ORDER BY embedding <=> $1::vector
                LIMIT 10
            """, test_embedding)
            exact_time = (time.time() - start) * 1000
            exact_ids = [str(r['id']) for r in exact_results]
            
            # Approximate search
            await conn.execute("SET LOCAL enable_indexscan = ON")
            start = time.time()
            approx_results = await conn.fetch("""
                SELECT id FROM vector_memories
                ORDER BY embedding <=> $1::vector
                LIMIT 10
            """, test_embedding)
            approx_time = (time.time() - start) * 1000
            approx_ids = [str(r['id']) for r in approx_results]
            
            # Calculate metrics
            matches = sum(1 for aid in approx_ids if aid in exact_ids)
            recall = matches / len(exact_ids) if exact_ids else 1.0
            speedup = exact_time / approx_time if approx_time > 0 else 0
            
            recalls.append(recall)
            speedups.append(speedup)
            
            logger.info(f"  Query {i+1}: Recall={recall:.1%}, Speedup={speedup:.1f}x")
    
    if recalls:
        avg_recall = sum(recalls) / len(recalls)
        avg_speedup = sum(speedups) / len(speedups)
        
        logger.info(f"\n📈 Summary:")
        logger.info(f"  Average recall: {avg_recall:.1%}")
        logger.info(f"  Average speedup: {avg_speedup:.1f}x")
        logger.info(f"  Min recall: {min(recalls):.1%}")
        logger.info(f"  Max recall: {max(recalls):.1%}")
    
    # Save results
    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "single_query_test": {
            "recall": recall,
            "speedup": exact_time/approx_time if approx_time > 0 else 0,
            "exact_time_ms": exact_time,
            "approx_time_ms": approx_time,
            "order_accuracy": order_accuracy
        },
        "multi_query_test": {
            "avg_recall": avg_recall if recalls else 0,
            "min_recall": min(recalls) if recalls else 0,
            "max_recall": max(recalls) if recalls else 0,
            "avg_speedup": avg_speedup if speedups else 0,
            "num_queries": len(recalls)
        }
    }
    
    with open('simple_recall_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\n✅ Results saved to simple_recall_results.json")
    
    await conn.close()


async def main():
    await test_recall()


if __name__ == "__main__":
    asyncio.run(main())