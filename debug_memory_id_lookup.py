#!/usr/bin/env python3
"""
Debug Memory ID Lookup
Investigates why GET /memories/{id} is returning 404
"""

import asyncio
import asyncpg
import requests
import uuid
from datetime import datetime

# Configuration
PGVECTOR_CONFIG = {
    "host": "dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com",
    "port": 5432,
    "database": "nexus_memory_db",
    "user": "nexus_memory_db_user",
    "password": "2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V"
}

RENDER_SERVICE_URL = "https://core-nexus-memory-service.onrender.com"

async def debug_memory_id_lookup():
    """Debug the memory ID lookup issue"""
    print("🔍 DEBUGGING MEMORY ID LOOKUP")
    print("=" * 40)
    
    # Step 1: Get a real memory ID from the database
    print("\n📊 Step 1: Getting real memory IDs from database")
    connection = await asyncpg.connect(**PGVECTOR_CONFIG)
    
    try:
        # Get 3 recent memory IDs
        rows = await connection.fetch("""
            SELECT id, content, created_at 
            FROM vector_memories 
            ORDER BY created_at DESC 
            LIMIT 3
        """)
        
        memory_ids = []
        for row in rows:
            memory_id = str(row['id'])
            memory_ids.append(memory_id)
            print(f"  ID: {memory_id}")
            print(f"  Content: {row['content'][:50]}...")
            print(f"  Created: {row['created_at']}")
            print()
        
        if not memory_ids:
            print("❌ No memories found in database")
            return
        
        test_memory_id = memory_ids[0]
        print(f"🎯 Testing with memory ID: {test_memory_id}")
        
        # Step 2: Test direct database lookup
        print(f"\n📊 Step 2: Direct database lookup")
        direct_result = await connection.fetchrow("""
            SELECT id, content, metadata, created_at, importance_score
            FROM vector_memories 
            WHERE id = $1
        """, test_memory_id)
        
        if direct_result:
            print(f"✅ Direct DB lookup successful:")
            print(f"  ID: {direct_result['id']}")
            print(f"  Content: {direct_result['content'][:50]}...")
        else:
            print(f"❌ Direct DB lookup failed for ID: {test_memory_id}")
            return
        
        # Step 3: Test with different ID formats
        print(f"\n📊 Step 3: Testing ID format variations")
        
        # Test as string
        test_variations = [
            test_memory_id,  # Original string
            test_memory_id.lower(),  # Lowercase
            test_memory_id.upper(),  # Uppercase
        ]
        
        # Try parsing as UUID and back to string
        try:
            parsed_uuid = uuid.UUID(test_memory_id)
            test_variations.append(str(parsed_uuid))  # Standard UUID format
            print(f"  UUID parsed successfully: {parsed_uuid}")
        except ValueError as e:
            print(f"  UUID parsing failed: {e}")
        
        for i, variation in enumerate(test_variations):
            print(f"\n  Testing variation {i+1}: {variation}")
            
            try:
                db_result = await connection.fetchrow("""
                    SELECT id FROM vector_memories WHERE id = $1
                """, variation)
                
                if db_result:
                    print(f"    ✅ DB found with variation {i+1}")
                else:
                    print(f"    ❌ DB not found with variation {i+1}")
                    
            except Exception as e:
                print(f"    ❌ DB error with variation {i+1}: {e}")
        
        # Step 4: Test API endpoint directly
        print(f"\n📊 Step 4: Testing API endpoint")
        
        for i, variation in enumerate(test_variations):
            print(f"\n  Testing API with variation {i+1}: {variation}")
            
            try:
                response = requests.get(
                    f"{RENDER_SERVICE_URL}/memories/{variation}",
                    timeout=30
                )
                
                print(f"    Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"    ✅ API success: {data.get('content', '')[:50]}...")
                elif response.status_code == 404:
                    print(f"    ❌ API 404: {response.text}")
                else:
                    print(f"    ❌ API error: {response.text}")
                    
            except Exception as e:
                print(f"    ❌ API exception: {e}")
        
        # Step 5: Test if emergency retrieval is working
        print(f"\n📊 Step 5: Testing emergency retrieval directly")
        
        from emergency_foundation_fix import EmergencyMemoryRetrieval
        emergency = EmergencyMemoryRetrieval()
        await emergency.connect()
        
        try:
            emergency_result = await emergency.get_memory_by_id(test_memory_id)
            
            if emergency_result:
                print(f"✅ Emergency retrieval successful:")
                print(f"  Content: {emergency_result['content'][:50]}...")
            else:
                print(f"❌ Emergency retrieval returned None")
                
        except Exception as e:
            print(f"❌ Emergency retrieval exception: {e}")
        
        finally:
            if emergency.connection:
                await emergency.connection.close()
        
        # Step 6: Test GET /memories to see if it uses emergency mode
        print(f"\n📊 Step 6: Checking if GET /memories uses emergency mode")
        
        try:
            response = requests.get(
                f"{RENDER_SERVICE_URL}/memories",
                params={"limit": 1},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                emergency_mode = data.get("query_metadata", {}).get("emergency_mode", False)
                providers_used = data.get("providers_used", [])
                
                print(f"  Emergency mode: {emergency_mode}")
                print(f"  Providers used: {providers_used}")
                
                if not emergency_mode:
                    print("  ⚠️ Emergency mode is FALSE - emergency system may not be initializing")
                else:
                    print("  ✅ Emergency mode is TRUE - system working as expected")
                    
        except Exception as e:
            print(f"  ❌ GET /memories test failed: {e}")
        
        print(f"\n🎯 DEBUGGING COMPLETE")
        print("Possible issues:")
        print("1. Emergency retrieval system not initializing properly")
        print("2. Global variable scoping issues in FastAPI")
        print("3. UUID format mismatch")
        print("4. Path parameter parsing issues")
        print("5. Exception handling masking the real error")
        
    finally:
        await connection.close()

if __name__ == "__main__":
    asyncio.run(debug_memory_id_lookup())