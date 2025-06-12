"""
Instrumented Unified Vector Store

Extends the UnifiedVectorStore with comprehensive OpenTelemetry instrumentation
for tracing embedding generation, deduplication, and cross-provider operations.
"""

import time
from typing import Any, Optional

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from .models import MemoryRequest, MemoryResponse, QueryRequest, QueryResponse
from .observability import trace_operation, record_metric, add_span_attributes
from .unified_store import UnifiedVectorStore as BaseUnifiedVectorStore

tracer = trace.get_tracer(__name__)


class InstrumentedUnifiedVectorStore(BaseUnifiedVectorStore):
    """
    Unified Vector Store with comprehensive observability.
    
    Adds tracing for:
    - Embedding generation
    - Deduplication checks
    - Cross-provider operations
    - ADM scoring
    - Cache operations
    """
    
    @trace_operation("unified_store.store_memory")
    async def store_memory(self, request: MemoryRequest) -> MemoryResponse:
        """Store memory with detailed performance tracking."""
        start_time = time.time()
        
        # Add initial span attributes
        add_span_attributes(
            content_length=len(request.content),
            has_embedding=bool(request.embedding),
            has_user_id=bool(request.user_id),
            has_conversation_id=bool(request.conversation_id),
            has_importance_score=request.importance_score is not None
        )
        
        try:
            # Trace deduplication check
            if self.deduplication_service:
                with tracer.start_as_current_span("deduplication.check") as dedup_span:
                    dedup_start = time.time()
                    dedup_result = await self.deduplication_service.check_duplicate(
                        content=request.content,
                        metadata=request.metadata
                    )
                    dedup_duration = (time.time() - dedup_start) * 1000
                    
                    dedup_span.set_attribute("is_duplicate", dedup_result.is_duplicate)
                    dedup_span.set_attribute("confidence_score", dedup_result.confidence_score)
                    dedup_span.set_attribute("decision", dedup_result.decision.value)
                    dedup_span.set_attribute("duration_ms", dedup_duration)
                    
                    record_metric("deduplication_checks", 1)
                    if dedup_result.is_duplicate:
                        record_metric("duplicates_detected", 1)
                        add_span_attributes(duplicate_found=True)
                        return dedup_result.existing_memory
            
            # Trace embedding generation
            if not request.embedding and self.embedding_model:
                with tracer.start_as_current_span("embedding.generate") as embed_span:
                    embed_start = time.time()
                    try:
                        embedding = await self._generate_embedding(request.content)
                        embed_duration = (time.time() - embed_start) * 1000
                        
                        embed_span.set_attribute("model", self.embedding_model.__class__.__name__)
                        embed_span.set_attribute("dimension", len(embedding))
                        embed_span.set_attribute("duration_ms", embed_duration)
                        
                        record_metric("embedding_generation_duration", embed_duration)
                        request.embedding = embedding
                        
                    except Exception as e:
                        embed_span.set_status(Status(StatusCode.ERROR, str(e)))
                        embed_span.record_exception(e)
                        record_metric("embedding_generation_errors", 1)
                        raise
            
            # Trace ADM scoring
            if self.adm_enabled and self.adm_engine and request.importance_score is None:
                with tracer.start_as_current_span("adm.calculate_score") as adm_span:
                    adm_start = time.time()
                    adm_result = await self.adm_engine.calculate_adm_score(
                        request.content,
                        request.metadata
                    )
                    adm_duration = (time.time() - adm_start) * 1000
                    
                    adm_span.set_attribute("adm_score", adm_result['adm_score'])
                    adm_span.set_attribute("data_quality", adm_result['data_quality'])
                    adm_span.set_attribute("data_relevance", adm_result['data_relevance'])
                    adm_span.set_attribute("data_intelligence", adm_result['data_intelligence'])
                    adm_span.set_attribute("duration_ms", adm_duration)
                    
                    request.importance_score = adm_result['adm_score']
            
            # Call base implementation
            memory = await super().store_memory(request)
            
            # Record success metrics
            total_duration = (time.time() - start_time) * 1000
            add_span_attributes(
                memory_id=str(memory.id),
                importance_score=memory.importance_score,
                total_duration_ms=total_duration,
                success=True
            )
            
            return memory
            
        except Exception as e:
            add_span_attributes(success=False, error_type=type(e).__name__)
            raise
    
    @trace_operation("unified_store.query_memories")
    async def query_memories(self, request: QueryRequest) -> QueryResponse:
        """Query memories with detailed tracing."""
        start_time = time.time()
        
        # Add query attributes
        add_span_attributes(
            query_text=request.query[:100] if request.query else "",
            query_limit=request.limit,
            min_similarity=request.min_similarity,
            has_filters=bool(request.filters),
            is_empty_query=not request.query or request.query.strip() == ""
        )
        
        # Check cache
        cache_key = self._get_cache_key(request)
        cache_hit = cache_key in self.query_cache
        
        with tracer.start_as_current_span("cache.check") as cache_span:
            cache_span.set_attribute("cache.hit", cache_hit)
            cache_span.set_attribute("cache.key", cache_key[:50])
            
            if cache_hit:
                cached_result = self.query_cache[cache_key]
                if time.time() - cached_result['timestamp'] < 300:
                    cache_span.set_attribute("cache.valid", True)
                    record_metric("cache_hits", 1, {"operation": "query"})
                    return cached_result['response']
                else:
                    cache_span.set_attribute("cache.valid", False)
                    cache_span.set_attribute("cache.expired", True)
        
        record_metric("cache_misses", 1, {"operation": "query"})
        
        # Trace embedding generation for query
        if request.query and self.embedding_model:
            with tracer.start_as_current_span("query.embedding.generate") as embed_span:
                embed_start = time.time()
                try:
                    query_embedding = await self._generate_embedding(request.query)
                    embed_duration = (time.time() - embed_start) * 1000
                    
                    embed_span.set_attribute("dimension", len(query_embedding))
                    embed_span.set_attribute("duration_ms", embed_duration)
                    
                    record_metric("embedding_generation_duration", embed_duration, {"type": "query"})
                    
                except Exception as e:
                    embed_span.set_status(Status(StatusCode.ERROR, str(e)))
                    embed_span.record_exception(e)
                    record_metric("embedding_generation_errors", 1, {"type": "query"})
                    query_embedding = None
        else:
            query_embedding = None
        
        # Execute query
        try:
            response = await super().query_memories(request)
            
            # Add response attributes
            total_duration = (time.time() - start_time) * 1000
            add_span_attributes(
                results_found=response.total_found,
                results_returned=len(response.memories),
                providers_used=",".join(response.providers_used),
                total_duration_ms=total_duration,
                success=True
            )
            
            # Cache the result
            with tracer.start_as_current_span("cache.store"):
                self.query_cache[cache_key] = {
                    'response': response,
                    'timestamp': time.time()
                }
            
            return response
            
        except Exception as e:
            add_span_attributes(success=False, error_type=type(e).__name__)
            raise
    
    async def _query_provider(self, provider, query_embedding, request):
        """Query provider with tracing."""
        with tracer.start_as_current_span(f"provider.query.{provider.name}") as span:
            span.set_attribute("provider.name", provider.name)
            span.set_attribute("provider.enabled", provider.enabled)
            span.set_attribute("provider.primary", provider == self.primary_provider)
            
            start_time = time.time()
            try:
                results = await super()._query_provider(provider, query_embedding, request)
                
                duration = (time.time() - start_time) * 1000
                span.set_attribute("duration_ms", duration)
                span.set_attribute("results_count", len(results))
                
                record_metric(f"{provider.name}.query.duration", duration)
                record_metric(f"{provider.name}.query.results", len(results))
                
                return results
                
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                record_metric(f"{provider.name}.query.errors", 1)
                raise
    
    async def _store_with_retry(self, provider, content, embedding, metadata):
        """Store with retry and tracing."""
        with tracer.start_as_current_span(f"provider.store.{provider.name}") as span:
            span.set_attribute("provider.name", provider.name)
            span.set_attribute("retry_count", provider.config.retry_count)
            
            for attempt in range(provider.config.retry_count):
                try:
                    span.set_attribute("attempt", attempt + 1)
                    start_time = time.time()
                    
                    result = await provider.store(content, embedding, metadata)
                    
                    duration = (time.time() - start_time) * 1000
                    span.set_attribute("duration_ms", duration)
                    span.set_attribute("success", True)
                    
                    record_metric(f"{provider.name}.store.duration", duration)
                    
                    return result
                    
                except Exception as e:
                    if attempt == provider.config.retry_count - 1:
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        span.record_exception(e)
                        record_metric(f"{provider.name}.store.errors", 1)
                        raise
                    else:
                        span.add_event(f"Retry attempt {attempt + 1} failed: {str(e)}")
                        await asyncio.sleep(2 ** attempt)
    
    async def health_check(self):
        """Health check with tracing."""
        with tracer.start_as_current_span("unified_store.health_check") as span:
            start_time = time.time()
            
            try:
                result = await super().health_check()
                
                duration = (time.time() - start_time) * 1000
                span.set_attribute("duration_ms", duration)
                span.set_attribute("overall_status", result['status'])
                span.set_attribute("providers_checked", len(result['providers']))
                
                # Add provider statuses
                for provider_name, provider_health in result['providers'].items():
                    span.set_attribute(f"provider.{provider_name}.status", provider_health['status'])
                
                return result
                
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise