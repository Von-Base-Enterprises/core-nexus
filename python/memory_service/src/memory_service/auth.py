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
        # Defensive configuration loading with fallbacks (SECURITY FIX: Prevent auth crashes)
        try:
            self.enabled = getattr(config, 'auth', None) and getattr(config.auth, 'ENABLED', True)
            
            # Safe API key loading with validation
            if hasattr(config, 'auth') and hasattr(config.auth, 'API_KEYS'):
                raw_keys = config.auth.API_KEYS if config.auth.API_KEYS else []
                self.valid_keys = set(key.strip() for key in raw_keys if key and key.strip()) if getattr(config.auth, 'VALIDATE_KEYS', True) else set()
            else:
                logger.warning("No API_KEYS configuration found, using empty set")
                self.valid_keys = set()
            
            # Safe admin key loading
            self.admin_key = getattr(config.auth, 'ADMIN_KEY', '') if hasattr(config, 'auth') else ''
            
            # Safe bypass endpoints loading
            if hasattr(config, 'auth') and hasattr(config.auth, 'BYPASS_ENDPOINTS'):
                self.bypass_endpoints = config.auth.BYPASS_ENDPOINTS
            else:
                # Fallback bypass endpoints for safety
                self.bypass_endpoints = {"/", "/health", "/metrics", "/docs", "/redoc", "/openapi.json"}
                logger.warning("Using fallback bypass endpoints")
            
            # Safe rate limit loading
            self.rate_limit = getattr(config.auth, 'RATE_LIMIT_PER_MINUTE', 1000) if hasattr(config, 'auth') else 1000
            
        except Exception as e:
            # CRITICAL: If config loading fails, use safe defaults to prevent crashes
            logger.error(f"Authentication configuration loading failed: {e}")
            logger.error("Using emergency fallback authentication settings")
            self.enabled = True  # Default to enabled for security
            self.valid_keys = set()  # Empty set means no keys are valid
            self.admin_key = ''
            self.bypass_endpoints = {"/", "/health", "/metrics", "/docs", "/redoc", "/openapi.json"}
            self.rate_limit = 1000
        
        # Clean empty keys
        self.valid_keys = {key.strip() for key in self.valid_keys if key.strip()}
        
        # Enhanced startup logging for debugging
        if self.enabled:
            logger.info(f"API Key authentication enabled with {len(self.valid_keys)} valid keys")
            logger.info(f"Admin key configured: {bool(self.admin_key)}")
            logger.info(f"Rate limit: {self.rate_limit} requests/minute")
            logger.info(f"Bypass endpoints: {sorted(self.bypass_endpoints)}")
            
            if not self.valid_keys and not self.admin_key:
                logger.warning("No API keys configured - all requests will be rejected!")
            elif not self.valid_keys:
                logger.info("Only admin key configured for authentication")
        else:
            logger.info("API Key authentication disabled - all requests allowed")
            
        # Log any configuration issues
        if not hasattr(config, 'auth'):
            logger.warning("No 'auth' section found in configuration")
        
        logger.debug(f"Authentication system initialized: enabled={self.enabled}, keys={len(self.valid_keys)}, admin={bool(self.admin_key)}")
        
        # Run startup validation
        self._validate_configuration()
    
    def _validate_configuration(self):
        """Validate authentication configuration and log any issues."""
        try:
            validation_issues = []
            
            # Check if auth is enabled but no keys configured
            if self.enabled and not self.valid_keys and not self.admin_key:
                validation_issues.append("Authentication enabled but no API keys configured")
            
            # Check for empty or whitespace-only keys
            if self.valid_keys:
                empty_keys = [key for key in self.valid_keys if not key or not key.strip()]
                if empty_keys:
                    validation_issues.append(f"Found {len(empty_keys)} empty API keys")
                    
            # Check admin key quality if provided
            if self.admin_key and len(self.admin_key.strip()) < 8:
                validation_issues.append("Admin key is too short (minimum 8 characters recommended)")
            
            # Check rate limit configuration
            if not isinstance(self.rate_limit, int) or self.rate_limit <= 0:
                validation_issues.append(f"Invalid rate limit configuration: {self.rate_limit}")
            
            # Check bypass endpoints
            if not isinstance(self.bypass_endpoints, set) or not self.bypass_endpoints:
                validation_issues.append("No bypass endpoints configured - health checks may fail")
            
            # Log validation results
            if validation_issues:
                logger.warning("Authentication configuration issues detected:")
                for issue in validation_issues:
                    logger.warning(f"  - {issue}")
            else:
                logger.info("✅ Authentication configuration validation passed")
                
            # Log successful configuration summary
            logger.info(f"🔐 Authentication system ready:")
            logger.info(f"   Enabled: {self.enabled}")
            logger.info(f"   Valid API keys: {len(self.valid_keys)}")
            logger.info(f"   Admin key configured: {bool(self.admin_key)}")
            logger.info(f"   Rate limit: {self.rate_limit}/minute")
            logger.info(f"   Bypass endpoints: {len(self.bypass_endpoints)}")
            
        except Exception as e:
            logger.error(f"Authentication configuration validation failed: {e}")
    
    def is_endpoint_bypassed(self, path: str) -> bool:
        """Check if endpoint should bypass authentication"""
        return path in self.bypass_endpoints
    
    def validate_api_key(self, api_key: str) -> bool:
        """Validate API key against configured keys with enhanced safety"""
        try:
            if not self.enabled:
                return True
                
            if not api_key or not isinstance(api_key, str):
                return False
                
            # Safe admin key check
            if self.admin_key and isinstance(self.admin_key, str) and api_key == self.admin_key:
                return True
                
            # Safe regular API key check
            if hasattr(self, 'valid_keys') and self.valid_keys and isinstance(self.valid_keys, set):
                return api_key in self.valid_keys
            
            # If no valid keys configured, reject all
            return False
            
        except Exception as e:
            logger.error(f"API key validation error: {e}")
            return False  # Fail securely
    
    def check_rate_limit(self, api_key: str) -> bool:
        """Check if API key is within rate limits with enhanced safety"""
        try:
            if not self.enabled or not hasattr(self, 'rate_limit') or self.rate_limit <= 0:
                return True
                
            if not api_key or not isinstance(api_key, str):
                return False
                
            current_time = time.time()
            window_start = current_time - 60  # 1 minute window
            
            # Safe rate limit storage access
            if api_key not in _rate_limit_storage:
                _rate_limit_storage[api_key] = []
            
            # Clean old entries safely
            _rate_limit_storage[api_key] = [
                timestamp for timestamp in _rate_limit_storage[api_key]
                if isinstance(timestamp, (int, float)) and timestamp > window_start
            ]
            
            # Check current count
            current_count = len(_rate_limit_storage[api_key])
            if current_count >= self.rate_limit:
                return False
            
            # Add current request
            _rate_limit_storage[api_key].append(current_time)
            return True
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            return True  # Allow request on error to avoid blocking legitimate users
    
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
        try:
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
            
            # Validate API key with enhanced error handling
            if not self.validate_api_key(api_key):
                # Safe key hashing for logging (security)
                try:
                    key_hash = hashlib.sha256(api_key.encode('utf-8')).hexdigest()[:8]
                except Exception:
                    key_hash = 'invalid_key'
                
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
            
            # Check rate limits with error handling
            if not self.check_rate_limit(api_key):
                # Safe key truncation for logging
                safe_key = api_key[:8] + '...' if len(api_key) > 8 else api_key
                logger.warning(f"Authentication failed: Rate limit exceeded for API key {safe_key} for {request.url.path}")
                
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "rate_limit_exceeded",
                        "message": f"Rate limit exceeded. Maximum {self.rate_limit} requests per minute.",
                        "code": "AUTH_003"
                    }
                )
            
            # Log successful authentication for debugging
            safe_key = api_key[:8] + '...' if len(api_key) > 8 else api_key
            logger.debug(f"Authentication successful: API key {safe_key} for {request.url.path}")
            return api_key
            
        except HTTPException:
            # Re-raise authentication errors (these are expected)
            raise
        except Exception as e:
            # Log unexpected errors with full details for debugging
            logger.error(f"Unexpected authentication error for {request.url.path}: {e}")
            logger.exception("Full authentication error details:")
            
            # Return a generic authentication error instead of 500
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "auth_system_error",
                    "message": "Authentication system encountered an error. Please try again.",
                    "code": "AUTH_004"
                }
            )

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
                # SECURITY FIX: Use auth_handler's safely loaded admin_key instead of direct config access
                try:
                    request.state.is_admin = (
                        auth_handler.admin_key and 
                        isinstance(auth_handler.admin_key, str) and 
                        api_key == auth_handler.admin_key
                    )
                except (AttributeError, TypeError) as e:
                    logger.warning(f"Admin key comparison failed safely: {e}")
                    request.state.is_admin = False
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
            # Re-raise authentication errors (these are expected)
            raise
        except (AttributeError, TypeError, KeyError, ValueError) as e:
            # Handle configuration and data-related errors specifically
            logger.error(f"Authentication configuration error: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "auth_config_error",
                    "message": "Authentication configuration issue. Please try again.",
                    "code": "AUTH_998"
                }
            )
        except Exception as e:
            # Log unexpected middleware errors with full details
            logger.error(f"Authentication middleware critical error: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.exception("Full middleware error details:")
            
            # Return authentication error instead of 500 to maintain security
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "auth_middleware_error",
                    "message": "Authentication system unavailable. Please try again.",
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