"""
Intelligent Query Orchestrator for Core Nexus Memory Service

Optimizes query execution with parallel multi-provider support, intelligent routing,
and advanced performance optimizations for 1GB RAM PostgreSQL deployment.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from .models import QueryRequest, QueryResponse, MemoryResponse
from .unified_store import VectorProvider

logger = logging.getLogger(__name__)


@dataclass
class QueryPlan:
    """Represents an optimized query execution plan"""
    providers: List[VectorProvider]
    execution_strategy: str  # 'parallel', 'sequential', 'primary_only'
    estimated_cost: float
    memory_usage_mb: float
    expected_latency_ms: float
    use_cache: bool
    batch_size: Optional[int] = None


@dataclass
class ProviderPerformance:
    """Tracks performance metrics for each provider"""
    name: str
    avg_latency_ms: float
    success_rate: float
    memory_efficiency: float
    query_capacity: int
    last_updated: float
    total_queries: int = 0
    failed_queries: int = 0


class QueryComplexityAnalyzer:
    """Analyzes query complexity for optimization decisions"""
    
    @staticmethod
    def analyze_query(request: QueryRequest) -> Dict[str, Any]:
        """Analyze query complexity and characteristics"""
        complexity = {
            'score': 0.0,
            'factors': {},
            'recommendations': []
        }
        
        # Query text complexity
        if request.query:
            text_length = len(request.query)
            word_count = len(request.query.split())
            complexity['factors']['text_complexity'] = min(1.0, text_length / 1000)
            complexity['factors']['word_count'] = word_count
            complexity['score'] += complexity['factors']['text_complexity'] * 0.2
        
        # Result set size impact
        limit_factor = min(1.0, request.limit / 1000)
        complexity['factors']['result_size'] = limit_factor
        complexity['score'] += limit_factor * 0.3
        
        # Filter complexity
        filter_count = len(request.filters) if request.filters else 0
        filter_complexity = min(1.0, filter_count / 10)
        complexity['factors']['filter_complexity'] = filter_complexity
        complexity['score'] += filter_complexity * 0.2
        
        # Similarity threshold impact (lower threshold = more complex)
        similarity_factor = 1.0 - request.min_similarity
        complexity['factors']['similarity_breadth'] = similarity_factor
        complexity['score'] += similarity_factor * 0.3
        
        # Add recommendations based on complexity
        if complexity['score'] > 0.7:
            complexity['recommendations'].append('use_parallel_providers')
            complexity['recommendations'].append('enable_aggressive_caching')
        elif complexity['score'] > 0.4:
            complexity['recommendations'].append('use_primary_with_fallback')
        else:
            complexity['recommendations'].append('use_primary_only')
            
        return complexity


class QueryOptimizer:
    """Optimizes query execution plans based on performance data"""
    
    def __init__(self):
        self.provider_performance: Dict[str, ProviderPerformance] = {}
        self.query_patterns: Dict[str, Any] = {}
        
    async def create_execution_plan(
        self, 
        request: QueryRequest, 
        available_providers: List[VectorProvider],
        complexity_analysis: Dict[str, Any]
    ) -> QueryPlan:
        """Create optimal execution plan for the query"""
        
        # Analyze provider performance
        best_providers = self._rank_providers(available_providers, request)
        
        # Determine execution strategy
        strategy = self._determine_strategy(complexity_analysis, best_providers)
        
        # Estimate costs and performance
        cost_estimate = self._estimate_cost(request, best_providers, strategy)
        memory_estimate = self._estimate_memory_usage(request, strategy)
        latency_estimate = self._estimate_latency(request, best_providers, strategy)
        
        # Determine optimal providers for this plan
        if strategy == 'parallel':
            selected_providers = best_providers[:min(3, len(best_providers))]
        elif strategy == 'sequential':
            selected_providers = best_providers[:2]
        else:  # primary_only
            selected_providers = best_providers[:1]
        
        return QueryPlan(
            providers=selected_providers,
            execution_strategy=strategy,
            estimated_cost=cost_estimate,
            memory_usage_mb=memory_estimate,
            expected_latency_ms=latency_estimate,
            use_cache=complexity_analysis['score'] < 0.6,  # Cache simpler queries
            batch_size=min(request.limit, 100) if request.limit > 100 else None
        )
    
    def _rank_providers(
        self, 
        providers: List[VectorProvider], 
        request: QueryRequest
    ) -> List[VectorProvider]:
        """Rank providers by expected performance for this query"""
        ranked = []
        
        for provider in providers:
            if not provider.enabled:
                continue
                
            performance = self.provider_performance.get(provider.name)
            if not performance:
                # Initialize performance tracking for new providers
                performance = ProviderPerformance(
                    name=provider.name,
                    avg_latency_ms=100.0,  # Default estimate
                    success_rate=1.0,
                    memory_efficiency=0.8,
                    query_capacity=100,
                    last_updated=time.time()
                )
                self.provider_performance[provider.name] = performance
            
            # Calculate ranking score based on multiple factors
            score = self._calculate_provider_score(provider, performance, request)
            ranked.append((score, provider))
        
        # Sort by score (higher is better) and return providers
        ranked.sort(key=lambda x: x[0], reverse=True)
        return [provider for _, provider in ranked]
    
    def _calculate_provider_score(
        self, 
        provider: VectorProvider, 
        performance: ProviderPerformance, 
        request: QueryRequest
    ) -> float:
        """Calculate provider score for query routing"""
        score = 0.0
        
        # Latency factor (lower latency = higher score)
        latency_score = max(0, 1.0 - (performance.avg_latency_ms / 1000))
        score += latency_score * 0.4
        
        # Success rate factor
        score += performance.success_rate * 0.3
        
        # Memory efficiency factor
        score += performance.memory_efficiency * 0.2
        
        # Provider-specific optimizations
        if provider.name == 'pgvector':
            # pgvector is excellent for complex filters and recent data
            if request.filters and len(request.filters) > 2:
                score += 0.1
            if any('created_at' in str(f) or 'timestamp' in str(f) 
                   for f in (request.filters or {}).keys()):
                score += 0.15
        
        elif provider.name == 'chromadb':
            # ChromaDB is excellent for pure similarity search
            if not request.filters or len(request.filters) <= 1:
                score += 0.1
            if request.limit <= 50:  # Better for smaller result sets
                score += 0.05
        
        # Capacity consideration (avoid overloaded providers)
        if performance.total_queries > performance.query_capacity:
            score *= 0.8
        
        return max(0.0, min(1.0, score))
    
    def _determine_strategy(
        self, 
        complexity_analysis: Dict[str, Any], 
        ranked_providers: List[VectorProvider]
    ) -> str:
        """Determine optimal execution strategy"""
        if len(ranked_providers) < 2:
            return 'primary_only'
        
        complexity_score = complexity_analysis['score']
        recommendations = complexity_analysis['recommendations']
        
        if 'use_parallel_providers' in recommendations and len(ranked_providers) >= 3:
            return 'parallel'
        elif 'use_primary_with_fallback' in recommendations and len(ranked_providers) >= 2:
            return 'sequential'
        else:
            return 'primary_only'
    
    def _estimate_cost(
        self, 
        request: QueryRequest, 
        providers: List[VectorProvider], 
        strategy: str
    ) -> float:
        """Estimate computational cost of query execution"""
        base_cost = 1.0
        
        # Query complexity factors
        if request.query:
            base_cost += len(request.query) / 1000
        
        base_cost += request.limit / 1000
        base_cost += len(request.filters or {}) * 0.1
        
        # Strategy multipliers
        if strategy == 'parallel':
            base_cost *= len(providers) * 0.8  # Parallel efficiency
        elif strategy == 'sequential':
            base_cost *= len(providers) * 1.2  # Sequential overhead
        
        return base_cost
    
    def _estimate_memory_usage(self, request: QueryRequest, strategy: str) -> float:
        """Estimate memory usage in MB"""
        # Base memory for query processing
        base_memory = 5.0  # MB
        
        # Memory for result storage (rough estimate)
        result_memory = request.limit * 0.002  # ~2KB per result
        
        # Memory for embeddings (1536 dimensions * 4 bytes per float)
        embedding_memory = 1536 * 4 / 1024 / 1024  # ~6KB per embedding
        
        # Strategy overhead
        if strategy == 'parallel':
            multiplier = 1.5  # Multiple providers in parallel
        elif strategy == 'sequential':
            multiplier = 1.2  # Sequential overhead
        else:
            multiplier = 1.0
        
        total_memory = (base_memory + result_memory + embedding_memory) * multiplier
        return total_memory
    
    def _estimate_latency(
        self, 
        request: QueryRequest, 
        providers: List[VectorProvider], 
        strategy: str
    ) -> float:
        """Estimate query latency in milliseconds"""
        if not providers:
            return 1000.0  # Default high latency
        
        # Get average latency from performance data
        avg_latencies = []
        for provider in providers:
            performance = self.provider_performance.get(provider.name)
            if performance:
                avg_latencies.append(performance.avg_latency_ms)
            else:
                avg_latencies.append(100.0)  # Default estimate
        
        if strategy == 'parallel':
            # Parallel execution - limited by slowest provider
            return max(avg_latencies) + 20  # 20ms coordination overhead
        elif strategy == 'sequential':
            # Sequential execution - sum of all providers
            return sum(avg_latencies) + 10  # 10ms coordination overhead
        else:
            # Single provider
            return avg_latencies[0] if avg_latencies else 100.0
    
    async def update_provider_performance(
        self, 
        provider_name: str, 
        latency_ms: float, 
        success: bool, 
        memory_used_mb: float = 0.0
    ):
        """Update provider performance metrics"""
        if provider_name not in self.provider_performance:
            self.provider_performance[provider_name] = ProviderPerformance(
                name=provider_name,
                avg_latency_ms=latency_ms,
                success_rate=1.0 if success else 0.0,
                memory_efficiency=1.0,
                query_capacity=100,
                last_updated=time.time(),
                total_queries=1,
                failed_queries=0 if success else 1
            )
            return
        
        perf = self.provider_performance[provider_name]
        
        # Update moving averages
        alpha = 0.1  # Smoothing factor
        perf.avg_latency_ms = (1 - alpha) * perf.avg_latency_ms + alpha * latency_ms
        
        # Update success rate
        perf.total_queries += 1
        if not success:
            perf.failed_queries += 1
        perf.success_rate = 1.0 - (perf.failed_queries / perf.total_queries)
        
        # Update memory efficiency (lower memory usage = higher efficiency)
        if memory_used_mb > 0:
            efficiency = max(0.1, 1.0 - (memory_used_mb / 100))  # Normalize to 100MB baseline
            perf.memory_efficiency = (1 - alpha) * perf.memory_efficiency + alpha * efficiency
        
        perf.last_updated = time.time()


class AdvancedQueryEngine:
    """
    Advanced query engine with intelligent orchestration and optimization
    """
    
    def __init__(self):
        self.complexity_analyzer = QueryComplexityAnalyzer()
        self.optimizer = QueryOptimizer()
        self.active_queries: Dict[str, Any] = {}
        
    async def execute_optimized_query(
        self, 
        request: QueryRequest, 
        available_providers: List[VectorProvider],
        query_embedding: Optional[List[float]] = None
    ) -> QueryResponse:
        """Execute query with optimal strategy and performance tracking"""
        start_time = time.time()
        query_id = f"query_{int(start_time * 1000)}"
        
        try:
            # Analyze query complexity
            complexity = self.complexity_analyzer.analyze_query(request)
            logger.info(f"Query {query_id} complexity: {complexity['score']:.2f}")
            
            # Create execution plan
            plan = await self.optimizer.create_execution_plan(
                request, available_providers, complexity
            )
            
            logger.info(
                f"Query {query_id} plan: {plan.execution_strategy} "
                f"with {len(plan.providers)} providers, "
                f"estimated latency: {plan.expected_latency_ms:.1f}ms"
            )
            
            # Execute query according to plan
            if plan.execution_strategy == 'parallel':
                response = await self._execute_parallel_query(
                    request, plan, query_embedding, query_id
                )
            elif plan.execution_strategy == 'sequential':
                response = await self._execute_sequential_query(
                    request, plan, query_embedding, query_id
                )
            else:
                response = await self._execute_single_provider_query(
                    request, plan, query_embedding, query_id
                )
            
            # Update performance metrics
            execution_time = (time.time() - start_time) * 1000
            for provider in plan.providers:
                await self.optimizer.update_provider_performance(
                    provider.name, execution_time / len(plan.providers), True
                )
            
            logger.info(
                f"Query {query_id} completed in {execution_time:.1f}ms, "
                f"returned {len(response.memories)} results"
            )
            
            return response
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Query {query_id} failed after {execution_time:.1f}ms: {e}")
            
            # Update failure metrics
            for provider in (plan.providers if 'plan' in locals() else available_providers):
                await self.optimizer.update_provider_performance(
                    provider.name, execution_time, False
                )
            
            raise
    
    async def _execute_parallel_query(
        self, 
        request: QueryRequest, 
        plan: QueryPlan, 
        query_embedding: Optional[List[float]],
        query_id: str
    ) -> QueryResponse:
        """Execute query across multiple providers in parallel"""
        logger.info(f"Executing parallel query {query_id} across {len(plan.providers)} providers")
        
        # Create tasks for parallel execution
        tasks = []
        for provider in plan.providers:
            task = asyncio.create_task(
                self._query_single_provider(provider, request, query_embedding, query_id)
            )
            tasks.append((provider.name, task))
        
        # Wait for all providers to complete
        results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        # Aggregate results
        all_memories = []
        successful_providers = []
        
        for i, ((provider_name, _), result) in enumerate(zip(tasks, results)):
            if isinstance(result, Exception):
                logger.warning(f"Provider {provider_name} failed in parallel query: {result}")
            else:
                all_memories.extend(result)
                successful_providers.append(provider_name)
                logger.info(f"Provider {provider_name} returned {len(result)} results")
        
        # Merge and deduplicate results
        deduplicated_memories = self._deduplicate_results(all_memories)
        
        # Sort by combined score
        deduplicated_memories.sort(
            key=lambda m: (m.similarity_score or 0) * 0.7 + (m.importance_score or 0) * 0.3,
            reverse=True
        )
        
        return QueryResponse(
            memories=deduplicated_memories[:request.limit],
            total_found=len(deduplicated_memories),
            query_time_ms=0,  # Will be filled by caller
            providers_used=successful_providers
        )
    
    async def _execute_sequential_query(
        self, 
        request: QueryRequest, 
        plan: QueryPlan, 
        query_embedding: Optional[List[float]],
        query_id: str
    ) -> QueryResponse:
        """Execute query across providers sequentially with fallback"""
        logger.info(f"Executing sequential query {query_id}")
        
        all_memories = []
        successful_providers = []
        
        for provider in plan.providers:
            try:
                memories = await self._query_single_provider(
                    provider, request, query_embedding, query_id
                )
                all_memories.extend(memories)
                successful_providers.append(provider.name)
                logger.info(f"Provider {provider.name} returned {len(memories)} results")
                
                # If we have enough results, we can stop early
                if len(all_memories) >= request.limit * 2:
                    break
                    
            except Exception as e:
                logger.warning(f"Provider {provider.name} failed in sequential query: {e}")
                continue
        
        # Sort combined results
        all_memories.sort(
            key=lambda m: (m.similarity_score or 0) * 0.7 + (m.importance_score or 0) * 0.3,
            reverse=True
        )
        
        return QueryResponse(
            memories=all_memories[:request.limit],
            total_found=len(all_memories),
            query_time_ms=0,
            providers_used=successful_providers
        )
    
    async def _execute_single_provider_query(
        self, 
        request: QueryRequest, 
        plan: QueryPlan, 
        query_embedding: Optional[List[float]],
        query_id: str
    ) -> QueryResponse:
        """Execute query on single best provider"""
        provider = plan.providers[0]
        logger.info(f"Executing single provider query {query_id} on {provider.name}")
        
        memories = await self._query_single_provider(
            provider, request, query_embedding, query_id
        )
        
        return QueryResponse(
            memories=memories[:request.limit],
            total_found=len(memories),
            query_time_ms=0,
            providers_used=[provider.name]
        )
    
    async def _query_single_provider(
        self, 
        provider: VectorProvider, 
        request: QueryRequest, 
        query_embedding: Optional[List[float]],
        query_id: str
    ) -> List[MemoryResponse]:
        """Query a single provider with error handling"""
        try:
            if query_embedding:
                # Regular vector similarity query
                return await provider.query(
                    query_embedding, 
                    request.limit * 2,  # Get more results for better ranking
                    request.filters or {}
                )
            else:
                # Fallback to recent memories if no embedding
                if hasattr(provider, 'get_recent_memories'):
                    return await provider.get_recent_memories(
                        request.limit * 2, 
                        request.filters or {}
                    )
                else:
                    return []
        except Exception as e:
            logger.error(f"Provider {provider.name} query failed: {e}")
            raise
    
    def _deduplicate_results(self, memories: List[MemoryResponse]) -> List[MemoryResponse]:
        """Remove duplicate results from multiple providers"""
        seen_ids = set()
        deduplicated = []
        
        # Sort by quality score first
        memories.sort(
            key=lambda m: (m.similarity_score or 0) * 0.7 + (m.importance_score or 0) * 0.3,
            reverse=True
        )
        
        for memory in memories:
            if memory.id not in seen_ids:
                seen_ids.add(memory.id)
                deduplicated.append(memory)
        
        return deduplicated
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        return {
            'provider_performance': {
                name: {
                    'avg_latency_ms': perf.avg_latency_ms,
                    'success_rate': perf.success_rate,
                    'memory_efficiency': perf.memory_efficiency,
                    'total_queries': perf.total_queries,
                    'failed_queries': perf.failed_queries
                }
                for name, perf in self.optimizer.provider_performance.items()
            },
            'active_queries': len(self.active_queries),
            'query_patterns': len(self.optimizer.query_patterns)
        }