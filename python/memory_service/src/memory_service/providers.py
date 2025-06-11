"""
Provider Implementations for Unified Vector Store

Concrete implementations that wrap existing Pinecone and ChromaDB code
from the Core Nexus codebase while preparing for pgvector integration.
"""

import asyncio
import json
import logging
from typing import Any
from uuid import uuid4

try:
    from typing import UUID
except ImportError:
    from uuid import UUID

from .models import MemoryResponse, ProviderConfig
from .unified_store import VectorProvider

logger = logging.getLogger(__name__)


class PineconeProvider(VectorProvider):
    """
    Pinecone provider wrapping existing implementations from CoreNexus.py

    Leverages existing cloud-scale vector storage with added resilience.
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        # TODO: Initialize Pinecone client with config
        self.enabled = False  # Disabled until Pinecone integration is complete

    async def store(self, content: str, embedding: list[float], metadata: dict[str, Any]) -> UUID:
        """Store vector in Pinecone."""
        if not self.enabled:
            raise RuntimeError("Pinecone provider not enabled")

        # TODO: Implement Pinecone storage
        # This will wrap existing functionality from the current codebase
        memory_id = uuid4()

        logger.info(f"Stored in Pinecone: {memory_id}")
        return memory_id

    async def query(self, query_embedding: list[float], limit: int, filters: dict[str, Any]) -> list[MemoryResponse]:
        """Query Pinecone for similar vectors."""
        if not self.enabled:
            return []

        # TODO: Implement Pinecone query
        # This will wrap existing functionality from the current codebase

        return []

    async def health_check(self) -> dict[str, Any]:
        """Check Pinecone health."""
        return {
            'status': 'disabled',
            'reason': 'Pinecone integration pending'
        }

    async def get_stats(self) -> dict[str, Any]:
        """Get Pinecone statistics."""
        return {
            'provider': 'pinecone',
            'enabled': self.enabled,
            'message': 'Pinecone integration pending'
        }


class ChromaProvider(VectorProvider):
    """
    ChromaDB provider for local vector storage.

    Fast, embedded solution perfect for development and edge deployments.
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.collection = None
        self._initialize_chroma(config.config)

    def _initialize_chroma(self, config: dict[str, Any]):
        """Initialize ChromaDB collection."""
        try:
            import chromadb
            from chromadb.config import Settings

            # Initialize ChromaDB client
            persist_dir = config.get('persist_directory', './chroma_db')
            self.client = chromadb.PersistentClient(
                path=persist_dir,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            # Get or create collection
            collection_name = config.get('collection_name', 'core_nexus_memories')
            try:
                self.collection = self.client.get_collection(collection_name)
                logger.info(f"Loaded existing ChromaDB collection: {collection_name}")
            except Exception:
                self.collection = self.client.create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"Created new ChromaDB collection: {collection_name}")

        except ImportError:
            logger.error("ChromaDB not installed. Install with: pip install chromadb")
            self.enabled = False
            raise
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.enabled = False
            raise

    async def store(self, content: str, embedding: list[float], metadata: dict[str, Any]) -> UUID:
        """Store vector in ChromaDB."""
        if not self.collection:
            raise RuntimeError("ChromaDB not initialized")

        memory_id = uuid4()

        # ChromaDB is synchronous, so we run in executor
        loop = asyncio.get_event_loop()

        def _store():
            self.collection.add(
                embeddings=[embedding],
                documents=[content],
                metadatas=[metadata],
                ids=[str(memory_id)]
            )

        await loop.run_in_executor(None, _store)

        logger.debug(f"Stored in ChromaDB: {memory_id}")
        return memory_id

    async def query(self, query_embedding: list[float], limit: int, filters: dict[str, Any]) -> list[MemoryResponse]:
        """Query ChromaDB for similar vectors."""
        if not self.collection:
            return []

        loop = asyncio.get_event_loop()

        def _query():
            # Apply filters if provided
            where_clause = {}
            if filters:
                # ChromaDB uses a different filter format
                # Convert our filters to ChromaDB format
                for key, value in filters.items():
                    if key not in ['limit', 'offset']:  # Skip non-metadata filters
                        where_clause[key] = value

            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where_clause if where_clause else None,
                include=['metadatas', 'documents', 'distances']
            )

            return results

        results = await loop.run_in_executor(None, _query)

        # Convert ChromaDB results to MemoryResponse objects
        memories = []
        if results and results['ids'] and len(results['ids'][0]) > 0:
            for i in range(len(results['ids'][0])):
                memory = MemoryResponse(
                    id=UUID(results['ids'][0][i]),
                    content=results['documents'][0][i],
                    metadata=results['metadatas'][0][i] or {},
                    embedding=[],  # ChromaDB doesn't return embeddings by default
                    importance_score=results['metadatas'][0][i].get('importance_score', 0.5),
                    similarity_score=1.0 - results['distances'][0][i],  # Convert distance to similarity
                    created_at=results['metadatas'][0][i].get('created_at', '')
                )
                memories.append(memory)

        return memories

    async def health_check(self) -> dict[str, Any]:
        """Check ChromaDB health."""
        try:
            if self.collection:
                count = self.collection.count()
                return {
                    'status': 'healthy',
                    'details': {
                        'total_vectors': count,
                        'collection_name': self.collection.name
                    }
                }
            else:
                return {
                    'status': 'unhealthy',
                    'error': 'Collection not initialized'
                }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }

    async def get_stats(self) -> dict[str, Any]:
        """Get ChromaDB statistics."""
        try:
            if self.collection:
                count = self.collection.count()
                return {
                    'provider': 'chromadb',
                    'total_memories': count,
                    'collection_name': self.collection.name,
                    'embedding_dimension': 1536  # Default for OpenAI embeddings
                }
            else:
                return {
                    'provider': 'chromadb',
                    'error': 'Collection not initialized'
                }
        except Exception as e:
            return {
                'provider': 'chromadb',
                'error': str(e)
            }


