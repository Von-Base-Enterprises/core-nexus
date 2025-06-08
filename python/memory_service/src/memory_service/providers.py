"""
Provider Implementations for Unified Vector Store

Concrete implementations that wrap existing Pinecone and ChromaDB code
from the Core Nexus codebase while preparing for pgvector integration.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4
try:
    from typing import UUID
except ImportError:
    from uuid import UUID

from .unified_store import VectorProvider
from .models import MemoryResponse, ProviderConfig

logger = logging.getLogger(__name__)


class PineconeProvider(VectorProvider):
    """
    Pinecone provider wrapping existing implementations from CoreNexus.py
    
    Leverages existing cloud-scale vector storage with added resilience.
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.index = None
        self.embedding_dim = config.config.get('embedding_dim', 1536)
        self.metric = config.config.get('metric', 'cosine')
        self._initialize_pinecone()
    
    def _initialize_pinecone(self):
        """Initialize Pinecone connection using existing patterns."""
        try:
            import pinecone
            from pinecone import Pinecone
            
            # Use existing API key patterns from CoreNexus.py
            api_key = self.config.config.get('api_key')
            if not api_key:
                raise ValueError("Pinecone API key required in config")
            
            # Initialize client
            pc = Pinecone(api_key=api_key)
            
            index_name = self.config.config.get('index_name', 'core-nexus-memories')
            
            # Check if index exists, create if needed
            existing_indexes = [idx.name for idx in pc.list_indexes()]
            if index_name not in existing_indexes:
                logger.info(f"Creating Pinecone index: {index_name}")
                pc.create_index(
                    name=index_name,
                    dimension=self.embedding_dim,
                    metric=self.metric,
                    spec=pinecone.ServerlessSpec(
                        cloud='aws',
                        region='us-east-1'
                    )
                )
            
            self.index = pc.Index(index_name)
            logger.info(f"Pinecone provider initialized: {index_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}")
            self.enabled = False
            raise
    
    async def store(self, content: str, embedding: List[float], metadata: Dict[str, Any]) -> UUID:
        """Store memory in Pinecone with UUID."""
        if not self.index:
            raise RuntimeError("Pinecone index not initialized")
        
        memory_id = uuid4()
        
        # Prepare metadata (Pinecone has limitations on metadata types)
        pinecone_metadata = {
            'content': content[:1000],  # Truncate for metadata storage
            'user_id': str(metadata.get('user_id', '')),
            'conversation_id': str(metadata.get('conversation_id', '')),
            'importance_score': float(metadata.get('importance_score', 0.5)),
            'created_at': float(metadata.get('created_at', time.time())),
            'content_length': int(metadata.get('content_length', len(content)))
        }
        
        # Store vector with metadata
        vector_data = {
            'id': str(memory_id),
            'values': embedding,
            'metadata': pinecone_metadata
        }
        
        # Use asyncio to make synchronous pinecone call async
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.index.upsert, [vector_data])
        
        logger.debug(f"Stored memory {memory_id} in Pinecone")
        return memory_id
    
    async def query(self, query_embedding: List[float], limit: int, filters: Dict[str, Any]) -> List[MemoryResponse]:
        """Query similar memories from Pinecone."""
        if not self.index:
            raise RuntimeError("Pinecone index not initialized")
        
        # Build Pinecone filter from generic filters
        pinecone_filter = {}
        if filters:
            if 'user_id' in filters:
                pinecone_filter['user_id'] = {'$eq': str(filters['user_id'])}
            if 'conversation_id' in filters:
                pinecone_filter['conversation_id'] = {'$eq': str(filters['conversation_id'])}
            if 'min_importance' in filters:
                pinecone_filter['importance_score'] = {'$gte': float(filters['min_importance'])}
        
        # Query Pinecone
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, 
            lambda: self.index.query(
                vector=query_embedding,
                top_k=limit,
                filter=pinecone_filter if pinecone_filter else None,
                include_metadata=True
            )
        )
        
        # Convert to MemoryResponse objects
        memories = []
        for match in response.matches:
            metadata = match.metadata or {}
            memory = MemoryResponse(
                id=UUID(match.id),
                content=metadata.get('content', ''),
                metadata=dict(metadata),
                importance_score=float(metadata.get('importance_score', 0.5)),
                similarity_score=float(match.score)
            )
            memories.append(memory)
        
        logger.debug(f"Pinecone query returned {len(memories)} memories")
        return memories
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Pinecone health and stats."""
        try:
            if not self.index:
                return {'status': 'error', 'message': 'Index not initialized'}
            
            # Get index stats
            loop = asyncio.get_event_loop()
            stats = await loop.run_in_executor(None, self.index.describe_index_stats)
            
            return {
                'status': 'healthy',
                'total_vectors': stats.total_vector_count,
                'dimension': stats.dimension,
                'index_fullness': stats.index_fullness,
                'namespaces': len(stats.namespaces) if stats.namespaces else 0
            }
            
        except Exception as e:
            logger.error(f"Pinecone health check failed: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get detailed Pinecone statistics."""
        health = await self.health_check()
        return {
            'provider': 'pinecone',
            'health': health,
            'features': ['cloud_scale', 'managed_service', 'auto_scaling']
        }


