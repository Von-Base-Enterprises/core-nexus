#!/usr/bin/env python3
"""
Direct migration to create memory-entity mappings for Von Base Enterprises and Core Nexus.
"""

import asyncio
import asyncpg
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def direct_migration():
    # Database connection
    connection_string = (
        f"postgresql://nexus_memory_db_user:2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V@"
        f"dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com:5432/nexus_memory_db"
    )
    
    conn = await asyncpg.connect(connection_string)
    
    try:
        # First, check key entities
        logger.info("Checking key entities...")
        
        key_entities = ["Von Base Enterprises", "Core Nexus", "GraphRAG"]
        entity_ids = {}
        
        for entity_name in key_entities:
            result = await conn.fetchrow(
                "SELECT id, mention_count FROM graph_nodes WHERE entity_name = $1",
                entity_name
            )
            if result:
                entity_ids[entity_name] = result['id']
                logger.info(f"Found {entity_name}: ID={result['id']}, mentions={result['mention_count']}")
            else:
                logger.warning(f"{entity_name} not found in graph_nodes")
        
        # Now find memories containing these entities
        logger.info("\nSearching for memories containing key entities...")
        
        for entity_name, entity_id in entity_ids.items():
            # Find memories containing this entity
            memories = await conn.fetch("""
                SELECT id, content 
                FROM vector_memories 
                WHERE content ILIKE $1
                LIMIT 50
            """, f'%{entity_name}%')
            
            logger.info(f"\nFound {len(memories)} memories containing '{entity_name}'")
            
            # Create mappings
            created = 0
            for memory in memories:
                try:
                    await conn.execute("""
                        INSERT INTO memory_entity_map (memory_id, entity_id)
                        VALUES ($1, $2)
                        ON CONFLICT DO NOTHING
                    """, memory['id'], entity_id)
                    created += 1
                except Exception as e:
                    logger.error(f"Error creating mapping: {e}")
            
            logger.info(f"Created {created} mappings for {entity_name}")
        
        # Check final statistics
        logger.info("\n=== Final Statistics ===")
        
        # Total mappings
        total_mappings = await conn.fetchval("SELECT COUNT(*) FROM memory_entity_map")
        logger.info(f"Total memory-entity mappings: {total_mappings}")
        
        # Check specific entities
        for entity_name, entity_id in entity_ids.items():
            count = await conn.fetchval("""
                SELECT COUNT(*) 
                FROM memory_entity_map 
                WHERE entity_id = $1
            """, entity_id)
            logger.info(f"{entity_name} connected memories: {count}")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(direct_migration())