class PgVectorProvider(VectorProvider):
    """
    PostgreSQL with pgvector extension provider.

    Combines the reliability of PostgreSQL with vector similarity search.
    Perfect for unified queries across structured and vector data.
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.connection_pool = None
        self.table_name = config.config.get('table_name', 'memories')  # Use new non-partitioned table
        self.embedding_dim = config.config.get('embedding_dim', 1536)
        self._pool_initialization_task = None
        self._initialize_pool(config.config)

    def _initialize_pool(self, config: dict[str, Any]):
        """Initialize async connection pool."""

        async def init_pool():
            try:
                import asyncpg

                # Build connection string
                conn_str = (
                    f"postgresql://{config['user']}:{config['password']}@"
                    f"{config['host']}:{config['port']}/{config['database']}"
                )

                self.connection_pool = await asyncpg.create_pool(
                    conn_str,
                    min_size=5,
                    max_size=20,
                    command_timeout=60,
                    server_settings={
                        'synchronous_commit': 'on',  # Ensure synchronous commits
                        'jit': 'off'  # Disable JIT for more predictable performance
                    }
                )

                # Ensure pgvector extension is enabled
                async with self.connection_pool.acquire() as conn:
                    await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

                    # Create table if not exists
                    await conn.execute(f"""
                        CREATE TABLE IF NOT EXISTS {self.table_name} (
                            id UUID PRIMARY KEY,
                            content TEXT NOT NULL,
                            embedding vector({self.embedding_dim}),
                            metadata JSONB DEFAULT '{{}}',
                            importance_score FLOAT DEFAULT 0.5,
                            created_at TIMESTAMP DEFAULT NOW(),
                            updated_at TIMESTAMP DEFAULT NOW()
                        )
                    """)

                    # Create indexes
                    await conn.execute(f"""
                        CREATE INDEX IF NOT EXISTS idx_{self.table_name}_embedding
                        ON {self.table_name}
                        USING ivfflat (embedding vector_cosine_ops)
                        WITH (lists = 100)
                    """)

                    await conn.execute(f"""
                        CREATE INDEX IF NOT EXISTS idx_{self.table_name}_metadata
                        ON {self.table_name}
                        USING GIN (metadata)
                    """)

                    await conn.execute(f"""
                        CREATE INDEX IF NOT EXISTS idx_{self.table_name}_importance
                        ON {self.table_name} (importance_score DESC)
                    """)

                    await conn.execute(f"""
                        CREATE INDEX IF NOT EXISTS idx_{self.table_name}_created_at
                        ON {self.table_name} (created_at DESC)
                    """)

                logger.info("PgVector provider initialized successfully")
                self.enabled = True  # Mark as enabled after successful initialization

            except ImportError:
                logger.error("asyncpg not installed. Install with: pip install asyncpg")
                self.enabled = False
                raise
            except Exception as e:
                logger.error(f"Failed to initialize PgVector: {e}")
                self.enabled = False
                raise

        # Run initialization
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're already in an async context
                self._pool_initialization_task = asyncio.create_task(init_pool())
            else:
                # Synchronous context
                loop.run_until_complete(init_pool())
        except RuntimeError:
            # No event loop, create one
            asyncio.run(init_pool())

    async def _ensure_pool_ready(self):
        """Ensure the connection pool is ready before use."""
        if self._pool_initialization_task and not self._pool_initialization_task.done():
            await self._pool_initialization_task
        if not self.connection_pool:
            raise RuntimeError("PgVector connection pool not initialized")

    async def store(self, content: str, embedding: list[float], metadata: dict[str, Any]) -> UUID:
        """Store vector in PostgreSQL with transaction wrapping."""
        await self._ensure_pool_ready()

        memory_id = uuid4()

        async with self.connection_pool.acquire() as conn:
            # Use transaction for atomicity
            async with conn.transaction():
                # Convert embedding to PostgreSQL vector format
                embedding_str = '[' + ','.join(map(str, embedding)) + ']'

                # Serialize metadata to JSON string for PostgreSQL JSONB column
                metadata_json = json.dumps(metadata) if metadata else '{}'

                await conn.execute(f"""
                    INSERT INTO {self.table_name}
                    (id, content, embedding, metadata, importance_score)
                    VALUES ($1, $2, $3::vector, $4::jsonb, $5)
                """,
                    memory_id,
                    content,
                    embedding_str,
                    metadata_json,
                    metadata.get('importance_score', 0.5)
                )

                # Force synchronous commit for immediate consistency
                await conn.execute("SET LOCAL synchronous_commit = on")

        logger.debug(f"Stored in PgVector: {memory_id}")
        return memory_id

    async def query(self, query_embedding: list[float], limit: int, filters: dict[str, Any]) -> list[MemoryResponse]:
        """Query PostgreSQL for similar vectors."""
        await self._ensure_pool_ready()

        async with self.connection_pool.acquire() as conn:
            # Build query with filters
            where_clauses = []
            params = []
            param_count = 2  # $1 is embedding, $2 is limit

            # Add metadata filters
            if filters:
                for key, value in filters.items():
                    if key not in ['limit', 'offset']:
                        where_clauses.append(f"metadata->>'{key}' = ${param_count + 1}")
                        params.append(str(value))
                        param_count += 1

            where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

            # Convert embedding to PostgreSQL vector format
            embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'

            # Query with cosine similarity - handle NULL embeddings
            query = f"""
                SELECT
                    id,
                    content,
                    metadata,
                    COALESCE(importance_score, 0.5) as importance_score,
                    CASE 
                        WHEN embedding IS NULL THEN 0.0
                        ELSE 1 - (embedding <=> $1::vector)
                    END as similarity_score,
                    created_at
                FROM vector_memories
                {where_clause}
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> $1::vector
                LIMIT $2
            """

            # Use read committed isolation level for consistent reads
            rows = await conn.fetch(query, embedding_str, limit, *params)

            # Convert to MemoryResponse objects
            memories = []
            for row in rows:
                memory = MemoryResponse(
                    id=row['id'],
                    content=row['content'],
                    metadata=row['metadata'] if isinstance(row['metadata'], dict) else {},
                    embedding=[],  # Don't return full embeddings in response
                    importance_score=float(row['importance_score']),
                    similarity_score=float(row['similarity_score']),
                    created_at=row['created_at'].isoformat() if row['created_at'] else ''
                )
                memories.append(memory)

        return memories

    async def get_recent_memories(self, limit: int, filters: dict[str, Any] | None = None) -> list[MemoryResponse]:
        """
        Get recent memories without vector similarity search.
        
        This method bypasses the vector similarity calculation entirely,
        returning memories ordered by creation date (newest first).
        Perfect for "get all" queries where relevance isn't needed.
        """
        await self._ensure_pool_ready()
        
        async with self.connection_pool.acquire() as conn:
            # Build query with filters
            where_clauses = []
            params = []
            param_count = 1  # $1 is limit
            
            # Add metadata filters
            if filters:
                for key, value in filters.items():
                    if key not in ['limit', 'offset']:
                        where_clauses.append(f"metadata->>'{key}' = ${param_count + 1}")
                        params.append(str(value))
                        param_count += 1
            
            where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            
            # Query WITHOUT vector similarity - just get recent memories
            # Use COALESCE to handle both partitioned and non-partitioned tables
            query = f"""
                SELECT
                    id,
                    content,
                    metadata,
                    COALESCE(importance_score, 0.5) as importance_score,
                    created_at
                FROM vector_memories
                {where_clause}
                ORDER BY created_at DESC
                LIMIT $1
            """
            
            rows = await conn.fetch(query, limit, *params)
            
            # Convert to MemoryResponse objects
            memories = []
            for row in rows:
                memory = MemoryResponse(
                    id=row['id'],
                    content=row['content'],
                    metadata=row['metadata'] if isinstance(row['metadata'], dict) else {},
                    embedding=[],  # Don't return full embeddings
                    importance_score=float(row['importance_score']),
                    similarity_score=1.0,  # Default high score since no similarity calc
                    created_at=row['created_at'].isoformat() if row['created_at'] else ''
                )
                memories.append(memory)
        
        logger.debug(f"Retrieved {len(memories)} recent memories from PgVector")
        return memories

    async def health_check(self) -> dict[str, Any]:
        """Check PostgreSQL health."""
        try:
            await self._ensure_pool_ready()
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': f'Connection pool not ready: {str(e)}'
            }

        try:
            async with self.connection_pool.acquire() as conn:
                # Check connection
                await conn.fetchval("SELECT 1")

                # Get table stats
                count = await conn.fetchval(
                    f"SELECT COUNT(*) FROM {self.table_name}"
                )

                # Check if pgvector is enabled
                pgvector_enabled = await conn.fetchval("""
                    SELECT COUNT(*) > 0
                    FROM pg_extension
                    WHERE extname = 'vector'
                """)

                return {
                    'status': 'healthy',
                    'details': {
                        'total_vectors': count,
                        'pgvector_enabled': pgvector_enabled,
                        'table_name': self.table_name,
                        'pool_size': self.connection_pool.get_size()
                    }
                }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }

    async def get_stats(self) -> dict[str, Any]:
        """Get PgVector statistics."""
        try:
            await self._ensure_pool_ready()
        except Exception as e:
            return {
                'provider': 'pgvector',
                'error': f'Connection pool not ready: {str(e)}'
            }

        try:
            async with self.connection_pool.acquire() as conn:
                stats = await conn.fetchrow(f"""
                    SELECT
                        COUNT(*) as total_memories,
                        AVG(importance_score) as avg_importance,
                        MIN(created_at) as oldest_memory,
                        MAX(created_at) as newest_memory,
                        pg_size_pretty(pg_total_relation_size('{self.table_name}')) as table_size
                    FROM {self.table_name}
                """)

                return {
                    'provider': 'pgvector',
                    'total_memories': stats['total_memories'],
                    'avg_importance_score': float(stats['avg_importance']) if stats['avg_importance'] else 0,
                    'oldest_memory': stats['oldest_memory'].isoformat() if stats['oldest_memory'] else None,
                    'newest_memory': stats['newest_memory'].isoformat() if stats['newest_memory'] else None,
                    'table_size': stats['table_size'],
                    'table_name': self.table_name,
                    'embedding_dimension': self.embedding_dim
                }
        except Exception as e:
            return {
                'provider': 'pgvector',
                'error': str(e)
            }

    async def delete(self, memory_id: UUID) -> bool:
        """Delete a memory from PgVector."""
        try:
            await self._ensure_pool_ready()
        except Exception as e:
            logger.error(f"Pool not ready for delete: {e}")
            return False

        try:
            async with self.connection_pool.acquire() as conn:
                # Use transaction for atomicity
                async with conn.transaction():
                    result = await conn.execute(
                        f"DELETE FROM {self.table_name} WHERE id = $1",
                        memory_id
                    )
                    # Force synchronous commit
                    await conn.execute("SET LOCAL synchronous_commit = on")
                return result.split()[-1] == '1'  # "DELETE 1" means success
        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}")
            return False

    async def update_importance(self, memory_id: UUID, importance_score: float) -> bool:
        """Update importance score for a memory."""
        try:
            await self._ensure_pool_ready()
        except Exception as e:
            logger.error(f"Pool not ready for update: {e}")
            return False

        try:
            async with self.connection_pool.acquire() as conn:
                # Use transaction for atomicity
                async with conn.transaction():
                    result = await conn.execute(f"""
                        UPDATE {self.table_name}
                        SET importance_score = $1, updated_at = NOW()
                        WHERE id = $2
                    """, importance_score, memory_id)
                    # Force synchronous commit
                    await conn.execute("SET LOCAL synchronous_commit = on")
                return result.split()[-1] == '1'  # "UPDATE 1" means success
        except Exception as e:
            logger.error(f"Failed to update importance for {memory_id}: {e}")
            return False

    async def close(self):
        """Close the connection pool."""
        if self.connection_pool:
            await self.connection_pool.close()
            self.connection_pool = None
            logger.info("PgVector provider closed")


# =====================================================
# GRAPH PROVIDER (Added by Agent 2)
# =====================================================

class GraphProvider(VectorProvider):
    """
    PostgreSQL-based Graph Provider for Knowledge Graph functionality.

    Extends the existing provider pattern to add relationship understanding
    to memories, transforming isolated data into connected intelligence.
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.connection_pool = config.config.get('connection_pool')  # Reuse existing pool
        self.connection_string = config.config.get('connection_string')
        self.table_prefix = config.config.get('table_prefix', 'graph')
        self.entity_extractor = None  # Will be initialized lazily
        self._pool_initialized = bool(self.connection_pool)  # Already initialized if pool provided

    async def _ensure_pool(self):
        """Ensure connection pool is initialized (lazy initialization)."""
        if not self._pool_initialized:
            if self.connection_pool:
                # Pool was provided, mark as initialized
                self._pool_initialized = True
                logger.info("Graph provider using shared connection pool")
            elif self.connection_string:
                # Create new pool from connection string (fallback)
                try:
                    import asyncpg

                    self.connection_pool = await asyncpg.create_pool(
                        self.connection_string,
                        min_size=2,
                        max_size=10,
                        command_timeout=60
                    )
                    self._pool_initialized = True
                    logger.info("Graph provider created new connection pool")

                except Exception as e:
                    logger.error(f"Failed to initialize graph provider pool: {e}")
                    self.enabled = False
                    raise
            else:
                raise RuntimeError("GraphProvider requires either connection_pool or connection_string")

    async def _get_or_create_embedding_model(self):
        """Get or create the embedding model for entity embeddings."""
        if not hasattr(self, '_embedding_model') or self._embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Initialized entity embedding model")
            except ImportError:
                logger.warning("sentence-transformers not available, using mock embeddings")
                self._embedding_model = None
        return self._embedding_model

    async def _extract_entities(self, content: str) -> list[dict[str, Any]]:
        """Extract entities from memory content using NLP."""
        entities = []

        try:
            # Try to use spaCy for entity extraction
            if self.entity_extractor is None:
                try:
                    import spacy
                    self.entity_extractor = spacy.load("en_core_web_sm")
                except Exception:
                    logger.warning("spaCy not available, using simple pattern matching")
                    self.entity_extractor = "simple"

            if self.entity_extractor != "simple":
                # Use spaCy NER
                doc = self.entity_extractor(content)
                for ent in doc.ents:
                    entity_type = self._map_spacy_to_entity_type(ent.label_)
                    entities.append({
                        'name': ent.text,
                        'type': entity_type,
                        'start': ent.start_char,
                        'end': ent.end_char,
                        'confidence': 0.8  # spaCy doesn't provide confidence scores
                    })
            else:
                # Simple pattern matching fallback
                # Extract capitalized words as potential entities
                import re
                pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
                for match in re.finditer(pattern, content):
                    entities.append({
                        'name': match.group(),
                        'type': 'other',
                        'start': match.start(),
                        'end': match.end(),
                        'confidence': 0.5
                    })

        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")

        return entities

    def _map_spacy_to_entity_type(self, spacy_label: str) -> str:
        """Map spaCy entity labels to our entity types."""
        mapping = {
            'PERSON': 'person',
            'ORG': 'organization',
            'GPE': 'location',
            'LOC': 'location',
            'EVENT': 'event',
            'PRODUCT': 'product',
            'WORK_OF_ART': 'concept',
            'LAW': 'concept',
            'LANGUAGE': 'technology',
            'DATE': 'event',
            'TIME': 'event',
            'MONEY': 'concept',
            'QUANTITY': 'concept',
            'CARDINAL': 'concept',
            'ORDINAL': 'concept',
            'PERCENT': 'concept'
        }
        return mapping.get(spacy_label, 'other')

    async def _infer_relationships(self, entities: list[dict[str, Any]], content: str) -> list[dict[str, Any]]:
        """Infer relationships between entities based on context."""
        relationships = []

        # Simple co-occurrence based relationships
        for i, entity1 in enumerate(entities):
            for j, entity2 in enumerate(entities):
                if i >= j:  # Avoid duplicates and self-relationships
                    continue

                # Calculate distance between entities
                distance = abs(entity1['start'] - entity2['start'])

                # If entities are close in text, they're likely related
                if distance < 200:  # Within ~200 characters
                    strength = 1.0 - (distance / 200.0)  # Closer = stronger

                    # Determine relationship type based on entity types
                    rel_type = self._determine_relationship_type(
                        entity1['type'], entity2['type'], content[entity1['start']:entity2['end']]
                    )

                    relationships.append({
                        'from_entity': entity1['name'],
                        'to_entity': entity2['name'],
                        'type': rel_type,
                        'strength': strength,
                        'confidence': min(entity1['confidence'], entity2['confidence'])
                    })

        return relationships

    def _determine_relationship_type(self, type1: str, type2: str, context: str) -> str:
        """Determine relationship type based on entity types and context."""
        # Simple heuristics for relationship type
        context_lower = context.lower()

        if 'work' in context_lower or 'employ' in context_lower:
            return 'works_at'
        elif 'develop' in context_lower or 'create' in context_lower or 'build' in context_lower:
            return 'develops'
        elif 'lead' in context_lower or 'manage' in context_lower:
            return 'leads'
        elif 'use' in context_lower or 'utilize' in context_lower:
            return 'uses'
        elif type1 == 'person' and type2 == 'organization':
            return 'affiliated_with'
        elif type1 == 'person' and type2 == 'location':
            return 'located_at'
        else:
            return 'relates_to'  # Default relationship

    async def store(self, content: str, embedding: list[float], metadata: dict[str, Any]) -> UUID:
        """
        Store memory and extract knowledge graph components.

        This method:
        1. Stores the memory normally (delegated to pgvector)
        2. Extracts entities from the content
        3. Creates graph nodes for entities
        4. Infers and creates relationships
        """
        # Ensure pool is initialized
        await self._ensure_pool()

        if not self.connection_pool:
            raise RuntimeError("Graph provider not initialized")

        memory_id = uuid4()

        async with self.connection_pool.acquire() as conn:
            try:
                # Extract entities from content
                entities = await self._extract_entities(content)

                # Get embedding model
                embedding_model = await self._get_or_create_embedding_model()

                # Store entities as graph nodes
                entity_ids = {}
                for entity in entities:
                    # Generate entity embedding if model available
                    entity_embedding = None
                    if embedding_model:
                        entity_embedding = embedding_model.encode(entity['name']).tolist()

                    # Check if entity already exists
                    existing = await conn.fetchrow("""
                        SELECT id, mention_count FROM graph_nodes
                        WHERE entity_name = $1 AND entity_type = $2
                    """, entity['name'], entity['type'])

                    if existing:
                        # Update existing entity
                        entity_id = existing['id']
                        await conn.execute("""
                            UPDATE graph_nodes
                            SET mention_count = mention_count + 1,
                                last_seen = NOW(),
                                importance_score = LEAST(importance_score + 0.1, 1.0)
                            WHERE id = $1
                        """, entity_id)
                    else:
                        # Create new entity
                        entity_id = uuid4()
                        embedding_str = '[' + ','.join(map(str, entity_embedding)) + ']' if entity_embedding else None

                        await conn.execute("""
                            INSERT INTO graph_nodes
                            (id, entity_type, entity_name, embedding, importance_score)
                            VALUES ($1, $2, $3, $4::vector, $5)
                        """, entity_id, entity['type'], entity['name'],
                            embedding_str, metadata.get('importance_score', 0.5))

                    entity_ids[entity['name']] = entity_id

                    # Link entity to memory
                    await conn.execute("""
                        INSERT INTO memory_entity_map (memory_id, entity_id)
                        VALUES ($1, $2)
                        ON CONFLICT DO NOTHING
                    """, memory_id, entity_id)

                # Infer and store relationships
                relationships = await self._infer_relationships(entities, content)

                for rel in relationships:
                    if rel['from_entity'] in entity_ids and rel['to_entity'] in entity_ids:
                        # Calculate ADM score for relationship
                        rel['strength'] * rel['confidence'] * metadata.get('importance_score', 0.5)

                        await conn.execute("""
                            INSERT INTO graph_relationships
                            (from_node_id, to_node_id, relationship_type, strength, confidence, adm_score, metadata)
                            VALUES ($1, $2, $3, $4, $5, $6, $7)
                            ON CONFLICT (from_node_id, to_node_id, relationship_type) DO UPDATE SET
                                occurrence_count = graph_relationships.occurrence_count + 1,
                                strength = GREATEST(graph_relationships.strength, EXCLUDED.strength),
                                last_seen = NOW()
                        """, entity_ids[rel['from_entity']], entity_ids[rel['to_entity']],
                            rel['type'], rel['strength'], rel['confidence'],
                            {'context': content[entities[0]['start']:entities[-1]['end']][:200]})

                logger.info(f"Stored memory {memory_id} with {len(entities)} entities and {len(relationships)} relationships")

            except Exception as e:
                logger.error(f"Failed to process graph data: {e}")
                # Don't fail the whole operation if graph processing fails

        return memory_id

    async def query(self, query_embedding: list[float], limit: int, filters: dict[str, Any]) -> list[MemoryResponse]:
        """
        Query memories using graph relationships.

        This enhanced query can:
        1. Find memories by entity relationships
        2. Traverse the graph to find related memories
        3. Use graph structure to improve relevance
        """
        # Ensure pool is initialized
        await self._ensure_pool()

        if not self.connection_pool:
            return []

        memories = []

        async with self.connection_pool.acquire() as conn:
            try:
                # If entity_name filter is provided, use graph traversal
                if filters.get('entity_name'):
                    entity_name = filters['entity_name']

                    # Find memories connected to this entity through the graph
                    rows = await conn.fetch("""
                        WITH entity_memories AS (
                            SELECT DISTINCT mem.memory_id, gr.strength as relationship_strength
                            FROM graph_nodes gn
                            JOIN memory_entity_map mem ON gn.id = mem.entity_id
                            LEFT JOIN graph_relationships gr ON (gn.id = gr.from_node_id OR gn.id = gr.to_node_id)
                            WHERE gn.entity_name = $1
                        )
                        SELECT
                            vm.id,
                            vm.content,
                            vm.metadata,
                            vm.importance_score,
                            em.relationship_strength,
                            vm.created_at
                        FROM entity_memories em
                        JOIN vector_memories vm ON em.memory_id = vm.id
                        ORDER BY em.relationship_strength DESC NULLS LAST
                        LIMIT $2
                    """, entity_name, limit)

                    for row in rows:
                        memories.append(MemoryResponse(
                            id=row['id'],
                            content=row['content'],
                            metadata=dict(row['metadata']) if row['metadata'] else {},
                            importance_score=float(row['importance_score']),
                            similarity_score=float(row['relationship_strength']),
                            created_at=row['created_at']
                        ))

            except Exception as e:
                logger.error(f"Graph query failed: {e}")

        return memories

    async def get_relationships(self, node_id: UUID) -> list[dict[str, Any]]:
        """Get all relationships for a specific node."""
        # Ensure pool is initialized
        await self._ensure_pool()

        if not self.connection_pool:
            return []

        relationships = []

        async with self.connection_pool.acquire() as conn:
            try:
                rows = await conn.fetch("""
                    SELECT
                        gr.*,
                        gn_from.entity_name as from_name,
                        gn_from.entity_type as from_type,
                        gn_to.entity_name as to_name,
                        gn_to.entity_type as to_type
                    FROM graph_relationships gr
                    JOIN graph_nodes gn_from ON gr.from_node_id = gn_from.id
                    JOIN graph_nodes gn_to ON gr.to_node_id = gn_to.id
                    WHERE gr.from_node_id = $1 OR gr.to_node_id = $1
                    ORDER BY gr.strength DESC
                """, node_id)

                for row in rows:
                    relationships.append({
                        'id': row['id'],
                        'from_node': {
                            'id': row['from_node_id'],
                            'name': row['from_name'],
                            'type': row['from_type']
                        },
                        'to_node': {
                            'id': row['to_node_id'],
                            'name': row['to_name'],
                            'type': row['to_type']
                        },
                        'type': row['relationship_type'],
                        'strength': float(row['strength']),
                        'confidence': float(row['confidence']),
                        'occurrences': row['occurrence_count']
                    })

            except Exception as e:
                logger.error(f"Failed to get relationships: {e}")

        return relationships

    async def health_check(self) -> dict[str, Any]:
        """Check health of the graph provider."""
        # Ensure pool is initialized
        await self._ensure_pool()

        if not self.connection_pool:
            return {
                'status': 'unhealthy',
                'error': 'Connection pool not initialized',
                'details': {}
            }

        try:
            async with self.connection_pool.acquire() as conn:
                # Check database connection
                await conn.fetchval("SELECT 1")

                # Get graph statistics
                node_count = await conn.fetchval("SELECT COUNT(*) FROM graph_nodes")
                relationship_count = await conn.fetchval("SELECT COUNT(*) FROM graph_relationships")

                return {
                    'status': 'healthy',
                    'details': {
                        'connection': 'active',
                        'graph_nodes': node_count,
                        'graph_relationships': relationship_count,
                        'entity_extractor': 'spacy' if self.entity_extractor and self.entity_extractor != 'simple' else 'regex'
                    }
                }
        except Exception as e:
            logger.error(f"Graph health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'details': {}
            }

    async def get_stats(self) -> dict[str, Any]:
        """Get statistics for the graph provider."""
        # Ensure pool is initialized
        await self._ensure_pool()

        if not self.connection_pool:
            return {'error': 'Provider not initialized'}

        try:
            async with self.connection_pool.acquire() as conn:
                stats = await conn.fetchrow("""
                    SELECT
                        (SELECT COUNT(*) FROM graph_nodes) as total_nodes,
                        (SELECT COUNT(*) FROM graph_relationships) as total_relationships,
                        (SELECT COUNT(DISTINCT entity_type) FROM graph_nodes) as entity_types,
                        (SELECT COUNT(DISTINCT relationship_type) FROM graph_relationships) as relationship_types,
                        (SELECT AVG(mention_count) FROM graph_nodes) as avg_mentions_per_entity,
                        (SELECT AVG(occurrence_count) FROM graph_relationships) as avg_occurrences_per_relationship
                """)

                return {
                    'total_nodes': stats['total_nodes'],
                    'total_relationships': stats['total_relationships'],
                    'entity_types': stats['entity_types'],
                    'relationship_types': stats['relationship_types'],
                    'avg_mentions_per_entity': float(stats['avg_mentions_per_entity'] or 0),
                    'avg_occurrences_per_relationship': float(stats['avg_occurrences_per_relationship'] or 0)
                }
        except Exception as e:
            logger.error(f"Failed to get graph stats: {e}")
            return {'error': str(e)}
