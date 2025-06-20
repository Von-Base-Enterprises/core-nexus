"""
Optimization Integration Module

Provides seamless integration of the performance optimization engine
with the existing Core Nexus Memory Service.
"""

import asyncio
import logging
import os
from typing import Optional

from .config import config
from .unified_store import UnifiedVectorStore
from .optimized_unified_store import OptimizedUnifiedVectorStore, create_optimized_unified_store
from .providers import PgVectorProvider, ChromaProvider, PineconeProvider
from .models import ProviderConfig

logger = logging.getLogger(__name__)


class OptimizationManager:
    """Manages the integration of optimization features"""
    
    def __init__(self):
        self.optimization_enabled = os.getenv("OPTIMIZATION_ENABLED", "true").lower() == "true"
        self.store: Optional[UnifiedVectorStore] = None
        self._initialized = False
    
    async def create_vector_store(self, embedding_model=None) -> UnifiedVectorStore:
        """Create appropriate vector store based on optimization settings"""
        
        # Create providers
        providers = await self._create_providers()
        
        if self.optimization_enabled and providers:
            logger.info("Creating optimized unified vector store...")
            try:
                self.store = await create_optimized_unified_store(
                    providers=providers,
                    embedding_model=embedding_model,
                    adm_enabled=config.features.ADM_ENABLED
                )
                logger.info("✅ Optimized vector store created successfully")
            except Exception as e:
                logger.error(f"❌ Failed to create optimized store: {e}")
                logger.info("🔄 Falling back to standard unified store...")
                self.store = UnifiedVectorStore(
                    providers=providers,
                    embedding_model=embedding_model,
                    adm_enabled=config.features.ADM_ENABLED
                )
        else:
            logger.info("Creating standard unified vector store...")
            self.store = UnifiedVectorStore(
                providers=providers,
                embedding_model=embedding_model,
                adm_enabled=config.features.ADM_ENABLED
            )
        
        self._initialized = True
        return self.store
    
    async def _create_providers(self) -> list:
        """Create and configure vector providers"""
        providers = []
        
        # Create pgvector provider
        try:
            pgvector_config = ProviderConfig(
                name="pgvector",
                enabled=True,
                primary=config.providers.PRIMARY_PROVIDER == "pgvector",
                retry_count=3,
                config={
                    'host': config.database.HOST,
                    'port': config.database.PORT,
                    'database': config.database.DATABASE,
                    'user': config.database.USER,
                    'password': config.database.PASSWORD,
                    'table_name': config.database.TABLE_NAME,
                    'embedding_dim': config.database.VECTOR_DIMENSION
                }
            )
            
            pgvector_provider = PgVectorProvider(pgvector_config)
            providers.append(pgvector_provider)
            logger.info("✅ PgVector provider configured")
            
        except Exception as e:
            logger.error(f"❌ Failed to create PgVector provider: {e}")
        
        # Create ChromaDB provider if enabled
        if config.providers.CHROMADB_ENABLED:
            try:
                chromadb_config = ProviderConfig(
                    name="chromadb",
                    enabled=True,
                    primary=config.providers.PRIMARY_PROVIDER == "chromadb",
                    retry_count=2,
                    config={
                        'persist_directory': config.providers.CHROMADB_PERSIST_DIR,
                        'collection_name': config.providers.CHROMADB_COLLECTION
                    }
                )
                
                chromadb_provider = ChromaProvider(chromadb_config)
                providers.append(chromadb_provider)
                logger.info("✅ ChromaDB provider configured")
                
            except Exception as e:
                logger.error(f"❌ Failed to create ChromaDB provider: {e}")
        
        # Create Pinecone provider if enabled
        if config.providers.PINECONE_ENABLED and config.providers.PINECONE_API_KEY:
            try:
                pinecone_config = ProviderConfig(
                    name="pinecone",
                    enabled=False,  # Disabled until fully implemented
                    primary=config.providers.PRIMARY_PROVIDER == "pinecone",
                    retry_count=3,
                    config={
                        'api_key': config.providers.PINECONE_API_KEY,
                        'index_name': config.providers.PINECONE_INDEX_NAME,
                        'environment': config.providers.PINECONE_ENVIRONMENT
                    }
                )
                
                pinecone_provider = PineconeProvider(pinecone_config)
                providers.append(pinecone_provider)
                logger.info("✅ Pinecone provider configured (disabled)")
                
            except Exception as e:
                logger.error(f"❌ Failed to create Pinecone provider: {e}")
        
        if not providers:
            raise RuntimeError("No vector providers could be created")
        
        logger.info(f"Created {len(providers)} vector providers")
        return providers
    
    async def get_optimization_status(self) -> dict:
        """Get current optimization status"""
        status = {
            'optimization_enabled': self.optimization_enabled,
            'store_initialized': self._initialized,
            'store_type': type(self.store).__name__ if self.store else None,
            'features': {
                'query_optimization': False,
                'connection_pooling': False,
                'caching': False,
                'provider_intelligence': False,
                'vector_optimization': False,
                'analytics': False
            }
        }
        
        if isinstance(self.store, OptimizedUnifiedVectorStore):
            status['features'] = {
                'query_optimization': self.store._optimization_initialized,
                'connection_pooling': True,
                'caching': True,
                'provider_intelligence': True,
                'vector_optimization': True,
                'analytics': True
            }
            
            # Get optimization stats
            if self.store._optimization_initialized:
                status['optimization_stats'] = self.store.optimization_stats.copy()
        
        return status
    
    async def enable_optimization(self) -> bool:
        """Enable optimization features"""
        if not self.optimization_enabled:
            logger.info("Enabling optimization features...")
            self.optimization_enabled = True
            
            # Recreate store with optimization
            if self.store:
                embedding_model = getattr(self.store, 'embedding_model', None)
                await self.create_vector_store(embedding_model)
            
            return True
        
        return False
    
    async def disable_optimization(self) -> bool:
        """Disable optimization features"""
        if self.optimization_enabled:
            logger.info("Disabling optimization features...")
            self.optimization_enabled = False
            
            # Shutdown optimization components if they exist
            if isinstance(self.store, OptimizedUnifiedVectorStore):
                await self.store.shutdown_optimizations()
            
            return True
        
        return False
    
    async def get_performance_report(self) -> dict:
        """Get comprehensive performance report"""
        if not self.store:
            return {'error': 'Vector store not initialized'}
        
        try:
            # Get basic health check
            health = await self.store.health_check()
            
            # Get optimization-specific data if available
            if isinstance(self.store, OptimizedUnifiedVectorStore):
                dashboard = await self.store.get_performance_dashboard()
                recommendations = await self.store.get_optimization_recommendations()
                
                return {
                    'health': health,
                    'dashboard': dashboard,
                    'recommendations': recommendations,
                    'optimization_status': await self.get_optimization_status()
                }
            else:
                return {
                    'health': health,
                    'optimization_status': await self.get_optimization_status(),
                    'message': 'Optimization features not enabled'
                }
                
        except Exception as e:
            logger.error(f"Failed to generate performance report: {e}")
            return {'error': f'Failed to generate report: {str(e)}'}
    
    async def optimize_performance(self) -> dict:
        """Trigger manual performance optimization"""
        if isinstance(self.store, OptimizedUnifiedVectorStore):
            try:
                return await self.store.optimize_performance()
            except Exception as e:
                logger.error(f"Manual optimization failed: {e}")
                return {'error': str(e)}
        else:
            return {'error': 'Optimization features not available'}
    
    async def shutdown(self):
        """Shutdown optimization manager and cleanup"""
        if isinstance(self.store, OptimizedUnifiedVectorStore):
            await self.store.shutdown_optimizations()
        
        self._initialized = False
        logger.info("Optimization manager shut down")


