#!/usr/bin/env python3
"""
Test GraphProvider directly to isolate the issue.
"""

import asyncio
import asyncpg
import logging
from uuid import UUID

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Minimal GraphProvider implementation for testing
class TestGraphProvider:
    def __init__(self, connection_string):
        self.connection_string = connection_string
        self.connection_pool = None
    
    async def initialize(self):
        self.connection_pool = await asyncpg.create_pool(
            self.connection_string,
            min_size=2,
            max_size=10
        )
        logger.info("Connection pool initialized")
    
    async def query_entity(self, entity_name: str, limit: int = 20):
        """Query memories for a specific entity."""
        memories = []
        
        async with self.connection_pool.acquire() as conn:
            try:
                logger.info(f"Querying for entity: {entity_name}")
                
                # First check if entity exists
                entity_check = await conn.fetchrow(
                    "SELECT id, entity_name FROM graph_nodes WHERE entity_name = $1",
                    entity_name
                )
                
                if entity_check:
                    logger.info(f"Entity found with ID: {entity_check['id']}")
                else:
                    logger.warning(f"Entity not found: {entity_name}")
                    return memories
                
                # Run the exact query from GraphProvider
                rows = await conn.fetch("""
                    WITH entity_memories AS (
                        SELECT DISTINCT mem.memory_id, gr.strength as relationship_strength
                        FROM graph_nodes gn
                        JOIN memory_entity_map mem ON gn.id = mem.entity_id
                        LEFT JOIN graph_relationships gr ON (gn.id = gr.from_node_id OR gn.id = gr.to_node_id)
                        WHERE gn.entity_name = $1
                    )
                    SELECT 
                        vm.id,
                        vm.content,
                        vm.metadata,
                        vm.importance_score,
                        em.relationship_strength,
                        vm.created_at
                    FROM entity_memories em
                    JOIN vector_memories vm ON em.memory_id = vm.id
                    ORDER BY em.relationship_strength DESC NULLS LAST
                    LIMIT $2
                """, entity_name, limit)
                
                logger.info(f"Query returned {len(rows)} rows")
                
                for i, row in enumerate(rows[:3]):
                    logger.debug(f"Row {i}: ID={row['id']}, Content={row['content'][:50]}...")
                
                return rows
                
            except Exception as e:
                logger.error(f"Query failed: {e}", exc_info=True)
                raise
    
    async def close(self):
        if self.connection_pool:
            await self.connection_pool.close()

async def test():
    connection_string = (
        f"postgresql://nexus_memory_db_user:2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V@"
        f"dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com:5432/nexus_memory_db"
    )
    
    provider = TestGraphProvider(connection_string)
    
    try:
        await provider.initialize()
        
        # Test query
        results = await provider.query_entity("Von Base Enterprises", limit=10)
        
        print(f"\nFound {len(results)} memories for Von Base Enterprises")
        
        if results:
            print("\nFirst 3 memories:")
            for i, row in enumerate(results[:3]):
                print(f"{i+1}. {row['content'][:100]}...")
        
    finally:
        await provider.close()

if __name__ == "__main__":
    asyncio.run(test())