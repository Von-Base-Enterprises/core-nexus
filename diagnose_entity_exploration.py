#!/usr/bin/env python3
"""
Diagnose why entity exploration returns 0 memories.
"""

import asyncio
import os
import asyncpg
from datetime import datetime

async def diagnose():
    # Get database URL from environment
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("ERROR: DATABASE_URL environment variable not set")
        return
    
    conn = await asyncpg.connect(db_url)
    
    try:
        print(f"Diagnosis started at {datetime.now()}")
        print("=" * 80)
        
        # 1. Check memory_entity_map table
        count = await conn.fetchval("SELECT COUNT(*) FROM memory_entity_map")
        print(f"Total memory-entity mappings: {count}")
        
        # 2. Check for orphaned mappings
        orphaned = await conn.fetchval("""
            SELECT COUNT(*) 
            FROM memory_entity_map mem 
            LEFT JOIN vector_memories vm ON mem.memory_id = vm.id 
            WHERE vm.id IS NULL
        """)
        print(f"Orphaned mappings (memory doesn't exist): {orphaned}")
        
        # 3. Check a specific entity
        entity_name = 'AI'  # Example entity
        print(f"\nChecking entity '{entity_name}':")
        
        # Check if entity exists
        entity = await conn.fetchrow("""
            SELECT id, entity_type, mention_count, importance_score 
            FROM graph_nodes 
            WHERE entity_name = $1
        """, entity_name)
        
        if entity:
            print(f"  Entity found: ID={entity['id']}, type={entity['entity_type']}, mentions={entity['mention_count']}")
            
            # Check mappings for this entity
            mappings = await conn.fetch("""
                SELECT mem.*, vm.id as vm_exists
                FROM memory_entity_map mem
                LEFT JOIN vector_memories vm ON mem.memory_id = vm.id
                WHERE mem.entity_id = $1
                LIMIT 5
            """, entity['id'])
            
            print(f"  Mappings found: {len(mappings)}")
            for m in mappings:
                print(f"    Memory ID: {m['memory_id']}, Exists: {'Yes' if m['vm_exists'] else 'NO!'}")
        else:
            print(f"  Entity '{entity_name}' NOT FOUND")
        
        # 4. Test the actual query used by GraphProvider
        print(f"\nTesting GraphProvider query for entity '{entity_name}':")
        
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
            LIMIT 5
        """, entity_name)
        
        print(f"  Query returned {len(rows)} memories")
        
        if len(rows) == 0:
            # Debug: Check what entity_memories CTE returns
            print("\n  Debugging CTE:")
            cte_rows = await conn.fetch("""
                SELECT DISTINCT mem.memory_id, gr.strength as relationship_strength
                FROM graph_nodes gn
                JOIN memory_entity_map mem ON gn.id = mem.entity_id
                LEFT JOIN graph_relationships gr ON (gn.id = gr.from_node_id OR gn.id = gr.to_node_id)
                WHERE gn.entity_name = $1
                LIMIT 5
            """, entity_name)
            print(f"  CTE returns {len(cte_rows)} memory IDs")
            for row in cte_rows:
                print(f"    Memory ID: {row['memory_id']}")
                
                # Check if this memory exists
                exists = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM vector_memories WHERE id = $1)",
                    row['memory_id']
                )
                print(f"      Exists in vector_memories: {exists}")
        
        # 5. List all entities with their memory counts
        print("\nTop entities by memory count:")
        entities = await conn.fetch("""
            SELECT gn.entity_name, gn.entity_type, COUNT(DISTINCT mem.memory_id) as memory_count
            FROM graph_nodes gn
            JOIN memory_entity_map mem ON gn.id = mem.entity_id
            JOIN vector_memories vm ON mem.memory_id = vm.id
            GROUP BY gn.entity_name, gn.entity_type
            ORDER BY memory_count DESC
            LIMIT 10
        """)
        
        for e in entities:
            print(f"  {e['entity_name']} ({e['entity_type']}): {e['memory_count']} memories")
        
        print("\n" + "=" * 80)
        print("Diagnosis complete")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(diagnose())