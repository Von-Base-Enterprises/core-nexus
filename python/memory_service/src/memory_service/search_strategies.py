"""
Search Strategies Module

Consolidates all search approaches into a clean interface.
Replaces emergency search_fix.py with proper abstractions.
"""

import logging
from typing import Any, Optional, List
from abc import ABC, abstractmethod

from .models import MemoryResponse

logger = logging.getLogger(__name__)


class SearchStrategy(ABC):
    """Abstract base class for search strategies"""
    
    @abstractmethod
    async def search(self, query: str, limit: int, filters: dict[str, Any]) -> List[MemoryResponse]:
        """Execute search with given parameters"""
        pass


class VectorSearchStrategy(SearchStrategy):
    """Vector similarity search using embeddings"""
    
    def __init__(self, provider, embedding_model):
        self.provider = provider
        self.embedding_model = embedding_model
    
    async def search(self, query: str, limit: int, filters: dict[str, Any]) -> List[MemoryResponse]:
        """Execute vector similarity search"""
        if not query:
            raise ValueError("Vector search requires a query")
        
        # Generate embedding
        query_embedding = await self.embedding_model.embed_text(query)
        
        # Execute search
        return await self.provider.query(query_embedding, limit, filters)


class RecentMemoriesStrategy(SearchStrategy):
    """Get recent memories without vector search"""
    
    def __init__(self, provider):
        self.provider = provider
    
    async def search(self, query: str, limit: int, filters: dict[str, Any]) -> List[MemoryResponse]:
        """Get recent memories ordered by creation date"""
        # Ignore query for recent memories
        return await self.provider.get_recent_memories(limit, filters)


class TextSearchStrategy(SearchStrategy):
    """PostgreSQL full-text search"""
    
    def __init__(self, connection_pool, table_name='vector_memories'):
        self.connection_pool = connection_pool
        self.table_name = table_name
    
    async def search(self, query: str, limit: int, filters: dict[str, Any]) -> List[MemoryResponse]:
        """Execute PostgreSQL full-text search"""
        if not query:
            raise ValueError("Text search requires a query")
        
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch(f"""
                SELECT 
                    id,
                    content,
                    metadata,
                    importance_score,
                    created_at,
                    ts_rank_cd(
                        to_tsvector('english', content),
                        plainto_tsquery('english', $1)
                    ) as rank
                FROM {self.table_name}
                WHERE to_tsvector('english', content) @@ plainto_tsquery('english', $1)
                ORDER BY rank DESC, created_at DESC
                LIMIT $2
            """, query, limit)
            
            memories = []
            for row in rows:
                memory = MemoryResponse(
                    id=row['id'],
                    content=row['content'],
                    metadata=row['metadata'] if isinstance(row['metadata'], dict) else {},
                    embedding=[],
                    importance_score=float(row['importance_score'] or 0.5),
                    similarity_score=float(row['rank']) if row['rank'] else 0.5,
                    created_at=row['created_at'].isoformat() if row['created_at'] else ''
                )
                memories.append(memory)
            
            logger.info(f"Text search found {len(memories)} memories for query: {query}")
            return memories


class FuzzySearchStrategy(SearchStrategy):
    """Fuzzy search using ILIKE for partial matches"""
    
    def __init__(self, connection_pool, table_name='vector_memories'):
        self.connection_pool = connection_pool
        self.table_name = table_name
    
    async def search(self, query: str, limit: int, filters: dict[str, Any]) -> List[MemoryResponse]:
        """Execute fuzzy search with ILIKE"""
        if not query:
            raise ValueError("Fuzzy search requires a query")
        
        async with self.connection_pool.acquire() as conn:
            # Split query into words for better matching
            words = query.lower().split()[:5]  # Limit to first 5 words
            
            # Build ILIKE conditions
            conditions = [f"LOWER(content) LIKE '%{word}%'" for word in words]
            where_clause = " OR ".join(conditions) if conditions else "TRUE"
            
            rows = await conn.fetch(f"""
                SELECT 
                    id,
                    content,
                    metadata,
                    importance_score,
                    created_at
                FROM {self.table_name}
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT $1
            """, limit)
            
            memories = []
            for row in rows:
                # Calculate simple relevance score
                content_lower = row['content'].lower()
                match_count = sum(1 for word in words if word in content_lower)
                relevance = match_count / max(len(words), 1)
                
                memory = MemoryResponse(
                    id=row['id'],
                    content=row['content'],
                    metadata=row['metadata'] if isinstance(row['metadata'], dict) else {},
                    embedding=[],
                    importance_score=float(row['importance_score'] or 0.5),
                    similarity_score=relevance,
                    created_at=row['created_at'].isoformat() if row['created_at'] else ''
                )
                memories.append(memory)
            
            # Sort by relevance
            memories.sort(key=lambda m: m.similarity_score, reverse=True)
            
            logger.info(f"Fuzzy search found {len(memories)} memories")
            return memories


class SearchStrategyManager:
    """Manages search strategy selection and fallback"""
    
    def __init__(self, providers, embedding_model=None):
        self.providers = providers
        self.embedding_model = embedding_model
        self.strategies = {}
        
        # Initialize available strategies
        pgvector = providers.get('pgvector')
        if pgvector and pgvector.enabled:
            self.strategies['vector'] = VectorSearchStrategy(pgvector, embedding_model)
            self.strategies['recent'] = RecentMemoriesStrategy(pgvector)
            
            if hasattr(pgvector, 'connection_pool'):
                self.strategies['text'] = TextSearchStrategy(pgvector.connection_pool)
                self.strategies['fuzzy'] = FuzzySearchStrategy(pgvector.connection_pool)
    
    async def search(self, strategy_name: str, query: str, limit: int, filters: dict[str, Any]) -> List[MemoryResponse]:
        """Execute search with specified strategy"""
        strategy = self.strategies.get(strategy_name)
        if not strategy:
            raise ValueError(f"Search strategy '{strategy_name}' not available")
        
        return await strategy.search(query, limit, filters)
    
    async def search_with_fallback(self, query: str, limit: int, filters: dict[str, Any]) -> List[MemoryResponse]:
        """Try multiple search strategies with fallback"""
        strategies_to_try = []
        
        if query:
            # For queries, try vector first, then text, then fuzzy
            strategies_to_try = ['vector', 'text', 'fuzzy']
        else:
            # For empty queries, use recent memories
            strategies_to_try = ['recent']
        
        last_error = None
        for strategy_name in strategies_to_try:
            if strategy_name in self.strategies:
                try:
                    results = await self.search(strategy_name, query, limit, filters)
                    if results:
                        logger.info(f"Search successful with {strategy_name} strategy")
                        return results
                except Exception as e:
                    logger.warning(f"{strategy_name} search failed: {e}")
                    last_error = e
        
        # If all strategies fail, return empty list
        logger.error(f"All search strategies failed. Last error: {last_error}")
        return []