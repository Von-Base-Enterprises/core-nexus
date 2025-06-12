"""
Instrumented Provider Implementations

Extends the existing providers with OpenTelemetry instrumentation
for comprehensive observability of vector operations.
"""

import time
from typing import Any, Optional
from uuid import UUID

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from .models import MemoryResponse, ProviderConfig
from .observability import trace_operation, record_metric, add_span_attributes
from .providers import PgVectorProvider as BasePgVectorProvider
from .providers import ChromaProvider as BaseChromaProvider

tracer = trace.get_tracer(__name__)


class InstrumentedPgVectorProvider(BasePgVectorProvider):
    """
    PgVector provider with OpenTelemetry instrumentation.
    
    Adds detailed tracing and metrics for all vector operations.
    """
    
    @trace_operation("pgvector.store")
    async def store(self, content: str, embedding: list[float], metadata: dict[str, Any]) -> UUID:
        """Store vector with detailed performance tracking."""
        start_time = time.time()
        
        # Add span attributes
        add_span_attributes(
            provider="pgvector",
            operation="store",
            embedding_dimension=len(embedding),
            content_length=len(content),
            has_metadata=bool(metadata)
        )
        
        try:
            # Execute the actual store operation
            memory_id = await super().store(content, embedding, metadata)
            
            # Record success metrics
            duration = (time.time() - start_time) * 1000
            record_metric("pgvector.store.duration", duration)
            record_metric("pgvector.store.success", 1)
            
            add_span_attributes(
                memory_id=str(memory_id),
                duration_ms=duration
            )
            
            return memory_id
            
        except Exception as e:
            # Record failure metrics
            record_metric("pgvector.store.errors", 1, {"error_type": type(e).__name__})
            raise
    
    async def query(self, query_embedding: list[float], limit: int, filters: dict[str, Any]) -> list[MemoryResponse]:
        """Query with comprehensive tracing."""
        with tracer.start_as_current_span("pgvector.query") as span:
            start_time = time.time()
            
            # Set initial attributes
            span.set_attribute("provider", "pgvector")
            span.set_attribute("operation", "query")
            span.set_attribute("query.limit", limit)
            span.set_attribute("query.has_filters", bool(filters))
            span.set_attribute("embedding.dimension", len(query_embedding))
            
            # Check if this is an empty query
            is_empty_query = all(v == 0.0 for v in query_embedding)
            span.set_attribute("query.is_empty", is_empty_query)
            
            try:
                # Trace the actual database query
                with tracer.start_as_current_span("pgvector.query.execute") as query_span:
                    # Get the SQL query that will be executed
                    if is_empty_query and hasattr(self, 'get_recent_memories'):
                        query_span.set_attribute("query.type", "recent_memories")
                        results = await self.get_recent_memories(limit, filters)
                    else:
                        query_span.set_attribute("query.type", "vector_similarity")
                        
                        # Trace index usage
                        with tracer.start_as_current_span("pgvector.check_index") as index_span:
                            async with self.connection_pool.acquire() as conn:
                                # Check if HNSW index exists
                                index_info = await conn.fetchval("""
                                    SELECT COUNT(*) 
                                    FROM pg_indexes 
                                    WHERE tablename = 'vector_memories' 
                                    AND indexdef LIKE '%hnsw%'
                                """)
                                index_span.set_attribute("index.hnsw_exists", bool(index_info))
                        
                        results = await super().query(query_embedding, limit, filters)
                
                # Record results
                duration = (time.time() - start_time) * 1000
                span.set_attribute("query.results_count", len(results))
                span.set_attribute("query.duration_ms", duration)
                
                # Analyze result quality
                if results:
                    similarity_scores = [r.similarity_score for r in results if r.similarity_score]
                    if similarity_scores:
                        span.set_attribute("results.avg_similarity", sum(similarity_scores) / len(similarity_scores))
                        span.set_attribute("results.max_similarity", max(similarity_scores))
                        span.set_attribute("results.min_similarity", min(similarity_scores))
                
                # Record metrics
                record_metric("pgvector.query.duration", duration)
                record_metric("pgvector.query.results", len(results))
                
                span.set_status(Status(StatusCode.OK))
                return results
                
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                record_metric("pgvector.query.errors", 1, {"error_type": type(e).__name__})
                raise
    
    async def health_check(self) -> dict[str, Any]:
        """Health check with performance tracking."""
        with tracer.start_as_current_span("pgvector.health_check") as span:
            start_time = time.time()
            
            try:
                result = await super().health_check()
                
                # Add health info to span
                span.set_attribute("health.status", result.get('status', 'unknown'))
                if 'details' in result:
                    details = result['details']
                    span.set_attribute("health.total_vectors", details.get('total_vectors', 0))
                    span.set_attribute("health.pool_size", details.get('pool_size', 0))
                
                duration = (time.time() - start_time) * 1000
                record_metric("pgvector.health_check.duration", duration)
                
                return result
                
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise


