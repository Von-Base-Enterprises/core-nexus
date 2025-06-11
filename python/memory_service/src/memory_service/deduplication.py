"""
Enterprise-Grade Deduplication Service

Implements a 3-tier deduplication pipeline:
1. Content Hash Matching (SHA-256)
2. Vector Similarity Search
3. Business Rule Application
"""

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from .models import MemoryResponse

logger = logging.getLogger(__name__)


class DeduplicationMode(Enum):
    """Deduplication operational modes."""
    OFF = "off"
    LOG_ONLY = "log_only"
    ACTIVE = "active"


class DeduplicationDecision(Enum):
    """Possible deduplication decisions."""
    DUPLICATE = "duplicate"
    UNIQUE = "unique"
    REVIEW_NEEDED = "review_needed"


@dataclass
class DeduplicationResult:
    """Result of deduplication check."""
    is_duplicate: bool
    existing_memory: Optional[MemoryResponse] = None
    confidence_score: float = 0.0
    decision: DeduplicationDecision = DeduplicationDecision.UNIQUE
    reason: str = ""
    content_hash: Optional[str] = None
    similarity_score: Optional[float] = None


class DeduplicationService:
    """
    Enterprise deduplication service with multi-stage detection.
    
    Features:
    - SHA-256 content hashing for exact matches
    - Vector similarity for semantic duplicates
    - Configurable business rules
    - Performance metrics and monitoring
    - Audit trail for all decisions
    """
    
    def __init__(self, 
                 vector_store,
                 mode: DeduplicationMode = DeduplicationMode.ACTIVE,
                 similarity_threshold: float = 0.95,
                 exact_match_only: bool = False):
        """
        Initialize deduplication service.
        
        Args:
            vector_store: UnifiedVectorStore instance
            mode: Operational mode (off, log_only, active)
            similarity_threshold: Threshold for semantic similarity (0.0-1.0)
            exact_match_only: If True, only use content hash matching
        """
        self.vector_store = vector_store
        self.mode = mode
        self.similarity_threshold = similarity_threshold
        self.exact_match_only = exact_match_only
        self.connection_pool = None
        
        # Metrics
        self.metrics = {
            'total_checks': 0,
            'exact_matches': 0,
            'semantic_matches': 0,
            'unique_contents': 0,
            'false_positives': 0,
            'processing_time_ms': []
        }
        
        logger.info(f"Initialized DeduplicationService in {mode.value} mode")
    
    async def _ensure_pool(self):
        """Ensure database connection pool is available."""
        if not self.connection_pool:
            # Get pgvector provider's pool
            pgvector = self.vector_store.providers.get('pgvector')
            if pgvector and hasattr(pgvector, 'connection_pool'):
                self.connection_pool = pgvector.connection_pool
            else:
                raise RuntimeError("PgVector connection pool not available for deduplication")
    
    def _hash_content(self, content: str) -> str:
        """Generate SHA-256 hash of content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    async def check_duplicate(self, content: str, metadata: Optional[dict] = None) -> DeduplicationResult:
        """
        Check if content is a duplicate using multi-stage pipeline.
        
        Args:
            content: Memory content to check
            metadata: Optional metadata for business rules
            
        Returns:
            DeduplicationResult with decision and details
        """
        start_time = time.time()
        self.metrics['total_checks'] += 1
        
        # Mode check
        if self.mode == DeduplicationMode.OFF:
            return DeduplicationResult(is_duplicate=False, reason="Deduplication disabled")
        
        try:
            await self._ensure_pool()
            
            # Stage 1: Content Hash Check
            content_hash = self._hash_content(content)
            exact_match = await self._check_exact_match(content_hash)
            
            if exact_match:
                self.metrics['exact_matches'] += 1
                result = DeduplicationResult(
                    is_duplicate=True,
                    existing_memory=exact_match,
                    confidence_score=1.0,
                    decision=DeduplicationDecision.DUPLICATE,
                    reason="Exact content match (SHA-256)",
                    content_hash=content_hash
                )
                
                # Record decision
                if self.mode == DeduplicationMode.ACTIVE:
                    await self._record_decision(None, exact_match.id, result)
                
                return result
            
            # Stage 2: Vector Similarity Check (if not exact-match-only mode)
            if not self.exact_match_only:
                semantic_match = await self._check_semantic_similarity(content)
                
                if semantic_match and semantic_match.similarity_score >= self.similarity_threshold:
                    self.metrics['semantic_matches'] += 1
                    
                    # Stage 3: Apply Business Rules
                    decision = await self._apply_business_rules(
                        content, semantic_match, metadata
                    )
                    
                    result = DeduplicationResult(
                        is_duplicate=decision == DeduplicationDecision.DUPLICATE,
                        existing_memory=semantic_match if decision == DeduplicationDecision.DUPLICATE else None,
                        confidence_score=semantic_match.similarity_score,
                        decision=decision,
                        reason=f"Semantic similarity: {semantic_match.similarity_score:.3f}",
                        content_hash=content_hash,
                        similarity_score=semantic_match.similarity_score
                    )
                    
                    # Record decision
                    if self.mode == DeduplicationMode.ACTIVE:
                        await self._record_decision(None, semantic_match.id, result)
                    
                    return result
            
            # No duplicates found
            self.metrics['unique_contents'] += 1
            return DeduplicationResult(
                is_duplicate=False,
                confidence_score=1.0,
                decision=DeduplicationDecision.UNIQUE,
                reason="No duplicates found",
                content_hash=content_hash
            )
            
        except Exception as e:
            logger.error(f"Deduplication check failed: {e}")
            # Fail open - don't block on dedup errors
            return DeduplicationResult(
                is_duplicate=False,
                reason=f"Deduplication error: {str(e)}"
            )
        finally:
            # Record processing time
            processing_time = (time.time() - start_time) * 1000
            self.metrics['processing_time_ms'].append(processing_time)
            
            # Keep only last 1000 measurements
            if len(self.metrics['processing_time_ms']) > 1000:
                self.metrics['processing_time_ms'] = self.metrics['processing_time_ms'][-1000:]
    
    async def _check_exact_match(self, content_hash: str) -> Optional[MemoryResponse]:
        """Check for exact content match using hash."""
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT vm.* 
                FROM memory_content_hashes mch
                JOIN vector_memories vm ON mch.memory_id = vm.id
                WHERE mch.content_hash = $1
                ORDER BY vm.created_at DESC
                LIMIT 1
            """, content_hash)
            
            if row:
                return MemoryResponse(
                    id=row['id'],
                    content=row['content'],
                    metadata=dict(row['metadata']) if row['metadata'] else {},
                    importance_score=float(row['importance_score']),
                    created_at=row['created_at'].isoformat() if row['created_at'] else ''
                )
            
            return None
    
    async def _check_semantic_similarity(self, content: str) -> Optional[MemoryResponse]:
        """Check for semantic duplicates using vector similarity."""
        # Generate embedding for content
        if not self.vector_store.embedding_model:
            return None
            
        try:
            embedding = await self.vector_store.embedding_model.embed_text(content)
            
            # Query for similar memories
            pgvector = self.vector_store.providers.get('pgvector')
            if not pgvector:
                return None
                
            similar_memories = await pgvector.query(
                query_embedding=embedding,
                limit=1,
                filters={}
            )
            
            if similar_memories and similar_memories[0].similarity_score >= self.similarity_threshold:
                return similar_memories[0]
                
        except Exception as e:
            logger.error(f"Semantic similarity check failed: {e}")
            
        return None
    
    async def _apply_business_rules(self, 
                                   content: str,
                                   existing_memory: MemoryResponse,
                                   metadata: Optional[dict]) -> DeduplicationDecision:
        """
        Apply business rules to determine final decision.
        
        Rules:
        1. If importance score differs significantly, keep both
        2. If user_id is different, keep both (user-specific memories)
        3. If conversation_id differs, consider context
        4. Time-based rules (e.g., keep if >30 days old)
        """
        # Rule 1: Importance score difference
        if metadata and 'importance_score' in metadata:
            score_diff = abs(metadata['importance_score'] - existing_memory.importance_score)
            if score_diff > 0.3:
                return DeduplicationDecision.UNIQUE
        
        # Rule 2: User-specific memories
        if metadata and existing_memory.metadata:
            new_user = metadata.get('user_id')
            existing_user = existing_memory.metadata.get('user_id')
            if new_user and existing_user and new_user != existing_user:
                return DeduplicationDecision.UNIQUE
        
        # Rule 3: Time-based rule
        if existing_memory.created_at:
            from datetime import datetime, timedelta
            created_at = datetime.fromisoformat(existing_memory.created_at.replace('Z', '+00:00'))
            if datetime.now().astimezone() - created_at > timedelta(days=30):
                return DeduplicationDecision.REVIEW_NEEDED
        
        # Default: Mark as duplicate if similarity is high enough
        return DeduplicationDecision.DUPLICATE
    
    async def _record_decision(self, 
                              candidate_id: Optional[UUID],
                              existing_id: UUID,
                              result: DeduplicationResult):
        """Record deduplication decision for audit trail."""
        if not self.connection_pool:
            return
            
        try:
            async with self.connection_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO deduplication_reviews
                    (candidate_id, existing_id, similarity_score, content_hash_match,
                     vector_similarity_score, decision, decision_reason, auto_decision)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (candidate_id, existing_id) DO UPDATE
                    SET similarity_score = EXCLUDED.similarity_score,
                        decision = EXCLUDED.decision,
                        reviewed_at = NOW()
                """, 
                candidate_id, existing_id, 
                result.confidence_score,
                result.content_hash is not None,
                result.similarity_score,
                result.decision.value,
                result.reason,
                True  # auto_decision
                )
                
                # Record metric
                await conn.execute("""
                    INSERT INTO deduplication_metrics
                    (metric_type, metric_value, metric_metadata)
                    VALUES ($1, $2, $3)
                """,
                'dedup_decision',
                1.0,
                {
                    'decision': result.decision.value,
                    'confidence': result.confidence_score,
                    'mode': self.mode.value
                })
                
        except Exception as e:
            logger.error(f"Failed to record deduplication decision: {e}")
    
    async def mark_false_positive(self, memory_id: UUID, actual_unique_id: UUID):
        """Mark a deduplication decision as false positive."""
        self.metrics['false_positives'] += 1
        
        try:
            await self._ensure_pool()
            async with self.connection_pool.acquire() as conn:
                await conn.execute("""
                    UPDATE deduplication_reviews
                    SET decision = 'unique',
                        decision_reason = 'Marked as false positive by user',
                        auto_decision = FALSE,
                        reviewed_by = 'user',
                        reviewed_at = NOW()
                    WHERE candidate_id = $1 AND existing_id = $2
                """, memory_id, actual_unique_id)
                
        except Exception as e:
            logger.error(f"Failed to mark false positive: {e}")
    
    async def get_stats(self) -> dict[str, Any]:
        """Get deduplication statistics."""
        stats = {
            'mode': self.mode.value,
            'similarity_threshold': self.similarity_threshold,
            'metrics': {
                'total_checks': self.metrics['total_checks'],
                'exact_matches': self.metrics['exact_matches'],
                'semantic_matches': self.metrics['semantic_matches'],
                'unique_contents': self.metrics['unique_contents'],
                'false_positives': self.metrics['false_positives'],
                'avg_processing_time_ms': (
                    sum(self.metrics['processing_time_ms']) / len(self.metrics['processing_time_ms'])
                    if self.metrics['processing_time_ms'] else 0
                )
            }
        }
        
        # Get database stats
        try:
            await self._ensure_pool()
            async with self.connection_pool.acquire() as conn:
                db_stats = await conn.fetchrow("""
                    SELECT * FROM deduplication_stats
                """)
                
                if db_stats:
                    stats['database_stats'] = dict(db_stats)
                    
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            
        return stats
    
    async def cleanup_old_hashes(self, days: int = 90):
        """Clean up old content hashes for deleted memories."""
        try:
            await self._ensure_pool()
            async with self.connection_pool.acquire() as conn:
                deleted = await conn.fetchval("""
                    DELETE FROM memory_content_hashes
                    WHERE memory_id NOT IN (SELECT id FROM vector_memories)
                    AND created_at < NOW() - INTERVAL '%s days'
                    RETURNING COUNT(*)
                """, days)
                
                logger.info(f"Cleaned up {deleted} orphaned content hashes")
                return deleted
                
        except Exception as e:
            logger.error(f"Failed to cleanup old hashes: {e}")
            return 0