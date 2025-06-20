#!/usr/bin/env python3
"""
Debug pgvector provider initialization failure
This will help us understand why pgvector is disabled
"""

import asyncio
import asyncpg
import os
import sys

# Add the source directory to the path
sys.path.insert(0, '/mnt/c/Users/Tyvon/core-nexus/python/memory_service/src')

async def debug_pgvector_initialization():
    """Debug why pgvector provider is failing to initialize"""
    print("🔍 DEBUGGING PGVECTOR INITIALIZATION FAILURE")
    print("="*60)
    
    # Check environment variables
    pgvector_host = os.getenv("PGVECTOR_HOST", "dpg-d12n0np5pdvs73ctmm40-a")
    pgvector_password = os.getenv("PGPASSWORD") or os.getenv("PGVECTOR_PASSWORD")
    pgvector_port = int(os.getenv("PGVECTOR_PORT", "5432"))
    pgvector_database = os.getenv("PGVECTOR_DATABASE", "nexus_memory_db")
    pgvector_user = os.getenv("PGVECTOR_USER", "nexus_memory_db_user")
    
    print("📋 Environment Variables:")
    print(f"  PGVECTOR_HOST: {pgvector_host}")
    print(f"  PGVECTOR_PORT: {pgvector_port}")
    print(f"  PGVECTOR_DATABASE: {pgvector_database}")
    print(f"  PGVECTOR_USER: {pgvector_user}")
    print(f"  PGPASSWORD: {'SET' if os.getenv('PGPASSWORD') else 'NOT SET'}")
    print(f"  PGVECTOR_PASSWORD: {'SET' if os.getenv('PGVECTOR_PASSWORD') else 'NOT SET'}")
    print(f"  Password available: {'YES' if pgvector_password else 'NO'}")
    print()
    
    if not pgvector_password:
        print("❌ CRITICAL: No password found in environment variables")
        print("   This is why pgvector provider is disabled!")
        print("   The service falls back to ChromaDB (0 memories)")
        print("   Need to set PGPASSWORD or PGVECTOR_PASSWORD")
        return False
    
    # Try to connect directly
    print("🔌 Testing direct database connection...")
    try:
        conn_string = f"postgresql://{pgvector_user}:{pgvector_password}@{pgvector_host}:{pgvector_port}/{pgvector_database}?sslmode=require"
        
        conn = await asyncpg.connect(conn_string)
        
        # Test basic queries
        memory_count = await conn.fetchval("SELECT COUNT(*) FROM vector_memories")
        print(f"✅ Connection successful! Found {memory_count} memories")
        
        # Check if pgvector extension is available
        vector_support = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')")
        print(f"✅ pgvector extension: {'AVAILABLE' if vector_support else 'MISSING'}")
        
        await conn.close()
        return True
        
    except asyncpg.exceptions.InvalidPasswordError:
        print("❌ Invalid password - authentication failed")
        return False
    except asyncpg.exceptions.ConnectionError as e:
        print(f"❌ Connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

async def test_provider_initialization():
    """Test the actual provider initialization"""
    print("\n🧪 Testing Provider Initialization...")
    
    try:
        from memory_service.providers import PgVectorProvider
        from memory_service.models import ProviderConfig
        
        pgvector_host = os.getenv("PGVECTOR_HOST", "dpg-d12n0np5pdvs73ctmm40-a")
        pgvector_password = os.getenv("PGPASSWORD") or os.getenv("PGVECTOR_PASSWORD")
        
        if not pgvector_password:
            print("❌ Cannot test provider - no password available")
            return False
            
        pgvector_config = ProviderConfig(
            name="pgvector",
            enabled=True,
            primary=True,
            config={
                "host": pgvector_host,
                "port": int(os.getenv("PGVECTOR_PORT", "5432")),
                "database": os.getenv("PGVECTOR_DATABASE", "nexus_memory_db"),
                "user": os.getenv("PGVECTOR_USER", "nexus_memory_db_user"),
                "password": pgvector_password,
                "table_name": "vector_memories",
                "embedding_dim": 1536,
                "distance_metric": "cosine"
            }
        )
        
        provider = PgVectorProvider(pgvector_config)
        await provider.initialize()
        
        print("✅ Provider initialization successful!")
        
        # Test health check
        health = await provider.health_check()
        print(f"✅ Health check: {health}")
        
        await provider.close()
        return True
        
    except Exception as e:
        print(f"❌ Provider initialization failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False

async def main():
    """Main debugging routine"""
    print("🚨 CRITICAL ISSUE: pgvector provider disabled")
    print("   This means 1,152 production memories are inaccessible")
    print("   /memories endpoint returns internal server error")
    print()
    
    # Test direct connection
    direct_success = await debug_pgvector_initialization()
    
    if direct_success:
        # Test provider initialization
        provider_success = await test_provider_initialization()
        
        if provider_success:
            print("\n🎉 PGVECTOR IS WORKING!")
            print("   The issue must be in the service initialization logic")
            print("   Need to check why provider is being disabled at startup")
        else:
            print("\n⚠️ Direct connection works but provider initialization fails")
            print("   Need to debug the provider initialization code")
    else:
        print("\n❌ Direct connection failed")
        print("   Need to fix environment variables or connection settings")
        
    print("\n🔧 NEXT STEPS:")
    print("1. Ensure environment variables are properly set in production")
    print("2. Check service logs for initialization errors")
    print("3. Fix provider initialization logic if needed")
    print("4. Restart service to restore access to 1,152 memories")

if __name__ == "__main__":
    asyncio.run(main())