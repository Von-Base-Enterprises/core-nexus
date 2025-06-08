"""
Database monitoring and telemetry for Core Nexus Memory Service
"""

import asyncio
import asyncpg
import logging
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from .metrics import update_db_pool_metrics, time_db_query

logger = logging.getLogger(__name__)

@dataclass
class SlowQuery:
    """Represents a slow database query"""
    query: str
    total_time: float
    calls: int
    mean_time: float
    max_time: float
    stddev_time: float

@dataclass
class PoolStats:
    """Database connection pool statistics"""
    size: int
    used: int
    free: int
    waiting: int
    max_size: int

class DatabaseMonitor:
    """
    Monitors PostgreSQL database performance and connection pool health
    """
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.pool: Optional[asyncpg.Pool] = None
        self._monitoring_enabled = False
        
    async def initialize_pool(self, min_size: int = 5, max_size: int = 20) -> asyncpg.Pool:
        """Initialize connection pool with monitoring"""
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=min_size,
                max_size=max_size,
                command_timeout=30,
                server_settings={
                    'application_name': 'core_nexus_memory_service',
                    'shared_preload_libraries': 'pg_stat_statements'
                }
            )
            
            # Enable pg_stat_statements if available
            await self._enable_query_monitoring()
            logger.info(f"Database pool initialized: {min_size}-{max_size} connections")
            return self.pool
            
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    async def _enable_query_monitoring(self):
        """Enable pg_stat_statements for query monitoring"""
        try:
            async with self.pool.acquire() as conn:
                # Check if pg_stat_statements is available
                result = await conn.fetchval(
                    "SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'"
                )
                
                if result:
                    # Reset statistics to start fresh
                    await conn.execute("SELECT pg_stat_statements_reset()")
                    self._monitoring_enabled = True
                    logger.info("pg_stat_statements monitoring enabled")
                else:
                    logger.warning("pg_stat_statements extension not available")
                    
        except Exception as e:
            logger.warning(f"Could not enable query monitoring: {e}")
    
    async def get_pool_stats(self) -> PoolStats:
        """Get current connection pool statistics"""
        if not self.pool:
            return PoolStats(0, 0, 0, 0, 0)
        
        try:
            # Get pool statistics
            size = self.pool.get_size()
            used = size - self.pool.get_idle_size()
            free = self.pool.get_idle_size()
            max_size = self.pool.get_max_size()
            
            # Update Prometheus metrics
            update_db_pool_metrics(size, used)
            
            return PoolStats(
                size=size,
                used=used,
                free=free,
                waiting=0,  # asyncpg doesn't expose waiting connections
                max_size=max_size
            )
            
        except Exception as e:
            logger.error(f"Error getting pool stats: {e}")
            return PoolStats(0, 0, 0, 0, 0)
    
    async def get_slow_queries(self, limit: int = 10) -> List[SlowQuery]:
        """Get slowest queries from pg_stat_statements"""
        if not self.pool or not self._monitoring_enabled:
            return []
        
        try:
            async with self.pool.acquire() as conn:
                query = """
                SELECT 
                    query,
                    total_exec_time as total_time,
                    calls,
                    mean_exec_time as mean_time,
                    max_exec_time as max_time,
                    stddev_exec_time as stddev_time
                FROM pg_stat_statements 
                WHERE query NOT LIKE '%pg_stat_statements%'
                  AND query NOT LIKE '%pg_database%'
                ORDER BY total_exec_time DESC 
                LIMIT $1
                """
                
                rows = await conn.fetch(query, limit)
                
                slow_queries = []
                for row in rows:
                    slow_queries.append(SlowQuery(
                        query=row['query'][:200] + "..." if len(row['query']) > 200 else row['query'],
                        total_time=float(row['total_time']),
                        calls=int(row['calls']),
                        mean_time=float(row['mean_time']),
                        max_time=float(row['max_time']),
                        stddev_time=float(row['stddev_time'])
                    ))
                
                return slow_queries
                
        except Exception as e:
            logger.error(f"Error getting slow queries: {e}")
            return []
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        if not self.pool:
            return {}
        
        try:
            async with self.pool.acquire() as conn:
                # Get basic database info
                db_info = await conn.fetchrow("""
                    SELECT 
                        datname,
                        numbackends,
                        xact_commit,
                        xact_rollback,
                        blks_read,
                        blks_hit,
                        tup_returned,
                        tup_fetched,
                        tup_inserted,
                        tup_updated,
                        tup_deleted
                    FROM pg_stat_database 
                    WHERE datname = current_database()
                """)
                
                # Get active connections
                active_connections = await conn.fetchval("""
                    SELECT count(*) 
                    FROM pg_stat_activity 
                    WHERE state = 'active' 
                      AND datname = current_database()
                """)
                
                # Get cache hit ratio
                cache_hit_ratio = 0
                if db_info['blks_read'] + db_info['blks_hit'] > 0:
                    cache_hit_ratio = db_info['blks_hit'] / (db_info['blks_read'] + db_info['blks_hit'])
                
                return {
                    "database_name": db_info['datname'],
                    "active_connections": active_connections,
                    "total_connections": db_info['numbackends'],
                    "transactions": {
                        "commits": db_info['xact_commit'],
                        "rollbacks": db_info['xact_rollback']
                    },
                    "cache_hit_ratio": cache_hit_ratio,
                    "tuples": {
                        "returned": db_info['tup_returned'],
                        "fetched": db_info['tup_fetched'],
                        "inserted": db_info['tup_inserted'],
                        "updated": db_info['tup_updated'],
                        "deleted": db_info['tup_deleted']
                    }
                }
                
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}
    
    @time_db_query("vector_search")
    async def execute_vector_query(self, query: str, *args) -> List[Dict]:
        """Execute a vector search query with timing"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
    
    @time_db_query("memory_insert")
    async def execute_memory_insert(self, query: str, *args) -> str:
        """Execute a memory insert query with timing"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)
    
    @time_db_query("general")
    async def execute_query(self, query: str, *args) -> Any:
        """Execute a general query with timing"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def close(self):
        """Close the connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Database pool closed")

# Global database monitor instance
db_monitor: Optional[DatabaseMonitor] = None

def get_db_monitor() -> Optional[DatabaseMonitor]:
    """Get the global database monitor instance"""
    return db_monitor

def initialize_db_monitor(connection_string: str) -> DatabaseMonitor:
    """Initialize the global database monitor"""
    global db_monitor
    db_monitor = DatabaseMonitor(connection_string)
    return db_monitor

async def get_database_health() -> Dict[str, Any]:
    """Get database health status for API endpoint"""
    if not db_monitor or not db_monitor.pool:
        return {
            "status": "disconnected",
            "error": "Database monitor not initialized"
        }
    
    try:
        # Test connection
        async with db_monitor.pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        
        # Get statistics
        pool_stats = await db_monitor.get_pool_stats()
        db_stats = await db_monitor.get_database_stats()
        slow_queries = await db_monitor.get_slow_queries(5)
        
        return {
            "status": "healthy",
            "pool": {
                "size": pool_stats.size,
                "used": pool_stats.used,
                "free": pool_stats.free,
                "max_size": pool_stats.max_size,
                "utilization": pool_stats.used / pool_stats.max_size if pool_stats.max_size > 0 else 0
            },
            "database": db_stats,
            "slow_queries": [
                {
                    "query": sq.query,
                    "total_time_ms": sq.total_time,
                    "calls": sq.calls,
                    "avg_time_ms": sq.mean_time
                }
                for sq in slow_queries
            ]
        }
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }