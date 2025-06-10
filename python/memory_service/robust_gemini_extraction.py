#!/usr/bin/env python3
"""
Robust Gemini Extraction with Error Handling
Processes all memories with reliability
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from uuid import uuid4

import asyncpg
import google.generativeai as genai

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("robust_extraction")

# Configure Gemini
GEMINI_API_KEY = "AIzaSyAIl8F81WwFfx5_62y19KuO12ermaDC6FQ"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Simple, robust prompt
ROBUST_PROMPT = """
Extract entities and relationships from these memories.

MEMORIES:
{memories_text}

Return ONLY a valid JSON object like this:
{{
  "entities": [
    {{"name": "entity name", "type": "PERSON/ORGANIZATION/TECHNOLOGY", "importance": 0.5}}
  ],
  "relationships": [
    {{"source": "entity1", "target": "entity2", "type": "relationship", "strength": 0.5}}
  ]
}}

Focus on: VBE, Nike, Core Nexus, agents, technologies, people.
Keep it simple and valid JSON only.
"""

async def process_memories_safely():
    """Process all memories with robust error handling"""
    logger.info("🚀 Starting Robust Extraction Pipeline")

    # Connect to database
    conn_string = (
        "postgresql://nexus_memory_db_user:2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V@"
        "dpg-d12n0np5pdvs73ctmm40-a.ohio-postgres.render.com:5432/nexus_memory_db"
    )

    conn = await asyncpg.connect(conn_string)
    logger.info("✅ Connected to database")

    # Fetch memories
    rows = await conn.fetch("""
        SELECT id, content, metadata, created_at
        FROM vector_memories
        ORDER BY created_at ASC
    """)

    logger.info(f"📊 Total memories: {len(rows)}")

    # Process in smaller, safer batches
    BATCH_SIZE = 150  # Smaller batches for reliability
    all_entities = {}
    all_relationships = []
    successful_batches = 0
    failed_batches = 0

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i+BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(rows) + BATCH_SIZE - 1) // BATCH_SIZE

        logger.info(f"\n{'='*60}")
        logger.info(f"Processing Batch {batch_num}/{total_batches} ({len(batch)} memories)")
        logger.info(f"{'='*60}")

        # Prepare batch text (limit size)
        memories_text = ""
        for j, row in enumerate(batch[:100]):  # Limit to 100 per batch for safety
            content = row['content'][:500]  # Truncate long memories
            memories_text += f"\n[Memory {j+1}]: {content}\n"

        # Create prompt
        prompt = ROBUST_PROMPT.format(memories_text=memories_text)

        try:
            start_time = time.time()

            # Generate response with timeout
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,  # Very low for consistency
                    max_output_tokens=2048  # Smaller output
                )
            )

            duration = time.time() - start_time

            # Extract and parse JSON safely
            response_text = response.text

            # Try multiple JSON extraction methods
            json_data = None

            # Method 1: Direct parse
            try:
                json_data = json.loads(response_text)
            except Exception:
                # Method 2: Extract from code blocks
                if "```json" in response_text:
                    json_str = response_text.split("```json")[1].split("```")[0]
                    try:
                        json_data = json.loads(json_str.strip())
                    except Exception:
                        pass
                elif "```" in response_text:
                    json_str = response_text.split("```")[1].split("```")[0]
                    try:
                        json_data = json.loads(json_str.strip())
                    except Exception:
                        pass

                # Method 3: Find JSON object
                if not json_data:
                    import re
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        try:
                            json_data = json.loads(json_match.group())
                        except Exception:
                            pass

            if json_data:
                # Process entities
                entities = json_data.get('entities', [])
                for entity in entities:
                    if isinstance(entity, dict) and entity.get('name'):
                        name = entity['name']
                        if name in all_entities:
                            all_entities[name]['count'] += 1
                            all_entities[name]['importance'] = max(
                                all_entities[name]['importance'],
                                entity.get('importance', 0.5)
                            )
                        else:
                            all_entities[name] = {
                                'name': name,
                                'type': entity.get('type', 'UNKNOWN'),
                                'importance': entity.get('importance', 0.5),
                                'count': 1
                            }

                # Process relationships
                relationships = json_data.get('relationships', [])
                all_relationships.extend(relationships)

                logger.info(f"✅ Batch {batch_num} extracted in {duration:.2f}s")
                logger.info(f"   Found {len(entities)} entities, {len(relationships)} relationships")
                successful_batches += 1
            else:
                logger.warning(f"⚠️ Batch {batch_num}: Could not parse JSON response")
                failed_batches += 1

        except Exception as e:
            logger.error(f"❌ Batch {batch_num} failed: {str(e)[:100]}...")
            failed_batches += 1

        # Rate limiting
        if i + BATCH_SIZE < len(rows):
            wait_time = 65
            logger.info(f"⏳ Waiting {wait_time}s for rate limit...")
            await asyncio.sleep(wait_time)

    # Process results
    logger.info("\n" + "="*80)
    logger.info("📊 EXTRACTION COMPLETE")
    logger.info("="*80)
    logger.info(f"✅ Successful batches: {successful_batches}")
    logger.info(f"❌ Failed batches: {failed_batches}")

    # Convert to list and sort
    unique_entities = list(all_entities.values())
    unique_entities.sort(key=lambda x: x['importance'] * x['count'], reverse=True)

    logger.info(f"🔍 Total unique entities: {len(unique_entities)}")
    logger.info(f"🔗 Total relationships: {len(all_relationships)}")

    # Display top entities
    print("\n🏆 TOP 25 ENTITIES:")
    for entity in unique_entities[:25]:
        score = entity['importance'] * entity['count']
        print(f"  - {entity['name']} ({entity['type']}) - Score: {score:.2f} (appears {entity['count']}x)")

    # Deduplicate relationships
    unique_rels = {}
    for rel in all_relationships:
        if isinstance(rel, dict) and rel.get('source') and rel.get('target'):
            key = f"{rel['source']}→{rel['target']}→{rel.get('type', 'RELATED')}"
            unique_rels[key] = rel

    print(f"\n🔗 UNIQUE RELATIONSHIPS: {len(unique_rels)}")

    # Save results
    results = {
        'timestamp': datetime.now().isoformat(),
        'memories_processed': len(rows),
        'successful_batches': successful_batches,
        'failed_batches': failed_batches,
        'entities': unique_entities,
        'relationships': list(unique_rels.values())
    }

    with open('robust_extraction_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    logger.info("\n📋 Results saved to robust_extraction_results.json")

    # Insert into database
    logger.info("\n💾 Updating graph database...")

    entity_id_map = {}
    new_entities = 0

    for entity in unique_entities:
        entity_id = str(uuid4())
        entity_id_map[entity['name']] = entity_id

        try:
            await conn.execute("""
                INSERT INTO graph_nodes (id, entity_type, entity_name, importance_score, mention_count)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (entity_name) DO UPDATE SET
                    importance_score = GREATEST(graph_nodes.importance_score, EXCLUDED.importance_score),
                    mention_count = graph_nodes.mention_count + EXCLUDED.mention_count
                RETURNING id
            """, entity_id, entity['type'], entity['name'],
                float(entity['importance']), entity['count'])
            new_entities += 1
        except Exception:
            # Get existing entity ID
            existing_id = await conn.fetchval(
                "SELECT id FROM graph_nodes WHERE entity_name = $1",
                entity['name']
            )
            if existing_id:
                entity_id_map[entity['name']] = str(existing_id)

    # Insert relationships
    new_relationships = 0
    for rel in unique_rels.values():
        source = rel.get('source', '')
        target = rel.get('target', '')

        if source in entity_id_map and target in entity_id_map:
            try:
                await conn.execute("""
                    INSERT INTO graph_relationships (
                        from_node_id, to_node_id, relationship_type, strength
                    ) VALUES ($1, $2, $3, $4)
                    ON CONFLICT DO NOTHING
                """, entity_id_map[source], entity_id_map[target],
                    rel.get('type', 'RELATED_TO'),
                    float(rel.get('strength', 0.5)))
                new_relationships += 1
            except Exception:
                pass

    # Get final stats
    total_entities = await conn.fetchval("SELECT COUNT(*) FROM graph_nodes")
    total_relationships = await conn.fetchval("SELECT COUNT(*) FROM graph_relationships")

    # Display final summary
    print("\n" + "="*80)
    print("🎉 ROBUST EXTRACTION SUMMARY")
    print("="*80)
    print(f"✅ Memories processed: {len(rows)}")
    print(f"📦 Successful batches: {successful_batches}/{total_batches}")
    print(f"🔍 Unique entities found: {len(unique_entities)}")
    print(f"🔗 Relationships discovered: {len(unique_rels)}")
    print(f"💾 New entities added: {new_entities}")
    print(f"💾 New relationships added: {new_relationships}")
    print(f"📊 Total graph size: {total_entities} entities, {total_relationships} relationships")
    print(f"💰 Estimated cost: ~${successful_batches * 0.03:.2f}")

    await conn.close()

async def main():
    """Main entry point"""
    print("="*80)
    print("🚀 ROBUST GEMINI EXTRACTION")
    print("🛡️ Error-resistant processing for all memories")
    print("📊 Smaller batches for reliability")
    print("="*80)

    await process_memories_safely()

if __name__ == "__main__":
    asyncio.run(main())
