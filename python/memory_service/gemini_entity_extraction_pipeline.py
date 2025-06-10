#!/usr/bin/env python3
"""
Gemini-Powered Entity Extraction Pipeline
Uses Google's Gemini 2.0 Flash for state-of-the-art entity extraction
and knowledge graph population from Core Nexus memories.

Agent 2 Backend - Cutting-edge AI approach
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Any
from uuid import uuid4

import asyncpg
import google.generativeai as genai
from asyncpg.pool import Pool

# Add the source directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from memory_service.logging_config import get_logger, setup_logging

# Setup logging
setup_logging()
logger = get_logger("gemini_extraction")

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyAIl8F81WwFfx5_62y19KuO12ermaDC6FQ")
genai.configure(api_key=GEMINI_API_KEY)

# Initialize Gemini 2.0 Flash model
model = genai.GenerativeModel('gemini-2.0-flash-exp')

# Response schema for structured output
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string", "enum": ["PERSON", "ORGANIZATION", "TECHNOLOGY", "PRODUCT", "LOCATION", "CONCEPT", "EVENT"]},
                    "importance": {"type": "number"},
                    "description": {"type": "string"}
                },
                "required": ["name", "type", "importance"]
            }
        },
        "relationships": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "type": {"type": "string", "enum": ["WORKS_AT", "USES", "PARTNERS_WITH", "LOCATED_IN", "DEVELOPS", "FOUNDED", "MENTIONS", "RELATES_TO", "MANAGES", "CREATED"]},
                    "strength": {"type": "number"},
                    "context": {"type": "string"}
                },
                "required": ["source", "target", "type", "strength"]
            }
        }
    },
    "required": ["entities", "relationships"]
}

# Entity extraction prompt template
ENTITY_EXTRACTION_PROMPT = """
You are an expert knowledge graph builder. Extract all entities and relationships from this text.

IMPORTANT INSTRUCTIONS:
1. Identify ALL named entities (people, organizations, technologies, products, locations, concepts, events)
2. For each entity, assess its importance (0.0-1.0) based on how central it is to the content
3. Find ALL relationships between entities, including implicit ones
4. Rate relationship strength (0.0-1.0) based on how strong/direct the connection is
5. Be comprehensive - extract even minor entities and relationships

Text to analyze:
{memory_content}

Additional context:
- Memory ID: {memory_id}
- Created: {created_at}
- User: {user_id}
- Importance Score: {importance_score}

