"""
Memory Service Data Models

Unified data models for the Core Nexus Long Term Memory Module.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

try:
    from typing import UUID
except ImportError:
    from uuid import UUID

from pydantic import BaseModel, Field


class MemoryRequest(BaseModel):
    """Request model for storing memories."""

    content: str = Field(..., description="Text content to store")
    metadata: dict[str, Any] | None = Field(default_factory=dict, description="Additional metadata")
    embedding: list[float] | None = Field(None, description="Pre-computed embedding vector")
    importance_score: float | None = Field(None, ge=0.0, le=1.0, description="Memory importance (0-1)")
    user_id: str | None = Field(None, description="User identifier")
    conversation_id: str | None = Field(None, description="Conversation identifier")


class MemoryResponse(BaseModel):
    """Response model for stored memories."""

    id: UUID = Field(default_factory=uuid4, description="Unique memory identifier")
    content: str = Field(..., description="Stored content")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata")
    importance_score: float = Field(0.5, description="Calculated importance score")
    similarity_score: float | None = Field(None, description="Similarity score (for queries)")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")


class QueryRequest(BaseModel):
    """Request model for querying memories."""

    query: str = Field("", description="Query text (empty returns all memories)")
    limit: int = Field(10, ge=1, le=100, description="Maximum results to return")
    min_similarity: float = Field(0.3, ge=0.0, le=1.0, description="Minimum similarity threshold")
    filters: dict[str, Any] | None = Field(None, description="Metadata filters")
    user_id: str | None = Field(None, description="Filter by user")
    conversation_id: str | None = Field(None, description="Filter by conversation")
    time_range: dict[str, datetime] | None = Field(None, description="Time range filter")
    providers: list[str] | None = Field(None, description="Specific providers to query")
    include_reasoning: bool = Field(False, description="Include JARVIS reasoning analysis")


class QueryResponse(BaseModel):
    """Response model for memory queries."""

    memories: list[MemoryResponse] = Field(default_factory=list, description="Retrieved memories")
    total_found: int = Field(0, description="Total memories found")
    query_time_ms: float = Field(0.0, description="Query execution time in milliseconds")
    providers_used: list[str] = Field(default_factory=list, description="Vector providers queried")
    trust_metrics: dict[str, Any] | None = Field(None, description="Trust and confidence metrics")
    query_metadata: dict[str, Any] | None = Field(None, description="Additional query metadata")
    reasoning_analysis: dict[str, Any] | None = Field(None, description="JARVIS reasoning analysis")


class HealthCheckResponse(BaseModel):
    """Response model for health checks."""

    status: str = Field(..., description="Overall health status")
    providers: dict[str, dict[str, Any]] = Field(default_factory=dict, description="Provider health details")
    total_memories: int = Field(0, description="Total memories stored")
    avg_query_time_ms: float = Field(0.0, description="Average query time")
    uptime_seconds: float = Field(0.0, description="Service uptime")


class ProviderConfig(BaseModel):
    """Configuration for vector providers."""

    name: str = Field(..., description="Provider name")
    enabled: bool = Field(True, description="Whether provider is enabled")
    primary: bool = Field(False, description="Whether this is the primary provider")
    config: dict[str, Any] = Field(default_factory=dict, description="Provider-specific configuration")
    retry_count: int = Field(3, description="Number of retries on failure")
    timeout_seconds: float = Field(30.0, description="Request timeout")


class MemoryStats(BaseModel):
    """Memory service statistics."""

    total_memories: int = Field(0, description="Total memories stored")
    memories_by_provider: dict[str, int] = Field(default_factory=dict, description="Memory count by provider")
    avg_importance_score: float = Field(0.0, description="Average importance score")
    most_recent_memory: datetime | None = Field(None, description="Most recent memory timestamp")
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
    properties: dict[str, Any] = Field(default_factory=dict, description="Additional properties")
    embedding: list[float] | None = Field(None, description="Entity embedding vector")
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
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional context")
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
    context: str | None = Field(None, description="Surrounding context")


class GraphQuery(BaseModel):
    """Request model for graph queries."""

    entity_name: str | None = Field(None, description="Query by entity name")
    entity_type: str | None = Field(None, description="Filter by entity type")
    relationship_type: str | None = Field(None, description="Filter by relationship type")
    max_depth: int = Field(3, ge=1, le=5, description="Maximum traversal depth")
    limit: int = Field(20, ge=1, le=100, description="Maximum results")
    min_strength: float = Field(0.3, ge=0.0, le=1.0, description="Minimum relationship strength")
    include_properties: bool = Field(True, description="Include entity properties")


class GraphResponse(BaseModel):
    """Response model for graph queries."""

    nodes: list[GraphNode] = Field(default_factory=list, description="Graph nodes")
    relationships: list[GraphRelationship] = Field(default_factory=list, description="Graph relationships")
    query_time_ms: float = Field(0.0, description="Query execution time")
    total_nodes: int = Field(0, description="Total nodes found")
    total_relationships: int = Field(0, description="Total relationships found")


class EntityInsights(BaseModel):
    """Insights about an entity from the knowledge graph."""

    entity: GraphNode = Field(..., description="The entity")
    memory_count: int = Field(0, description="Number of memories mentioning this entity")
    relationship_count: int = Field(0, description="Number of relationships")
    top_relationships: list[GraphRelationship] = Field(default_factory=list, description="Most important relationships")
    co_occurring_entities: list[GraphNode] = Field(default_factory=list, description="Frequently co-occurring entities")
    temporal_pattern: dict[str, Any] | None = Field(None, description="When entity appears over time")
    importance_trend: list[float] | None = Field(None, description="Importance score over time")


# =====================================================
# AGENT COORDINATION MODELS (Added by Intelligent Coordination Engine)
# =====================================================

class AgentStatus(str):
    """Valid agent status values."""
    IDLE = "idle"
    WORKING = "working"
    WAITING = "waiting"
    BLOCKED = "blocked"
    ERROR = "error"
    OFFLINE = "offline"


class AgentType(str):
    """Valid agent type categories."""
    MEMORY_AGENT = "memory_agent"
    JARVIS_AGENT = "jarvis_agent"
    PERFORMANCE_AGENT = "performance_agent"
    OBSERVABILITY_AGENT = "observability_agent"
    TESTING_AGENT = "testing_agent"
    QA_AGENT = "qa_agent"
    INTEGRATION_AGENT = "integration_agent"
    HOTFIX_AGENT = "hotfix_agent"
    AUTO_DEPLOY_AGENT = "auto_deploy_agent"


class WorkspaceType(str):
    """Valid workspace categories."""
    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"
    COMPONENT = "component"
    SUPPORT = "support"


class AgentProfile(BaseModel):
    """Agent profile and capabilities."""

    agent_id: str = Field(..., description="Unique agent identifier")
    agent_name: str = Field(..., description="Human-readable agent name")
    agent_type: str = Field(..., description="Agent type category")
    workspace: str = Field(..., description="Primary workspace/worktree")
    workspace_type: str = Field(..., description="Workspace safety level")
    capabilities: list[str] = Field(default_factory=list, description="Agent capabilities")
    max_concurrent_tasks: int = Field(3, description="Maximum concurrent tasks")
    preferred_components: list[str] = Field(default_factory=list, description="Preferred components to work on")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    total_tasks_completed: int = Field(0, description="Lifetime task completion count")
    success_rate: float = Field(1.0, description="Task success rate (0-1)")


class AgentActivity(BaseModel):
    """Real-time agent activity tracking."""

    activity_id: UUID = Field(default_factory=uuid4)
    agent_id: str = Field(..., description="Agent identifier")
    workspace: str = Field(..., description="Current workspace")
    status: str = Field(..., description="Current agent status")
    current_task: str | None = Field(None, description="Current task description")
    task_progress: float = Field(0.0, ge=0.0, le=1.0, description="Task completion percentage")
    component: str | None = Field(None, description="Component being worked on")
    branch: str | None = Field(None, description="Git branch")
    start_time: datetime = Field(default_factory=datetime.utcnow)
    last_update: datetime = Field(default_factory=datetime.utcnow)
    estimated_completion: datetime | None = Field(None, description="Estimated completion time")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")
    blocked_by: list[str] = Field(default_factory=list, description="Blocking dependencies")
    blocking_others: list[str] = Field(default_factory=list, description="Agents this is blocking")


class TaskDefinition(BaseModel):
    """Automated task definition for workflow orchestration."""

    task_id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., description="Task name")
    description: str = Field(..., description="Detailed task description")
    task_type: str = Field(..., description="Type of task")
    required_agent_type: str | None = Field(None, description="Required agent type")
    required_capabilities: list[str] = Field(default_factory=list, description="Required capabilities")
    workspace: str | None = Field(None, description="Required workspace")
    priority: str = Field("medium", description="Task priority")
    estimated_duration_minutes: int = Field(30, description="Estimated duration")
    dependencies: list[UUID] = Field(default_factory=list, description="Task dependencies")
    automated_checks: list[str] = Field(default_factory=list, description="Automated validation checks")
    success_criteria: dict[str, Any] = Field(default_factory=dict, description="Success criteria")
    rollback_procedure: str | None = Field(None, description="Rollback instructions")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str | None = Field(None, description="Creator agent ID")


class TaskAssignment(BaseModel):
    """Task assignment and execution tracking."""

    assignment_id: UUID = Field(default_factory=uuid4)
    task_id: UUID = Field(..., description="Reference to task definition")
    assigned_agent_id: str = Field(..., description="Assigned agent")
    status: str = Field("pending", description="Assignment status")
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = Field(None)
    completed_at: datetime | None = Field(None)
    progress: float = Field(0.0, ge=0.0, le=1.0, description="Completion progress")
    execution_log: list[str] = Field(default_factory=list, description="Execution log entries")
    results: dict[str, Any] = Field(default_factory=dict, description="Task execution results")
    error_details: str | None = Field(None, description="Error details if failed")
    auto_retry_count: int = Field(0, description="Number of automatic retries")
    manual_interventions: list[str] = Field(default_factory=list, description="Manual intervention log")


class ConflictDetection(BaseModel):
    """Conflict detection and resolution tracking."""

    conflict_id: UUID = Field(default_factory=uuid4)
    conflict_type: str = Field(..., description="Type of conflict")
    severity: str = Field(..., description="Conflict severity level")
    affected_agents: list[str] = Field(..., description="Agents involved in conflict")
    affected_resources: list[str] = Field(default_factory=list, description="Resources in conflict")
    workspace: str | None = Field(None, description="Affected workspace")
    description: str = Field(..., description="Conflict description")
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    detection_method: str = Field(..., description="How conflict was detected")
    resolution_strategy: str | None = Field(None, description="Chosen resolution strategy")
    resolution_status: str = Field("detected", description="Resolution status")
    resolved_at: datetime | None = Field(None)
    resolved_by: str | None = Field(None, description="Agent that resolved conflict")
    resolution_actions: list[str] = Field(default_factory=list, description="Actions taken to resolve")
    prevention_suggestions: list[str] = Field(default_factory=list, description="Future prevention strategies")


class HandoffRequest(BaseModel):
    """Context-aware handoff between agents."""

    handoff_id: UUID = Field(default_factory=uuid4)
    from_agent_id: str = Field(..., description="Source agent")
    to_agent_id: str = Field(..., description="Target agent")
    component: str = Field(..., description="Component being handed off")
    workspace: str = Field(..., description="Workspace location")
    handoff_type: str = Field("standard", description="Type of handoff")
    urgency: str = Field("normal", description="Handoff urgency level")
    context_summary: str = Field(..., description="Work context summary")
    completed_tasks: list[str] = Field(default_factory=list, description="Completed tasks")
    next_steps: list[str] = Field(default_factory=list, description="Recommended next steps")
    known_issues: list[str] = Field(default_factory=list, description="Known issues to address")
    test_status: str = Field(..., description="Current test status")
    dependencies: list[str] = Field(default_factory=list, description="External dependencies")
    embedded_context: list[float] | None = Field(None, description="Context embedding vector")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    accepted_at: datetime | None = Field(None)
    completed_at: datetime | None = Field(None)
    handoff_quality_score: float | None = Field(None, description="Quality of handoff documentation")


class CoordinationMessage(BaseModel):
    """Real-time coordination messages between agents."""

    message_id: UUID = Field(default_factory=uuid4)
    from_agent_id: str = Field(..., description="Source agent")
    to_agent_id: str | None = Field(None, description="Target agent (null for broadcast)")
    message_type: str = Field(..., description="Message type")
    priority: str = Field("normal", description="Message priority")
    subject: str = Field(..., description="Message subject")
    content: str = Field(..., description="Message content")
    workspace: str | None = Field(None, description="Related workspace")
    component: str | None = Field(None, description="Related component")
    requires_response: bool = Field(False, description="Whether response is required")
    response_deadline: datetime | None = Field(None, description="Response deadline")
    thread_id: UUID | None = Field(None, description="Message thread ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    read_at: datetime | None = Field(None)
    responded_at: datetime | None = Field(None)
    archived_at: datetime | None = Field(None)


class CoordinationMetrics(BaseModel):
    """Coordination system performance metrics."""

    metric_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    active_agents: int = Field(0, description="Number of active agents")
    total_tasks_active: int = Field(0, description="Active tasks")
    total_tasks_completed_today: int = Field(0, description="Tasks completed today")
    average_task_duration_minutes: float = Field(0.0, description="Average task duration")
    conflicts_detected_today: int = Field(0, description="Conflicts detected today")
    conflicts_resolved_today: int = Field(0, description="Conflicts resolved today")
    handoffs_completed_today: int = Field(0, description="Handoffs completed today")
    coordination_efficiency_score: float = Field(0.0, description="Overall coordination efficiency")
    top_bottlenecks: list[str] = Field(default_factory=list, description="Current system bottlenecks")
    agent_productivity_scores: dict[str, float] = Field(default_factory=dict, description="Agent productivity")
    system_health_score: float = Field(1.0, description="Overall system health")


class CoordinationDashboard(BaseModel):
    """Real-time coordination dashboard data."""

    dashboard_id: UUID = Field(default_factory=uuid4)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    active_agents: list[AgentActivity] = Field(default_factory=list, description="Currently active agents")
    recent_tasks: list[TaskAssignment] = Field(default_factory=list, description="Recent task assignments")
    active_conflicts: list[ConflictDetection] = Field(default_factory=list, description="Unresolved conflicts")
    pending_handoffs: list[HandoffRequest] = Field(default_factory=list, description="Pending handoffs")
    system_alerts: list[str] = Field(default_factory=list, description="System-level alerts")
    performance_summary: CoordinationMetrics = Field(..., description="Performance metrics")
    next_scheduled_tasks: list[TaskDefinition] = Field(default_factory=list, description="Upcoming scheduled tasks")
    resource_utilization: dict[str, float] = Field(default_factory=dict, description="Resource utilization by workspace")
    prediction_insights: dict[str, Any] = Field(default_factory=dict, description="AI-powered insights and predictions")
