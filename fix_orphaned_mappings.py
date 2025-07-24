#!/usr/bin/env python3
"""
Fix orphaned memory-entity mappings.
"""

import asyncio
import asyncpg
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_orphaned_mappings():
    # Database connection
    connection_string = (
        f"postgresql://nexus_memory_db_user:2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V@"
        f"dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com:5432/nexus_memory_db"
    )
    
    conn = await asyncpg.connect(connection_string)
    
    try:
        # Check for orphaned mappings
        logger.info("Checking for orphaned memory-entity mappings...")
        
        orphaned_count = await conn.fetchval("""
            SELECT COUNT(*) 
            FROM memory_entity_map mem
            WHERE NOT EXISTS (
                SELECT 1 FROM vector_memories vm WHERE vm.id = mem.memory_id
            )
        """)
        
        logger.info(f"Found {orphaned_count} orphaned mappings")
        
        if orphaned_count > 0:
            # Delete orphaned mappings
            deleted = await conn.execute("""
                DELETE FROM memory_entity_map 
                WHERE memory_id NOT IN (SELECT id FROM vector_memories)
            """)
            logger.info(f"Deleted orphaned mappings: {deleted}")
        
        # Check valid mappings for key entities
        logger.info("\nChecking valid mappings for key entities...")
        
        key_entities = ["Von Base Enterprises", "Core Nexus"]
        
        for entity_name in key_entities:
            result = await conn.fetchrow("""
                SELECT 
                    gn.id,
                    gn.entity_name,
                    COUNT(DISTINCT mem.memory_id) as valid_memories
                FROM graph_nodes gn
                LEFT JOIN memory_entity_map mem ON gn.id = mem.entity_id
                LEFT JOIN vector_memories vm ON mem.memory_id = vm.id
                WHERE gn.entity_name = $1
                AND vm.id IS NOT NULL
                GROUP BY gn.id, gn.entity_name
            """, entity_name)
            
            if result:
                logger.info(f"{entity_name}: {result['valid_memories']} valid memory connections")
            else:
                logger.info(f"{entity_name}: Not found or no valid connections")
        
        # Now re-create mappings with valid memories only
        logger.info("\nRe-creating mappings for memories that actually exist...")
        
        for entity_name in key_entities:
            # Get entity ID
            entity_result = await conn.fetchrow(
                "SELECT id FROM graph_nodes WHERE entity_name = $1",
                entity_name
            )
            
            if entity_result:
                entity_id = entity_result['id']
                
                # Find and map valid memories
                memories = await conn.fetch("""
                    SELECT id 
                    FROM vector_memories 
                    WHERE content ILIKE $1
                    LIMIT 100
                """, f'%{entity_name}%')
                
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
                        pass
                
                logger.info(f"Created {created} valid mappings for {entity_name}")
        
        # Final check
        logger.info("\n=== Final Statistics ===")
        
        total_mappings = await conn.fetchval("""
            SELECT COUNT(*) 
            FROM memory_entity_map mem
            WHERE EXISTS (
                SELECT 1 FROM vector_memories vm WHERE vm.id = mem.memory_id
            )
        """)
        logger.info(f"Total valid memory-entity mappings: {total_mappings}")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_orphaned_mappings())