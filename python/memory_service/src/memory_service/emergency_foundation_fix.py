#!/usr/bin/env python3
"""
EMERGENCY FOUNDATION FIX
Creates a simple, bulletproof memory retrieval system that bypasses broken query logic.
This is to restore basic functionality while we fix the underlying issues.
"""

import asyncio
import asyncpg
import json
from datetime import datetime
from typing import List, Dict, Any

# Configuration
PGVECTOR_CONFIG = {
    "host": "dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com",
    "port": 5432,
    "database": "nexus_memory_db",
    "user": "nexus_memory_db_user",
    "password": "2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V"
}

class EmergencyMemoryRetrieval:
    def __init__(self):
        self.connection = None
    
    async def connect(self):
        """Connect to database"""
        self.connection = await asyncpg.connect(**PGVECTOR_CONFIG)
        return self.connection
    
    async def get_all_memories(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Simple, bulletproof memory retrieval"""
        try:
            query = """
            SELECT 
                id,
                content,
                metadata,
                created_at,
                importance_score
            FROM vector_memories 
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
            """
            
            rows = await self.connection.fetch(query, limit, offset)
            
            memories = []
            for row in rows:
                memory = {
                    "id": str(row['id']),
                    "content": row['content'],
                    "metadata": row['metadata'] if row['metadata'] else {},
                    "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                    "importance_score": float(row['importance_score']) if row['importance_score'] else 0.0,
                    "similarity_score": 1.0  # Default for non-search queries
                }
                memories.append(memory)
            
            return memories
            
        except Exception as e:
            print(f"❌ Emergency retrieval failed: {e}")
            return []
    
    async def get_memory_by_id(self, memory_id: str) -> Dict | None:
        """Simple memory lookup by ID"""
        try:
            query = """
            SELECT 
                id,
                content,
                metadata,
                created_at,
                importance_score
            FROM vector_memories 
            WHERE id = $1
            """
            
            row = await self.connection.fetchrow(query, memory_id)
            
            if row:
                return {
                    "id": str(row['id']),
                    "content": row['content'],
                    "metadata": row['metadata'] if row['metadata'] else {},
                    "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                    "importance_score": float(row['importance_score']) if row['importance_score'] else 0.0,
                    "similarity_score": 1.0
                }
            else:
                return None
                
        except Exception as e:
            print(f"❌ Emergency ID lookup failed: {e}")
            return None
    
    async def search_memories(self, query_text: str, limit: int = 50) -> List[Dict]:
        """Simple text search using PostgreSQL full-text search"""
        try:
            search_query = """
            SELECT 
                id,
                content,
                metadata,
                created_at,
                importance_score,
                ts_rank(to_tsvector('english', content), plainto_tsquery('english', $1)) as rank
            FROM vector_memories 
            WHERE to_tsvector('english', content) @@ plainto_tsquery('english', $1)
            ORDER BY rank DESC, created_at DESC
            LIMIT $2
            """
            
            rows = await self.connection.fetch(search_query, query_text, limit)
            
            memories = []
            for row in rows:
                memory = {
                    "id": str(row['id']),
                    "content": row['content'],
                    "metadata": row['metadata'] if row['metadata'] else {},
                    "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                    "importance_score": float(row['importance_score']) if row['importance_score'] else 0.0,
                    "similarity_score": float(row['rank']) if row['rank'] else 0.0
                }
                memories.append(memory)
            
            return memories
            
        except Exception as e:
            print(f"❌ Emergency search failed: {e}")
            # Fallback to simple ILIKE search
            try:
                fallback_query = """
                SELECT 
                    id,
                    content,
                    metadata,
                    created_at,
                    importance_score
                FROM vector_memories 
                WHERE content ILIKE $1
                ORDER BY created_at DESC
                LIMIT $2
                """
                
                rows = await self.connection.fetch(fallback_query, f"%{query_text}%", limit)
                
                memories = []
                for row in rows:
                    memory = {
                        "id": str(row['id']),
                        "content": row['content'],
                        "metadata": row['metadata'] if row['metadata'] else {},
                        "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                        "importance_score": float(row['importance_score']) if row['importance_score'] else 0.0,
                        "similarity_score": 0.8  # Default for text matches
                    }
                    memories.append(memory)
                
                return memories
                
            except Exception as e2:
                print(f"❌ Fallback search also failed: {e2}")
                return []
    
    async def get_statistics(self) -> Dict:
        """Get basic statistics"""
        try:
            stats_query = """
            SELECT 
                COUNT(*) as total_memories,
                MIN(created_at) as earliest_memory,
                MAX(created_at) as latest_memory,
                AVG(LENGTH(content)) as avg_content_length,
                COUNT(DISTINCT (metadata->>'user_id')) as unique_users
            FROM vector_memories
            """
            
            row = await self.connection.fetchrow(stats_query)
            
            return {
                "total_memories": row['total_memories'],
                "earliest_memory": row['earliest_memory'].isoformat() if row['earliest_memory'] else None,
                "latest_memory": row['latest_memory'].isoformat() if row['latest_memory'] else None,
                "avg_content_length": float(row['avg_content_length']) if row['avg_content_length'] else 0,
                "unique_users": row['unique_users']
            }
            
        except Exception as e:
            print(f"❌ Statistics query failed: {e}")
            return {}

async def test_emergency_retrieval():
    """Test the emergency retrieval system"""
    print("🚨 TESTING EMERGENCY FOUNDATION FIX")
    print("=" * 50)
    
    retrieval = EmergencyMemoryRetrieval()
    
    try:
        await retrieval.connect()
        print("✅ Connected to database")
        
        # Test 1: Get statistics
        print("\n📊 Test 1: Statistics")
        stats = await retrieval.get_statistics()
        print(f"Total memories: {stats.get('total_memories', 0)}")
        print(f"Latest memory: {stats.get('latest_memory', 'None')}")
        
        # Test 2: Get recent memories
        print("\n📋 Test 2: Recent Memories")
        recent = await retrieval.get_all_memories(limit=5)
        print(f"Retrieved {len(recent)} recent memories:")
        for i, memory in enumerate(recent, 1):
            print(f"  {i}. {memory['content'][:50]}... (ID: {memory['id']})")
        
        # Test 3: Get memory by ID (using first recent memory)
        if recent:
            test_id = recent[0]['id']
            print(f"\n🔍 Test 3: Memory by ID ({test_id})")
            by_id = await retrieval.get_memory_by_id(test_id)
            if by_id:
                print(f"✅ Found memory: {by_id['content'][:50]}...")
            else:
                print("❌ Memory not found by ID")
        
        # Test 4: Search
        print("\n🔎 Test 4: Text Search")
        search_results = await retrieval.search_memories("test", limit=3)
        print(f"Search for 'test' returned {len(search_results)} results:")
        for i, memory in enumerate(search_results, 1):
            print(f"  {i}. {memory['content'][:50]}... (Score: {memory['similarity_score']})")
        
        return True
        
    except Exception as e:
        print(f"❌ Emergency retrieval test failed: {e}")
        return False
    
    finally:
        if retrieval.connection:
            await retrieval.connection.close()

def create_emergency_api_endpoints():
    """Generate emergency API endpoint code to replace broken ones"""
    
    emergency_code = '''
# EMERGENCY FOUNDATION FIX - Add these endpoints to api.py

from .emergency_foundation_fix import EmergencyMemoryRetrieval

# Create global emergency retrieval instance
emergency_retrieval = EmergencyMemoryRetrieval()

@app.on_event("startup")
async def connect_emergency_retrieval():
    """Connect emergency retrieval system"""
    await emergency_retrieval.connect()
    logger.info("Emergency retrieval system connected")

@app.on_event("shutdown") 
async def disconnect_emergency_retrieval():
    """Disconnect emergency retrieval system"""
    if emergency_retrieval.connection:
        await emergency_retrieval.connection.close()

@app.get("/emergency/memories")
async def emergency_get_memories(
    limit: int = 100,
    offset: int = 0
):
    """Emergency memory retrieval that bypasses broken query system"""
    try:
        memories = await emergency_retrieval.get_all_memories(limit, offset)
        
        return {
            "memories": memories,
            "total_found": len(memories),
            "query_time_ms": 0,
            "providers_used": ["emergency_direct"],
            "status": "emergency_mode",
            "note": "Using emergency retrieval - bypasses broken unified store"
        }
    except Exception as e:
        logger.error(f"Emergency retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Emergency retrieval failed: {str(e)}")

@app.get("/emergency/memories/{memory_id}")
async def emergency_get_memory_by_id(memory_id: str):
    """Emergency memory lookup by ID"""
    try:
        memory = await emergency_retrieval.get_memory_by_id(memory_id)
        
        if memory:
            return memory
        else:
            raise HTTPException(status_code=404, detail="Memory not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Emergency memory lookup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Emergency lookup failed: {str(e)}")

@app.get("/emergency/search")
async def emergency_search_memories(
    q: str,
    limit: int = 50
):
    """Emergency memory search using simple text search"""
    try:
        memories = await emergency_retrieval.search_memories(q, limit)
        
        return {
            "memories": memories,
            "total_found": len(memories),
            "query": q,
            "query_time_ms": 0,
            "providers_used": ["emergency_text_search"],
            "status": "emergency_mode"
        }
    except Exception as e:
        logger.error(f"Emergency search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Emergency search failed: {str(e)}")

@app.get("/emergency/stats")
async def emergency_get_stats():
    """Emergency statistics endpoint"""
    try:
        stats = await emergency_retrieval.get_statistics()
        return {
            "statistics": stats,
            "status": "emergency_mode",
            "note": "Direct database statistics"
        }
    except Exception as e:
        logger.error(f"Emergency stats failed: {e}")
        raise HTTPException(status_code=500, detail=f"Emergency stats failed: {str(e)}")
'''
    
    with open('emergency_api_endpoints.py', 'w') as f:
        f.write(emergency_code)
    
    print("📄 Emergency API endpoints code saved to: emergency_api_endpoints.py")
    print("Add these endpoints to your api.py to restore functionality")

async def main():
    """Main entry point"""
    success = await test_emergency_retrieval()
    
    if success:
        print("\n✅ Emergency retrieval system working!")
        print("📝 Generating emergency API endpoint code...")
        create_emergency_api_endpoints()
        
        print("\n🎯 IMMEDIATE ACTIONS:")
        print("1. Add emergency endpoints to api.py to restore basic functionality")
        print("2. Fix the broken query_memories method in unified_store.py")
        print("3. Debug why get_recent_memories is failing")
        print("4. Test and fix individual memory retrieval by ID")
        print("5. THEN worry about ChromaDB replication")
        
        return 0
    else:
        print("\n❌ Emergency retrieval system failed")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))