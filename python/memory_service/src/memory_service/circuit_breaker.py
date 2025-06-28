"""
Circuit Breaker Pattern for Enhanced Load Balancing

Implements circuit breaker to improve system resilience under load
and prevent cascade failures across providers.
"""

import asyncio
import time
from enum import Enum
from typing import Any, Callable, Optional, Dict, List
import logging
from dataclasses import dataclass

from .config import config
from .logging_config import get_logger
import structlog

logger = get_logger("circuit_breaker")
structlog_logger = structlog.get_logger("circuit_breaker")


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


@dataclass
class FallbackConfig:
    """Configuration for fallback behavior"""
    enabled: bool = True
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout_seconds: float = 30.0
    degraded_mode_threshold: float = 0.5  # Success rate threshold for degraded mode


class StrategicIntelligenceCircuitBreaker:
    """
    Specialized circuit breaker for JARVIS strategic intelligence operations
    
    Provides graceful degradation and fallback for strategic analysis requests.
    """
    
    def __init__(self, fallback_config: Optional[FallbackConfig] = None):
        # Use defensive logging to prevent keyword argument errors
        try:
            self.logger = structlog_logger.bind(component="strategic_intelligence_circuit_breaker")
        except Exception:
            # Fallback to standard logger if structlog binding fails
            self.logger = logger
        self.config = fallback_config or FallbackConfig()
        
        # Main circuit breakers for different components
        self.jarvis_circuit = CircuitBreaker(
            failure_threshold=3,
            timeout=60.0,
            recovery_timeout=30.0
        )
        
        self.strategic_analysis_circuit = CircuitBreaker(
            failure_threshold=2,  # More sensitive for strategic analysis
            timeout=120.0,  # Longer timeout for strategic analysis
            recovery_timeout=45.0
        )
        
        self.enhanced_reasoning_circuit = CircuitBreaker(
            failure_threshold=4,
            timeout=45.0,
            recovery_timeout=20.0
        )
        
        # Fallback strategies
        self.degraded_mode_active = False
        self.fallback_queue: List[Dict[str, Any]] = []
        
        self.logger.info(f"Strategic Intelligence Circuit Breaker initialized: failure_threshold={self.jarvis_circuit.failure_threshold}, timeout={self.jarvis_circuit.timeout}")
    
    async def call_strategic_intelligence(
        self, 
        func: Callable, 
        query: str,
        context: Optional[Dict[str, Any]] = None,
        fallback_enabled: bool = True
    ) -> Any:
        """
        Execute strategic intelligence analysis with circuit breaker protection
        
        Args:
            func: The strategic intelligence function to call
            query: The strategic query
            context: Additional context for analysis
            fallback_enabled: Whether to enable fallback processing
            
        Returns:
            Strategic analysis result or fallback response
        """
        try:
            self.logger.info(f"Executing strategic intelligence call with circuit protection: query_preview={query[:50]}, circuit_state={self.strategic_analysis_circuit.state.value}")
            
            # Attempt strategic intelligence processing
            result = await self.strategic_analysis_circuit.call(func, query, context)
            
            # Check if we should exit degraded mode
            if self.degraded_mode_active and self.strategic_analysis_circuit.success_rate > 0.8:
                self.degraded_mode_active = False
                self.logger.info("Exiting degraded mode - strategic intelligence recovery successful")
            
            return result
            
        except Exception as e:
            self.logger.warning(f"Strategic intelligence circuit breaker failure: error={str(e)}, circuit_state={self.strategic_analysis_circuit.state.value}")
            
            if not fallback_enabled:
                raise
            
            # Activate degraded mode if needed
            if (self.strategic_analysis_circuit.success_rate < self.config.degraded_mode_threshold and
                not self.degraded_mode_active):
                self.degraded_mode_active = True
                self.logger.warning(f"Activating degraded mode for strategic intelligence: success_rate={self.strategic_analysis_circuit.success_rate}")
            
            # Return fallback response
            return await self._provide_strategic_fallback(query, context, str(e))
    
    async def call_enhanced_reasoning(
        self, 
        func: Callable,
        query: str,
        memories: List[Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute enhanced reasoning with circuit breaker protection"""
        try:
            self.logger.info(f"Executing enhanced reasoning call with circuit protection: query_preview={query[:50]}, memory_count={len(memories)}, circuit_state={self.enhanced_reasoning_circuit.state.value}")
            
            result = await self.enhanced_reasoning_circuit.call(func, query, memories, context)
            return result
            
        except Exception as e:
            self.logger.warning(f"Enhanced reasoning circuit breaker failure: error={str(e)}")
            
            # Fallback to basic reasoning summary
            return await self._provide_reasoning_fallback(query, memories, str(e))
    
    async def call_jarvis_service(
        self, 
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute general JARVIS service call with circuit breaker protection"""
        try:
            return await self.jarvis_circuit.call(func, *args, **kwargs)
            
        except Exception as e:
            self.logger.warning(f"JARVIS service circuit breaker failure: error={str(e)}")
            
            # Check JARVIS health and provide appropriate fallback
            if self.jarvis_circuit.state == CircuitState.OPEN:
                return await self._provide_jarvis_unavailable_response()
            
            raise
    
    async def _provide_strategic_fallback(
        self, 
        query: str, 
        context: Optional[Dict[str, Any]], 
        error: str
    ) -> Dict[str, Any]:
        """Provide fallback strategic analysis when main system fails"""
        
        # Queue request for retry when service recovers
        if self.config.enabled:
            self.fallback_queue.append({
                "query": query,
                "context": context,
                "timestamp": time.time(),
                "type": "strategic_analysis"
            })
        
        # Provide basic analysis based on available context
        fallback_analysis = {
            "success": False,
            "analysis_id": f"fallback_strategic_{int(time.time())}",
            "executive_summary": f"""
# Strategic Analysis Fallback Mode

**Query**: {query}

**Status**: Service temporarily unavailable - operating in degraded mode

## Available Information Analysis
{self._analyze_context_basic(context) if context else 'Limited context available for analysis.'}

## Degraded Mode Recommendations
1. **Immediate**: Monitor system recovery and retry analysis when service is restored
2. **Short-term**: Review available data manually for critical insights
3. **Long-term**: Implement additional redundancy for strategic intelligence processing

## Confidence Assessment
- **Overall Confidence**: 25% (Degraded mode operation)
- **Recommendation**: DEFER major decisions until full analysis is available
- **Risk Level**: HIGH - Limited analytical capability

*This is a fallback response. Full strategic intelligence analysis will be available when service recovers.*
            """,
            "strategic_recommendations": [
                "Defer strategic decisions until full analysis is available",
                "Monitor service recovery status",
                "Review available data manually for urgent insights"
            ],
            "confidence_assessment": {
                "overall_confidence": 25.0,
                "decision_recommendation": "DEFER",
                "risk_management": "HIGH RISK - Limited analytical capability",
                "degraded_mode": True
            },
            "implementation_plan": {
                "immediate_actions": ["Monitor service recovery", "Queue request for retry"],
                "short_term": ["Manual review of available data"],
                "long_term": ["Implement additional redundancy"]
            },
            "risk_assessment": {
                "high_risks": ["Strategic analysis incomplete", "Service unavailable"],
                "mitigation_strategies": ["Retry when service recovers", "Manual review"]
            },
            "domain_analyses": {},
            "processing_time": 0.1,
            "intelligence_sources": ["fallback_system"],
            "error": f"Strategic intelligence service failure: {error}",
            "fallback_mode": True
        }
        
        self.logger.info(f"Provided strategic analysis fallback response: query_preview={query[:50]}, confidence=25.0")
        
        return fallback_analysis
    
    async def _provide_reasoning_fallback(
        self, 
        query: str, 
        memories: List[Any], 
        error: str
    ) -> Dict[str, Any]:
        """Provide fallback reasoning analysis"""
        
        # Basic summary of available memories
        memory_summary = ""
        if memories:
            memory_summary = f"Found {len(memories)} relevant memories:\n"
            for i, memory in enumerate(memories[:3], 1):
                content_preview = getattr(memory, 'content', str(memory))[:100]
                memory_summary += f"{i}. {content_preview}...\n"
        else:
            memory_summary = "No relevant memories found."
        
        fallback_reasoning = {
            "success": False,
            "task_id": f"fallback_reasoning_{int(time.time())}",
            "summary": f"Basic analysis of query: {query[:100]}",
            "decision": {
                "decision": f"Enhanced reasoning unavailable. Basic summary: {memory_summary}",
                "confidence": 0.3
            },
            "agent_outputs": {},
            "performance": {
                "iterations": 0,
                "duration_seconds": 0.1,
                "learning_opportunities": 0,
                "improvement_suggestions": 0
            },
            "error": f"Enhanced reasoning service failure: {error}",
            "enhancement_type": "fallback_reasoning",
            "fallback_mode": True
        }
        
        self.logger.info(f"Provided reasoning analysis fallback response: query_preview={query[:50]}, memory_count={len(memories)}")
        
        return fallback_reasoning
    
    async def _provide_jarvis_unavailable_response(self) -> Dict[str, Any]:
        """Provide response when JARVIS service is completely unavailable"""
        return {
            "success": False,
            "error": "JARVIS service is currently unavailable",
            "fallback_mode": True,
            "retry_after": self.jarvis_circuit.recovery_timeout,
            "message": "Service temporarily unavailable. Please try again later."
        }
    
    def _analyze_context_basic(self, context: Dict[str, Any]) -> str:
        """Provide basic context analysis for fallback mode"""
        analysis_parts = []
        
        if context.get("retrieved_memories"):
            memory_count = len(context["retrieved_memories"])
            analysis_parts.append(f"- Found {memory_count} relevant memories in knowledge base")
        
        if context.get("user_context"):
            analysis_parts.append("- User context available for personalization")
        
        if context.get("total_memories_found", 0) > 0:
            total = context["total_memories_found"]
            analysis_parts.append(f"- Total knowledge base contains {total} relevant entries")
        
        return "\n".join(analysis_parts) if analysis_parts else "Limited context available."
    
    def get_circuit_status(self) -> Dict[str, Any]:
        """Get comprehensive circuit breaker status"""
        return {
            "strategic_intelligence": self.strategic_analysis_circuit.get_metrics(),
            "enhanced_reasoning": self.enhanced_reasoning_circuit.get_metrics(),
            "jarvis_service": self.jarvis_circuit.get_metrics(),
            "degraded_mode_active": self.degraded_mode_active,
            "fallback_queue_size": len(self.fallback_queue),
            "overall_health": self._calculate_overall_health()
        }
    
    def _calculate_overall_health(self) -> str:
        """Calculate overall system health based on circuit states"""
        circuits = [
            self.strategic_analysis_circuit,
            self.enhanced_reasoning_circuit,
            self.jarvis_circuit
        ]
        
        available_circuits = sum(1 for circuit in circuits if circuit.is_available)
        total_circuits = len(circuits)
        
        health_percentage = (available_circuits / total_circuits) * 100
        
        if health_percentage >= 100:
            return "HEALTHY"
        elif health_percentage >= 66:
            return "DEGRADED"
        elif health_percentage >= 33:
            return "CRITICAL"
        else:
            return "FAILURE"
    
    async def process_fallback_queue(self):
        """Process queued requests when services recover"""
        if not self.fallback_queue:
            return
        
        self.logger.info(f"Processing fallback queue: queue_size={len(self.fallback_queue)}")
        
        # Only process if circuits are healthy
        if self.strategic_analysis_circuit.is_available:
            processed = 0
            queue_copy = self.fallback_queue.copy()
            self.fallback_queue.clear()
            
            for request in queue_copy:
                try:
                    # Check if request is still relevant (not too old)
                    age = time.time() - request["timestamp"]
                    if age > 3600:  # 1 hour old
                        continue
                    
                    # Re-queue for background processing
                    # This would integrate with actual background task system
                    self.logger.info(f"Re-queued fallback request for processing: request_type={request['type']}, age_seconds={age}")
                    processed += 1
                    
                except Exception as e:
                    self.logger.error(f"Failed to process fallback request: error={str(e)}")
            
            self.logger.info(f"Fallback queue processing completed: processed_count={processed}")


class CircuitBreakerManager:
    """
    Central manager for all circuit breakers in the system
    
    Provides unified access and monitoring for all circuit breaker instances.
    """
    
    def __init__(self):
        # Use defensive logging to prevent keyword argument errors
        try:
            self.logger = structlog_logger.bind(component="circuit_breaker_manager")
        except Exception:
            # Fallback to standard logger if structlog binding fails
            self.logger = logger
        
        # Initialize specialized circuit breakers
        self.strategic_intelligence = StrategicIntelligenceCircuitBreaker()
        self.memory_store = CircuitBreaker(failure_threshold=5, timeout=30.0, recovery_timeout=15.0)
        self.embedding_service = CircuitBreaker(failure_threshold=4, timeout=20.0, recovery_timeout=10.0)
        
        # Global circuit breaker registry
        self.circuit_registry = {
            "strategic_intelligence": self.strategic_intelligence,
            "memory_store": self.memory_store,
            "embedding_service": self.embedding_service
        }
        
        self.logger.info(f"Circuit Breaker Manager initialized: circuit_count={len(self.circuit_registry)}")
    
    async def call_memory_store(self, func: Callable, *args, **kwargs) -> Any:
        """Execute memory store operation with circuit breaker protection"""
        try:
            return await self.memory_store.call(func, *args, **kwargs)
        except Exception as e:
            self.logger.error(f"Memory store circuit breaker failure: error={str(e)}")
            raise
    
    async def call_embedding_service(self, func: Callable, *args, **kwargs) -> Any:
        """Execute embedding service operation with circuit breaker protection"""
        try:
            return await self.embedding_service.call(func, *args, **kwargs)
        except Exception as e:
            self.logger.error(f"Embedding service circuit breaker failure: error={str(e)}")
            # Could provide embedding fallback here
            raise
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health status"""
        health_data = {
            "timestamp": time.time(),
            "overall_status": "UNKNOWN",
            "circuit_breakers": {}
        }
        
        # Collect status from all circuits
        for name, circuit in self.circuit_registry.items():
            if hasattr(circuit, 'get_circuit_status'):
                health_data["circuit_breakers"][name] = circuit.get_circuit_status()
            else:
                health_data["circuit_breakers"][name] = circuit.get_metrics()
        
        # Calculate overall system status
        total_circuits = len(self.circuit_registry)
        healthy_circuits = sum(
            1 for circuit in self.circuit_registry.values()
            if (hasattr(circuit, 'is_available') and circuit.is_available) or
               (hasattr(circuit, '_calculate_overall_health') and 
                circuit._calculate_overall_health() in ["HEALTHY", "DEGRADED"])
        )
        
        health_percentage = (healthy_circuits / total_circuits) * 100
        
        if health_percentage >= 100:
            health_data["overall_status"] = "HEALTHY"
        elif health_percentage >= 75:
            health_data["overall_status"] = "DEGRADED"
        elif health_percentage >= 50:
            health_data["overall_status"] = "CRITICAL"
        else:
            health_data["overall_status"] = "FAILURE"
        
        health_data["health_percentage"] = health_percentage
        
        return health_data
    
    async def run_health_check_cycle(self):
        """Run periodic health checks and maintenance"""
        try:
            # Process any fallback queues
            if hasattr(self.strategic_intelligence, 'process_fallback_queue'):
                await self.strategic_intelligence.process_fallback_queue()
            
            # Log health status
            health = self.get_system_health()
            self.logger.info(f"Health check cycle completed: overall_status={health['overall_status']}, health_percentage={health['health_percentage']}")
            
        except Exception as e:
            self.logger.error(f"Health check cycle failed: error={str(e)}")


# Global circuit breaker manager instance
_circuit_manager: Optional[CircuitBreakerManager] = None

async def get_circuit_manager() -> CircuitBreakerManager:
    """Get the global circuit breaker manager instance"""
    global _circuit_manager
    if _circuit_manager is None:
        _circuit_manager = CircuitBreakerManager()
    return _circuit_manager

# Convenience functions for common operations
async def call_with_strategic_circuit(func: Callable, query: str, context: Optional[Dict[str, Any]] = None) -> Any:
    """Execute strategic intelligence call with circuit breaker protection"""
    manager = await get_circuit_manager()
    return await manager.strategic_intelligence.call_strategic_intelligence(func, query, context)

async def call_with_reasoning_circuit(
    func: Callable, 
    query: str, 
    memories: List[Any], 
    context: Optional[Dict[str, Any]] = None
) -> Any:
    """Execute enhanced reasoning call with circuit breaker protection"""
    manager = await get_circuit_manager()
    return await manager.strategic_intelligence.call_enhanced_reasoning(func, query, memories, context)

async def call_with_jarvis_circuit(func: Callable, *args, **kwargs) -> Any:
    """Execute JARVIS service call with circuit breaker protection"""
    manager = await get_circuit_manager()
    return await manager.strategic_intelligence.call_jarvis_service(func, *args, **kwargs)

async def call_with_memory_circuit(func: Callable, *args, **kwargs) -> Any:
    """Execute memory store call with circuit breaker protection"""
    manager = await get_circuit_manager()
    return await manager.call_memory_store(func, *args, **kwargs)

async def call_with_embedding_circuit(func: Callable, *args, **kwargs) -> Any:
    """Execute embedding service call with circuit breaker protection"""
    manager = await get_circuit_manager()
    return await manager.call_embedding_service(func, *args, **kwargs)

async def get_system_health() -> Dict[str, Any]:
    """Get comprehensive system health status"""
    manager = await get_circuit_manager()
    return manager.get_system_health()