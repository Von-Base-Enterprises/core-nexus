"""
Authentication and Rate Limiting Middleware

Provides API key authentication and rate limiting for the Core Nexus Memory Service.
"""

import asyncio
import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import os

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class AuthenticationError(HTTPException):
    """Custom exception for authentication failures."""
    def __init__(self, detail: str, error_code: str = "AUTH_001"):
        super().__init__(
            status_code=401,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )
        self.error_code = error_code


class RateLimitExceeded(HTTPException):
    """Custom exception for rate limit violations."""
    def __init__(self, detail: str, retry_after: int):
        super().__init__(
            status_code=429,
            detail=detail,
            headers={"Retry-After": str(retry_after)}
        )


class RateLimiter:
    """
    Token bucket rate limiter implementation.
    
    Tracks request counts per API key and enforces rate limits.
    """
    
    def __init__(self, requests_per_minute: int = 60, burst_size: int = 10):
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.request_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=requests_per_minute))
        self.lock = asyncio.Lock()
    
    async def check_rate_limit(self, key: str) -> Tuple[bool, Dict[str, str]]:
        """
        Check if a request is allowed under the rate limit.
        
        Returns:
            Tuple of (is_allowed, rate_limit_headers)
        """
        async with self.lock:
            now = time.time()
            window_start = now - 60  # 1 minute window
            
            # Clean old requests
            request_times = self.request_times[key]
            while request_times and request_times[0] < window_start:
                request_times.popleft()
            
            # Calculate rate limit headers
            requests_in_window = len(request_times)
            remaining = max(0, self.requests_per_minute - requests_in_window)
            reset_time = int(now + 60)
            
            headers = {
                "X-RateLimit-Limit": str(self.requests_per_minute),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(reset_time)
            }
            
            # Check if limit exceeded
            if requests_in_window >= self.requests_per_minute:
                # Calculate retry after
                oldest_request = request_times[0]
                retry_after = int(oldest_request + 60 - now) + 1
                headers["Retry-After"] = str(retry_after)
                return False, headers
            
            # Record this request
            request_times.append(now)
            return True, headers


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware for API key validation and rate limiting.
    """
    
    def __init__(self, app, bypass_endpoints: Optional[set] = None):
        super().__init__(app)
        
        # Load API keys from environment
        self.valid_api_keys = set()
        api_keys_str = os.getenv("API_KEYS", "dev-key-12345,test-key-67890")
        if api_keys_str:
            self.valid_api_keys = {key.strip() for key in api_keys_str.split(",")}
        
        # Admin key for special operations
        self.admin_key = os.getenv("ADMIN_KEY", "admin-key-super-secret")
        
        # Endpoints that don't require authentication
        self.bypass_endpoints = bypass_endpoints or {"/health", "/metrics", "/docs", "/openapi.json"}
        
        # Rate limiter
        self.rate_limiter = RateLimiter(
            requests_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
            burst_size=int(os.getenv("RATE_LIMIT_BURST", "10"))
        )
        
        # Track authentication failures
        self.auth_failures: Dict[str, int] = defaultdict(int)
        
        logger.info(f"AuthMiddleware initialized with {len(self.valid_api_keys)} API keys")
    
    async def dispatch(self, request: Request, call_next):
        """Process request through authentication and rate limiting."""
        # Check if endpoint bypasses authentication
        if request.url.path in self.bypass_endpoints:
            response = await call_next(request)
            return response
        
        try:
            # Extract API key
            api_key = self._extract_api_key(request)
            
            # Validate API key
            if not api_key:
                logger.warning(f"Missing API key for request to {request.url.path}")
                raise AuthenticationError(
                    detail="API key required. Provide via X-API-Key header.",
                    error_code="AUTH_001"
                )
            
            if api_key not in self.valid_api_keys and api_key != self.admin_key:
                logger.warning(f"Invalid API key attempt: {api_key[:8]}...")
                self.auth_failures[api_key] += 1
                raise AuthenticationError(
                    detail="Invalid API key",
                    error_code="AUTH_002"
                )
            
            # Check rate limit
            is_allowed, rate_headers = await self.rate_limiter.check_rate_limit(api_key)
            
            if not is_allowed:
                retry_after = int(rate_headers.get("Retry-After", "60"))
                logger.warning(f"Rate limit exceeded for key: {api_key[:8]}...")
                raise RateLimitExceeded(
                    detail="Rate limit exceeded",
                    retry_after=retry_after
                )
            
            # Add authentication context to request
            request.state.api_key = api_key
            request.state.is_admin = (api_key == self.admin_key)
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers to response
            for header, value in rate_headers.items():
                response.headers[header] = value
            
            # Add authentication success header
            response.headers["X-API-Key-Valid"] = "true"
            response.headers["X-Is-Admin"] = str(request.state.is_admin).lower()
            
            return response
            
        except (AuthenticationError, RateLimitExceeded) as e:
            # Return proper error response with rate limit headers if available
            headers = {}
            if hasattr(e, 'headers'):
                headers.update(e.headers)
            
            # Add rate limit headers even on auth failures
            if 'api_key' in locals():
                _, rate_headers = await self.rate_limiter.check_rate_limit(
                    api_key if api_key else "anonymous"
                )
                headers.update(rate_headers)
            
            return Response(
                content=f'{{"detail": "{e.detail}", "error_code": "{getattr(e, "error_code", "ERROR")}"}}',
                status_code=e.status_code,
                headers=headers,
                media_type="application/json"
            )
        
        except Exception as e:
            logger.error(f"Unexpected error in auth middleware: {str(e)}")
            return Response(
                content='{"detail": "Internal server error", "error_code": "SERVER_ERROR"}',
                status_code=500,
                media_type="application/json"
            )
    
    def _extract_api_key(self, request: Request) -> Optional[str]:
        """
        Extract API key from request headers.
        
        Supports:
        - X-API-Key header
        - Authorization: Bearer <token>
        """
        # Check X-API-Key header
        api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
        if api_key:
            return api_key
        
        # Check Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove "Bearer " prefix
        
        return None


def create_auth_middleware(bypass_endpoints: Optional[set] = None):
    """Factory function to create authentication middleware."""
    return lambda app: AuthMiddleware(app, bypass_endpoints)