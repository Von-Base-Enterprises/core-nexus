"""
Provider Intelligence Engine for Core Nexus Memory Service

Implements smart provider selection, performance-based routing, and adaptive
load balancing optimized for multi-provider vector storage architecture.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict, deque

from .models import QueryRequest, MemoryResponse
from .unified_store import VectorProvider

logger = logging.getLogger(__name__)


class ProviderHealth(Enum):
    """Provider health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics for a provider"""
    # Latency metrics
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    
    # Success metrics
    success_rate: float = 1.0
    total_requests: int = 0
    failed_requests: int = 0
    timeout_requests: int = 0
    
    # Resource metrics
    memory_efficiency: float = 1.0
    cpu_efficiency: float = 1.0
    throughput_qps: float = 0.0
    
    # Quality metrics
    avg_result_quality: float = 1.0
    result_consistency: float = 1.0
    
    # Time tracking
    last_updated: float = field(default_factory=time.time)
    measurement_window_start: float = field(default_factory=time.time)
    
    def update_latency(self, latency_ms: float):
        """Update latency metrics with new measurement"""
        alpha = 0.1  # Exponential moving average factor
        self.avg_latency_ms = (1 - alpha) * self.avg_latency_ms + alpha * latency_ms
        self.last_updated = time.time()
    
    def update_success(self, success: bool, is_timeout: bool = False):
        """Update success rate metrics"""
        self.total_requests += 1
        if not success:
            self.failed_requests += 1
            if is_timeout:
                self.timeout_requests += 1
        
        self.success_rate = 1.0 - (self.failed_requests / self.total_requests)
        self.last_updated = time.time()
    
    def get_health_score(self) -> float:
        """Calculate overall health score (0.0 to 1.0)"""
        # Weight different factors
        latency_score = max(0, 1.0 - (self.avg_latency_ms / 2000))  # 2s = 0 score
        success_score = self.success_rate
        efficiency_score = (self.memory_efficiency + self.cpu_efficiency) / 2
        quality_score = (self.avg_result_quality + self.result_consistency) / 2
        
        # Weighted combination
        weights = [0.3, 0.4, 0.2, 0.1]  # latency, success, efficiency, quality
        scores = [latency_score, success_score, efficiency_score, quality_score]
        
        return sum(w * s for w, s in zip(weights, scores))


@dataclass
class QueryCharacteristics:
    """Characteristics of a query for provider selection"""
    complexity_score: float = 0.0
    result_size: int = 0
    has_filters: bool = False
    filter_complexity: float = 0.0
    is_temporal: bool = False  # Query involves time-based filtering
    is_similarity_heavy: bool = True  # Requires vector similarity
    expected_memory_mb: float = 0.0
    priority: str = "normal"  # low, normal, high


class ProviderCapabilities:
    """Tracks provider capabilities and specializations"""
    
    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.specializations = set()
        self.optimal_query_types = set()
        self.max_concurrent_queries = 10
        self.memory_limit_mb = 100
        self.supports_filters = True
        self.supports_temporal_queries = True
        self.vector_dimension_support = [1536]  # Supported embedding dimensions
        
        # Initialize based on provider type
        self._initialize_capabilities()
    
    def _initialize_capabilities(self):
        """Initialize capabilities based on provider type"""
        if self.provider_name.lower() == 'pgvector':
            self.specializations.update(['complex_filters', 'temporal_queries', 'joins'])
            self.optimal_query_types.update(['filtered_search', 'recent_memories'])
            self.max_concurrent_queries = 20
            self.memory_limit_mb = 200
            
        elif self.provider_name.lower() == 'chromadb':
            self.specializations.update(['pure_similarity', 'fast_retrieval', 'small_datasets'])
            self.optimal_query_types.update(['similarity_search', 'embedding_lookup'])
            self.max_concurrent_queries = 15
            self.memory_limit_mb = 50
            
        elif self.provider_name.lower() == 'pinecone':
            self.specializations.update(['large_scale', 'cloud_distributed', 'high_throughput'])
            self.optimal_query_types.update(['similarity_search', 'large_datasets'])
            self.max_concurrent_queries = 50
            self.memory_limit_mb = 500
    
    def is_optimal_for_query(self, characteristics: QueryCharacteristics) -> float:
        """Calculate optimization score for query characteristics (0.0 to 1.0)"""
        score = 0.5  # Base score
        
        # Check specializations
        if characteristics.has_filters and 'complex_filters' in self.specializations:
            score += 0.2
        
        if characteristics.is_temporal and 'temporal_queries' in self.specializations:
            score += 0.15
        
        if characteristics.is_similarity_heavy and 'pure_similarity' in self.specializations:
            score += 0.1
        
        # Check memory requirements
        if characteristics.expected_memory_mb <= self.memory_limit_mb:
            score += 0.1
        else:
            score -= 0.2  # Penalty for exceeding memory limit
        
        # Check complexity handling
        if characteristics.complexity_score > 0.7 and 'complex_filters' in self.specializations:
            score += 0.1
        elif characteristics.complexity_score < 0.3 and 'fast_retrieval' in self.specializations:
            score += 0.1
        
        return max(0.0, min(1.0, score))


class LoadBalancer:
    """Intelligent load balancer for provider selection"""
    
    def __init__(self):
        self.active_queries: Dict[str, int] = defaultdict(int)  # provider -> count
        self.query_queue: Dict[str, deque] = defaultdict(deque)  # provider -> queue
        self.routing_history: List[Tuple[str, float, bool]] = []  # provider, latency, success
        self._lock = asyncio.Lock()
    
    async def select_provider(
        self, 
        available_providers: List[VectorProvider],
        provider_metrics: Dict[str, PerformanceMetrics],
        provider_capabilities: Dict[str, ProviderCapabilities],
        query_characteristics: QueryCharacteristics
    ) -> List[VectorProvider]:
        """Select optimal provider(s) for query execution"""
        
        async with self._lock:
            # Score each provider
            provider_scores = []
            
            for provider in available_providers:
                if not provider.enabled:
                    continue
                
                score = await self._calculate_provider_score(
                    provider, 
                    provider_metrics.get(provider.name, PerformanceMetrics()),
                    provider_capabilities.get(provider.name, ProviderCapabilities(provider.name)),
                    query_characteristics
                )
                
                provider_scores.append((score, provider))
            
            # Sort by score (highest first)
            provider_scores.sort(key=lambda x: x[0], reverse=True)
            
            # Select providers based on query priority and load
            selected_providers = self._select_optimal_providers(
                provider_scores, query_characteristics
            )
            
            # Track provider usage
            for provider in selected_providers:
                self.active_queries[provider.name] += 1
            
            return selected_providers
    
    async def _calculate_provider_score(
        self,
        provider: VectorProvider,
        metrics: PerformanceMetrics,
        capabilities: ProviderCapabilities,
        characteristics: QueryCharacteristics
    ) -> float:
        """Calculate comprehensive provider score"""
        
        # Base health score
        health_score = metrics.get_health_score()
        
        # Capability match score
        capability_score = capabilities.is_optimal_for_query(characteristics)
        
        # Load score (prefer less loaded providers)
        current_load = self.active_queries[provider.name]
        max_load = capabilities.max_concurrent_queries
        load_score = max(0, 1.0 - (current_load / max_load))
        
        # Recent performance score
        recent_performance = self._get_recent_performance_score(provider.name)
        
        # Combine scores with weights
        weights = [0.4, 0.3, 0.2, 0.1]  # health, capability, load, recent
        scores = [health_score, capability_score, load_score, recent_performance]
        
        final_score = sum(w * s for w, s in zip(weights, scores))
        
        logger.debug(
            f"Provider {provider.name} score: {final_score:.3f} "
            f"(health: {health_score:.3f}, capability: {capability_score:.3f}, "
            f"load: {load_score:.3f}, recent: {recent_performance:.3f})"
        )
        
        return final_score
    
    def _select_optimal_providers(
        self, 
        provider_scores: List[Tuple[float, VectorProvider]], 
        characteristics: QueryCharacteristics
    ) -> List[VectorProvider]:
        """Select providers based on query requirements"""
        
        if not provider_scores:
            return []
        
        # High priority queries get multiple providers
        if characteristics.priority == "high":
            return [provider for _, provider in provider_scores[:3]]
        
        # Complex queries might benefit from multiple providers
        elif characteristics.complexity_score > 0.7:
            return [provider for _, provider in provider_scores[:2]]
        
        # Simple queries use single best provider
        else:
            return [provider_scores[0][1]]
    
    def _get_recent_performance_score(self, provider_name: str) -> float:
        """Get recent performance score based on routing history"""
        recent_entries = [
            (latency, success) for prov, latency, success in self.routing_history[-50:]
            if prov == provider_name
        ]
        
        if not recent_entries:
            return 0.8  # Neutral score for no history
        
        avg_latency = sum(latency for latency, _ in recent_entries) / len(recent_entries)
        success_rate = sum(success for _, success in recent_entries) / len(recent_entries)
        
        latency_score = max(0, 1.0 - (avg_latency / 1000))  # 1s = 0 score
        
        return (latency_score + success_rate) / 2
    
    async def record_query_completion(
        self, 
        provider_name: str, 
        latency_ms: float, 
        success: bool
    ):
        """Record query completion for performance tracking"""
        async with self._lock:
            # Decrease active query count
            if self.active_queries[provider_name] > 0:
                self.active_queries[provider_name] -= 1
            
            # Record in history
            self.routing_history.append((provider_name, latency_ms, success))
            
            # Keep history bounded
            if len(self.routing_history) > 1000:
                self.routing_history = self.routing_history[-500:]
    
    async def get_load_stats(self) -> Dict[str, Any]:
        """Get current load balancing statistics"""
        return {
            'active_queries': dict(self.active_queries),
            'routing_history_size': len(self.routing_history),
            'recent_performance': self._analyze_recent_performance()
        }
    
    def _analyze_recent_performance(self) -> Dict[str, Any]:
        """Analyze recent performance across providers"""
        provider_stats = defaultdict(lambda: {'total': 0, 'success': 0, 'latency_sum': 0})
        
        for provider, latency, success in self.routing_history[-100:]:
            stats = provider_stats[provider]
            stats['total'] += 1
            if success:
                stats['success'] += 1
            stats['latency_sum'] += latency
        
        return {
            provider: {
                'success_rate': stats['success'] / stats['total'] if stats['total'] > 0 else 0,
                'avg_latency_ms': stats['latency_sum'] / stats['total'] if stats['total'] > 0 else 0,
                'query_count': stats['total']
            }
            for provider, stats in provider_stats.items()
        }


class ProviderIntelligenceEngine:
    """
    Advanced provider intelligence engine for optimal query routing
    """
    
    def __init__(self):
        self.provider_metrics: Dict[str, PerformanceMetrics] = {}
        self.provider_capabilities: Dict[str, ProviderCapabilities] = {}
        self.load_balancer = LoadBalancer()
        self.monitoring_enabled = True
        self._last_health_check = 0
        self._health_check_interval = 30  # seconds
    
    async def initialize_provider(self, provider: VectorProvider):
        """Initialize tracking for a new provider"""
        provider_name = provider.name
        
        if provider_name not in self.provider_metrics:
            self.provider_metrics[provider_name] = PerformanceMetrics()
        
        if provider_name not in self.provider_capabilities:
            self.provider_capabilities[provider_name] = ProviderCapabilities(provider_name)
        
        logger.info(f"Initialized intelligence tracking for provider: {provider_name}")
    
    async def analyze_query_characteristics(self, request: QueryRequest) -> QueryCharacteristics:
        """Analyze query to determine optimal routing"""
        characteristics = QueryCharacteristics()
        
        # Analyze query complexity
        if request.query:
            word_count = len(request.query.split())
            char_count = len(request.query)
            characteristics.complexity_score = min(1.0, (word_count / 20 + char_count / 500) / 2)
        
        # Analyze result requirements
        characteristics.result_size = request.limit
        characteristics.has_filters = bool(request.filters)
        
        if request.filters:
            characteristics.filter_complexity = min(1.0, len(request.filters) / 10)
            
            # Check for temporal queries
            temporal_keys = ['created_at', 'timestamp', 'date', 'time']
            characteristics.is_temporal = any(
                any(key in str(filter_key).lower() for key in temporal_keys)
                for filter_key in request.filters.keys()
            )
        
        # Estimate memory requirements
        characteristics.expected_memory_mb = (
            characteristics.result_size * 0.01 +  # ~10KB per result
            characteristics.complexity_score * 5 +  # Complex queries need more memory
            (10 if characteristics.has_filters else 0)  # Filter processing overhead
        )
        
        # Determine if this is primarily similarity-based
        characteristics.is_similarity_heavy = bool(request.query)
        
        logger.debug(f"Query characteristics: complexity={characteristics.complexity_score:.2f}, "
                    f"filters={characteristics.has_filters}, temporal={characteristics.is_temporal}")
        
        return characteristics
    
    async def select_optimal_providers(
        self, 
        available_providers: List[VectorProvider],
        request: QueryRequest
    ) -> List[VectorProvider]:
        """Select optimal providers for query execution"""
        
        # Analyze query characteristics
        characteristics = await self.analyze_query_characteristics(request)
        
        # Initialize any new providers
        for provider in available_providers:
            await self.initialize_provider(provider)
        
        # Use load balancer to select providers
        selected_providers = await self.load_balancer.select_provider(
            available_providers,
            self.provider_metrics,
            self.provider_capabilities,
            characteristics
        )
        
        logger.info(f"Selected {len(selected_providers)} providers for query: "
                   f"{[p.name for p in selected_providers]}")
        
        return selected_providers
    
    async def record_query_performance(
        self, 
        provider_name: str, 
        latency_ms: float, 
        success: bool,
        is_timeout: bool = False,
        result_quality: Optional[float] = None
    ):
        """Record query performance metrics"""
        
        if provider_name not in self.provider_metrics:
            self.provider_metrics[provider_name] = PerformanceMetrics()
        
        metrics = self.provider_metrics[provider_name]
        
        # Update metrics
        metrics.update_latency(latency_ms)
        metrics.update_success(success, is_timeout)
        
        if result_quality is not None:
            alpha = 0.1
            metrics.avg_result_quality = (
                (1 - alpha) * metrics.avg_result_quality + alpha * result_quality
            )
        
        # Update load balancer
        await self.load_balancer.record_query_completion(provider_name, latency_ms, success)
        
        logger.debug(f"Recorded performance for {provider_name}: "
                    f"{latency_ms:.1f}ms, success={success}")
    
    async def get_provider_health(self, provider_name: str) -> ProviderHealth:
        """Get current health status of a provider"""
        if provider_name not in self.provider_metrics:
            return ProviderHealth.OFFLINE
        
        metrics = self.provider_metrics[provider_name]
        health_score = metrics.get_health_score()
        
        if health_score >= 0.8:
            return ProviderHealth.HEALTHY
        elif health_score >= 0.6:
            return ProviderHealth.DEGRADED
        else:
            return ProviderHealth.UNHEALTHY
    
    async def optimize_provider_configuration(self, provider_name: str) -> Dict[str, Any]:
        """Generate optimization recommendations for a provider"""
        if provider_name not in self.provider_metrics:
            return {'error': 'Provider not found'}
        
        metrics = self.provider_metrics[provider_name]
        capabilities = self.provider_capabilities.get(provider_name)
        
        recommendations = []
        
        # Latency optimizations
        if metrics.avg_latency_ms > 500:
            recommendations.append({
                'type': 'latency',
                'issue': f'High average latency: {metrics.avg_latency_ms:.1f}ms',
                'recommendation': 'Consider connection pooling optimization or query caching'
            })
        
        # Success rate optimizations
        if metrics.success_rate < 0.95:
            recommendations.append({
                'type': 'reliability',
                'issue': f'Low success rate: {metrics.success_rate:.1%}',
                'recommendation': 'Investigate connection stability and error handling'
            })
        
        # Throughput optimizations
        if capabilities and metrics.total_requests > capabilities.max_concurrent_queries * 0.8:
            recommendations.append({
                'type': 'capacity',
                'issue': 'Approaching concurrent query limit',
                'recommendation': 'Consider increasing connection pool size or load balancing'
            })
        
        return {
            'provider': provider_name,
            'health_score': metrics.get_health_score(),
            'recommendations': recommendations,
            'current_metrics': {
                'avg_latency_ms': metrics.avg_latency_ms,
                'success_rate': metrics.success_rate,
                'total_requests': metrics.total_requests
            }
        }
    
    async def get_comprehensive_intelligence_report(self) -> Dict[str, Any]:
        """Generate comprehensive intelligence report"""
        provider_reports = {}
        
        for provider_name in self.provider_metrics:
            health = await self.get_provider_health(provider_name)
            optimization = await self.optimize_provider_configuration(provider_name)
            
            provider_reports[provider_name] = {
                'health': health.value,
                'metrics': self.provider_metrics[provider_name],
                'optimization': optimization
            }
        
        load_stats = await self.load_balancer.get_load_stats()
        
        return {
            'providers': provider_reports,
            'load_balancing': load_stats,
            'system_health': {
                'total_providers': len(self.provider_metrics),
                'healthy_providers': sum(
                    1 for name in self.provider_metrics 
                    if await self.get_provider_health(name) == ProviderHealth.HEALTHY
                ),
                'monitoring_enabled': self.monitoring_enabled
            }
        }
    
    async def adaptive_rebalance(self):
        """Perform adaptive rebalancing based on current performance"""
        logger.info("Starting adaptive provider rebalancing...")
        
        # Analyze current performance
        total_requests = sum(m.total_requests for m in self.provider_metrics.values())
        
        if total_requests < 100:
            logger.info("Insufficient data for rebalancing")
            return
        
        # Update provider capabilities based on observed performance
        for provider_name, metrics in self.provider_metrics.items():
            if provider_name in self.provider_capabilities:
                capabilities = self.provider_capabilities[provider_name]
                
                # Adjust concurrent query limits based on performance
                if metrics.success_rate > 0.95 and metrics.avg_latency_ms < 200:
                    capabilities.max_concurrent_queries = min(
                        capabilities.max_concurrent_queries * 1.1, 100
                    )
                elif metrics.success_rate < 0.9 or metrics.avg_latency_ms > 1000:
                    capabilities.max_concurrent_queries = max(
                        capabilities.max_concurrent_queries * 0.9, 5
                    )
        
        logger.info("Adaptive rebalancing completed")


# Singleton instance
provider_intelligence = ProviderIntelligenceEngine()