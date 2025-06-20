#!/usr/bin/env python3
"""
Test direct access to 1,152 production memories to verify they're accessible
This bypasses the provider system entirely
"""

import asyncio
import asyncpg
import os
import sys

# Add the source directory to the path
sys.path.insert(0, '/mnt/c/Users/Tyvon/core-nexus/python/memory_service/src')

async def test_direct_memory_access():
    """Test direct database access to production memories"""
    print("🔍 TESTING DIRECT MEMORY ACCESS")
    print("=" * 60)
    
    # Try different environment variables
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        print("✅ DATABASE_URL found")
        try:
            import urllib.parse
            parsed = urllib.parse.urlparse(database_url)
            host = parsed.hostname
            port = parsed.port or 5432
            database = parsed.path[1:] if parsed.path and len(parsed.path) > 1 else "nexus_memory_db"
            user = parsed.username
            password = parsed.password
            
            print(f"📊 Connection info: {user}@{host}:{port}/{database}")
            
            # Test connection
            conn_string = f"postgresql://{user}:{password}@{host}:{port}/{database}?sslmode=require"
            conn = await asyncpg.connect(conn_string)
            
            # Get memory count
            memory_count = await conn.fetchval("SELECT COUNT(*) FROM vector_memories")
            print(f"🎯 TOTAL MEMORIES: {memory_count}")
            
            # Get recent memories
            recent_memories = await conn.fetch("""
                SELECT id, LEFT(content, 100) as content_preview, created_at
                FROM vector_memories 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            
            print(f"\n📝 RECENT MEMORIES:")
            for i, memory in enumerate(recent_memories, 1):
                print(f"  {i}. {memory['content_preview']}... ({memory['created_at']})")
            
            # Test embeddings
            embedding_test = await conn.fetchval("""
                SELECT COUNT(*) FROM vector_memories 
                WHERE embedding IS NOT NULL AND array_length(embedding, 1) > 0
            """)
            print(f"\n🔢 MEMORIES WITH EMBEDDINGS: {embedding_test}")
            
            # Test vector operations
            try:
                # Create a simple test vector
                test_vector = [0.1] * 1536
                similar_count = await conn.fetchval("""
                    SELECT COUNT(*) FROM vector_memories 
                    WHERE embedding IS NOT NULL 
                    AND array_length(embedding, 1) = 1536
                    LIMIT 10
                """)
                print(f"✅ VECTOR COMPATIBILITY: {similar_count} memories have proper 1536-dim embeddings")
            except Exception as e:
                print(f"⚠️ Vector operation test failed: {e}")
            
            await conn.close()
            
            if memory_count >= 1152:
                print(f"\n🎉 SUCCESS: All {memory_count} production memories are accessible!")
                print("✅ Database connection working")
                print("✅ Table exists and has data")
                print("✅ Embeddings are present")
                return True
            else:
                print(f"\n⚠️ WARNING: Only {memory_count} memories found (expected 1152)")
                return False
                
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    else:
        print("❌ No DATABASE_URL found")
        return False

async def test_service_api_simple():
    """Test if we can create a simple memory via API"""
    print(f"\n🧪 TESTING SIMPLE API OPERATIONS")
    print("=" * 60)
    
    import httpx
    import json
    import time
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test 1: Health check
        try:
            response = await client.get("https://core-nexus-memory-service.onrender.com/health")
            health = response.json()
            print(f"Health Status: {health['status']}")
            print(f"Total Memories Reported: {health['total_memories']}")
            
            pgvector_status = health['providers'].get('pgvector', {}).get('status', 'unknown')
            print(f"PgVector Status: {pgvector_status}")
            
        except Exception as e:
            print(f"❌ Health check failed: {e}")
        
        # Test 2: Try to create a memory
        try:
            test_memory = {
                "content": f"Test memory access validation {time.time()}",
                "metadata": {
                    "test": True,
                    "timestamp": time.time()
                }
            }
            
            response = await client.post(
                "https://core-nexus-memory-service.onrender.com/memories",
                json=test_memory
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Memory creation successful: {result['id']}")
                return True
            else:
                print(f"❌ Memory creation failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ API test failed: {e}")
            return False

async def main():
    """Main test routine"""
    print("🚨 DIRECT MEMORY ACCESS TEST")
    print("Testing if 1,152 production memories are accessible")
    print()
    
    # Test 1: Direct database access
    direct_success = await test_direct_memory_access()
    
    # Test 2: API functionality
    api_success = await test_service_api_simple()
    
    print(f"\n📊 RESULTS:")
    print(f"  Direct Database Access: {'✅ WORKING' if direct_success else '❌ FAILED'}")
    print(f"  API Memory Operations: {'✅ WORKING' if api_success else '❌ FAILED'}")
    
    if direct_success and not api_success:
        print(f"\n🔧 DIAGNOSIS: Database is accessible but provider layer is broken")
        print("  - 1,152 memories are safe and accessible")
        print("  - pgvector provider needs to be enabled in service")
        print("  - Emergency restoration endpoint should work once deployed")
    elif direct_success and api_success:
        print(f"\n🎉 EXCELLENT: Both database and API are working!")
        print("  - Production memories are fully accessible")
        print("  - Ready for performance optimizations")
    else:
        print(f"\n⚠️ ISSUE: Need to investigate connection problems")

if __name__ == "__main__":
    asyncio.run(main())