class InstrumentedChromaProvider(BaseChromaProvider):
    """
    ChromaDB provider with OpenTelemetry instrumentation.
    """
    
    @trace_operation("chromadb.store")
    async def store(self, content: str, embedding: list[float], metadata: dict[str, Any]) -> UUID:
        """Store with instrumentation."""
        start_time = time.time()
        
        add_span_attributes(
            provider="chromadb",
            operation="store",
            embedding_dimension=len(embedding),
            content_length=len(content)
        )
        
        try:
            memory_id = await super().store(content, embedding, metadata)
            
            duration = (time.time() - start_time) * 1000
            record_metric("chromadb.store.duration", duration)
            
            return memory_id
            
        except Exception as e:
            record_metric("chromadb.store.errors", 1)
            raise
    
    @trace_operation("chromadb.query")
    async def query(self, query_embedding: list[float], limit: int, filters: dict[str, Any]) -> list[MemoryResponse]:
        """Query with instrumentation."""
        start_time = time.time()
        
        add_span_attributes(
            provider="chromadb",
            operation="query",
            query_limit=limit,
            has_filters=bool(filters)
        )
        
        try:
            results = await super().query(query_embedding, limit, filters)
            
            duration = (time.time() - start_time) * 1000
            record_metric("chromadb.query.duration", duration)
            record_metric("chromadb.query.results", len(results))
            
            add_span_attributes(
                results_count=len(results),
                duration_ms=duration
            )
            
            return results
            
        except Exception as e:
            record_metric("chromadb.query.errors", 1)
            raise


# Specialized tracing for vector operations
class VectorOperationTracer:
    """
    Utility class for tracing vector-specific operations.
    """
    
    @staticmethod
    def trace_embedding_generation(provider: str):
        """Create a span for embedding generation."""
        return tracer.start_as_current_span(
            "embedding.generate",
            attributes={
                "embedding.provider": provider,
                "operation": "generate"
            }
        )
    
    @staticmethod
    def trace_similarity_calculation(num_vectors: int, dimensions: int):
        """Create a span for similarity calculation."""
        return tracer.start_as_current_span(
            "vector.similarity_calculation",
            attributes={
                "vector.count": num_vectors,
                "vector.dimensions": dimensions,
                "operation": "similarity"
            }
        )
    
    @staticmethod
    def trace_index_operation(operation: str, index_type: str):
        """Create a span for index operations."""
        return tracer.start_as_current_span(
            f"index.{operation}",
            attributes={
                "index.type": index_type,
                "operation": operation
            }
        )


# Query performance analyzer
class QueryPerformanceAnalyzer:
    """
    Analyzes query performance and adds detailed tracing.
    """
    
    def __init__(self, tracer):
        self.tracer = tracer
    
    async def analyze_query_plan(self, connection, query: str, params: tuple):
        """Analyze PostgreSQL query execution plan."""
        with self.tracer.start_as_current_span("query.analyze_plan") as span:
            try:
                # Get query plan
                explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
                plan_result = await connection.fetchval(explain_query, *params)
                
                if plan_result:
                    plan = plan_result[0]["Plan"]
                    
                    # Extract key metrics
                    span.set_attribute("plan.total_time", plan.get("Actual Total Time", 0))
                    span.set_attribute("plan.rows", plan.get("Actual Rows", 0))
                    span.set_attribute("plan.node_type", plan.get("Node Type", "unknown"))
                    
                    # Check for sequential scans
                    if "Seq Scan" in str(plan):
                        span.set_attribute("plan.has_seq_scan", True)
                        span.add_event("Sequential scan detected - consider adding index")
                    
                    # Check for index usage
                    if "Index Scan" in str(plan) or "Index Only Scan" in str(plan):
                        span.set_attribute("plan.uses_index", True)
                    
                    return plan
                    
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, "Failed to analyze query plan"))
                return None