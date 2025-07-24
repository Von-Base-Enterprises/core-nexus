"""
Graph Traversal Engine

Implements breadth-first search (BFS) and advanced graph traversal algorithms
for multi-hop path finding and evidence chain generation.
"""

import asyncio
import logging
import time
from collections import deque, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from .models import EvidenceChain

logger = logging.getLogger(__name__)


@dataclass
class GraphTraversalSafetyConfig:
    """Safety configuration for graph traversal to prevent path explosion."""
    max_search_depth: int = 3  # Reduced from 5 to limit explosion
    max_nodes_per_level: int = 25  # Reduced from 50 to prevent memory issues
    max_paths_per_query: int = 5  # Limit number of paths returned
    max_evidence_chains: int = 10  # Limit evidence chains per query
    traversal_timeout_seconds: float = 5.0  # Timeout for path finding
    cache_size_limit: int = 500  # Limit cache size
    min_strength_threshold: float = 0.3  # Filter weak relationships


@dataclass
class GraphPath:
    """Represents a path through the knowledge graph."""
    entities: List[str]
    relationships: List[str]
    entity_ids: List[UUID]
    total_strength: float
    total_confidence: float
    hop_count: int
    path_score: float


@dataclass
class PathFindingResult:
    """Result of path finding between two entities."""
    from_entity: str
    to_entity: str
    paths_found: List[GraphPath]
    search_depth_reached: int
    total_nodes_explored: int
    execution_time_ms: float
    success: bool


