"""
Graph-Enhanced Scoring Engine

Implements sophisticated scoring algorithms that leverage knowledge graph structure
for enhanced memory relevance and importance calculation.
"""

import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID
import math

logger = logging.getLogger(__name__)


@dataclass
class EntityScore:
    """Score breakdown for an entity."""
    entity_name: str
    centrality_score: float
    relationship_strength: float
    mention_frequency: float
    temporal_relevance: float
    combined_score: float


@dataclass  
class GraphScoreWeights:
    """Configurable weights for graph scoring components."""
    centrality: float = 0.3
    relationship_strength: float = 0.25
    mention_frequency: float = 0.2
    temporal_relevance: float = 0.15
    query_relevance: float = 0.1
    
    def __post_init__(self):
        total = sum([self.centrality, self.relationship_strength, self.mention_frequency, 
                    self.temporal_relevance, self.query_relevance])
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Graph scoring weights must sum to 1.0, got {total}")


@dataclass
class GraphPerformanceConfig:
    """Configuration for graph performance and safety limits."""
    max_entities_per_memory: int = 10  # Limit entity extraction to prevent explosion
    max_scoring_time_ms: int = 1000  # Maximum time for memory scoring
    max_centrality_cache_size: int = 1000  # Limit cache to prevent memory bloat
    enable_fast_mode: bool = False  # Skip expensive calculations for speed
    max_relationships_per_entity: int = 50  # Limit relationships to prevent explosion
    min_confidence_threshold: float = 0.5  # Filter out low-confidence entities
    enable_scoring_timeout: bool = True  # Enable timeout for scoring operations


