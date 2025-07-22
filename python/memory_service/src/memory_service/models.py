"""
Memory Service Data Models

Unified data models for the Core Nexus Long Term Memory Module.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4
try:
    from typing import UUID
except ImportError:
    from uuid import UUID

from pydantic import BaseModel, Field


class MemoryRequest(BaseModel):
    """Request model for storing memories."""
    
    content: str = Field(..., description="Text content to store")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    embedding: Optional[List[float]] = Field(None, description="Pre-computed embedding vector")
    importance_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Memory importance (0-1)")
    user_id: Optional[str] = Field(None, description="User identifier")
    conversation_id: Optional[str] = Field(None, description="Conversation identifier")
    

class MemoryResponse(BaseModel):
    """Response model for stored memories."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique memory identifier")
    content: str = Field(..., description="Stored content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")
    importance_score: float = Field(0.5, description="Calculated importance score")
    similarity_score: Optional[float] = Field(None, description="Similarity score (for queries)")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class QueryRequest(BaseModel):
    """Request model for querying memories."""
    
    query: str = Field("", description="Query text (empty returns all memories)")
    limit: int = Field(10, ge=1, le=100, description="Maximum results to return")
    min_similarity: float = Field(0.3, ge=0.0, le=1.0, description="Minimum similarity threshold")
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata filters")
    user_id: Optional[str] = Field(None, description="Filter by user")
    conversation_id: Optional[str] = Field(None, description="Filter by conversation")
    time_range: Optional[Dict[str, datetime]] = Field(None, description="Time range filter")
    providers: Optional[List[str]] = Field(None, description="Specific providers to query")


class QueryResponse(BaseModel):
    """Response model for memory queries."""
    
    memories: List[MemoryResponse] = Field(default_factory=list, description="Retrieved memories")
    total_found: int = Field(0, description="Total memories found")
    query_time_ms: float = Field(0.0, description="Query execution time in milliseconds")
    providers_used: List[str] = Field(default_factory=list, description="Vector providers queried")
    trust_metrics: Optional[Dict[str, Any]] = Field(None, description="Trust and confidence metrics")
    query_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional query metadata")


class HealthCheckResponse(BaseModel):
    """Response model for health checks."""
    
    status: str = Field(..., description="Overall health status")
    providers: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Provider health details")
    total_memories: int = Field(0, description="Total memories stored")
    avg_query_time_ms: float = Field(0.0, description="Average query time")
    uptime_seconds: float = Field(0.0, description="Service uptime")
    cache_type: str = Field("unknown", description="Cache type (redis/memory)")
    cache_size: int = Field(-1, description="Number of cached queries")


class ProviderConfig(BaseModel):
    """Configuration for vector providers."""
    
    name: str = Field(..., description="Provider name")
    enabled: bool = Field(True, description="Whether provider is enabled")
    primary: bool = Field(False, description="Whether this is the primary provider")
    config: Dict[str, Any] = Field(default_factory=dict, description="Provider-specific configuration")
    retry_count: int = Field(3, description="Number of retries on failure")
    timeout_seconds: float = Field(30.0, description="Request timeout")


class MemoryStats(BaseModel):
    """Memory service statistics."""
    
    total_memories: int = Field(0, description="Total memories stored")
    memories_by_provider: Dict[str, int] = Field(default_factory=dict, description="Memory count by provider")
    avg_importance_score: float = Field(0.0, description="Average importance score")
    most_recent_memory: Optional[datetime] = Field(None, description="Most recent memory timestamp")
    queries_last_hour: int = Field(0, description="Queries in last hour")
    avg_query_time_ms: float = Field(0.0, description="Average query time")


class TemporalQuery(BaseModel):
    """Temporal query model leveraging existing partition strategy."""
    
    query: str = Field(..., description="Query text")
    start_time: datetime = Field(..., description="Query start time")
    end_time: datetime = Field(..., description="Query end time") 
    limit: int = Field(10, ge=1, le=100, description="Maximum results")
    partition_strategy: str = Field("auto", description="Partition selection strategy")
    include_summary: bool = Field(False, description="Include conversation summaries")


class ImportanceScoring(BaseModel):
    """Model for memory importance calculation."""
    
    content_length_weight: float = Field(0.2, description="Weight for content length")
    recency_weight: float = Field(0.3, description="Weight for recency")
    interaction_weight: float = Field(0.3, description="Weight for user interactions")
    semantic_weight: float = Field(0.2, description="Weight for semantic uniqueness")
    min_score: float = Field(0.1, description="Minimum importance score")
    max_score: float = Field(1.0, description="Maximum importance score")