Return as JSON with the exact structure specified.
"""

# Generation configuration for optimal results
GENERATION_CONFIG = {
    "temperature": 0.1,      # Low for consistency
    "top_p": 0.8,           # Focused results
    "top_k": 40,            # Standard
    "max_output_tokens": 2048,  # Enough for complex entities
    "response_mime_type": "application/json"
}


class GeminiEntityExtractor:
    """Manages entity extraction using Gemini API."""

    def __init__(self, db_pool: Pool | None = None):
        self.db_pool = db_pool
        self.model = model
        self.stats = {
            'memories_processed': 0,
            'entities_extracted': 0,
            'relationships_found': 0,
            'errors': []
        }
        self.entity_cache = {}  # Cache for entity deduplication

    async def init_database_pool(self):
        """Initialize database connection pool."""
        if not self.db_pool:
            connection_string = (
                f"postgresql://{os.getenv('PGVECTOR_USER', 'nexus_memory_db_user')}:"
                f"{os.getenv('PGVECTOR_PASSWORD')}@"
                f"{os.getenv('PGVECTOR_HOST', 'dpg-d12n0np5pdvs73ctmm40-a')}:"
                f"{os.getenv('PGVECTOR_PORT', '5432')}/"
                f"{os.getenv('PGVECTOR_DATABASE', 'nexus_memory_db')}"
            )
            self.db_pool = await asyncpg.create_pool(
                connection_string,
                min_size=5,
                max_size=20
            )
            logger.info("✅ Database connection pool initialized")

    async def extract_entities_from_memory(self, memory: dict[str, Any]) -> dict[str, Any]:
        """Extract entities and relationships from a single memory using Gemini."""
        try:
            # Prepare the prompt with memory context
            prompt = ENTITY_EXTRACTION_PROMPT.format(
                memory_content=memory['content'],
                memory_id=memory['id'],
                created_at=memory.get('created_at', 'Unknown'),
                user_id=memory.get('user_id', 'Unknown'),
                importance_score=memory.get('importance_score', 0.5)
            )

            # Generate response with structured output
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=GENERATION_CONFIG['temperature'],
                    top_p=GENERATION_CONFIG['top_p'],
                    top_k=GENERATION_CONFIG['top_k'],
                    max_output_tokens=GENERATION_CONFIG['max_output_tokens'],
                    response_mime_type=GENERATION_CONFIG['response_mime_type'],
                    response_schema=RESPONSE_SCHEMA
                )
            )

            # Parse the JSON response
            if response.text:
                extracted_data = json.loads(response.text)

                # Add memory context to extracted data
                extracted_data['memory_id'] = memory['id']
                extracted_data['extraction_timestamp'] = datetime.now().isoformat()

                # Update stats
                self.stats['entities_extracted'] += len(extracted_data.get('entities', []))
                self.stats['relationships_found'] += len(extracted_data.get('relationships', []))

                logger.info(
                    f"✅ Extracted {len(extracted_data.get('entities', []))} entities "
                    f"and {len(extracted_data.get('relationships', []))} relationships "
                    f"from memory {memory['id']}"
                )

                return extracted_data
            else:
                raise ValueError("Empty response from Gemini")

        except Exception as e:
            error_msg = f"Failed to extract from memory {memory['id']}: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.stats['errors'].append(error_msg)
            return {'entities': [], 'relationships': [], 'error': str(e)}

    async def deduplicate_entity(self, entity: dict[str, Any]) -> tuple[str, bool]:
        """Deduplicate entities based on name and type."""
        # Create a cache key
        cache_key = f"{entity['type']}:{entity['name'].lower()}"

        if cache_key in self.entity_cache:
            # Entity exists, return existing ID
            return self.entity_cache[cache_key], False
        else:
            # New entity, generate ID and cache it
            entity_id = str(uuid4())
            self.entity_cache[cache_key] = entity_id
            return entity_id, True

    async def insert_entities_and_relationships(self, extraction_data: dict[str, Any], memory_id: str):
        """Insert extracted entities and relationships into the database."""
        if not self.db_pool:
            await self.init_database_pool()

        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                try:
                    # Process entities
                    entity_mapping = {}  # Map entity names to IDs

                    for entity in extraction_data.get('entities', []):
                        entity_id, is_new = await self.deduplicate_entity(entity)
                        entity_mapping[entity['name']] = entity_id

                        if is_new:
                            # Insert new entity into graph_nodes
                            await conn.execute("""
                                INSERT INTO graph_nodes (
                                    id, entity_type, entity_name, properties,
                                    importance_score, first_seen, last_seen, mention_count
                                ) VALUES ($1, $2, $3, $4, $5, $6, $6, 1)
                                ON CONFLICT (id) DO UPDATE SET
                                    last_seen = EXCLUDED.last_seen,
                                    mention_count = graph_nodes.mention_count + 1,
                                    importance_score = GREATEST(graph_nodes.importance_score, EXCLUDED.importance_score)
                            """,
                                entity_id,
                                entity['type'],
                                entity['name'],
                                json.dumps({'description': entity.get('description', '')}),
                                float(entity['importance']),
                                datetime.now()
                            )
                        else:
                            # Update existing entity
                            await conn.execute("""
                                UPDATE graph_nodes
                                SET last_seen = $1,
                                    mention_count = mention_count + 1,
                                    importance_score = GREATEST(importance_score, $2)
                                WHERE id = $3
                            """, datetime.now(), float(entity['importance']), entity_id)

                        # Create memory-entity mapping
                        await conn.execute("""
                            INSERT INTO memory_entity_map (
                                memory_id, entity_id, confidence
                            ) VALUES ($1, $2, $3)
                            ON CONFLICT DO NOTHING
                        """, memory_id, entity_id, float(entity['importance']))

                    # Process relationships
                    for relationship in extraction_data.get('relationships', []):
                        source_id = entity_mapping.get(relationship['source'])
                        target_id = entity_mapping.get(relationship['target'])

                        if source_id and target_id:
                            # Insert or update relationship
                            await conn.execute("""
                                INSERT INTO graph_relationships (
                                    from_node_id, to_node_id, relationship_type,
                                    strength, confidence, metadata, first_seen, last_seen
                                ) VALUES ($1, $2, $3, $4, $4, $5, $6, $6)
                                ON CONFLICT (from_node_id, to_node_id, relationship_type)
                                DO UPDATE SET
                                    strength = GREATEST(graph_relationships.strength, EXCLUDED.strength),
                                    last_seen = EXCLUDED.last_seen,
                                    occurrence_count = graph_relationships.occurrence_count + 1
                            """,
                                source_id,
                                target_id,
                                relationship['type'],
                                float(relationship['strength']),
                                json.dumps({'context': relationship.get('context', '')}),
                                datetime.now()
                            )

                    logger.info(f"✅ Inserted {len(entity_mapping)} entities and relationships for memory {memory_id}")

                except Exception as e:
                    logger.error(f"❌ Database insertion failed for memory {memory_id}: {e}")
                    raise

    async def process_memory_batch(self, memories: list[dict[str, Any]], batch_size: int = 10):
        """Process a batch of memories concurrently."""
        logger.info(f"🔄 Processing batch of {len(memories)} memories...")

        for i in range(0, len(memories), batch_size):
            batch = memories[i:i+batch_size]

            # Process batch concurrently
            extraction_tasks = []
            for memory in batch:
                task = self.extract_entities_from_memory(memory)
                extraction_tasks.append(task)

            # Wait for all extractions to complete
            extraction_results = await asyncio.gather(*extraction_tasks, return_exceptions=True)

            # Insert results into database
            for memory, result in zip(batch, extraction_results, strict=False):
                if isinstance(result, Exception):
                    logger.error(f"❌ Extraction failed for memory {memory['id']}: {result}")
                    continue

                if 'error' not in result:
                    await self.insert_entities_and_relationships(result, memory['id'])
                    self.stats['memories_processed'] += 1

            # Progress report
            progress = min(i + batch_size, len(memories)) / len(memories) * 100
            logger.info(
                f"📈 Progress: {progress:.1f}% "
                f"({self.stats['memories_processed']}/{len(memories)} processed)"
            )

            # Rate limiting to avoid API quotas
            await asyncio.sleep(1)

    async def fetch_all_memories(self) -> list[dict[str, Any]]:
        """Fetch all memories from the database."""
        if not self.db_pool:
            await self.init_database_pool()

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, content, metadata, user_id, conversation_id,
                       importance_score, created_at
                FROM vector_memories
                ORDER BY importance_score DESC, created_at DESC
            """)

            memories = []
            for row in rows:
                memories.append({
                    'id': str(row['id']),
                    'content': row['content'],
                    'metadata': dict(row['metadata']) if row['metadata'] else {},
                    'user_id': row['user_id'],
                    'conversation_id': row['conversation_id'],
                    'importance_score': float(row['importance_score']) if row['importance_score'] else 0.5,
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None
                })

            logger.info(f"📊 Fetched {len(memories)} memories from database")
            return memories

    async def run_full_extraction(self):
        """Run the complete entity extraction pipeline on all memories."""
        logger.info("🚀 Starting Gemini-powered entity extraction pipeline...")
        start_time = time.time()

        try:
            # Initialize database
            await self.init_database_pool()

            # Fetch all memories
            memories = await self.fetch_all_memories()

            if not memories:
                logger.warning("⚠️ No memories found to process")
                return

            logger.info(f"🎯 Processing {len(memories)} memories for entity extraction")

            # Process memories in batches
            await self.process_memory_batch(memories, batch_size=10)

            # Calculate final statistics
            duration = time.time() - start_time

            logger.info("🎉 Entity extraction pipeline completed!")
            logger.info(f"⏱️ Duration: {duration:.2f} seconds")
            logger.info(f"📊 Memories processed: {self.stats['memories_processed']}")
            logger.info(f"🔍 Entities extracted: {self.stats['entities_extracted']}")
            logger.info(f"🔗 Relationships found: {self.stats['relationships_found']}")
            logger.info(f"❌ Errors: {len(self.stats['errors'])}")

            # Save detailed report
            report = {
                'timestamp': datetime.now().isoformat(),
                'duration_seconds': duration,
                'stats': self.stats,
                'cost_estimate': {
                    'api_calls': self.stats['memories_processed'],
                    'cost_per_1000': 0.21,
                    'total_cost': self.stats['memories_processed'] * 0.21 / 1000
                }
            }

            with open('gemini_extraction_report.json', 'w') as f:
                json.dump(report, f, indent=2)

            logger.info("📋 Detailed report saved to gemini_extraction_report.json")

        except Exception as e:
            logger.error(f"❌ Pipeline failed: {e}")
            raise

        finally:
            if self.db_pool:
                await self.db_pool.close()


