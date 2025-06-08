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
    ImportanceScoring
)

logger = logging.getLogger(__name__)


class VectorProvider(ABC):
    """Abstract base class for vector storage providers."""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.name = config.name
        self.enabled = config.enabled
        
    @abstractmethod
    async def store(self, content: str, embedding: List[float], metadata: Dict[str, Any]) -> UUID:
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
        self.primary_provider = next((p for p in providers if p.config.primary), providers[0])
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
            
            # Async replication to secondary providers for resilience
            asyncio.create_task(self._replicate_to_secondaries(
                memory_id, request.content, embedding, metadata
            ))
            
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
            
            # Generate query embedding
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
            self.query_cache[cache_key] = {
                'response': response,
                'timestamp': time.time()
            }
            
            logger.info(f"Query returned {len(filtered_memories)} memories in {query_time:.1f}ms")
            return response
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
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
        
        return {
            'status': 'healthy' if overall_healthy else 'degraded',
            'providers': results,
            'stats': self.stats,
            'cache_size': len(self.query_cache)
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
                               embedding: List[float], metadata: Dict[str, Any]) -> UUID:
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
                                       embedding: List[float], metadata: Dict[str, Any]):
        """Replicate to secondary providers for resilience."""
        secondary_providers = [p for p in self.providers.values() 
                             if p != self.primary_provider and p.enabled]
        
        for provider in secondary_providers:
            try:
                await self._store_with_retry(provider, content, embedding, metadata)
                logger.debug(f"Replicated memory {memory_id} to {provider.name}")
            except Exception as e:
                logger.warning(f"Failed to replicate to {provider.name}: {e}")
    
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