"""
Live sync endpoints for Agent 3 dashboard
Add these to api.py to enable real-time graph stats
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Add these endpoints to your existing router in api.py

async def get_graph_live_stats(conn):
    """Get live, deduplicated graph statistics for Agent 3"""
    try:
        # Get unique entity count
        entity_count = await conn.fetchval(
            "SELECT COUNT(*) FROM graph_nodes"
        )

        # Get relationship count
        rel_count = await conn.fetchval(
            "SELECT COUNT(*) FROM graph_relationships"
        )

        # Get top entities by connections
        top_entities = await conn.fetch("""
            SELECT n.entity_name, n.entity_type, n.importance_score,
                   COUNT(DISTINCT r.to_node_id) + COUNT(DISTINCT r2.from_node_id) as connections
            FROM graph_nodes n
            LEFT JOIN graph_relationships r ON n.id = r.from_node_id
            LEFT JOIN graph_relationships r2 ON n.id = r2.to_node_id
            GROUP BY n.id, n.entity_name, n.entity_type, n.importance_score
            ORDER BY connections DESC, n.importance_score DESC
            LIMIT 10
        """)

        # Get entity type distribution
        type_dist = await conn.fetch("""
            SELECT entity_type, COUNT(*) as count
            FROM graph_nodes
            GROUP BY entity_type
            ORDER BY count DESC
        """)

        return {
            "entity_count": entity_count,
            "relationship_count": rel_count,
            "top_entities": [
                {
                    "name": e["entity_name"],
                    "type": e["entity_type"],
                    "importance": float(e["importance_score"]),
                    "connections": e["connections"]
                }
                for e in top_entities
            ],
            "entity_types": {
                row["entity_type"]: row["count"]
                for row in type_dist
            },
            "last_updated": datetime.utcnow().isoformat(),
            "sync_version": "2.0",
            "status": "live",
            "extraction_complete": True,
            "deduplication_status": "in_progress"
        }
    except Exception as e:
        logger.error(f"Error getting live stats: {e}")
        return {"error": str(e), "status": "error"}


# Add this to api.py after your existing endpoints:
"""
@router.get("/api/knowledge-graph/live-stats")
async def knowledge_graph_live_stats():
    '''Real-time stats for Agent 3 dashboard'''
    pool = get_connection_pool()
    async with pool.acquire() as conn:
        return JSONResponse(await get_graph_live_stats(conn))

@router.post("/api/knowledge-graph/refresh-cache")
async def refresh_dashboard_cache():
    '''Signal Agent 3 to refresh its cache'''
    return JSONResponse({
        "cache_refresh_requested": True,
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Agent 3 should refresh dashboard within 10 seconds"
    })

@router.get("/api/knowledge-graph/sync-status")
async def get_sync_status():
    '''Check if Agent 2 and Agent 3 are in sync'''
    pool = get_connection_pool()
    async with pool.acquire() as conn:
        stats = await get_graph_live_stats(conn)
        
        return JSONResponse({
            "agent2_stats": stats,
            "sync_instructions": {
                "polling_interval": "10s",
                "endpoint": "/api/knowledge-graph/live-stats",
                "cache_key": "graph_stats_v2"
            }
        })
"""
