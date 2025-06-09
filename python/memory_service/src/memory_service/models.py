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