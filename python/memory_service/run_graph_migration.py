#!/usr/bin/env python3
"""
Script to run the graph entity migration and populate memory_entity_map table.
This will enable GraphRAG functionality by linking memories to entities.
"""

import asyncio
import os
import sys
from datetime import datetime

# Ensure we can import the migration module
sys.path.insert(0, os.path.dirname(__file__))

from migrate_graph_entities import GraphMigration


async def main():
    """Run the graph migration to populate memory_entity_map."""
    
    print("=" * 80)
    print("GraphRAG Migration Runner")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 80)
    
    # Check environment variables
    required_vars = ['PGVECTOR_HOST', 'PGVECTOR_DATABASE', 'PGVECTOR_USER', 'PGVECTOR_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("\n❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these variables before running migration.")
        print("\nExample:")
        print("export PGVECTOR_HOST=dpg-d12n0np5pdvs73ctmm40-a")
        print("export PGVECTOR_DATABASE=nexus_memory_db")
        print("export PGVECTOR_USER=nexus_memory_db_user")
        print("export PGVECTOR_PASSWORD=<your-password>")
        return 1
    
    # Build connection string
    connection_string = (
        f"postgresql://{os.getenv('PGVECTOR_USER')}:"
        f"{os.getenv('PGVECTOR_PASSWORD')}@"
        f"{os.getenv('PGVECTOR_HOST')}:"
        f"{os.getenv('PGVECTOR_PORT', '5432')}/"
        f"{os.getenv('PGVECTOR_DATABASE')}"
    )
    
    print("\n📊 Database Configuration:")
    print(f"   Host: {os.getenv('PGVECTOR_HOST')}")
    print(f"   Database: {os.getenv('PGVECTOR_DATABASE')}")
    print(f"   User: {os.getenv('PGVECTOR_USER')}")
    print()
    
    # Create migration instance
    migration = GraphMigration(connection_string)
    
    try:
        # Initialize connection
        print("🔄 Initializing database connection...")
        await migration.initialize()
        
        # Check current state
        print("\n📈 Checking current graph state...")
        async with migration.pool.acquire() as conn:
            # Count entities
            entity_count = await conn.fetchval("SELECT COUNT(*) FROM graph_nodes")
            print(f"   Entities in graph: {entity_count}")
            
            # Count relationships
            rel_count = await conn.fetchval("SELECT COUNT(*) FROM graph_relationships")
            print(f"   Relationships: {rel_count}")
            
            # Count memory-entity mappings
            map_count = await conn.fetchval("SELECT COUNT(*) FROM memory_entity_map")
            print(f"   Memory-entity mappings: {map_count}")
            
            # Count total memories
            memory_count = await conn.fetchval("SELECT COUNT(*) FROM vector_memories")
            print(f"   Total memories: {memory_count}")
        
        if map_count > 0:
            print(f"\n⚠️  Warning: {map_count} mappings already exist.")
            response = input("Continue and add more mappings? (y/N): ")
            if response.lower() != 'y':
                print("Migration cancelled.")
                return 0
        
        # Run migration
        print("\n🚀 Starting migration...")
        print("   This will extract entities from all memories and create mappings.")
        print("   Progress will be shown below...\n")
        
        await migration.run_migration()
        
        # Show results
        print("\n✅ Migration completed!")
        print(f"\n📊 Results:")
        print(f"   Memories processed: {migration.stats['memories_processed']}")
        print(f"   Entities found: {migration.stats['entities_found']}")
        print(f"   Mappings created: {migration.stats['mappings_created']}")
        print(f"   Errors: {migration.stats['errors']}")
        
        # Verify results
        async with migration.pool.acquire() as conn:
            new_map_count = await conn.fetchval("SELECT COUNT(*) FROM memory_entity_map")
            print(f"\n🔍 Verification:")
            print(f"   Total memory-entity mappings: {new_map_count}")
            
            # Show sample mappings
            sample_mappings = await conn.fetch("""
                SELECT m.content, n.entity_name, n.entity_type, map.confidence
                FROM memory_entity_map map
                JOIN vector_memories m ON map.memory_id = m.id
                JOIN graph_nodes n ON map.entity_id = n.id
                ORDER BY map.confidence DESC
                LIMIT 5
            """)
            
            if sample_mappings:
                print(f"\n📝 Sample mappings:")
                for mapping in sample_mappings:
                    content_preview = mapping['content'][:60] + "..." if len(mapping['content']) > 60 else mapping['content']
                    print(f"   - '{mapping['entity_name']}' ({mapping['entity_type']}) -> \"{content_preview}\"")
        
        print("\n🎉 GraphRAG is now ready to use!")
        print("   - Queries will now extract entities")
        print("   - Graph will be consulted for enhanced search")
        print("   - Evidence chains will be generated")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        return 1
        
    finally:
        if migration.pool:
            await migration.pool.close()
    
    print("\n" + "=" * 80)
    print(f"Completed: {datetime.now().isoformat()}")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)