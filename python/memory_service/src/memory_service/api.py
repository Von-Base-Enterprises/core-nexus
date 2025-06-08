"""
FastAPI REST API for Unified Memory Service

Provides HTTP endpoints for the Core Nexus Long Term Memory Module,
wrapping the UnifiedVectorStore with proper error handling and validation.
"""

import asyncio
import logging
import time
import os
import sys
import json
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from prometheus_client import CONTENT_TYPE_LATEST
from prometheus_fastapi_instrumentator import Instrumentator

from .models import (
    MemoryRequest, MemoryResponse, QueryRequest, QueryResponse,
    HealthCheckResponse, MemoryStats, ProviderConfig
)
from .unified_store import UnifiedVectorStore
from .providers import PineconeProvider, ChromaProvider, PgVectorProvider
from .logging_config import setup_logging, get_logger
# Temporarily disable complex imports for stable deployment
# from .metrics import (
#     metrics_collector, get_metrics, record_request, time_request,
#     record_memory_operation, set_service_info
# )
# from .db_monitoring import get_database_health

# Setup logging with Papertrail support
setup_logging()
logger = get_logger("api")

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
        primary=False,  # Don't make primary unless it initializes successfully
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
        pgvector_config.primary = True  # Make primary if successful
        logger.info("PgVector provider initialized as primary")
    except Exception as e:
        logger.warning(f"PgVector provider failed to initialize: {e}")
        pgvector_config.enabled = False
    
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
        primary=True,  # Make primary by default
        config={
            "collection_name": "core_nexus_memories",
            "persist_directory": "./memory_service_chroma"
        }
    )
    try:
        chroma_provider = ChromaProvider(chroma_config)
        providers.append(chroma_provider)
        # If pgvector was successfully initialized, make it primary instead
        if any(p.name == "pgvector" and p.enabled for p in providers):
            chroma_config.primary = False
            logger.info("ChromaDB provider initialized as secondary (pgvector is primary)")
        else:
            logger.info("ChromaDB provider initialized as primary")
    except Exception as e:
        logger.error(f"ChromaDB provider failed to initialize: {e}")
    
    # Add Graph Provider for knowledge graph functionality - TEMPORARILY DISABLED
    # TODO: Re-enable once deployment is stable
    logger.info("Graph provider temporarily disabled for stable deployment")
    
    if not providers:
        raise RuntimeError("No vector providers could be initialized")
    
    # Ensure we have at least one enabled primary provider
    enabled_providers = [p for p in providers if p.enabled]
    if not enabled_providers:
        raise RuntimeError("No enabled vector providers available")
    
    # If no primary provider is enabled, make the first enabled one primary
    has_enabled_primary = any(p.enabled and p.config.primary for p in providers)
    if not has_enabled_primary:
        enabled_providers[0].config.primary = True
        logger.warning(f"No enabled primary provider found, setting {enabled_providers[0].name} as primary")
    
    # Initialize OpenAI embedding model
    embedding_model = None
    try:
        from .embedding_models import create_embedding_model
        
        # Check if OpenAI API key is available
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key and openai_api_key.strip():
            embedding_model = create_embedding_model(
                provider="openai",
                model="text-embedding-3-small",
                api_key=openai_api_key,
                max_retries=3,
                timeout=30.0
            )
            logger.info("Initialized OpenAI embedding model: text-embedding-3-small")
        else:
            embedding_model = create_embedding_model(provider="mock", dimension=1536)
            logger.warning("No OpenAI API key found, using mock embeddings")
            
    except Exception as e:
        logger.error(f"Failed to initialize embedding model: {e}")
        # Fallback to mock model
        from .embedding_models import MockEmbeddingModel
        embedding_model = MockEmbeddingModel(dimension=1536)
        logger.warning("Using mock embedding model as fallback")
    
    # Initialize unified store with ADM enabled and embedding model
    unified_store = UnifiedVectorStore(providers, embedding_model=embedding_model, adm_enabled=True)
    logger.info(f"Memory service started with {len(providers)} providers and {embedding_model.__class__.__name__}")
    
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
    
    @app.get("/debug/env")
    async def debug_environment():
        """Debug endpoint to check environment variables."""
        import os
        api_key = os.getenv("OPENAI_API_KEY", "NOT_SET")
        return {
            "openai_api_key_present": bool(api_key and api_key != "NOT_SET"),
            "api_key_length": len(api_key) if api_key != "NOT_SET" else 0,
            "api_key_starts_with": api_key[:7] if api_key != "NOT_SET" else "NOT_SET",
            "embedding_model_type": unified_store.embedding_model.__class__.__name__ if unified_store and unified_store.embedding_model else "None"
        }
    
    @app.get("/debug/logs")
    async def get_recent_logs(lines: int = 100):
        """
        Get recent application logs for debugging.
        
        Returns last N lines of logs with timestamps and levels.
        """
        try:
            import os
            from collections import deque
            from datetime import datetime
            
            # Create in-memory log buffer if not exists
            if not hasattr(app.state, 'log_buffer'):
                app.state.log_buffer = deque(maxlen=1000)
                
                # Set up log capture handler
                import logging
                
                class BufferHandler(logging.Handler):
                    def emit(self, record):
                        try:
                            log_entry = {
                                'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                                'level': record.levelname,
                                'logger': record.name,
                                'message': self.format(record),
                                'module': record.module,
                                'function': record.funcName,
                                'line': record.lineno
                            }
                            app.state.log_buffer.append(log_entry)
                        except Exception:
                            pass
                
                # Add handler to root logger
                buffer_handler = BufferHandler()
                buffer_handler.setLevel(logging.DEBUG)
                buffer_handler.setFormatter(logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                ))
                logging.getLogger().addHandler(buffer_handler)
                
                # Also add to our logger
                logger.addHandler(buffer_handler)
                
                # Log that we started capturing
                logger.info("Log capture initialized for debug endpoint")
            
            # Get requested number of recent logs
            recent_logs = list(app.state.log_buffer)[-lines:]
            
            # Add some system info
            system_info = {
                'python_version': sys.version,
                'service_uptime_seconds': time.time() - app.state.start_time if hasattr(app.state, 'start_time') else 0,
                'log_buffer_size': len(app.state.log_buffer),
                'providers_status': {
                    name: {
                        'enabled': provider.enabled,
                        'primary': provider == unified_store.primary_provider
                    }
                    for name, provider in unified_store.providers.items()
                } if unified_store else {},
                'embedding_model': unified_store.embedding_model.__class__.__name__ if unified_store and unified_store.embedding_model else None
            }
            
            return {
                'logs': recent_logs,
                'total_logs_captured': len(app.state.log_buffer),
                'logs_returned': len(recent_logs),
                'system_info': system_info
            }
            
        except Exception as e:
            logger.error(f"Failed to get logs: {e}")
            return {
                'error': str(e),
                'logs': [],
                'message': 'Log capture may not be initialized yet'
            }
    
    @app.get("/debug/startup-logs")
    async def get_startup_logs():
        """
        Get startup and initialization logs.
        
        Shows what happened during service initialization.
        """
        # Create a summary of startup state
        startup_info = {
            'service_status': 'running',
            'uptime_seconds': time.time() - app.state.start_time if hasattr(app.state, 'start_time') else 0,
            'providers': {},
            'embedding_model': None,
            'initialization_errors': []
        }
        
        # Check providers
        if unified_store:
            for name, provider in unified_store.providers.items():
                startup_info['providers'][name] = {
                    'enabled': provider.enabled,
                    'primary': provider == unified_store.primary_provider,
                    'status': 'active' if provider.enabled else 'disabled'
                }
            
            # Check embedding model
            if unified_store.embedding_model:
                startup_info['embedding_model'] = {
                    'type': unified_store.embedding_model.__class__.__name__,
                    'dimension': unified_store.embedding_model.dimension
                }
                
                # Check if it's OpenAI and why it might have failed
                if startup_info['embedding_model']['type'] == 'MockEmbeddingModel':
                    import os
                    api_key = os.getenv("OPENAI_API_KEY", "")
                    if not api_key:
                        startup_info['initialization_errors'].append(
                            "OPENAI_API_KEY environment variable not found"
                        )
                    elif api_key == "mock_key_for_demo":
                        startup_info['initialization_errors'].append(
                            "OPENAI_API_KEY is set to mock value from render.yaml"
                        )
        
        # Check for common issues
        if 'pgvector' in startup_info['providers'] and not startup_info['providers']['pgvector']['enabled']:
            startup_info['initialization_errors'].append(
                "PgVector provider failed to initialize - PostgreSQL connection refused"
            )
        
        return startup_info
    
    @app.get("/logs/stream")
    async def stream_logs(format: str = "json"):
        """
        Stream logs in real-time via Server-Sent Events (SSE).
        
        Formats:
        - json: JSON formatted logs
        - syslog: Syslog format (RFC3164) compatible with Papertrail
        - plain: Plain text logs
        
        Usage:
        - curl https://service.com/logs/stream
        - curl https://service.com/logs/stream?format=syslog
        """
        import queue
        import threading
        from datetime import datetime
        
        # Create queue for log streaming
        log_queue = queue.Queue(maxsize=100)
        
        # Custom handler to capture logs
        class StreamHandler(logging.Handler):
            def emit(self, record):
                try:
                    if format == "syslog":
                        # Syslog format: <priority>timestamp hostname app[pid]: message
                        priority = self._get_syslog_priority(record.levelno)
                        timestamp = datetime.fromtimestamp(record.created).strftime('%b %d %H:%M:%S')
                        hostname = os.getenv('RENDER_SERVICE_NAME', 'core-nexus-memory')
                        pid = os.getpid()
                        message = self.format(record)
                        log_line = f"<{priority}>{timestamp} {hostname} {record.name}[{pid}]: {message}\n"
                    elif format == "plain":
                        log_line = f"{self.format(record)}\n"
                    else:  # json
                        log_data = {
                            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                            'level': record.levelname,
                            'logger': record.name,
                            'message': self.format(record),
                            'module': record.module,
                            'function': record.funcName,
                            'line': record.lineno
                        }
                        log_line = f"data: {json.dumps(log_data)}\n\n"
                    
                    # Non-blocking put
                    log_queue.put_nowait(log_line)
                except queue.Full:
                    pass  # Drop log if queue is full
                except Exception:
                    pass
            
            def _get_syslog_priority(self, levelno):
                """Convert Python log level to syslog priority."""
                # Facility = 16 (local0), Severity based on level
                facility = 16
                if levelno >= 50:  # CRITICAL
                    severity = 2
                elif levelno >= 40:  # ERROR
                    severity = 3
                elif levelno >= 30:  # WARNING
                    severity = 4
                elif levelno >= 20:  # INFO
                    severity = 6
                else:  # DEBUG
                    severity = 7
                return facility * 8 + severity
        
        # Add handler to capture logs
        stream_handler = StreamHandler()
        stream_handler.setLevel(logging.DEBUG)
        stream_handler.setFormatter(logging.Formatter('%(message)s'))
        
        # Add to root logger and our logger
        root_logger = logging.getLogger()
        root_logger.addHandler(stream_handler)
        logger.addHandler(stream_handler)
        
        async def generate():
            """Generate log stream."""
            try:
                # Send initial connection message
                if format == "json":
                    yield f"data: {json.dumps({'connected': True, 'format': format})}\n\n"
                elif format == "syslog":
                    yield f"<134>{datetime.now().strftime('%b %d %H:%M:%S')} {os.getenv('RENDER_SERVICE_NAME', 'core-nexus')} logger[{os.getpid()}]: Log streaming connected\n"
                else:
                    yield "Log streaming connected\n"
                
                # Stream logs
                while True:
                    try:
                        # Get log with timeout
                        log_line = await asyncio.get_event_loop().run_in_executor(
                            None, log_queue.get, True, 1.0
                        )
                        yield log_line
                        
                        # Send keepalive every 30 seconds
                        if format == "json" and asyncio.get_event_loop().time() % 30 < 1:
                            yield f"data: {json.dumps({'keepalive': True})}\n\n"
                            
                    except queue.Empty:
                        # Send keepalive
                        if format == "json":
                            yield "\n"  # SSE keepalive
                        await asyncio.sleep(0.1)
                        
            finally:
                # Cleanup
                root_logger.removeHandler(stream_handler)
                logger.removeHandler(stream_handler)
        
        # Return appropriate response type
        if format == "json":
            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"  # Disable Nginx buffering
                }
            )
        else:
            return StreamingResponse(
                generate(),
                media_type="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
    
    @app.get("/logs/syslog")
    async def syslog_endpoint(request: Request):
        """
        Syslog endpoint information for external log aggregation.
        
        Returns connection details for setting up syslog forwarding.
        """
        return {
            "message": "To stream logs to an external syslog server like Papertrail:",
            "options": {
                "1_streaming_endpoint": {
                    "description": "Use our streaming endpoint",
                    "url": f"{request.url.scheme}://{request.url.netloc}/logs/stream?format=syslog",
                    "method": "GET",
                    "format": "RFC3164 syslog format"
                },
                "2_environment_config": {
                    "description": "Configure via environment variables",
                    "PAPERTRAIL_HOST": "logs.papertrailapp.com",
                    "PAPERTRAIL_PORT": "34949",
                    "note": "Logs will be automatically forwarded if these are set"
                },
                "3_render_integration": {
                    "description": "Add log drain in Render.com dashboard",
                    "format": "syslog+tls://logs.papertrailapp.com:34949",
                    "location": "Settings -> Log Streams"
                }
            },
            "current_config": {
                "papertrail_configured": bool(os.getenv("PAPERTRAIL_HOST")),
                "service_name": os.getenv("RENDER_SERVICE_NAME", "core-nexus-memory")
            }
        }
    
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
            
            # Add embedding model info
            embedding_info = {
                'model_type': store.embedding_model.__class__.__name__ if store.embedding_model else None,
                'dimension': store.embedding_model.dimension if store.embedding_model else None
            }
            
            # Add health check for embedding model if it's OpenAI
            if hasattr(store.embedding_model, 'health_check'):
                try:
                    embedding_health = await store.embedding_model.health_check()
                    embedding_info['health'] = embedding_health
                except Exception as e:
                    embedding_info['health'] = {'status': 'error', 'error': str(e)}
            
            return {
                'providers': provider_info,
                'primary_provider': store.primary_provider.name,
                'total_providers': len(store.providers),
                'embedding_model': embedding_info
            }
            
        except Exception as e:
            logger.error(f"Failed to list providers: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    @app.post("/embeddings/test")
    async def test_embedding(
        text: str,
        store: UnifiedVectorStore = Depends(get_store)
    ):
        """
        Test the embedding functionality with provided text.
        
        Useful for verifying OpenAI integration and debugging embedding issues.
        """
        try:
            if not store.embedding_model:
                raise HTTPException(status_code=503, detail="No embedding model configured")
            
            start_time = time.time()
            embedding = await store.embedding_model.embed_text(text)
            duration = (time.time() - start_time) * 1000
            
            return {
                'text': text,
                'embedding_dimension': len(embedding),
                'embedding_sample': embedding[:5],  # First 5 values for verification
                'model_type': store.embedding_model.__class__.__name__,
                'generation_time_ms': round(duration, 2),
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Embedding test failed: {e}")
            raise HTTPException(status_code=500, detail=f"Embedding test failed: {str(e)}")
    
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