"""
Emergency Search Fix Module

This module provides fallback search mechanisms to ensure users can always find their memories.
"""

import logging
import asyncio
from typing import Any, Optional
from uuid import UUID

from .models import MemoryResponse

logger = logging.getLogger(__name__)


class EmergencySearchFix:
    """
    Emergency search fix to ensure 100% search reliability.
    
    Implements multiple fallback strategies:
    1. Direct table scan without vector similarity
    2. Full-text search on content
    3. Metadata search
    4. AI-powered semantic search (if needed)
    """
    
    def __init__(self, connection_pool):
        self.connection_pool = connection_pool
    
    async def emergency_search_all(self, limit: int = 1000) -> list[MemoryResponse]:
        """
        Emergency method to retrieve ALL memories without any filtering.
        This ensures users can see their data.
        """
        try:
            async with self.connection_pool.acquire() as conn:
                # Direct query without vector operations
                rows = await conn.fetch("""
                    SELECT 
                        id, 
                        content, 
                        metadata, 
                        importance_score,
                        created_at
                    FROM vector_memories
                    ORDER BY created_at DESC
                    LIMIT $1
                """, limit)
                
                memories = []
                for row in rows:
                    memory = MemoryResponse(
                        id=row['id'],
                        content=row['content'],
                        metadata=dict(row['metadata']) if row['metadata'] else {},
                        embedding=[],
                        importance_score=float(row['importance_score'] or 0.5),
                        similarity_score=1.0,  # Default high score
                        created_at=row['created_at'].isoformat() if row['created_at'] else ''
                    )
                    memories.append(memory)
                
                logger.info(f"Emergency search retrieved {len(memories)} memories")
                return memories
                
        except Exception as e:
            logger.error(f"Emergency search failed: {e}")
            return []
    
    async def text_search(self, query: str, limit: int = 100) -> list[MemoryResponse]:
        """
        Full-text search fallback using PostgreSQL text search.
        """
        try:
            async with self.connection_pool.acquire() as conn:
                # Use PostgreSQL full-text search
                rows = await conn.fetch("""
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
                    FROM vector_memories
                    WHERE to_tsvector('english', content) @@ plainto_tsquery('english', $1)
                    ORDER BY rank DESC, created_at DESC
                    LIMIT $2
                """, query, limit)
                
                memories = []
                for row in rows:
                    memory = MemoryResponse(
                        id=row['id'],
                        content=row['content'],
                        metadata=dict(row['metadata']) if row['metadata'] else {},
                        embedding=[],
                        importance_score=float(row['importance_score'] or 0.5),
                        similarity_score=float(row['rank']) if row['rank'] else 0.5,
                        created_at=row['created_at'].isoformat() if row['created_at'] else ''
                    )
                    memories.append(memory)
                
                logger.info(f"Text search found {len(memories)} memories for query: {query}")
                return memories
                
        except Exception as e:
            logger.error(f"Text search failed: {e}")
            return []
    
    async def fuzzy_search(self, query: str, limit: int = 100) -> list[MemoryResponse]:
        """
        Fuzzy search using ILIKE for partial matches.
        """
        try:
            async with self.connection_pool.acquire() as conn:
                # Split query into words for better matching
                words = query.lower().split()
                
                # Build ILIKE conditions
                conditions = []
                for word in words[:5]:  # Limit to first 5 words
                    conditions.append(f"LOWER(content) LIKE '%{word}%'")
                
                where_clause = " OR ".join(conditions) if conditions else "TRUE"
                
                rows = await conn.fetch(f"""
                    SELECT 
                        id,
                        content,
                        metadata,
                        importance_score,
                        created_at
                    FROM vector_memories
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
                        metadata=dict(row['metadata']) if row['metadata'] else {},
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
                
        except Exception as e:
            logger.error(f"Fuzzy search failed: {e}")
            return []
    
    async def ensure_all_memories_visible(self) -> dict[str, Any]:
        """
        Diagnostic method to ensure all memories are accessible.
        """
        try:
            async with self.connection_pool.acquire() as conn:
                # Count total memories
                total_count = await conn.fetchval("SELECT COUNT(*) FROM vector_memories")
                
                # Count memories with embeddings
                with_embeddings = await conn.fetchval(
                    "SELECT COUNT(*) FROM vector_memories WHERE embedding IS NOT NULL"
                )
                
                # Count memories without embeddings
                without_embeddings = total_count - with_embeddings
                
                # Get sample of memories without embeddings
                missing_samples = await conn.fetch("""
                    SELECT id, SUBSTRING(content, 1, 100) as content_preview
                    FROM vector_memories
                    WHERE embedding IS NULL
                    LIMIT 5
                """)
                
                return {
                    "total_memories": total_count,
                    "with_embeddings": with_embeddings,
                    "without_embeddings": without_embeddings,
                    "missing_embedding_samples": [
                        {"id": str(row['id']), "preview": row['content_preview']}
                        for row in missing_samples
                    ]
                }
                
        except Exception as e:
            logger.error(f"Diagnostic check failed: {e}")
            return {"error": str(e)}