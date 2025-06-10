"""
OpenAI Embedding Models for Core Nexus Memory Service

Provides text embedding generation using OpenAI's embedding models,
specifically optimized for text-embedding-3-small for cost efficiency.
"""

import asyncio
import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Any

try:
    import openai
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)


class EmbeddingModel(ABC):
    """Abstract base class for embedding models."""

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for text."""
        pass

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Get embedding dimension."""
        pass


class OpenAIEmbeddingModel(EmbeddingModel):
    """OpenAI embedding model implementation using text-embedding-3-small."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "text-embedding-3-small",
        max_retries: int = 3,
        timeout: float = 30.0,
        max_batch_size: int = 100
    ):
        """
        Initialize OpenAI embedding model.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: OpenAI embedding model to use
            max_retries: Maximum retry attempts for failed requests
            timeout: Request timeout in seconds
            max_batch_size: Maximum texts per batch request
        """
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "OpenAI package not available. Install with: pip install openai"
            )

        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout
        self.max_batch_size = max_batch_size

        # Initialize OpenAI client
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.client = AsyncOpenAI(
            api_key=self.api_key,
            timeout=timeout,
            max_retries=max_retries
        )

        # Cache for embedding dimensions
        self._dimension_cache: int | None = None

        logger.info(f"Initialized OpenAI embedding model: {model}")

    @property
    def dimension(self) -> int:
        """Get embedding dimension for the model."""
        if self._dimension_cache is None:
            # text-embedding-3-small has 1536 dimensions
            if "text-embedding-3-small" in self.model:
                self._dimension_cache = 1536
            elif "text-embedding-3-large" in self.model:
                self._dimension_cache = 3072
            elif "text-embedding-ada-002" in self.model:
                self._dimension_cache = 1536
            else:
                # Default to 1536 for unknown models
                self._dimension_cache = 1536
                logger.warning(f"Unknown model {self.model}, assuming 1536 dimensions")

        return self._dimension_cache

    async def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding vector
            
        Raises:
            ValueError: If text is empty or too long
            Exception: If OpenAI API request fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        # Clean and truncate text if needed
        cleaned_text = self._clean_text(text)

        try:
            start_time = time.time()

            response = await self.client.embeddings.create(
                input=[cleaned_text],
                model=self.model
            )

            embedding = response.data[0].embedding

            # Log performance metrics
            duration = (time.time() - start_time) * 1000
            logger.debug(f"Generated embedding in {duration:.1f}ms for {len(text)} chars")

            return embedding

        except openai.RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {e}")
            raise Exception(f"Rate limit exceeded: {e}")
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise Exception(f"API error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error generating embedding: {e}")
            raise Exception(f"Failed to generate embedding: {e}")

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts efficiently.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors in the same order as input texts
            
        Raises:
            ValueError: If any text is invalid
            Exception: If OpenAI API request fails
        """
        if not texts:
            return []

        # Validate and clean texts
        cleaned_texts = []
        for i, text in enumerate(texts):
            if not text or not text.strip():
                raise ValueError(f"Text at index {i} cannot be empty")
            cleaned_texts.append(self._clean_text(text))

        # Process in batches if needed
        all_embeddings = []

        for i in range(0, len(cleaned_texts), self.max_batch_size):
            batch = cleaned_texts[i:i + self.max_batch_size]
            batch_embeddings = await self._embed_batch_chunk(batch)
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    async def _embed_batch_chunk(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a chunk of texts."""
        try:
            start_time = time.time()

            response = await self.client.embeddings.create(
                input=texts,
                model=self.model
            )

            embeddings = [data.embedding for data in response.data]

            # Log performance metrics
            duration = (time.time() - start_time) * 1000
            total_chars = sum(len(text) for text in texts)
            logger.debug(
                f"Generated {len(embeddings)} embeddings in {duration:.1f}ms "
                f"for {total_chars} total chars"
            )

            return embeddings

        except openai.RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded for batch: {e}")
            # Implement exponential backoff
            await asyncio.sleep(2 ** (self.max_retries - 1))
            raise Exception(f"Rate limit exceeded: {e}")
        except openai.APIError as e:
            logger.error(f"OpenAI API error for batch: {e}")
            raise Exception(f"API error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in batch embedding: {e}")
            raise Exception(f"Failed to generate batch embeddings: {e}")

    def _clean_text(self, text: str) -> str:
        """
        Clean and prepare text for embedding.
        
        Args:
            text: Raw input text
            
        Returns:
            Cleaned text ready for embedding
        """
        # Remove excessive whitespace
        cleaned = " ".join(text.split())

        # Truncate if too long (OpenAI has token limits)
        # text-embedding-3-small supports up to 8192 tokens
        # Roughly 4 chars per token, so ~32k characters max
        max_chars = 32000
        if len(cleaned) > max_chars:
            cleaned = cleaned[:max_chars]
            logger.warning(f"Truncated text from {len(text)} to {max_chars} characters")

        return cleaned

    async def health_check(self) -> dict[str, Any]:
        """
        Check if the embedding service is healthy.
        
        Returns:
            Dictionary with health status and metrics
        """
        try:
            # Test with a small embedding request
            test_text = "Health check test"
            start_time = time.time()

            await self.embed_text(test_text)

            response_time = (time.time() - start_time) * 1000

            return {
                "status": "healthy",
                "model": self.model,
                "dimension": self.dimension,
                "response_time_ms": round(response_time, 2),
                "api_key_configured": bool(self.api_key),
                "max_batch_size": self.max_batch_size
            }

        except Exception as e:
            logger.error(f"Embedding health check failed: {e}")
            return {
                "status": "unhealthy",
                "model": self.model,
                "error": str(e),
                "api_key_configured": bool(self.api_key)
            }


class MockEmbeddingModel(EmbeddingModel):
    """Mock embedding model for testing and development."""

    def __init__(self, dimension: int = 1536):
        """Initialize mock embedding model."""
        self._dimension = dimension
        logger.info(f"Initialized mock embedding model with {dimension} dimensions")

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimension

    async def embed_text(self, text: str) -> list[float]:
        """Generate mock embedding for text."""
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        # Generate deterministic mock embedding based on text hash
        import hashlib
        hash_bytes = hashlib.md5(text.encode()).digest()

        embedding = []
        for i in range(self._dimension):
            byte_idx = i % len(hash_bytes)
            # Normalize to [-1, 1] range like real embeddings
            embedding.append((float(hash_bytes[byte_idx]) / 127.5) - 1.0)

        return embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate mock embeddings for multiple texts."""
        embeddings = []
        for text in texts:
            embedding = await self.embed_text(text)
            embeddings.append(embedding)
        return embeddings


def create_embedding_model(
    provider: str = "openai",
    model: str = "text-embedding-3-small",
    **kwargs
) -> EmbeddingModel:
    """
    Factory function to create embedding models.
    
    Args:
        provider: Embedding provider ("openai" or "mock")
        model: Model name for the provider
        **kwargs: Additional configuration for the model
        
    Returns:
        Configured embedding model instance
        
    Raises:
        ValueError: If provider is not supported
        ImportError: If required packages are not installed
    """
    if provider.lower() == "openai":
        return OpenAIEmbeddingModel(model=model, **kwargs)
    elif provider.lower() == "mock":
        dimension = kwargs.get("dimension", 1536)
        return MockEmbeddingModel(dimension=dimension)
    else:
        raise ValueError(f"Unsupported embedding provider: {provider}")
