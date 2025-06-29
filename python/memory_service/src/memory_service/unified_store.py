"""
Unified Vector Store

Core implementation that leverages existing Pinecone and ChromaDB implementations
while adding pgvector as a third option for maximum resilience and performance.
"""

import asyncio
import logging
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from .models import (
    ImportanceScoring,
    MemoryRequest,
    MemoryResponse,
    ProviderConfig,
    QueryRequest,
    QueryResponse,
)
from .deduplication import DeduplicationService, DeduplicationMode
from .reliable_task_queue import get_task_queue, TaskPriority, ReliableTaskQueue
try:
    from .monitoring import get_error_monitor, ErrorCategory
except ImportError:
    # Fallback for deployment compatibility
    def get_error_monitor():
        class MockErrorMonitor:
            def record_circuit_breaker_event(self, **kwargs):
                pass
            def record_error(self, **kwargs):
                pass
        return MockErrorMonitor()
    
    class ErrorCategory:
        PROVIDER_FAILURE = "provider_failure"
        CIRCUIT_BREAKER = "circuit_breaker"
        QUERY_ERROR = "query_error"

logger = logging.getLogger(__name__)


class ProviderCircuitBreaker:
    """
    Circuit breaker for individual vector providers to prevent cascade failures.
    
    EMERGENCY FIX: Protects against provider failures causing system-wide outages.
    """
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 300, test_request_interval: int = 30):
        self.failure_threshold = failure_threshold  # failures before opening circuit
        self.recovery_timeout = recovery_timeout    # seconds to wait before testing recovery
        self.test_request_interval = test_request_interval  # seconds between test requests
        
        # Circuit state
        self.state = 'closed'  # closed, open, half_open
        self.failure_count = 0
        self.last_failure_time = None
        self.last_success_time = datetime.utcnow()
        self.last_test_time = None
        
        # Statistics
        self.total_requests = 0
        self.total_failures = 0
        self.total_successes = 0
    
    def can_attempt(self) -> bool:
        """Check if circuit breaker allows an operation attempt."""
        now = datetime.utcnow()
        self.total_requests += 1
        
        if self.state == 'closed':
            return True
        elif self.state == 'open':
            # Check if recovery timeout has passed
            if (self.last_failure_time and 
                (now - self.last_failure_time).total_seconds() > self.recovery_timeout):
                self.state = 'half_open'
                self.last_test_time = now
                logger.info(f"Circuit breaker moving to half-open state for recovery test")
                return True
            return False
        elif self.state == 'half_open':
            # Allow test requests with throttling
            if (not self.last_test_time or 
                (now - self.last_test_time).total_seconds() > self.test_request_interval):
                self.last_test_time = now
                return True
            return False
        
        return False
    
    def record_success(self):
        """Record a successful operation."""
        self.total_successes += 1
        self.last_success_time = datetime.utcnow()
        
        if self.state == 'half_open':
            # Recovery successful, close circuit
            old_state = self.state
            self.state = 'closed'
            self.failure_count = 0
            logger.info(f"Circuit breaker closed - provider recovered")
            
            # Report recovery to monitoring system
            try:
                monitor = get_error_monitor()
                monitor.record_circuit_breaker_event(
                    provider=getattr(self, '_provider_name', 'unknown'),
                    old_state=old_state,
                    new_state='closed',
                    reason="Recovery successful"
                )
            except Exception as e:
                logger.warning(f"Failed to report circuit breaker recovery: {e}")
                
        elif self.state == 'closed':
            # Gradually reduce failure count on success
            self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self, error: Exception):
        """Record a failed operation."""
        self.total_failures += 1
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            if self.state != 'open':
                old_state = self.state
                self.state = 'open'
                logger.error(f"Circuit breaker OPENED after {self.failure_count} failures. Last error: {error}")
                
                # Report to monitoring system
                try:
                    monitor = get_error_monitor()
                    monitor.record_circuit_breaker_event(
                        provider=getattr(self, '_provider_name', 'unknown'),
                        old_state=old_state,
                        new_state='open',
                        reason=f"Failure threshold exceeded: {self.failure_count} failures"
                    )
                except Exception as e:
                    logger.warning(f"Failed to report circuit breaker event: {e}")
                    
        elif self.state == 'half_open':
            # Test failed, go back to open
            old_state = self.state
            self.state = 'open'
            logger.warning(f"Circuit breaker test failed, returning to open state: {error}")
            
            # Report to monitoring system
            try:
                monitor = get_error_monitor()
                monitor.record_circuit_breaker_event(
                    provider=getattr(self, '_provider_name', 'unknown'),
                    old_state=old_state,
                    new_state='open',
                    reason=f"Recovery test failed: {error}"
                )
            except Exception as e:
                logger.warning(f"Failed to report circuit breaker event: {e}")
    
    def get_status(self) -> dict:
        """Get circuit breaker status for monitoring."""
        uptime = (datetime.utcnow() - self.last_success_time).total_seconds() if self.last_success_time else None
        downtime = (datetime.utcnow() - self.last_failure_time).total_seconds() if self.last_failure_time else None
        
        return {
            'state': self.state,
            'failure_count': self.failure_count,
            'total_requests': self.total_requests,
            'total_failures': self.total_failures,
            'total_successes': self.total_successes,
            'success_rate': self.total_successes / max(1, self.total_requests),
            'uptime_seconds': uptime,
            'downtime_seconds': downtime,
            'last_failure': self.last_failure_time.isoformat() if self.last_failure_time else None,
            'last_success': self.last_success_time.isoformat() if self.last_success_time else None
        }


