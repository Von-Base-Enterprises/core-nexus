"""
Temporal Memory Store

Leverages existing PostgreSQL partitioning strategy from conversation_history
to provide time-based memory queries with high performance.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

import asyncpg

from .models import MemoryResponse, TemporalQuery
from .unified_store import UnifiedVectorStore

logger = logging.getLogger(__name__)


class TemporalMemoryStore:
    """
    Temporal memory queries leveraging existing PostgreSQL partitioning.
    
    Integrates with the existing conversation_history partition strategy
    while providing vector similarity search across time ranges.
    """

    def __init__(self, unified_store: UnifiedVectorStore, db_config: dict[str, Any]):
        self.unified_store = unified_store
        self.db_config = db_config
        self.connection_pool: asyncpg.Pool | None = None

    async def initialize(self):
        """Initialize database connection pool."""
        try:
            self.connection_pool = await asyncpg.create_pool(
                host=self.db_config.get('host', 'localhost'),
                port=self.db_config.get('port', 5432),
                user=self.db_config.get('user', 'postgres'),
                password=self.db_config.get('password'),
                database=self.db_config.get('database', 'postgres'),
                min_size=2,
                max_size=10
            )
            logger.info("Temporal memory store initialized")

        except Exception as e:
            logger.error(f"Failed to initialize temporal store: {e}")
            raise

    async def query_temporal_memories(self, query: TemporalQuery) -> list[MemoryResponse]:
        """
        Query memories within a specific time range using partition optimization.
        
        Combines PostgreSQL temporal queries with vector similarity search.
        """
        if not self.connection_pool:
            raise RuntimeError("Temporal store not initialized")

        try:
            # Step 1: Get conversation IDs from the time range using existing partitions
            conversation_ids = await self._get_conversations_in_range(
                query.start_time,
                query.end_time
            )

            if not conversation_ids:
                logger.info(f"No conversations found in time range {query.start_time} to {query.end_time}")
                return []

            # Step 2: Query vector store with conversation filter
            vector_query = {
                'query': query.query,
                'limit': query.limit * 2,  # Get more to account for time filtering
                'filters': {
                    'conversation_ids': conversation_ids,
                    'start_time': query.start_time.timestamp(),
                    'end_time': query.end_time.timestamp()
                }
            }

            # Use existing unified vector store
            from .models import QueryRequest
            request = QueryRequest(**vector_query)
            response = await self.unified_store.query_memories(request)

            # Step 3: Apply temporal filtering and ranking
            temporal_memories = self._rank_temporal_relevance(
                response.memories,
                query
            )

            logger.info(f"Temporal query returned {len(temporal_memories)} memories")
            return temporal_memories[:query.limit]

        except Exception as e:
            logger.error(f"Temporal query failed: {e}")
            raise

    async def _get_conversations_in_range(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> list[str]:
        """
        Get conversation IDs from time range using existing partition strategy.
        
        Leverages the existing conversation_history partitioning for efficiency.
        """
        async with self.connection_pool.acquire() as conn:
            # Query existing conversation_history partitions
            # This leverages the existing PostgreSQL partitioning strategy
            query = """
            SELECT DISTINCT conversation_id 
            FROM conversation_history 
            WHERE created_at >= $1 AND created_at <= $2
            ORDER BY created_at DESC
            LIMIT 1000
            """

            rows = await conn.fetch(query, start_time, end_time)
            conversation_ids = [row['conversation_id'] for row in rows]

            logger.debug(f"Found {len(conversation_ids)} conversations in time range")
            return conversation_ids

    def _rank_temporal_relevance(
        self,
        memories: list[MemoryResponse],
        query: TemporalQuery
    ) -> list[MemoryResponse]:
        """
        Rank memories by temporal relevance combined with semantic similarity.
        
        Applies time-decay weighting to balance recency with relevance.
        """
        now = datetime.utcnow()
        query_duration = (query.end_time - query.start_time).total_seconds()

        for memory in memories:
            # Calculate time-based relevance
            memory_age = (now - memory.created_at).total_seconds()
            time_weight = max(0.1, 1.0 - (memory_age / (30 * 24 * 3600)))  # 30-day decay

            # Combine similarity with temporal relevance
            semantic_score = memory.similarity_score or 0.0
            temporal_score = time_weight * 0.3 + semantic_score * 0.7

            # Update the similarity score with temporal weighting
            memory.similarity_score = temporal_score

        # Sort by combined score
        memories.sort(key=lambda m: m.similarity_score or 0.0, reverse=True)
        return memories

    async def get_conversation_summary(
        self,
        conversation_id: str,
        time_range: tuple[datetime, datetime] | None = None
    ) -> dict[str, Any] | None:
        """
        Get conversation summary leveraging existing conversation_history.
        
        Provides context for memory retrieval and importance scoring.
        """
        if not self.connection_pool:
            raise RuntimeError("Temporal store not initialized")

        try:
            async with self.connection_pool.acquire() as conn:
                # Build query with optional time range
                base_query = """
                SELECT 
                    conversation_id,
                    COUNT(*) as message_count,
                    MIN(created_at) as start_time,
                    MAX(created_at) as end_time,
                    AVG(COALESCE(metadata->>'importance_score', '0.5')::float) as avg_importance,
                    ARRAY_AGG(DISTINCT user_id) as participants
                FROM conversation_history 
                WHERE conversation_id = $1
                """

                params = [conversation_id]

                if time_range:
                    base_query += " AND created_at BETWEEN $2 AND $3"
                    params.extend([time_range[0], time_range[1]])

                base_query += " GROUP BY conversation_id"

                row = await conn.fetchrow(base_query, *params)

                if row:
                    return {
                        'conversation_id': row['conversation_id'],
                        'message_count': row['message_count'],
                        'duration': (row['end_time'] - row['start_time']).total_seconds(),
                        'avg_importance': float(row['avg_importance']),
                        'participants': row['participants'],
                        'start_time': row['start_time'],
                        'end_time': row['end_time']
                    }

                return None

        except Exception as e:
            logger.error(f"Failed to get conversation summary: {e}")
            return None

    async def get_memory_timeline(
        self,
        user_id: str,
        days_back: int = 30,
        limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Get user's memory timeline leveraging existing data structures.
        
        Provides chronological view of important memories and conversations.
        """
        if not self.connection_pool:
            raise RuntimeError("Temporal store not initialized")

        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days_back)

            async with self.connection_pool.acquire() as conn:
                # Query existing conversation_history for timeline
                query = """
                SELECT 
                    conversation_id,
                    created_at,
                    metadata,
                    COALESCE(metadata->>'importance_score', '0.5')::float as importance
                FROM conversation_history 
                WHERE user_id = $1 
                    AND created_at >= $2 
                    AND created_at <= $3
                ORDER BY importance DESC, created_at DESC
                LIMIT $4
                """

                rows = await conn.fetch(query, user_id, start_time, end_time, limit)

                timeline = []
                for row in rows:
                    timeline.append({
                        'conversation_id': row['conversation_id'],
                        'timestamp': row['created_at'],
                        'importance_score': row['importance'],
                        'metadata': row['metadata'] or {},
                        'type': 'conversation'
                    })

                logger.info(f"Retrieved {len(timeline)} timeline entries for user {user_id}")
                return timeline

        except Exception as e:
            logger.error(f"Failed to get memory timeline: {e}")
            return []

    async def get_partition_stats(self) -> dict[str, Any]:
        """
        Get statistics about temporal partitions for monitoring.
        
        Shows how data is distributed across time partitions.
        """
        if not self.connection_pool:
            return {'error': 'Not initialized'}

        try:
            async with self.connection_pool.acquire() as conn:
                # Get partition information from existing conversation_history
                query = """
                SELECT 
                    schemaname,
                    tablename,
                    attname,
                    n_distinct,
                    avg_width
                FROM pg_stats 
                WHERE tablename LIKE 'conversation_history%'
                ORDER BY tablename
                """

                rows = await conn.fetch(query)

                partition_info = {}
                for row in rows:
                    table_name = row['tablename']
                    if table_name not in partition_info:
                        partition_info[table_name] = {}

                    partition_info[table_name][row['attname']] = {
                        'distinct_values': row['n_distinct'],
                        'avg_width': row['avg_width']
                    }

                return {
                    'partitions': partition_info,
                    'total_partitions': len(partition_info),
                    'strategy': 'time_based'
                }

        except Exception as e:
            logger.error(f"Failed to get partition stats: {e}")
            return {'error': str(e)}

    async def cleanup_old_memories(self, days_to_keep: int = 365) -> dict[str, Any]:
        """
        Clean up old memories beyond retention period.
        
        Leverages existing partition strategy for efficient cleanup.
        """
        if not self.connection_pool:
            raise RuntimeError("Temporal store not initialized")

        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

            async with self.connection_pool.acquire() as conn:
                # Count memories to be deleted
                count_query = """
                SELECT COUNT(*) as count
                FROM conversation_history 
                WHERE created_at < $1
                """

                count_row = await conn.fetchrow(count_query, cutoff_date)
                memories_to_delete = count_row['count']

                # For now, just return stats (actual deletion should be carefully planned)
                return {
                    'memories_to_delete': memories_to_delete,
                    'cutoff_date': cutoff_date,
                    'status': 'analysis_only',
                    'recommendation': 'Use partition dropping for efficient cleanup'
                }

        except Exception as e:
            logger.error(f"Cleanup analysis failed: {e}")
            return {'error': str(e)}

    async def close(self):
        """Close the connection pool."""
        if self.connection_pool:
            await self.connection_pool.close()
            self.connection_pool = None
            logger.info("Temporal memory store closed")
