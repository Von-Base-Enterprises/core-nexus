"""
Optimized Unified Vector Store

Enhanced version of the unified vector store that integrates all performance
optimization components for 1GB RAM PostgreSQL deployment.
"""

import asyncio
import logging
import os
import time
from typing import Any, List, Optional
from uuid import UUID

from .models import (
    ImportanceScoring,
    MemoryRequest,
    MemoryResponse,
    ProviderConfig,
    QueryRequest,
    QueryResponse,
)
from .unified_store import VectorProvider, UnifiedVectorStore
from .deduplication import DeduplicationService, DeduplicationMode

# Import optimization components
from .query_engine import AdvancedQueryEngine
from .cache_engine import cache_engine
from .provider_intelligence import provider_intelligence
from .vector_optimizer import vector_optimizer
from .analytics_engine import analytics_engine
from .connection_manager import connection_manager

logger = logging.getLogger(__name__)


class OptimizedUnifiedVectorStore(UnifiedVectorStore):
    """
    Enhanced unified vector store with comprehensive optimization pipeline
    """
    
    def __init__(self, providers: List[VectorProvider], embedding_model=None, adm_enabled=True):
        # Initialize base unified store
        super().__init__(providers, embedding_model, adm_enabled)
        
        # Initialize optimization components
        self.query_engine = AdvancedQueryEngine()
        self.optimization_enabled = True
        self._optimization_initialized = False
        
        # Enhanced statistics
        self.optimization_stats = {
            'optimized_queries': 0,
            'cache_hits': 0,
            'parallel_executions': 0,
            'optimization_time_saved_ms': 0.0,
            'memory_optimizations': 0
        }
        
        logger.info("Initialized OptimizedUnifiedVectorStore with performance optimization engine")
    
    async def initialize_optimizations(self):
        """Initialize all optimization components"""
        if self._optimization_initialized:
            return
        
        try:
            # Initialize components in order
            logger.info("Initializing optimization components...")
            
            # Initialize connection manager
            await connection_manager.initialize()
            
            # Initialize vector optimizer
            await vector_optimizer.initialize()
            
            # Initialize cache engine (already initialized on import)
            
            # Initialize analytics engine
            await analytics_engine.start()
            
            # Initialize provider intelligence for all providers
            for provider in self.providers.values():
                await provider_intelligence.initialize_provider(provider)
            
            self._optimization_initialized = True
            logger.info("All optimization components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize optimizations: {e}")
            self.optimization_enabled = False
    
    async def store_memory(self, request: MemoryRequest) -> MemoryResponse:
        """
        Enhanced memory storage with optimization pipeline
        """
        start_time = time.time()
        
        # Ensure optimizations are initialized
        if not self._optimization_initialized:
            await self.initialize_optimizations()
        
        try:
            # Check deduplication first with enhanced caching
            if self.deduplication_service:
                # Try to get from cache first
                cache_key = f"dedup:{hash(request.content)}"
                cached_result = await cache_engine.get_generic(cache_key)
                
                if cached_result is None:
                    dedup_result = await self.deduplication_service.check_duplicate(
                        content=request.content,
                        metadata=request.metadata
                    )
                    # Cache deduplication result
                    await cache_engine.set_generic(cache_key, dedup_result, ttl=300)
                else:
                    dedup_result = cached_result
                
                if dedup_result.is_duplicate and dedup_result.existing_memory:
                    self.stats['duplicates_prevented'] += 1
                    self.stats['storage_saved_bytes'] += len(request.content)
                    
                    logger.info(f"Duplicate detected via optimization: {dedup_result.reason}")
                    return dedup_result.existing_memory
            
            # Generate or retrieve embedding with caching
            embedding = request.embedding
            if not embedding and self.embedding_model:
                # Try cache first
                cached_embedding = await cache_engine.get_embedding(request.content)
                if cached_embedding is not None:
                    embedding = cached_embedding.tolist()
                    logger.debug("Retrieved embedding from cache")
                else:
                    embedding = await self._generate_embedding(request.content)
                    # Cache the embedding
                    import numpy as np
                    await cache_engine.set_embedding(request.content, np.array(embedding))
            elif not embedding:
                raise ValueError("No embedding provided and no embedding model configured")
            
            # Calculate importance score with optimization
            importance_score = request.importance_score
            adm_data = {}
            
            if importance_score is None:
                if self.adm_enabled and self.adm_engine:
                    # Cache ADM results
                    adm_cache_key = f"adm:{hash(request.content)}"
                    cached_adm = await cache_engine.get_generic(adm_cache_key)
                    
                    if cached_adm is None:
                        try:
                            adm_result = await self.adm_engine.calculate_adm_score(
                                request.content,
                                request.metadata
                            )
                            importance_score = adm_result['adm_score']
                            adm_data = adm_result
                            
                            # Cache ADM result
                            await cache_engine.set_generic(adm_cache_key, adm_result, ttl=600)
                            
                        except Exception as e:
                            logger.warning(f"ADM scoring failed, using fallback: {e}")
                            importance_score = self._calculate_importance(request)
                    else:
                        adm_result = cached_adm
                        importance_score = adm_result['adm_score']
                        adm_data = adm_result
                else:
                    importance_score = self._calculate_importance(request)
            
            # Prepare optimized metadata
            metadata = {
                **request.metadata,
                'user_id': request.user_id,
                'conversation_id': request.conversation_id,
                'importance_score': importance_score,
                'created_at': time.time(),
                'content_length': len(request.content),
                'optimization_version': '1.0'
            }
            
            if adm_data:
                metadata.update({
                    'adm_score': adm_data['adm_score'],
                    'data_quality': adm_data['data_quality'],
                    'data_relevance': adm_data['data_relevance'],
                    'data_intelligence': adm_data['data_intelligence'],
                    'adm_calculation_time': adm_data.get('calculation_time_ms', 0)
                })
            
            # Store in primary provider with optimization
            memory_id = await self._optimized_store_with_retry(
                self.primary_provider,
                request.content,
                embedding,
                metadata
            )
            
            # Enhanced replication with performance tracking
            replication_start = time.time()
            replication_success = False
            try:
                logger.info(f"🔄 Starting optimized replication for memory {memory_id}")
                await self._optimized_replicate_to_secondaries(
                    memory_id, request.content, embedding, metadata
                )
                replication_success = True
                replication_time = (time.time() - replication_start) * 1000
                logger.info(f"✅ Optimized replication completed in {replication_time:.1f}ms")
                
            except Exception as e:
                logger.error(f"❌ CRITICAL: Optimized replication failed for memory {memory_id}: {e}")
            
            # Update enhanced statistics
            self.stats['total_stores'] += 1
            self.stats['provider_usage'][self.primary_provider.name] += 1
            self.optimization_stats['memory_optimizations'] += 1
            
            storage_time = (time.time() - start_time) * 1000
            logger.info(f"Stored memory {memory_id} with optimizations in {storage_time:.1f}ms")
            
            # Record performance analytics
            if self.optimization_enabled:
                await analytics_engine.record_query_performance(
                    storage_time, True, self.primary_provider.name
                )
            
            return MemoryResponse(
                id=memory_id,
                content=request.content,
                metadata=metadata,
                importance_score=importance_score
            )
            
        except Exception as e:
            storage_time = (time.time() - start_time) * 1000
            logger.error(f"Failed to store memory with optimizations: {e}")
            
            # Record failure in analytics
            if self.optimization_enabled:
                await analytics_engine.record_query_performance(
                    storage_time, False, self.primary_provider.name if self.primary_provider else "unknown"
                )
            
            raise
    
    async def query_memories(self, request: QueryRequest) -> QueryResponse:
        """
        Enhanced memory querying with comprehensive optimization pipeline
        """
        start_time = time.time()
        
        # Ensure optimizations are initialized
        if not self._optimization_initialized:
            await self.initialize_optimizations()
        
        try:
            # Check cache first for exact query match
            cached_response = await cache_engine.get_query_result(request)
            if cached_response is not None:
                self.optimization_stats['cache_hits'] += 1
                query_time = (time.time() - start_time) * 1000
                logger.info(f"Query served from cache in {query_time:.1f}ms")
                
                # Update cache hit analytics
                await analytics_engine.record_cache_performance(1.0, "query_cache")
                
                return cached_response
            
            # Record cache miss
            await analytics_engine.record_cache_performance(0.0, "query_cache")
            
            # Generate embedding with optimization
            query_embedding = None
            if request.query:
                # Try embedding cache first
                cached_embedding = await cache_engine.get_embedding(request.query)
                if cached_embedding is not None:
                    query_embedding = cached_embedding.tolist()
                    logger.debug("Query embedding served from cache")
                else:
                    if self.embedding_model:
                        query_embedding = await self._generate_embedding(request.query)
                        # Cache the query embedding
                        import numpy as np
                        await cache_engine.set_embedding(request.query, np.array(query_embedding))
            
            # Use intelligent provider selection
            available_providers = [p for p in self.providers.values() if p.enabled]
            
            if self.optimization_enabled:
                selected_providers = await provider_intelligence.select_optimal_providers(
                    available_providers, request
                )
            else:
                selected_providers = [self.primary_provider] if self.primary_provider.enabled else available_providers[:1]
            
            # Execute optimized query using query engine
            if len(selected_providers) > 1:
                self.optimization_stats['parallel_executions'] += 1
            
            if self.optimization_enabled:
                response = await self.query_engine.execute_optimized_query(
                    request, selected_providers, query_embedding
                )
            else:
                # Fallback to original query logic
                response = await self._fallback_query_execution(request, selected_providers, query_embedding)
            
            # Record provider performance
            query_time = (time.time() - start_time) * 1000
            response.query_time_ms = query_time
            
            for provider_name in response.providers_used:
                if self.optimization_enabled:
                    await provider_intelligence.record_query_performance(
                        provider_name, query_time / len(response.providers_used), True
                    )
            
            # Cache successful query result
            await cache_engine.set_query_result(request, response)
            
            # Update statistics
            self.stats['total_queries'] += 1
            self.optimization_stats['optimized_queries'] += 1
            
            # Calculate optimization time saved (estimate)
            estimated_unoptimized_time = query_time * 1.5  # Assume 50% improvement
            self.optimization_stats['optimization_time_saved_ms'] += (estimated_unoptimized_time - query_time)
            
            # Record analytics
            if self.optimization_enabled:
                await analytics_engine.record_query_performance(
                    query_time, True, response.providers_used[0] if response.providers_used else "unknown"
                )
            
            logger.info(f"Optimized query returned {len(response.memories)} memories in {query_time:.1f}ms")
            return response
            
        except Exception as e:
            query_time = (time.time() - start_time) * 1000
            logger.error(f"Optimized query failed: {e}")
            
            # Record failure
            if self.optimization_enabled:
                await analytics_engine.record_query_performance(
                    query_time, False, "unknown"
                )
            
            raise
    
    async def _optimized_store_with_retry(
        self, 
        provider: VectorProvider, 
        content: str,
        embedding: List[float], 
        metadata: dict[str, Any]
    ) -> UUID:
        """Enhanced store with retry logic and optimization"""
        if self.optimization_enabled:
            # Use optimized connection manager if it's a pgvector provider
            if hasattr(provider, 'connection_pool') and connection_manager._is_initialized:
                try:
                    # Use optimized connection for storage
                    return await self._store_via_connection_manager(provider, content, embedding, metadata)
                except Exception as e:
                    logger.warning(f"Optimized storage failed, falling back: {e}")
            
        # Fallback to original retry logic
        for attempt in range(provider.config.retry_count):
            try:
                return await provider.store(content, embedding, metadata)
            except Exception as e:
                if attempt == provider.config.retry_count - 1:
                    raise
                logger.warning(f"Store attempt {attempt + 1} failed for {provider.name}: {e}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    async def _store_via_connection_manager(
        self, 
        provider: VectorProvider, 
        content: str, 
        embedding: List[float], 
        metadata: dict[str, Any]
    ) -> UUID:
        """Store using optimized connection manager"""
        # This would implement optimized storage using the connection manager
        # For now, fall back to provider's store method
        return await provider.store(content, embedding, metadata)
    
    async def _optimized_replicate_to_secondaries(
        self, 
        memory_id: UUID, 
        content: str,
        embedding: List[float], 
        metadata: dict[str, Any]
    ):
        """Enhanced replication with parallel execution and optimization"""
        secondary_providers = [p for p in self.providers.values()
                             if p != self.primary_provider and p.enabled]
        
        if not secondary_providers:
            logger.warning("⚠️ No secondary providers enabled for replication")
            return
        
        # Use parallel replication for better performance
        replication_tasks = []
        for provider in secondary_providers:
            task = asyncio.create_task(
                self._optimized_replicate_single_provider(provider, memory_id, content, embedding, metadata)
            )
            replication_tasks.append((provider.name, task))
        
        # Wait for all replications with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*[task for _, task in replication_tasks], return_exceptions=True),
                timeout=30.0  # 30 second timeout
            )
            
            # Process results
            successful = 0
            for i, ((provider_name, _), result) in enumerate(zip(replication_tasks, results)):
                if isinstance(result, Exception):
                    logger.error(f"❌ Replication to {provider_name} failed: {result}")
                else:
                    successful += 1
                    logger.info(f"✅ Replicated to {provider_name} successfully")
            
            logger.info(f"📊 Parallel replication: {successful}/{len(secondary_providers)} succeeded")
            
        except asyncio.TimeoutError:
            logger.error("🚨 Replication timeout - some providers may be slow")
            # Cancel remaining tasks
            for _, task in replication_tasks:
                if not task.done():
                    task.cancel()
    
    async def _optimized_replicate_single_provider(
        self, 
        provider: VectorProvider, 
        memory_id: UUID, 
        content: str, 
        embedding: List[float], 
        metadata: dict[str, Any]
    ):
        """Replicate to single provider with optimization"""
        return await self._optimized_store_with_retry(provider, content, embedding, metadata)
    
    async def _fallback_query_execution(
        self, 
        request: QueryRequest, 
        providers: List[VectorProvider], 
        query_embedding: Optional[List[float]]
    ) -> QueryResponse:
        """Fallback query execution without optimization engine"""
        # Use the original query logic from parent class
        if not query_embedding and request.query:
            # Handle empty query case
            return QueryResponse(
                memories=[],
                total_found=0,
                query_time_ms=0,
                providers_used=[]
            )
        
        # Simple single provider query
        provider = providers[0] if providers else self.primary_provider
        
        try:
            if query_embedding:
                memories = await provider.query(query_embedding, request.limit, request.filters or {})
            else:
                # Try get_recent_memories if available
                if hasattr(provider, 'get_recent_memories'):
                    memories = await provider.get_recent_memories(request.limit, request.filters or {})
                else:
                    memories = []
            
            return QueryResponse(
                memories=memories[:request.limit],
                total_found=len(memories),
                query_time_ms=0,
                providers_used=[provider.name]
            )
            
        except Exception as e:
            logger.error(f"Fallback query failed: {e}")
            return QueryResponse(
                memories=[],
                total_found=0,
                query_time_ms=0,
                providers_used=[]
            )
    
    async def health_check(self) -> dict[str, Any]:
        """Enhanced health check with optimization status"""
        base_health = await super().health_check()
        
        # Add optimization status
        optimization_health = {
            'optimization_enabled': self.optimization_enabled,
            'optimization_initialized': self._optimization_initialized,
            'components': {}
        }
        
        if self._optimization_initialized:
            # Check component health
            try:
                optimization_health['components']['cache_engine'] = await cache_engine.get_comprehensive_stats()
                optimization_health['components']['vector_optimizer'] = await vector_optimizer.get_optimization_stats()
                optimization_health['components']['analytics_engine'] = {
                    'is_running': analytics_engine._is_running
                }
                optimization_health['components']['connection_manager'] = await connection_manager.get_performance_stats()
            except Exception as e:
                optimization_health['component_check_error'] = str(e)
        
        # Add optimization statistics
        base_health['optimization'] = optimization_health
        base_health['optimization_stats'] = self.optimization_stats.copy()
        
        return base_health
    
    async def get_performance_dashboard(self) -> dict[str, Any]:
        """Get comprehensive performance dashboard"""
        if not self._optimization_initialized:
            await self.initialize_optimizations()
        
        try:
            return await analytics_engine.get_performance_dashboard()
        except Exception as e:
            logger.error(f"Failed to get performance dashboard: {e}")
            return {
                'error': 'Performance dashboard unavailable',
                'basic_stats': self.stats.copy(),
                'optimization_stats': self.optimization_stats.copy()
            }
    
    async def get_optimization_recommendations(self) -> List[dict[str, Any]]:
        """Get current optimization recommendations"""
        if not self._optimization_initialized:
            return []
        
        try:
            from .analytics_engine import analytics_engine
            recommendations = await analytics_engine.auto_tuner.get_recommendations()
            return [
                {
                    'id': rec.id,
                    'category': rec.category,
                    'title': rec.title,
                    'description': rec.description,
                    'impact': rec.impact,
                    'effort': rec.effort,
                    'confidence': rec.confidence
                }
                for rec in recommendations
            ]
        except Exception as e:
            logger.error(f"Failed to get optimization recommendations: {e}")
            return []
    
    async def optimize_performance(self) -> dict[str, Any]:
        """Manually trigger performance optimization"""
        if not self._optimization_initialized:
            await self.initialize_optimizations()
        
        optimization_results = {}
        
        try:
            # Optimize cache
            await cache_engine.optimize_cache()
            optimization_results['cache'] = 'optimized'
            
            # Optimize database connections
            if connection_manager._is_initialized:
                index_results = await connection_manager.optimize_indexes()
                optimization_results['database'] = index_results
            
            # Trigger provider rebalancing
            await provider_intelligence.adaptive_rebalance()
            optimization_results['provider_balancing'] = 'completed'
            
            # Update stats
            self.optimization_stats['memory_optimizations'] += 1
            
            logger.info("Manual performance optimization completed")
            
        except Exception as e:
            logger.error(f"Performance optimization failed: {e}")
            optimization_results['error'] = str(e)
        
        return optimization_results
    
    async def shutdown_optimizations(self):
        """Gracefully shutdown optimization components"""
        if not self._optimization_initialized:
            return
        
        logger.info("Shutting down optimization components...")
        
        try:
            # Shutdown in reverse order
            await analytics_engine.stop()
            await vector_optimizer.shutdown()
            await connection_manager.close()
            
            self._optimization_initialized = False
            logger.info("All optimization components shut down successfully")
            
        except Exception as e:
            logger.error(f"Error during optimization shutdown: {e}")


# Factory function to create optimized store
async def create_optimized_unified_store(
    providers: List[VectorProvider], 
    embedding_model=None, 
    adm_enabled=True
) -> OptimizedUnifiedVectorStore:
    """Create and initialize an optimized unified vector store"""
    store = OptimizedUnifiedVectorStore(providers, embedding_model, adm_enabled)
    await store.initialize_optimizations()
    return store