# Global optimization manager instance
optimization_manager = OptimizationManager()


async def get_vector_store(embedding_model=None) -> UnifiedVectorStore:
    """Get the configured vector store (optimized or standard)"""
    if not optimization_manager._initialized:
        return await optimization_manager.create_vector_store(embedding_model)
    return optimization_manager.store


async def get_optimization_status() -> dict:
    """Get current optimization status"""
    return await optimization_manager.get_optimization_status()


async def get_performance_report() -> dict:
    """Get comprehensive performance report"""
    return await optimization_manager.get_performance_report()


async def optimize_performance() -> dict:
    """Trigger manual performance optimization"""
    return await optimization_manager.optimize_performance()


async def enable_optimization() -> bool:
    """Enable optimization features"""
    return await optimization_manager.enable_optimization()


async def disable_optimization() -> bool:
    """Disable optimization features"""
    return await optimization_manager.disable_optimization()


# Health check function for monitoring
async def health_check_optimization() -> dict:
    """Health check specifically for optimization components"""
    try:
        status = await get_optimization_status()
        
        if status['optimization_enabled'] and status['store_initialized']:
            # Test basic functionality
            test_results = {
                'cache_accessible': False,
                'analytics_running': False,
                'connection_manager_ready': False
            }
            
            # Test cache engine
            try:
                from .cache_engine import cache_engine
                stats = await cache_engine.get_comprehensive_stats()
                test_results['cache_accessible'] = True
            except Exception:
                pass
            
            # Test analytics engine
            try:
                from .analytics_engine import analytics_engine
                test_results['analytics_running'] = analytics_engine._is_running
            except Exception:
                pass
            
            # Test connection manager
            try:
                from .connection_manager import connection_manager
                test_results['connection_manager_ready'] = connection_manager._is_initialized
            except Exception:
                pass
            
            status['component_health'] = test_results
        
        return status
        
    except Exception as e:
        return {
            'error': str(e),
            'optimization_enabled': False,
            'healthy': False
        }