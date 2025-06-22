#!/usr/bin/env python3
"""
Quick test to diagnose environment variable issues and establish database connectivity.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the memory service to the path
sys.path.append(str(Path(__file__).parent / "python" / "memory_service" / "src"))

async def test_environment_and_database():
    """Test environment variables and database connectivity."""
    print("=== ENVIRONMENT DIAGNOSIS ===")
    
    # Check all environment variables
    print("Environment variables with 'PG':")
    pg_vars = {k: v for k, v in os.environ.items() if 'PG' in k.upper()}
    for k, v in pg_vars.items():
        print(f"  {k}: {'***REDACTED***' if 'PASSWORD' in k.upper() else v}")
    
    # Check memory service config
    try:
        from memory_service.config import DatabaseConfig
        print("\n=== DATABASE CONFIG ===")
        print(f"Host: {DatabaseConfig.HOST}")
        print(f"Port: {DatabaseConfig.PORT}")
        print(f"Database: {DatabaseConfig.DATABASE}")
        print(f"User: {DatabaseConfig.USER}")
        print(f"Password: {'***SET***' if DatabaseConfig.PASSWORD else 'NOT_SET'}")
    except Exception as e:
        print(f"Config import failed: {e}")
        return
    
    # Test database connection
    if DatabaseConfig.PASSWORD:
        print("\n=== DATABASE CONNECTION TEST ===")
        try:
            import asyncpg
            
            conn_str = f"postgresql://{DatabaseConfig.USER}:{DatabaseConfig.PASSWORD}@{DatabaseConfig.HOST}:{DatabaseConfig.PORT}/{DatabaseConfig.DATABASE}"
            print(f"Connecting to: {DatabaseConfig.USER}@{DatabaseConfig.HOST}:{DatabaseConfig.PORT}/{DatabaseConfig.DATABASE}")
            
            conn = await asyncpg.connect(conn_str, command_timeout=10)
            
            # Test basic queries
            version = await conn.fetchval("SELECT version()")
            print(f"✅ Connected! PostgreSQL version: {version[:50]}...")
            
            # Test vector extension
            vector_extension = await conn.fetchval("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            print(f"✅ Vector extension: {vector_extension}")
            
            # Test vector_memories table
            table_count = await conn.fetchval("SELECT COUNT(*) FROM vector_memories")
            print(f"✅ vector_memories table: {table_count} rows")
            
            # Simple performance test
            import time
            start_time = time.time()
            test_vector = [0.1] * 1536
            
            rows = await conn.fetch("""
                SELECT id, embedding <=> $1::vector as distance
                FROM vector_memories
                ORDER BY embedding <=> $1::vector
                LIMIT 5
            """, test_vector)
            
            query_time = (time.time() - start_time) * 1000
            print(f"✅ Sample query: {len(rows)} results in {query_time:.1f}ms")
            
            await conn.close()
            
            print(f"\n🎯 REAL BASELINE: {query_time:.1f}ms query time")
            print(f"🎯 IMPROVEMENT TARGET: <20ms (potential {((query_time - 20) / query_time * 100):.1f}% improvement)")
            
            return True
            
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False
    else:
        print("❌ No database password available")
        return False

if __name__ == "__main__":
    asyncio.run(test_environment_and_database())