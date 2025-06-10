#!/usr/bin/env python3
"""
Retry failed Batch 2 with improved prompt
"""

import asyncio
import json
import logging
from uuid import uuid4

import asyncpg
import google.generativeai as genai

# Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("retry_batch2")

GEMINI_API_KEY = "AIzaSyAIl8F81WwFfx5_62y19KuO12ermaDC6FQ"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Improved prompt - more explicit
IMPROVED_PROMPT = """
Extract entities and relationships from these 150 memories (Batch 2).

STRICT RULES:
1. Return ONLY valid JSON
2. NO comments, NO explanations, NO markdown
3. Use EXACT format below

Required JSON format:
{{
  "entities": [
    {{"name": "Entity Name", "type": "ORGANIZATION", "importance": 0.8}},
    {{"name": "Another Entity", "type": "TECHNOLOGY", "importance": 0.7}}
  ],
  "relationships": [
    {{"source": "Entity Name", "target": "Another Entity", "type": "PARTNERS_WITH", "strength": 0.8}}
  ]
}}

Entity types: ORGANIZATION, TECHNOLOGY, PERSON, PROJECT, CONCEPT
Relationship types: USES, PARTNERS_WITH, DEVELOPS, WORKS_FOR, RELATED_TO

MEMORIES TO ANALYZE:
{memories_text}

Extract ALL entities and relationships. Focus on: VBE, Nike, Core Nexus, technologies, people.
"""

async def retry_batch2():
    """Retry the failed Batch 2 extraction"""
    logger.info("🔄 Retrying Batch 2 with improved prompt...")

    # Connect to database
    conn = await asyncpg.connect(
        "postgresql://nexus_memory_db_user:2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V@"
        "dpg-d12n0np5pdvs73ctmm40-a.ohio-postgres.render.com:5432/nexus_memory_db"
    )

    # Fetch Batch 2 memories (rows 151-300)
    rows = await conn.fetch("""
        SELECT id, content, metadata, created_at
        FROM vector_memories
        ORDER BY created_at ASC
        OFFSET 150 LIMIT 150
    """)

    logger.info(f"📊 Loaded {len(rows)} memories for Batch 2 retry")

    # Prepare memories text
    memories_text = ""
    for i, row in enumerate(rows[:100]):  # Limit for safety
        content = row['content'][:500]  # Truncate
        memories_text += f"\n[Memory {i+1}]: {content}\n"

    # Create prompt
    prompt = IMPROVED_PROMPT.format(memories_text=memories_text)

    try:
        # Generate with explicit JSON mode
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.1,  # Very low for consistency
                max_output_tokens=2048,
                response_mime_type="application/json"  # Force JSON response
            )
        )

        # Parse response
        data = json.loads(response.text)

        logger.info("✅ Batch 2 retry successful!")
        logger.info(f"🔍 Found {len(data.get('entities', []))} entities")
        logger.info(f"🔗 Found {len(data.get('relationships', []))} relationships")

        # Display results
        print("\n📊 BATCH 2 RETRY RESULTS")
        print("="*60)

        print("\n🔍 ENTITIES FOUND:")
        for entity in data.get('entities', [])[:10]:
            print(f"  - {entity['name']} ({entity['type']}) - {entity['importance']}")

        print("\n🔗 RELATIONSHIPS FOUND:")
        for rel in data.get('relationships', [])[:10]:
            print(f"  - {rel['source']} → {rel['target']} ({rel['type']})")

        # Save results
        with open('batch2_retry_results.json', 'w') as f:
            json.dump({
                'timestamp': asyncio.get_event_loop().time(),
                'batch': 2,
                'memories_processed': len(rows),
                'entities': data.get('entities', []),
                'relationships': data.get('relationships', [])
            }, f, indent=2)

        # Insert into database
        logger.info("\n💾 Inserting Batch 2 entities...")

        entity_map = {}
        for entity in data.get('entities', []):
            if entity.get('name'):
                entity_id = str(uuid4())
                entity_map[entity['name']] = entity_id

                try:
                    await conn.execute("""
                        INSERT INTO graph_nodes (id, entity_type, entity_name, importance_score)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (entity_name) DO UPDATE SET
                            importance_score = GREATEST(graph_nodes.importance_score, EXCLUDED.importance_score)
                    """, entity_id, entity['type'], entity['name'], float(entity['importance']))
                except Exception:
                    logger.debug(f"Entity exists: {entity['name']}")

        # Insert relationships
        rel_count = 0
        for rel in data.get('relationships', []):
            if rel.get('source') in entity_map and rel.get('target') in entity_map:
                try:
                    await conn.execute("""
                        INSERT INTO graph_relationships (
                            from_node_id, to_node_id, relationship_type, strength
                        ) VALUES ($1, $2, $3, $4)
                        ON CONFLICT DO NOTHING
                    """, entity_map[rel['source']], entity_map[rel['target']],
                        rel['type'], float(rel.get('strength', 0.5)))
                    rel_count += 1
                except Exception:
                    pass

        logger.info(f"✅ Inserted {len(entity_map)} entities and {rel_count} relationships")

        # Final stats
        total_entities = await conn.fetchval("SELECT COUNT(*) FROM graph_nodes")
        total_rels = await conn.fetchval("SELECT COUNT(*) FROM graph_relationships")

        print("\n📊 UPDATED GRAPH TOTALS:")
        print(f"  - Total Entities: {total_entities}")
        print(f"  - Total Relationships: {total_rels}")

    except Exception as e:
        logger.error(f"❌ Batch 2 retry failed: {e}")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(retry_batch2())
