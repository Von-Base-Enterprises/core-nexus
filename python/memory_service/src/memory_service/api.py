"""
FastAPI REST API for Unified Memory Service

Provides HTTP endpoints for the Core Nexus Long Term Memory Module,
wrapping the UnifiedVectorStore with proper error handling and validation.
"""

import asyncio
import logging
import time
import os
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST
from prometheus_fastapi_instrumentator import Instrumentator

from .models import (
    MemoryRequest, MemoryResponse, QueryRequest, QueryResponse,
    HealthCheckResponse, MemoryStats, ProviderConfig
)
from .unified_store import UnifiedVectorStore
from .providers import PineconeProvider, ChromaProvider, PgVectorProvider
# Temporarily disable complex imports for stable deployment
# from .metrics import (
#     metrics_collector, get_metrics, record_request, time_request,
#     record_memory_operation, set_service_info
# )
# from .db_monitoring import get_database_health

logger = logging.getLogger(__name__)

# Global instances
unified_store: Optional[UnifiedVectorStore] = None
usage_collector: Optional['UsageCollector'] = None
memory_dashboard: Optional['MemoryDashboard'] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    global unified_store, usage_collector, memory_dashboard
    
    # Startup
    logger.info("Initializing Core Nexus Memory Service...")
    
    # Initialize providers based on environment/config
    providers = []
    
    # Add pgvector if PostgreSQL is available
    pgvector_config = ProviderConfig(
        name="pgvector",
        enabled=True,
        primary=True,  # Make pgvector primary for SQL capabilities
        config={
            "host": "localhost",
            "port": 5432,
            "database": "core_nexus",
            "user": "postgres",
            "password": "secure_password_change_me",
            "table_name": "vector_memories",
            "embedding_dim": 1536,
            "distance_metric": "cosine"
        }
    )
    try:
        pgvector_provider = PgVectorProvider(pgvector_config)
        providers.append(pgvector_provider)
        logger.info("PgVector provider initialized")
    except Exception as e:
        logger.warning(f"PgVector provider failed to initialize: {e}")
    
    # Add Pinecone if configured
    pinecone_config = ProviderConfig(
        name="pinecone",
        enabled=False,  # Disabled by default, enable with env var
        primary=False,
        config={
            "api_key": os.getenv("PINECONE_API_KEY", ""),
            "index_name": "core-nexus-memories",
            "embedding_dim": 1536
        }
    )
    try:
        pinecone_provider = PineconeProvider(pinecone_config)
        if pinecone_config.enabled:
            providers.append(pinecone_provider)
            logger.info("Pinecone provider initialized")
    except Exception as e:
        logger.warning(f"Pinecone provider failed to initialize: {e}")
    
    # Add ChromaDB (always available as local fallback)
    chroma_config = ProviderConfig(
        name="chromadb",
        enabled=True,
        primary=len(providers) == 0,  # Primary if others failed
        config={
            "collection_name": "core_nexus_memories",
            "persist_directory": "./memory_service_chroma"
        }
    )
    try:
        chroma_provider = ChromaProvider(chroma_config)
        providers.append(chroma_provider)
        logger.info("ChromaDB provider initialized")
    except Exception as e:
        logger.error(f"ChromaDB provider failed to initialize: {e}")
    
    # Add Graph Provider for knowledge graph functionality - TEMPORARILY DISABLED
    # TODO: Re-enable once deployment is stable
    logger.info("Graph provider temporarily disabled for stable deployment")
    
    if not providers:
        raise RuntimeError("No vector providers could be initialized")
    
    # Initialize unified store with ADM enabled
    unified_store = UnifiedVectorStore(providers, adm_enabled=True)
    logger.info(f"Memory service started with {len(providers)} providers")
    
    # Initialize usage tracking - DISABLED FOR STABLE DEPLOYMENT
    # from .tracking import UsageCollector
    # usage_collector = UsageCollector(unified_store=unified_store)
    # logger.info("Usage tracking initialized")
    usage_collector = None
    
    # Initialize dashboard - DISABLED FOR STABLE DEPLOYMENT
    # from .dashboard import MemoryDashboard
    # memory_dashboard = MemoryDashboard(unified_store)
    # logger.info("Memory dashboard initialized")
    memory_dashboard = None
    
    # Set startup time for uptime tracking
    import time
    app.state.start_time = time.time()
    
    # Initialize service info metrics - DISABLED FOR STABLE DEPLOYMENT
    # set_service_info(
    #     version="0.1.0",
    #     config={
    #         "providers": [p.name for p in providers],
    #         "environment": os.getenv("ENVIRONMENT", "production")
    #     }
    # )
    
    yield
    
    # Shutdown
    logger.info("Shutting down Memory Service...")
    
    # Close provider connections
    for provider in providers:
        if hasattr(provider, 'close'):
            try:
                await provider.close()
            except Exception as e:
                logger.warning(f"Error closing provider {provider.name}: {e}")
    
    unified_store = None
    usage_collector = None
    memory_dashboard = None


