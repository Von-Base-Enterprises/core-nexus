"""
Circuit Breaker Pattern for Enhanced Load Balancing

Implements circuit breaker to improve system resilience under load
and prevent cascade failures across providers.
"""

import asyncio
import time
from enum import Enum
from typing import Any, Callable, Optional
import logging

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing fast
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker for provider operations.
    
    Prevents system overload by failing fast when error rates are high.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        recovery_timeout: float = 30.0
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.recovery_timeout = recovery_timeout
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        
        # Performance metrics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        self.total_requests += 1
        
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                # Fail fast
                self.failed_requests += 1
                raise Exception("Circuit breaker is OPEN - failing fast")
        
        try:
            # Execute the function
            start_time = time.time()
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Success - reset failure count
            self._on_success()
            
            # Log performance metrics
            if execution_time > 1.0:  # Log slow operations
                logger.warning(f"Slow operation detected: {execution_time:.2f}s")
            
            return result
            
        except Exception as e:
            self._on_failure()
            logger.error(f"Circuit breaker caught failure: {e}")
            raise
    
    def _on_success(self):
        """Handle successful operation."""
        self.successful_requests += 1
        self.failure_count = 0
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logger.info("Circuit breaker reset to CLOSED state")
    
    def _on_failure(self):
        """Handle failed operation."""
        self.failed_requests += 1
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker OPENED after {self.failure_count} failures")
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt to reset."""
        if self.last_failure_time is None:
            return False
        
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    @property
    def is_available(self) -> bool:
        """Check if circuit is available for requests."""
        return self.state in [CircuitState.CLOSED, CircuitState.HALF_OPEN]
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests
    
    def get_metrics(self) -> dict[str, Any]:
        """Get circuit breaker metrics."""
        return {
            "state": self.state.value,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.success_rate,
            "failure_count": self.failure_count,
            "is_available": self.is_available
        }


class LoadBalancer:
    """
    Enhanced load balancer with circuit breaker protection.
    
    Distributes requests across providers with health awareness.
    """
    
    def __init__(self, providers: list):
        self.providers = providers
        self.circuit_breakers = {
            provider.name: CircuitBreaker() for provider in providers
        }
        self.request_count = 0
        
    async def execute_with_fallback(self, operation: str, *args, **kwargs) -> Any:
        """Execute operation with automatic fallback."""
        self.request_count += 1
        
        # Get available providers (circuit breaker check)
        available_providers = [
            provider for provider in self.providers
            if (provider.enabled and 
                self.circuit_breakers[provider.name].is_available)
        ]
        
        if not available_providers:
            raise Exception("No available providers - all circuits open")
        
        # Try primary provider first, then fallback
        primary_provider = next(
            (p for p in available_providers if getattr(p.config, 'primary', False)),
            available_providers[0]
        )
        
        # Attempt operation with circuit breaker protection
        circuit = self.circuit_breakers[primary_provider.name]
        
        try:
            operation_func = getattr(primary_provider, operation)
            return await circuit.call(operation_func, *args, **kwargs)
            
        except Exception as primary_error:
            logger.warning(f"Primary provider {primary_provider.name} failed: {primary_error}")
            
            # Try fallback providers
            for fallback_provider in available_providers[1:]:
                if fallback_provider.name == primary_provider.name:
                    continue
                    
                fallback_circuit = self.circuit_breakers[fallback_provider.name]
                if not fallback_circuit.is_available:
                    continue
                
                try:
                    fallback_operation = getattr(fallback_provider, operation)
                    result = await fallback_circuit.call(fallback_operation, *args, **kwargs)
                    logger.info(f"Fallback successful with provider: {fallback_provider.name}")
                    return result
                    
                except Exception as fallback_error:
                    logger.warning(f"Fallback provider {fallback_provider.name} failed: {fallback_error}")
                    continue
            
            # All providers failed
            raise Exception(f"All providers failed for operation: {operation}")
    
    def get_health_status(self) -> dict[str, Any]:
        """Get comprehensive health status."""
        return {
            "total_requests": self.request_count,
            "providers": {
                name: circuit.get_metrics()
                for name, circuit in self.circuit_breakers.items()
            },
            "available_providers": [
                provider.name for provider in self.providers
                if (provider.enabled and 
                    self.circuit_breakers[provider.name].is_available)
            ]
        }


# Connection Pool Optimization
class ConnectionPoolManager:
    """
    Optimized connection pool management for database operations.
    """
    
    def __init__(self):
        self.pools = {}
        self.pool_stats = {}
        
    async def get_optimized_pool(self, provider_name: str, config: dict) -> Any:
        """Get or create optimized connection pool."""
        if provider_name in self.pools:
            return self.pools[provider_name]
        
        # Enhanced pool configuration based on load characteristics
        if "pgvector" in provider_name.lower():
            pool_config = {
                "min_size": 10,      # Increased minimum connections
                "max_size": 30,      # Optimized for 1GB RAM constraint  
                "command_timeout": 20,  # Reduced timeout for faster failover
                "max_queries": 50000,   # Prevent connection exhaustion
                "max_inactive_connection_lifetime": 300  # 5 minutes
            }
        else:
            # Default configuration for other providers
            pool_config = {
                "min_size": 5,
                "max_size": 15,
                "command_timeout": 30
            }
        
        # Create pool with optimized settings
        try:
            # This would integrate with actual pool creation
            # For now, return the config as a placeholder
            pool = {"config": pool_config, "provider": provider_name}
            self.pools[provider_name] = pool
            self.pool_stats[provider_name] = {
                "created_at": time.time(),
                "connections_created": 0,
                "queries_executed": 0
            }
            
            logger.info(f"Created optimized connection pool for {provider_name}")
            return pool
            
        except Exception as e:
            logger.error(f"Failed to create connection pool for {provider_name}: {e}")
            raise
    
    def get_pool_metrics(self) -> dict[str, Any]:
        """Get connection pool performance metrics."""
        return {
            "active_pools": len(self.pools),
            "pool_details": self.pool_stats
        }