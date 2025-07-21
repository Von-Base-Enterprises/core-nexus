#!/usr/bin/env python3
"""
Robust GraphRAG migration script that handles various metadata formats.
"""

import asyncio
import asyncpg
import os
import logging
import json
from datetime import datetime
from uuid import UUID
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RobustGraphMigration:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.pool = None
        self.stats = {
            'memories_processed': 0,
            'entities_found': 0,
            'mappings_created': 0,
            'errors': 0,
            'skipped': 0
        }
    
    async def initialize(self):
        """Initialize database connection pool."""
        self.pool = await asyncpg.create_pool(
            self.connection_string,
            min_size=5,
            max_size=20,
            command_timeout=60
        )
        logger.info("Database connection pool initialized")
    
    async def extract_entities_simple(self, content: str) -> List[Dict[str, Any]]:
        """Simple entity extraction using regex patterns."""
        import re
        entities = []
        
        # Extract capitalized words/phrases as potential entities
        pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        
        seen = set()
        for match in re.finditer(pattern, content):
            entity_name = match.group()
            if entity_name not in seen and len(entity_name) > 2:
                seen.add(entity_name)
                
                # Guess entity type based on patterns
                entity_type = self.guess_entity_type(entity_name, content)
                
                entities.append({
                    'name': entity_name,
                    'type': entity_type,
                    'confidence': 0.6
                })
        
        return entities
    
    def guess_entity_type(self, entity_name: str, context: str) -> str:
        """Guess entity type based on name and context."""
        name_lower = entity_name.lower()
        context_lower = context.lower()
        
        # Common patterns
        if any(corp in name_lower for corp in ['enterprises', 'inc', 'corp', 'company', 'labs']):
            return 'organization'
        elif any(tech in name_lower for tech in ['api', 'sdk', 'gpt', 'ai', 'ml']):
            return 'technology'
        elif name_lower in ['core nexus', 'graphrag', 'vector store']:
            return 'technology'
        elif 'project' in context_lower and entity_name in context:
            return 'project'
        elif any(name_lower.endswith(suffix) for suffix in ['ment', 'tion', 'ity', 'ness']):
            return 'concept'
        elif len(entity_name.split()) == 2 and all(word[0].isupper() for word in entity_name.split()):
            # Two capitalized words might be a person's name
            return 'person'
        else:
            return 'other'
    
    def parse_metadata(self, metadata: Any) -> Dict[str, Any]:
        """Safely parse metadata from various formats."""
        if metadata is None:
            return {}
        
        if isinstance(metadata, dict):
            return metadata
        
        if isinstance(metadata, str):
            try:
                # Try to parse as JSON
                return json.loads(metadata)
            except:
                # If not JSON, return empty dict
                logger.debug(f"Could not parse metadata as JSON: {metadata[:50]}...")
                return {}
        
        # For any other type, return empty dict
        return {}
    
    async def migrate_memory(self, memory_id: UUID, content: str, metadata: Any, importance_score: Optional[float] = None):
        """Process a single memory and create entity mappings."""
        try:
            # Parse metadata safely
            parsed_metadata = self.parse_metadata(metadata)
            
            # Extract entities from content
            entities = await self.extract_entities_simple(content)
            
            if not entities:
                self.stats['skipped'] += 1
                return
            
            # Use importance score from memory or metadata
            if importance_score is None:
                importance_score = parsed_metadata.get('importance_score', 0.5)
            
            async with self.pool.acquire() as conn:
                for entity in entities:
                    try:
                        # Check if entity already exists (by name only due to unique constraint)
                        existing = await conn.fetchrow("""
                            SELECT id, mention_count FROM graph_nodes 
                            WHERE entity_name = $1
                        """, entity['name'])
                        
                        if existing:
                            entity_id = existing['id']
                            # Update mention count
                            await conn.execute("""
                                UPDATE graph_nodes 
                                SET mention_count = mention_count + 1
                                WHERE id = $1
                            """, entity_id)
                        else:
                            # Create new entity
                            entity_id = await conn.fetchval("""
                                INSERT INTO graph_nodes 
                                (entity_name, entity_type, importance_score, mention_count)
                                VALUES ($1, $2, $3, 1)
                                RETURNING id
                            """, entity['name'], entity['type'], importance_score)
                            
                            self.stats['entities_found'] += 1
                        
                        # Create memory-entity mapping
                        await conn.execute("""
                            INSERT INTO memory_entity_map (memory_id, entity_id)
                            VALUES ($1, $2)
                            ON CONFLICT DO NOTHING
                        """, memory_id, entity_id)
                        
                        self.stats['mappings_created'] += 1
                        
                    except Exception as e:
                        logger.debug(f"Error processing entity {entity['name']}: {e}")
            
            self.stats['memories_processed'] += 1
            
            if self.stats['memories_processed'] % 100 == 0:
                logger.info(f"Progress: {self.stats}")
                
        except Exception as e:
            logger.error(f"Error processing memory {memory_id}: {e}")
            self.stats['errors'] += 1
    
    async def run_migration(self, batch_size: int = 100):
        """Run the migration in batches."""
        logger.info("Starting robust GraphRAG migration...")
        
        async with self.pool.acquire() as conn:
            # Get total count
            total_count = await conn.fetchval("SELECT COUNT(*) FROM vector_memories")
            logger.info(f"Found {total_count} memories to process")
            
            # Process in batches
            offset = 0
            while offset < total_count:
                # Fetch batch of memories
                memories = await conn.fetch("""
                    SELECT id, content, metadata, importance_score
                    FROM vector_memories
                    ORDER BY created_at DESC
                    LIMIT $1 OFFSET $2
                """, batch_size, offset)
                
                # Process each memory
                for memory in memories:
                    await self.migrate_memory(
                        memory['id'],
                        memory['content'],
                        memory['metadata'],
                        memory['importance_score']
                    )
                
                offset += batch_size
                logger.info(f"Processed {min(offset, total_count)}/{total_count} memories")
        
        # Print final statistics
        logger.info("Migration completed!")
        logger.info(f"Final Statistics:")
        logger.info(f"  - Memories processed: {self.stats['memories_processed']}")
        logger.info(f"  - Memories skipped (no entities): {self.stats['skipped']}")
        logger.info(f"  - New entities found: {self.stats['entities_found']}")
        logger.info(f"  - Mappings created: {self.stats['mappings_created']}")
        logger.info(f"  - Errors: {self.stats['errors']}")
        
        # Calculate success rate
        total_attempted = self.stats['memories_processed'] + self.stats['errors']
        if total_attempted > 0:
            success_rate = (self.stats['memories_processed'] / total_attempted) * 100
            logger.info(f"  - Success rate: {success_rate:.1f}%")
    
    async def verify_migration(self):
        """Verify the migration results."""
        async with self.pool.acquire() as conn:
            # Check entity counts
            entity_count = await conn.fetchval("SELECT COUNT(*) FROM graph_nodes")
            mapping_count = await conn.fetchval("SELECT COUNT(*) FROM memory_entity_map")
            
            # Get top entities by mention count
            top_entities = await conn.fetch("""
                SELECT entity_name, entity_type, mention_count
                FROM graph_nodes
                ORDER BY mention_count DESC
                LIMIT 10
            """)
            
            # Get some sample mappings
            samples = await conn.fetch("""
                SELECT 
                    gn.entity_name,
                    gn.entity_type,
                    COUNT(mem.memory_id) as connected_memories
                FROM graph_nodes gn
                LEFT JOIN memory_entity_map mem ON gn.id = mem.entity_id
                GROUP BY gn.id, gn.entity_name, gn.entity_type
                ORDER BY connected_memories DESC
                LIMIT 10
            """)
            
            logger.info("\nVerification Results:")
            logger.info(f"Total entities: {entity_count}")
            logger.info(f"Total mappings: {mapping_count}")
            
            logger.info("\nTop entities by mentions:")
            for entity in top_entities:
                logger.info(f"  - {entity['entity_name']} ({entity['entity_type']}): {entity['mention_count']} mentions")
            
            logger.info("\nEntities with most connected memories:")
            for sample in samples:
                logger.info(f"  - {sample['entity_name']} ({sample['entity_type']}): {sample['connected_memories']} memories")
    
    async def close(self):
        """Close database connections."""
        if self.pool:
            await self.pool.close()


async def main():
    """Main migration function."""
    # Get database connection from environment
    db_host = os.getenv("PGVECTOR_HOST", "dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com")
    db_port = os.getenv("PGVECTOR_PORT", "5432")
    db_name = os.getenv("PGVECTOR_DATABASE", "nexus_memory_db")
    db_user = os.getenv("PGVECTOR_USER", "nexus_memory_db_user")
    db_password = os.getenv("PGVECTOR_PASSWORD", "2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V")
    
    connection_string = (
        f"postgresql://{db_user}:{db_password}@"
        f"{db_host}:{db_port}/{db_name}"
    )
    
    # Run migration
    migration = RobustGraphMigration(connection_string)
    
    try:
        await migration.initialize()
        await migration.run_migration()
        await migration.verify_migration()
    finally:
        await migration.close()


if __name__ == "__main__":
    asyncio.run(main())