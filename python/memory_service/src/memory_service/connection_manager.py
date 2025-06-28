"""
Advanced Connection Manager for Core Nexus Memory Service

Optimizes database connections, prepared statements, and connection pooling
for high-performance operations with 1GB RAM PostgreSQL deployment.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import asyncpg

from .config import config

logger = logging.getLogger(__name__)


@dataclass
class ConnectionStats:
    """Connection performance statistics"""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    failed_connections: int = 0
    avg_connection_time_ms: float = 0.0
    total_queries: int = 0
    avg_query_time_ms: float = 0.0
    prepared_statements_count: int = 0
    cache_hit_rate: float = 0.0


class PreparedStatementCache:
    """Cache for prepared statements to improve query performance"""
    
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.cache: Dict[str, str] = {}  # query_hash -> statement_name
        self.usage_count: Dict[str, int] = {}
        self.last_used: Dict[str, float] = {}
    
    def get_statement_name(self, query_hash: str) -> Optional[str]:
        """Get cached prepared statement name"""
        if query_hash in self.cache:
            self.usage_count[query_hash] = self.usage_count.get(query_hash, 0) + 1
            self.last_used[query_hash] = time.time()
            return self.cache[query_hash]
        return None
    
    def add_statement(self, query_hash: str, statement_name: str):
        """Add prepared statement to cache"""
        # Evict oldest if cache is full
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
        
        self.cache[query_hash] = statement_name
        self.usage_count[query_hash] = 1
        self.last_used[query_hash] = time.time()
    
    def _evict_oldest(self):
        """Evict the least recently used statement"""
        if not self.cache:
            return
        
        oldest_key = min(self.last_used.keys(), key=lambda k: self.last_used[k])
        del self.cache[oldest_key]
        del self.usage_count[oldest_key]
        del self.last_used[oldest_key]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'cache_size': len(self.cache),
            'max_size': self.max_size,
            'total_usage': sum(self.usage_count.values()),
            'avg_usage_per_statement': sum(self.usage_count.values()) / len(self.cache) if self.cache else 0
        }


class ConnectionHealthMonitor:
    """Monitors connection health and performance"""
    
    def __init__(self):
        self.connection_metrics: Dict[str, List[float]] = {}
        self.failed_connections: int = 0
        self.total_connections: int = 0
        
    async def test_connection(self, connection: asyncpg.Connection) -> Tuple[bool, float]:
        """Test connection health and measure latency"""
        start_time = time.time()
        try:
            await connection.fetchval("SELECT 1")
            latency = (time.time() - start_time) * 1000
            self.total_connections += 1
            return True, latency
        except Exception as e:
            self.failed_connections += 1
            latency = (time.time() - start_time) * 1000
            logger.warning(f"Connection health check failed: {e}")
            return False, latency
    
    def get_health_score(self) -> float:
        """Get overall connection health score (0.0 to 1.0)"""
        if self.total_connections == 0:
            return 1.0
        
        success_rate = 1.0 - (self.failed_connections / self.total_connections)
        return max(0.0, min(1.0, success_rate))


class OptimizedConnectionPool:
    """
    High-performance connection pool optimized for 1GB RAM and vector operations
    """
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.prepared_cache = PreparedStatementCache(config.database.MAX_PREPARED_STATEMENTS)
        self.health_monitor = ConnectionHealthMonitor()
        self.stats = ConnectionStats()
        self._initialization_lock = asyncio.Lock()
        self._is_initialized = False
        
        # Detect environment type for appropriate optimizations
        self.is_managed_postgres = self._detect_managed_postgres()
        if self.is_managed_postgres:
            logger.info("Detected managed PostgreSQL environment - using compatible settings")
    
    def _detect_managed_postgres(self) -> bool:
        """Detect if running on managed PostgreSQL service"""
        # Check for managed PostgreSQL indicators
        host = config.database.HOST.lower()
        
        # Common managed PostgreSQL hostnames
        managed_indicators = [
            'render.com',           # Render.com managed PostgreSQL
            'amazonaws.com',        # AWS RDS
            'database.azure.com',   # Azure Database
            'googleusercontent.com', # Google Cloud SQL
            'heroku.com',           # Heroku Postgres
            'planetscale.com',      # PlanetScale
            'supabase.com',         # Supabase
            'neon.tech'             # Neon
        ]
        
        return any(indicator in host for indicator in managed_indicators)
        
    async def initialize(self) -> bool:
        """Initialize the connection pool with optimized settings"""
        async with self._initialization_lock:
            if self._is_initialized:
                return True
            
            try:
                environment_type = "managed PostgreSQL" if self.is_managed_postgres else "self-hosted PostgreSQL"
                logger.info(f"Initializing optimized connection pool for {environment_type}...")
                
                # Build connection string
                conn_str = (
                    f"postgresql://{config.database.USER}:{config.database.PASSWORD}@"
                    f"{config.database.HOST}:{config.database.PORT}/{config.database.DATABASE}"
                )
                
                # Get appropriate server settings based on environment
                server_settings = self._get_optimized_server_settings()
                
                # Initialize pool with optimized settings
                self.pool = await asyncpg.create_pool(
                    conn_str,
                    min_size=config.database.POOL_MIN_SIZE,
                    max_size=config.database.POOL_MAX_SIZE,
                    command_timeout=config.database.COMMAND_TIMEOUT,
                    init=self._init_connection_safe,
                    server_settings=server_settings
                )
                
                # Test pool connectivity
                async with self.pool.acquire() as conn:
                    is_healthy, latency = await self.health_monitor.test_connection(conn)
                    if not is_healthy:
                        raise RuntimeError("Initial connection health check failed")
                
                self._is_initialized = True
                logger.info(
                    f"Connection pool initialized successfully: "
                    f"{config.database.POOL_MIN_SIZE}-{config.database.POOL_MAX_SIZE} connections, "
                    f"initial latency: {latency:.1f}ms"
                )
                return True
                
            except Exception as e:
                logger.error(f"Failed to initialize connection pool: {e}")
                self._is_initialized = False
                return False
    
    async def _init_connection_safe(self, conn: asyncpg.Connection):
        """Initialize each connection with safe settings for managed PostgreSQL"""
        try:
            # Set search path
            await conn.execute("SET search_path TO public, pg_catalog")
            
            # Enable vector extension
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            
            # Register vector type
            try:
                from pgvector.asyncpg import register_vector
                await register_vector(conn)
                logger.debug("Vector type registered successfully")
            except ImportError:
                logger.warning("pgvector.asyncpg not available, using manual vector casting")
            except Exception as e:
                logger.warning(f"Vector type registration failed: {e}")
            
            # Apply session-level optimizations based on environment
            if self.is_managed_postgres:
                # Conservative settings for managed PostgreSQL
                await self._apply_managed_postgres_settings(conn)
            else:
                # Full optimizations for self-hosted PostgreSQL
                await self._apply_selfhosted_postgres_settings(conn)
            
            logger.debug(f"Connection {id(conn)} initialized with environment-appropriate settings")
            
        except Exception as e:
            logger.error(f"Failed to initialize connection: {e}")
            raise
    
    async def _apply_managed_postgres_settings(self, conn: asyncpg.Connection):
        """Apply conservative settings for managed PostgreSQL services"""
        applied_settings = []
        failed_settings = []
        
        # Conservative session-level parameters - apply individually with graceful degradation
        settings_to_try = [
            (f"SET work_mem = '{min(config.database.WORK_MEM_MB, 4)}MB'", "work_mem"),
            ("SET random_page_cost = 1.1", "random_page_cost"),
            ("SET seq_page_cost = 1.0", "seq_page_cost"),
            ("SET enable_hashjoin = on", "enable_hashjoin"),
            ("SET enable_mergejoin = on", "enable_mergejoin")
        ]
        
        for setting_sql, setting_name in settings_to_try:
            try:
                await conn.execute(setting_sql)
                applied_settings.append(setting_name)
            except Exception as e:
                failed_settings.append(f"{setting_name}: {str(e)}")
                logger.debug(f"Managed PostgreSQL setting failed: {setting_name} - {e}")
        
        logger.info(f"Managed PostgreSQL settings applied: {len(applied_settings)} successful, {len(failed_settings)} failed")
        if failed_settings:
            logger.debug(f"Failed managed PostgreSQL settings: {', '.join(failed_settings)}")
    
    async def _apply_selfhosted_postgres_settings(self, conn: asyncpg.Connection):
        """Apply full optimizations for self-hosted PostgreSQL"""
        try:
            # Full memory optimizations
            await conn.execute(f"SET work_mem = '{config.database.WORK_MEM_MB}MB'")
            await conn.execute(f"SET maintenance_work_mem = '{config.database.MAINTENANCE_WORK_MEM_MB}MB'")
            await conn.execute("SET random_page_cost = 1.1")  # Optimized for SSD
            await conn.execute("SET seq_page_cost = 1.0")
            await conn.execute("SET effective_io_concurrency = 200")  # High concurrency
            
            # Enable query optimization
            await conn.execute("SET enable_hashjoin = on")
            await conn.execute("SET enable_mergejoin = on")
            await conn.execute("SET enable_nestloop = off")  # Avoid nested loops for large datasets
            
            # Optimize for vector operations
            await conn.execute("SET max_parallel_workers_per_gather = 4")
            await conn.execute("SET parallel_setup_cost = 100")
            await conn.execute("SET parallel_tuple_cost = 0.1")
            
            logger.debug("Applied self-hosted PostgreSQL settings")
        except Exception as e:
            logger.warning(f"Some self-hosted PostgreSQL settings failed: {e}")
    
    
    def _get_optimized_server_settings(self) -> Dict[str, str]:
        """Get optimized server settings for the connection pool"""
        if self.is_managed_postgres:
            # No server settings for managed PostgreSQL - use defaults only
            logger.info("Using no server settings for managed PostgreSQL environment")
            return {}
        
        # Full server settings for self-hosted PostgreSQL
        return {
            'synchronous_commit': 'on',  # Ensure data consistency
            'log_statement': 'none',     # Reduce logging overhead
            'log_min_duration_statement': '1000',  # Only log slow queries
            'shared_preload_libraries': 'vector'   # Ensure vector extension is loaded
        }
    
    @asynccontextmanager
    async def acquire_connection(self):
        """Get a connection from the pool with automatic cleanup"""
        if not self._is_initialized:
            await self.initialize()
        
        if not self.pool:
            raise RuntimeError("Connection pool not initialized")
        
        start_time = time.time()
        connection = None
        
        try:
            connection = await self.pool.acquire()
            
            # Update connection stats
            connection_time = (time.time() - start_time) * 1000
            self.stats.total_connections += 1
            self.stats.active_connections += 1
            
            # Update moving average for connection time
            alpha = 0.1
            self.stats.avg_connection_time_ms = (
                (1 - alpha) * self.stats.avg_connection_time_ms + 
                alpha * connection_time
            )
            
            yield connection
            
        except Exception as e:
            self.stats.failed_connections += 1
            logger.error(f"Failed to acquire connection: {e}")
            raise
        finally:
            if connection:
                try:
                    await self.pool.release(connection)
                    self.stats.active_connections -= 1
                except Exception as e:
                    logger.error(f"Failed to release connection: {e}")
    
    async def execute_optimized_query(
        self, 
        query: str, 
        *args,
        use_prepared: bool = True,
        fetch_method: str = 'fetch'  # 'fetch', 'fetchval', 'fetchrow'
    ) -> Any:
        """Execute query with prepared statement optimization"""
        start_time = time.time()
        
        try:
            async with self.acquire_connection() as conn:
                # Use prepared statements if enabled and beneficial
                if use_prepared and config.database.ENABLE_PREPARED_STATEMENTS:
                    result = await self._execute_prepared_query(
                        conn, query, args, fetch_method
                    )
                else:
                    # Execute directly
                    if fetch_method == 'fetch':
                        result = await conn.fetch(query, *args)
                    elif fetch_method == 'fetchval':
                        result = await conn.fetchval(query, *args)
                    elif fetch_method == 'fetchrow':
                        result = await conn.fetchrow(query, *args)
                    else:
                        result = await conn.execute(query, *args)
                
                # Update query stats
                query_time = (time.time() - start_time) * 1000
                self.stats.total_queries += 1
                
                # Update moving average for query time
                alpha = 0.1
                self.stats.avg_query_time_ms = (
                    (1 - alpha) * self.stats.avg_query_time_ms + 
                    alpha * query_time
                )
                
                return result
                
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    async def _execute_prepared_query(
        self, 
        conn: asyncpg.Connection, 
        query: str, 
        args: Tuple,
        fetch_method: str
    ) -> Any:
        """Execute query using prepared statements"""
        # Generate query hash for caching
        query_hash = f"{hash(query)}_{len(args)}"
        
        # Check if we have a prepared statement
        statement_name = self.prepared_cache.get_statement_name(query_hash)
        
        if statement_name:
            # Use existing prepared statement
            try:
                if fetch_method == 'fetch':
                    return await conn.fetch(f"EXECUTE {statement_name}($1, $2, $3, $4, $5)", *args[:5])
                elif fetch_method == 'fetchval':
                    return await conn.fetchval(f"EXECUTE {statement_name}($1, $2, $3, $4, $5)", *args[:5])
                elif fetch_method == 'fetchrow':
                    return await conn.fetchrow(f"EXECUTE {statement_name}($1, $2, $3, $4, $5)", *args[:5])
                else:
                    return await conn.execute(f"EXECUTE {statement_name}($1, $2, $3, $4, $5)", *args[:5])
            except Exception:
                # Prepared statement might be invalid, fall back to direct execution
                pass
        
        # Create new prepared statement
        statement_name = f"stmt_{uuid4().hex[:8]}"
        
        try:
            await conn.execute(f"PREPARE {statement_name} AS {query}")
            self.prepared_cache.add_statement(query_hash, statement_name)
            self.stats.prepared_statements_count += 1
            
            # Execute the prepared statement
            if fetch_method == 'fetch':
                return await conn.fetch(f"EXECUTE {statement_name}", *args)
            elif fetch_method == 'fetchval':
                return await conn.fetchval(f"EXECUTE {statement_name}", *args)
            elif fetch_method == 'fetchrow':
                return await conn.fetchrow(f"EXECUTE {statement_name}", *args)
            else:
                return await conn.execute(f"EXECUTE {statement_name}", *args)
                
        except Exception as e:
            logger.warning(f"Failed to create prepared statement: {e}")
            # Fall back to direct execution
            if fetch_method == 'fetch':
                return await conn.fetch(query, *args)
            elif fetch_method == 'fetchval':
                return await conn.fetchval(query, *args)
            elif fetch_method == 'fetchrow':
                return await conn.fetchrow(query, *args)
            else:
                return await conn.execute(query, *args)
    
    async def execute_batch_optimized(
        self, 
        queries: List[Tuple[str, Tuple]], 
        batch_size: int = 100
    ) -> List[Any]:
        """Execute multiple queries in optimized batches"""
        results = []
        
        async with self.acquire_connection() as conn:
            # Execute in batches to optimize memory usage
            for i in range(0, len(queries), batch_size):
                batch = queries[i:i + batch_size]
                
                # Use transaction for batch
                async with conn.transaction():
                    for query, args in batch:
                        try:
                            result = await conn.fetch(query, *args)
                            results.append(result)
                        except Exception as e:
                            logger.error(f"Batch query failed: {e}")
                            results.append([])  # Empty result for failed query
        
        return results
    
    async def optimize_indexes(self) -> Dict[str, Any]:
        """Optimize vector indexes for better performance"""
        optimization_results = {}
        
        try:
            async with self.acquire_connection() as conn:
                logger.info("Starting index optimization for 1GB RAM...")
                
                # Check current HNSW indexes
                existing_indexes = await conn.fetch("""
                    SELECT indexname, indexdef 
                    FROM pg_indexes 
                    WHERE tablename = $1 AND indexdef LIKE '%hnsw%'
                """, config.database.TABLE_NAME)
                
                optimization_results['existing_indexes'] = len(existing_indexes)
                
                # Drop old indexes if they don't match our optimized parameters
                for index in existing_indexes:
                    if 'm=16' in index['indexdef'] or 'ef_construction=64' in index['indexdef']:
                        logger.info(f"Dropping suboptimal index: {index['indexname']}")
                        await conn.execute(f"DROP INDEX IF EXISTS {index['indexname']}")
                
                # Create optimized HNSW index
                optimized_index_name = f"idx_{config.database.TABLE_NAME}_embedding_hnsw_optimized"
                
                create_index_sql = f"""
                    CREATE INDEX IF NOT EXISTS {optimized_index_name}
                    ON {config.database.TABLE_NAME} 
                    USING hnsw (embedding vector_cosine_ops) 
                    WITH (m = {config.database.HNSW_M}, ef_construction = {config.database.HNSW_EF_CONSTRUCTION})
                """
                
                logger.info(f"Creating optimized HNSW index with m={config.database.HNSW_M}, ef_construction={config.database.HNSW_EF_CONSTRUCTION}")
                start_time = time.time()
                await conn.execute(create_index_sql)
                index_creation_time = time.time() - start_time
                
                optimization_results['new_index_created'] = True
                optimization_results['index_creation_time_seconds'] = index_creation_time
                
                # Update table statistics
                await conn.execute(f"ANALYZE {config.database.TABLE_NAME}")
                optimization_results['table_analyzed'] = True
                
                logger.info(f"Index optimization completed in {index_creation_time:.1f} seconds")
                
        except Exception as e:
            logger.error(f"Index optimization failed: {e}")
            optimization_results['error'] = str(e)
        
        return optimization_results
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive connection pool performance statistics"""
        pool_stats = {}
        
        if self.pool:
            pool_stats = {
                'pool_size': self.pool.get_size(),
                'pool_min_size': self.pool.get_min_size(),
                'pool_max_size': self.pool.get_max_size(),
                'idle_connections': self.pool.get_idle_size(),
            }
        
        return {
            'connection_stats': {
                'total_connections': self.stats.total_connections,
                'active_connections': self.stats.active_connections,
                'failed_connections': self.stats.failed_connections,
                'avg_connection_time_ms': self.stats.avg_connection_time_ms,
                'health_score': self.health_monitor.get_health_score()
            },
            'query_stats': {
                'total_queries': self.stats.total_queries,
                'avg_query_time_ms': self.stats.avg_query_time_ms,
                'prepared_statements_count': self.stats.prepared_statements_count
            },
            'pool_stats': pool_stats,
            'prepared_statement_cache': self.prepared_cache.get_stats()
        }
    
    async def close(self):
        """Clean up connection pool"""
        if self.pool:
            await self.pool.close()
            self._is_initialized = False
            logger.info("Connection pool closed")


# Singleton instance
connection_manager = OptimizedConnectionPool()