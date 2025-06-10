#!/usr/bin/env python3
"""
Gemini Mega-Context Entity Extraction Pipeline
Leverages Gemini's 1 million token context window to process multiple memories at once
for more efficient and context-aware entity extraction.

Agent 2 Backend - Optimized for massive context processing
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Any
from uuid import uuid4

import asyncpg
import google.generativeai as genai
from asyncpg.pool import Pool

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("gemini_mega_context")

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyAIl8F81WwFfx5_62y19KuO12ermaDC6FQ")
genai.configure(api_key=GEMINI_API_KEY)

# Initialize Gemini 2.0 Flash model with 1M context
model = genai.GenerativeModel('gemini-1.5-flash-002')  # Using 1.5 Flash for 1M context window

# Mega-batch prompt template
MEGA_BATCH_EXTRACTION_PROMPT = """
You are an expert knowledge graph builder analyzing a large collection of memories from the Core Nexus system.

TASK: Extract ALL entities and relationships from ALL the memories below. Look for connections ACROSS memories, not just within individual memories.

IMPORTANT INSTRUCTIONS:
1. Identify ALL named entities across all memories (people, organizations, technologies, products, locations, concepts, events)
2. Find relationships BETWEEN memories - the same entity appearing in multiple memories
3. Infer implicit relationships based on temporal proximity and context
4. Rate entity importance globally (across all memories, not just within one)
5. Identify entity evolution - how entities change over time
6. Find patterns and themes across the memory collection

OUTPUT FORMAT:
Return a single JSON object with:
- entities: All unique entities found across all memories
- relationships: All relationships (including cross-memory connections)
- patterns: High-level patterns or themes discovered
- entity_memory_map: Which entities appear in which memories

MEMORIES TO ANALYZE:
{memories_json}

