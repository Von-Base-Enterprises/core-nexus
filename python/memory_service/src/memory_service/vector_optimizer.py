"""
Vector Processing Optimizer for Core Nexus Memory Service

Implements high-performance vector operations, batch processing, and optimization
techniques specifically designed for 1GB RAM PostgreSQL deployment.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union
from concurrent.futures import ThreadPoolExecutor
import math

import numpy as np

from .config import config
from .models import MemoryResponse

logger = logging.getLogger(__name__)


@dataclass
class VectorBatch:
    """Represents a batch of vectors for processing"""
    vectors: np.ndarray
    metadata: List[Dict[str, Any]]
    batch_id: str
    created_at: float
    size_mb: float


@dataclass
class OptimizationStats:
    """Statistics for vector optimization operations"""
    total_operations: int = 0
    batch_operations: int = 0
    optimization_time_ms: float = 0.0
    memory_saved_mb: float = 0.0
    speedup_factor: float = 1.0


class VectorCompressor:
    """Handles vector compression and decompression for memory efficiency"""
    
    def __init__(self):
        self.compression_ratio = 0.5  # Target compression ratio
        self.precision_loss = 0.01   # Acceptable precision loss
    
    def compress_vectors(self, vectors: np.ndarray, method: str = "quantization") -> Tuple[np.ndarray, Dict[str, Any]]:
        """Compress vectors using various methods"""
        start_time = time.time()
        original_size = vectors.nbytes
        
        if method == "quantization":
            compressed, metadata = self._quantize_vectors(vectors)
        elif method == "pca":
            compressed, metadata = self._pca_compress_vectors(vectors)
        elif method == "sparse":
            compressed, metadata = self._sparse_compress_vectors(vectors)
        else:
            # No compression
            compressed = vectors.copy()
            metadata = {"method": "none"}
        
        compression_time = (time.time() - start_time) * 1000
        compressed_size = compressed.nbytes
        ratio = compressed_size / original_size
        
        metadata.update({
            "original_size_mb": original_size / 1024 / 1024,
            "compressed_size_mb": compressed_size / 1024 / 1024,
            "compression_ratio": ratio,
            "compression_time_ms": compression_time
        })
        
        logger.debug(f"Compressed {vectors.shape[0]} vectors: "
                    f"{ratio:.2%} of original size in {compression_time:.1f}ms")
        
        return compressed, metadata
    
    def _quantize_vectors(self, vectors: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Quantize vectors to reduce precision"""
        # Use 16-bit floats instead of 32-bit
        quantized = vectors.astype(np.float16)
        
        metadata = {
            "method": "quantization",
            "precision": "float16",
            "original_dtype": str(vectors.dtype)
        }
        
        return quantized, metadata
    
    def _pca_compress_vectors(self, vectors: np.ndarray, target_dims: int = 768) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Compress vectors using PCA dimensionality reduction"""
        if vectors.shape[1] <= target_dims:
            return vectors.copy(), {"method": "pca", "reduction": "none"}
        
        # Simple PCA implementation
        mean_vector = np.mean(vectors, axis=0)
        centered = vectors - mean_vector
        
        # Compute covariance matrix (memory efficient for small batches)
        if vectors.shape[0] < vectors.shape[1]:
            cov = np.dot(centered, centered.T) / (vectors.shape[0] - 1)
            eigenvals, eigenvecs = np.linalg.eigh(cov)
            eigenvecs = np.dot(centered.T, eigenvecs)
        else:
            cov = np.dot(centered.T, centered) / (vectors.shape[0] - 1)
            eigenvals, eigenvecs = np.linalg.eigh(cov)
        
        # Select top components
        idx = np.argsort(eigenvals)[::-1][:target_dims]
        selected_eigenvecs = eigenvecs[:, idx]
        
        # Project vectors
        compressed = np.dot(centered, selected_eigenvecs)
        
        metadata = {
            "method": "pca",
            "original_dims": vectors.shape[1],
            "compressed_dims": target_dims,
            "mean_vector": mean_vector,
            "eigenvectors": selected_eigenvecs,
            "eigenvalues": eigenvals[idx]
        }
        
        return compressed.astype(np.float32), metadata
    
    def _sparse_compress_vectors(self, vectors: np.ndarray, threshold: float = 0.01) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Compress vectors by zeroing small values"""
        # Zero out values below threshold
        mask = np.abs(vectors) < threshold
        compressed = vectors.copy()
        compressed[mask] = 0
        
        sparsity = np.sum(mask) / vectors.size
        
        metadata = {
            "method": "sparse",
            "threshold": threshold,
            "sparsity": sparsity
        }
        
        return compressed, metadata
    
    def decompress_vectors(self, compressed: np.ndarray, metadata: Dict[str, Any]) -> np.ndarray:
        """Decompress vectors back to original format"""
        method = metadata.get("method", "none")
        
        if method == "none":
            return compressed.copy()
        elif method == "quantization":
            # Convert back to float32
            return compressed.astype(np.float32)
        elif method == "pca":
            # Reconstruct from PCA
            mean_vector = metadata["mean_vector"]
            eigenvectors = metadata["eigenvectors"]
            reconstructed = np.dot(compressed, eigenvectors.T) + mean_vector
            return reconstructed.astype(np.float32)
        elif method == "sparse":
            # Already in correct format
            return compressed.astype(np.float32)
        else:
            logger.warning(f"Unknown compression method: {method}")
            return compressed.copy()


