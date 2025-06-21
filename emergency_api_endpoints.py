
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