class ChromaProvider(VectorProvider):
    """
    ChromaDB provider wrapping existing implementations from chroma_vectorstore.py
    
    Leverages existing local-speed vector storage with added structure.
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.client = None
        self.collection = None
        self.collection_name = config.config.get('collection_name', 'core_nexus_memories')
        self._initialize_chroma()
    
    def _initialize_chroma(self):
        """Initialize ChromaDB connection using existing patterns."""
        try:
            import chromadb
            from chromadb.config import Settings
            
            # Configure ChromaDB client
            persist_directory = self.config.config.get('persist_directory', './chroma_db')
            
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            try:
                self.collection = self.client.get_collection(name=self.collection_name)
                logger.info(f"Using existing ChromaDB collection: {self.collection_name}")
            except Exception:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "Core Nexus unified memory storage"}
                )
                logger.info(f"Created new ChromaDB collection: {self.collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.enabled = False
            raise
    
    async def store(self, content: str, embedding: List[float], metadata: Dict[str, Any]) -> UUID:
        """Store memory in ChromaDB with UUID."""
        if not self.collection:
            raise RuntimeError("ChromaDB collection not initialized")
        
        memory_id = uuid4()
        
        # Prepare metadata for ChromaDB
        chroma_metadata = {
            'user_id': str(metadata.get('user_id', '')),
            'conversation_id': str(metadata.get('conversation_id', '')),
            'importance_score': float(metadata.get('importance_score', 0.5)),
            'created_at': float(metadata.get('created_at', time.time())),
            'content_length': int(metadata.get('content_length', len(content)))
        }
        
        # Store in ChromaDB
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self.collection.add(
                ids=[str(memory_id)],
                documents=[content],
                metadatas=[chroma_metadata],
                embeddings=[embedding]
            )
        )
        
        logger.debug(f"Stored memory {memory_id} in ChromaDB")
        return memory_id
    
    async def query(self, query_embedding: List[float], limit: int, filters: Dict[str, Any]) -> List[MemoryResponse]:
        """Query similar memories from ChromaDB."""
        if not self.collection:
            raise RuntimeError("ChromaDB collection not initialized")
        
        # Build ChromaDB where filter
        where_filter = {}
        if filters:
            if 'user_id' in filters:
                where_filter['user_id'] = {'$eq': str(filters['user_id'])}
            if 'conversation_id' in filters:
                where_filter['conversation_id'] = {'$eq': str(filters['conversation_id'])}
            if 'min_importance' in filters:
                where_filter['importance_score'] = {'$gte': float(filters['min_importance'])}
        
        # Query ChromaDB
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where_filter if where_filter else None,
                include=['documents', 'metadatas', 'distances']
            )
        )
        
        # Convert to MemoryResponse objects
        memories = []
        if results['documents'] and len(results['documents']) > 0:
            documents = results['documents'][0]
            metadatas = results['metadatas'][0] if results['metadatas'] else []
            distances = results['distances'][0] if results['distances'] else []
            ids = results['ids'][0] if results['ids'] else []
            
            for i, doc in enumerate(documents):
                metadata = metadatas[i] if i < len(metadatas) else {}
                distance = distances[i] if i < len(distances) else 1.0
                doc_id = ids[i] if i < len(ids) else str(uuid4())
                
                # Convert distance to similarity (ChromaDB uses distance, we want similarity)
                similarity_score = max(0.0, 1.0 - distance)
                
                memory = MemoryResponse(
                    id=UUID(doc_id),
                    content=doc,
                    metadata=dict(metadata),
                    importance_score=float(metadata.get('importance_score', 0.5)),
                    similarity_score=similarity_score
                )
                memories.append(memory)
        
        logger.debug(f"ChromaDB query returned {len(memories)} memories")
        return memories
    
    async def health_check(self) -> Dict[str, Any]:
        """Check ChromaDB health and stats."""
        try:
            if not self.collection:
                return {'status': 'error', 'message': 'Collection not initialized'}
            
            # Get collection stats
            loop = asyncio.get_event_loop()
            count = await loop.run_in_executor(None, self.collection.count)
            
            return {
                'status': 'healthy',
                'total_vectors': count,
                'collection_name': self.collection_name,
                'storage_type': 'persistent_local'
            }
            
        except Exception as e:
            logger.error(f"ChromaDB health check failed: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get detailed ChromaDB statistics."""
        health = await self.health_check()
        return {
            'provider': 'chromadb',
            'health': health,
            'features': ['local_storage', 'fast_queries', 'no_api_limits']
        }


