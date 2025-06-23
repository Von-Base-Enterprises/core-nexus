#!/usr/bin/env python3
"""
Simple Migration Status Checker
"""

import asyncio
import asyncpg
import os

async def check_status():
    """Check migration status."""
    
    db_config = {
        'host': 'dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com',
        'port': 5432,
        'database': 'nexus_memory_db',
        'user': 'nexus_memory_db_user',
        'password': os.getenv('PGVECTOR_PASSWORD')
    }
    
    conn = await asyncpg.connect(**db_config)
    
    try:
        # Check counts
        original_count = await conn.fetchval("SELECT COUNT(*) FROM vector_memories WHERE embedding IS NOT NULL")
        optimized_count = await conn.fetchval("SELECT COUNT(*) FROM vector_memories_optimized WHERE embedding IS NOT NULL")
        
        print(f"\n📊 MIGRATION STATUS:")
        print(f"   Original vectors: {original_count}")
        print(f"   Optimized vectors: {optimized_count}")
        print(f"   Progress: {(optimized_count/original_count*100):.1f}%")
        print(f"   Remaining: {original_count - optimized_count}")
        
        if optimized_count >= original_count:
            print("🎉 MIGRATION COMPLETE!")
        else:
            print(f"🔄 Migration in progress...")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_status())