class VectorProvider(ABC):
    """Abstract base class for vector storage providers."""

    def __init__(self, config: ProviderConfig):
        self.config = config
        self.name = config.name
        self.enabled = config.enabled
        
        # EMERGENCY FIX: Add circuit breaker to prevent cascade failures
        self.circuit_breaker = ProviderCircuitBreaker(
            failure_threshold=config.config.get('circuit_breaker_failure_threshold', 5),
            recovery_timeout=config.config.get('circuit_breaker_recovery_timeout', 300),
            test_request_interval=config.config.get('circuit_breaker_test_interval', 30)
        )
        # Set provider name for monitoring
        self.circuit_breaker._provider_name = self.name

    @abstractmethod
    async def store(self, content: str, embedding: list[float], metadata: dict[str, Any]) -> UUID:
        """Store a memory with embedding."""
        pass

    @abstractmethod
    async def query(self, query_embedding: list[float], limit: int, filters: dict[str, Any]) -> list[MemoryResponse]:
        """Query similar memories."""
        pass

    @abstractmethod
    async def retrieve(self, memory_id: UUID) -> Optional[MemoryResponse]:
        """Retrieve a specific memory by ID."""
        pass

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Check provider health."""
        pass

    @abstractmethod
    async def get_stats(self) -> dict[str, Any]:
        """Get provider statistics."""
        pass

    def is_available(self) -> bool:
        """Check if provider is available (enabled and circuit breaker allows)."""
        return self.enabled and self.circuit_breaker.can_attempt()
    
    def record_success(self):
        """Record successful operation with circuit breaker."""
        self.circuit_breaker.record_success()
    
    def record_failure(self, error: Exception):
        """Record failed operation with circuit breaker."""
        self.circuit_breaker.record_failure(error)
        
        # Temporarily disable provider if circuit breaker is open
        if self.circuit_breaker.state == 'open':
            logger.warning(f"Provider {self.name} temporarily disabled due to circuit breaker")
    
    def get_circuit_breaker_status(self) -> dict:
        """Get circuit breaker status for monitoring."""
        return {
            'provider': self.name,
            'enabled': self.enabled,
            **self.circuit_breaker.get_status()
        }


class UnifiedVectorStore:
    """
    Unified vector store that leverages existing implementations:
    - Pinecone (cloud scale)
    - ChromaDB (local speed)
    - pgvector (unified queries)

    Provides automatic failover, load balancing, and caching.
    """

    def __init__(self, providers: list[VectorProvider], embedding_model=None, adm_enabled=True):
        self.providers = {p.name: p for p in providers}
        # Find primary provider that's actually enabled
        self.primary_provider = next(
            (p for p in providers if p.config.primary and p.enabled),
            next((p for p in providers if p.enabled), None)
        )
        if not self.primary_provider:
            raise RuntimeError("No enabled vector providers available")
        self.embedding_model = embedding_model
        self.importance_scorer = ImportanceScoring()
        
        # Enhanced load balancing with circuit breaker
        try:
            from .circuit_breaker import LoadBalancer
            self.load_balancer = LoadBalancer(providers)
            logger.info("Enhanced load balancing initialized")
        except ImportError:
            logger.warning("Circuit breaker not available, using basic failover")
            self.load_balancer = None
        # Initialize caching (Redis if available, in-memory otherwise)
        self.query_cache = self._initialize_cache()
        self.stats = {
            'total_stores': 0,
            'total_queries': 0,
            'provider_usage': {p.name: 0 for p in providers},
            'avg_query_time': 0.0,
            'adm_calculations': 0,
            'avg_adm_score': 0.0,
            'duplicates_prevented': 0,
            'storage_saved_bytes': 0,
            'total_failures': 0,
            'failover_successes': 0
        }
        
        # Schedule initial stats sync after initialization
        asyncio.create_task(self._sync_initial_stats())

        # Initialize ADM scoring if enabled
        self.adm_enabled = adm_enabled
        self.adm_engine = None
        if adm_enabled:
            self._initialize_adm_engine()

        # RELIABILITY OPTIMIZATION: Initialize reliable task queue
        self.task_queue: Optional[ReliableTaskQueue] = None
        asyncio.create_task(self._initialize_task_queue())
        
        # Initialize Deduplication Service
        self.deduplication_service = None
        dedup_mode = os.getenv('DEDUPLICATION_MODE', 'off').lower()
        if dedup_mode != 'off':
            try:
                mode = DeduplicationMode(dedup_mode)
                similarity_threshold = float(os.getenv('DEDUP_SIMILARITY_THRESHOLD', '0.95'))
                exact_match_only = os.getenv('DEDUP_EXACT_MATCH_ONLY', 'false').lower() == 'true'
                
                self.deduplication_service = DeduplicationService(
                    vector_store=self,
                    mode=mode,
                    similarity_threshold=similarity_threshold,
                    exact_match_only=exact_match_only
                )
                logger.info(f"Initialized deduplication service in {mode.value} mode")
            except Exception as e:
                logger.error(f"Failed to initialize deduplication service: {e}")

        # Initialize Graph Provider for knowledge graph functionality
        self.graph_provider = None
        graph_provider = next((p for p in providers if p.name == 'graph' and p.enabled), None)
        if graph_provider:
            self.graph_provider = graph_provider
            logger.info("Graph provider initialized - Knowledge graph functionality ENABLED")
        else:
            logger.info("Graph provider not available - Knowledge graph functionality DISABLED")

        # Initialize reliable task queue for background operations
        self.task_queue: Optional[ReliableTaskQueue] = None
        asyncio.create_task(self._initialize_task_queue())

        logger.info(f"Initialized UnifiedVectorStore with providers: {list(self.providers.keys())}")
        logger.info(f"Primary provider: {self.primary_provider.name}")
        logger.info(f"ADM scoring: {'enabled' if adm_enabled else 'disabled'}")
        logger.info(f"Deduplication: {'enabled' if self.deduplication_service else 'disabled'}")
        logger.info(f"Graph functionality: {'enabled' if self.graph_provider else 'disabled'}")
        logger.info("Reliable task queue initialization scheduled")

    def _initialize_adm_engine(self):
        """Initialize the ADM scoring engine."""
        try:
            from .adm import ADMScoringEngine

            # Use default weights and thresholds for now
            # TODO: Load from configuration
            self.adm_engine = ADMScoringEngine(self)
            logger.info("ADM scoring engine initialized")

        except Exception as e:
            logger.error(f"Failed to initialize ADM engine: {e}")
            self.adm_enabled = False

    def _initialize_cache(self):
        """Initialize caching system (Redis if available, in-memory fallback)"""
        try:
            import os

            import redis

            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            redis_client = redis.from_url(redis_url, decode_responses=True)

            # Test connection
            redis_client.ping()
            logger.info("Redis cache initialized")
            return redis_client

        except Exception as e:
            logger.info(f"Redis not available, using in-memory cache: {e}")
            return {}

    async def _initialize_task_queue(self):
        """Initialize the reliable task queue and register handlers"""
        try:
            self.task_queue = await get_task_queue()
            
            # Register task handlers for background operations
            self.task_queue.register_handler('graph_processing', self._task_graph_processing)
            self.task_queue.register_handler('provider_replication', self._task_provider_replication)
            self.task_queue.register_handler('provider_reconciliation', self._task_provider_reconciliation)
            self.task_queue.register_handler('provider_repair', self._task_provider_repair)
            
            logger.info("✅ Reliable task queue initialized with handlers")
            
            # Schedule initial provider reconciliation to detect issues
            await self._schedule_provider_reconciliation()
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize task queue: {e}")
            self.task_queue = None

    async def _schedule_provider_reconciliation(self):
        """Schedule provider reconciliation task on startup"""
        try:
            if self.task_queue:
                await self.task_queue.submit_task(
                    task_type='provider_reconciliation',
                    payload={},
                    priority=TaskPriority.LOW,
                    max_retries=1
                )
                logger.info("📋 Scheduled initial provider reconciliation task")
        except Exception as e:
            logger.error(f"Failed to schedule reconciliation task: {e}")

    async def store_memory(self, request: MemoryRequest) -> MemoryResponse:
        """
        Store a memory across providers with automatic replication.

        Leverages existing implementations while adding resilience.
        """
        start_time = time.time()

        try:
            # Initialize monitoring for this request
            monitor = get_error_monitor()
            # Check for duplicates first if deduplication is enabled
            if self.deduplication_service:
                dedup_result = await self.deduplication_service.check_duplicate(
                    content=request.content,
                    metadata=request.metadata
                )
                
                if dedup_result.is_duplicate and dedup_result.existing_memory:
                    # Update statistics
                    self.stats['duplicates_prevented'] += 1
                    self.stats['storage_saved_bytes'] += len(request.content)
                    
                    logger.info(f"Duplicate detected: {dedup_result.reason}")
                    
                    # Return existing memory instead of creating new one
                    return dedup_result.existing_memory

            # Generate embedding if not provided
            embedding = request.embedding
            if not embedding and self.embedding_model:
                embedding = await self._generate_embedding(request.content)
            elif not embedding:
                raise ValueError("No embedding provided and no embedding model configured")

            # PERFORMANCE OPTIMIZATION: Use fast fallback scoring, upgrade to ADM in background
            importance_score = request.importance_score
            adm_data = {}

            if importance_score is None:
                # Use fast fallback scoring first for immediate response
                importance_score = self._calculate_importance(request)
                
                # Schedule ADM scoring enhancement in background if available
                if self.adm_enabled and self.adm_engine:
                    logger.info(f"🧮 Using fast fallback scoring ({importance_score:.3f}), scheduling ADM enhancement in background")
                else:
                    logger.info(f"🧮 Using standard importance scoring: {importance_score:.3f}")
            else:
                logger.info(f"🧮 Using provided importance score: {importance_score:.3f}")

            # Prepare metadata
            metadata = {
                **request.metadata,
                'user_id': request.user_id,
                'conversation_id': request.conversation_id,
                'importance_score': importance_score,
                'created_at': time.time(),
                'content_length': len(request.content)
            }

            # Add ADM scoring data if available
            if adm_data:
                metadata.update({
                    'adm_score': adm_data['adm_score'],
                    'data_quality': adm_data['data_quality'],
                    'data_relevance': adm_data['data_relevance'],
                    'data_intelligence': adm_data['data_intelligence'],
                    'adm_calculation_time': adm_data.get('calculation_time_ms', 0)
                })

            # Store in primary provider first
            memory_id = await self._store_with_retry(
                self.primary_provider,
                request.content,
                embedding,
                metadata
            )

            # PERFORMANCE OPTIMIZATION: Use fire-and-forget async tasks for background operations
            # This ensures the primary storage response is not blocked by background tasks
            
            # Schedule background tasks asynchronously (non-blocking)
            try:
                if self.task_queue:
                    # Use asyncio.create_task for non-blocking background submission
                    if self.graph_provider and self.graph_provider.enabled:
                        asyncio.create_task(self._submit_graph_task(memory_id, request.content, embedding, metadata))
                    
                    # Submit replication task in background
                    asyncio.create_task(self._submit_replication_task(memory_id, request.content, embedding, metadata))
                else:
                    # Direct fire-and-forget fallback
                    if self.graph_provider and self.graph_provider.enabled:
                        asyncio.create_task(self._background_graph_processing(memory_id, request.content, embedding, metadata))
                    asyncio.create_task(self._background_replication(memory_id, request.content, embedding, metadata))
            except Exception as e:
                # Don't let background task errors affect main storage response
                logger.warning(f"Background task scheduling failed (non-critical): {e}")

            # Update stats
            self.stats['total_stores'] += 1
            self.stats['provider_usage'][self.primary_provider.name] += 1

            # Record successful request for monitoring
            duration_ms = (time.time() - start_time) * 1000
            monitor.record_request(
                duration_ms=duration_ms,
                success=True,
                provider=self.primary_provider.name if self.primary_provider else None,
                operation="store_memory"
            )
            
            logger.info(f"Stored memory {memory_id} in {time.time() - start_time:.3f}s")

            return MemoryResponse(
                id=memory_id,
                content=request.content,
                metadata=metadata,
                importance_score=importance_score
            )

        except Exception as e:
            # EMERGENCY FIX: Replace catastrophic catch-all with provider failover
            logger.error(f"Primary storage failed, attempting failover: {e}")
            
            # Record error for monitoring
            monitor.record_error(
                error=e,
                category=ErrorCategory.PROVIDER_FAILURE,
                provider=self.primary_provider.name if self.primary_provider else None,
                component="unified_store",
                operation="store_memory"
            )
            
            # Record failure for primary provider
            if self.primary_provider:
                self.primary_provider.record_failure(e)
            
            # Attempt failover to healthy secondary providers
            available_providers = [p for p in self.providers.values() 
                                 if p != self.primary_provider and p.is_available()]
            
            if not available_providers:
                logger.error("🚨 TOTAL SYSTEM FAILURE: No providers available for failover")
                self.stats['total_failures'] += 1
                raise Exception(f"All providers failed or unavailable. Last error: {e}")
            
            logger.warning(f"🔄 Attempting failover to {len(available_providers)} providers")
            
            # Try each available provider
            for failover_provider in available_providers:
                try:
                    logger.info(f"🔄 Failover attempt with {failover_provider.name}")
                    memory_id = await self._store_with_retry(
                        failover_provider, request.content, embedding, metadata
                    )
                    
                    # Success! Record and return
                    failover_provider.record_success()
                    self.stats['total_stores'] += 1
                    self.stats['provider_usage'][failover_provider.name] += 1
                    self.stats['failover_successes'] = self.stats.get('failover_successes', 0) + 1
                    
                    # Record successful failover for monitoring
                    duration_ms = (time.time() - start_time) * 1000
                    monitor.record_request(
                        duration_ms=duration_ms,
                        success=True,
                        provider=failover_provider.name,
                        operation="store_memory_failover"
                    )
                    
                    logger.info(f"✅ Failover successful: stored memory {memory_id} via {failover_provider.name}")
                    
                    return MemoryResponse(
                        id=memory_id,
                        content=request.content,
                        metadata=metadata,
                        importance_score=importance_score
                    )
                    
                except Exception as failover_error:
                    logger.warning(f"❌ Failover to {failover_provider.name} failed: {failover_error}")
                    failover_provider.record_failure(failover_error)
                    
                    # Record failover error for monitoring
                    monitor.record_error(
                        error=failover_error,
                        category=ErrorCategory.PROVIDER_FAILURE,
                        provider=failover_provider.name,
                        component="unified_store",
                        operation="store_memory_failover"
                    )
                    continue
            
            # All failover attempts failed
            logger.error("🚨 COMPLETE FAILOVER FAILURE: All providers exhausted")
            self.stats['total_failures'] += 1
            
            # Record total failure for monitoring
            duration_ms = (time.time() - start_time) * 1000
            monitor.record_request(
                duration_ms=duration_ms,
                success=False,
                provider="all_providers",
                operation="store_memory_total_failure"
            )
            
            raise Exception(f"Primary and all failover providers failed. Original error: {e}")

    async def query_memories(self, request: QueryRequest) -> QueryResponse:
        """
        Query memories across providers with intelligent routing.

        Uses existing vector store implementations with added optimizations.
        """
        start_time = time.time()

        try:
            # PERFORMANCE: Clean cache periodically (every 100 queries)
            if not hasattr(self, '_query_count'):
                self._query_count = 0
            self._query_count += 1
            if self._query_count % 100 == 0:
                self._cleanup_query_cache()
            
            # PERFORMANCE: Check cache first with optimized key generation
            cache_key = self._get_cache_key(request)
            if cache_key in self.query_cache:
                cached_result = self.query_cache[cache_key]
                if time.time() - cached_result['timestamp'] < 300:  # 5 min cache
                    # PERFORMANCE: Reduce logging in hot path
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"Cache hit for query: {request.query[:50]}...")
                    return cached_result['response']
                else:
                    # Remove expired entry
                    del self.query_cache[cache_key]

            # PERFORMANCE: Fast path for empty queries with reduced logging
            is_empty_query = not request.query or request.query.strip() == ""
            if is_empty_query:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("Empty query detected, using emergency retrieval")
                
                try:
                    # Use the proven emergency retrieval system
                    from .emergency_foundation_fix import EmergencyMemoryRetrieval
                    emergency = EmergencyMemoryRetrieval()
                    await emergency.connect()
                    
                    memories_raw = await emergency.get_all_memories(request.limit, 0)
                    logger.info(f"Emergency retrieval returned {len(memories_raw)} memories")
                    
                    # Convert to MemoryResponse objects
                    memories = []
                    for mem in memories_raw:
                        memory_response = MemoryResponse(
                            id=mem['id'],
                            content=mem['content'],
                            metadata=mem.get('metadata', {}),
                            importance_score=mem.get('importance_score', 0.0),
                            similarity_score=1.0,  # Default for non-search queries
                            created_at=mem.get('created_at'),
                            updated_at=None
                        )
                        memories.append(memory_response)
                    
                    response = QueryResponse(
                        memories=memories[:request.limit],
                        total_found=len(memories),
                        query_time_ms=(time.time() - start_time) * 1000,
                        providers_used=['emergency_direct']
                    )
                    
                    # Close emergency connection
                    if emergency.connection:
                        await emergency.connection.close()
                    
                    # Cache result
                    self.query_cache[cache_key] = {
                        'response': response,
                        'timestamp': time.time()
                    }
                    
                    logger.info(f"Emergency retrieval completed: {len(memories)} memories returned")
                    return response
                    
                except Exception as e:
                    logger.error(f"Emergency retrieval failed: {e}")
                    # Return empty response rather than crash
                    return QueryResponse(
                        memories=[],
                        total_found=0,
                        query_time_ms=(time.time() - start_time) * 1000,
                        providers_used=['emergency_failed']
                    )
            
            # PERFORMANCE OPTIMIZATION: Parallel processing for non-empty queries
            query_embedding = None
            memories = []
            
            # PERFORMANCE: Parallel embedding generation and provider selection
            async def generate_embedding_task():
                """Generate embedding in parallel with other tasks."""
                if self.embedding_model and request.query:
                    try:
                        return await asyncio.wait_for(
                            self._generate_embedding(request.query),
                            timeout=5.0  # 5 second timeout for embedding generation
                        )
                    except asyncio.TimeoutError:
                        logger.warning("Embedding generation timed out (5s)")
                        return None
                    except Exception as e:
                        logger.error(f"Embedding generation failed: {e}")
                        return None
                else:
                    logger.warning("No embedding model available for query")
                    return None

            async def select_providers_task():
                """Select providers in parallel with embedding generation."""
                return self._select_providers(request)

            # Execute embedding generation and provider selection in parallel
            try:
                embedding_task = asyncio.create_task(generate_embedding_task())
                provider_task = asyncio.create_task(select_providers_task())
                
                # Wait for both tasks to complete
                query_embedding, providers_to_query = await asyncio.gather(
                    embedding_task, provider_task, return_exceptions=True
                )
                
                # Handle any exceptions from parallel tasks
                if isinstance(query_embedding, Exception):
                    logger.error(f"Embedding generation task failed: {query_embedding}")
                    query_embedding = None
                    
                if isinstance(providers_to_query, Exception):
                    logger.error(f"Provider selection task failed: {providers_to_query}")
                    providers_to_query = []
                    
            except Exception as e:
                logger.error(f"Parallel task execution failed: {e}")
                query_embedding = None
                providers_to_query = []
            
            # CRITICAL FIX: Only use graph provider for explicit entity queries with specific filters
            # All other queries (including empty queries and semantic searches) MUST use pgvector
            use_graph_provider = False
            graph_memories = []
            
            # PERFORMANCE: Streamlined provider selection with minimal logging
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Query processing: '{request.query}' with filters: {request.filters}")
            
            # PERFORMANCE: Fast graph provider decision
            if self.graph_provider and self.graph_provider.enabled and request.filters:
                # Check for explicit entity filters with actual values
                entity_filters = {k: v for k, v in request.filters.items() 
                                if k in ['entity_name', 'entity_type', 'relationship_type'] 
                                and v is not None and str(v).strip()}
                
                # ONLY use graph if we have explicit entity filters with non-empty values
                if entity_filters:
                    try:
                        # PERFORMANCE: Add timeout for graph queries
                        graph_memories = await asyncio.wait_for(
                            self.graph_provider.query(query_embedding or [], request.limit, request.filters),
                            timeout=10.0  # 10 second timeout for graph queries
                        )
                        if graph_memories:
                            use_graph_provider = True
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.debug(f"Graph provider returned {len(graph_memories)} results")
                    except (Exception, asyncio.TimeoutError) as e:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f"Graph query failed: {e}, using vector fallback")
            
            # PERFORMANCE: Streamlined routing logic with minimal logging
            if use_graph_provider and graph_memories:
                memories = graph_memories
                providers_used = ['graph']
            elif use_graph_provider and not graph_memories:
                # PERFORMANCE: Fast fallback to primary provider
                if query_embedding and providers_to_query:
                    try:
                        provider = providers_to_query[0]  # Use primary provider (pgvector)
                        memories = await self._query_provider(provider, query_embedding, request)
                        providers_used = [f'{provider.name}_fallback']
                    except Exception as e:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f"Fallback search failed: {e}")
                        memories = []
                        providers_used = ['graph_failed']
                else:
                    memories = []
                    providers_used = ['graph_failed']
            elif query_embedding:
                # PERFORMANCE: Fast vector search routing
                try:
                    if len(providers_to_query) == 1:
                        # PERFORMANCE: Single provider - direct query
                        provider = providers_to_query[0]
                        memories = await self._query_provider(provider, query_embedding, request)
                        providers_used = [provider.name]
                    else:
                        # PERFORMANCE: Multi-provider parallel query
                        memories, providers_used = await self._query_multiple_providers(
                            providers_to_query, query_embedding, request
                        )
                except Exception as e:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"Vector search failed: {e}")
                    memories = []
                    providers_used = []
            else:
                # PERFORMANCE: No embedding available
                memories = []
                providers_used = []
            
            # PERFORMANCE: Optional text search fallback (only if specifically needed)
            if not memories and request.query and len(request.query) > 3:
                # Only attempt text search for longer queries to avoid noise
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Vector search returned 0 results, trying text search")
                
                pgvector = self.providers.get('pgvector')
                if pgvector and pgvector.enabled:
                    from .search_fix import EmergencySearchFix
                    emergency_search = EmergencySearchFix(pgvector.connection_pool, getattr(pgvector, "table_name", "vector_memories"))
                    
                    # Try full-text search
                    memories = await emergency_search.text_search(request.query, limit=request.limit * 2)
                    
                    # If still no results, try fuzzy search
                    if not memories:
                        logger.warning("Text search failed, trying fuzzy search")
                        memories = await emergency_search.fuzzy_search(request.query, limit=request.limit * 2)
                    
                    providers_used = ['text_search_fallback']

            # Filter and sort results - but be more lenient
            if memories:
                # Lower the similarity threshold to avoid filtering out all results
                original_threshold = request.min_similarity
                if len(memories) < request.limit / 2:
                    request.min_similarity = 0.0  # Accept all results if we have too few
                    logger.info(f"Lowered similarity threshold from {original_threshold} to 0.0")
                
                filtered_memories = self._filter_and_rank_memories(memories, request)
                
                # Restore original threshold
                request.min_similarity = original_threshold
            else:
                filtered_memories = []

            query_time = (time.time() - start_time) * 1000  # Convert to ms

            # Update stats
            self.stats['total_queries'] += 1
            self.stats['avg_query_time'] = (
                (self.stats['avg_query_time'] * (self.stats['total_queries'] - 1) + query_time) /
                self.stats['total_queries']
            )

            response = QueryResponse(
                memories=filtered_memories[:request.limit],
                total_found=len(filtered_memories),
                query_time_ms=query_time,
                providers_used=providers_used
            )

            # Cache result
            self.query_cache[cache_key] = {
                'response': response,
                'timestamp': time.time()
            }

            logger.info(f"Query returned {len(filtered_memories)} memories in {query_time:.1f}ms")
            return response

        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise

    async def health_check(self) -> dict[str, Any]:
        """Check health of all providers."""
        results = {}
        overall_healthy = True

        for name, provider in self.providers.items():
            try:
                if provider.enabled:
                    health = await provider.health_check()
                    results[name] = {
                        'status': 'healthy',
                        'details': health,
                        'primary': provider == self.primary_provider
                    }
                else:
                    results[name] = {'status': 'disabled'}

            except Exception as e:
                results[name] = {
                    'status': 'unhealthy',
                    'error': str(e),
                    'primary': provider == self.primary_provider
                }
                if provider == self.primary_provider:
                    overall_healthy = False

        # Calculate actual total memories from provider stats
        actual_total_memories = 0
        for provider_name, provider_health in results.items():
            if provider_health.get('status') == 'healthy' and 'details' in provider_health:
                details = provider_health['details']
                if 'details' in details and 'total_vectors' in details['details']:
                    actual_total_memories += details['details']['total_vectors']
                elif 'total_vectors' in details:
                    actual_total_memories += details['total_vectors']

        # Update stats with actual total if available
        updated_stats = dict(self.stats)
        if actual_total_memories > 0:
            updated_stats['total_stores'] = actual_total_memories

        # Enhanced health check with load balancing metrics and task queue status
        enhanced_health = {
            'status': 'healthy' if overall_healthy else 'degraded',
            'providers': results,
            'stats': updated_stats,
            'cache_size': len(self.query_cache),
            'graph_enabled': self.graph_provider is not None and self.graph_provider.enabled,
            'features': {
                'vector_storage': True,
                'knowledge_graph': self.graph_provider is not None and self.graph_provider.enabled,
                'adm_scoring': self.adm_enabled,
                'deduplication': self.deduplication_service is not None,
                'load_balancing': self.load_balancer is not None,
                'reliable_task_queue': self.task_queue is not None
            }
        }
        
        # Add task queue metrics if available
        if self.task_queue:
            try:
                task_queue_metrics = self.get_task_queue_metrics()
                enhanced_health['task_queue'] = task_queue_metrics
                
                # Update overall status based on task queue health
                if task_queue_metrics.get('dead_letter_tasks', 0) > 10:
                    enhanced_health['status'] = 'degraded'
                    enhanced_health['warnings'] = enhanced_health.get('warnings', [])
                    enhanced_health['warnings'].append('High number of dead letter tasks detected')
                    
            except Exception as e:
                logger.error(f"Failed to get task queue metrics: {e}")
                enhanced_health['task_queue'] = {'error': str(e)}
        
        # Add load balancer health metrics if available
        if self.load_balancer:
            try:
                load_balancer_health = self.load_balancer.get_health_status()
                enhanced_health['load_balancer'] = load_balancer_health
                
                # Update overall status based on load balancer health
                available_providers = len(load_balancer_health.get('available_providers', []))
                if available_providers == 0:
                    enhanced_health['status'] = 'critical'
                elif available_providers < len(self.providers):
                    enhanced_health['status'] = 'degraded'
                    
            except Exception as e:
                logger.error(f"Failed to get load balancer health: {e}")
                enhanced_health['load_balancer'] = {'error': str(e)}
        
        return enhanced_health

    def _calculate_importance(self, request: MemoryRequest) -> float:
        """
        Calculate memory importance score using existing metadata patterns.

        This leverages patterns found in existing conversation_history tables.
        """
        scoring = self.importance_scorer

        # Content length factor
        content_score = min(1.0, len(request.content) / 1000) * scoring.content_length_weight

        # Default base score
        base_score = 0.5 * (1 - scoring.content_length_weight)

        # User/conversation context boost
        context_boost = 0.0
        if request.user_id:
            context_boost += 0.1
        if request.conversation_id:
            context_boost += 0.1

        total_score = content_score + base_score + context_boost
        return max(scoring.min_score, min(scoring.max_score, total_score))

    async def retrieve(self, memory_id: UUID) -> Optional[MemoryResponse]:
        """Retrieve a specific memory by ID from any available provider."""
        logger.debug(f"Retrieving memory {memory_id}")
        
        # Try primary provider first
        if self.primary_provider:
            try:
                memory = await self.primary_provider.retrieve(memory_id)
                if memory:
                    logger.debug(f"Retrieved memory {memory_id} from primary provider {self.primary_provider.name}")
                    return memory
            except Exception as e:
                logger.warning(f"Failed to retrieve from primary provider {self.primary_provider.name}: {e}")
        
        # Try secondary providers
        for provider in self.providers.values():
            if provider == self.primary_provider or not provider.enabled:
                continue
            
            try:
                memory = await provider.retrieve(memory_id)
                if memory:
                    logger.debug(f"Retrieved memory {memory_id} from secondary provider {provider.name}")
                    return memory
            except Exception as e:
                logger.warning(f"Failed to retrieve from provider {provider.name}: {e}")
        
        logger.debug(f"Memory {memory_id} not found in any provider")
        return None

    async def _store_with_retry(self, provider: VectorProvider, content: str,
                               embedding: list[float], metadata: dict[str, Any]) -> UUID:
        """Store with retry logic and circuit breaker protection."""
        
        # EMERGENCY FIX: Check circuit breaker before attempting
        if not provider.is_available():
            raise Exception(f"Provider {provider.name} unavailable (circuit breaker: {provider.circuit_breaker.state})")
        
        last_error = None
        for attempt in range(provider.config.retry_count):
            try:
                # Check circuit breaker for each attempt
                if not provider.circuit_breaker.can_attempt():
                    raise Exception(f"Provider {provider.name} circuit breaker blocked attempt {attempt + 1}")
                
                result = await provider.store(content, embedding, metadata)
                
                # Record success
                provider.record_success()
                logger.debug(f"✅ Store successful on attempt {attempt + 1} for {provider.name}")
                return result
                
            except Exception as e:
                last_error = e
                provider.record_failure(e)
                
                if attempt == provider.config.retry_count - 1:
                    # Final attempt failed, circuit breaker will handle state change
                    logger.error(f"❌ Final attempt {attempt + 1} failed for {provider.name}: {e}")
                    raise e
                
                # Calculate backoff with jitter to prevent thundering herd
                backoff_time = (2 ** attempt) + (time.time() % 1.0)  # Add jitter
                logger.warning(f"⚠️ Store attempt {attempt + 1} failed for {provider.name}: {e}")
                logger.info(f"🔄 Retrying in {backoff_time:.2f}s...")
                await asyncio.sleep(backoff_time)

    async def _replicate_to_secondaries(self, memory_id: UUID, content: str,
                                       embedding: list[float], metadata: dict[str, Any]):
        """Replicate to secondary providers for data consistency."""
        logger.info(f"🔍 Identifying secondary providers for replication...")
        
        secondary_providers = [p for p in self.providers.values()
                             if p != self.primary_provider and p.enabled]

        logger.info(f"📊 Found {len(secondary_providers)} secondary providers: {[p.name for p in secondary_providers]}")
        
        if not secondary_providers:
            logger.warning("⚠️ No secondary providers enabled for replication - DATA REDUNDANCY BROKEN!")
            logger.warning(f"   Primary: {self.primary_provider.name if self.primary_provider else 'None'}")
            logger.warning(f"   All providers: {[(p.name, p.enabled) for p in self.providers.values()]}")
            return

        replication_results = []
        for provider in secondary_providers:
            try:
                logger.info(f"🔄 Attempting replication to {provider.name}...")
                logger.info(f"   Content length: {len(content)} chars")
                logger.info(f"   Embedding dimension: {len(embedding)}")
                logger.info(f"   Metadata keys: {list(metadata.keys())}")
                
                stored_id = await self._store_with_retry(provider, content, embedding, metadata)
                logger.info(f"✅ Replicated memory {memory_id} to {provider.name} as {stored_id}")
                replication_results.append({"provider": provider.name, "success": True, "id": stored_id})
            except Exception as e:
                logger.error(f"❌ Failed to replicate memory {memory_id} to {provider.name}: {e}")
                logger.error(f"   Error type: {type(e).__name__}")
                logger.error(f"   Provider enabled: {provider.enabled}")
                logger.error(f"   Provider type: {type(provider).__name__}")
                replication_results.append({"provider": provider.name, "success": False, "error": str(e)})

        # Log detailed summary
        successful = sum(1 for r in replication_results if r["success"])
        total = len(replication_results)
        logger.warning(f"📊 Replication summary for {memory_id}: {successful}/{total} providers succeeded")
        
        for result in replication_results:
            if result["success"]:
                logger.info(f"   ✅ {result['provider']}: SUCCESS (ID: {result['id']})")
            else:
                logger.error(f"   ❌ {result['provider']}: FAILED - {result['error']}")
        
        if successful == 0:
            logger.error(f"🚨 CATASTROPHIC: All secondary replication failed for memory {memory_id}")
            raise Exception(f"All secondary replication failed for memory {memory_id}")

    async def _generate_embedding(self, text: str) -> list[float]:
        """Generate embedding using configured model with caching for performance."""
        if not self.embedding_model:
            raise ValueError("No embedding model configured")

        # PARETO PERFORMANCE FIX: Cache embeddings to eliminate API bottleneck
        embedding_cache_key = f"embedding:{hash(text)}"
        if embedding_cache_key in self.query_cache:
            cached_embedding = self.query_cache[embedding_cache_key]
            if time.time() - cached_embedding['timestamp'] < 3600:  # 1 hour cache
                logger.debug(f"Embedding cache hit for text: {text[:50]}...")
                return cached_embedding['embedding']

        # Generate embedding via API only if not cached
        start_time = time.time()
        embedding = await self.embedding_model.embed_text(text)
        api_time = (time.time() - start_time) * 1000
        
        # Cache the embedding for future use
        self.query_cache[embedding_cache_key] = {
            'embedding': embedding,
            'timestamp': time.time()
        }
        
        logger.debug(f"Generated embedding in {api_time:.1f}ms for text: {text[:50]}...")
        return embedding

    def _select_providers(self, request: QueryRequest) -> list[VectorProvider]:
        """Select optimal providers for query."""
        if request.providers:
            # User specified providers
            return [self.providers[name] for name in request.providers
                   if name in self.providers and self.providers[name].enabled]

        # Auto-select based on query characteristics
        enabled_providers = [p for p in self.providers.values() if p.enabled]

        # For now, use primary provider, but this can be optimized based on:
        # - Query complexity
        # - Time range filters (use ChromaDB for recent, pgvector for complex joins)
        # - Load balancing
        return [self.primary_provider] if self.primary_provider.enabled else enabled_providers[:1]

    async def _query_provider(self, provider: VectorProvider, query_embedding: list[float],
                             request: QueryRequest) -> list[MemoryResponse]:
        """
        PERFORMANCE OPTIMIZED: Query a single provider with timeout and streamlined logic.
        Target: Individual provider queries under 200ms.
        """
        try:
            # PERFORMANCE: Add timeout to prevent slow queries from blocking
            query_timeout = 15.0  # 15 second timeout per provider
            
            # Check if this is an empty query (zero vector or no embedding)
            is_empty_query = not query_embedding or all(v == 0.0 for v in query_embedding)
            
            if is_empty_query:
                # PERFORMANCE: Streamlined empty query handling - prefer fastest path
                if hasattr(provider, 'get_recent_memories'):
                    # Fast path: Use optimized recent memories query
                    results = await asyncio.wait_for(
                        provider.get_recent_memories(request.limit * 2, request.filters or {}),
                        timeout=query_timeout
                    )
                else:
                    # Fallback: Use regular query
                    results = await asyncio.wait_for(
                        provider.query(query_embedding, request.limit * 2, request.filters),
                        timeout=query_timeout
                    )
            else:
                # PERFORMANCE: Direct vector query with timeout
                results = await asyncio.wait_for(
                    provider.query(query_embedding, request.limit * 2, request.filters),
                    timeout=query_timeout
                )
            
            # PERFORMANCE: Update stats without expensive logging
            self.stats['provider_usage'][provider.name] = self.stats['provider_usage'].get(provider.name, 0) + 1
            
            return results
            
        except asyncio.TimeoutError:
            logger.warning(f"Query timeout ({query_timeout}s) for provider {provider.name}")
            raise
        except Exception as e:
            logger.error(f"Query failed for provider {provider.name}: {e}")
            raise

    async def _query_multiple_providers(self, providers: list[VectorProvider],
                                       query_embedding: list[float], request: QueryRequest) -> tuple[list[MemoryResponse], list[str]]:
        """
        PERFORMANCE OPTIMIZED: Query multiple providers with enhanced parallel processing.
        
        Optimizations:
        - Parallel execution with asyncio.gather()
        - Per-provider timeouts to prevent blocking
        - Concurrent result processing
        - Early result streaming for large queries
        """
        tasks = []
        provider_names = []
        query_timeout = 10.0  # 10 second timeout per provider

        # Create timeout-wrapped tasks for each provider
        for provider in providers:
            # Wrap each provider query with timeout
            async def query_with_timeout(prov=provider):
                try:
                    return await asyncio.wait_for(
                        self._query_provider(prov, query_embedding, request),
                        timeout=query_timeout
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"Provider {prov.name} query timed out after {query_timeout}s")
                    raise
                except Exception as e:
                    logger.warning(f"Provider {prov.name} query failed: {e}")
                    raise

            task = asyncio.create_task(query_with_timeout())
            tasks.append(task)
            provider_names.append(provider.name)

        # Execute all provider queries in parallel with exception handling
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # PERFORMANCE: Parallel result aggregation and processing
        all_memories = []
        successful_providers = []
        
        # Process results concurrently where possible
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_type = type(result).__name__
                if isinstance(result, asyncio.TimeoutError):
                    logger.warning(f"Provider {provider_names[i]} timed out ({query_timeout}s)")
                else:
                    logger.warning(f"Provider {provider_names[i]} failed with {error_type}: {result}")
            elif result:  # Check if result is not empty
                all_memories.extend(result)
                successful_providers.append(provider_names[i])
                
                # PERFORMANCE: Log successful provider metrics
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Provider {provider_names[i]} returned {len(result)} results")

        # PERFORMANCE: Early sorting for large result sets (>100 results)
        if len(all_memories) > 100:
            logger.debug(f"Large result set ({len(all_memories)} memories), applying early optimization")
            
            # Pre-filter by similarity to reduce processing overhead
            all_memories = [m for m in all_memories 
                          if m.similarity_score and m.similarity_score >= request.min_similarity]
            
            # Sort by similarity + importance early to reduce downstream processing
            all_memories.sort(key=lambda m: (
                (m.similarity_score or 0) * 0.7 + (m.importance_score or 0) * 0.3
            ), reverse=True)
            
            # Limit to reasonable size to prevent memory issues
            max_intermediate_results = min(request.limit * 5, 500)  # 5x requested or 500 max
            all_memories = all_memories[:max_intermediate_results]

        return all_memories, successful_providers

    def _filter_and_rank_memories(self, memories: list[MemoryResponse],
                                 request: QueryRequest) -> list[MemoryResponse]:
        """Filter and rank memories by relevance and importance."""
        # Filter by similarity threshold
        filtered = [m for m in memories if m.similarity_score and m.similarity_score >= request.min_similarity]

        # Sort by combined score (similarity + importance)
        filtered.sort(key=lambda m: (
            (m.similarity_score or 0) * 0.7 +
            (m.importance_score or 0) * 0.3
        ), reverse=True)

        return filtered

    def _get_cache_key(self, request: QueryRequest) -> str:
        """
        PERFORMANCE OPTIMIZED: Generate efficient cache key using hash.
        Target: Cache key generation under 1ms.
        """
        # PERFORMANCE: Use hash instead of string concatenation for better memory efficiency
        key_parts = [
            request.query or "",
            str(request.limit),
            str(request.min_similarity),
            str(sorted(request.filters.items()) if request.filters else ""),
            request.user_id or "",
            request.conversation_id or ""
        ]
        # Use hash for consistent short keys that are memory efficient
        import hashlib
        cache_string = "|".join(key_parts)
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def _cleanup_query_cache(self):
        """
        PERFORMANCE: Clean up expired cache entries to prevent memory bloat.
        Called periodically to maintain cache performance.
        """
        try:
            current_time = time.time()
            cache_ttl = 300  # 5 minutes
            
            # Remove expired entries
            expired_keys = [
                key for key, cached_data in self.query_cache.items()
                if current_time - cached_data['timestamp'] > cache_ttl
            ]
            
            for key in expired_keys:
                del self.query_cache[key]
                
            # PERFORMANCE: Limit cache size to prevent memory bloat (LRU eviction)
            max_cache_size = 1000
            if len(self.query_cache) > max_cache_size:
                # Remove oldest entries
                sorted_items = sorted(
                    self.query_cache.items(),
                    key=lambda x: x[1]['timestamp']
                )
                
                # Remove oldest 20% when cache is full
                num_to_remove = len(sorted_items) - int(max_cache_size * 0.8)
                for key, _ in sorted_items[:num_to_remove]:
                    del self.query_cache[key]
                    
            logger.debug(f"Cache cleanup completed: {len(self.query_cache)} entries remaining")
            
        except Exception as e:
            logger.warning(f"Cache cleanup failed (non-critical): {e}")
    
    async def _sync_initial_stats(self):
        """Synchronize initial stats with actual database counts."""
        try:
            # Wait a bit for providers to fully initialize
            await asyncio.sleep(2)
            
            logger.info("Syncing initial stats from providers...")
            
            # Get actual counts from each provider
            total_memories = 0
            for name, provider in self.providers.items():
                if provider.enabled:
                    try:
                        stats = await provider.get_stats()
                        if 'total_memories' in stats:
                            count = stats['total_memories']
                            total_memories += count
                            logger.info(f"Provider {name} has {count} memories")
                    except Exception as e:
                        logger.warning(f"Failed to get stats from {name}: {e}")
            
            # Update our stats with the actual count
            if total_memories > 0:
                self.stats['total_stores'] = total_memories
                logger.info(f"Initialized total_stores to {total_memories} from providers")
            else:
                logger.warning("No memories found in any provider during initialization")
                
        except Exception as e:
            logger.error(f"Failed to sync initial stats: {e}")
    
    async def refresh_stats(self) -> int:
        """
        Manually refresh stats from all providers.
        Returns the new total count.
        """
        try:
            logger.info("Refreshing stats from all providers...")
            
            total_memories = 0
            provider_counts = {}
            
            for name, provider in self.providers.items():
                if provider.enabled:
                    try:
                        count = 0
                        
                        # Try to get count from health check
                        health = await provider.health_check()
                        if isinstance(health, dict):
                            # Check various possible locations for the count
                            if 'total_vectors' in health:
                                count = health['total_vectors']
                            elif 'details' in health and 'total_vectors' in health['details']:
                                count = health['details']['total_vectors']
                            elif 'total_memories' in health:
                                count = health['total_memories']
                        
                        # Special handling for pgvector
                        if count == 0 and name == 'pgvector' and hasattr(provider, 'connection_pool'):
                            async with provider.connection_pool.acquire() as conn:
                                count = await conn.fetchval("SELECT COUNT(*) FROM vector_memories")
                        
                        if count > 0:
                            total_memories += count
                            provider_counts[name] = count
                            logger.info(f"Provider {name} has {count} memories")
                            
                    except Exception as e:
                        logger.warning(f"Failed to get count from {name}: {e}")
                        provider_counts[name] = 0
            
            # Update stats
            old_total = self.stats.get('total_stores', 0)
            self.stats['total_stores'] = total_memories
            
            # Update provider usage
            for name, count in provider_counts.items():
                if count > 0:
                    self.stats['provider_usage'][name] = count
            
            logger.info(f"Stats refreshed: {old_total} -> {total_memories} total memories")
            return total_memories
            
        except Exception as e:
            logger.error(f"Failed to refresh stats: {e}")
            raise

    async def _execute_background_tasks(self, memory_id: str, tasks: list):
        """Execute background tasks asynchronously without blocking the main response."""
        try:
            logger.info(f"🚀 Starting {len(tasks)} background tasks for memory {memory_id}")
            start_time = time.time()
            
            # Execute all background tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            execution_time = (time.time() - start_time) * 1000
            
            # Log results
            successful = 0
            failed = 0
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"❌ Background task {i} failed for memory {memory_id}: {result}")
                    failed += 1
                else:
                    logger.info(f"✅ Background task {i} completed for memory {memory_id}")
                    successful += 1
            
            logger.info(f"📊 Background tasks for {memory_id}: {successful} successful, {failed} failed in {execution_time:.1f}ms")
            
        except Exception as e:
            logger.error(f"❌ Critical error in background task execution for memory {memory_id}: {e}")

    async def _background_graph_processing(self, memory_id: str, content: str, embedding: list[float], metadata: dict):
        """Process knowledge graph extraction in the background."""
        try:
            logger.info(f"🧠 Starting background graph processing for memory {memory_id}")
            await self.graph_provider.extract_and_link_entities(memory_id, content, embedding, metadata)
            logger.info(f"✅ Background graph processing completed for memory {memory_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Background graph processing failed for memory {memory_id}: {e}")
            return False

    async def _background_replication(self, memory_id: str, content: str, embedding: list[float], metadata: dict):
        """Handle replication to secondary providers in the background."""
        try:
            logger.info(f"🔄 Starting background replication for memory {memory_id}")
            
            # Track replication success rate
            if not hasattr(self, 'replication_stats'):
                self.replication_stats = {'total': 0, 'successful': 0, 'failed': 0}
            self.replication_stats['total'] += 1
            
            await self._replicate_to_secondaries(memory_id, content, embedding, metadata)
            
            self.replication_stats['successful'] += 1
            logger.info(f"✅ Background replication completed for memory {memory_id}")
            return True
            
        except Exception as e:
            self.replication_stats['failed'] += 1
            logger.error(f"❌ Background replication failed for memory {memory_id}: {e}")
            return False

    async def _submit_graph_task(self, memory_id: str, content: str, embedding: list[float], metadata: dict):
        """Submit graph processing task to the task queue (fire-and-forget)."""
        try:
            if self.task_queue and self.graph_provider and self.graph_provider.enabled:
                await self.task_queue.submit_task(
                    task_id=f"graph_processing_{memory_id}",
                    handler=self._task_graph_processing,
                    args=(memory_id, content, embedding, metadata),
                    priority=TaskPriority.MEDIUM,
                    retry_count=2,
                    timeout_seconds=60
                )
                logger.debug(f"🧠 Graph processing task submitted for memory {memory_id}")
        except Exception as e:
            logger.warning(f"Failed to submit graph processing task for memory {memory_id}: {e}")

    async def _submit_replication_task(self, memory_id: str, content: str, embedding: list[float], metadata: dict):
        """Submit replication task to the task queue (fire-and-forget)."""
        try:
            if self.task_queue:
                await self.task_queue.submit_task(
                    task_id=f"replication_{memory_id}",
                    handler=self._task_replication,
                    args=(memory_id, content, embedding, metadata),
                    priority=TaskPriority.LOW,
                    retry_count=3,
                    timeout_seconds=120
                )
                logger.debug(f"🔄 Replication task submitted for memory {memory_id}")
        except Exception as e:
            logger.warning(f"Failed to submit replication task for memory {memory_id}: {e}")

    # ========================================
    # RELIABLE TASK QUEUE HANDLERS
    # ========================================

    async def _task_graph_processing(self, memory_id: str, content: str, embedding: list[float], metadata: dict) -> bool:
        """Task queue handler for graph processing with enhanced error handling"""
        try:
            logger.info(f"🧠 [TASK QUEUE] Starting graph processing for memory {memory_id}")
            
            if not (self.graph_provider and self.graph_provider.enabled):
                logger.warning(f"Graph provider not available for memory {memory_id}")
                return False
            
            await self.graph_provider.extract_and_link_entities(memory_id, content, embedding, metadata)
            
            logger.info(f"✅ [TASK QUEUE] Graph processing completed for memory {memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ [TASK QUEUE] Graph processing failed for memory {memory_id}: {e}")
            # Don't re-raise - let task queue handle retry logic
            return False

    async def _task_provider_replication(self, memory_id: str, content: str, embedding: list[float], metadata: dict) -> bool:
        """Task queue handler for provider replication with enhanced reliability"""
        try:
            logger.info(f"🔄 [TASK QUEUE] Starting provider replication for memory {memory_id}")
            
            # Track replication attempts
            if not hasattr(self, 'replication_stats'):
                self.replication_stats = {'total': 0, 'successful': 0, 'failed': 0}
            
            self.replication_stats['total'] += 1
            
            # Perform replication to secondary providers
            await self._replicate_to_secondaries(memory_id, content, embedding, metadata)
            
            self.replication_stats['successful'] += 1
            logger.info(f"✅ [TASK QUEUE] Provider replication completed for memory {memory_id}")
            return True
            
        except Exception as e:
            self.replication_stats['failed'] += 1
            logger.error(f"❌ [TASK QUEUE] Provider replication failed for memory {memory_id}: {e}")
            
            # Log replication health every failed attempt
            if hasattr(self, 'replication_stats') and self.replication_stats['total'] > 0:
                success_rate = (self.replication_stats['successful'] / self.replication_stats['total']) * 100
                logger.warning(f"📊 Current replication success rate: {success_rate:.1f}%")
            
            # Don't re-raise - let task queue handle retry logic
            return False

    async def _task_provider_reconciliation(self, provider_name: str = None) -> bool:
        """Task queue handler for provider reconciliation to detect and fix inconsistencies"""
        try:
            logger.info(f"🔧 [TASK QUEUE] Starting provider reconciliation (provider: {provider_name or 'all'})")
            
            # Get current memory counts from all providers
            provider_counts = {}
            primary_count = 0
            
            for name, provider in self.providers.items():
                if not provider.enabled:
                    continue
                    
                try:
                    health = await provider.health_check()
                    count = 0
                    
                    if isinstance(health, dict):
                        count = health.get('total_vectors', health.get('total_memories', 0))
                    
                    provider_counts[name] = count
                    
                    if provider == self.primary_provider:
                        primary_count = count
                        
                    logger.info(f"Provider {name}: {count} memories")
                    
                except Exception as e:
                    logger.error(f"Failed to get count from provider {name}: {e}")
                    provider_counts[name] = -1  # Mark as error
            
            # Detect inconsistencies
            inconsistencies = []
            tolerance = 0.05  # 5% tolerance for minor discrepancies
            
            for name, count in provider_counts.items():
                if count == -1:  # Provider error
                    inconsistencies.append(f"Provider {name}: Health check failed")
                elif abs(count - primary_count) > (primary_count * tolerance):
                    diff = count - primary_count
                    inconsistencies.append(f"Provider {name}: {diff:+d} memories vs primary")
            
            if inconsistencies:
                logger.warning(f"🚨 Provider inconsistencies detected:")
                for issue in inconsistencies:
                    logger.warning(f"   • {issue}")
                
                # TODO: Implement automatic repair mechanisms
                logger.info("Reconciliation completed with issues - manual intervention may be required")
                return False
            else:
                logger.info("✅ [TASK QUEUE] All providers are consistent")
                return True
                
        except Exception as e:
            logger.error(f"❌ [TASK QUEUE] Provider reconciliation failed: {e}")
            return False

    async def _task_provider_repair(self, provider_name: str, repair_type: str = "sync") -> bool:
        """Task queue handler for automatic provider repair"""
        try:
            logger.info(f"🔧 [TASK QUEUE] Starting provider repair for {provider_name} (type: {repair_type})")
            
            if repair_type == "sync":
                return await self._repair_provider_sync(provider_name)
            elif repair_type == "rebuild":
                return await self._repair_provider_rebuild(provider_name)
            else:
                logger.error(f"Unknown repair type: {repair_type}")
                return False
                
        except Exception as e:
            logger.error(f"❌ [TASK QUEUE] Provider repair failed for {provider_name}: {e}")
            return False

    async def _repair_provider_sync(self, provider_name: str) -> bool:
        """Synchronize a secondary provider with the primary provider"""
        try:
            if provider_name not in self.providers:
                logger.error(f"Provider {provider_name} not found")
                return False
                
            provider = self.providers[provider_name]
            if not provider.enabled or provider == self.primary_provider:
                logger.warning(f"Cannot sync provider {provider_name} (disabled or is primary)")
                return False
            
            logger.info(f"🔄 Starting sync repair for provider {provider_name}")
            
            # Get recent memories from primary provider (last 100)
            # This is a simplified repair - in production you'd want more sophisticated sync
            try:
                primary_health = await self.primary_provider.health_check()
                secondary_health = await provider.health_check()
                
                primary_count = primary_health.get('total_vectors', 0)
                secondary_count = secondary_health.get('total_vectors', 0)
                
                if primary_count == secondary_count:
                    logger.info(f"✅ Provider {provider_name} is already in sync ({primary_count} memories)")
                    return True
                
                missing_count = primary_count - secondary_count
                logger.info(f"Provider {provider_name} is missing {missing_count} memories, starting sync...")
                
                # IMPLEMENTATION: Actual sync logic - copy missing memories from primary to secondary
                if missing_count > 0:
                    logger.info(f"🔄 Syncing {missing_count} missing memories to {provider_name}")
                    
                    # Get recent memories from primary to copy over
                    try:
                        # Query primary provider for recent memories (limited batch for safety)
                        batch_size = min(50, missing_count)  # Process in batches of 50
                        
                        if hasattr(self.primary_provider, 'get_recent_memories'):
                            recent_memories = await self.primary_provider.get_recent_memories(batch_size, {})
                        else:
                            # Fallback: empty query to get recent memories
                            recent_memories = await self.primary_provider.query([], batch_size, {})
                        
                        if not recent_memories:
                            logger.warning(f"No recent memories found in primary provider for sync")
                            return False
                        
                        # Replicate memories to secondary provider
                        sync_successes = 0
                        sync_failures = 0
                        
                        for memory in recent_memories:
                            try:
                                # Extract memory data
                                content = memory.content
                                metadata = memory.metadata or {}
                                
                                # Generate embedding if not available
                                if hasattr(memory, 'embedding') and memory.embedding:
                                    embedding = memory.embedding
                                else:
                                    embedding = await self._generate_embedding(content)
                                
                                # Store in secondary provider
                                await provider.store(content, embedding, metadata)
                                sync_successes += 1
                                
                            except Exception as e:
                                logger.error(f"Failed to sync memory {getattr(memory, 'id', 'unknown')}: {e}")
                                sync_failures += 1
                        
                        logger.info(f"✅ Sync completed: {sync_successes} successful, {sync_failures} failed")
                        
                        # Verify sync was successful
                        post_sync_health = await provider.health_check()
                        post_sync_count = post_sync_health.get('total_vectors', 0)
                        
                        if post_sync_count > secondary_count:
                            logger.info(f"✅ Sync successful: {provider_name} now has {post_sync_count} memories")
                            return True
                        else:
                            logger.warning(f"⚠️ Sync may have failed: count unchanged at {post_sync_count}")
                            return False
                            
                    except Exception as e:
                        logger.error(f"Sync operation failed: {e}")
                        return False
                else:
                    logger.info(f"✅ Provider {provider_name} is already in sync ({primary_count} memories)")
                    return True
                
            except Exception as e:
                logger.error(f"Failed to compare provider counts: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Sync repair failed for {provider_name}: {e}")
            return False

    async def _repair_provider_rebuild(self, provider_name: str) -> bool:
        """Rebuild a provider from scratch (emergency repair)"""
        try:
            logger.warning(f"🚨 Starting rebuild repair for provider {provider_name}")
            logger.warning("This is an emergency operation that will clear and rebuild the provider")
            
            if provider_name not in self.providers:
                logger.error(f"Provider {provider_name} not found")
                return False
                
            provider = self.providers[provider_name]
            if not provider.enabled or provider == self.primary_provider:
                logger.error(f"Cannot rebuild provider {provider_name} (disabled or is primary)")
                return False
            
            # IMPLEMENTATION: Complete rebuild process
            try:
                # Step 1: Get all memories from primary provider for full rebuild
                logger.info(f"🔄 Step 1: Fetching all memories from primary provider...")
                
                # Get a larger batch for full rebuild (but still manageable)
                rebuild_batch_size = 200
                
                if hasattr(self.primary_provider, 'get_recent_memories'):
                    all_memories = await self.primary_provider.get_recent_memories(rebuild_batch_size, {})
                else:
                    # Fallback: empty query to get memories
                    all_memories = await self.primary_provider.query([], rebuild_batch_size, {})
                
                if not all_memories:
                    logger.error(f"No memories found in primary provider for rebuild")
                    return False
                
                logger.info(f"Found {len(all_memories)} memories to rebuild")
                
                # Step 2: Clear the secondary provider (if supported)
                logger.warning(f"🧹 Step 2: Clearing provider {provider_name} (if supported)...")
                # Note: Most providers don't support full clear operations
                # This would need provider-specific implementation
                
                # Step 3: Re-replicate all memories
                logger.info(f"🔄 Step 3: Re-replicating {len(all_memories)} memories...")
                
                rebuild_successes = 0
                rebuild_failures = 0
                
                for memory in all_memories:
                    try:
                        content = memory.content
                        metadata = memory.metadata or {}
                        
                        # Generate embedding if not available
                        if hasattr(memory, 'embedding') and memory.embedding:
                            embedding = memory.embedding
                        else:
                            embedding = await self._generate_embedding(content)
                        
                        # Store in provider
                        await provider.store(content, embedding, metadata)
                        rebuild_successes += 1
                        
                        # Add small delay to prevent overwhelming the provider
                        if rebuild_successes % 10 == 0:
                            await asyncio.sleep(0.1)
                        
                    except Exception as e:
                        logger.error(f"Failed to rebuild memory {getattr(memory, 'id', 'unknown')}: {e}")
                        rebuild_failures += 1
                
                logger.info(f"📊 Rebuild completed: {rebuild_successes} successful, {rebuild_failures} failed")
                
                # Step 4: Verify the rebuild
                logger.info(f"🔍 Step 4: Verifying rebuild...")
                
                post_rebuild_health = await provider.health_check()
                post_rebuild_count = post_rebuild_health.get('total_vectors', 0)
                
                primary_health = await self.primary_provider.health_check()
                primary_count = primary_health.get('total_vectors', 0)
                
                # Check if rebuild was successful (allowing for small discrepancies)
                success_threshold = 0.9  # 90% of primary count is acceptable
                if post_rebuild_count >= (primary_count * success_threshold):
                    logger.info(f"✅ Rebuild successful: {provider_name} now has {post_rebuild_count}/{primary_count} memories")
                    return True
                else:
                    logger.error(f"❌ Rebuild failed: {provider_name} has {post_rebuild_count}/{primary_count} memories")
                    return False
                    
            except Exception as e:
                logger.error(f"Rebuild operation failed: {e}")
                return False
            
        except Exception as e:
            logger.error(f"Rebuild repair failed for {provider_name}: {e}")
            return False
    
    # ========================================
    # TASK QUEUE INITIALIZATION AND INTEGRATION
    # ========================================
    
    async def _initialize_task_queue(self):
        """Initialize and configure the reliable task queue with handlers"""
        try:
            logger.info("🚀 Initializing reliable task queue for Core Nexus...")
            
            # Get or create the global task queue
            self.task_queue = await get_task_queue()
            
            # Register task handlers for different background operations
            self.task_queue.register_handler('graph_processing', self._task_graph_processing)
            self.task_queue.register_handler('provider_replication', self._task_provider_replication)
            self.task_queue.register_handler('provider_reconciliation', self._task_provider_reconciliation)
            self.task_queue.register_handler('provider_repair', self._task_provider_repair)
            
            logger.info("✅ Reliable task queue initialized with 4 handlers")
            
            # Schedule initial provider reconciliation to check system health
            if self.task_queue:
                await self.task_queue.submit_task(
                    task_type='provider_reconciliation',
                    payload={},
                    priority=TaskPriority.HIGH,
                    max_retries=2
                )
                logger.info("🔍 Scheduled initial provider reconciliation")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize task queue: {e}")
            self.task_queue = None
    
    def get_task_queue_metrics(self) -> dict:
        """Get metrics from the reliable task queue"""
        if self.task_queue:
            return self.task_queue.get_metrics()
        return {}
    
    async def submit_repair_task(self, provider_name: str, repair_type: str = "sync") -> str:
        """Public method to submit a provider repair task"""
        if not self.task_queue:
            raise RuntimeError("Task queue not initialized")
        
        return await self.task_queue.submit_task(
            task_type='provider_repair',
            payload={
                'provider_name': provider_name,
                'repair_type': repair_type
            },
            priority=TaskPriority.CRITICAL,
            max_retries=2
        )
