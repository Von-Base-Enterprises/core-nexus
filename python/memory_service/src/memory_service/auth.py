"""
Core Nexus Authentication Module

Provides API key authentication for AI agents and external clients.
Designed to be lightweight and development-friendly while maintaining security.
"""

import hashlib
import logging
import time
from collections import defaultdict
from typing import Optional, Set

from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.api_key import APIKeyHeader

from .config import config

logger = logging.getLogger(__name__)

# Rate limiting storage (in-memory for simplicity)
# In production, this could be Redis or a database
_rate_limit_storage = defaultdict(list)

# API Key header extractor
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

class APIKeyAuth:
    """
    Simple but effective API key authentication for AI agents.
    
    Features:
    - Header-based authentication (X-API-Key)
    - Rate limiting per API key
    - Bypass for health/docs endpoints
    - Development-friendly with default keys
    """
    
    def __init__(self):
        self.enabled = config.auth.ENABLED
        self.valid_keys = set(config.auth.API_KEYS) if config.auth.VALIDATE_KEYS else set()
        self.admin_key = config.auth.ADMIN_KEY
        self.bypass_endpoints = config.auth.BYPASS_ENDPOINTS
        self.rate_limit = config.auth.RATE_LIMIT_PER_MINUTE
        
        # Clean empty keys
        self.valid_keys = {key.strip() for key in self.valid_keys if key.strip()}
        
        if self.enabled:
            logger.info(f"API Key authentication enabled with {len(self.valid_keys)} keys")
            if not self.valid_keys:
                logger.warning("No API keys configured - all requests will be rejected!")
        else:
            logger.info("API Key authentication disabled")
    
    def is_endpoint_bypassed(self, path: str) -> bool:
        """Check if endpoint should bypass authentication"""
        return path in self.bypass_endpoints
    
    def validate_api_key(self, api_key: str) -> bool:
        """Validate API key against configured keys"""
        if not self.enabled:
            return True
            
        if not api_key:
            return False
            
        # Check admin key
        if self.admin_key and api_key == self.admin_key:
            return True
            
        # Check regular API keys
        return api_key in self.valid_keys
    
    def check_rate_limit(self, api_key: str) -> bool:
        """Check if API key is within rate limits"""
        if not self.enabled or self.rate_limit <= 0:
            return True
            
        current_time = time.time()
        window_start = current_time - 60  # 1 minute window
        
        # Clean old entries
        _rate_limit_storage[api_key] = [
            timestamp for timestamp in _rate_limit_storage[api_key]
            if timestamp > window_start
        ]
        
        # Check current count
        current_count = len(_rate_limit_storage[api_key])
        if current_count >= self.rate_limit:
            return False
        
        # Add current request
        _rate_limit_storage[api_key].append(current_time)
        return True
    
    def get_api_key_from_request(self, request: Request) -> Optional[str]:
        """Extract API key from request headers"""
        # Try X-API-Key header first (preferred)
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return api_key.strip()
        
        # Try Authorization header as fallback (Bearer token)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:].strip()
        
        return None
    
    async def authenticate_request(self, request: Request) -> Optional[str]:
        """
        Main authentication method for middleware.
        
        Returns:
            API key if authenticated, None if not authenticated
            
        Raises:
            HTTPException for authentication failures
        """
        # Skip authentication if disabled
        if not self.enabled:
            return None
        
        # Check if endpoint should bypass authentication
        if self.is_endpoint_bypassed(request.url.path):
            return None
        
        # Extract API key
        api_key = self.get_api_key_from_request(request)
        
        if not api_key:
            # Safely get client host without causing exceptions
            client_host = 'unknown'
            try:
                if request.client and hasattr(request.client, 'host'):
                    client_host = request.client.host
            except Exception:
                pass
            
            logger.warning(f"Authentication failed: No API key provided for {request.url.path} from {client_host}")
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "missing_api_key",
                    "message": "API key required. Provide via X-API-Key header.",
                    "code": "AUTH_001"
                }
            )
        
        # Validate API key
        if not self.validate_api_key(api_key):
            # Hash the key for logging (security)
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:8]
            
            # Safely get client host without causing exceptions
            client_host = 'unknown'
            try:
                if request.client and hasattr(request.client, 'host'):
                    client_host = request.client.host
            except Exception:
                pass
            
            logger.warning(f"Authentication failed: Invalid API key {key_hash}... for {request.url.path} from {client_host}")
            
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "invalid_api_key",
                    "message": "Invalid API key provided.",
                    "code": "AUTH_002"
                }
            )
        
        # Check rate limits
        if not self.check_rate_limit(api_key):
            logger.warning(f"Authentication failed: Rate limit exceeded for API key {api_key[:8]}... for {request.url.path}")
            
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": f"Rate limit exceeded. Maximum {self.rate_limit} requests per minute.",
                    "code": "AUTH_003"
                }
            )
        
        # Log successful authentication for debugging
        logger.debug(f"Authentication successful: API key {api_key[:8]}... for {request.url.path}")
        return api_key

# Global authentication instance
auth_handler = APIKeyAuth()

async def get_current_api_key(request: Request) -> Optional[str]:
    """
    FastAPI dependency for getting the current API key.
    
    Usage:
        @app.get("/protected")
        async def protected_endpoint(api_key: str = Depends(get_current_api_key)):
            return {"message": "Authenticated!", "api_key": api_key[:8] + "..."}
    """
    return await auth_handler.authenticate_request(request)

def create_auth_middleware():
    """
    Create authentication middleware for FastAPI.
    
    This middleware will be applied to all requests automatically.
    """
    async def auth_middleware(request: Request, call_next):
        """Authentication middleware implementation"""
        try:
            # Authenticate the request (may raise HTTPException)
            api_key = await auth_handler.authenticate_request(request)
            
            # Add API key to request state for use in endpoints
            if api_key:
                request.state.api_key = api_key
                request.state.is_admin = api_key == config.auth.ADMIN_KEY
            else:
                request.state.api_key = None
                request.state.is_admin = False
            
            # Process the request
            response = await call_next(request)
            
            # Add authentication info to response headers (for debugging)
            if hasattr(request.state, 'api_key') and request.state.api_key:
                response.headers["X-API-Key-Valid"] = "true"
                response.headers["X-Is-Admin"] = str(request.state.is_admin).lower()
            
            return response
            
        except HTTPException:
            # Re-raise authentication errors
            raise
        except Exception as e:
            # Log unexpected errors but don't expose them
            logger.error(f"Authentication middleware error: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "auth_error",
                    "message": "Authentication system error",
                    "code": "AUTH_999"
                }
            )
    
    return auth_middleware

def get_api_usage_stats() -> dict:
    """Get API usage statistics for monitoring"""
    if not auth_handler.enabled:
        return {"authentication": "disabled"}
    
    current_time = time.time()
    window_start = current_time - 60  # Last minute
    
    stats = {
        "authentication": "enabled",
        "configured_keys": len(auth_handler.valid_keys),
        "rate_limit_per_minute": auth_handler.rate_limit,
        "active_keys_last_minute": 0,
        "total_requests_last_minute": 0
    }
    
    # Count active keys and requests in the last minute
    active_keys = set()
    total_requests = 0
    
    for api_key, timestamps in _rate_limit_storage.items():
        recent_requests = [ts for ts in timestamps if ts > window_start]
        if recent_requests:
            active_keys.add(api_key)
            total_requests += len(recent_requests)
    
    stats["active_keys_last_minute"] = len(active_keys)
    stats["total_requests_last_minute"] = total_requests
    
    return stats