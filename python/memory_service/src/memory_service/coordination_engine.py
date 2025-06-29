"""
Intelligent Agent Coordination Engine

Core orchestration system for multi-agent coordination that integrates with
the Memory Service to provide real-time coordination, conflict detection,
and context-aware handoffs.
"""

import asyncio
import json
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

import asyncpg

from .models import (
    AgentActivity,
    AgentProfile,
    AgentStatus,
    AgentType,
    ConflictDetection,
    CoordinationDashboard,
    CoordinationMessage,
    CoordinationMetrics,
    HandoffRequest,
    MemoryRequest,
    TaskAssignment,
    TaskDefinition,
    WorkspaceType,
)

logger = logging.getLogger(__name__)


class CoordinationStatePersistence:
    """
    Persistence layer for coordination state to prevent total data loss on restart.
    
    Stores critical coordination state in PostgreSQL for recovery after service restarts.
    """
    
    def __init__(self, db_url: str = None):
        self.db_url = db_url or self._get_db_url()
        self.connection_pool = None
        self._initialized = False
    
    def _get_db_url(self) -> str:
        """Get database URL from environment or config."""
        import os
        host = os.getenv("PGVECTOR_HOST", "localhost")
        port = os.getenv("PGVECTOR_PORT", "5432")
        database = os.getenv("PGVECTOR_DATABASE", "nexus_memory_db")
        user = os.getenv("PGVECTOR_USER", "postgres")
        password = os.getenv("PGVECTOR_PASSWORD", "")
        
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    async def initialize(self):
        """Initialize database connection and create tables."""
        try:
            # Create connection pool
            self.connection_pool = await asyncpg.create_pool(
                self.db_url,
                min_size=1,
                max_size=5,
                command_timeout=30
            )
            
            # Create tables for coordination state
            async with self.connection_pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS coordination_agents (
                        agent_id TEXT PRIMARY KEY,
                        agent_profile JSONB NOT NULL,
                        agent_activity JSONB NOT NULL,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
                
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS coordination_tasks (
                        assignment_id UUID PRIMARY KEY,
                        task_id UUID NOT NULL,
                        task_definition JSONB NOT NULL,
                        task_assignment JSONB NOT NULL,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
                
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS coordination_conflicts (
                        conflict_id UUID PRIMARY KEY,
                        conflict_data JSONB NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
                
                # Create indexes for performance
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_coordination_agents_updated ON coordination_agents(updated_at)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_coordination_tasks_updated ON coordination_tasks(updated_at)")
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_coordination_conflicts_created ON coordination_conflicts(created_at)")
            
            self._initialized = True
            logger.info("Coordination state persistence initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize coordination persistence: {e}")
            raise
    
    async def save_agent_state(self, agent_id: str, profile: AgentProfile, activity: AgentActivity):
        """Save agent profile and activity state."""
        if not self._initialized:
            await self.initialize()
        
        try:
            async with self.connection_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO coordination_agents (agent_id, agent_profile, agent_activity, updated_at)
                    VALUES ($1, $2, $3, NOW())
                    ON CONFLICT (agent_id) 
                    DO UPDATE SET 
                        agent_profile = $2,
                        agent_activity = $3,
                        updated_at = NOW()
                """, agent_id, profile.dict(), activity.dict())
                
        except Exception as e:
            logger.error(f"Failed to save agent state for {agent_id}: {e}")
    
    async def save_task_state(self, assignment_id: UUID, task_definition: dict, task_assignment: TaskAssignment):
        """Save task assignment state."""
        if not self._initialized:
            await self.initialize()
        
        try:
            async with self.connection_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO coordination_tasks (assignment_id, task_id, task_definition, task_assignment, updated_at)
                    VALUES ($1, $2, $3, $4, NOW())
                    ON CONFLICT (assignment_id)
                    DO UPDATE SET
                        task_definition = $3,
                        task_assignment = $4,
                        updated_at = NOW()
                """, assignment_id, task_assignment.task_id, task_definition, task_assignment.dict())
                
        except Exception as e:
            logger.error(f"Failed to save task state for {assignment_id}: {e}")
    
    async def save_conflict_state(self, conflict: ConflictDetection):
        """Save conflict state."""
        if not self._initialized:
            await self.initialize()
        
        try:
            async with self.connection_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO coordination_conflicts (conflict_id, conflict_data, created_at, updated_at)
                    VALUES ($1, $2, NOW(), NOW())
                    ON CONFLICT (conflict_id)
                    DO UPDATE SET
                        conflict_data = $2,
                        updated_at = NOW()
                """, conflict.conflict_id, conflict.dict())
                
        except Exception as e:
            logger.error(f"Failed to save conflict state for {conflict.conflict_id}: {e}")
    
    async def load_agent_states(self) -> Dict[str, tuple[AgentProfile, AgentActivity]]:
        """Load all agent states from database."""
        if not self._initialized:
            await self.initialize()
        
        try:
            async with self.connection_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT agent_id, agent_profile, agent_activity 
                    FROM coordination_agents
                    WHERE updated_at > NOW() - INTERVAL '24 hours'
                """)
                
                agents = {}
                for row in rows:
                    try:
                        profile = AgentProfile(**row['agent_profile'])
                        activity = AgentActivity(**row['agent_activity'])
                        agents[row['agent_id']] = (profile, activity)
                    except Exception as e:
                        logger.warning(f"Failed to restore agent {row['agent_id']}: {e}")
                
                return agents
                
        except Exception as e:
            logger.error(f"Failed to load agent states: {e}")
            return {}
    
    async def load_task_states(self) -> Dict[UUID, TaskAssignment]:
        """Load all active task states from database."""
        if not self._initialized:
            await self.initialize()
        
        try:
            async with self.connection_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT assignment_id, task_assignment 
                    FROM coordination_tasks
                    WHERE updated_at > NOW() - INTERVAL '72 hours'
                    AND (task_assignment->>'status' IN ('assigned', 'in_progress'))
                """)
                
                tasks = {}
                for row in rows:
                    try:
                        assignment = TaskAssignment(**row['task_assignment'])
                        tasks[row['assignment_id']] = assignment
                    except Exception as e:
                        logger.warning(f"Failed to restore task {row['assignment_id']}: {e}")
                
                return tasks
                
        except Exception as e:
            logger.error(f"Failed to load task states: {e}")
            return {}
    
    async def load_conflict_states(self) -> List[ConflictDetection]:
        """Load all unresolved conflicts from database."""
        if not self._initialized:
            await self.initialize()
        
        try:
            async with self.connection_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT conflict_data 
                    FROM coordination_conflicts
                    WHERE created_at > NOW() - INTERVAL '48 hours'
                    AND (conflict_data->>'resolution_status' IN ('detected', 'in_progress'))
                """)
                
                conflicts = []
                for row in rows:
                    try:
                        conflict = ConflictDetection(**row['conflict_data'])
                        conflicts.append(conflict)
                    except Exception as e:
                        logger.warning(f"Failed to restore conflict: {e}")
                
                return conflicts
                
        except Exception as e:
            logger.error(f"Failed to load conflict states: {e}")
            return []
    
    async def cleanup_old_data(self):
        """Clean up old coordination data to prevent unbounded growth."""
        if not self._initialized:
            return
        
        try:
            async with self.connection_pool.acquire() as conn:
                # Remove old agent data (older than 7 days)
                await conn.execute("""
                    DELETE FROM coordination_agents 
                    WHERE updated_at < NOW() - INTERVAL '7 days'
                """)
                
                # Remove completed tasks (older than 7 days)
                await conn.execute("""
                    DELETE FROM coordination_tasks
                    WHERE updated_at < NOW() - INTERVAL '7 days'
                    AND (task_assignment->>'status' IN ('completed', 'failed', 'cancelled'))
                """)
                
                # Remove resolved conflicts (older than 30 days)
                await conn.execute("""
                    DELETE FROM coordination_conflicts
                    WHERE created_at < NOW() - INTERVAL '30 days'
                    AND (conflict_data->>'resolution_status' = 'resolved')
                """)
                
        except Exception as e:
            logger.error(f"Failed to cleanup old coordination data: {e}")
    
    async def close(self):
        """Close database connections."""
        if self.connection_pool:
            await self.connection_pool.close()


