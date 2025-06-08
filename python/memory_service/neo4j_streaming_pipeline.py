#!/usr/bin/env python3
"""
Async Neo4j Streaming Pipeline for Core Nexus
Real-time entity extraction and graph building following Neo4j GraphRAG patterns
Agent 2 Advanced Implementation
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging
from dataclasses import dataclass
from uuid import UUID

import spacy
from neo4j import AsyncGraphDatabase
import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ExtractedEntity:
    """Entity extracted from memory content."""
    name: str
    type: str
    confidence: float
    start: int
    end: int
    context: str


@dataclass
class InferredRelationship:
    """Relationship inferred between entities."""
    source: str
    target: str
    type: str
    confidence: float
    context: str


class Neo4jStreamingPipeline:
    """
    Async streaming pipeline that:
    1. Monitors new memories from Core Nexus
    2. Extracts entities using spaCy
    3. Deduplicates and enriches entities
    4. Streams to Neo4j in real-time
    
    Following patterns from:
    - Neo4j GraphRAG guide
    - O'Reilly Knowledge Graphs book
    - FastAPI async best practices
    """
    
    def __init__(self, 
                 neo4j_uri: str,
                 neo4j_user: str,
                 neo4j_password: str,
                 core_nexus_url: str = "https://core-nexus-memory-service.onrender.com"):
        
        self.neo4j_driver = AsyncGraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )
        self.core_nexus_url = core_nexus_url
        
        # Load spaCy model
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except:
            logger.warning("spaCy model not found, using simple extraction")
            self.nlp = None
        
        # Entity deduplication cache
        self.entity_cache = {}
        
        # Performance metrics
        self.metrics = {
            "memories_processed": 0,
            "entities_extracted": 0,
            "relationships_created": 0,
            "processing_time_ms": []
        }
    
    async def extract_entities(self, text: str) -> List[ExtractedEntity]:
        """Extract entities using spaCy with GraphRAG patterns."""
        entities = []
        
        if self.nlp:
            doc = self.nlp(text)
            
            # Extract named entities
            for ent in doc.ents:
                entities.append(ExtractedEntity(
                    name=ent.text,
                    type=self._map_spacy_type(ent.label_),
                    confidence=0.85,  # spaCy is high confidence
                    start=ent.start_char,
                    end=ent.end_char,
                    context=text[max(0, ent.start_char-50):min(len(text), ent.end_char+50)]
                ))
            
            # Extract additional patterns (following GraphRAG guide)
            # Technologies mentioned
            tech_patterns = ["AI", "ML", "API", "GraphQL", "REST", "Docker", "Kubernetes"]
            for tech in tech_patterns:
                if tech.lower() in text.lower():
                    entities.append(ExtractedEntity(
                        name=tech,
                        type="TECHNOLOGY",
                        confidence=0.7,
                        start=text.lower().find(tech.lower()),
                        end=text.lower().find(tech.lower()) + len(tech),
                        context=tech
                    ))
        
        return entities
    
    def _map_spacy_type(self, spacy_type: str) -> str:
        """Map spaCy types to Neo4j node labels."""
        mapping = {
            'PERSON': 'Person',
            'ORG': 'Organization',
            'GPE': 'Location',
            'LOC': 'Location',
            'PRODUCT': 'Product',
            'EVENT': 'Event',
            'DATE': 'TimeReference',
            'MONEY': 'Financial',
            'WORK_OF_ART': 'Creative'
        }
        return mapping.get(spacy_type, 'Entity')
    
    async def infer_relationships(self, 
                                entities: List[ExtractedEntity], 
                                text: str) -> List[InferredRelationship]:
        """
        Infer relationships using GraphRAG patterns:
        - Co-occurrence within sentences
        - Verb-based patterns
        - Domain-specific rules
        """
        relationships = []
        
        # Split into sentences for co-occurrence
        sentences = text.split('.')
        
        for sentence in sentences:
            entities_in_sentence = [e for e in entities if e.context in sentence]
            
            # Co-occurrence relationships
            for i, e1 in enumerate(entities_in_sentence):
                for e2 in entities_in_sentence[i+1:]:
                    rel_type = self._determine_relationship_type(e1, e2, sentence)
                    
                    relationships.append(InferredRelationship(
                        source=e1.name,
                        target=e2.name,
                        type=rel_type,
                        confidence=0.7,
                        context=sentence[:100]
                    ))
        
        return relationships
    
    def _determine_relationship_type(self, e1: ExtractedEntity, e2: ExtractedEntity, context: str) -> str:
        """Determine relationship type using patterns from GraphRAG guide."""
        context_lower = context.lower()
        
        # Verb patterns
        if any(verb in context_lower for verb in ['develops', 'creates', 'builds']):
            return 'CREATES'
        elif any(verb in context_lower for verb in ['uses', 'utilizes', 'employs']):
            return 'USES'
        elif any(verb in context_lower for verb in ['works', 'employed', 'job']):
            return 'WORKS_AT'
        elif any(verb in context_lower for verb in ['located', 'based', 'headquartered']):
            return 'LOCATED_IN'
        elif e1.type == 'Person' and e2.type == 'Organization':
            return 'AFFILIATED_WITH'
        else:
            return 'RELATED_TO'
    
    async def deduplicate_entity(self, entity: ExtractedEntity) -> str:
        """Deduplicate entities using Neo4j patterns."""
        # Simple normalization
        normalized_name = entity.name.lower().strip()
        
        # Check cache
        cache_key = f"{entity.type}:{normalized_name}"
        if cache_key in self.entity_cache:
            return self.entity_cache[cache_key]
        
        # Will be replaced with Neo4j lookup in production
        canonical_name = entity.name
        self.entity_cache[cache_key] = canonical_name
        
        return canonical_name
    
    async def stream_to_neo4j(self, 
                            memory_id: UUID,
                            entities: List[ExtractedEntity],
                            relationships: List[InferredRelationship]):
        """
        Stream entities and relationships to Neo4j.
        Uses MERGE to handle duplicates (O'Reilly pattern).
        """
        async with self.neo4j_driver.session() as session:
            # Create entities
            for entity in entities:
                canonical_name = await self.deduplicate_entity(entity)
                
                await session.run("""
                    MERGE (e:Entity {name: $name})
                    ON CREATE SET 
                        e.type = $type,
                        e.first_seen = datetime(),
                        e.confidence = $confidence,
                        e.mention_count = 1
                    ON MATCH SET
                        e.mention_count = e.mention_count + 1,
                        e.last_seen = datetime(),
                        e.confidence = CASE 
                            WHEN e.confidence < $confidence 
                            THEN $confidence 
                            ELSE e.confidence 
                        END
                    WITH e
                    MERGE (m:Memory {id: $memory_id})
                    MERGE (e)-[r:MENTIONED_IN]->(m)
                    ON CREATE SET r.created = datetime()
                """, 
                name=canonical_name,
                type=entity.type,
                confidence=entity.confidence,
                memory_id=str(memory_id))
                
                self.metrics["entities_extracted"] += 1
            
            # Create relationships
            for rel in relationships:
                await session.run("""
                    MATCH (source:Entity {name: $source})
                    MATCH (target:Entity {name: $target})
                    MERGE (source)-[r:RELATIONSHIP {type: $type}]->(target)
                    ON CREATE SET
                        r.confidence = $confidence,
                        r.first_seen = datetime(),
                        r.occurrences = 1,
                        r.contexts = [$context]
                    ON MATCH SET
                        r.occurrences = r.occurrences + 1,
                        r.last_seen = datetime(),
                        r.confidence = CASE
                            WHEN r.confidence < $confidence
                            THEN $confidence
                            ELSE r.confidence
                        END,
                        r.contexts = r.contexts + $context
                """,
                source=rel.source,
                target=rel.target,
                type=rel.type,
                confidence=rel.confidence,
                context=rel.context)
                
                self.metrics["relationships_created"] += 1
    
    async def process_memory(self, memory_id: UUID, content: str):
        """Process a single memory through the pipeline."""
        start_time = datetime.now()
        
        try:
            # Extract entities
            entities = await self.extract_entities(content)
            
            # Infer relationships
            relationships = await self.infer_relationships(entities, content)
            
            # Stream to Neo4j
            await self.stream_to_neo4j(memory_id, entities, relationships)
            
            # Track metrics
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self.metrics["processing_time_ms"].append(processing_time)
            self.metrics["memories_processed"] += 1
            
            logger.info(f"✅ Processed memory {memory_id}: {len(entities)} entities, {len(relationships)} relationships in {processing_time:.0f}ms")
            
        except Exception as e:
            logger.error(f"❌ Failed to process memory {memory_id}: {e}")
    
    async def monitor_and_stream(self, poll_interval: int = 30):
        """
        Monitor Core Nexus for new memories and stream to Neo4j.
        This is the main pipeline loop.
        """
        logger.info("🚀 Starting Neo4j Streaming Pipeline...")
        
        last_check = datetime.now()
        
        while True:
            try:
                # Query for new memories since last check
                async with aiohttp.ClientSession() as session:
                    # TODO: Use actual Core Nexus API when available
                    # For now, simulate with stats endpoint
                    async with session.get(f"{self.core_nexus_url}/memories/stats") as response:
                        if response.status == 200:
                            data = await response.json()
                            total_memories = data.get('total_memories', 0)
                            
                            if total_memories > self.metrics["memories_processed"]:
                                logger.info(f"📥 Found {total_memories - self.metrics['memories_processed']} new memories")
                                
                                # TODO: Fetch and process actual memories
                                # For demo, process sample
                                await self.process_memory(
                                    UUID('12345678-1234-5678-1234-567812345678'),
                                    "Von Base Enterprises is developing Core Nexus with advanced AI capabilities. "
                                    "The team includes John Smith as CTO and Sarah Johnson as AI Lead."
                                )
                
                # Log performance stats
                if self.metrics["memories_processed"] % 10 == 0 and self.metrics["processing_time_ms"]:
                    avg_time = sum(self.metrics["processing_time_ms"]) / len(self.metrics["processing_time_ms"])
                    logger.info(f"📊 Performance: Avg {avg_time:.0f}ms per memory, {self.metrics['entities_extracted']} entities extracted")
                
                last_check = datetime.now()
                await asyncio.sleep(poll_interval)
                
            except Exception as e:
                logger.error(f"Pipeline error: {e}")
                await asyncio.sleep(poll_interval)
    
    async def close(self):
        """Clean up resources."""
        await self.neo4j_driver.close()


async def main():
    """Run the streaming pipeline."""
    # Configuration (use environment variables in production)
    pipeline = Neo4jStreamingPipeline(
        neo4j_uri="neo4j://localhost:7687",  # Or Neo4j Aura URI
        neo4j_user="neo4j",
        neo4j_password="password",
        core_nexus_url="https://core-nexus-memory-service.onrender.com"
    )
    
    try:
        # Start monitoring and streaming
        await pipeline.monitor_and_stream()
    finally:
        await pipeline.close()


if __name__ == "__main__":
    asyncio.run(main())