# Real-time extraction hook for new memories
async def extract_entities_for_new_memory(memory_data: dict[str, Any]):
    """Hook into memory creation for real-time entity extraction."""
    extractor = GeminiEntityExtractor()

    try:
        # Extract entities
        extraction_result = await extractor.extract_entities_from_memory(memory_data)

        if 'error' not in extraction_result:
            # Insert into graph
            await extractor.insert_entities_and_relationships(
                extraction_result,
                memory_data['id']
            )

            logger.info(f"✅ Real-time extraction complete for memory {memory_data['id']}")

    except Exception as e:
        logger.error(f"❌ Real-time extraction failed: {e}")

    finally:
        if extractor.db_pool:
            await extractor.db_pool.close()


async def main():
    """Main entry point for the Gemini entity extraction pipeline."""
    print("=" * 70)
    print("🚀 GEMINI-POWERED ENTITY EXTRACTION PIPELINE")
    print("Agent 2 Backend: Transforming memories into knowledge")
    print("Model: Gemini 2.0 Flash (gemini-2.0-flash-exp)")
    print("=" * 70)

    # Check environment
    if not os.getenv("PGVECTOR_PASSWORD"):
        logger.error("❌ PGVECTOR_PASSWORD environment variable required")
        return 1

    # Run the extraction pipeline
    extractor = GeminiEntityExtractor()

    try:
        await extractor.run_full_extraction()

        print("\n✅ Knowledge graph population complete!")
        print(f"🔍 Total entities: {extractor.stats['entities_extracted']}")
        print(f"🔗 Total relationships: {extractor.stats['relationships_found']}")
        print(f"💰 Estimated cost: ${extractor.stats['memories_processed'] * 0.21 / 1000:.2f}")

        return 0

    except Exception as e:
        logger.error(f"❌ Pipeline error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
