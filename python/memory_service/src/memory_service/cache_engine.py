"""
Multi-Tier Cache Engine for Core Nexus Memory Service

Implements intelligent caching with embedding cache, query result cache,
and semantic similarity clustering optimized for 1GB RAM deployment.
"""

import asyncio
import hashlib
import json
import logging
import pickle
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID

import numpy as np

from .config import config
from .models import QueryRequest, QueryResponse, MemoryResponse

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a cache entry with metadata"""
    key: str
    value: Any
    created_at: float
    last_accessed: float
    access_count: int
    size_bytes: int
    ttl: Optional[float] = None
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl
    
    def touch(self):
        """Update last accessed time and increment access count"""
        self.last_accessed = time.time()
        self.access_count += 1


@dataclass
class CacheStats:
    """Cache performance statistics"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size_bytes: int = 0
    entry_count: int = 0
    avg_access_time_ms: float = 0.0
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class CacheBackend(ABC):
    """Abstract base class for cache backends"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        pass


class LRUMemoryCache(CacheBackend):
    """High-performance in-memory LRU cache"""
    
    def __init__(self, max_size_mb: int = 100, default_ttl: int = 600):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.stats = CacheStats()
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key not in self.cache:
                self.stats.misses += 1
                return None
            
            entry = self.cache[key]
            
            # Check expiration
            if entry.is_expired():
                del self.cache[key]
                self.stats.misses += 1
                self.stats.evictions += 1
                return None
            
            # Move to end (most recently used)
            entry.touch()
            self.cache.move_to_end(key)
            self.stats.hits += 1
            
            return entry.value
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        async with self._lock:
            try:
                # Estimate size
                size_bytes = self._estimate_size(value)
                
                # Check if we need to evict
                while (self.stats.size_bytes + size_bytes > self.max_size_bytes and 
                       len(self.cache) > 0):
                    self._evict_lru()
                
                # Create cache entry
                entry = CacheEntry(
                    key=key,
                    value=value,
                    created_at=time.time(),
                    last_accessed=time.time(),
                    access_count=1,
                    size_bytes=size_bytes,
                    ttl=ttl or self.default_ttl
                )
                
                # Remove existing entry if present
                if key in self.cache:
                    old_entry = self.cache[key]
                    self.stats.size_bytes -= old_entry.size_bytes
                    self.stats.entry_count -= 1
                
                # Add new entry
                self.cache[key] = entry
                self.stats.size_bytes += size_bytes
                self.stats.entry_count += 1
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to cache entry: {e}")
                return False
    
    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self.cache:
                entry = self.cache[key]
                self.stats.size_bytes -= entry.size_bytes
                self.stats.entry_count -= 1
                del self.cache[key]
                return True
            return False
    
    async def clear(self) -> bool:
        async with self._lock:
            self.cache.clear()
            self.stats = CacheStats()
            return True
    
    def _evict_lru(self):
        """Evict least recently used entry"""
        if not self.cache:
            return
        
        key, entry = self.cache.popitem(last=False)  # Remove from beginning (LRU)
        self.stats.size_bytes -= entry.size_bytes
        self.stats.entry_count -= 1
        self.stats.evictions += 1
    
    def _estimate_size(self, value: Any) -> int:
        """Estimate size of value in bytes"""
        try:
            if isinstance(value, str):
                return len(value.encode('utf-8'))
            elif isinstance(value, (list, dict)):
                return len(pickle.dumps(value))
            elif isinstance(value, np.ndarray):
                return value.nbytes
            else:
                return len(str(value).encode('utf-8'))
        except Exception:
            return 1024  # Default estimate
    
    async def get_stats(self) -> Dict[str, Any]:
        return {
            'backend': 'memory_lru',
            'hit_rate': self.stats.hit_rate,
            'hits': self.stats.hits,
            'misses': self.stats.misses,
            'evictions': self.stats.evictions,
            'size_mb': self.stats.size_bytes / 1024 / 1024,
            'max_size_mb': self.max_size_bytes / 1024 / 1024,
            'entry_count': self.stats.entry_count,
            'utilization': self.stats.size_bytes / self.max_size_bytes
        }


class RedisCache(CacheBackend):
    """Redis distributed cache backend"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", default_ttl: int = 600):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.redis_client = None
        self.stats = CacheStats()
        self._connection_lock = asyncio.Lock()
    
    async def _ensure_connected(self):
        """Ensure Redis connection is established"""
        if self.redis_client is not None:
            return
        
        async with self._connection_lock:
            if self.redis_client is not None:
                return
            
            try:
                import redis.asyncio as redis
                self.redis_client = redis.from_url(self.redis_url, decode_responses=False)
                await self.redis_client.ping()
                logger.info("Redis cache connected successfully")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                self.redis_client = None
    
    async def get(self, key: str) -> Optional[Any]:
        await self._ensure_connected()
        if not self.redis_client:
            self.stats.misses += 1
            return None
        
        try:
            data = await self.redis_client.get(f"nexus:{key}")
            if data is None:
                self.stats.misses += 1
                return None
            
            value = pickle.loads(data)
            self.stats.hits += 1
            return value
            
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")
            self.stats.misses += 1
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        await self._ensure_connected()
        if not self.redis_client:
            return False
        
        try:
            data = pickle.dumps(value)
            await self.redis_client.setex(
                f"nexus:{key}", 
                ttl or self.default_ttl, 
                data
            )
            return True
        except Exception as e:
            logger.warning(f"Redis set failed: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        await self._ensure_connected()
        if not self.redis_client:
            return False
        
        try:
            result = await self.redis_client.delete(f"nexus:{key}")
            return result > 0
        except Exception as e:
            logger.warning(f"Redis delete failed: {e}")
            return False
    
    async def clear(self) -> bool:
        await self._ensure_connected()
        if not self.redis_client:
            return False
        
        try:
            keys = await self.redis_client.keys("nexus:*")
            if keys:
                await self.redis_client.delete(*keys)
            return True
        except Exception as e:
            logger.warning(f"Redis clear failed: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        await self._ensure_connected()
        stats = {
            'backend': 'redis',
            'hit_rate': self.stats.hit_rate,
            'hits': self.stats.hits,
            'misses': self.stats.misses,
            'connected': self.redis_client is not None
        }
        
        if self.redis_client:
            try:
                info = await self.redis_client.info('memory')
                stats.update({
                    'memory_used_mb': info.get('used_memory', 0) / 1024 / 1024,
                    'memory_peak_mb': info.get('used_memory_peak', 0) / 1024 / 1024
                })
            except Exception:
                pass
        
        return stats


class EmbeddingCache:
    """Specialized cache for embeddings with semantic similarity clustering"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.embeddings: Dict[str, np.ndarray] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}
        self.similarity_index: Dict[str, List[str]] = {}  # text_hash -> similar_hashes
        self.access_count: Dict[str, int] = {}
        self.last_accessed: Dict[str, float] = {}
        self._lock = asyncio.Lock()
    
    async def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get cached embedding for text"""
        text_hash = self._hash_text(text)
        
        async with self._lock:
            if text_hash in self.embeddings:
                self.access_count[text_hash] = self.access_count.get(text_hash, 0) + 1
                self.last_accessed[text_hash] = time.time()
                return self.embeddings[text_hash].copy()
            
            # Check for semantically similar cached embeddings
            similar_hash = await self._find_similar_text(text)
            if similar_hash and similar_hash in self.embeddings:
                logger.debug(f"Found similar cached embedding for: {text[:50]}...")
                self.access_count[similar_hash] = self.access_count.get(similar_hash, 0) + 1
                self.last_accessed[similar_hash] = time.time()
                return self.embeddings[similar_hash].copy()
            
            return None
    
    async def set_embedding(self, text: str, embedding: np.ndarray, metadata: Optional[Dict] = None):
        """Cache embedding for text"""
        text_hash = self._hash_text(text)
        
        async with self._lock:
            # Evict if necessary
            while len(self.embeddings) >= self.max_size:
                self._evict_lru()
            
            # Store embedding
            self.embeddings[text_hash] = embedding.copy()
            self.metadata[text_hash] = metadata or {'text': text[:100], 'length': len(text)}
            self.access_count[text_hash] = 1
            self.last_accessed[text_hash] = time.time()
            
            # Update similarity index
            await self._update_similarity_index(text_hash, text)
    
    async def _find_similar_text(self, text: str) -> Optional[str]:
        """Find similar cached text using simple heuristics"""
        # Simple similarity check based on length and word overlap
        words = set(text.lower().split())
        
        for text_hash, meta in self.metadata.items():
            cached_text = meta.get('text', '')
            cached_words = set(cached_text.lower().split())
            
            # Check word overlap
            if len(words & cached_words) / max(len(words), len(cached_words)) > 0.8:
                return text_hash
        
        return None
    
    async def _update_similarity_index(self, text_hash: str, text: str):
        """Update similarity index for fast lookups"""
        # Simple implementation - could be enhanced with more sophisticated similarity
        words = set(text.lower().split())
        
        similar_hashes = []
        for existing_hash, meta in self.metadata.items():
            if existing_hash == text_hash:
                continue
            
            existing_text = meta.get('text', '')
            existing_words = set(existing_text.lower().split())
            
            overlap = len(words & existing_words) / max(len(words), len(existing_words))
            if overlap > 0.7:
                similar_hashes.append(existing_hash)
        
        self.similarity_index[text_hash] = similar_hashes
    
    def _evict_lru(self):
        """Evict least recently used embedding"""
        if not self.embeddings:
            return
        
        # Find LRU entry
        lru_hash = min(self.last_accessed.keys(), key=lambda k: self.last_accessed[k])
        
        # Remove from all structures
        del self.embeddings[lru_hash]
        del self.metadata[lru_hash]
        del self.access_count[lru_hash]
        del self.last_accessed[lru_hash]
        
        if lru_hash in self.similarity_index:
            del self.similarity_index[lru_hash]
    
    def _hash_text(self, text: str) -> str:
        """Generate hash for text"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    async def get_stats(self) -> Dict[str, Any]:
        return {
            'cached_embeddings': len(self.embeddings),
            'max_size': self.max_size,
            'utilization': len(self.embeddings) / self.max_size,
            'total_accesses': sum(self.access_count.values()),
            'similarity_index_size': len(self.similarity_index)
        }


class QueryResultCache:
    """Specialized cache for query results with intelligent invalidation"""
    
    def __init__(self, max_size: int = 500, default_ttl: int = 600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.query_patterns: Dict[str, int] = {}  # Track query patterns
        self._lock = asyncio.Lock()
    
    async def get_query_result(self, request: QueryRequest) -> Optional[QueryResponse]:
        """Get cached query result"""
        cache_key = self._generate_cache_key(request)
        
        async with self._lock:
            if cache_key not in self.cache:
                return None
            
            entry = self.cache[cache_key]
            if entry.is_expired():
                del self.cache[cache_key]
                return None
            
            entry.touch()
            
            # Track query patterns
            pattern = self._extract_query_pattern(request)
            self.query_patterns[pattern] = self.query_patterns.get(pattern, 0) + 1
            
            return entry.value
    
    async def set_query_result(self, request: QueryRequest, response: QueryResponse, ttl: Optional[int] = None):
        """Cache query result"""
        cache_key = self._generate_cache_key(request)
        
        async with self._lock:
            # Evict if necessary
            while len(self.cache) >= self.max_size:
                self._evict_lru()
            
            # Estimate size
            size_bytes = self._estimate_response_size(response)
            
            # Create cache entry
            entry = CacheEntry(
                key=cache_key,
                value=response,
                created_at=time.time(),
                last_accessed=time.time(),
                access_count=1,
                size_bytes=size_bytes,
                ttl=ttl or self.default_ttl
            )
            
            self.cache[cache_key] = entry
    
    def _generate_cache_key(self, request: QueryRequest) -> str:
        """Generate cache key for query request"""
        # Create deterministic key based on query parameters
        key_data = {
            'query': request.query,
            'limit': request.limit,
            'min_similarity': request.min_similarity,
            'filters': sorted(request.filters.items()) if request.filters else None,
            'user_id': request.user_id,
            'conversation_id': request.conversation_id
        }
        
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode('utf-8')).hexdigest()
    
    def _extract_query_pattern(self, request: QueryRequest) -> str:
        """Extract query pattern for analysis"""
        # Simplified pattern extraction
        if not request.query:
            return "empty_query"
        
        word_count = len(request.query.split())
        if word_count <= 3:
            return "short_query"
        elif word_count <= 10:
            return "medium_query"
        else:
            return "long_query"
    
    def _estimate_response_size(self, response: QueryResponse) -> int:
        """Estimate size of query response"""
        try:
            return len(pickle.dumps(response))
        except Exception:
            return len(response.memories) * 1000  # Rough estimate
    
    def _evict_lru(self):
        """Evict least recently used query result"""
        if not self.cache:
            return
        
        lru_key = min(self.cache.keys(), key=lambda k: self.cache[k].last_accessed)
        del self.cache[lru_key]
    
    async def invalidate_user_cache(self, user_id: str):
        """Invalidate cache entries for specific user"""
        async with self._lock:
            keys_to_remove = []
            for key, entry in self.cache.items():
                if hasattr(entry.value, 'user_id') and entry.value.user_id == user_id:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.cache[key]
    
    async def get_stats(self) -> Dict[str, Any]:
        return {
            'cached_queries': len(self.cache),
            'max_size': self.max_size,
            'utilization': len(self.cache) / self.max_size,
            'query_patterns': dict(self.query_patterns),
            'total_pattern_hits': sum(self.query_patterns.values())
        }


class AdvancedCacheEngine:
    """
    Multi-tier cache engine with intelligent caching strategies
    """
    
    def __init__(self):
        # Initialize cache backends
        self.l1_cache = LRUMemoryCache(
            max_size_mb=config.api.CACHE_MAX_SIZE_MB,
            default_ttl=config.api.CACHE_TTL
        )
        
        # Try to initialize Redis for L2 cache
        self.l2_cache = None
        try:
            redis_url = "redis://localhost:6379"  # Could be configured
            self.l2_cache = RedisCache(redis_url, config.api.CACHE_TTL)
        except Exception as e:
            logger.info(f"Redis L2 cache not available: {e}")
        
        # Specialized caches
        self.embedding_cache = EmbeddingCache(config.api.EMBEDDING_CACHE_SIZE)
        self.query_cache = QueryResultCache(
            config.api.QUERY_RESULT_CACHE_SIZE, 
            config.api.CACHE_TTL
        )
        
        # Statistics
        self.cache_operations = 0
        self.start_time = time.time()
    
    async def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get cached embedding with fallback chain"""
        # Try embedding cache first
        embedding = await self.embedding_cache.get_embedding(text)
        if embedding is not None:
            return embedding
        
        # Try L1 cache
        cache_key = f"embedding:{hashlib.md5(text.encode()).hexdigest()}"
        embedding = await self.l1_cache.get(cache_key)
        if embedding is not None:
            # Store in embedding cache for faster future access
            await self.embedding_cache.set_embedding(text, embedding)
            return embedding
        
        # Try L2 cache if available
        if self.l2_cache:
            embedding = await self.l2_cache.get(cache_key)
            if embedding is not None:
                # Populate L1 and embedding cache
                await self.l1_cache.set(cache_key, embedding)
                await self.embedding_cache.set_embedding(text, embedding)
                return embedding
        
        return None
    
    async def set_embedding(self, text: str, embedding: np.ndarray, ttl: Optional[int] = None):
        """Cache embedding across all appropriate tiers"""
        # Store in embedding cache
        await self.embedding_cache.set_embedding(text, embedding)
        
        # Store in L1 cache
        cache_key = f"embedding:{hashlib.md5(text.encode()).hexdigest()}"
        await self.l1_cache.set(cache_key, embedding, ttl)
        
        # Store in L2 cache if available
        if self.l2_cache:
            await self.l2_cache.set(cache_key, embedding, ttl)
    
    async def get_query_result(self, request: QueryRequest) -> Optional[QueryResponse]:
        """Get cached query result"""
        return await self.query_cache.get_query_result(request)
    
    async def set_query_result(self, request: QueryRequest, response: QueryResponse, ttl: Optional[int] = None):
        """Cache query result"""
        await self.query_cache.set_query_result(request, response, ttl)
    
    async def get_generic(self, key: str) -> Optional[Any]:
        """Get generic cached value with fallback chain"""
        # Try L1 first
        value = await self.l1_cache.get(key)
        if value is not None:
            return value
        
        # Try L2 if available
        if self.l2_cache:
            value = await self.l2_cache.get(key)
            if value is not None:
                # Populate L1
                await self.l1_cache.set(key, value)
                return value
        
        return None
    
    async def set_generic(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set generic cached value across tiers"""
        await self.l1_cache.set(key, value, ttl)
        
        if self.l2_cache:
            await self.l2_cache.set(key, value, ttl)
    
    async def invalidate_user_cache(self, user_id: str):
        """Invalidate all cache entries for a user"""
        await self.query_cache.invalidate_user_cache(user_id)
        
        # Could extend to other caches if needed
    
    async def preload_cache(self, popular_queries: List[Tuple[QueryRequest, QueryResponse]]):
        """Preload cache with popular queries"""
        logger.info(f"Preloading cache with {len(popular_queries)} popular queries")
        
        for request, response in popular_queries:
            await self.set_query_result(request, response)
        
        logger.info("Cache preloading completed")
    
    async def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        l1_stats = await self.l1_cache.get_stats()
        l2_stats = await self.l2_cache.get_stats() if self.l2_cache else {}
        embedding_stats = await self.embedding_cache.get_stats()
        query_stats = await self.query_cache.get_stats()
        
        return {
            'uptime_seconds': time.time() - self.start_time,
            'total_operations': self.cache_operations,
            'l1_cache': l1_stats,
            'l2_cache': l2_stats,
            'embedding_cache': embedding_stats,
            'query_cache': query_stats,
            'overall_performance': {
                'combined_hit_rate': (l1_stats.get('hits', 0) + l2_stats.get('hits', 0)) / 
                                   max(1, l1_stats.get('hits', 0) + l1_stats.get('misses', 0) + 
                                       l2_stats.get('hits', 0) + l2_stats.get('misses', 0)),
                'total_memory_mb': l1_stats.get('size_mb', 0) + l2_stats.get('memory_used_mb', 0)
            }
        }
    
    async def optimize_cache(self):
        """Perform cache optimization and cleanup"""
        logger.info("Starting cache optimization...")
        
        # Clear expired entries (handled automatically by most caches)
        # Could add additional optimization logic here
        
        stats = await self.get_comprehensive_stats()
        logger.info(f"Cache optimization completed. Hit rate: {stats['overall_performance']['combined_hit_rate']:.2%}")
    
    async def clear_all_caches(self):
        """Clear all caches"""
        await self.l1_cache.clear()
        if self.l2_cache:
            await self.l2_cache.clear()
        
        # Recreate specialized caches
        self.embedding_cache = EmbeddingCache(config.api.EMBEDDING_CACHE_SIZE)
        self.query_cache = QueryResultCache(
            config.api.QUERY_RESULT_CACHE_SIZE, 
            config.api.CACHE_TTL
        )
        
        logger.info("All caches cleared")


# Singleton instance
cache_engine = AdvancedCacheEngine()