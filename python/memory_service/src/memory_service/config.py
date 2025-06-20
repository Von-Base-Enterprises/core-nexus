"""
Core Nexus Configuration Module

Centralizes all configuration settings for the memory service.
"""

import os
from typing import Optional

# Database Configuration
class DatabaseConfig:
    """PostgreSQL and pgvector configuration optimized for 1GB RAM"""
    HOST = os.getenv("PGVECTOR_HOST", "dpg-d12n0np5pdvs73ctmm40-a")
    PORT = int(os.getenv("PGVECTOR_PORT", "5432"))
    DATABASE = os.getenv("PGVECTOR_DATABASE", "nexus_memory_db")
    USER = os.getenv("PGVECTOR_USER", "nexus_memory_db_user")
    PASSWORD = os.getenv("PGPASSWORD") or os.getenv("PGVECTOR_PASSWORD")
    
    # Connection pool settings optimized for 1GB RAM
    POOL_MIN_SIZE = int(os.getenv("POOL_MIN_SIZE", "20"))  # Increased from 10
    POOL_MAX_SIZE = int(os.getenv("POOL_MAX_SIZE", "50"))  # Increased from 20
    POOL_TIMEOUT = int(os.getenv("POOL_TIMEOUT", "30"))    # Reduced for faster failover
    COMMAND_TIMEOUT = int(os.getenv("COMMAND_TIMEOUT", "15"))  # Increased for complex vector ops
    
    # Vector settings
    VECTOR_DIMENSION = 1536
    TABLE_NAME = "vector_memories"
    DISTANCE_METRIC = "cosine"
    
    # Performance optimization settings for 1GB RAM
    SHARED_BUFFERS_MB = int(os.getenv("SHARED_BUFFERS_MB", "256"))  # 256MB
    WORK_MEM_MB = int(os.getenv("WORK_MEM_MB", "16"))              # 16MB per operation
    MAINTENANCE_WORK_MEM_MB = int(os.getenv("MAINTENANCE_WORK_MEM_MB", "64"))  # 64MB
    EFFECTIVE_CACHE_SIZE_MB = int(os.getenv("EFFECTIVE_CACHE_SIZE_MB", "768"))  # 768MB
    
    # HNSW index optimization
    HNSW_M = int(os.getenv("HNSW_M", "32"))                        # Increased from 16
    HNSW_EF_CONSTRUCTION = int(os.getenv("HNSW_EF_CONSTRUCTION", "128"))  # Increased from 64
    
    # Query optimization
    ENABLE_PREPARED_STATEMENTS = os.getenv("ENABLE_PREPARED_STATEMENTS", "true").lower() == "true"
    MAX_PREPARED_STATEMENTS = int(os.getenv("MAX_PREPARED_STATEMENTS", "100"))
    QUERY_PLAN_CACHE_SIZE = int(os.getenv("QUERY_PLAN_CACHE_SIZE", "50"))

# API Configuration
class APIConfig:
    """FastAPI service configuration"""
    HOST = os.getenv("API_HOST", "0.0.0.0")
    PORT = int(os.getenv("API_PORT", "8000"))
    WORKERS = int(os.getenv("WORKERS", "4"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # CORS settings
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
    
    # Request limits
    MAX_QUERY_LIMIT = int(os.getenv("MAX_QUERY_LIMIT", "1000"))
    DEFAULT_QUERY_LIMIT = int(os.getenv("DEFAULT_QUERY_LIMIT", "100"))
    
    # Cache settings optimized for 1GB RAM
    CACHE_TTL = int(os.getenv("CACHE_TTL", "600"))  # 10 minutes - longer cache
    CACHE_MAX_SIZE_MB = int(os.getenv("CACHE_MAX_SIZE_MB", "100"))  # 100MB cache
    EMBEDDING_CACHE_SIZE = int(os.getenv("EMBEDDING_CACHE_SIZE", "1000"))  # Cache 1000 embeddings
    QUERY_RESULT_CACHE_SIZE = int(os.getenv("QUERY_RESULT_CACHE_SIZE", "500"))  # Cache 500 query results

# Provider Configuration
class ProviderConfig:
    """Multi-provider configuration"""
    # Primary provider
    PRIMARY_PROVIDER = os.getenv("PRIMARY_PROVIDER", "pgvector")
    
    # ChromaDB settings - Use persistent directory for data retention
    CHROMADB_ENABLED = os.getenv("CHROMADB_ENABLED", "true").lower() == "true"
    CHROMADB_PERSIST_DIR = os.getenv("CHROMADB_PERSIST_DIR", "/app/chroma_db")
    CHROMADB_COLLECTION = os.getenv("CHROMADB_COLLECTION", "core_nexus_memories")
    
    # Pinecone settings
    PINECONE_ENABLED = os.getenv("PINECONE_ENABLED", "false").lower() == "true"
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "core-nexus-memories")
    PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "us-east-1-aws")

# Feature Flags
class FeatureFlags:
    """Feature toggles for gradual rollout"""
    GRAPH_ENABLED = os.getenv("GRAPH_ENABLED", "false").lower() == "true"
    ADM_ENABLED = os.getenv("ADM_EVOLUTION_ENABLED", "true").lower() == "true"
    DEDUPLICATION_MODE = os.getenv("DEDUPLICATION_MODE", "off").lower()
    OBSERVABILITY_ENABLED = os.getenv("OTEL_TRACING_ENABLED", "true").lower() == "true"

# Embedding Configuration
class EmbeddingConfig:
    """Embedding model configuration"""
    PROVIDER = os.getenv("EMBEDDING_PROVIDER", "openai")
    MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    DIMENSION = 1536
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Admin Configuration
class AdminConfig:
    """Admin and emergency endpoint configuration"""
    ADMIN_KEY = os.getenv("ADMIN_KEY", "")
    ENABLE_NUCLEAR_ENDPOINTS = os.getenv("ENABLE_NUCLEAR_ENDPOINTS", "true").lower() == "true"
    ENABLE_DEBUG_ENDPOINTS = os.getenv("ENABLE_DEBUG_ENDPOINTS", "false").lower() == "true"

# Singleton config instance
class Config:
    """Main configuration object"""
    database = DatabaseConfig()
    api = APIConfig()
    providers = ProviderConfig()
    features = FeatureFlags()
    embedding = EmbeddingConfig()
    admin = AdminConfig()
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.database.PASSWORD:
            raise ValueError("PGPASSWORD or PGVECTOR_PASSWORD must be set")
        
        if cls.embedding.PROVIDER == "openai" and not cls.embedding.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY must be set for OpenAI embeddings")
        
        return True

# Export singleton
config = Config()