#!/usr/bin/env python3
"""
Debug entity exploration query.
"""

import asyncio
import asyncpg
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_entity_exploration():
    # Database connection
    connection_string = (
        f"postgresql://nexus_memory_db_user:2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V@"
        f"dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com:5432/nexus_memory_db"
    )
    
    conn = await asyncpg.connect(connection_string)
    
    try:
        entity_name = "Von Base Enterprises"
        
        # First, check if entity exists
        entity = await conn.fetchrow(
            "SELECT id, entity_name FROM graph_nodes WHERE entity_name = $1",
            entity_name
        )
        
        if entity:
            logger.info(f"Found entity: {entity['entity_name']} with ID: {entity['id']}")
            
            # Check direct mappings
            mapping_count = await conn.fetchval("""
                SELECT COUNT(*) 
                FROM memory_entity_map 
                WHERE entity_id = $1
            """, entity['id'])
            logger.info(f"Direct mappings: {mapping_count}")
            
            # Check mappings with valid memories
            valid_mapping_count = await conn.fetchval("""
                SELECT COUNT(*) 
                FROM memory_entity_map mem
                JOIN vector_memories vm ON mem.memory_id = vm.id
                WHERE mem.entity_id = $1
            """, entity['id'])
            logger.info(f"Valid mappings (with existing memories): {valid_mapping_count}")
            
            # Try the actual query used by GraphProvider
            logger.info("\nTrying GraphProvider query pattern...")
            
            # This mimics the query in providers.py
            results = await conn.fetch("""
                WITH entity_memories AS (
                    SELECT DISTINCT mem.memory_id
                    FROM graph_nodes gn
                    JOIN memory_entity_map mem ON gn.id = mem.entity_id
                    WHERE gn.entity_name = $1
                )
                SELECT 
                    vm.id,
                    vm.content,
                    vm.metadata,
                    vm.importance_score,
                    vm.created_at
                FROM entity_memories em
                JOIN vector_memories vm ON em.memory_id = vm.id
                ORDER BY vm.importance_score DESC
                LIMIT 10
            """, entity_name)
            
            logger.info(f"GraphProvider query returned {len(results)} results")
            
            if results:
                logger.info("\nFirst few memories:")
                for i, result in enumerate(results[:3]):
                    logger.info(f"{i+1}. {result['content'][:100]}...")
            
            # Try a simpler direct query
            logger.info("\nTrying simple direct query...")
            simple_results = await conn.fetch("""
                SELECT vm.content
                FROM memory_entity_map mem
                JOIN vector_memories vm ON mem.memory_id = vm.id
                WHERE mem.entity_id = $1
                LIMIT 5
            """, entity['id'])
            
            logger.info(f"Simple query returned {len(simple_results)} results")
            
        else:
            logger.error(f"Entity '{entity_name}' not found!")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(debug_entity_exploration())