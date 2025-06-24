"""
JARVIS Configuration Management
Environment variables and system configuration for Core Nexus integration
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class JarvisConfig:
    """JARVIS System Configuration"""
    
    # Gemini AI Configuration
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    gemini_thinking_enabled: bool = os.getenv("GEMINI_THINKING_ENABLED", "true").lower() == "true"
    
    # Core Nexus Memory Service Integration
    core_nexus_url: str = os.getenv("CORE_NEXUS_URL", "https://core-nexus-memory-service.onrender.com")
    core_nexus_timeout: int = int(os.getenv("CORE_NEXUS_TIMEOUT", "30"))
    
    # LangGraph Configuration
    langgraph_checkpoint_backend: str = os.getenv("LANGGRAPH_CHECKPOINT_BACKEND", "memory")
    
    # Database Configuration (PostgreSQL for checkpointing)
    database_url: str = os.getenv("DATABASE_URL", "")
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_db: str = os.getenv("POSTGRES_DB", "jarvis_state")
    postgres_user: str = os.getenv("POSTGRES_USER", "jarvis")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "")
    
    # Redis Configuration (for pub/sub and caching)
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_db: int = int(os.getenv("REDIS_DB", "0"))
    
    # JARVIS Behavior Configuration
    max_iterations: int = int(os.getenv("JARVIS_MAX_ITERATIONS", "10"))
    thinking_timeout: int = int(os.getenv("JARVIS_THINKING_TIMEOUT", "120"))
    memory_sync_interval: int = int(os.getenv("JARVIS_MEMORY_SYNC_INTERVAL", "300"))  # 5 minutes
    
    # Self-Improvement Configuration
    self_improvement_enabled: bool = os.getenv("JARVIS_SELF_IMPROVEMENT", "true").lower() == "true"
    human_approval_required: bool = os.getenv("JARVIS_HUMAN_APPROVAL", "false").lower() == "true"
    
    # Development & Debugging
    debug_mode: bool = os.getenv("JARVIS_DEBUG", "false").lower() == "true"
    log_level: str = os.getenv("JARVIS_LOG_LEVEL", "INFO")
    
    # FastAPI Configuration
    api_host: str = os.getenv("JARVIS_API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("JARVIS_API_PORT", "8001"))
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
    
    @property
    def postgres_connection_string(self) -> str:
        """Generate PostgreSQL connection string"""
        if self.database_url:
            return self.database_url
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

# Global configuration instance
config = JarvisConfig()

def get_config() -> JarvisConfig:
    """Get the global configuration instance"""
    return config