def create_memory_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="Core Nexus Memory Service",
        description="Unified Long Term Memory Module with multi-provider vector storage",
        version="0.1.0",
        lifespan=lifespan
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # FastAPI Prometheus Instrumentator for enhanced metrics
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_round_latency_decimals=True,
        excluded_handlers=["/metrics"],  # Don't track metrics endpoint itself
    )
    instrumentator.instrument(app)
    instrumentator.expose(app, endpoint="/metrics/fastapi")
    
    # Custom Prometheus metrics middleware
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Record metrics - DISABLED FOR STABLE DEPLOYMENT
        process_time = time.time() - start_time
        # record_request(
        #     method=request.method,
        #     endpoint=request.url.path,
        #     status_code=response.status_code
        # )
        
        # Add process time header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
    
    # Add usage tracking middleware - DISABLED FOR STABLE DEPLOYMENT
    # @app.on_event("startup")
    # async def add_usage_tracking():
    #     if usage_collector:
    #         from .tracking import UsageTrackingMiddleware
    #         app.add_middleware(UsageTrackingMiddleware, usage_collector=usage_collector)
    
    def get_store() -> UnifiedVectorStore:
        """Dependency to get the unified store instance."""
        if unified_store is None:
            raise HTTPException(
                status_code=503,
                detail="Memory service not initialized"
            )
        return unified_store
    
    @app.get("/health", response_model=HealthCheckResponse)
    async def health_check(store: UnifiedVectorStore = Depends(get_store)):
        """
        Check the health of all vector providers.
        
        Returns detailed status of each provider and overall service health.
        """
        try:
            health_data = await store.health_check()
            
            return HealthCheckResponse(
                status=health_data['status'],
                providers=health_data['providers'],
                total_memories=health_data['stats']['total_stores'],
                avg_query_time_ms=health_data['stats']['avg_query_time'],
                uptime_seconds=(time.time() - app.state.start_time) if hasattr(app.state, 'start_time') else 0
            )
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # @app.get("/metrics") - DISABLED FOR STABLE DEPLOYMENT
    # async def metrics_endpoint():
    #     """
    #     Prometheus metrics endpoint.
    #     
    #     Returns service metrics in Prometheus text format for monitoring and alerting.
    #     """
    #     try:
    #         # Collect current metrics
    #         if unified_store:
    #             await metrics_collector.collect_service_metrics(unified_store)
    #         
    #         # Return Prometheus metrics
    #         metrics_data = get_metrics()
    #         return Response(
    #             content=metrics_data,
    #             media_type=CONTENT_TYPE_LATEST,
    #             headers={"Cache-Control": "no-cache"}
    #         )
    #     except Exception as e:
    #         logger.error(f"Metrics collection failed: {e}")
    #         raise HTTPException(status_code=500, detail="Metrics collection failed")
    
    # @app.get("/db/stats") - DISABLED FOR STABLE DEPLOYMENT
    # async def database_stats():
    #     """
    #     Database statistics and performance metrics.
    #     
    #     Returns connection pool status, slow queries, and database health information.
    #     """
    #     try:
    #         health_data = await get_database_health()
    #         return JSONResponse(content=health_data)
    #     except Exception as e:
    #         logger.error(f"Database stats failed: {e}")
    #         raise HTTPException(status_code=500, detail="Database stats unavailable")
    
    @app.post("/memories", response_model=MemoryResponse)
    async def store_memory(
        request: MemoryRequest,
        background_tasks: BackgroundTasks,
        store: UnifiedVectorStore = Depends(get_store)
    ):
        """
        Store a new memory with automatic embedding generation.
        
        The memory will be stored across all enabled providers for resilience.
        """
        try:
            start_time = time.time()
            memory = await store.store_memory(request)
            
            # Log performance
            store_time = (time.time() - start_time) * 1000
            logger.info(f"Memory stored in {store_time:.1f}ms: {memory.id}")
            
            return memory
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    @app.post("/memories/query", response_model=QueryResponse)
    async def query_memories(
        request: QueryRequest,
        store: UnifiedVectorStore = Depends(get_store)
    ):
        """
        Query memories using natural language.
        
        Returns semantically similar memories ranked by relevance and importance.
        """
        try:
            start_time = time.time()
            response = await store.query_memories(request)
            
            # Add request timing info
            total_time = (time.time() - start_time) * 1000
            logger.info(f"Query completed in {total_time:.1f}ms, found {response.total_found} memories")
            
            return response
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    @app.get("/memories/stats", response_model=MemoryStats)
    async def get_memory_stats(store: UnifiedVectorStore = Depends(get_store)):
        """
        Get comprehensive memory service statistics.
        
        Includes counts, performance metrics, and provider-specific details.
        """
        try:
            stats = store.stats
            health_data = await store.health_check()
            
            # Calculate provider-specific stats
            memories_by_provider = {}
            for provider_name, provider_health in health_data['providers'].items():
                if 'details' in provider_health and 'total_vectors' in provider_health['details']:
                    memories_by_provider[provider_name] = provider_health['details']['total_vectors']
                else:
                    memories_by_provider[provider_name] = 0
            
            return MemoryStats(
                total_memories=stats['total_stores'],
                memories_by_provider=memories_by_provider,
                avg_importance_score=0.5,  # TODO: Calculate from actual data
                queries_last_hour=stats['total_queries'],  # TODO: Implement time-based tracking
                avg_query_time_ms=stats['avg_query_time']
            )
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    @app.get("/providers")
    async def list_providers(store: UnifiedVectorStore = Depends(get_store)):
        """
        List all configured vector providers and their status.
        
        Useful for monitoring and debugging provider configurations.
        """
        try:
            provider_info = []
            
            for name, provider in store.providers.items():
                provider_stats = await provider.get_stats()
                provider_info.append({
                    'name': name,
                    'enabled': provider.enabled,
                    'primary': provider == store.primary_provider,
                    'config': {
                        'retry_count': provider.config.retry_count,
                        'timeout_seconds': provider.config.timeout_seconds
                    },
                    'stats': provider_stats
                })
            
            return {
                'providers': provider_info,
                'primary_provider': store.primary_provider.name,
                'total_providers': len(store.providers)
            }
            
        except Exception as e:
            logger.error(f"Failed to list providers: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    @app.post("/memories/batch", response_model=List[MemoryResponse])
    async def store_memories_batch(
        requests: List[MemoryRequest],
        store: UnifiedVectorStore = Depends(get_store)
    ):
        """
        Store multiple memories in batch for better performance.
        
        Processes memories concurrently while maintaining data integrity.
        """
        try:
            if len(requests) > 100:
                raise HTTPException(
                    status_code=400, 
                    detail="Batch size limited to 100 memories"
                )
            
            start_time = time.time()
            
            # Process batch concurrently
            tasks = [store.store_memory(req) for req in requests]
            memories = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle any failures
            successful_memories = []
            for i, memory in enumerate(memories):
                if isinstance(memory, Exception):
                    logger.error(f"Failed to store memory {i}: {memory}")
                else:
                    successful_memories.append(memory)
            
            batch_time = (time.time() - start_time) * 1000
            logger.info(f"Batch stored {len(successful_memories)}/{len(requests)} memories in {batch_time:.1f}ms")
            
            return successful_memories
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Batch store failed: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    @app.delete("/memories/cache")
    async def clear_query_cache(store: UnifiedVectorStore = Depends(get_store)):
        """
        Clear the query result cache.
        
        Use this when you need fresh results or after significant data updates.
        """
        try:
            cache_size = len(store.query_cache)
            store.query_cache.clear()
            
            return {
                'message': f'Cleared {cache_size} cached queries',
                'cache_size_before': cache_size,
                'cache_size_after': 0
            }
            
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    # =============================================================================
    # DASHBOARD AND ANALYTICS ENDPOINTS
    # =============================================================================
    
    @app.get("/dashboard/metrics")
    async def get_dashboard_metrics():
        """
        Get comprehensive dashboard metrics.
        
        Provides real-time insights into memory service performance and quality.
        """
        try:
            if not memory_dashboard:
                raise HTTPException(status_code=503, detail="Dashboard not initialized")
            
            metrics = await memory_dashboard.get_comprehensive_metrics()
            return metrics.to_dict()
            
        except Exception as e:
            logger.error(f"Dashboard metrics failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to get dashboard metrics")
    
    @app.get("/dashboard/quality-trends")
    async def get_quality_trends(days: int = 7):
        """
        Get memory quality trends over time.
        
        Shows how memory quality has evolved over the specified period.
        """
        try:
            if not memory_dashboard:
                raise HTTPException(status_code=503, detail="Dashboard not initialized")
            
            trends = await memory_dashboard.get_quality_trends(days=days)
            return {"trends": trends, "period_days": days}
            
        except Exception as e:
            logger.error(f"Quality trends failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to get quality trends")
    
    @app.get("/dashboard/provider-performance")
    async def get_provider_performance():
        """
        Get detailed performance metrics for each vector provider.
        
        Includes health, performance, and feature comparison.
        """
        try:
            if not memory_dashboard:
                raise HTTPException(status_code=503, detail="Dashboard not initialized")
            
            performance = await memory_dashboard.get_provider_performance()
            return {"providers": performance}
            
        except Exception as e:
            logger.error(f"Provider performance failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to get provider performance")
    
    @app.get("/dashboard/insights")
    async def get_memory_insights(limit: int = 50):
        """
        Get insights about memory patterns and usage.
        
        Identifies trends, patterns, and optimization opportunities.
        """
        try:
            if not memory_dashboard:
                raise HTTPException(status_code=503, detail="Dashboard not initialized")
            
            insights = await memory_dashboard.get_memory_insights(limit=limit)
            return insights
            
        except Exception as e:
            logger.error(f"Memory insights failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to get memory insights")
    
    # =============================================================================
    # ADM SCORING AND INTELLIGENCE ENDPOINTS
    # =============================================================================
    
    @app.get("/adm/performance")
    async def get_adm_performance(store: UnifiedVectorStore = Depends(get_store)):
        """
        Get ADM scoring engine performance metrics.
        
        Shows how well the automated decision making is performing.
        """
        try:
            if not memory_dashboard:
                raise HTTPException(status_code=503, detail="Dashboard not initialized")
            
            adm_perf = await memory_dashboard.get_adm_performance()
            return adm_perf
            
        except Exception as e:
            logger.error(f"ADM performance failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to get ADM performance")
    
    @app.post("/adm/analyze")
    async def analyze_content_adm(
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        store: UnifiedVectorStore = Depends(get_store)
    ):
        """
        Analyze content using ADM scoring without storing.
        
        Provides detailed breakdown of data quality, relevance, and intelligence.
        """
        try:
            if not store.adm_enabled or not store.adm_engine:
                raise HTTPException(status_code=400, detail="ADM scoring not enabled")
            
            analysis = await store.adm_engine.calculate_adm_score(
                content=content,
                metadata=metadata or {}
            )
            
            return {
                "analysis": analysis,
                "recommendations": {
                    "store_recommended": analysis["adm_score"] > 0.5,
                    "importance_level": "high" if analysis["adm_score"] > 0.7 else "medium" if analysis["adm_score"] > 0.4 else "low",
                    "quality_notes": {
                        "data_quality": "excellent" if analysis["data_quality"] > 0.8 else "good" if analysis["data_quality"] > 0.6 else "needs_improvement",
                        "data_relevance": "high" if analysis["data_relevance"] > 0.8 else "medium" if analysis["data_relevance"] > 0.6 else "low",
                        "data_intelligence": "high" if analysis["data_intelligence"] > 0.8 else "medium" if analysis["data_intelligence"] > 0.6 else "low"
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"ADM analysis failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to analyze content")
    
    @app.post("/adm/suggest-evolution/{memory_id}")
    async def suggest_memory_evolution(
        memory_id: str,
        store: UnifiedVectorStore = Depends(get_store)
    ):
        """
        Suggest evolution strategy for a specific memory.
        
        Uses Darwin-Gödel principles to recommend memory lifecycle actions.
        """
        try:
            if not store.adm_enabled or not store.adm_engine:
                raise HTTPException(status_code=400, detail="ADM scoring not enabled")
            
            # TODO: Get memory by ID from providers
            # For now, return mock suggestion
            from .adm import EvolutionStrategy
            
            strategy, confidence = await store.adm_engine.suggest_evolution_strategy(
                memory=None  # TODO: Implement memory retrieval by ID
            )
            
            return {
                "memory_id": memory_id,
                "suggested_strategy": strategy.value,
                "confidence_score": confidence,
                "reasoning": f"Based on ADM analysis, {strategy.value} is recommended with {confidence:.1%} confidence",
                "next_steps": {
                    "reinforcement": "Increase importance score and access frequency",
                    "diversification": "Explore related topics and expand context",
                    "consolidation": "Merge with similar high-value memories",
                    "pruning": "Consider archival or removal due to low value"
                }.get(strategy.value, "Monitor and maintain current state")
            }
            
        except Exception as e:
            logger.error(f"Evolution suggestion failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to suggest evolution")
    
    # =============================================================================
    # USAGE TRACKING AND ANALYTICS ENDPOINTS
    # =============================================================================
    
    @app.get("/analytics/usage")
    async def get_usage_analytics():
        """
        Get comprehensive usage analytics and patterns.
        
        Provides insights into system performance and user behavior.
        """
        try:
            if not usage_collector:
                raise HTTPException(status_code=503, detail="Usage tracking not initialized")
            
            performance_metrics = usage_collector.get_performance_metrics()
            usage_patterns = usage_collector.get_usage_patterns()
            
            return {
                "performance": {
                    "total_requests": performance_metrics.total_requests,
                    "avg_response_time_ms": performance_metrics.avg_response_time_ms,
                    "p95_response_time_ms": performance_metrics.p95_response_time_ms,
                    "p99_response_time_ms": performance_metrics.p99_response_time_ms,
                    "error_rate": performance_metrics.error_rate,
                    "requests_per_minute": performance_metrics.requests_per_minute,
                    "memory_operations_per_minute": performance_metrics.memory_operations_per_minute,
                    "unique_users_last_hour": performance_metrics.unique_users_last_hour
                },
                "patterns": usage_patterns
            }
            
        except Exception as e:
            logger.error(f"Usage analytics failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to get usage analytics")
    
    @app.get("/analytics/export")
    async def export_analytics(format: str = "json", limit: Optional[int] = None):
        """
        Export usage events and analytics data.
        
        Supports JSON and CSV formats for external analysis.
        """
        try:
            if not usage_collector:
                raise HTTPException(status_code=503, detail="Usage tracking not initialized")
            
            if not memory_dashboard:
                raise HTTPException(status_code=503, detail="Dashboard not initialized")
            
            # Export comprehensive data
            if format.lower() == "comprehensive":
                export_data = await memory_dashboard.export_metrics(format="json")
                return JSONResponse(
                    content={"data": export_data},
                    headers={"Content-Disposition": "attachment; filename=memory_service_export.json"}
                )
            else:
                # Export usage events
                events_data = usage_collector.export_events(format=format, limit=limit)
                
                if format.lower() == "json":
                    return JSONResponse(
                        content={"events": events_data},
                        headers={"Content-Disposition": "attachment; filename=usage_events.json"}
                    )
                else:
                    return Response(
                        content=events_data,
                        media_type="text/csv",
                        headers={"Content-Disposition": "attachment; filename=usage_events.csv"}
                    )
            
        except Exception as e:
            logger.error(f"Analytics export failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to export analytics")
    
    @app.post("/analytics/feedback")
    async def record_feedback(
        memory_id: str,
        useful: bool,
        feedback_type: str = "general",
        notes: Optional[str] = None,
        store: UnifiedVectorStore = Depends(get_store)
    ):
        """
        Record user feedback on memory usefulness.
        
        This feeds the evolution engine for continuous improvement.
        """
        try:
            # Create feedback memory for system learning
            feedback_content = f"FEEDBACK: Memory {memory_id} marked as {'useful' if useful else 'not useful'}"
            if notes:
                feedback_content += f" - Notes: {notes}"
            
            feedback_memory = MemoryRequest(
                content=feedback_content,
                metadata={
                    "type": "user_feedback",
                    "target_memory_id": memory_id,
                    "useful": useful,
                    "feedback_type": feedback_type,
                    "notes": notes,
                    "user_id": "system",
                    "conversation_id": "feedback_system",
                    "importance_score": 0.6  # Feedback is valuable for learning
                }
            )
            
            # Store feedback asynchronously
            asyncio.create_task(store.store_memory(feedback_memory))
            
            return {
                "message": "Feedback recorded successfully",
                "memory_id": memory_id,
                "useful": useful,
                "learning_impact": "This feedback will improve future memory scoring and evolution decisions"
            }
            
        except Exception as e:
            logger.error(f"Feedback recording failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to record feedback")
    
    # =====================================================
    # KNOWLEDGE GRAPH ENDPOINTS (Added by Agent 2)
    # =====================================================
    
    @app.post("/graph/sync/{memory_id}")
    async def sync_memory_to_graph(
        memory_id: str,
        store: UnifiedVectorStore = Depends(get_store)
    ):
        """
        Sync a specific memory to the knowledge graph.
        
        Extracts entities and relationships from an existing memory.
        """
        try:
            # Check if graph provider is available
            graph_provider = store.providers.get('graph')
            if not graph_provider or not graph_provider.enabled:
                raise HTTPException(status_code=503, detail="Graph provider not available")
            
            # TODO: Fetch memory from vector store and process
            # For now, return a placeholder
            return {
                "status": "success",
                "memory_id": memory_id,
                "message": "Memory synced to graph (placeholder)"
            }
            
        except Exception as e:
            logger.error(f"Graph sync failed: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to sync memory: {str(e)}")
    
    @app.get("/graph/explore/{entity_name}")
    async def explore_entity_relationships(
        entity_name: str,
        max_depth: int = 2,
        limit: int = 20,
        store: UnifiedVectorStore = Depends(get_store)
    ):
        """
        Explore relationships from a specific entity.
        
        Returns connected entities and their relationships up to max_depth.
        """
        try:
            graph_provider = store.providers.get('graph')
            if not graph_provider or not graph_provider.enabled:
                raise HTTPException(status_code=503, detail="Graph provider not available")
            
            # Query memories filtered by entity
            filters = {"entity_name": entity_name}
            memories = await graph_provider.query([], limit, filters)
            
            return {
                "entity": entity_name,
                "max_depth": max_depth,
                "memories_found": len(memories),
                "memories": [
                    {
                        "id": str(mem.id),
                        "content": mem.content[:200] + "..." if len(mem.content) > 200 else mem.content,
                        "importance": mem.importance_score,
                        "similarity": mem.similarity_score
                    }
                    for mem in memories
                ]
            }
            
        except Exception as e:
            logger.error(f"Entity exploration failed: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to explore entity: {str(e)}")
    
    @app.get("/graph/path/{from_entity}/{to_entity}")
    async def find_entity_path(
        from_entity: str,
        to_entity: str,
        max_depth: int = 3,
        store: UnifiedVectorStore = Depends(get_store)
    ):
        """
        Find the shortest path between two entities in the knowledge graph.
        
        Uses graph traversal to find connections.
        """
        try:
            graph_provider = store.providers.get('graph')
            if not graph_provider or not graph_provider.enabled:
                raise HTTPException(status_code=503, detail="Graph provider not available")
            
            # TODO: Implement actual path finding
            return {
                "from": from_entity,
                "to": to_entity,
                "path_found": False,
                "message": "Path finding not yet implemented"
            }
            
        except Exception as e:
            logger.error(f"Path finding failed: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to find path: {str(e)}")
    
    @app.get("/graph/insights/{memory_id}")
    async def get_memory_graph_insights(
        memory_id: str,
        store: UnifiedVectorStore = Depends(get_store)
    ):
        """
        Get graph-based insights for a specific memory.
        
        Shows entities extracted and their relationships.
        """
        try:
            graph_provider = store.providers.get('graph')
            if not graph_provider or not graph_provider.enabled:
                raise HTTPException(status_code=503, detail="Graph provider not available")
            
            # TODO: Implement actual insights gathering
            # For now, return mock data
            return {
                "memory_id": memory_id,
                "entity": {
                    "id": memory_id,
                    "entity_type": "concept",
                    "entity_name": "placeholder",
                    "properties": {},
                    "importance_score": 0.5
                },
                "memory_count": 1,
                "relationship_count": 0,
                "top_relationships": [],
                "co_occurring_entities": []
            }
            
        except Exception as e:
            logger.error(f"Graph insights failed: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get insights: {str(e)}")
    
    @app.post("/graph/bulk-sync")
    async def bulk_sync_memories_to_graph(
        memory_ids: List[str],
        store: UnifiedVectorStore = Depends(get_store)
    ):
        """
        Sync multiple memories to the knowledge graph in bulk.
        
        Efficient batch processing for initial graph population.
        """
        try:
            graph_provider = store.providers.get('graph')
            if not graph_provider or not graph_provider.enabled:
                raise HTTPException(status_code=503, detail="Graph provider not available")
            
            # TODO: Implement bulk sync
            return {
                "status": "success",
                "memories_processed": len(memory_ids),
                "message": "Bulk sync initiated (placeholder)"
            }
            
        except Exception as e:
            logger.error(f"Bulk sync failed: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to bulk sync: {str(e)}")
    
    @app.get("/graph/stats")
    async def get_graph_statistics(store: UnifiedVectorStore = Depends(get_store)):
        """
        Get comprehensive knowledge graph statistics.
        
        Shows entity counts, relationship types, and graph health.
        """
        try:
            graph_provider = store.providers.get('graph')
            if not graph_provider or not graph_provider.enabled:
                raise HTTPException(status_code=503, detail="Graph provider not available")
            
            stats = await graph_provider.get_stats()
            health = await graph_provider.health_check()
            
            return {
                "health": health,
                "statistics": stats
            }
            
        except Exception as e:
            logger.error(f"Graph stats failed: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get graph stats: {str(e)}")
    
    @app.post("/graph/query")
    async def query_knowledge_graph(
        query: dict,
        store: UnifiedVectorStore = Depends(get_store)
    ):
        """
        Advanced graph query endpoint.
        
        Supports entity filtering, relationship traversal, and pattern matching.
        """
        try:
            graph_provider = store.providers.get('graph')
            if not graph_provider or not graph_provider.enabled:
                raise HTTPException(status_code=503, detail="Graph provider not available")
            
            # Convert query dict to filters for the provider
            filters = {}
            if query.get('entity_name'):
                filters['entity_name'] = query['entity_name']
            if query.get('entity_type'):
                filters['entity_type'] = query['entity_type']
            if query.get('relationship_type'):
                filters['relationship_type'] = query['relationship_type']
            
            # Execute query
            import time
            start_time = time.time()
            
            limit = query.get('limit', 10)
            memories = await graph_provider.query([], limit, filters)
            
            query_time = (time.time() - start_time) * 1000
            
            # TODO: Convert memories to graph nodes and relationships
            return {
                "nodes": [],
                "relationships": [],
                "query_time_ms": query_time,
                "total_nodes": 0,
                "total_relationships": 0
            }
            
        except Exception as e:
            logger.error(f"Graph query failed: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to query graph: {str(e)}")
    
    return app


# For running with uvicorn
app = create_memory_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "memory_service.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )