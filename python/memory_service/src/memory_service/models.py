"""
Memory Service Data Models

Unified data models for the Core Nexus Long Term Memory Module.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

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
    
    query: str = Field(..., description="Query text")
    limit: int = Field(10, ge=1, le=100, description="Maximum results to return")
    min_similarity: float = Field(0.7, ge=0.0, le=1.0, description="Minimum similarity threshold")
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