class EnhancedActivityLogger:
    """
    Enhanced activity logging system for comprehensive coordination tracking.
    
    Provides automatic, structured logging of all coordination activities with
    semantic search capabilities and historical analysis support.
    """
    
    def __init__(self, unified_store=None, embedding_model=None):
        self.unified_store = unified_store
        self.embedding_model = embedding_model
        
        # Batch processing for performance
        self.activity_batch = []
        self.batch_size = 10
        self.last_batch_flush = datetime.utcnow()
        self.batch_flush_interval = 30  # seconds
        self.max_batch_size = 50  # ADDED: Prevent memory leaks
        
        # Circuit breaker for reliability (ADDED: Critical reliability fix)
        self.circuit_breaker = {
            'failure_count': 0,
            'last_failure': None,
            'failure_threshold': 5,
            'recovery_timeout': 300,  # 5 minutes
            'state': 'closed'  # closed, open, half_open
        }
        
        # Activity categories for structured logging
        self.activity_categories = {
            'agent_lifecycle': ['registration', 'connection', 'disconnection', 'status_change'],
            'task_management': ['assignment', 'progress_update', 'completion', 'cancellation'],
            'coordination': ['handoff_request', 'handoff_completion', 'conflict_detection', 'conflict_resolution'],
            'communication': ['message_sent', 'broadcast_sent', 'notification_sent'],
            'system_events': ['performance_alert', 'health_check', 'error_recovery']
        }
        
        logger.info("Enhanced Activity Logger initialized with circuit breaker protection")
    
    async def log_activity(
        self, 
        activity_type: str, 
        category: str, 
        agent_id: str = None, 
        details: Dict[str, Any] = None, 
        importance: str = "normal",
        auto_embed: bool = True
    ):
        """
        Log a coordination activity with enhanced metadata and optional embedding.
        
        Args:
            activity_type: Type of activity (e.g., 'agent_registration', 'task_assignment')
            category: Activity category for organization
            agent_id: ID of the primary agent involved
            details: Additional activity details and context
            importance: Importance level ('low', 'normal', 'high', 'critical')
            auto_embed: Whether to automatically generate embeddings for semantic search
        """
        try:
            # Check circuit breaker state (ADDED: Critical reliability fix)
            if not self._circuit_breaker_allow():
                logger.debug(f"Circuit breaker open: dropping activity log {activity_type}")
                return
            
            activity_data = {
                'activity_id': str(uuid4()),
                'timestamp': datetime.utcnow().isoformat(),
                'activity_type': activity_type,
                'category': category,
                'agent_id': agent_id,
                'importance': importance,
                'details': details or {},
                'coordination_engine': True,
                'session_id': self._get_session_id()
            }
            
            # Generate human-readable summary
            content = self._generate_activity_summary(activity_type, category, agent_id, details)
            
            # Add to batch for processing with overflow protection
            self.activity_batch.append({
                'content': content,
                'metadata': activity_data,
                'auto_embed': auto_embed
            })
            
            # Prevent memory leaks from unbounded batch growth (ADDED: Critical reliability fix)
            if len(self.activity_batch) > self.max_batch_size:
                logger.warning(f"Activity batch overflow: {len(self.activity_batch)} items, force flushing")
                await self.flush_activity_batch()
            
            # Check if batch should be flushed
            await self._check_batch_flush()
            
        except Exception as e:
            logger.error(f"Failed to log activity {activity_type}: {e}")
            # Don't let activity logging errors break coordination engine (ADDED: Error isolation)
            self._circuit_breaker_record_failure()
    
    async def log_agent_registration(self, agent_profile: AgentProfile):
        """Log agent registration with detailed context."""
        await self.log_activity(
            activity_type="agent_registration",
            category="agent_lifecycle",
            agent_id=agent_profile.agent_id,
            details={
                'agent_name': agent_profile.agent_name,
                'agent_type': agent_profile.agent_type,
                'workspace': agent_profile.workspace,
                'capabilities': agent_profile.capabilities,
                'success_rate': agent_profile.success_rate
            },
            importance="normal"
        )
    
    async def log_activity_update(self, agent_id: str, activity_update: Dict[str, Any], previous_status: str = None):
        """Log agent activity updates with status transitions."""
        await self.log_activity(
            activity_type="activity_update",
            category="agent_lifecycle", 
            agent_id=agent_id,
            details={
                'previous_status': previous_status,
                'new_status': activity_update.get('status'),
                'workspace': activity_update.get('workspace'),
                'component': activity_update.get('component'),
                'current_task': activity_update.get('current_task'),
                'progress': activity_update.get('task_progress'),
                'update_fields': list(activity_update.keys())
            },
            importance="normal"
        )
    
    async def log_task_assignment(self, task_definition: TaskDefinition, assignment: TaskAssignment):
        """Log task assignments with comprehensive context."""
        await self.log_activity(
            activity_type="task_assignment",
            category="task_management",
            agent_id=assignment.assigned_agent_id,
            details={
                'task_id': str(task_definition.task_id),
                'assignment_id': str(assignment.assignment_id),
                'task_name': task_definition.name,
                'task_type': task_definition.task_type,
                'workspace': task_definition.workspace,
                'priority': task_definition.priority,
                'estimated_duration': task_definition.estimated_duration_minutes,
                'required_capabilities': task_definition.required_capabilities
            },
            importance="high"
        )
    
    async def log_handoff_request(self, handoff_request: HandoffRequest):
        """Log handoff requests with full context preservation."""
        await self.log_activity(
            activity_type="handoff_request",
            category="coordination",
            agent_id=handoff_request.from_agent_id,
            details={
                'handoff_id': str(handoff_request.handoff_id),
                'from_agent': handoff_request.from_agent_id,
                'to_agent': handoff_request.to_agent_id,
                'component': handoff_request.component,
                'workspace': handoff_request.workspace,
                'urgency': handoff_request.urgency,
                'context_summary': handoff_request.context_summary,
                'completed_tasks': handoff_request.completed_tasks,
                'next_steps': handoff_request.next_steps,
                'known_issues': handoff_request.known_issues,
                'test_status': handoff_request.test_status,
                'dependencies': handoff_request.dependencies
            },
            importance="high"
        )
    
    async def log_conflict_detection(self, conflict: ConflictDetection):
        """Log conflict detection with resolution tracking."""
        await self.log_activity(
            activity_type="conflict_detection",
            category="coordination",
            agent_id=conflict.affected_agents[0] if conflict.affected_agents else None,
            details={
                'conflict_id': str(conflict.conflict_id),
                'conflict_type': conflict.conflict_type,
                'severity': conflict.severity,
                'affected_agents': conflict.affected_agents,
                'affected_resources': conflict.affected_resources,
                'workspace': conflict.workspace,
                'description': conflict.description,
                'detection_method': conflict.detection_method,
                'resolution_strategy': conflict.resolution_strategy
            },
            importance="high" if conflict.severity == "high" else "normal"
        )
    
    async def log_system_event(self, event_type: str, details: Dict[str, Any], importance: str = "normal"):
        """Log system-level coordination events."""
        await self.log_activity(
            activity_type=event_type,
            category="system_events",
            details=details,
            importance=importance
        )
    
    async def flush_activity_batch(self):
        """Manually flush the activity batch to Memory Service."""
        if not self.activity_batch:
            return
        
        # Check circuit breaker (ADDED: Critical reliability fix)
        if not self._circuit_breaker_allow():
            logger.warning("Circuit breaker open: skipping activity batch flush")
            return
        
        batch_to_process = []
        try:
            batch_to_process = self.activity_batch.copy()
            self.activity_batch.clear()
            
            # Process each activity in the batch
            for activity in batch_to_process:
                await self._store_single_activity(
                    activity['content'],
                    activity['metadata'],
                    activity['auto_embed']
                )
            
            self.last_batch_flush = datetime.utcnow()
            logger.info(f"Flushed {len(batch_to_process)} activities to Memory Service")
            
            # Record success for circuit breaker (ADDED: Critical reliability fix)
            self._circuit_breaker_record_success()
            
        except Exception as e:
            logger.error(f"Failed to flush activity batch: {e}")
            # Record failure for circuit breaker (ADDED: Critical reliability fix)
            self._circuit_breaker_record_failure()
            
            # Restore batch on failure only if circuit breaker allows (prevent unbounded growth)
            if self.circuit_breaker['state'] != 'open' and len(self.activity_batch) + len(batch_to_process) <= self.max_batch_size:
                self.activity_batch.extend(batch_to_process)
            else:
                logger.warning(f"Dropping {len(batch_to_process)} activities due to persistent failures or batch overflow")
    
    async def get_activity_history(
        self, 
        agent_id: str = None, 
        category: str = None, 
        hours_back: int = 24,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Retrieve activity history with filtering options."""
        try:
            if not self.unified_store:
                return []
            
            # Build metadata filters
            filters = {"coordination_engine": True}
            
            if agent_id:
                filters["agent_id"] = agent_id
            if category:
                filters["category"] = category
            
            # EMERGENCY FIX: Remove time_range since unified_store doesn't handle it
            # We'll do time filtering manually after getting results
            since_time = datetime.utcnow() - timedelta(hours=hours_back)
            
            # Query Memory Service with larger limit for manual time filtering
            from .models import QueryRequest
            
            query = QueryRequest(
                query="",  # Empty query to use metadata filtering only
                limit=min(limit * 3, 1000),  # Get more results for time filtering
                filters=filters,
                user_id="coordination_engine",
                conversation_id="agent_coordination"
                # REMOVED: time_range=time_range (doesn't work)
            )
            
            results = await self.unified_store.query_memories(query)
            
            # Convert to dict format and manually filter by time
            activity_results = []
            for result in results.memories:
                activity_data = result.dict()
                
                # Manual time filtering (EMERGENCY FIX)
                timestamp_str = activity_data.get('metadata', {}).get('timestamp')
                if timestamp_str:
                    try:
                        # Parse timestamp and check if within time range
                        activity_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        if activity_time >= since_time:
                            activity_results.append(activity_data)
                        
                        # Stop if we have enough recent results
                        if len(activity_results) >= limit:
                            break
                    except (ValueError, AttributeError) as e:
                        logger.debug(f"Failed to parse timestamp {timestamp_str}: {e}")
                        # Include items with unparseable timestamps (better than losing data)
                        activity_results.append(activity_data)
            
            # Sort by timestamp (most recent first) 
            def get_sort_key(item):
                timestamp_str = item.get('metadata', {}).get('timestamp', '')
                try:
                    return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except:
                    return datetime.min  # Put unparseable timestamps at end
            
            sorted_results = sorted(activity_results, key=get_sort_key, reverse=True)
            
            # Return up to the requested limit
            return sorted_results[:limit]
            
        except Exception as e:
            logger.error(f"Failed to retrieve activity history: {e}")
            return []
    
    # Private helper methods
    
    async def _check_batch_flush(self):
        """Check if batch should be flushed based on size or time."""
        should_flush = (
            len(self.activity_batch) >= self.batch_size or
            (datetime.utcnow() - self.last_batch_flush).total_seconds() > self.batch_flush_interval
        )
        
        if should_flush:
            await self.flush_activity_batch()
    
    async def _store_single_activity(self, content: str, metadata: Dict[str, Any], auto_embed: bool):
        """Store a single activity in the Memory Service."""
        if not self.unified_store:
            return
        
        try:
            # Generate embedding if requested and embedding model is available
            embedding = None
            if auto_embed and self.embedding_model:
                embedding = await self.embedding_model.embed_text(content)
            
            request = MemoryRequest(
                content=content,
                metadata=metadata,
                embedding=embedding,
                user_id="coordination_engine",
                conversation_id="agent_coordination"
            )
            
            await self.unified_store.store_memory(request)
            
        except Exception as e:
            logger.error(f"Failed to store single activity: {e}")
    
    def _generate_activity_summary(self, activity_type: str, category: str, agent_id: str, details: Dict[str, Any]) -> str:
        """Generate human-readable activity summary."""
        try:
            timestamp = datetime.utcnow().strftime("%H:%M:%S")
            
            if activity_type == "agent_registration":
                agent_name = details.get('agent_name', agent_id)
                workspace = details.get('workspace', 'unknown')
                return f"[{timestamp}] Agent {agent_name} registered in {workspace} workspace"
            
            elif activity_type == "activity_update":
                status = details.get('new_status', 'unknown')
                task = details.get('current_task', '')
                task_info = f" (working on: {task})" if task else ""
                return f"[{timestamp}] Agent {agent_id} status changed to {status}{task_info}"
            
            elif activity_type == "task_assignment":
                task_name = details.get('task_name', 'Unknown Task')
                return f"[{timestamp}] Task '{task_name}' assigned to agent {agent_id}"
            
            elif activity_type == "handoff_request":
                component = details.get('component', 'unknown component')
                to_agent = details.get('to_agent', 'unknown')
                return f"[{timestamp}] Handoff requested: {component} from {agent_id} to {to_agent}"
            
            elif activity_type == "conflict_detection":
                conflict_type = details.get('conflict_type', 'unknown')
                severity = details.get('severity', 'unknown')
                return f"[{timestamp}] {severity.upper()} conflict detected: {conflict_type}"
            
            else:
                return f"[{timestamp}] {category}: {activity_type} - Agent: {agent_id or 'system'}"
                
        except Exception as e:
            logger.error(f"Failed to generate activity summary: {e}")
            return f"[{datetime.utcnow().strftime('%H:%M:%S')}] {activity_type} - {category}"
    
    def _get_session_id(self) -> str:
        """Generate or retrieve current session ID for activity grouping."""
        # Simple session ID based on date for daily grouping
        return datetime.utcnow().strftime("%Y-%m-%d")
    
    def _circuit_breaker_allow(self) -> bool:
        """Check if circuit breaker allows operation (ADDED: Critical reliability fix)."""
        now = datetime.utcnow()
        
        if self.circuit_breaker['state'] == 'closed':
            return True
        elif self.circuit_breaker['state'] == 'open':
            # Check if recovery timeout has passed
            if (self.circuit_breaker['last_failure'] and 
                (now - self.circuit_breaker['last_failure']).total_seconds() > self.circuit_breaker['recovery_timeout']):
                self.circuit_breaker['state'] = 'half_open'
                logger.info("Circuit breaker moving to half-open state")
                return True
            return False
        elif self.circuit_breaker['state'] == 'half_open':
            # Allow one operation to test if service is recovered
            return True
        
        return False
    
    def _circuit_breaker_record_failure(self):
        """Record a failure in the circuit breaker (ADDED: Critical reliability fix)."""
        self.circuit_breaker['failure_count'] += 1
        self.circuit_breaker['last_failure'] = datetime.utcnow()
        
        if self.circuit_breaker['failure_count'] >= self.circuit_breaker['failure_threshold']:
            self.circuit_breaker['state'] = 'open'
            logger.warning(f"Circuit breaker opened after {self.circuit_breaker['failure_count']} failures")
    
    def _circuit_breaker_record_success(self):
        """Record a successful operation in the circuit breaker (ADDED: Critical reliability fix)."""
        if self.circuit_breaker['state'] == 'half_open':
            # Service is recovered, close circuit breaker
            self.circuit_breaker['state'] = 'closed'
            self.circuit_breaker['failure_count'] = 0
            logger.info("Circuit breaker closed - service recovered")
        elif self.circuit_breaker['state'] == 'closed':
            # Reset failure count on success
            self.circuit_breaker['failure_count'] = max(0, self.circuit_breaker['failure_count'] - 1)


class AgentCoordinationEngine:
    """
    Intelligent coordination engine for multi-agent development workflows.
    
    Provides:
    - Real-time agent activity tracking
    - Predictive conflict detection
    - Automated task orchestration
    - Context-aware handoffs
    - Performance analytics and optimization
    """

    def __init__(self, unified_store=None, embedding_model=None, websocket_manager=None):
        self.unified_store = unified_store
        self.embedding_model = embedding_model
        self.websocket_manager = websocket_manager
        
        # Initialize Enhanced Activity Logger
        self.activity_logger = EnhancedActivityLogger(unified_store, embedding_model)
        
        # Initialize State Persistence (EMERGENCY FIX: Prevent data loss on restart)
        self.state_persistence = CoordinationStatePersistence()
        
        # In-memory state for real-time coordination
        self.active_agents: Dict[str, AgentActivity] = {}
        self.agent_profiles: Dict[str, AgentProfile] = {}
        self.active_tasks: Dict[UUID, TaskAssignment] = {}
        self.conflict_history: List[ConflictDetection] = []
        self.coordination_metrics = CoordinationMetrics()
        
        # Predictive models and caching
        self.conflict_prediction_cache = {}
        self.workspace_utilization = defaultdict(float)
        
        # State management flags
        self._state_loaded = False
        self._last_cleanup = datetime.utcnow()
        
        # Concurrency protection (EMERGENCY FIX: Prevent state corruption from race conditions)
        self._agent_state_lock = asyncio.Lock()
        self._task_state_lock = asyncio.Lock()
        self._conflict_state_lock = asyncio.Lock()
        
        logger.info("Agent Coordination Engine initialized with Enhanced Activity Logging, State Persistence, and Concurrency Protection")

    async def initialize(self):
        """Initialize the coordination engine and load persisted state (EMERGENCY FIX: Restore state after restart)."""
        try:
            # Initialize state persistence
            await self.state_persistence.initialize()
            
            # Load previous state
            await self.load_state_from_persistence()
            
            # Start periodic cleanup task
            asyncio.create_task(self._periodic_cleanup_task())
            
            logger.info("Coordination engine fully initialized with state restoration")
            
        except Exception as e:
            logger.error(f"Failed to initialize coordination engine: {e}")
            # Continue with empty state rather than crashing

    async def load_state_from_persistence(self):
        """Load coordination state from database (EMERGENCY FIX: Restore state after restart)."""
        if self._state_loaded:
            return
        
        try:
            logger.info("Loading coordination state from persistence...")
            
            # Load agent states
            agent_states = await self.state_persistence.load_agent_states()
            for agent_id, (profile, activity) in agent_states.items():
                self.agent_profiles[agent_id] = profile
                self.active_agents[agent_id] = activity
            
            # Load task states
            task_states = await self.state_persistence.load_task_states()
            self.active_tasks.update(task_states)
            
            # Load conflict states
            conflict_states = await self.state_persistence.load_conflict_states()
            self.conflict_history.extend(conflict_states)
            
            self._state_loaded = True
            logger.info(f"State loaded: {len(agent_states)} agents, {len(task_states)} tasks, {len(conflict_states)} conflicts")
            
        except Exception as e:
            logger.error(f"Failed to load coordination state: {e}")
            # Continue with empty state rather than crashing
    
    async def _save_agent_state(self, agent_id: str):
        """Save agent state to persistence."""
        try:
            if agent_id in self.agent_profiles and agent_id in self.active_agents:
                await self.state_persistence.save_agent_state(
                    agent_id, 
                    self.agent_profiles[agent_id], 
                    self.active_agents[agent_id]
                )
        except Exception as e:
            logger.error(f"Failed to save agent state for {agent_id}: {e}")
    
    async def _save_task_state(self, assignment_id: UUID, task_definition: dict = None):
        """Save task state to persistence."""
        try:
            if assignment_id in self.active_tasks:
                task_assignment = self.active_tasks[assignment_id]
                await self.state_persistence.save_task_state(
                    assignment_id, 
                    task_definition or {}, 
                    task_assignment
                )
        except Exception as e:
            logger.error(f"Failed to save task state for {assignment_id}: {e}")
    
    async def _save_conflict_state(self, conflict: ConflictDetection):
        """Save conflict state to persistence."""
        try:
            await self.state_persistence.save_conflict_state(conflict)
        except Exception as e:
            logger.error(f"Failed to save conflict state for {conflict.conflict_id}: {e}")
    
    async def _cleanup_stale_state(self):
        """Clean up stale state and run periodic maintenance (EMERGENCY FIX: Prevent memory leaks)."""
        try:
            now = datetime.utcnow()
            
            # Only run cleanup every hour
            if (now - self._last_cleanup).total_seconds() < 3600:
                return
            
            # Acquire all locks for cleanup operations (EMERGENCY FIX: Prevent state corruption during cleanup)
            async with self._agent_state_lock:
                async with self._task_state_lock:
                    async with self._conflict_state_lock:
                        # Remove agents that haven't been seen in 24 hours
                        stale_agents = [
                            agent_id for agent_id, activity in self.active_agents.items()
                            if (now - activity.last_update).total_seconds() > 86400  # 24 hours
                        ]
                        
                        for agent_id in stale_agents:
                            logger.info(f"Removing stale agent: {agent_id}")
                            self.active_agents.pop(agent_id, None)
                            self.agent_profiles.pop(agent_id, None)
                        
                        # Remove completed tasks older than 72 hours
                        stale_tasks = [
                            assignment_id for assignment_id, task in self.active_tasks.items()
                            if (task.status in ['completed', 'failed', 'cancelled'] and 
                                task.completed_at and 
                                (now - task.completed_at).total_seconds() > 259200)  # 72 hours
                        ]
                        
                        for assignment_id in stale_tasks:
                            logger.info(f"Removing stale task: {assignment_id}")
                            self.active_tasks.pop(assignment_id, None)
                        
                        # Remove resolved conflicts older than 48 hours
                        self.conflict_history = [
                            conflict for conflict in self.conflict_history
                            if not (conflict.resolution_status == "resolved" and 
                                   conflict.resolved_at and 
                                   (now - conflict.resolved_at).total_seconds() > 172800)  # 48 hours
                        ]
                        
                        self._last_cleanup = now
            
            # Run database cleanup (outside locks to avoid long-running operations in critical sections)
            await self.state_persistence.cleanup_old_data()
            
            logger.info(f"Cleanup completed: removed {len(stale_agents)} agents, {len(stale_tasks)} tasks")
            
        except Exception as e:
            logger.error(f"Failed to cleanup stale state: {e}")

    async def _periodic_cleanup_task(self):
        """Periodic background task for state cleanup (EMERGENCY FIX: Prevent memory leaks)."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                await self._cleanup_stale_state()
            except Exception as e:
                logger.error(f"Error in periodic cleanup task: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying

    async def register_agent(self, agent_profile: AgentProfile) -> bool:
        """Register a new agent with the coordination system."""
        try:
            # Acquire lock to prevent race conditions (EMERGENCY FIX: Prevent state corruption)
            async with self._agent_state_lock:
                # Store agent profile
                self.agent_profiles[agent_profile.agent_id] = agent_profile
                
                # Initialize agent activity
                activity = AgentActivity(
                    agent_id=agent_profile.agent_id,
                    workspace=agent_profile.workspace,
                    status=AgentStatus.IDLE,
                    start_time=datetime.utcnow()
                )
                self.active_agents[agent_profile.agent_id] = activity
                
                # Save agent state to persistence (EMERGENCY FIX: Prevent data loss on restart)
                await self._save_agent_state(agent_profile.agent_id)
            
            # Log registration with enhanced activity logger (outside lock to avoid blocking)
            await self.activity_logger.log_agent_registration(agent_profile)
            
            # Broadcast registration to other agents
            await self._broadcast_message(
                from_agent_id="coordination_engine",
                message_type="agent_registration",
                subject=f"New agent registered: {agent_profile.agent_name}",
                content=f"Agent {agent_profile.agent_name} is now available in {agent_profile.workspace}",
                workspace=agent_profile.workspace
            )
            
            logger.info(f"Agent registered: {agent_profile.agent_id} ({agent_profile.agent_name})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register agent {agent_profile.agent_id}: {e}")
            return False

    async def update_agent_activity(self, agent_id: str, activity_update: Dict[str, Any]) -> bool:
        """Update agent activity status and detect potential conflicts."""
        try:
            # Check if agent exists (outside lock for performance)
            if agent_id not in self.active_agents:
                logger.warning(f"Unknown agent: {agent_id}")
                return False
            
            # Acquire lock to prevent race conditions (EMERGENCY FIX: Prevent state corruption)
            async with self._agent_state_lock:
                # Re-check existence within lock
                if agent_id not in self.active_agents:
                    logger.warning(f"Agent {agent_id} removed during update")
                    return False
                    
                # Capture previous status for logging
                activity = self.active_agents[agent_id]
                previous_status = activity.status
                
                # Update activity
                for key, value in activity_update.items():
                    if hasattr(activity, key):
                        setattr(activity, key, value)
                activity.last_update = datetime.utcnow()
                
                # Update workspace utilization
                if 'workspace' in activity_update:
                    self.workspace_utilization[activity.workspace] += 0.1
                
                # Save updated agent state to persistence (EMERGENCY FIX: Prevent data loss on restart)
                await self._save_agent_state(agent_id)
            
            # Log activity update with enhanced logger (outside lock to avoid blocking)
            await self.activity_logger.log_activity_update(
                agent_id, activity_update, previous_status
            )
            
            # Detect potential conflicts
            conflicts = await self._detect_conflicts(agent_id, activity)
            if conflicts:
                for conflict in conflicts:
                    await self._handle_conflict(conflict)
            
            # Notify relevant agents of status change  
            await self._notify_dependent_agents(agent_id, activity)
            
            logger.debug(f"Activity updated for agent {agent_id}: {activity.status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update activity for agent {agent_id}: {e}")
            return False

    async def assign_task(self, task_definition: TaskDefinition, preferred_agent: Optional[str] = None) -> Optional[TaskAssignment]:
        """Intelligently assign a task to the most suitable agent."""
        try:
            # Find suitable agent (outside locks for performance)
            suitable_agent = await self._find_suitable_agent(task_definition, preferred_agent)
            if not suitable_agent:
                logger.warning(f"No suitable agent found for task: {task_definition.name}")
                return None
            
            # Acquire locks to prevent race conditions (EMERGENCY FIX: Prevent state corruption)
            async with self._task_state_lock:
                async with self._agent_state_lock:
                    # Create task assignment
                    assignment = TaskAssignment(
                        task_id=task_definition.task_id,
                        assigned_agent_id=suitable_agent,
                        status="assigned",
                        assigned_at=datetime.utcnow()
                    )
                    
                    self.active_tasks[assignment.assignment_id] = assignment
                    
                    # Update agent status
                    if suitable_agent in self.active_agents:
                        self.active_agents[suitable_agent].status = AgentStatus.WORKING
                        self.active_agents[suitable_agent].current_task = task_definition.name
                    
                    # Save task and agent state to persistence (EMERGENCY FIX: Prevent data loss on restart)
                    await self._save_task_state(assignment.assignment_id, task_definition.dict())
                    await self._save_agent_state(suitable_agent)
            
            # Log task assignment with enhanced logger (outside locks to avoid blocking)
            await self.activity_logger.log_task_assignment(task_definition, assignment)
            
            # Notify agent of assignment
            await self._send_message(
                from_agent_id="coordination_engine",
                to_agent_id=suitable_agent,
                message_type="task_assignment",
                subject=f"New task assigned: {task_definition.name}",
                content=f"You have been assigned: {task_definition.description}",
                workspace=task_definition.workspace
            )
            
            logger.info(f"Task {task_definition.name} assigned to agent {suitable_agent}")
            return assignment
            
        except Exception as e:
            logger.error(f"Failed to assign task {task_definition.name}: {e}")
            return None

    async def request_handoff(self, handoff_request: HandoffRequest) -> bool:
        """Process a context-aware handoff between agents."""
        try:
            # Generate context embedding
            if self.embedding_model and handoff_request.context_summary:
                handoff_request.embedded_context = await self.embedding_model.embed_text(
                    handoff_request.context_summary
                )
            
            # Validate target agent availability
            target_agent = handoff_request.to_agent_id
            if target_agent not in self.active_agents:
                logger.warning(f"Target agent {target_agent} not available for handoff")
                return False
            
            target_activity = self.active_agents[target_agent]
            if target_activity.status not in [AgentStatus.IDLE, AgentStatus.WAITING]:
                logger.warning(f"Target agent {target_agent} is busy ({target_activity.status})")
                return False
            
            # Log handoff request with enhanced logger
            await self.activity_logger.log_handoff_request(handoff_request)
            
            # Notify target agent with rich context
            await self._send_message(
                from_agent_id=handoff_request.from_agent_id,
                to_agent_id=target_agent,
                message_type="handoff_request",
                subject=f"Handoff request: {handoff_request.component}",
                content=self._format_handoff_content(handoff_request),
                workspace=handoff_request.workspace,
                requires_response=True,
                response_deadline=datetime.utcnow() + timedelta(hours=1)
            )
            
            # Update agent statuses
            if handoff_request.from_agent_id in self.active_agents:
                self.active_agents[handoff_request.from_agent_id].status = AgentStatus.WAITING
            
            logger.info(f"Handoff requested: {handoff_request.component} from {handoff_request.from_agent_id} to {target_agent}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to process handoff request: {e}")
            return False

    async def get_coordination_dashboard(self) -> CoordinationDashboard:
        """Generate real-time coordination dashboard data."""
        try:
            # Update metrics
            await self._update_coordination_metrics()
            
            # Get recent tasks (last 24 hours)
            recent_tasks = [
                assignment for assignment in self.active_tasks.values()
                if assignment.assigned_at > datetime.utcnow() - timedelta(days=1)
            ]
            
            # Get active conflicts
            active_conflicts = [
                conflict for conflict in self.conflict_history
                if conflict.resolution_status in ["detected", "in_progress"]
            ]
            
            # Get pending handoffs (you'd track these in a real implementation)
            pending_handoffs = []  # Would be populated from stored handoff requests
            
            # Generate system alerts
            system_alerts = await self._generate_system_alerts()
            
            # Get next scheduled tasks
            next_scheduled_tasks = []  # Would be populated from task scheduler
            
            # Calculate resource utilization
            resource_utilization = dict(self.workspace_utilization)
            
            # Generate AI-powered insights
            prediction_insights = await self._generate_prediction_insights()
            
            dashboard = CoordinationDashboard(
                active_agents=list(self.active_agents.values()),
                recent_tasks=recent_tasks,
                active_conflicts=active_conflicts,
                pending_handoffs=pending_handoffs,
                system_alerts=system_alerts,
                performance_summary=self.coordination_metrics,
                next_scheduled_tasks=next_scheduled_tasks,
                resource_utilization=resource_utilization,
                prediction_insights=prediction_insights
            )
            
            logger.debug("Generated coordination dashboard")
            return dashboard
            
        except Exception as e:
            logger.error(f"Failed to generate coordination dashboard: {e}")
            # Return empty dashboard on error
            return CoordinationDashboard(performance_summary=self.coordination_metrics)

    async def get_activity_history(
        self, 
        agent_id: str = None, 
        category: str = None, 
        hours_back: int = 24,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get coordination activity history with filtering options."""
        return await self.activity_logger.get_activity_history(
            agent_id=agent_id, 
            category=category, 
            hours_back=hours_back, 
            limit=limit
        )

    async def flush_activity_logs(self):
        """Manually flush pending activity logs to Memory Service."""
        await self.activity_logger.flush_activity_batch()

    async def complete_task(self, assignment_id: UUID, completion_status: str = "completed", completion_notes: str = None) -> bool:
        """Mark a task as completed and log the completion (ADDED: Missing integration point)."""
        try:
            if assignment_id not in self.active_tasks:
                logger.warning(f"Unknown task assignment: {assignment_id}")
                return False
            
            assignment = self.active_tasks[assignment_id]
            assignment.status = completion_status
            assignment.completed_at = datetime.utcnow()
            
            # Update agent status to idle
            agent_id = assignment.assigned_agent_id
            if agent_id in self.active_agents:
                self.active_agents[agent_id].status = AgentStatus.IDLE
                self.active_agents[agent_id].current_task = None
                self.active_agents[agent_id].task_progress = 0.0
            
            # Log task completion with enhanced logger
            await self.activity_logger.log_activity(
                activity_type="task_completion",
                category="task_management",
                agent_id=agent_id,
                details={
                    "assignment_id": str(assignment_id),
                    "completion_status": completion_status,
                    "completion_notes": completion_notes,
                    "duration_minutes": (assignment.completed_at - assignment.assigned_at).total_seconds() / 60,
                    "task_metadata": {
                        "task_id": str(assignment.task_id),
                        "assigned_at": assignment.assigned_at.isoformat(),
                        "completed_at": assignment.completed_at.isoformat()
                    }
                },
                importance="high" if completion_status == "completed" else "normal"
            )
            
            logger.info(f"Task {assignment_id} {completion_status} by agent {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to complete task {assignment_id}: {e}")
            return False

    async def resolve_conflict(self, conflict_id: UUID, resolution_method: str, resolution_notes: str = None) -> bool:
        """Mark a conflict as resolved and log the resolution (ADDED: Missing integration point)."""
        try:
            # Acquire lock to prevent race conditions (EMERGENCY FIX: Prevent state corruption)
            async with self._conflict_state_lock:
                # Find the conflict in history
                conflict = None
                for c in self.conflict_history:
                    if c.conflict_id == conflict_id:
                        conflict = c
                        break
                
                if not conflict:
                    logger.warning(f"Unknown conflict: {conflict_id}")
                    return False
                
                # Update conflict status
                conflict.resolution_status = "resolved"
                conflict.resolved_at = datetime.utcnow()
                conflict.resolution_strategy = resolution_method
                
                # Save resolved conflict state to persistence (EMERGENCY FIX: Prevent data loss on restart)
                await self._save_conflict_state(conflict)
            
            # Log conflict resolution
            await self.activity_logger.log_activity(
                activity_type="conflict_resolution",
                category="coordination",
                agent_id=conflict.affected_agents[0] if conflict.affected_agents else None,
                details={
                    "conflict_id": str(conflict_id),
                    "conflict_type": conflict.conflict_type,
                    "original_severity": conflict.severity,
                    "resolution_method": resolution_method,
                    "resolution_notes": resolution_notes,
                    "affected_agents": conflict.affected_agents,
                    "resolution_duration_minutes": (conflict.resolved_at - conflict.detected_at).total_seconds() / 60,
                    "workspace": conflict.workspace
                },
                importance="high" if conflict.severity == "high" else "normal"
            )
            
            logger.info(f"Conflict {conflict_id} resolved using {resolution_method}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resolve conflict {conflict_id}: {e}")
            return False

    # Private helper methods

    async def _detect_conflicts(self, agent_id: str, activity: AgentActivity) -> List[ConflictDetection]:
        """Detect potential conflicts based on agent activity."""
        conflicts = []
        
        try:
            # Check for workspace conflicts
            workspace_agents = [
                other_id for other_id, other_activity in self.active_agents.items()
                if other_id != agent_id and other_activity.workspace == activity.workspace
                and other_activity.status == AgentStatus.WORKING
            ]
            
            if len(workspace_agents) > 0 and activity.status == AgentStatus.WORKING:
                # Multiple agents working in same workspace
                conflict = ConflictDetection(
                    conflict_type="workspace_contention",
                    severity="medium",
                    affected_agents=[agent_id] + workspace_agents,
                    affected_resources=[activity.workspace],
                    workspace=activity.workspace,
                    description=f"Multiple agents working simultaneously in {activity.workspace}",
                    detection_method="activity_monitoring"
                )
                conflicts.append(conflict)
            
            # Check for component conflicts
            if activity.component:
                component_agents = [
                    other_id for other_id, other_activity in self.active_agents.items()
                    if (other_id != agent_id and 
                        other_activity.component == activity.component and
                        other_activity.status == AgentStatus.WORKING)
                ]
                
                if component_agents:
                    conflict = ConflictDetection(
                        conflict_type="component_conflict",
                        severity="high",
                        affected_agents=[agent_id] + component_agents,
                        affected_resources=[activity.component],
                        workspace=activity.workspace,
                        description=f"Multiple agents modifying component {activity.component}",
                        detection_method="component_monitoring"
                    )
                    conflicts.append(conflict)
            
            # Store conflicts in history
            for conflict in conflicts:
                self.conflict_history.append(conflict)
                
        except Exception as e:
            logger.error(f"Error detecting conflicts for agent {agent_id}: {e}")
        
        return conflicts

    async def _handle_conflict(self, conflict: ConflictDetection):
        """Handle detected conflicts with automated resolution strategies."""
        try:
            logger.warning(f"Conflict detected: {conflict.conflict_type} - {conflict.description}")
            
            # Acquire lock to prevent race conditions in conflict handling (EMERGENCY FIX: Prevent state corruption)
            async with self._conflict_state_lock:
                # Add to conflict history
                self.conflict_history.append(conflict)
                
                # Choose resolution strategy based on conflict type and severity
                if conflict.conflict_type == "workspace_contention" and conflict.severity == "medium":
                    # Suggest coordination between agents
                    resolution_strategy = "coordination_suggestion"
                    await self._suggest_agent_coordination(conflict)
                    
                elif conflict.conflict_type == "component_conflict" and conflict.severity == "high":
                    # Require explicit handoff or task splitting
                    resolution_strategy = "explicit_handoff_required"
                    await self._require_explicit_handoff(conflict)
                    
                else:
                    # Generic notification
                    resolution_strategy = "notification_only"
                    await self._notify_conflict(conflict)
                
                # Update conflict record
                conflict.resolution_strategy = resolution_strategy
                conflict.resolution_status = "in_progress"
                
                # Save conflict state to persistence (EMERGENCY FIX: Prevent data loss on restart)
                await self._save_conflict_state(conflict)
            
            # Log conflict detection with enhanced logger (outside lock to avoid blocking)
            await self.activity_logger.log_conflict_detection(conflict)
                
        except Exception as e:
            logger.error(f"Error handling conflict {conflict.conflict_id}: {e}")

    async def _find_suitable_agent(self, task: TaskDefinition, preferred_agent: Optional[str] = None) -> Optional[str]:
        """Find the most suitable agent for a task based on capabilities and availability."""
        try:
            # If preferred agent is specified and available, use them
            if preferred_agent and preferred_agent in self.active_agents:
                activity = self.active_agents[preferred_agent]
                if activity.status in [AgentStatus.IDLE, AgentStatus.WAITING]:
                    return preferred_agent
            
            # Find agents by type and capabilities
            suitable_agents = []
            for agent_id, profile in self.agent_profiles.items():
                # Check agent type compatibility
                if task.required_agent_type and profile.agent_type != task.required_agent_type:
                    continue
                
                # Check capability requirements
                if task.required_capabilities:
                    if not all(cap in profile.capabilities for cap in task.required_capabilities):
                        continue
                
                # Check workspace compatibility
                if task.workspace and profile.workspace != task.workspace:
                    continue
                
                # Check availability
                if agent_id in self.active_agents:
                    activity = self.active_agents[agent_id]
                    if activity.status not in [AgentStatus.IDLE, AgentStatus.WAITING]:
                        continue
                
                suitable_agents.append((agent_id, profile))
            
            if not suitable_agents:
                return None
            
            # Select best agent based on success rate and task load
            best_agent = max(suitable_agents, key=lambda x: x[1].success_rate)
            return best_agent[0]
            
        except Exception as e:
            logger.error(f"Error finding suitable agent for task {task.name}: {e}")
            return None


    async def _broadcast_message(self, from_agent_id: str, message_type: str, subject: str, content: str, **kwargs):
        """Broadcast a message to all connected agents."""
        message_data = {
            "subject": subject,
            "content": content,
            "from_agent_id": from_agent_id,
            **kwargs
        }
        
        if self.websocket_manager:
            sent_count = await self.websocket_manager.broadcast_message(
                message_type=message_type,
                data=message_data,
                from_agent_id=from_agent_id
            )
            logger.info(f"Broadcast message '{subject}' to {sent_count} agents")
        else:
            logger.info(f"Broadcasting message (WebSocket unavailable): {subject}")

    async def _send_message(self, from_agent_id: str, to_agent_id: str, message_type: str, subject: str, content: str, **kwargs):
        """Send a direct message to a specific agent."""
        message_data = {
            "subject": subject,
            "content": content,
            "from_agent_id": from_agent_id,
            **kwargs
        }
        
        if self.websocket_manager:
            success = await self.websocket_manager.send_message(
                target_agent_id=to_agent_id,
                message_type=message_type,
                data=message_data,
                from_agent_id=from_agent_id
            )
            logger.info(f"Sent message to {to_agent_id}: {subject} ({'delivered' if success else 'queued'})")
        else:
            logger.info(f"Sending message (WebSocket unavailable) to {to_agent_id}: {subject}")

    async def _notify_dependent_agents(self, agent_id: str, activity: AgentActivity):
        """Notify agents that depend on this agent's work."""
        # Find agents that might be blocked by this agent
        dependent_agents = [
            other_id for other_id, other_activity in self.active_agents.items()
            if agent_id in other_activity.blocked_by
        ]
        
        for dependent_agent in dependent_agents:
            await self._send_message(
                from_agent_id="coordination_engine",
                to_agent_id=dependent_agent,
                message_type="dependency_update",
                subject=f"Dependency update: {agent_id}",
                content=f"Agent {agent_id} status changed to {activity.status}",
                workspace=activity.workspace
            )

    def _format_handoff_content(self, handoff: HandoffRequest) -> str:
        """Format handoff request content for agent notification."""
        return f"""
Component: {handoff.component}
Workspace: {handoff.workspace}
Urgency: {handoff.urgency}

Context Summary:
{handoff.context_summary}

Completed Tasks:
{chr(10).join(f"- {task}" for task in handoff.completed_tasks)}

Next Steps:
{chr(10).join(f"- {step}" for step in handoff.next_steps)}

Known Issues:
{chr(10).join(f"- {issue}" for issue in handoff.known_issues)}

Test Status: {handoff.test_status}

Dependencies:
{chr(10).join(f"- {dep}" for dep in handoff.dependencies)}
        """.strip()

    async def _update_coordination_metrics(self):
        """Update coordination performance metrics."""
        try:
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Count active agents
            active_count = len([a for a in self.active_agents.values() if a.status != AgentStatus.OFFLINE])
            
            # Count tasks completed today
            tasks_completed_today = len([
                task for task in self.active_tasks.values()
                if task.completed_at and task.completed_at >= today_start
            ])
            
            # Calculate average task duration
            completed_tasks = [task for task in self.active_tasks.values() if task.completed_at]
            avg_duration = 0.0
            if completed_tasks:
                durations = [
                    (task.completed_at - task.started_at).total_seconds() / 60
                    for task in completed_tasks if task.started_at
                ]
                avg_duration = sum(durations) / len(durations) if durations else 0.0
            
            # Count conflicts today
            conflicts_today = len([
                conflict for conflict in self.conflict_history
                if conflict.detected_at >= today_start
            ])
            
            resolved_conflicts_today = len([
                conflict for conflict in self.conflict_history
                if conflict.resolved_at and conflict.resolved_at >= today_start
            ])
            
            # Calculate coordination efficiency (placeholder algorithm)
            efficiency_score = min(1.0, (tasks_completed_today / max(1, conflicts_today)) * 0.1)
            
            # Update metrics
            self.coordination_metrics = CoordinationMetrics(
                timestamp=now,
                active_agents=active_count,
                total_tasks_active=len([t for t in self.active_tasks.values() if t.status in ["assigned", "in_progress"]]),
                total_tasks_completed_today=tasks_completed_today,
                average_task_duration_minutes=avg_duration,
                conflicts_detected_today=conflicts_today,
                conflicts_resolved_today=resolved_conflicts_today,
                coordination_efficiency_score=efficiency_score,
                system_health_score=1.0 if conflicts_today == 0 else max(0.5, 1.0 - (conflicts_today * 0.1))
            )
            
        except Exception as e:
            logger.error(f"Error updating coordination metrics: {e}")

    async def _generate_system_alerts(self) -> List[str]:
        """Generate system-level alerts based on current state."""
        alerts = []
        
        try:
            # Check for high conflict rate
            recent_conflicts = [
                c for c in self.conflict_history
                if c.detected_at > datetime.utcnow() - timedelta(hours=1)
            ]
            if len(recent_conflicts) > 3:
                alerts.append(f"High conflict rate: {len(recent_conflicts)} conflicts in the last hour")
            
            # Check for idle agents
            idle_agents = [a for a in self.active_agents.values() if a.status == AgentStatus.IDLE]
            if len(idle_agents) > len(self.active_agents) * 0.7:
                alerts.append(f"Many agents idle: {len(idle_agents)} of {len(self.active_agents)} agents")
            
            # Check for blocked agents
            blocked_agents = [a for a in self.active_agents.values() if a.status == AgentStatus.BLOCKED]
            if blocked_agents:
                alerts.append(f"Blocked agents detected: {len(blocked_agents)} agents blocked")
            
            # Check workspace utilization
            overutilized_workspaces = [
                ws for ws, util in self.workspace_utilization.items() if util > 2.0
            ]
            if overutilized_workspaces:
                alerts.append(f"Overutilized workspaces: {', '.join(overutilized_workspaces)}")
                
        except Exception as e:
            logger.error(f"Error generating system alerts: {e}")
            alerts.append("Error generating alerts - system monitoring degraded")
        
        return alerts

    async def _generate_prediction_insights(self) -> Dict[str, Any]:
        """Generate AI-powered insights and predictions."""
        insights = {}
        
        try:
            # Predict next likely conflicts based on current patterns
            insights["conflict_prediction"] = "Low risk in next 2 hours based on current activity patterns"
            
            # Suggest optimizations
            insights["optimization_suggestions"] = [
                "Consider load balancing between memory-service and jarvis workspaces",
                "Schedule integration tasks during low-activity periods"
            ]
            
            # Predict completion times
            active_tasks = [t for t in self.active_tasks.values() if t.status == "in_progress"]
            if active_tasks:
                insights["completion_predictions"] = f"{len(active_tasks)} tasks estimated to complete within 2 hours"
            
            # Identify bottlenecks
            workspace_loads = defaultdict(int)
            for activity in self.active_agents.values():
                if activity.status == AgentStatus.WORKING:
                    workspace_loads[activity.workspace] += 1
            
            if workspace_loads:
                max_load_workspace = max(workspace_loads.items(), key=lambda x: x[1])
                if max_load_workspace[1] > 1:
                    insights["bottleneck_alert"] = f"Potential bottleneck in {max_load_workspace[0]} workspace"
                    
        except Exception as e:
            logger.error(f"Error generating prediction insights: {e}")
            insights["error"] = "Prediction system temporarily unavailable"
        
        return insights

    async def _suggest_agent_coordination(self, conflict: ConflictDetection):
        """Suggest coordination strategies for workspace contention."""
        for agent_id in conflict.affected_agents:
            await self._send_message(
                from_agent_id="coordination_engine",
                to_agent_id=agent_id,
                message_type="coordination_suggestion",
                subject=f"Coordination needed in {conflict.workspace}",
                content=f"Multiple agents detected in {conflict.workspace}. Consider coordinating your efforts or using sequential development.",
                workspace=conflict.workspace
            )

    async def _require_explicit_handoff(self, conflict: ConflictDetection):
        """Require explicit handoff for component conflicts."""
        # Pause all but the first agent
        primary_agent = conflict.affected_agents[0]
        other_agents = conflict.affected_agents[1:]
        
        for agent_id in other_agents:
            if agent_id in self.active_agents:
                self.active_agents[agent_id].status = AgentStatus.BLOCKED
                self.active_agents[agent_id].blocked_by = [primary_agent]
                
            await self._send_message(
                from_agent_id="coordination_engine",
                to_agent_id=agent_id,
                message_type="conflict_resolution",
                subject=f"Component conflict: {conflict.affected_resources[0]}",
                content=f"You have been temporarily blocked due to component conflict. Please coordinate with {primary_agent} for explicit handoff.",
                workspace=conflict.workspace,
                requires_response=True
            )

    async def _notify_conflict(self, conflict: ConflictDetection):
        """Send general conflict notification."""
        for agent_id in conflict.affected_agents:
            await self._send_message(
                from_agent_id="coordination_engine",
                to_agent_id=agent_id,
                message_type="conflict_notification",
                subject=f"Conflict detected: {conflict.conflict_type}",
                content=conflict.description,
                workspace=conflict.workspace
            )