class GraphScoringEngine:
    """
    Advanced graph-aware scoring engine that calculates memory relevance
    based on knowledge graph structure and relationships.
    """
    
    def __init__(self, connection_pool, weights: Optional[GraphScoreWeights] = None, 
                 performance_config: Optional[GraphPerformanceConfig] = None):
        self.connection_pool = connection_pool
        self.weights = weights or GraphScoreWeights()
        self.performance_config = performance_config or GraphPerformanceConfig()
        self.entity_cache = {}  # Cache for entity centrality scores
        self.cache_expiry_time = 300  # 5 minutes cache
        self.last_cache_update = 0
        
        # Initialize performance tracking
        self.scoring_timeouts = 0
        self.cache_hits = 0
        self.cache_misses = 0
        
    async def calculate_memory_graph_score(
        self, 
        memory_id: UUID, 
        extracted_entities: List[str],
        query_entities: List[str],
        relationship_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive graph-based score for a memory.
        
        Returns detailed scoring breakdown including individual entity scores,
        relationship strengths, and overall graph-enhanced relevance.
        """
        try:
            start_time = time.time()
            
            # Apply performance and safety limits
            if len(extracted_entities) > self.performance_config.max_entities_per_memory:
                logger.warning(f"Limiting entities from {len(extracted_entities)} to {self.performance_config.max_entities_per_memory}")
                extracted_entities = extracted_entities[:self.performance_config.max_entities_per_memory]
            
            # Fast mode: return simplified scoring
            if self.performance_config.enable_fast_mode:
                return {
                    "graph_score": 0.7,  # Reasonable default
                    "entity_scores": [],
                    "network_strength": 0.5,
                    "query_relevance": self._calculate_query_relevance(extracted_entities, query_entities),
                    "temporal_factor": 0.8,
                    "calculation_time_ms": (time.time() - start_time) * 1000,
                    "scoring_method": "fast_mode",
                    "entities_limited": len(extracted_entities)
                }
            
            # Create timeout wrapper for scoring operations
            async def scoring_with_timeout():
                # Get entity scores for this memory
                entity_scores = await self._calculate_entity_scores(
                    extracted_entities, query_entities, memory_id
                )
                
                # Calculate relationship network strength
                network_strength = await self._calculate_network_strength(
                    extracted_entities, memory_id
                )
                
                # Calculate query-entity relevance matching
                query_relevance = self._calculate_query_relevance(
                    extracted_entities, query_entities
                )
                
                # Combine scores with temporal decay
                temporal_factor = await self._calculate_temporal_factor(memory_id)
                
                # Calculate final graph score
                graph_score = self._combine_graph_scores(
                    entity_scores, network_strength, query_relevance, temporal_factor
                )
                
                return entity_scores, network_strength, query_relevance, temporal_factor, graph_score
            
            # Execute with timeout if enabled
            if self.performance_config.enable_scoring_timeout:
                try:
                    entity_scores, network_strength, query_relevance, temporal_factor, graph_score = await asyncio.wait_for(
                        scoring_with_timeout(), 
                        timeout=self.performance_config.max_scoring_time_ms / 1000.0
                    )
                except asyncio.TimeoutError:
                    self.scoring_timeouts += 1
                    logger.warning(f"Graph scoring timeout for memory {memory_id} after {self.performance_config.max_scoring_time_ms}ms")
                    # Return fallback scores
                    return {
                        "graph_score": 0.5,
                        "entity_scores": [],
                        "network_strength": 0.5,
                        "query_relevance": self._calculate_query_relevance(extracted_entities, query_entities),
                        "temporal_factor": 0.7,
                        "calculation_time_ms": self.performance_config.max_scoring_time_ms,
                        "scoring_method": "timeout_fallback",
                        "timeout_count": self.scoring_timeouts
                    }
            else:
                entity_scores, network_strength, query_relevance, temporal_factor, graph_score = await scoring_with_timeout()
            
            calculation_time = (time.time() - start_time) * 1000
            
            return {
                "graph_score": graph_score,
                "entity_scores": entity_scores,
                "network_strength": network_strength,
                "query_relevance": query_relevance,
                "temporal_factor": temporal_factor,
                "calculation_time_ms": calculation_time,
                "scoring_method": "pagerank_enhanced"
            }
            
        except Exception as e:
            logger.error(f"Graph scoring failed for memory {memory_id}: {e}")
            return {
                "graph_score": 0.5,  # Neutral fallback score
                "error": str(e),
                "scoring_method": "fallback"
            }
    
    async def _calculate_entity_scores(
        self, 
        entities: List[str], 
        query_entities: List[str],
        memory_id: UUID
    ) -> List[EntityScore]:
        """Calculate detailed scores for each entity in the memory."""
        entity_scores = []
        
        if not entities:
            return entity_scores
            
        async with self.connection_pool.acquire() as conn:
            for entity_name in entities:
                try:
                    # Get entity data
                    entity_data = await conn.fetchrow("""
                        SELECT id, entity_type, importance_score, mention_count, last_seen
                        FROM graph_nodes 
                        WHERE entity_name = $1
                    """, entity_name)
                    
                    if not entity_data:
                        continue
                    
                    # Calculate centrality score (PageRank-style)
                    centrality_score = await self._calculate_entity_centrality(
                        entity_data['id'], conn
                    )
                    
                    # Calculate relationship strength for this entity
                    relationship_strength = await self._calculate_entity_relationship_strength(
                        entity_data['id'], conn
                    )
                    
                    # Mention frequency normalized score
                    mention_frequency = min(1.0, entity_data['mention_count'] / 50.0)  # Normalize to max 50 mentions
                    
                    # Temporal relevance based on when entity was last seen
                    temporal_relevance = self._calculate_temporal_relevance(
                        entity_data['last_seen']
                    )
                    
                    # Combine all scores
                    combined_score = (
                        centrality_score * self.weights.centrality +
                        relationship_strength * self.weights.relationship_strength +
                        mention_frequency * self.weights.mention_frequency +
                        temporal_relevance * self.weights.temporal_relevance
                    )
                    
                    # Boost if entity appears in query
                    if entity_name in query_entities:
                        combined_score += self.weights.query_relevance
                    
                    entity_scores.append(EntityScore(
                        entity_name=entity_name,
                        centrality_score=centrality_score,
                        relationship_strength=relationship_strength,
                        mention_frequency=mention_frequency,
                        temporal_relevance=temporal_relevance,
                        combined_score=min(1.0, combined_score)
                    ))
                    
                except Exception as e:
                    logger.warning(f"Failed to score entity {entity_name}: {e}")
                    continue
        
        return entity_scores
    
    async def _calculate_entity_centrality(self, entity_id: UUID, conn) -> float:
        """
        Calculate PageRank-style centrality score for an entity.
        
        Entities with more connections to important entities get higher scores.
        """
        try:
            # Use cached score if available and fresh
            cache_key = str(entity_id)
            current_time = time.time()
            
            if (cache_key in self.entity_cache and 
                current_time - self.last_cache_update < self.cache_expiry_time):
                return self.entity_cache[cache_key]
            
            # Calculate centrality based on weighted connections
            centrality_data = await conn.fetchrow("""
                WITH entity_connections AS (
                    -- Outgoing connections
                    SELECT r.to_node_id as connected_id, r.strength, tn.importance_score as target_importance
                    FROM graph_relationships r
                    JOIN graph_nodes tn ON r.to_node_id = tn.id
                    WHERE r.from_node_id = $1
                    
                    UNION ALL
                    
                    -- Incoming connections  
                    SELECT r.from_node_id as connected_id, r.strength, fn.importance_score as target_importance
                    FROM graph_relationships r
                    JOIN graph_nodes fn ON r.from_node_id = fn.id
                    WHERE r.to_node_id = $1
                ),
                centrality_calc AS (
                    SELECT 
                        COUNT(*) as connection_count,
                        AVG(strength) as avg_strength,
                        AVG(target_importance) as avg_target_importance,
                        SUM(strength * target_importance) as weighted_sum
                    FROM entity_connections
                )
                SELECT 
                    COALESCE(connection_count, 0) as connections,
                    COALESCE(avg_strength, 0) as strength,
                    COALESCE(avg_target_importance, 0) as target_importance,
                    COALESCE(weighted_sum, 0) as weighted_score
                FROM centrality_calc
            """, entity_id)
            
            if not centrality_data or centrality_data['connections'] == 0:
                centrality_score = 0.1  # Minimum score for isolated entities
            else:
                # PageRank-inspired calculation
                connections = centrality_data['connections']
                weighted_score = centrality_data['weighted_score']
                
                # Normalize based on connection count (more connections = higher base score)
                connection_factor = min(1.0, math.log(connections + 1) / math.log(21))  # Max at 20 connections
                
                # Weight by relationship strength and target importance
                weight_factor = min(1.0, weighted_score / connections) if connections > 0 else 0
                
                centrality_score = 0.1 + 0.9 * (connection_factor * 0.6 + weight_factor * 0.4)
            
            # Cache the result
            self.entity_cache[cache_key] = centrality_score
            self.last_cache_update = current_time
            
            return centrality_score
            
        except Exception as e:
            logger.warning(f"Centrality calculation failed for entity {entity_id}: {e}")
            return 0.5  # Neutral fallback
    
    async def _calculate_entity_relationship_strength(self, entity_id: UUID, conn) -> float:
        """Calculate the average strength of relationships involving this entity."""
        try:
            strength_data = await conn.fetchrow("""
                SELECT 
                    AVG(strength) as avg_strength,
                    COUNT(*) as relationship_count,
                    AVG(confidence) as avg_confidence
                FROM graph_relationships
                WHERE from_node_id = $1 OR to_node_id = $1
            """, entity_id)
            
            if not strength_data or strength_data['relationship_count'] == 0:
                return 0.2  # Low score for entities with no relationships
            
            avg_strength = strength_data['avg_strength']
            rel_count = strength_data['relationship_count']
            avg_confidence = strength_data['avg_confidence']
            
            # Boost entities with more high-quality relationships
            count_factor = min(1.0, rel_count / 10.0)  # Normalize to max 10 relationships
            quality_factor = (avg_strength + avg_confidence) / 2.0
            
            return count_factor * 0.4 + quality_factor * 0.6
            
        except Exception as e:
            logger.warning(f"Relationship strength calculation failed for entity {entity_id}: {e}")
            return 0.5
    
    def _calculate_temporal_relevance(self, last_seen_timestamp) -> float:
        """Calculate temporal relevance score based on how recently entity was seen."""
        if not last_seen_timestamp:
            return 0.3  # Neutral score for unknown timestamps
        
        try:
            import datetime
            
            # Calculate time since last seen
            now = datetime.datetime.utcnow()
            if hasattr(last_seen_timestamp, 'replace'):
                # PostgreSQL timestamp with timezone
                last_seen = last_seen_timestamp.replace(tzinfo=None)
            else:
                last_seen = last_seen_timestamp
            
            time_diff = (now - last_seen).total_seconds()
            days_ago = time_diff / (24 * 3600)
            
            # Exponential decay: recent entities get higher scores
            if days_ago <= 1:
                return 1.0  # Very recent
            elif days_ago <= 7:
                return 0.8  # This week
            elif days_ago <= 30:
                return 0.6  # This month
            elif days_ago <= 90:
                return 0.4  # Last 3 months
            else:
                return 0.2  # Older than 3 months
                
        except Exception as e:
            logger.warning(f"Temporal relevance calculation failed: {e}")
            return 0.5
    
    async def _calculate_network_strength(
        self, 
        entities: List[str], 
        memory_id: UUID
    ) -> float:
        """
        Calculate how well-connected the entities in this memory are to each other
        and to the broader knowledge graph.
        """
        if len(entities) < 2:
            return 0.3  # Single entity memories get neutral network score
        
        try:
            async with self.connection_pool.acquire() as conn:
                # Get entity IDs
                entity_ids = await conn.fetch("""
                    SELECT id, entity_name 
                    FROM graph_nodes 
                    WHERE entity_name = ANY($1)
                """, entities)
                
                if len(entity_ids) < 2:
                    return 0.3
                
                ids_list = [row['id'] for row in entity_ids]
                
                # Count internal connections (between entities in this memory)
                internal_connections = await conn.fetchval("""
                    SELECT COUNT(*)
                    FROM graph_relationships r
                    WHERE r.from_node_id = ANY($1) AND r.to_node_id = ANY($1)
                    AND r.from_node_id != r.to_node_id
                """, ids_list)
                
                # Count external connections (to entities not in this memory)
                external_connections = await conn.fetchval("""
                    SELECT COUNT(*)
                    FROM graph_relationships r
                    WHERE (r.from_node_id = ANY($1) AND r.to_node_id != ALL($1))
                       OR (r.to_node_id = ANY($1) AND r.from_node_id != ALL($1))
                """, ids_list)
                
                # Calculate network strength
                max_internal = len(entities) * (len(entities) - 1)  # Maximum possible internal connections
                internal_density = internal_connections / max_internal if max_internal > 0 else 0
                
                # Normalize external connections
                external_factor = min(1.0, external_connections / (len(entities) * 5))  # Assume avg 5 external connections per entity
                
                # Combine internal density and external connectivity
                network_strength = internal_density * 0.6 + external_factor * 0.4
                
                return min(1.0, network_strength)
                
        except Exception as e:
            logger.warning(f"Network strength calculation failed: {e}")
            return 0.5
    
    def _calculate_query_relevance(
        self, 
        memory_entities: List[str], 
        query_entities: List[str]
    ) -> float:
        """Calculate how relevant the memory entities are to the query entities."""
        if not query_entities or not memory_entities:
            return 0.5
        
        # Direct matches get highest score
        direct_matches = len(set(memory_entities) & set(query_entities))
        direct_match_score = direct_matches / len(query_entities)
        
        # Fuzzy matches (case-insensitive, substring matching)
        fuzzy_matches = 0
        for query_entity in query_entities:
            query_lower = query_entity.lower()
            for memory_entity in memory_entities:
                memory_lower = memory_entity.lower()
                if query_lower in memory_lower or memory_lower in query_lower:
                    fuzzy_matches += 0.5  # Half credit for fuzzy matches
                    break
        
        fuzzy_match_score = fuzzy_matches / len(query_entities)
        
        # Entity coverage (what percentage of memory entities are relevant)
        coverage_score = len(set(memory_entities) & set(query_entities)) / len(memory_entities) if memory_entities else 0
        
        # Combine scores
        relevance_score = (
            direct_match_score * 0.6 + 
            fuzzy_match_score * 0.3 + 
            coverage_score * 0.1
        )
        
        return min(1.0, relevance_score)
    
    async def _calculate_temporal_factor(self, memory_id: UUID) -> float:
        """Calculate temporal relevance factor for the memory itself."""
        try:
            async with self.connection_pool.acquire() as conn:
                # Get memory creation time from vector_memories table
                memory_data = await conn.fetchrow("""
                    SELECT created_at
                    FROM vector_memories
                    WHERE id = $1
                """, memory_id)
                
                if not memory_data or not memory_data['created_at']:
                    return 0.7  # Neutral score for unknown timestamps
                
                return self._calculate_temporal_relevance(memory_data['created_at'])
                
        except Exception as e:
            logger.warning(f"Temporal factor calculation failed for memory {memory_id}: {e}")
            return 0.7
    
    def _combine_graph_scores(
        self, 
        entity_scores: List[EntityScore],
        network_strength: float,
        query_relevance: float,
        temporal_factor: float
    ) -> float:
        """Combine all graph scoring components into final score."""
        if not entity_scores:
            return 0.3  # Minimum score for memories with no recognized entities
        
        # Average entity scores, weighted by their individual importance
        entity_score_sum = sum(score.combined_score for score in entity_scores)
        avg_entity_score = entity_score_sum / len(entity_scores)
        
        # Find the highest scoring entity (primary entity boost)
        max_entity_score = max(score.combined_score for score in entity_scores)
        
        # Combine all components
        final_score = (
            avg_entity_score * 0.4 +          # Average entity quality
            max_entity_score * 0.2 +          # Best entity boost
            network_strength * 0.2 +          # How well connected entities are
            query_relevance * 0.15 +          # Relevance to query
            temporal_factor * 0.05            # Recency factor
        )
        
        return min(1.0, final_score)
    
    async def calculate_graph_boost_factor(
        self,
        memory_id: UUID,
        extracted_entities: List[str],
        query_entities: List[str],
        vector_score: float
    ) -> float:
        """
        Calculate how much to boost the vector similarity score based on graph connections.
        
        Returns a multiplier (usually 1.0-2.0) to apply to the vector score.
        """
        try:
            # Get graph score details
            graph_data = await self.calculate_memory_graph_score(
                memory_id, extracted_entities, query_entities
            )
            
            graph_score = graph_data.get('graph_score', 0.5)
            query_relevance = graph_data.get('query_relevance', 0.5)
            
            # Calculate boost factor based on graph strength and query relevance
            if query_relevance > 0.8 and graph_score > 0.7:
                return 2.0  # Strong boost for highly relevant, well-connected memories
            elif query_relevance > 0.6 and graph_score > 0.6:
                return 1.7  # Good boost
            elif query_relevance > 0.4 and graph_score > 0.5:
                return 1.4  # Moderate boost
            elif graph_score > 0.4:
                return 1.2  # Small boost for decent graph connections
            else:
                return 1.0  # No boost for weak graph connections
                
        except Exception as e:
            logger.error(f"Graph boost calculation failed: {e}")
            return 1.0  # No boost on error
    
    async def get_scoring_statistics(self) -> Dict[str, Any]:
        """Get statistics about the graph scoring system performance."""
        try:
            async with self.connection_pool.acquire() as conn:
                stats = await conn.fetchrow("""
                    WITH entity_stats AS (
                        SELECT 
                            COUNT(*) as total_entities,
                            AVG(importance_score) as avg_importance,
                            AVG(mention_count) as avg_mentions
                        FROM graph_nodes
                    ),
                    relationship_stats AS (
                        SELECT 
                            COUNT(*) as total_relationships,
                            AVG(strength) as avg_strength,
                            AVG(confidence) as avg_confidence
                        FROM graph_relationships
                    )
                    SELECT 
                        e.total_entities,
                        e.avg_importance,
                        e.avg_mentions,
                        r.total_relationships,
                        r.avg_strength,
                        r.avg_confidence
                    FROM entity_stats e, relationship_stats r
                """)
                
                return {
                    "entities": {
                        "total": stats['total_entities'],
                        "avg_importance": float(stats['avg_importance'] or 0),
                        "avg_mentions": float(stats['avg_mentions'] or 0)
                    },
                    "relationships": {
                        "total": stats['total_relationships'],
                        "avg_strength": float(stats['avg_strength'] or 0),
                        "avg_confidence": float(stats['avg_confidence'] or 0)
                    },
                    "scoring_config": {
                        "centrality_weight": self.weights.centrality,
                        "relationship_weight": self.weights.relationship_strength,
                        "mention_weight": self.weights.mention_frequency,
                        "temporal_weight": self.weights.temporal_relevance,
                        "query_weight": self.weights.query_relevance
                    },
                    "cache_stats": {
                        "cached_entities": len(self.entity_cache),
                        "cache_age_seconds": time.time() - self.last_cache_update
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to get scoring statistics: {e}")
            return {"error": str(e)}