# =====================================================
# KNOWLEDGE GRAPH MODELS (Added by Agent 2)
# =====================================================

class EntityType(str):
    """Valid entity types for knowledge graph."""
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    CONCEPT = "concept"
    EVENT = "event"
    PRODUCT = "product"
    TECHNOLOGY = "technology"
    OTHER = "other"


class RelationshipType(str):
    """Valid relationship types for knowledge graph."""
    RELATES_TO = "relates_to"
    MENTIONS = "mentions"
    CAUSED_BY = "caused_by"
    PART_OF = "part_of"
    WORKS_WITH = "works_with"
    LOCATED_IN = "located_in"
    CREATED_BY = "created_by"
    USED_BY = "used_by"
    SIMILAR_TO = "similar_to"
    PRECEDES = "precedes"
    FOLLOWS = "follows"


class GraphNode(BaseModel):
    """Model for knowledge graph nodes (entities)."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique entity identifier")
    entity_type: str = Field(..., description="Type of entity")
    entity_name: str = Field(..., description="Normalized name of entity")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Additional properties")
    embedding: Optional[List[float]] = Field(None, description="Entity embedding vector")
    importance_score: float = Field(0.5, description="ADM-scored importance")
    mention_count: int = Field(1, description="Number of mentions across memories")
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)


class GraphRelationship(BaseModel):
    """Model for relationships between entities."""
    
    id: UUID = Field(default_factory=uuid4)
    from_node_id: UUID = Field(..., description="Source entity ID")
    to_node_id: UUID = Field(..., description="Target entity ID")
    relationship_type: str = Field(..., description="Type of relationship")
    strength: float = Field(0.5, description="ADM-scored relationship strength")
    confidence: float = Field(0.5, description="Extraction confidence")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    occurrence_count: int = Field(1, description="How often this relationship appears")
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)


class EntityExtraction(BaseModel):
    """Model for extracted entities from memory content."""
    
    entity_name: str = Field(..., description="Extracted entity name")
    entity_type: str = Field(..., description="Detected entity type")
    position_start: int = Field(..., description="Character position start in content")
    position_end: int = Field(..., description="Character position end in content")
    confidence: float = Field(..., description="Extraction confidence score")
    context: Optional[str] = Field(None, description="Surrounding context")


class GraphQuery(BaseModel):
    """Request model for graph queries."""
    
    entity_name: Optional[str] = Field(None, description="Query by entity name")
    entity_type: Optional[str] = Field(None, description="Filter by entity type")
    relationship_type: Optional[str] = Field(None, description="Filter by relationship type")
    max_depth: int = Field(3, ge=1, le=5, description="Maximum traversal depth")
    limit: int = Field(20, ge=1, le=100, description="Maximum results")
    min_strength: float = Field(0.3, ge=0.0, le=1.0, description="Minimum relationship strength")
    include_properties: bool = Field(True, description="Include entity properties")


class GraphResponse(BaseModel):
    """Response model for graph queries."""
    
    nodes: List[GraphNode] = Field(default_factory=list, description="Graph nodes")
    relationships: List[GraphRelationship] = Field(default_factory=list, description="Graph relationships")
    query_time_ms: float = Field(0.0, description="Query execution time")
    total_nodes: int = Field(0, description="Total nodes found")
    total_relationships: int = Field(0, description="Total relationships found")


class EntityInsights(BaseModel):
    """Insights about an entity from the knowledge graph."""
    
    entity: GraphNode = Field(..., description="The entity")
    memory_count: int = Field(0, description="Number of memories mentioning this entity")
    relationship_count: int = Field(0, description="Number of relationships")
    top_relationships: List[GraphRelationship] = Field(default_factory=list, description="Most important relationships")
    co_occurring_entities: List[GraphNode] = Field(default_factory=list, description="Frequently co-occurring entities")
    temporal_pattern: Optional[Dict[str, Any]] = Field(None, description="When entity appears over time")
    importance_trend: Optional[List[float]] = Field(None, description="Importance score over time")


# =====================================================
# GRAPH-AWARE RETRIEVAL MODELS (Phase 1.1)
# =====================================================

class EvidenceChain(BaseModel):
    """Evidence chain showing how a result connects to the query through the knowledge graph."""
    
    path: List[str] = Field(..., description="Entity names in connection path")
    relationship_types: List[str] = Field(..., description="Relationship types in path")
    strength: float = Field(..., description="Combined relationship strength (0-1)")
    confidence: float = Field(..., description="Combined confidence score (0-1)")
    reasoning: str = Field(..., description="Human-readable explanation of connection")
    hop_count: int = Field(..., description="Number of hops in the path")


class GraphConnection(BaseModel):
    """Information about graph connections for a result."""
    
    connected_entities: List[str] = Field(default_factory=list, description="Entities found in this result")
    relationship_count: int = Field(0, description="Total relationships involving these entities")
    centrality_score: float = Field(0.0, description="Graph centrality score for main entities")
    cluster_id: Optional[str] = Field(None, description="Graph cluster/community ID")


class EnhancedMemoryResponse(MemoryResponse):
    """Enhanced memory response with graph awareness."""
    
    # Inherit all fields from MemoryResponse
    evidence_chains: List[EvidenceChain] = Field(default_factory=list, description="Paths connecting query to this result")
    graph_connections: GraphConnection = Field(default_factory=GraphConnection, description="Graph connectivity info")
    graph_boost_factor: float = Field(1.0, description="Factor by which graph enhanced the score")
    connection_strength: Optional[float] = Field(None, description="Strength of connection to query entities")
    
    class Config:
        # Allow this model to inherit from MemoryResponse while adding fields
        arbitrary_types_allowed = True


class GraphAwareQueryRequest(QueryRequest):
    """Enhanced query request with graph-aware options."""
    
    # Inherit all fields from QueryRequest
    enable_graph_retrieval: bool = Field(True, description="Enable graph-enhanced retrieval")
    max_evidence_chains: int = Field(3, ge=0, le=10, description="Maximum evidence chains per result")
    max_traversal_depth: int = Field(3, ge=1, le=5, description="Maximum graph traversal depth")
    graph_weight: float = Field(0.3, ge=0.0, le=1.0, description="Weight of graph score vs vector score")
    require_entity_match: bool = Field(False, description="Only return results with entity matches")
    boost_connected_results: bool = Field(True, description="Boost results with strong graph connections")


class GraphAwareQueryResponse(QueryResponse):
    """Enhanced query response with graph awareness and evidence chains."""
    
    # Inherit all QueryResponse fields, but override memories type
    memories: List[EnhancedMemoryResponse] = Field(default_factory=list, description="Retrieved memories with graph enhancements")
    
    # Additional graph-aware fields
    extracted_entities: List[str] = Field(default_factory=list, description="Entities extracted from query")
    graph_enabled: bool = Field(False, description="Whether graph enhancement was used")
    related_entities: List[GraphNode] = Field(default_factory=list, description="Related entities found during search")
    entity_coverage: float = Field(0.0, description="% of results with entity connections")
    average_evidence_chains: float = Field(0.0, description="Average evidence chains per result")
    graph_query_time_ms: float = Field(0.0, description="Time spent on graph operations")
    
    # Connection map showing relationships between query entities and result entities
    entity_connections: Dict[str, List[str]] = Field(default_factory=dict, description="Map of entity connections")


class PathFindingRequest(BaseModel):
    """Request model for finding paths between entities."""
    
    from_entity: str = Field(..., description="Starting entity name")
    to_entity: str = Field(..., description="Target entity name")
    max_depth: int = Field(3, ge=1, le=5, description="Maximum path depth")
    include_indirect: bool = Field(True, description="Include indirect paths")
    min_strength: float = Field(0.3, ge=0.0, le=1.0, description="Minimum relationship strength")


class PathFindingResponse(BaseModel):
    """Response model for path finding between entities."""
    
    from_entity: str = Field(..., description="Starting entity")
    to_entity: str = Field(..., description="Target entity")
    path_found: bool = Field(..., description="Whether a path was found")
    paths: List[EvidenceChain] = Field(default_factory=list, description="Found paths (shortest first)")
    total_paths: int = Field(0, description="Total number of paths found")
    query_time_ms: float = Field(0.0, description="Path finding execution time")
    max_depth_reached: int = Field(0, description="Maximum depth explored")


class MemoryInsightsResponse(BaseModel):
    """Response model for memory-specific graph insights."""
    
    memory_id: UUID = Field(..., description="Memory identifier")
    extracted_entities: List[EntityExtraction] = Field(default_factory=list, description="Entities found in memory")
    entity_relationships: List[GraphRelationship] = Field(default_factory=list, description="Relationships between entities")
    connected_memories: List[UUID] = Field(default_factory=list, description="Related memories through shared entities")
    graph_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary statistics")
    evidence_chains_to_key_entities: List[EvidenceChain] = Field(default_factory=list, description="Chains to important entities")