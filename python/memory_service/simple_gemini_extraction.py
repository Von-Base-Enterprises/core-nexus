#!/usr/bin/env python3
"""
Simplified Gemini extraction that works
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
logger = logging.getLogger("simple_extraction")

# Configure Gemini
GEMINI_API_KEY = "AIzaSyAIl8F81WwFfx5_62y19KuO12ermaDC6FQ"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Simple prompt
EXTRACTION_PROMPT = """
Extract entities and relationships from these memories. Return ONLY valid JSON.

MEMORIES:
{memories_text}

Return this exact JSON structure:
{{
  "entities": [
    {{"name": "entity name", "type": "PERSON/ORGANIZATION/TECHNOLOGY/LOCATION/CONCEPT", "importance": 0.1-1.0}},
    ...
  ],
  "relationships": [
    {{"source": "entity1", "target": "entity2", "type": "relationship type", "strength": 0.1-1.0}},
    ...
  ]
}}

Focus on: VBE, Nike, Core Nexus, agents, technologies, people, projects.
"""

async def main():
    logger.info("🚀 Starting Simple Gemini Extraction")

    # Connect to database
    conn_string = (
        "postgresql://nexus_memory_db_user:2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V@"
        "dpg-d12n0np5pdvs73ctmm40-a.ohio-postgres.render.com:5432/nexus_memory_db"
    )

    conn = await asyncpg.connect(conn_string)
    logger.info("✅ Connected to database")

    # Fetch memories in smaller batch to avoid quota limits
    rows = await conn.fetch("""
        SELECT id, content, metadata, created_at
        FROM vector_memories
        ORDER BY created_at DESC
        LIMIT 100
    """)

    logger.info(f"📊 Processing {len(rows)} memories (batch limited for quota)")

    # Prepare memories text
    memories_text = ""
    memory_ids = []
    for i, row in enumerate(rows):
        memory_ids.append(str(row['id']))
        memories_text += f"\n--- Memory {i+1} (ID: {row['id']}) ---\n"
        memories_text += f"{row['content']}\n"

    # Create prompt
    prompt = EXTRACTION_PROMPT.format(memories_text=memories_text)

    logger.info("🤖 Calling Gemini API...")
    start_time = time.time()

    try:
        # Generate response
        response = model.generate_content(prompt)

        # Extract JSON from response
        response_text = response.text

        # Try to extract JSON from various formats
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        # Clean up common JSON formatting issues
        response_text = response_text.strip()

        # Try to parse the JSON
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            # Try to fix common issues
            logger.warning(f"JSON parse error: {e}")
            # Save raw response for debugging
            with open('raw_response.txt', 'w') as f:
                f.write(response.text)
            logger.info("Raw response saved to raw_response.txt")

            # Create minimal valid response
            data = {
                'entities': [],
                'relationships': []
            }

        duration = time.time() - start_time
        logger.info(f"✅ Extraction complete in {duration:.2f}s")
        logger.info(f"🔍 Found {len(data.get('entities', []))} entities")
        logger.info(f"🔗 Found {len(data.get('relationships', []))} relationships")

        # Show sample results
        print("\n📊 EXTRACTION RESULTS")
        print("=" * 60)

        print("\n🔍 TOP ENTITIES:")
        entities = data.get('entities', [])
        for entity in entities[:10]:
            if isinstance(entity, dict):
                print(f"  - {entity.get('name', 'Unknown')} ({entity.get('type', 'Unknown')}) - Importance: {entity.get('importance', 0.5)}")
            else:
                print(f"  - {entity}")

        print("\n🔗 TOP RELATIONSHIPS:")
        relationships = data.get('relationships', [])
        for rel in relationships[:10]:
            if isinstance(rel, dict):
                print(f"  - {rel.get('source', '?')} → {rel.get('target', '?')} ({rel.get('type', 'Unknown')})")
            else:
                print(f"  - {rel}")

        # Save results
        with open('extraction_results.json', 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'memories_processed': len(rows),
                'extraction_time': duration,
                'entities': data.get('entities', []),
                'relationships': data.get('relationships', []),
                'memory_ids': memory_ids
            }, f, indent=2)

        logger.info("\n📋 Results saved to extraction_results.json")

        # Insert into database
        logger.info("\n💾 Inserting into graph tables...")

        # Create entity mapping
        entity_map = {}
        entities_to_insert = []

        for entity in data.get('entities', []):
            if isinstance(entity, dict):
                entity_name = entity.get('name', '')
                entity_type = entity.get('type', 'UNKNOWN')
                importance = float(entity.get('importance', 0.5))

                if entity_name:
                    entity_id = str(uuid4())
                    entity_map[entity_name] = entity_id
                    entities_to_insert.append((entity_id, entity_type, entity_name, importance))

        # Insert entities
        for entity_id, entity_type, entity_name, importance in entities_to_insert:
            try:
                await conn.execute("""
                    INSERT INTO graph_nodes (id, entity_type, entity_name, importance_score)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (id) DO NOTHING
                """, entity_id, entity_type, entity_name, importance)
            except Exception as e:
                logger.warning(f"Failed to insert entity {entity_name}: {e}")

        # Insert relationships
        relationships_inserted = 0
        for rel in data.get('relationships', []):
            if isinstance(rel, dict):
                source = rel.get('source', '')
                target = rel.get('target', '')
                rel_type = rel.get('type', 'RELATED_TO')
                strength = float(rel.get('strength', 0.5))

                if source in entity_map and target in entity_map:
                    try:
                        await conn.execute("""
                            INSERT INTO graph_relationships (
                                from_node_id, to_node_id, relationship_type, strength
                            ) VALUES ($1, $2, $3, $4)
                            ON CONFLICT DO NOTHING
                        """, entity_map[source], entity_map[target], rel_type, strength)
                        relationships_inserted += 1
                    except Exception as e:
                        logger.warning(f"Failed to insert relationship {source} -> {target}: {e}")

        logger.info("✅ Graph populated successfully!")
        logger.info(f"📊 Inserted {len(entities_to_insert)} entities and {relationships_inserted} relationships")

    except Exception as e:
        logger.error(f"❌ Error: {e}")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