class PgVectorProvider(VectorProvider):
    """
    PostgreSQL + pgvector provider for unified SQL queries.
    
    Enables complex relational queries while maintaining vector similarity search.
    Uses asyncpg for optimal performance with asyncio.
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.connection_pool = None
        self.table_name = config.config.get('table_name', 'vector_memories')
        self.embedding_dim = config.config.get('embedding_dim', 1536)
        self.distance_metric = config.config.get('distance_metric', 'cosine')
        self.index_type = config.config.get('index_type', 'hnsw')  # hnsw or ivfflat
        self._initialize_connection()
        
    def _initialize_connection(self):
        """Initialize asyncpg connection pool."""
        asyncio.create_task(self._async_initialize())
        
    async def _async_initialize(self):
        """Async initialization of PostgreSQL + pgvector."""
        try:
            import asyncpg
            
            # Build connection string from config
            db_config = self.config.config
            dsn = f"postgresql://{db_config.get('user', 'postgres')}:" \
                  f"{db_config.get('password', '')}@" \
                  f"{db_config.get('host', 'localhost')}:" \
                  f"{db_config.get('port', 5432)}/" \
                  f"{db_config.get('database', 'postgres')}"
            
            # Create connection pool
            self.connection_pool = await asyncpg.create_pool(
                dsn,
                min_size=2,
                max_size=10,
                command_timeout=self.config.timeout_seconds
            )
            
            # Initialize database schema
            await self._setup_database()
            
            logger.info(f"PgVector provider initialized: {self.table_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize pgvector: {e}")
            self.enabled = False
            raise
            
    async def _setup_database(self):
        """Set up pgvector extension and memory table."""
        async with self.connection_pool.acquire() as conn:
            # Create pgvector extension
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            
            # Create memories table with vector column
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    content TEXT NOT NULL,
                    embedding vector({self.embedding_dim}),
                    metadata JSONB DEFAULT '{{}}',
                    user_id TEXT,
                    conversation_id TEXT,
                    importance_score FLOAT DEFAULT 0.5,
                    created_at TIMESTAMP DEFAULT NOW(),
                    last_accessed TIMESTAMP DEFAULT NOW(),
                    access_count INTEGER DEFAULT 0
                )
            """)
            
            # Create indexes for performance
            await self._create_indexes(conn)
            
            logger.info(f"Database schema initialized for {self.table_name}")
            
    async def _create_indexes(self, conn):
        """Create optimized indexes for vector similarity and metadata queries."""
        table = self.table_name
        
        try:
            # Vector similarity index (HNSW for best performance)
            if self.index_type == 'hnsw':
                await conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS {table}_embedding_hnsw_idx 
                    ON {table} USING hnsw (embedding vector_{self.distance_metric}_ops)
                    WITH (m = 16, ef_construction = 64)
                """)
            else:
                # IVFFlat alternative for very large datasets
                await conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS {table}_embedding_ivf_idx 
                    ON {table} USING ivfflat (embedding vector_{self.distance_metric}_ops)
                    WITH (lists = 1000)
                """)
            
            # Metadata indexes for filtering
            await conn.execute(f"CREATE INDEX IF NOT EXISTS {table}_user_id_idx ON {table} (user_id)")
            await conn.execute(f"CREATE INDEX IF NOT EXISTS {table}_conversation_id_idx ON {table} (conversation_id)")
            await conn.execute(f"CREATE INDEX IF NOT EXISTS {table}_created_at_idx ON {table} (created_at)")
            await conn.execute(f"CREATE INDEX IF NOT EXISTS {table}_importance_idx ON {table} (importance_score)")
            
            # Compound indexes for common queries
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS {table}_user_time_idx 
                ON {table} (user_id, created_at DESC)
            """)
            
            # GIN index for metadata JSONB queries
            await conn.execute(f"CREATE INDEX IF NOT EXISTS {table}_metadata_gin_idx ON {table} USING gin (metadata)")
            
            logger.debug(f"Created indexes for {table}")
            
        except Exception as e:
            logger.warning(f"Index creation failed (may already exist): {e}")
    
    async def store(self, content: str, embedding: List[float], metadata: Dict[str, Any]) -> UUID:
        """Store memory in PostgreSQL with pgvector."""
        if not self.connection_pool:
            raise RuntimeError("PgVector provider not initialized")
        
        # Generate UUID for memory
        memory_id = uuid4()
        
        async with self.connection_pool.acquire() as conn:
            # Insert memory with vector embedding
            await conn.execute(f"""
                INSERT INTO {self.table_name} (
                    id, content, embedding, metadata, user_id, conversation_id, 
                    importance_score, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, 
                memory_id,
                content,
                embedding,  # asyncpg handles vector type conversion
                metadata,
                metadata.get('user_id'),
                metadata.get('conversation_id'),
                float(metadata.get('importance_score', 0.5)),
                metadata.get('created_at', time.time())
            )
        
        logger.debug(f"Stored memory {memory_id} in pgvector")
        return memory_id
    
    async def query(self, query_embedding: List[float], limit: int, filters: Dict[str, Any]) -> List[MemoryResponse]:
        """Query memories using pgvector similarity search."""
        if not self.connection_pool:
            raise RuntimeError("PgVector provider not initialized")
        
        # Build WHERE clause from filters
        where_conditions = ["1=1"]  # Always true base condition
        params = [query_embedding, limit]
        param_idx = 3
        
        if filters:
            if 'user_id' in filters:
                where_conditions.append(f"user_id = ${param_idx}")
                params.append(filters['user_id'])
                param_idx += 1
                
            if 'conversation_id' in filters:
                where_conditions.append(f"conversation_id = ${param_idx}")
                params.append(filters['conversation_id'])
                param_idx += 1
                
            if 'min_importance' in filters:
                where_conditions.append(f"importance_score >= ${param_idx}")
                params.append(float(filters['min_importance']))
                param_idx += 1
                
            if 'start_time' in filters:
                where_conditions.append(f"created_at >= to_timestamp(${param_idx})")
                params.append(float(filters['start_time']))
                param_idx += 1
                
            if 'end_time' in filters:
                where_conditions.append(f"created_at <= to_timestamp(${param_idx})")
                params.append(float(filters['end_time']))
                param_idx += 1
        
        where_clause = " AND ".join(where_conditions)
        
        # Choose distance function based on metric
        distance_func = f"embedding <-> $1"  # L2 distance
        if self.distance_metric == 'cosine':
            distance_func = f"embedding <=> $1"  # Cosine distance
        elif self.distance_metric == 'inner_product':
            distance_func = f"embedding <#> $1"  # Inner product
        
        # Execute similarity query
        async with self.connection_pool.acquire() as conn:
            # Update access tracking
            query_sql = f"""
                UPDATE {self.table_name} 
                SET last_accessed = NOW(), access_count = access_count + 1
                WHERE id IN (
                    SELECT id FROM {self.table_name}
                    WHERE {where_clause}
                    ORDER BY {distance_func}
                    LIMIT $2
                );
                
                SELECT 
                    id, content, metadata, importance_score, created_at,
                    {distance_func} AS distance
                FROM {self.table_name}
                WHERE {where_clause}
                ORDER BY {distance_func}
                LIMIT $2
            """
            
            rows = await conn.fetch(query_sql, *params)
            
            # Convert to MemoryResponse objects
            memories = []
            for row in rows:
                # Convert distance to similarity score (0-1 range)
                distance = float(row['distance'])
                if self.distance_metric == 'cosine':
                    similarity_score = max(0.0, 1.0 - distance)
                else:
                    # For L2 distance, use exponential decay
                    similarity_score = max(0.0, 1.0 / (1.0 + distance))
                
                memory = MemoryResponse(
                    id=row['id'],
                    content=row['content'],
                    metadata=dict(row['metadata']) if row['metadata'] else {},
                    importance_score=float(row['importance_score']),
                    similarity_score=similarity_score,
                    created_at=row['created_at']
                )
                memories.append(memory)
        
        logger.debug(f"PgVector query returned {len(memories)} memories")
        return memories
    
    async def health_check(self) -> Dict[str, Any]:
        """Check PostgreSQL + pgvector health and performance."""
        try:
            if not self.connection_pool:
                return {'status': 'error', 'message': 'Connection pool not initialized'}
            
            async with self.connection_pool.acquire() as conn:
                # Check pgvector extension
                ext_check = await conn.fetchrow(
                    "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
                )
                
                if not ext_check:
                    return {'status': 'error', 'message': 'pgvector extension not found'}
                
                # Get table statistics
                stats = await conn.fetchrow(f"""
                    SELECT 
                        COUNT(*) as total_vectors,
                        AVG(importance_score) as avg_importance,
                        MIN(created_at) as oldest_memory,
                        MAX(created_at) as newest_memory,
                        AVG(access_count) as avg_access_count
                    FROM {self.table_name}
                """)
                
                # Check index usage
                index_stats = await conn.fetch(f"""
                    SELECT 
                        indexname, 
                        idx_scan as scans,
                        idx_tup_read as tuples_read,
                        idx_tup_fetch as tuples_fetched
                    FROM pg_stat_user_indexes 
                    WHERE tablename = '{self.table_name}'
                    ORDER BY idx_scan DESC
                """)
                
                return {
                    'status': 'healthy',
                    'pgvector_version': ext_check['extversion'],
                    'total_vectors': int(stats['total_vectors']) if stats['total_vectors'] else 0,
                    'avg_importance': float(stats['avg_importance']) if stats['avg_importance'] else 0.0,
                    'memory_span_days': (stats['newest_memory'] - stats['oldest_memory']).days if stats['oldest_memory'] else 0,
                    'avg_access_count': float(stats['avg_access_count']) if stats['avg_access_count'] else 0.0,
                    'distance_metric': self.distance_metric,
                    'index_type': self.index_type,
                    'embedding_dimensions': self.embedding_dim,
                    'active_indexes': len(index_stats),
                    'connection_pool_size': self.connection_pool._queue.qsize()
                }
                
        except Exception as e:
            logger.error(f"PgVector health check failed: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive pgvector statistics."""
        health = await self.health_check()
        
        try:
            async with self.connection_pool.acquire() as conn:
                # Query performance metrics
                perf_stats = await conn.fetchrow(f"""
                    SELECT 
                        pg_size_pretty(pg_total_relation_size('{self.table_name}')) as table_size,
                        pg_size_pretty(pg_indexes_size('{self.table_name}')) as index_size
                """)
                
                # Memory usage by user
                user_stats = await conn.fetch(f"""
                    SELECT 
                        user_id,
                        COUNT(*) as memory_count,
                        AVG(importance_score) as avg_importance
                    FROM {self.table_name}
                    WHERE user_id IS NOT NULL
                    GROUP BY user_id
                    ORDER BY memory_count DESC
                    LIMIT 10
                """)
                
                return {
                    'provider': 'pgvector',
                    'health': health,
                    'storage': {
                        'table_size': perf_stats['table_size'] if perf_stats else 'unknown',
                        'index_size': perf_stats['index_size'] if perf_stats else 'unknown'
                    },
                    'top_users': [
                        {
                            'user_id': row['user_id'],
                            'memory_count': row['memory_count'],
                            'avg_importance': float(row['avg_importance'])
                        }
                        for row in user_stats
                    ],
                    'features': [
                        'sql_queries', 'acid_compliance', 'complex_joins', 
                        'time_partitioning', 'metadata_indexing', 'access_tracking'
                    ]
                }
                
        except Exception as e:
            logger.error(f"Failed to get pgvector stats: {e}")
            return {
                'provider': 'pgvector',
                'health': health,
                'error': str(e)
            }
    
    async def close(self):
        """Close the connection pool."""
        if self.connection_pool:
            await self.connection_pool.close()
            self.connection_pool = None
            logger.info("PgVector provider closed")