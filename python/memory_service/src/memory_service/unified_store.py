"""
Unified Vector Store

Core implementation that leverages existing Pinecone and ChromaDB implementations
while adding pgvector as a third option for maximum resilience and performance.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID, uuid4

from .models import (
    MemoryRequest, 
    MemoryResponse, 
    QueryRequest, 
    QueryResponse, 
    ProviderConfig,
    ImportanceScoring,
    GraphAwareQueryRequest,
    GraphAwareQueryResponse,
    EnhancedMemoryResponse,
    EvidenceChain,
    GraphConnection
)

logger = logging.getLogger(__name__)


class VectorProvider(ABC):
    """Abstract base class for vector storage providers."""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.name = config.name
        self.enabled = config.enabled
        
    @abstractmethod
    async def store(self, content: str, embedding: List[float], metadata: Dict[str, Any], memory_id: Optional[UUID] = None) -> UUID:
        """Store a memory with embedding."""
        pass
        
    @abstractmethod
    async def query(self, query_embedding: List[float], limit: int, filters: Dict[str, Any]) -> List[MemoryResponse]:
        """Query similar memories."""
        pass
        
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check provider health."""
        pass
        
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
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
    
    def __init__(self, providers: List[VectorProvider], embedding_model=None, adm_enabled=True):
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
            'avg_adm_score': 0.0
        }
        
        # Initialize ADM scoring if enabled
        self.adm_enabled = adm_enabled
        self.adm_engine = None
        if adm_enabled:
            self._initialize_adm_engine()
        
        logger.info(f"Initialized UnifiedVectorStore with providers: {list(self.providers.keys())}")
        logger.info(f"Primary provider: {self.primary_provider.name}")
        logger.info(f"ADM scoring: {'enabled' if adm_enabled else 'disabled'}")
    
    def _initialize_adm_engine(self):
        """Initialize the ADM scoring engine."""
        try:
            from .adm import ADMScoringEngine, ADMWeights, ADMThresholds
            
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
            import redis
            import os
            
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            redis_client = redis.from_url(redis_url, decode_responses=True)
            
            # Test connection
            redis_client.ping()
            logger.info("Redis cache initialized")
            self._cache_type = 'redis'
            return redis_client
            
        except Exception as e:
            logger.info(f"Redis not available, using in-memory cache: {e}")
            self._cache_type = 'memory'
            return {}
    
    def _get_cached_result(self, cache_key: str):
        """Get cached result with proper handling for Redis vs in-memory cache."""
        try:
            if self._cache_type == 'redis':
                # Use Redis get operation
                cached_data = self.query_cache.get(cache_key)
                if cached_data:
                    import json
                    return json.loads(cached_data)
                return None
            else:
                # Use dict get operation
                return self.query_cache.get(cache_key)
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None
    
    def _set_cached_result(self, cache_key: str, result: dict, ttl_seconds: int = 300):
        """Set cached result with proper handling for Redis vs in-memory cache."""
        try:
            if self._cache_type == 'redis':
                # Use Redis setex operation with JSON serialization
                import json
                serialized_result = json.dumps(result, default=str)  # default=str handles datetime
                self.query_cache.setex(cache_key, ttl_seconds, serialized_result)
            else:
                # Use dict operation
                self.query_cache[cache_key] = result
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
            # Don't fail the query if cache fails
    
    async def store_memory(self, request: MemoryRequest) -> MemoryResponse:
        """
        Store a memory across providers with automatic replication.
        
        Leverages existing implementations while adding resilience.
        """
        start_time = time.time()
        
        try:
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
            
            logger.info(f"Primary storage complete for memory {memory_id}")
            
            # Async replication to secondary providers for resilience
            # Get enabled secondary providers
            secondary_providers = [p.name for p in self.providers.values() 
                                 if p != self.primary_provider and p.enabled]
            
            if secondary_providers:
                logger.info(f"Starting replication to secondary providers: {secondary_providers}")
                asyncio.create_task(self._replicate_to_secondaries(
                    memory_id, request.content, embedding, metadata
                ))
            else:
                logger.info("No secondary providers enabled for replication")
            
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
            cached_result = self._get_cached_result(cache_key)
            if cached_result and time.time() - cached_result['timestamp'] < 300:  # 5 min cache
                logger.debug(f"Cache hit for query: {request.query[:50]}...")
                return cached_result['response']
            
            # Generate query embedding
            # For empty queries, use a zero vector to match all memories
            if not request.query or request.query.strip() == "":
                query_embedding = [0.0] * 1536  # Use zero vector for "get all" queries
                logger.info("Empty query detected - using zero vector to retrieve all memories")
            else:
                query_embedding = await self._generate_embedding(request.query)
            
            # Determine which providers to query
            providers_to_query = self._select_providers(request)
            
            # Query providers (potentially in parallel for better performance)
            if len(providers_to_query) == 1:
                # Single provider query
                memories = await self._query_provider(
                    providers_to_query[0], 
                    query_embedding, 
                    request
                )
                providers_used = [providers_to_query[0].name]
            else:
                # Multi-provider query with result aggregation
                memories, providers_used = await self._query_multiple_providers(
                    providers_to_query, 
                    query_embedding, 
                    request
                )
            
            # Filter and sort results
            filtered_memories = self._filter_and_rank_memories(memories, request)
            
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
            self._set_cached_result(cache_key, {
                'response': response,
                'timestamp': time.time()
            })
            
            logger.info(f"Query returned {len(filtered_memories)} memories in {query_time:.1f}ms")
            return response
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise
    
    async def query_memories_with_graph(self, request: GraphAwareQueryRequest) -> GraphAwareQueryResponse:
        """
        Enhanced query method that combines vector similarity with graph relationships.
        
        This hybrid approach:
        1. Performs parallel vector search across all providers
        2. Extracts entities from the query using graph provider
        3. Finds graph connections to boost relevant results
        4. Generates evidence chains showing reasoning paths
        5. Provides 70% vector + 30% graph weighted scoring
        """
        start_time = time.time()
        graph_start_time = None
        
        try:
            logger.info(f"Graph-aware query: '{request.query[:100]}...' (graph_weight={request.graph_weight})")
            
            # Check if graph provider is available
            graph_provider = self.providers.get('graph')
            if not graph_provider or not graph_provider.enabled:
                logger.warning("Graph provider not available, falling back to regular vector search")
                # Fallback to regular query
                regular_response = await self.query_memories(request)
                return GraphAwareQueryResponse(
                    memories=[EnhancedMemoryResponse(**mem.dict()) for mem in regular_response.memories],
                    total_found=regular_response.total_found,
                    query_time_ms=regular_response.query_time_ms,
                    providers_used=regular_response.providers_used,
                    graph_enabled=False,
                    extracted_entities=[],
                    entity_coverage=0.0,
                    graph_query_time_ms=0.0
                )
            
            # Step 1: Generate query embedding and extract entities in parallel
            if not request.query or request.query.strip() == "":
                query_embedding = [0.0] * 1536  # Zero vector for "get all" queries
                extracted_entities = []
            else:
                # Parallel execution of embedding generation and entity extraction
                embedding_task = asyncio.create_task(self._generate_embedding(request.query))
                entity_extraction_task = asyncio.create_task(self._extract_query_entities(request.query, graph_provider))
                
                query_embedding, extracted_entities = await asyncio.gather(embedding_task, entity_extraction_task)
            
            logger.info(f"Extracted {len(extracted_entities)} entities from query: {extracted_entities}")
            
            # Step 2: Parallel vector search and graph relationship queries
            graph_start_time = time.time()
            
            # Determine providers for vector search
            vector_providers = self._select_providers(request)
            
            # Create parallel tasks
            tasks = []
            
            # Vector similarity search
            if len(vector_providers) == 1:
                vector_task = asyncio.create_task(
                    self._query_provider(vector_providers[0], query_embedding, request)
                )
            else:
                vector_task = asyncio.create_task(
                    self._query_multiple_providers(vector_providers, query_embedding, request)
                )
            tasks.append(('vector', vector_task))
            
            # Graph relationship search for each entity
            for entity_name in extracted_entities:
                entity_filters = {**request.filters, 'entity_name': entity_name}
                graph_task = asyncio.create_task(
                    graph_provider.query(query_embedding, request.limit, entity_filters)
                )
                tasks.append(('graph', graph_task))
            
            # Wait for all queries to complete
            results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)
            
            # Process results
            vector_memories = []
            graph_memories = []
            providers_used = []
            
            for i, (task_type, result) in enumerate(zip([task[0] for task in tasks], results)):
                if isinstance(result, Exception):
                    logger.warning(f"{task_type} search failed: {result}")
                    continue
                
                if task_type == 'vector':
                    if isinstance(result, tuple):  # Multiple providers result
                        vector_memories, providers_used = result
                    else:  # Single provider result
                        vector_memories = result
                        providers_used = [vector_providers[0].name]
                else:  # graph
                    graph_memories.extend(result)
            
            graph_query_time = (time.time() - graph_start_time) * 1000 if graph_start_time else 0
            
            # Step 3: Hybrid scoring and evidence chain generation
            if request.enable_graph_retrieval and extracted_entities:
                enhanced_memories = await self._create_enhanced_memories_with_graph(
                    vector_memories, graph_memories, extracted_entities, request
                )
            else:
                # No graph enhancement, convert to EnhancedMemoryResponse
                enhanced_memories = [
                    EnhancedMemoryResponse(**mem.dict(), graph_boost_factor=1.0)
                    for mem in vector_memories
                ]
            
            # Step 4: Final filtering and ranking
            filtered_memories = self._filter_and_rank_graph_memories(enhanced_memories, request)
            
            # Calculate statistics
            total_query_time = (time.time() - start_time) * 1000
            entity_coverage = self._calculate_entity_coverage(filtered_memories) if filtered_memories else 0.0
            avg_evidence_chains = self._calculate_avg_evidence_chains(filtered_memories) if filtered_memories else 0.0
            
            # Update stats
            self.stats['total_queries'] += 1
            self.stats['avg_query_time'] = (
                (self.stats['avg_query_time'] * (self.stats['total_queries'] - 1) + total_query_time) / 
                self.stats['total_queries']
            )
            
            # Build response
            response = GraphAwareQueryResponse(
                memories=filtered_memories[:request.limit],
                total_found=len(filtered_memories),
                query_time_ms=total_query_time,
                providers_used=providers_used + (['graph'] if graph_memories else []),
                extracted_entities=extracted_entities,
                graph_enabled=request.enable_graph_retrieval,
                related_entities=[],  # TODO: Implement in future iterations
                entity_coverage=entity_coverage,
                average_evidence_chains=avg_evidence_chains,
                graph_query_time_ms=graph_query_time,
                entity_connections=self._build_entity_connection_map(filtered_memories)
            )
            
            logger.info(f"Graph-aware query returned {len(filtered_memories)} memories in {total_query_time:.1f}ms "
                       f"(graph: {graph_query_time:.1f}ms, coverage: {entity_coverage:.1%})")
            
            return response
            
        except Exception as e:
            logger.error(f"Graph-aware query failed: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
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
        
        # Get cache size in a type-safe way
        try:
            if self._cache_type == 'redis':
                cache_size = self.query_cache.dbsize()  # Redis command for key count
            else:
                cache_size = len(self.query_cache)
        except:
            cache_size = -1  # Unknown cache size
        
        return {
            'status': 'healthy' if overall_healthy else 'degraded',
            'providers': results,
            'stats': self.stats,
            'cache_size': cache_size,
            'cache_type': self._cache_type
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
                               embedding: List[float], metadata: Dict[str, Any], memory_id: Optional[UUID] = None) -> UUID:
        """Store with retry logic."""
        for attempt in range(provider.config.retry_count):
            try:
                return await provider.store(content, embedding, metadata, memory_id)
            except Exception as e:
                if attempt == provider.config.retry_count - 1:
                    raise
                logger.warning(f"Store attempt {attempt + 1} failed for {provider.name}: {e}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    async def _replicate_to_secondaries(self, memory_id: UUID, content: str, 
                                       embedding: List[float], metadata: Dict[str, Any]):
        """Replicate to secondary providers for resilience."""
        secondary_providers = [p for p in self.providers.values() 
                             if p != self.primary_provider and p.enabled]
        
        for provider in secondary_providers:
            try:
                await self._store_with_retry(provider, content, embedding, metadata, memory_id)
                logger.info(f"Successfully replicated memory {memory_id} to {provider.name}")
            except Exception as e:
                # Log with full stack trace for debugging
                logger.error(f"Failed to replicate memory {memory_id} to {provider.name}: {e}", exc_info=True)
                # Continue with other providers even if one fails
                continue
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using configured model."""
        if not self.embedding_model:
            raise ValueError("No embedding model configured")
        
        # This will integrate with existing OpenAI embeddings from CoreNexus.py
        return await self.embedding_model.embed_text(text)
    
    def _select_providers(self, request: QueryRequest) -> List[VectorProvider]:
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
    
    async def _query_provider(self, provider: VectorProvider, query_embedding: List[float], 
                             request: QueryRequest) -> List[MemoryResponse]:
        """Query a single provider."""
        return await provider.query(query_embedding, request.limit * 2, request.filters)
    
    async def _query_multiple_providers(self, providers: List[VectorProvider], 
                                       query_embedding: List[float], request: QueryRequest) -> Tuple[List[MemoryResponse], List[str]]:
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
    
    def _filter_and_rank_memories(self, memories: List[MemoryResponse], 
                                 request: QueryRequest) -> List[MemoryResponse]:
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
    
    # =====================================================
    # GRAPH-AWARE RETRIEVAL HELPER METHODS (Phase 1.2)
    # =====================================================
    
    async def _extract_query_entities(self, query: str, graph_provider) -> List[str]:
        """Extract entities from query text using the graph provider."""
        try:
            # Use the graph provider's entity extraction
            entities = await graph_provider._extract_entities(query)
            return [entity['name'] for entity in entities if entity['confidence'] > 0.6]
        except Exception as e:
            logger.warning(f"Query entity extraction failed: {e}")
            return []
    
    async def _create_enhanced_memories_with_graph(
        self, 
        vector_memories: List[MemoryResponse], 
        graph_memories: List[MemoryResponse], 
        extracted_entities: List[str], 
        request: GraphAwareQueryRequest
    ) -> List[EnhancedMemoryResponse]:
        """
        Create enhanced memories by combining vector and graph search results.
        
        Uses hybrid scoring: (1 - graph_weight) * vector_score + graph_weight * graph_score
        """
        # Create a map for fast lookups
        vector_map = {str(mem.id): mem for mem in vector_memories}
        graph_map = {str(mem.id): mem for mem in graph_memories}
        
        # Get all unique memory IDs
        all_memory_ids = set(vector_map.keys()) | set(graph_map.keys())
        
        enhanced_memories = []
        
        for memory_id in all_memory_ids:
            vector_mem = vector_map.get(memory_id)
            graph_mem = graph_map.get(memory_id)
            
            # Determine base memory (prefer vector for completeness)
            base_memory = vector_mem or graph_mem
            
            # Calculate hybrid score
            vector_score = vector_mem.similarity_score if vector_mem else 0.0
            graph_score = graph_mem.similarity_score if graph_mem else 0.0
            
            # Hybrid scoring: combine vector and graph scores
            hybrid_score = (
                (1 - request.graph_weight) * vector_score + 
                request.graph_weight * graph_score
            )
            
            # Calculate graph boost factor
            graph_boost_factor = 1.0
            if graph_mem and vector_mem:
                # Memory found in both - significant boost
                graph_boost_factor = 1.5
            elif graph_mem and not vector_mem:
                # Memory found only through graph relationships
                graph_boost_factor = 1.2
            
            # Generate evidence chains for graph-connected memories
            evidence_chains = []
            if graph_mem and request.max_evidence_chains > 0:
                evidence_chains = await self._generate_evidence_chains(
                    base_memory, extracted_entities, request.max_evidence_chains
                )
            
            # Create graph connection info
            graph_connections = GraphConnection(
                connected_entities=self._extract_memory_entities(base_memory),
                relationship_count=len(evidence_chains),
                centrality_score=graph_score,  # Use graph score as proxy for centrality
                cluster_id=None  # TODO: Implement graph clustering
            )
            
            # Create enhanced memory
            enhanced_mem = EnhancedMemoryResponse(
                **base_memory.dict(),
                similarity_score=hybrid_score,
                evidence_chains=evidence_chains,
                graph_connections=graph_connections,
                graph_boost_factor=graph_boost_factor,
                connection_strength=graph_score if graph_mem else None
            )
            
            enhanced_memories.append(enhanced_mem)
        
        return enhanced_memories
    
    def _extract_memory_entities(self, memory: MemoryResponse) -> List[str]:
        """Extract entity names from memory metadata or content."""
        entities = []
        
        # Check if entities are stored in metadata
        if memory.metadata and 'entities' in memory.metadata:
            entities = memory.metadata['entities']
        else:
            # Simple extraction from content (fallback)
            import re
            pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
            entities = re.findall(pattern, memory.content)
        
        return entities[:5]  # Limit to top 5 entities
    
    async def _generate_evidence_chains(
        self, 
        memory: MemoryResponse, 
        query_entities: List[str], 
        max_chains: int
    ) -> List[EvidenceChain]:
        """Generate evidence chains showing how memory connects to query entities."""
        evidence_chains = []
        
        try:
            memory_entities = self._extract_memory_entities(memory)
            
            # For each query entity, try to find connections to memory entities
            for query_entity in query_entities[:max_chains]:
                for memory_entity in memory_entities:
                    if query_entity.lower() == memory_entity.lower():
                        # Direct match - strongest evidence
                        evidence_chains.append(EvidenceChain(
                            path=[query_entity],
                            relationship_types=[],
                            strength=1.0,
                            confidence=1.0,
                            reasoning=f"Direct mention of '{query_entity}' in memory",
                            hop_count=0
                        ))
                    else:
                        # TODO: Implement BFS graph traversal for multi-hop connections
                        # For now, create a simple semantic connection
                        if self._are_entities_related(query_entity, memory_entity):
                            evidence_chains.append(EvidenceChain(
                                path=[query_entity, memory_entity],
                                relationship_types=['relates_to'],
                                strength=0.7,
                                confidence=0.8,
                                reasoning=f"Semantic relationship between '{query_entity}' and '{memory_entity}'",
                                hop_count=1
                            ))
                
                # Limit evidence chains per memory
                if len(evidence_chains) >= max_chains:
                    break
        
        except Exception as e:
            logger.warning(f"Evidence chain generation failed: {e}")
        
        return evidence_chains[:max_chains]
    
    def _are_entities_related(self, entity1: str, entity2: str) -> bool:
        """Simple heuristic to determine if two entities might be related."""
        # Very simple semantic similarity check
        entity1_lower = entity1.lower()
        entity2_lower = entity2.lower()
        
        # Check for common words or similar patterns
        if len(set(entity1_lower.split()) & set(entity2_lower.split())) > 0:
            return True
        
        # Check for similar prefixes/suffixes
        if entity1_lower.startswith(entity2_lower[:3]) or entity2_lower.startswith(entity1_lower[:3]):
            return True
            
        return False
    
    def _filter_and_rank_graph_memories(
        self, 
        memories: List[EnhancedMemoryResponse], 
        request: GraphAwareQueryRequest
    ) -> List[EnhancedMemoryResponse]:
        """Filter and rank memories using graph-aware scoring."""
        # Filter by similarity threshold
        filtered = [
            m for m in memories 
            if m.similarity_score and m.similarity_score >= request.min_similarity
        ]
        
        # Apply graph-specific filters
        if request.require_entity_match:
            filtered = [m for m in filtered if m.evidence_chains]
        
        # Sort by enhanced scoring that considers graph connections
        filtered.sort(key=lambda m: (
            m.similarity_score * (m.graph_boost_factor if request.boost_connected_results else 1.0) * 0.8 +
            m.importance_score * 0.2
        ), reverse=True)
        
        return filtered
    
    def _calculate_entity_coverage(self, memories: List[EnhancedMemoryResponse]) -> float:
        """Calculate what percentage of results have entity connections."""
        if not memories:
            return 0.0
        
        with_entities = sum(1 for mem in memories if mem.graph_connections.connected_entities)
        return with_entities / len(memories)
    
    def _calculate_avg_evidence_chains(self, memories: List[EnhancedMemoryResponse]) -> float:
        """Calculate average number of evidence chains per result."""
        if not memories:
            return 0.0
        
        total_chains = sum(len(mem.evidence_chains) for mem in memories)
        return total_chains / len(memories)
    
    def _build_entity_connection_map(self, memories: List[EnhancedMemoryResponse]) -> Dict[str, List[str]]:
        """Build a map showing connections between query entities and result entities."""
        connection_map = {}
        
        for memory in memories:
            for chain in memory.evidence_chains:
                if len(chain.path) >= 2:
                    from_entity = chain.path[0]
                    to_entity = chain.path[-1]
                    
                    if from_entity not in connection_map:
                        connection_map[from_entity] = []
                    
                    if to_entity not in connection_map[from_entity]:
                        connection_map[from_entity].append(to_entity)
        
        return connection_map