class BatchProcessor:
    """Handles batch processing of vector operations"""
    
    def __init__(self, max_batch_size: int = 100, max_memory_mb: int = 50):
        self.max_batch_size = max_batch_size
        self.max_memory_mb = max_memory_mb
        self.current_batches: Dict[str, VectorBatch] = {}
        self.processing_queue = asyncio.Queue()
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._is_processing = False
    
    async def start_processing(self):
        """Start background batch processing"""
        if self._is_processing:
            return
        
        self._is_processing = True
        asyncio.create_task(self._process_batches())
        logger.info("Batch processor started")
    
    async def stop_processing(self):
        """Stop background batch processing"""
        self._is_processing = False
        logger.info("Batch processor stopped")
    
    async def add_to_batch(self, vectors: np.ndarray, metadata: List[Dict[str, Any]], batch_type: str = "similarity") -> str:
        """Add vectors to appropriate batch"""
        batch_id = f"{batch_type}_{int(time.time() * 1000)}"
        
        # Calculate batch size
        size_mb = vectors.nbytes / 1024 / 1024
        
        # Create new batch
        batch = VectorBatch(
            vectors=vectors,
            metadata=metadata,
            batch_id=batch_id,
            created_at=time.time(),
            size_mb=size_mb
        )
        
        self.current_batches[batch_id] = batch
        await self.processing_queue.put(batch_id)
        
        logger.debug(f"Added batch {batch_id} with {len(vectors)} vectors ({size_mb:.1f}MB)")
        return batch_id
    
    async def _process_batches(self):
        """Background batch processing loop"""
        while self._is_processing:
            try:
                # Wait for batch with timeout
                batch_id = await asyncio.wait_for(self.processing_queue.get(), timeout=1.0)
                
                if batch_id in self.current_batches:
                    batch = self.current_batches[batch_id]
                    await self._process_single_batch(batch)
                    del self.current_batches[batch_id]
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Batch processing error: {e}")
    
    async def _process_single_batch(self, batch: VectorBatch):
        """Process a single batch of vectors"""
        start_time = time.time()
        
        try:
            # Process in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                self._optimize_batch,
                batch
            )
            
            processing_time = (time.time() - start_time) * 1000
            logger.debug(f"Processed batch {batch.batch_id} in {processing_time:.1f}ms")
            
        except Exception as e:
            logger.error(f"Failed to process batch {batch.batch_id}: {e}")
    
    def _optimize_batch(self, batch: VectorBatch) -> Dict[str, Any]:
        """Optimize a batch of vectors (runs in thread pool)"""
        # Placeholder for batch optimization logic
        # Could include:
        # - Vector normalization
        # - Similarity pre-computation
        # - Index updates
        # - Compression
        
        return {
            "batch_id": batch.batch_id,
            "optimized": True,
            "vector_count": len(batch.vectors)
        }