Analyze these memories holistically, finding connections and patterns across the entire collection.
"""

# Response schema for mega-batch processing
MEGA_BATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "type": {"type": "string"},
                    "importance": {"type": "number"},
                    "description": {"type": "string"},
                    "first_seen": {"type": "string"},
                    "last_seen": {"type": "string"},
                    "memory_count": {"type": "integer"}
                }
            }
        },
        "relationships": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "type": {"type": "string"},
                    "strength": {"type": "number"},
                    "context": {"type": "string"},
                    "memory_ids": {"type": "array", "items": {"type": "string"}}
                }
            }
        },
        "patterns": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "description": {"type": "string"},
                    "entity_ids": {"type": "array", "items": {"type": "string"}}
                }
            }
        },
        "entity_memory_map": {
            "type": "object"
        }
    }
}


class GeminiMegaContextExtractor:
    """Leverages Gemini's 1M token context for batch processing."""

    def __init__(self):
        self.db_pool: Pool | None = None
        self.model = model
        self.stats = {
            'batches_processed': 0,
            'memories_processed': 0,
            'entities_extracted': 0,
            'relationships_found': 0,
            'patterns_discovered': 0,
            'tokens_processed': 0,
            'api_calls': 0
        }

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

    def estimate_tokens(self, memories: list[dict[str, Any]]) -> int:
        """Estimate token count for a batch of memories."""
        # Rough estimation: 1 token ≈ 4 characters
        total_chars = sum(len(m['content']) + len(json.dumps(m['metadata'])) for m in memories)
        return total_chars // 4

    def create_optimal_batches(self, memories: list[dict[str, Any]], max_tokens: int = 800000) -> list[list[dict[str, Any]]]:
        """Create optimal batches that fit within token limits while maximizing context."""
        batches = []
        current_batch = []
        current_tokens = 0

        for memory in memories:
            memory_tokens = self.estimate_tokens([memory])

            if current_tokens + memory_tokens > max_tokens and current_batch:
                # Current batch is full, start a new one
                batches.append(current_batch)
                current_batch = [memory]
                current_tokens = memory_tokens
            else:
                # Add to current batch
                current_batch.append(memory)
                current_tokens += memory_tokens

        if current_batch:
            batches.append(current_batch)

        logger.info(f"📦 Created {len(batches)} optimal batches from {len(memories)} memories")
        for i, batch in enumerate(batches):
            batch_tokens = self.estimate_tokens(batch)
            logger.info(f"  Batch {i+1}: {len(batch)} memories, ~{batch_tokens:,} tokens")

        return batches

    async def process_mega_batch(self, memories: list[dict[str, Any]]) -> dict[str, Any]:
        """Process a large batch of memories in a single Gemini call."""
        logger.info(f"🚀 Processing mega-batch of {len(memories)} memories...")

        # Prepare memories for prompt
        memories_data = []
        for memory in memories:
            memories_data.append({
                'id': memory['id'],
                'content': memory['content'],
                'metadata': memory.get('metadata', {}),
                'created_at': memory.get('created_at'),
                'importance_score': memory.get('importance_score', 0.5)
            })

        # Create the prompt
        prompt = MEGA_BATCH_EXTRACTION_PROMPT.format(
            memories_json=json.dumps(memories_data, indent=2)
        )

        # Estimate tokens
        prompt_tokens = len(prompt) // 4
        logger.info(f"📊 Prompt size: ~{prompt_tokens:,} tokens")

        try:
            # Generate with structured output
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.2,  # Slightly higher for pattern recognition
                    top_p=0.9,
                    max_output_tokens=8192,  # Large output for comprehensive results
                    response_mime_type="application/json",
                    response_schema=MEGA_BATCH_SCHEMA
                )
            )

            self.stats['api_calls'] += 1
            self.stats['tokens_processed'] += prompt_tokens

            if response.text:
                result = json.loads(response.text)

                # Update stats
                self.stats['entities_extracted'] += len(result.get('entities', []))
                self.stats['relationships_found'] += len(result.get('relationships', []))
                self.stats['patterns_discovered'] += len(result.get('patterns', []))
                self.stats['memories_processed'] += len(memories)

                logger.info(f"✅ Extracted {len(result.get('entities', []))} entities")
                logger.info(f"✅ Found {len(result.get('relationships', []))} relationships")
                logger.info(f"✅ Discovered {len(result.get('patterns', []))} patterns")

                return result
            else:
                raise ValueError("Empty response from Gemini")

        except Exception as e:
            logger.error(f"❌ Mega-batch processing failed: {e}")
            raise

    async def insert_batch_results(self, extraction_results: dict[str, Any]):
        """Insert mega-batch extraction results into the database."""
        if not self.db_pool:
            await self.init_database_pool()

        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                try:
                    # Insert entities
                    entity_id_map = {}
                    for entity in extraction_results.get('entities', []):
                        entity_id = entity.get('id', str(uuid4()))
                        entity_id_map[entity['name']] = entity_id

                        await conn.execute("""
                            INSERT INTO graph_nodes (
                                id, entity_type, entity_name, properties,
                                importance_score, first_seen, last_seen, mention_count
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                            ON CONFLICT (id) DO UPDATE SET
                                importance_score = GREATEST(graph_nodes.importance_score, EXCLUDED.importance_score),
                                last_seen = EXCLUDED.last_seen,
                                mention_count = EXCLUDED.mention_count
                        """,
                            entity_id,
                            entity['type'],
                            entity['name'],
                            json.dumps({
                                'description': entity.get('description', ''),
                                'patterns': []  # Will be updated with pattern associations
                            }),
                            float(entity['importance']),
                            datetime.fromisoformat(entity.get('first_seen', datetime.now().isoformat())),
                            datetime.fromisoformat(entity.get('last_seen', datetime.now().isoformat())),
                            entity.get('memory_count', 1)
                        )

                    # Insert relationships with cross-memory context
                    for relationship in extraction_results.get('relationships', []):
                        source_id = entity_id_map.get(relationship['source'])
                        target_id = entity_id_map.get(relationship['target'])

                        if source_id and target_id:
                            await conn.execute("""
                                INSERT INTO graph_relationships (
                                    from_node_id, to_node_id, relationship_type,
                                    strength, confidence, metadata, occurrence_count
                                ) VALUES ($1, $2, $3, $4, $4, $5, $6)
                                ON CONFLICT (from_node_id, to_node_id, relationship_type)
                                DO UPDATE SET
                                    strength = GREATEST(graph_relationships.strength, EXCLUDED.strength),
                                    occurrence_count = graph_relationships.occurrence_count + EXCLUDED.occurrence_count,
                                    metadata = graph_relationships.metadata || EXCLUDED.metadata
                            """,
                                source_id,
                                target_id,
                                relationship['type'],
                                float(relationship['strength']),
                                json.dumps({
                                    'context': relationship.get('context', ''),
                                    'memory_ids': relationship.get('memory_ids', [])
                                }),
                                len(relationship.get('memory_ids', []))
                            )

                    # Create memory-entity mappings
                    entity_memory_map = extraction_results.get('entity_memory_map', {})
                    for entity_name, memory_ids in entity_memory_map.items():
                        entity_id = entity_id_map.get(entity_name)
                        if entity_id:
                            for memory_id in memory_ids:
                                await conn.execute("""
                                    INSERT INTO memory_entity_map (
                                        memory_id, entity_id, confidence
                                    ) VALUES ($1, $2, 0.9)
                                    ON CONFLICT DO NOTHING
                                """, memory_id, entity_id)

                    # Store discovered patterns as metadata
                    for pattern in extraction_results.get('patterns', []):
                        logger.info(f"🔍 Pattern discovered: {pattern['pattern']}")
                        # Could store patterns in a separate table or as graph metadata

                    logger.info("✅ Batch results inserted successfully")

                except Exception as e:
                    logger.error(f"❌ Database insertion failed: {e}")
                    raise

    async def fetch_all_memories(self) -> list[dict[str, Any]]:
        """Fetch all memories from the database."""
        if not self.db_pool:
            await self.init_database_pool()

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, content, metadata,
                       metadata->>'user_id' as user_id,
                       metadata->>'conversation_id' as conversation_id,
                       COALESCE((metadata->>'importance_score')::float, 0.5) as importance_score,
                       created_at
                FROM vector_memories
                ORDER BY created_at DESC
            """)

            memories = []
            for row in rows:
                memories.append({
                    'id': str(row['id']),
                    'content': row['content'],
                    'metadata': row['metadata'] if isinstance(row['metadata'], dict) else {},
                    'user_id': row['user_id'] or 'unknown',
                    'conversation_id': row['conversation_id'] or 'unknown',
                    'importance_score': float(row['importance_score']) if row['importance_score'] else 0.5,
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None
                })

            logger.info(f"📊 Fetched {len(memories)} memories from database")
            return memories

    async def run_mega_context_extraction(self):
        """Run the mega-context extraction pipeline."""
        logger.info("🚀 Starting Gemini Mega-Context Entity Extraction Pipeline")
        logger.info("🧠 Leveraging 1 million token context window for holistic analysis")
        start_time = time.time()

        try:
            # Initialize database
            await self.init_database_pool()

            # Fetch all memories
            memories = await self.fetch_all_memories()

            if not memories:
                logger.warning("⚠️ No memories found to process")
                return

            # Create optimal batches
            batches = self.create_optimal_batches(memories, max_tokens=800000)

            # Process each batch
            for i, batch in enumerate(batches):
                logger.info(f"\n{'='*60}")
                logger.info(f"Processing batch {i+1}/{len(batches)}")
                logger.info(f"{'='*60}")

                # Extract entities and relationships
                extraction_results = await self.process_mega_batch(batch)

                # Insert results
                await self.insert_batch_results(extraction_results)

                self.stats['batches_processed'] += 1

                # Brief pause between batches
                if i < len(batches) - 1:
                    await asyncio.sleep(2)

            # Final statistics
            duration = time.time() - start_time

            logger.info("\n🎉 Mega-Context Extraction Complete!")
            logger.info(f"⏱️ Duration: {duration:.2f} seconds")
            logger.info(f"📦 Batches processed: {self.stats['batches_processed']}")
            logger.info(f"📄 Memories analyzed: {self.stats['memories_processed']}")
            logger.info(f"🔍 Entities extracted: {self.stats['entities_extracted']}")
            logger.info(f"🔗 Relationships found: {self.stats['relationships_found']}")
            logger.info(f"🎯 Patterns discovered: {self.stats['patterns_discovered']}")
            logger.info(f"🪙 Tokens processed: {self.stats['tokens_processed']:,}")
            logger.info(f"📞 API calls made: {self.stats['api_calls']}")
            logger.info(f"💰 Estimated cost: ${self.stats['api_calls'] * 0.21 / 1000:.4f}")

            # Save report
            report = {
                'timestamp': datetime.now().isoformat(),
                'duration_seconds': duration,
                'stats': self.stats,
                'efficiency': {
                    'memories_per_api_call': self.stats['memories_processed'] / max(1, self.stats['api_calls']),
                    'tokens_per_memory': self.stats['tokens_processed'] / max(1, self.stats['memories_processed']),
                    'cost_per_memory': (self.stats['api_calls'] * 0.21 / 1000) / max(1, self.stats['memories_processed'])
                }
            }

            with open('gemini_mega_context_report.json', 'w') as f:
                json.dump(report, f, indent=2)

            logger.info("📋 Report saved to gemini_mega_context_report.json")

        except Exception as e:
            logger.error(f"❌ Pipeline failed: {e}")
            raise

        finally:
            if self.db_pool:
                await self.db_pool.close()


async def main():
    """Main entry point."""
    print("=" * 80)
    print("🚀 GEMINI MEGA-CONTEXT ENTITY EXTRACTION PIPELINE")
    print("🧠 Leveraging 1 million token context window")
    print("📊 Processing all 1,005 memories with holistic analysis")
    print("=" * 80)

    # Check environment
    if not os.getenv("PGVECTOR_PASSWORD"):
        logger.error("❌ PGVECTOR_PASSWORD environment variable required")
        return 1

    # Run the pipeline
    extractor = GeminiMegaContextExtractor()

    try:
        await extractor.run_mega_context_extraction()
        return 0
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
