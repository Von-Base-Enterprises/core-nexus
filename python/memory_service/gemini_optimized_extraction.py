#!/usr/bin/env python3
"""
Optimized Gemini Extraction for Free Tier (250k tokens/minute)
Maximizes context while respecting rate limits
"""

import asyncio
import json
import os
import time
from datetime import datetime
import logging
from uuid import uuid4
import google.generativeai as genai
import asyncpg

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("optimized_extraction")

# Configure Gemini
GEMINI_API_KEY = "AIzaSyAIl8F81WwFfx5_62y19KuO12ermaDC6FQ"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Optimized prompt for maximum extraction
OPTIMIZED_PROMPT = """
Extract ALL entities and relationships from these {count} memories. Find cross-memory patterns.

Focus on:
- Von Base Enterprises (VBE) and all partnerships
- Core Nexus project evolution
- All people, organizations, technologies
- How entities connect across different memories
- Timeline of key events

MEMORIES:
{memories_text}

Return JSON with entities (name, type, importance, memory_count) and relationships (source, target, type, strength).
Include cross-memory connections!
"""

def estimate_tokens(text):
    """Conservative token estimation"""
    return len(text) // 3  # More conservative estimate

async def run_optimized_extraction():
    """Extract entities within free tier limits"""
    logger.info("🚀 Starting Optimized Extraction (250k token limit)")
    
    # Connect to database
    conn_string = (
        f"postgresql://nexus_memory_db_user:2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V@"
        f"dpg-d12n0np5pdvs73ctmm40-a.ohio-postgres.render.com:5432/nexus_memory_db"
    )
    
    conn = await asyncpg.connect(conn_string)
    logger.info("✅ Connected to database")
    
    # Fetch ALL memories
    rows = await conn.fetch("""
        SELECT id, content, metadata, created_at
        FROM vector_memories
        ORDER BY created_at ASC
    """)
    
    logger.info(f"📊 Total memories: {len(rows)}")
    
    # Calculate optimal batch size for 250k limit
    # Leave 50k buffer for prompt and response
    MAX_TOKENS_PER_BATCH = 200000
    
    batches = []
    current_batch = []
    current_tokens = 0
    
    for row in rows:
        memory_text = f"Memory {row['id']}: {row['content']}\n"
        memory_tokens = estimate_tokens(memory_text)
        
        if current_tokens + memory_tokens > MAX_TOKENS_PER_BATCH and current_batch:
            batches.append(current_batch)
            current_batch = [row]
            current_tokens = memory_tokens
        else:
            current_batch.append(row)
            current_tokens += memory_tokens
    
    if current_batch:
        batches.append(current_batch)
    
    logger.info(f"📦 Created {len(batches)} optimized batches:")
    for i, batch in enumerate(batches):
        batch_tokens = sum(estimate_tokens(f"Memory {r['id']}: {r['content']}\n") for r in batch)
        logger.info(f"  Batch {i+1}: {len(batch)} memories, ~{batch_tokens:,} tokens")
    
    # Process batches with rate limiting
    all_entities = {}
    all_relationships = []
    entity_memory_map = {}
    
    for i, batch in enumerate(batches):
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing Batch {i+1}/{len(batches)} ({len(batch)} memories)")
        logger.info(f"{'='*60}")
        
        # Prepare batch text
        memories_text = ""
        batch_ids = []
        for j, row in enumerate(batch):
            batch_ids.append(str(row['id']))
            memories_text += f"\n--- Memory {j+1} (ID: {row['id']}, Date: {row['created_at']}) ---\n"
            memories_text += f"{row['content']}\n"
        
        # Create prompt
        prompt = OPTIMIZED_PROMPT.format(count=len(batch), memories_text=memories_text)
        prompt_tokens = estimate_tokens(prompt)
        logger.info(f"📏 Batch prompt size: ~{prompt_tokens:,} tokens")
        
        try:
            start_time = time.time()
            
            # Generate response
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=4096
                )
            )
            
            duration = time.time() - start_time
            logger.info(f"✅ Batch extracted in {duration:.2f}s")
            
            # Parse response
            response_text = response.text
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            data = json.loads(response_text.strip())
            
            # Merge entities (deduplicate)
            batch_entities = data.get('entities', [])
            for entity in batch_entities:
                if isinstance(entity, dict):
                    name = entity.get('name', '')
                    if name:
                        if name in all_entities:
                            # Update existing entity
                            all_entities[name]['importance'] = max(
                                all_entities[name]['importance'],
                                entity.get('importance', 0.5)
                            )
                            all_entities[name]['memory_count'] += 1
                        else:
                            # New entity
                            all_entities[name] = {
                                'name': name,
                                'type': entity.get('type', 'UNKNOWN'),
                                'importance': entity.get('importance', 0.5),
                                'memory_count': 1
                            }
                        
                        # Track which memories contain this entity
                        if name not in entity_memory_map:
                            entity_memory_map[name] = []
                        entity_memory_map[name].extend(batch_ids[:10])  # Limit for performance
            
            # Add relationships
            batch_relationships = data.get('relationships', [])
            all_relationships.extend(batch_relationships)
            
            logger.info(f"🔍 Batch results: {len(batch_entities)} entities, {len(batch_relationships)} relationships")
            
        except Exception as e:
            logger.error(f"❌ Error processing batch {i+1}: {e}")
        
        # Rate limiting between batches
        if i < len(batches) - 1:
            wait_time = 65  # Wait 65 seconds to ensure we stay under limit
            logger.info(f"⏳ Waiting {wait_time}s for rate limit...")
            await asyncio.sleep(wait_time)
    
    # Final results
    logger.info("\n" + "="*80)
    logger.info("📊 EXTRACTION COMPLETE - FINAL RESULTS")
    logger.info("="*80)
    
    unique_entities = list(all_entities.values())
    logger.info(f"🔍 Total unique entities: {len(unique_entities)}")
    logger.info(f"🔗 Total relationships: {len(all_relationships)}")
    
    # Sort entities by importance
    sorted_entities = sorted(unique_entities, key=lambda x: x['importance'], reverse=True)
    
    print("\n🏆 TOP 20 ENTITIES BY IMPORTANCE:")
    for entity in sorted_entities[:20]:
        print(f"  - {entity['name']} ({entity['type']}) - Score: {entity['importance']:.2f}, Appears in {entity['memory_count']} batches")
    
    # Deduplicate relationships
    unique_rels = {}
    for rel in all_relationships:
        if isinstance(rel, dict):
            key = f"{rel.get('source', '')}→{rel.get('target', '')}→{rel.get('type', '')}"
            if key not in unique_rels:
                unique_rels[key] = rel
    
    print(f"\n🔗 UNIQUE RELATIONSHIPS: {len(unique_rels)}")
    for i, (key, rel) in enumerate(list(unique_rels.items())[:10]):
        print(f"  - {rel.get('source', '?')} → {rel.get('target', '?')} ({rel.get('type', 'UNKNOWN')})")
    
    # Save comprehensive results
    final_results = {
        'timestamp': datetime.now().isoformat(),
        'memories_processed': len(rows),
        'batches': len(batches),
        'entities': sorted_entities,
        'relationships': list(unique_rels.values()),
        'entity_memory_map': entity_memory_map,
        'extraction_method': 'optimized_batching'
    }
    
    with open('optimized_extraction_results.json', 'w') as f:
        json.dump(final_results, f, indent=2)
    
    logger.info("\n📋 Full results saved to optimized_extraction_results.json")
    
    # Insert into database
    logger.info("\n💾 Inserting into graph database...")
    
    entity_id_map = {}
    entities_inserted = 0
    
    for entity in sorted_entities:
        entity_id = str(uuid4())
        entity_id_map[entity['name']] = entity_id
        
        try:
            await conn.execute("""
                INSERT INTO graph_nodes (id, entity_type, entity_name, importance_score, properties)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (entity_name) DO UPDATE SET
                    importance_score = GREATEST(graph_nodes.importance_score, EXCLUDED.importance_score),
                    properties = graph_nodes.properties || EXCLUDED.properties
            """, entity_id, entity['type'], entity['name'], 
                float(entity['importance']),
                json.dumps({'memory_count': entity['memory_count']}))
            entities_inserted += 1
        except Exception as e:
            logger.debug(f"Entity {entity['name']} already exists or error: {e}")
    
    # Insert relationships
    relationships_inserted = 0
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
                relationships_inserted += 1
            except Exception as e:
                logger.debug(f"Relationship insert issue: {e}")
    
    logger.info(f"✅ Inserted {entities_inserted} new entities and {relationships_inserted} new relationships")
    
    # Final summary
    print("\n" + "="*80)
    print("🎉 OPTIMIZED EXTRACTION SUMMARY")
    print("="*80)
    print(f"✅ Memories processed: {len(rows)}")
    print(f"📦 Batches used: {len(batches)}")
    print(f"🔍 Unique entities found: {len(unique_entities)}")
    print(f"🔗 Relationships discovered: {len(unique_rels)}")
    print(f"💾 Database updated: {entities_inserted} entities, {relationships_inserted} relationships")
    print(f"💰 Estimated cost: ~${len(batches) * 0.05:.2f}")
    print("🚀 Optimization: Maximized context within free tier limits")
    
    await conn.close()

async def main():
    """Main entry point"""
    print("="*80)
    print("🚀 OPTIMIZED GEMINI EXTRACTION")
    print("📊 Maximizing context within 250k token/minute limit")
    print("🎯 Smart batching for cross-memory intelligence")
    print("="*80)
    
    await run_optimized_extraction()

if __name__ == "__main__":
    asyncio.run(main())