class GraphTraversalEngine:
    """
    Advanced graph traversal engine for finding paths between entities
    and generating evidence chains with sophisticated scoring.
    """
    
    def __init__(self, connection_pool, safety_config: Optional[GraphTraversalSafetyConfig] = None):
        self.connection_pool = connection_pool
        self.safety_config = safety_config or GraphTraversalSafetyConfig()
        self.max_search_depth = self.safety_config.max_search_depth
        self.max_nodes_per_level = self.safety_config.max_nodes_per_level
        self.path_cache = {}  # Cache for frequently requested paths
        self.cache_expiry_time = 600  # 10 minutes cache
        
        # Performance tracking
        self.cache_hits = 0
        self.cache_misses = 0
        self.traversal_timeouts = 0
    
    async def find_shortest_paths(
        self,
        from_entity: str,
        to_entity: str,
        max_depth: int = 3,
        max_paths: int = 5,
        min_strength: float = 0.3
    ) -> PathFindingResult:
        """
        Find shortest paths between two entities using BFS.
        
        Returns multiple path options ranked by strength and relevance.
        """
        start_time = time.time()
        
        try:
            # Check cache first
            cache_key = f"{from_entity}->{to_entity}:{max_depth}:{min_strength}"
            if cache_key in self.path_cache:
                cached_result, cache_time = self.path_cache[cache_key]
                if time.time() - cache_time < self.cache_expiry_time:
                    logger.info(f"Returning cached path for {from_entity} -> {to_entity}")
                    return cached_result
            
            # Get entity IDs
            async with self.connection_pool.acquire() as conn:
                entity_data = await conn.fetch("""
                    SELECT id, entity_name 
                    FROM graph_nodes 
                    WHERE entity_name IN ($1, $2)
                """, from_entity, to_entity)
                
                if len(entity_data) != 2:
                    return PathFindingResult(
                        from_entity=from_entity,
                        to_entity=to_entity,
                        paths_found=[],
                        search_depth_reached=0,
                        total_nodes_explored=0,
                        execution_time_ms=(time.time() - start_time) * 1000,
                        success=False
                    )
                
                entity_map = {row['entity_name']: row['id'] for row in entity_data}
                from_id = entity_map[from_entity]
                to_id = entity_map[to_entity]
                
                # Perform BFS to find paths with timeout protection
                try:
                    paths = await asyncio.wait_for(
                        self._bfs_find_paths(
                            conn, from_id, to_id, from_entity, to_entity, 
                            max_depth, max_paths, min_strength
                        ),
                        timeout=self.safety_config.traversal_timeout_seconds
                    )
                except asyncio.TimeoutError:
                    self.traversal_timeouts += 1
                    logger.warning(f"Path finding timeout for {from_entity} -> {to_entity} after {self.safety_config.traversal_timeout_seconds}s")
                    return PathFindingResult(
                        from_entity=from_entity,
                        to_entity=to_entity,
                        paths_found=[],
                        search_depth_reached=max_depth,
                        total_nodes_explored=0,
                        execution_time_ms=self.safety_config.traversal_timeout_seconds * 1000,
                        success=False
                    )
                
                # Calculate statistics
                total_nodes_explored = await self._count_nodes_in_depth(conn, from_id, max_depth)
                
                result = PathFindingResult(
                    from_entity=from_entity,
                    to_entity=to_entity,
                    paths_found=paths,
                    search_depth_reached=max_depth if paths else 0,
                    total_nodes_explored=total_nodes_explored,
                    execution_time_ms=(time.time() - start_time) * 1000,
                    success=bool(paths)
                )
                
                # Cache the result with size management
                if len(self.path_cache) >= self.safety_config.cache_size_limit:
                    # Remove oldest entries
                    oldest_keys = sorted(self.path_cache.keys(), key=lambda k: self.path_cache[k][1])[:10]
                    for old_key in oldest_keys:
                        del self.path_cache[old_key]
                        
                self.path_cache[cache_key] = (result, time.time())
                
                return result
                
        except Exception as e:
            logger.error(f"Path finding failed from {from_entity} to {to_entity}: {e}")
            return PathFindingResult(
                from_entity=from_entity,
                to_entity=to_entity,
                paths_found=[],
                search_depth_reached=0,
                total_nodes_explored=0,
                execution_time_ms=(time.time() - start_time) * 1000,
                success=False
            )
    
    async def _bfs_find_paths(
        self,
        conn,
        from_id: UUID,
        to_id: UUID,
        from_name: str,
        to_name: str,
        max_depth: int,
        max_paths: int,
        min_strength: float
    ) -> List[GraphPath]:
        """
        Core BFS implementation for finding paths between entities.
        """
        # Queue stores: (current_node_id, path_entities, path_relationships, path_ids, total_strength, total_confidence, depth)
        queue = deque([(from_id, [from_name], [], [from_id], 1.0, 1.0, 0)])
        visited = set([from_id])
        found_paths = []
        
        while queue and len(found_paths) < max_paths:
            current_id, path_entities, path_relationships, path_ids, total_strength, total_confidence, depth = queue.popleft()
            
            if depth >= max_depth:
                continue
            
            # Get all neighbors of current node
            neighbors = await conn.fetch("""
                SELECT 
                    CASE 
                        WHEN r.from_node_id = $1 THEN r.to_node_id
                        ELSE r.from_node_id
                    END as neighbor_id,
                    CASE 
                        WHEN r.from_node_id = $1 THEN tn.entity_name
                        ELSE fn.entity_name
                    END as neighbor_name,
                    r.relationship_type,
                    r.strength,
                    r.confidence
                FROM graph_relationships r
                JOIN graph_nodes fn ON r.from_node_id = fn.id
                JOIN graph_nodes tn ON r.to_node_id = tn.id
                WHERE (r.from_node_id = $1 OR r.to_node_id = $1)
                AND r.strength >= $2
                ORDER BY r.strength DESC
                LIMIT $3
            """, current_id, min_strength, self.max_nodes_per_level)
            
            for neighbor in neighbors:
                neighbor_id = neighbor['neighbor_id']
                neighbor_name = neighbor['neighbor_name']
                rel_type = neighbor['relationship_type']
                strength = neighbor['strength']
                confidence = neighbor['confidence']
                
                # Skip if we've already visited this node in this path
                if neighbor_id in path_ids:
                    continue
                
                # Calculate new path metrics
                new_strength = total_strength * strength
                new_confidence = total_confidence * confidence
                new_path_entities = path_entities + [neighbor_name]
                new_path_relationships = path_relationships + [rel_type]
                new_path_ids = path_ids + [neighbor_id]
                
                # Check if we've reached the target
                if neighbor_id == to_id:
                    path_score = self._calculate_path_score(
                        new_strength, new_confidence, depth + 1, new_path_entities
                    )
                    
                    found_paths.append(GraphPath(
                        entities=new_path_entities,
                        relationships=new_path_relationships,
                        entity_ids=new_path_ids,
                        total_strength=new_strength,
                        total_confidence=new_confidence,
                        hop_count=depth + 1,
                        path_score=path_score
                    ))
                    continue
                
                # Add to queue for further exploration
                if depth + 1 < max_depth:
                    queue.append((
                        neighbor_id, new_path_entities, new_path_relationships, 
                        new_path_ids, new_strength, new_confidence, depth + 1
                    ))
                    visited.add(neighbor_id)
        
        # Sort paths by score (best first)
        found_paths.sort(key=lambda p: p.path_score, reverse=True)
        
        return found_paths[:max_paths]
    
    def _calculate_path_score(
        self,
        total_strength: float,
        total_confidence: float,
        hop_count: int,
        entities: List[str]
    ) -> float:
        """
        Calculate a comprehensive score for a path considering multiple factors.
        """
        # Base score from relationship strength and confidence
        strength_score = total_strength
        confidence_score = total_confidence
        
        # Penalty for longer paths (prefer shorter paths)
        length_penalty = 1.0 / (1.0 + 0.2 * hop_count)
        
        # Bonus for paths through important entities (simple heuristic)
        importance_bonus = 1.0
        for entity in entities:
            if any(keyword in entity.lower() for keyword in ['system', 'core', 'main', 'primary']):
                importance_bonus += 0.1
        
        # Combine all factors
        path_score = (
            strength_score * 0.4 +
            confidence_score * 0.3 +
            length_penalty * 0.2 +
            min(importance_bonus, 1.2) * 0.1
        )
        
        return min(1.0, path_score)
    
    async def generate_evidence_chains_bfs(
        self,
        memory_entities: List[str],
        query_entities: List[str],
        max_chains: int = 3,
        max_depth: int = 2
    ) -> List[EvidenceChain]:
        """
        Generate evidence chains using BFS to show how memory entities
        connect to query entities through the knowledge graph.
        """
        evidence_chains = []
        
        if not memory_entities or not query_entities:
            return evidence_chains
        
        try:
            # Find paths from each query entity to each memory entity
            for query_entity in query_entities[:3]:  # Limit query entities to prevent explosion
                for memory_entity in memory_entities[:5]:  # Limit memory entities
                    if query_entity.lower() == memory_entity.lower():
                        # Direct match - create immediate evidence chain
                        evidence_chains.append(EvidenceChain(
                            path=[query_entity],
                            relationship_types=[],
                            strength=1.0,
                            confidence=1.0,
                            reasoning=f"Direct mention of '{query_entity}' found in memory",
                            hop_count=0
                        ))
                    else:
                        # Find path using BFS
                        path_result = await self.find_shortest_paths(
                            query_entity, memory_entity, max_depth, 1, 0.4
                        )
                        
                        if path_result.success and path_result.paths_found:
                            best_path = path_result.paths_found[0]
                            
                            # Convert to evidence chain
                            evidence_chains.append(EvidenceChain(
                                path=best_path.entities,
                                relationship_types=best_path.relationships,
                                strength=best_path.total_strength,
                                confidence=best_path.total_confidence,
                                reasoning=self._generate_reasoning(best_path),
                                hop_count=best_path.hop_count
                            ))
                    
                    # Stop if we have enough chains
                    if len(evidence_chains) >= max_chains:
                        break
                
                if len(evidence_chains) >= max_chains:
                    break
            
            # Sort by strength and confidence
            evidence_chains.sort(key=lambda e: e.strength * e.confidence, reverse=True)
            
            return evidence_chains[:max_chains]
            
        except Exception as e:
            logger.error(f"Evidence chain generation failed: {e}")
            return evidence_chains
    
    def _generate_reasoning(self, path: GraphPath) -> str:
        """Generate human-readable reasoning for a path."""
        if path.hop_count == 0:
            return f"Direct mention of '{path.entities[0]}'"
        elif path.hop_count == 1:
            return f"'{path.entities[0]}' {path.relationships[0]} '{path.entities[1]}'"
        else:
            # Multi-hop reasoning
            reasoning_parts = []
            for i in range(len(path.relationships)):
                reasoning_parts.append(f"'{path.entities[i]}' {path.relationships[i]} '{path.entities[i+1]}'")
            
            return f"Connection path: {' → '.join(reasoning_parts)}"
    
    async def find_entity_neighborhood(
        self,
        entity_name: str,
        depth: int = 2,
        max_neighbors: int = 20,
        min_strength: float = 0.3
    ) -> Dict[str, Any]:
        """
        Find all entities within a certain depth of a given entity.
        Returns neighborhood information for visualization.
        """
        try:
            async with self.connection_pool.acquire() as conn:
                # Get starting entity
                entity_data = await conn.fetchrow("""
                    SELECT id, entity_type, importance_score
                    FROM graph_nodes
                    WHERE entity_name = $1
                """, entity_name)
                
                if not entity_data:
                    return {
                        "center_entity": entity_name,
                        "neighbors": [],
                        "relationships": [],
                        "depth_reached": 0,
                        "total_neighbors": 0
                    }
                
                center_id = entity_data['id']
                
                # BFS to find neighborhood
                visited = set([center_id])
                neighbors_by_depth = {0: [entity_data]}
                all_relationships = []
                
                current_level = [center_id]
                
                for current_depth in range(depth):
                    if not current_level:
                        break
                    
                    next_level = []
                    
                    # Get all neighbors of current level entities
                    level_relationships = await conn.fetch("""
                        SELECT DISTINCT
                            r.from_node_id,
                            r.to_node_id,
                            r.relationship_type,
                            r.strength,
                            r.confidence,
                            fn.entity_name as from_name,
                            fn.entity_type as from_type,
                            tn.entity_name as to_name,
                            tn.entity_type as to_type,
                            tn.importance_score
                        FROM graph_relationships r
                        JOIN graph_nodes fn ON r.from_node_id = fn.id
                        JOIN graph_nodes tn ON r.to_node_id = tn.id
                        WHERE (r.from_node_id = ANY($1) OR r.to_node_id = ANY($1))
                        AND r.strength >= $2
                        ORDER BY r.strength DESC
                        LIMIT $3
                    """, current_level, min_strength, max_neighbors * 2)
                    
                    depth_neighbors = []
                    
                    for rel in level_relationships:
                        # Determine which entity is the new neighbor
                        if rel['from_node_id'] in current_level:
                            neighbor_id = rel['to_node_id']
                            neighbor_data = {
                                'id': neighbor_id,
                                'entity_name': rel['to_name'],
                                'entity_type': rel['to_type'],
                                'importance_score': rel['importance_score']
                            }
                        else:
                            neighbor_id = rel['from_node_id']
                            neighbor_data = {
                                'id': neighbor_id,
                                'entity_name': rel['from_name'],
                                'entity_type': rel['from_type'],
                                'importance_score': rel.get('from_importance', 0.5)  # Fallback
                            }
                        
                        # Add relationship info
                        all_relationships.append({
                            'from': rel['from_name'],
                            'to': rel['to_name'],
                            'type': rel['relationship_type'],
                            'strength': float(rel['strength']),
                            'confidence': float(rel['confidence'])
                        })
                        
                        # Add new neighbors for next level
                        if neighbor_id not in visited:
                            visited.add(neighbor_id)
                            next_level.append(neighbor_id)
                            depth_neighbors.append(neighbor_data)
                    
                    if depth_neighbors:
                        neighbors_by_depth[current_depth + 1] = depth_neighbors
                    
                    current_level = next_level
                    
                    if len(next_level) > max_neighbors:
                        # Trim to most important neighbors
                        sorted_neighbors = sorted(depth_neighbors, 
                                                key=lambda n: n['importance_score'], reverse=True)
                        neighbors_by_depth[current_depth + 1] = sorted_neighbors[:max_neighbors]
                        current_level = [n['id'] for n in sorted_neighbors[:max_neighbors]]
                
                # Flatten neighbors
                all_neighbors = []
                for depth_level, neighbors in neighbors_by_depth.items():
                    if depth_level > 0:  # Exclude center entity
                        for neighbor in neighbors:
                            all_neighbors.append({
                                'entity_name': neighbor['entity_name'],
                                'entity_type': neighbor['entity_type'],
                                'importance_score': float(neighbor['importance_score']),
                                'depth': depth_level
                            })
                
                return {
                    "center_entity": entity_name,
                    "neighbors": all_neighbors,
                    "relationships": all_relationships,
                    "depth_reached": len(neighbors_by_depth) - 1,
                    "total_neighbors": len(all_neighbors)
                }
                
        except Exception as e:
            logger.error(f"Neighborhood search failed for {entity_name}: {e}")
            return {
                "center_entity": entity_name,
                "neighbors": [],
                "relationships": [],
                "depth_reached": 0,
                "total_neighbors": 0,
                "error": str(e)
            }
    
    async def _count_nodes_in_depth(self, conn, start_id: UUID, depth: int) -> int:
        """Count total nodes reachable within given depth (for statistics)."""
        try:
            visited = set([start_id])
            current_level = [start_id]
            
            for _ in range(depth):
                if not current_level:
                    break
                
                neighbors = await conn.fetch("""
                    SELECT DISTINCT
                        CASE 
                            WHEN r.from_node_id = ANY($1) THEN r.to_node_id
                            ELSE r.from_node_id
                        END as neighbor_id
                    FROM graph_relationships r
                    WHERE (r.from_node_id = ANY($1) OR r.to_node_id = ANY($1))
                    AND (CASE 
                            WHEN r.from_node_id = ANY($1) THEN r.to_node_id
                            ELSE r.from_node_id
                        END) != ALL($1)
                """, current_level)
                
                next_level = []
                for neighbor in neighbors:
                    neighbor_id = neighbor['neighbor_id']
                    if neighbor_id not in visited:
                        visited.add(neighbor_id)
                        next_level.append(neighbor_id)
                
                current_level = next_level
            
            return len(visited)
            
        except Exception as e:
            logger.warning(f"Failed to count reachable nodes: {e}")
            return 0
    
    async def get_traversal_statistics(self) -> Dict[str, Any]:
        """Get statistics about graph traversal performance and cache usage."""
        try:
            cache_stats = {
                "cached_paths": len(self.path_cache),
                "cache_hit_ratio": "N/A",  # Would need to track hits/misses
                "max_search_depth": self.max_search_depth,
                "max_nodes_per_level": self.max_nodes_per_level
            }
            
            # Clean expired cache entries
            current_time = time.time()
            expired_keys = [
                key for key, (_, cache_time) in self.path_cache.items()
                if current_time - cache_time > self.cache_expiry_time
            ]
            
            for key in expired_keys:
                del self.path_cache[key]
            
            cache_stats["expired_entries_cleaned"] = len(expired_keys)
            
            return {
                "cache_stats": cache_stats,
                "algorithm_config": {
                    "traversal_method": "breadth_first_search",
                    "path_scoring": "strength_confidence_weighted",
                    "cycle_detection": "enabled",
                    "max_paths_per_query": 5
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get traversal statistics: {e}")
            return {"error": str(e)}