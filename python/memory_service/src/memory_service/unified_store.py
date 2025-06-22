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
from typing import Any
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

logger = logging.getLogger(__name__)


class VectorProvider(ABC):
    """Abstract base class for vector storage providers."""

    def __init__(self, config: ProviderConfig):
        self.config = config
        self.name = config.name
        self.enabled = config.enabled

    @abstractmethod
    async def store(self, content: str, embedding: list[float], metadata: dict[str, Any]) -> UUID:
        """Store a memory with embedding."""
        pass

    @abstractmethod
    async def query(self, query_embedding: list[float], limit: int, filters: dict[str, Any]) -> list[MemoryResponse]:
        """Query similar memories."""
        pass

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Check provider health."""
        pass

    @abstractmethod
    async def get_stats(self) -> dict[str, Any]:
        """Get provider statistics."""
        pass


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
            'storage_saved_bytes': 0
        }
        
        # Schedule initial stats sync after initialization
        asyncio.create_task(self._sync_initial_stats())

        # Initialize ADM scoring if enabled
        self.adm_enabled = adm_enabled
        self.adm_engine = None
        if adm_enabled:
            self._initialize_adm_engine()

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

        logger.info(f"Initialized UnifiedVectorStore with providers: {list(self.providers.keys())}")
        logger.info(f"Primary provider: {self.primary_provider.name}")
        logger.info(f"ADM scoring: {'enabled' if adm_enabled else 'disabled'}")
        logger.info(f"Deduplication: {'enabled' if self.deduplication_service else 'disabled'}")
        logger.info(f"Graph functionality: {'enabled' if self.graph_provider else 'disabled'}")

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

    async def store_memory(self, request: MemoryRequest) -> MemoryResponse:
        """
        Store a memory across providers with automatic replication.

        Leverages existing implementations while adding resilience.
        """
        start_time = time.time()

        try:
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

            # Calculate importance score using ADM if available
            importance_score = request.importance_score
            adm_data = {}

            if importance_score is None:
                if self.adm_enabled and self.adm_engine:
                    # Use ADM scoring for intelligent importance calculation
                    try:
                        adm_result = await self.adm_engine.calculate_adm_score(
                            request.content,
                            request.metadata
                        )
                        importance_score = adm_result['adm_score']
                        adm_data = adm_result

                        # Update ADM stats
                        self.stats['adm_calculations'] += 1
                        current_avg = self.stats['avg_adm_score']
                        count = self.stats['adm_calculations']
                        self.stats['avg_adm_score'] = (current_avg * (count - 1) + importance_score) / count

                    except Exception as e:
                        logger.warning(f"ADM scoring failed, using fallback: {e}")
                        importance_score = self._calculate_importance(request)
                else:
                    importance_score = self._calculate_importance(request)

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

            # Extract entities and relationships for knowledge graph if enabled
            if self.graph_provider and self.graph_provider.enabled:
                try:
                    logger.info(f"🧠 Extracting entities and relationships for memory {memory_id}")
                    # Use the memory_id from primary storage for graph consistency
                    await self.graph_provider.extract_and_link_entities(memory_id, request.content, embedding, metadata)
                    logger.info(f"✅ Successfully processed knowledge graph for memory {memory_id}")
                except Exception as e:
                    logger.error(f"❌ Graph processing failed for memory {memory_id}: {e}")
                    # Don't fail the whole operation if graph processing fails
                    logger.info("Continuing without graph processing - memory storage succeeded")

            # SYNCHRONOUS replication to secondary providers for data consistency
            # This ensures ChromaDB stays in sync with pgvector
            replication_success = False
            try:
                logger.info(f"🔄 Starting replication for memory {memory_id} to secondary providers")
                await self._replicate_to_secondaries(
                    memory_id, request.content, embedding, metadata
                )
                logger.info(f"✅ Successfully replicated memory {memory_id} to secondary providers")
                replication_success = True
            except Exception as e:
                logger.error(f"❌ CRITICAL: Secondary replication failed for memory {memory_id}: {e}")
                logger.error(f"❌ This means ChromaDB is not getting updates - data redundancy broken!")
                # Continue - primary storage succeeded, but log the failure prominently
                
            # Track replication success rate
            if not hasattr(self, 'replication_stats'):
                self.replication_stats = {'total': 0, 'successful': 0, 'failed': 0}
            self.replication_stats['total'] += 1
            if replication_success:
                self.replication_stats['successful'] += 1
            else:
                self.replication_stats['failed'] += 1
                
            # Log replication health every 10 operations
            if self.replication_stats['total'] % 10 == 0:
                success_rate = (self.replication_stats['successful'] / self.replication_stats['total']) * 100
                logger.warning(f"📊 Replication health: {success_rate:.1f}% success rate ({self.replication_stats['successful']}/{self.replication_stats['total']})")

            # Update stats
            self.stats['total_stores'] += 1
            self.stats['provider_usage'][self.primary_provider.name] += 1

            logger.info(f"Stored memory {memory_id} in {time.time() - start_time:.3f}s")

            return MemoryResponse(
                id=memory_id,
                content=request.content,
                metadata=metadata,
                importance_score=importance_score
            )

        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            raise

    async def query_memories(self, request: QueryRequest) -> QueryResponse:
        """
        Query memories across providers with intelligent routing.

        Uses existing vector store implementations with added optimizations.
        """
        start_time = time.time()

        try:
            # Check cache first (simple key based on query + filters)
            cache_key = self._get_cache_key(request)
            if cache_key in self.query_cache:
                cached_result = self.query_cache[cache_key]
                if time.time() - cached_result['timestamp'] < 300:  # 5 min cache
                    logger.debug(f"Cache hit for query: {request.query[:50]}...")
                    return cached_result['response']

            # EMERGENCY FIX: If empty query, use bulletproof emergency retrieval
            logger.info(f"🔍 EMPTY QUERY CHECK: query='{request.query}', is_empty={not request.query or request.query.strip() == ''}")
            if not request.query or request.query.strip() == "":
                logger.info("🚨 EMPTY QUERY DETECTED: Using bulletproof emergency retrieval")
                
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
            
            # For non-empty queries, try multiple search strategies
            query_embedding = None
            memories = []
            
            # Strategy 1: Try embedding-based search if possible
            try:
                if self.embedding_model and request.query:
                    query_embedding = await self._generate_embedding(request.query)
                else:
                    logger.warning("No embedding model available for query")

            except Exception as e:
                logger.error(f"Embedding generation failed: {e}")
            
            # Determine which providers to query
            providers_to_query = self._select_providers(request)
            
            # CRITICAL FIX: Only use graph provider for explicit entity queries with specific filters
            # All other queries (including empty queries and semantic searches) MUST use pgvector
            use_graph_provider = False
            graph_memories = []
            
            # Provider routing decision logging
            logger.debug(f"Query processing: '{request.query}' with filters: {request.filters}")
            
            # CRITICAL FIX: Much more restrictive graph provider selection
            # Only use graph provider for EXPLICIT entity relationship queries with actual entity filter values
            should_use_graph = False
            
            if self.graph_provider and self.graph_provider.enabled:
                # Check for explicit entity filters with actual values
                entity_filters = {}
                if request.filters:
                    entity_filters = {k: v for k, v in request.filters.items() 
                                    if k in ['entity_name', 'entity_type', 'relationship_type'] 
                                    and v is not None and str(v).strip()}
                
                logger.debug(f"Entity filters found: {entity_filters}")
                
                # ONLY use graph if we have explicit entity filters with non-empty values
                if entity_filters:
                    logger.info(f"🧠 Using graph provider for entity query: {entity_filters}")
                    try:
                        graph_memories = await self.graph_provider.query(
                            query_embedding or [], request.limit, request.filters
                        )
                        if graph_memories:
                            logger.info(f"✅ Graph provider returned {len(graph_memories)} results")
                            use_graph_provider = True
                        else:
                            logger.debug("Graph query returned no results, will attempt fallback")
                    except Exception as e:
                        logger.error(f"❌ Graph query failed: {e}, will attempt fallback")
                else:
                    logger.debug("No entity filters found, using vector search")
            else:
                logger.debug("Graph provider not available, using vector search")
            
            # DECISIVE ROUTING LOGIC WITH BULLETPROOF FALLBACK
            if use_graph_provider and graph_memories:
                memories = graph_memories
                providers_used = ['graph']
                logger.info(f"✅ FINAL ROUTING → GRAPH: {len(memories)} memories from graph provider")
            elif use_graph_provider and not graph_memories:
                # CRITICAL FALLBACK: If graph provider was selected but returned no results, fall back to pgvector
                logger.warning(f"🔄 GRAPH FALLBACK: Graph provider returned 0 results, falling back to pgvector")
                logger.info(f"🔍 FALLBACK TO VECTOR SEARCH: {len(providers_to_query)} providers available")
                
                if query_embedding and providers_to_query:
                    try:
                        provider = providers_to_query[0]  # Use primary provider (pgvector)
                        logger.info(f"🔍 FALLBACK PROVIDER: Using {provider.name}")
                        memories = await self._query_provider(
                            provider,
                            query_embedding,
                            request
                        )
                        providers_used = [f'{provider.name}_fallback']
                        logger.info(f"✅ FALLBACK SUCCESS → {provider.name.upper()}: {len(memories)} memories recovered")
                    except Exception as e:
                        logger.error(f"❌ Fallback search failed: {e}")
                        memories = []
                        providers_used = ['graph_failed']
                else:
                    logger.error("❌ No fallback providers available or no embedding")
                    memories = []
                    providers_used = ['graph_failed']
            elif query_embedding:
                # FORCE PGVECTOR ROUTING for non-entity queries
                logger.info(f"🔍 ROUTING TO VECTOR SEARCH: {len(providers_to_query)} providers available")
                logger.info(f"   Available providers: {[p.name for p in providers_to_query]}")
                
                try:
                    # Query providers (potentially in parallel for better performance)
                    if len(providers_to_query) == 1:
                        # Single provider query
                        provider = providers_to_query[0]
                        logger.info(f"🔍 SINGLE PROVIDER QUERY: Using {provider.name}")
                        memories = await self._query_provider(
                            provider,
                            query_embedding,
                            request
                        )
                        providers_used = [provider.name]
                        logger.info(f"✅ FINAL ROUTING → {provider.name.upper()}: {len(memories)} memories returned")
                    else:
                        # Multi-provider query with result aggregation
                        logger.info(f"🔍 MULTI PROVIDER QUERY: Querying {[p.name for p in providers_to_query]}")
                        memories, providers_used = await self._query_multiple_providers(
                            providers_to_query,
                            query_embedding,
                            request
                        )
                        logger.info(f"✅ FINAL ROUTING → MULTIPLE: {len(memories)} memories from {providers_used}")
                except Exception as e:
                    logger.error(f"❌ Vector search failed: {e}")
                    memories = []
                    providers_used = []
            else:
                logger.warning("❌ NO ROUTING: No query embedding generated, returning empty results")
                memories = []
                providers_used = []
            
            # EMERGENCY FIX: If vector search returns no results, use text search
            if not memories and request.query:
                logger.warning(f"Vector search returned 0 results for '{request.query}', trying text search")
                
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

        return {
            'status': 'healthy' if overall_healthy else 'degraded',
            'providers': results,
            'stats': updated_stats,
            'cache_size': len(self.query_cache),
            'graph_enabled': self.graph_provider is not None and self.graph_provider.enabled,
            'features': {
                'vector_storage': True,
                'knowledge_graph': self.graph_provider is not None and self.graph_provider.enabled,
                'adm_scoring': self.adm_enabled,
                'deduplication': self.deduplication_service is not None
            }
        }

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

    async def _store_with_retry(self, provider: VectorProvider, content: str,
                               embedding: list[float], metadata: dict[str, Any]) -> UUID:
        """Store with retry logic."""
        for attempt in range(provider.config.retry_count):
            try:
                return await provider.store(content, embedding, metadata)
            except Exception as e:
                if attempt == provider.config.retry_count - 1:
                    raise
                logger.warning(f"Store attempt {attempt + 1} failed for {provider.name}: {e}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

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
        """Query a single provider with proper error handling."""
        try:
            # Check if this is an empty query (zero vector or no embedding)
            is_empty_query = not query_embedding or all(v == 0.0 for v in query_embedding)
            
            if is_empty_query:
                # Use get_recent_memories if available (currently only PgVectorProvider)
                if hasattr(provider, 'get_recent_memories'):
                    logger.info(f"Using get_recent_memories for empty query on {provider.name}")
                    try:
                        results = await provider.get_recent_memories(request.limit * 2, request.filters or {})
                    except Exception as e:
                        logger.error(f"get_recent_memories failed: {e}")
                        # Try emergency search as last resort
                        if provider.name == 'pgvector' and hasattr(provider, 'connection_pool'):
                            from .search_fix import EmergencySearchFix
                            emergency = EmergencySearchFix(provider.connection_pool, getattr(provider, "table_name", "vector_memories"))
                            results = await emergency.emergency_search_all(request.limit * 2)
                        else:
                            results = []
                else:
                    # Fall back to regular query for providers without get_recent_memories
                    logger.info(f"Provider {provider.name} doesn't support get_recent_memories, using regular query")
                    results = await provider.query(query_embedding, request.limit * 2, request.filters)
            else:
                # Regular vector similarity query
                results = await provider.query(query_embedding, request.limit * 2, request.filters)
            
            # Update provider usage stats
            self.stats['provider_usage'][provider.name] = self.stats['provider_usage'].get(provider.name, 0) + 1
            
            return results
            
        except Exception as e:
            logger.error(f"Query failed for provider {provider.name}: {e}")
            # Re-raise the exception to be handled by _query_multiple_providers
            raise

    async def _query_multiple_providers(self, providers: list[VectorProvider],
                                       query_embedding: list[float], request: QueryRequest) -> tuple[list[MemoryResponse], list[str]]:
        """Query multiple providers and aggregate results."""
        tasks = []
        provider_names = []

        for provider in providers:
            task = asyncio.create_task(
                self._query_provider(provider, query_embedding, request)
            )
            tasks.append(task)
            provider_names.append(provider.name)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results, handling failures gracefully
        all_memories = []
        successful_providers = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Provider {provider_names[i]} failed: {result}")
            else:
                all_memories.extend(result)
                successful_providers.append(provider_names[i])

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
        """Generate cache key for query."""
        # Simple cache key - in production, use more sophisticated hashing
        key_parts = [
            request.query,
            str(request.limit),
            str(request.min_similarity),
            str(sorted(request.filters.items()) if request.filters else ""),
            request.user_id or "",
            request.conversation_id or ""
        ]
        return "|".join(key_parts)
    
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