class SimilarityOptimizer:
    """Optimizes vector similarity computations"""
    
    def __init__(self):
        self.similarity_cache: Dict[str, float] = {}
        self.cache_hits = 0
        self.cache_misses = 0
    
    def compute_similarities_batch(
        self, 
        query_vector: np.ndarray, 
        database_vectors: np.ndarray,
        method: str = "cosine"
    ) -> np.ndarray:
        """Compute similarities between query and database vectors efficiently"""
        start_time = time.time()
        
        if method == "cosine":
            similarities = self._cosine_similarity_batch(query_vector, database_vectors)
        elif method == "euclidean":
            similarities = self._euclidean_similarity_batch(query_vector, database_vectors)
        elif method == "dot":
            similarities = self._dot_product_batch(query_vector, database_vectors)
        else:
            raise ValueError(f"Unknown similarity method: {method}")
        
        computation_time = (time.time() - start_time) * 1000
        logger.debug(f"Computed {method} similarities for {len(database_vectors)} vectors in {computation_time:.1f}ms")
        
        return similarities
    
    def _cosine_similarity_batch(self, query: np.ndarray, database: np.ndarray) -> np.ndarray:
        """Optimized cosine similarity computation"""
        # Normalize vectors
        query_norm = query / (np.linalg.norm(query) + 1e-8)
        database_norms = database / (np.linalg.norm(database, axis=1, keepdims=True) + 1e-8)
        
        # Compute dot product (cosine similarity for normalized vectors)
        similarities = np.dot(database_norms, query_norm)
        return similarities
    
    def _euclidean_similarity_batch(self, query: np.ndarray, database: np.ndarray) -> np.ndarray:
        """Optimized Euclidean distance computation (converted to similarity)"""
        # Compute squared distances efficiently
        query_sq = np.sum(query ** 2)
        database_sq = np.sum(database ** 2, axis=1)
        dot_products = np.dot(database, query)
        
        squared_distances = query_sq + database_sq - 2 * dot_products
        distances = np.sqrt(np.maximum(squared_distances, 0))
        
        # Convert distances to similarities (1 / (1 + distance))
        similarities = 1.0 / (1.0 + distances)
        return similarities
    
    def _dot_product_batch(self, query: np.ndarray, database: np.ndarray) -> np.ndarray:
        """Simple dot product similarity"""
        return np.dot(database, query)
    
    def get_top_k_similar(
        self, 
        similarities: np.ndarray, 
        k: int,
        min_similarity: float = 0.0
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Get top-k most similar vectors efficiently"""
        # Filter by minimum similarity
        valid_mask = similarities >= min_similarity
        valid_indices = np.where(valid_mask)[0]
        valid_similarities = similarities[valid_mask]
        
        if len(valid_similarities) == 0:
            return np.array([]), np.array([])
        
        # Get top-k
        if len(valid_similarities) <= k:
            # Return all valid results
            sort_indices = np.argsort(valid_similarities)[::-1]
            return valid_indices[sort_indices], valid_similarities[sort_indices]
        else:
            # Use partial sort for efficiency
            top_k_indices = np.argpartition(valid_similarities, -k)[-k:]
            top_k_indices = top_k_indices[np.argsort(valid_similarities[top_k_indices])[::-1]]
            
            return valid_indices[top_k_indices], valid_similarities[top_k_indices]


class MemoryOptimizer:
    """Optimizes memory usage for vector operations"""
    
    def __init__(self):
        self.memory_threshold_mb = config.api.CACHE_MAX_SIZE_MB * 0.8  # 80% of cache limit
        self.current_memory_mb = 0.0
        self.memory_tracking: Dict[str, float] = {}
    
    def estimate_memory_usage(self, vectors: np.ndarray) -> float:
        """Estimate memory usage for vector array"""
        return vectors.nbytes / 1024 / 1024
    
    def check_memory_availability(self, required_mb: float) -> bool:
        """Check if required memory is available"""
        return (self.current_memory_mb + required_mb) <= self.memory_threshold_mb
    
    def allocate_memory(self, operation_id: str, size_mb: float) -> bool:
        """Allocate memory for operation"""
        if not self.check_memory_availability(size_mb):
            return False
        
        self.memory_tracking[operation_id] = size_mb
        self.current_memory_mb += size_mb
        return True
    
    def release_memory(self, operation_id: str):
        """Release allocated memory"""
        if operation_id in self.memory_tracking:
            size_mb = self.memory_tracking[operation_id]
            self.current_memory_mb -= size_mb
            del self.memory_tracking[operation_id]
    
    def optimize_vector_storage(self, vectors: List[np.ndarray]) -> List[np.ndarray]:
        """Optimize vector storage for memory efficiency"""
        optimized = []
        
        for vector in vectors:
            # Convert to most memory-efficient dtype while maintaining precision
            if vector.dtype == np.float64:
                # Convert double precision to single precision
                optimized.append(vector.astype(np.float32))
            elif vector.dtype == np.float32:
                # Keep as is or convert to half precision if acceptable
                if self.current_memory_mb > self.memory_threshold_mb * 0.9:
                    optimized.append(vector.astype(np.float16))
                else:
                    optimized.append(vector)
            else:
                optimized.append(vector)
        
        return optimized


class VectorOptimizationEngine:
    """
    Main vector optimization engine coordinating all optimization strategies
    """
    
    def __init__(self):
        self.compressor = VectorCompressor()
        self.batch_processor = BatchProcessor()
        self.similarity_optimizer = SimilarityOptimizer()
        self.memory_optimizer = MemoryOptimizer()
        self.stats = OptimizationStats()
        self._is_initialized = False
    
    async def initialize(self):
        """Initialize the optimization engine"""
        if self._is_initialized:
            return
        
        await self.batch_processor.start_processing()
        self._is_initialized = True
        logger.info("Vector optimization engine initialized")
    
    async def shutdown(self):
        """Shutdown the optimization engine"""
        await self.batch_processor.stop_processing()
        self._is_initialized = False
        logger.info("Vector optimization engine shutdown")
    
    async def optimize_vector_query(
        self, 
        query_vector: np.ndarray, 
        database_vectors: List[np.ndarray],
        similarity_method: str = "cosine",
        top_k: int = 100,
        min_similarity: float = 0.0
    ) -> Tuple[List[int], List[float]]:
        """Optimize vector similarity query"""
        start_time = time.time()
        operation_id = f"query_{int(time.time() * 1000)}"
        
        try:
            # Combine database vectors into single array for batch processing
            if not database_vectors:
                return [], []
            
            combined_vectors = np.vstack(database_vectors)
            required_memory = self.memory_optimizer.estimate_memory_usage(combined_vectors)
            
            # Check memory availability
            if not self.memory_optimizer.allocate_memory(operation_id, required_memory):
                logger.warning(f"Insufficient memory for query optimization ({required_memory:.1f}MB required)")
                # Fall back to non-optimized processing
                return await self._fallback_similarity_search(query_vector, database_vectors, top_k)
            
            # Optimize vectors for better performance
            optimized_vectors = self.memory_optimizer.optimize_vector_storage([combined_vectors])[0]
            optimized_query = self.memory_optimizer.optimize_vector_storage([query_vector])[0]
            
            # Compute similarities
            similarities = self.similarity_optimizer.compute_similarities_batch(
                optimized_query, optimized_vectors, similarity_method
            )
            
            # Get top-k results
            top_indices, top_similarities = self.similarity_optimizer.get_top_k_similar(
                similarities, top_k, min_similarity
            )
            
            # Update statistics
            self.stats.total_operations += 1
            optimization_time = (time.time() - start_time) * 1000
            self.stats.optimization_time_ms = (
                (self.stats.optimization_time_ms * (self.stats.total_operations - 1) + optimization_time) /
                self.stats.total_operations
            )
            
            logger.debug(f"Optimized vector query in {optimization_time:.1f}ms, "
                        f"found {len(top_indices)} results")
            
            return top_indices.tolist(), top_similarities.tolist()
            
        except Exception as e:
            logger.error(f"Vector query optimization failed: {e}")
            # Fall back to simple processing
            return await self._fallback_similarity_search(query_vector, database_vectors, top_k)
        
        finally:
            self.memory_optimizer.release_memory(operation_id)
    
    async def _fallback_similarity_search(
        self, 
        query_vector: np.ndarray, 
        database_vectors: List[np.ndarray], 
        top_k: int
    ) -> Tuple[List[int], List[float]]:
        """Fallback similarity search without optimization"""
        logger.info("Using fallback similarity search")
        
        similarities = []
        for i, db_vector in enumerate(database_vectors):
            # Simple cosine similarity
            similarity = np.dot(query_vector, db_vector) / (
                np.linalg.norm(query_vector) * np.linalg.norm(db_vector) + 1e-8
            )
            similarities.append((i, similarity))
        
        # Sort and return top-k
        similarities.sort(key=lambda x: x[1], reverse=True)
        top_results = similarities[:top_k]
        
        indices = [idx for idx, _ in top_results]
        scores = [score for _, score in top_results]
        
        return indices, scores
    
    async def optimize_vector_storage(
        self, 
        vectors: List[np.ndarray], 
        metadata: List[Dict[str, Any]],
        compression_method: str = "quantization"
    ) -> Tuple[List[np.ndarray], List[Dict[str, Any]]]:
        """Optimize vectors for storage"""
        if not vectors:
            return [], []
        
        start_time = time.time()
        optimized_vectors = []
        updated_metadata = []
        
        # Process in batches if many vectors
        batch_size = 50
        for i in range(0, len(vectors), batch_size):
            batch_vectors = vectors[i:i + batch_size]
            batch_metadata = metadata[i:i + batch_size]
            
            # Combine into array for batch processing
            if batch_vectors:
                combined = np.vstack(batch_vectors)
                compressed, compression_metadata = self.compressor.compress_vectors(
                    combined, compression_method
                )
                
                # Split back into individual vectors
                for j in range(len(batch_vectors)):
                    optimized_vectors.append(compressed[j:j+1].squeeze())
                    
                    # Update metadata
                    meta = batch_metadata[j].copy()
                    meta.update({
                        'compression': compression_metadata,
                        'optimized_at': time.time()
                    })
                    updated_metadata.append(meta)
        
        optimization_time = (time.time() - start_time) * 1000
        
        # Update statistics
        self.stats.batch_operations += 1
        original_size = sum(v.nbytes for v in vectors) / 1024 / 1024
        optimized_size = sum(v.nbytes for v in optimized_vectors) / 1024 / 1024
        self.stats.memory_saved_mb += (original_size - optimized_size)
        
        logger.info(f"Optimized {len(vectors)} vectors in {optimization_time:.1f}ms, "
                   f"saved {original_size - optimized_size:.1f}MB")
        
        return optimized_vectors, updated_metadata
    
    async def get_optimization_stats(self) -> Dict[str, Any]:
        """Get comprehensive optimization statistics"""
        return {
            'total_operations': self.stats.total_operations,
            'batch_operations': self.stats.batch_operations,
            'avg_optimization_time_ms': self.stats.optimization_time_ms,
            'memory_saved_mb': self.stats.memory_saved_mb,
            'speedup_factor': self.stats.speedup_factor,
            'memory_usage': {
                'current_mb': self.memory_optimizer.current_memory_mb,
                'threshold_mb': self.memory_optimizer.memory_threshold_mb,
                'utilization': self.memory_optimizer.current_memory_mb / self.memory_optimizer.memory_threshold_mb
            },
            'cache_performance': {
                'similarity_cache_hits': self.similarity_optimizer.cache_hits,
                'similarity_cache_misses': self.similarity_optimizer.cache_misses,
                'cache_hit_rate': (
                    self.similarity_optimizer.cache_hits / 
                    max(1, self.similarity_optimizer.cache_hits + self.similarity_optimizer.cache_misses)
                )
            },
            'batch_processing': {
                'active_batches': len(self.batch_processor.current_batches),
                'queue_size': self.batch_processor.processing_queue.qsize(),
                'is_processing': self.batch_processor._is_processing
            }
        }


# Singleton instance
vector_optimizer = VectorOptimizationEngine()