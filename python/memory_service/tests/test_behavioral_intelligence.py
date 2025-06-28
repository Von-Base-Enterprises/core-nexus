"""
Behavioral Intelligence Tests for Core Nexus Memory Service

Advanced testing suite that analyzes system behavior patterns, performance 
optimization opportunities, and usage intelligence to provide actionable
insights for system improvement and optimization.

These tests go beyond validation to provide predictive and analytical intelligence.
"""

import asyncio
import collections
import hashlib
import json
import logging
import statistics
import time
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import numpy as np
import pytest
from src.memory_service.models import MemoryResponse, MemoryRequest, QueryRequest, QueryResponse

# Import the actual service components
from src.memory_service.unified_store import UnifiedVectorStore

# Disable logging during tests
logging.getLogger().setLevel(logging.CRITICAL)


@dataclass
class QueryPattern:
    """Represents a detected query pattern."""
    pattern_id: str
    query_signature: str
    frequency: int
    avg_response_time: float
    cache_hit_potential: float
    optimization_opportunity: str


@dataclass
class BehaviorMetrics:
    """Comprehensive behavioral metrics."""
    query_patterns: list[QueryPattern]
    performance_trends: dict[str, list[float]]
    resource_utilization: dict[str, float]
    optimization_opportunities: list[str]
    predictive_insights: dict[str, Any]


class QueryAnalyzer:
    """Analyzes query patterns and behavior."""

    def __init__(self):
        self.queries = []
        self.response_times = []
        self.cache_hits = 0
        self.cache_misses = 0

    def record_query(self, query: str, response_time: float, result_count: int,
                    filters: dict[str, Any] = None):
        """Record a query for pattern analysis."""
        signature = self._generate_signature(query, filters or {})

        self.queries.append({
            'timestamp': time.time(),
            'query': query,
            'signature': signature,
            'response_time': response_time,
            'result_count': result_count,
            'filters': filters or {}
        })

        self.response_times.append(response_time)

    def _generate_signature(self, query: str, filters: dict[str, Any]) -> str:
        """Generate a signature for query pattern detection."""
        # Normalize query for pattern matching
        normalized_query = query.lower().strip()

        # Create signature from query structure and filters
        signature_data = {
            'query_length': len(normalized_query),
            'word_count': len(normalized_query.split()),
            'has_filters': bool(filters),
            'filter_keys': sorted(filters.keys()) if filters else []
        }

        signature_str = json.dumps(signature_data, sort_keys=True)
        return hashlib.md5(signature_str.encode()).hexdigest()[:8]

    def detect_patterns(self) -> list[QueryPattern]:
        """Detect recurring query patterns."""
        signature_stats = collections.defaultdict(list)

        # Group queries by signature
        for query_data in self.queries:
            signature_stats[query_data['signature']].append(query_data)

        patterns = []

        for signature, queries in signature_stats.items():
            if len(queries) >= 3:  # Pattern threshold
                avg_response_time = statistics.mean(q['response_time'] for q in queries)
                frequency = len(queries)

                # Calculate cache hit potential based on frequency and similarity
                cache_hit_potential = min(0.95, frequency / 10.0)

                # Determine optimization opportunity
                if avg_response_time > 0.1:
                    optimization = "High response time - consider caching"
                elif frequency > 10:
                    optimization = "High frequency - implement smart caching"
                elif cache_hit_potential > 0.8:
                    optimization = "Excellent cache candidate"
                else:
                    optimization = "Monitor for further optimization"

                patterns.append(QueryPattern(
                    pattern_id=signature,
                    query_signature=signature,
                    frequency=frequency,
                    avg_response_time=avg_response_time,
                    cache_hit_potential=cache_hit_potential,
                    optimization_opportunity=optimization
                ))

        return sorted(patterns, key=lambda p: p.frequency, reverse=True)

    def get_performance_insights(self) -> dict[str, Any]:
        """Generate performance insights from query data."""
        if not self.response_times:
            return {}

        return {
            'avg_response_time': statistics.mean(self.response_times),
            'median_response_time': statistics.median(self.response_times),
            'p95_response_time': np.percentile(self.response_times, 95),
            'p99_response_time': np.percentile(self.response_times, 99),
            'total_queries': len(self.queries),
            'performance_trend': self._calculate_trend(),
            'slow_query_threshold': np.percentile(self.response_times, 90)
        }

    def _calculate_trend(self) -> str:
        """Calculate performance trend over time."""
        if len(self.response_times) < 10:
            return "insufficient_data"

        # Compare first half vs second half
        mid_point = len(self.response_times) // 2
        first_half_avg = statistics.mean(self.response_times[:mid_point])
        second_half_avg = statistics.mean(self.response_times[mid_point:])

        difference = (second_half_avg - first_half_avg) / first_half_avg

        if difference > 0.1:
            return "degrading"
        elif difference < -0.1:
            return "improving"
        else:
            return "stable"


class UsageSimulator:
    """Simulates realistic usage patterns for behavioral analysis."""

    def __init__(self):
        self.user_profiles = self._create_user_profiles()

    def _create_user_profiles(self):
        """Create diverse user behavior profiles."""
        return {
            'power_user': {
                'query_frequency': 50,  # queries per session
                'query_complexity': 'high',
                'session_length': 30,  # minutes
                'repeat_query_rate': 0.3
            },
            'casual_user': {
                'query_frequency': 10,
                'query_complexity': 'low',
                'session_length': 5,
                'repeat_query_rate': 0.6
            },
            'researcher': {
                'query_frequency': 25,
                'query_complexity': 'high',
                'session_length': 45,
                'repeat_query_rate': 0.4
            },
            'automated_system': {
                'query_frequency': 100,
                'query_complexity': 'medium',
                'session_length': 1,  # Continuous
                'repeat_query_rate': 0.8
            }
        }

    def generate_user_session(self, profile_name: str) -> list[dict[str, Any]]:
        """Generate a realistic user session."""
        profile = self.user_profiles[profile_name]
        queries = []

        # Generate base queries
        base_queries = self._generate_base_queries(profile['query_complexity'])

        for i in range(profile['query_frequency']):
            # Decide if this should be a repeat query
            if i > 0 and np.random.random() < profile['repeat_query_rate']:
                # Repeat a previous query (with slight variation)
                base_query = np.random.choice(queries)['query']
                query = self._add_variation(base_query)
            else:
                # New query
                query = np.random.choice(base_queries)

            queries.append({
                'query': query,
                'user_profile': profile_name,
                'session_time': i * (profile['session_length'] * 60 / profile['query_frequency']),
                'expected_results': np.random.randint(1, 20)
            })

        return queries

    def _generate_base_queries(self, complexity: str) -> list[str]:
        """Generate base queries based on complexity."""
        if complexity == 'low':
            return [
                "find recent messages",
                "show important notes",
                "search conversations",
                "get updates",
                "find documents"
            ]
        elif complexity == 'medium':
            return [
                "find messages from last week about project planning",
                "search for conversations containing technical discussions",
                "get all important notes from Q1 2025",
                "find documents related to system architecture",
                "search for mentions of performance optimization"
            ]
        else:  # high complexity
            return [
                "find all technical discussions from the past month involving system architecture and performance optimization",
                "search for conversations where machine learning or AI was discussed in the context of data processing",
                "get comprehensive analysis of project planning discussions from Q1 including resource allocation",
                "find all design decisions related to database optimization and vector storage",
                "search for security-related conversations involving authentication and authorization frameworks"
            ]

    def _add_variation(self, base_query: str) -> str:
        """Add slight variation to a query to simulate human behavior."""
        variations = [
            base_query,  # No change
            base_query + " please",
            "can you " + base_query,
            base_query.replace("find", "search for"),
            base_query.replace("get", "show me"),
            base_query + " from yesterday"
        ]
        return np.random.choice(variations)


class TestBehavioralIntelligence:
    """
    Behavioral Intelligence Test Suite
    
    Analyzes system behavior patterns to provide insights into:
    - Query pattern optimization opportunities
    - Performance trends and predictions
    - Usage pattern analysis
    - Cache optimization recommendations
    """

    @pytest.fixture
    def mock_embedding(self):
        """Generate a consistent mock embedding vector."""
        return np.random.rand(1536).tolist()

    @pytest.fixture
    def query_analyzer(self):
        """Create a fresh query analyzer for each test."""
        return QueryAnalyzer()

    @pytest.fixture
    def usage_simulator(self):
        """Create a usage simulator for realistic patterns."""
        return UsageSimulator()

    @pytest.mark.asyncio
    async def test_query_pattern_detection(self, realistic_pgvector_provider, mock_embedding, query_analyzer):
        """Test detection of recurring query patterns for optimization."""

        # Mock provider with realistic response times
        mock_provider = AsyncMock()

        async def realistic_query(query_embedding, limit, filters):
            # Simulate realistic response times based on query complexity
            complexity_factor = len(str(filters)) * 0.01 + limit * 0.005
            await asyncio.sleep(complexity_factor)

            return [
                MemoryResponse(
                    id=uuid4(),
                    content="Result for query",
                    similarity_score=0.8,
                    metadata={"result_id": i}
                )
                for i in range(min(limit, 10))
            ]

        mock_provider.query = realistic_query

        # Create store with realistic provider configuration
        with patch('src.memory_service.unified_store.ImportanceScoring') as mock_importance:
            store = UnifiedVectorStore(
                providers=[realistic_pgvector_provider],
                embedding_model=AsyncMock(),
                adm_enabled=False
            )
        store._providers = [mock_provider]

        # Simulate various query patterns
        query_scenarios = [
            # Frequent simple queries
            ("find recent messages", {}, 10),
            ("find recent messages", {}, 10),
            ("find recent messages", {}, 10),
            ("find recent messages", {"user_id": "user1"}, 10),
            ("find recent messages", {"user_id": "user2"}, 10),

            # Complex analytical queries
            ("analyze performance data from last month", {"category": "performance"}, 20),
            ("analyze performance data from last month", {"category": "performance"}, 20),
            ("analyze performance data from last month", {"category": "analytics"}, 20),

            # Unique queries
            ("find specific document XYZ", {"document_id": "xyz"}, 5),
            ("search for rare technical term", {"technical": True}, 15),
        ]

        # Execute queries and measure patterns
        for query, filters, limit in query_scenarios:
            start_time = time.time()

            results = await store.query(mock_embedding, limit=limit, filters=filters)

            response_time = time.time() - start_time
            query_analyzer.record_query(query, response_time, len(results), filters)

        # Analyze patterns
        patterns = query_analyzer.detect_patterns()
        performance_insights = query_analyzer.get_performance_insights()

        # Validate pattern detection
        assert len(patterns) > 0, "Should detect query patterns"

        # Find the most frequent pattern
        top_pattern = patterns[0]
        assert top_pattern.frequency >= 3, "Top pattern should have sufficient frequency"
        assert top_pattern.optimization_opportunity is not None, "Should provide optimization suggestions"

        # Validate performance insights
        assert performance_insights['total_queries'] == len(query_scenarios)
        assert performance_insights['avg_response_time'] > 0
        assert performance_insights['performance_trend'] in ['improving', 'degrading', 'stable', 'insufficient_data']

        print("\nQuery Pattern Analysis Results:")
        print(f"  Detected Patterns: {len(patterns)}")
        print(f"  Top Pattern Frequency: {top_pattern.frequency}")
        print(f"  Cache Hit Potential: {top_pattern.cache_hit_potential:.2%}")
        print(f"  Optimization: {top_pattern.optimization_opportunity}")
        print(f"  Performance Trend: {performance_insights['performance_trend']}")
        print(f"  P95 Response Time: {performance_insights['p95_response_time']:.3f}s")

    @pytest.mark.asyncio
    async def test_user_behavior_simulation_analysis(self, realistic_pgvector_provider, mock_embedding, usage_simulator):
        """Test analysis of realistic user behavior patterns."""

        # Mock provider with user-specific response characteristics
        mock_provider = AsyncMock()
        user_cache = {}  # Simulate user-specific caching

        async def user_aware_query(query_embedding, limit, filters):
            user_id = filters.get('user_id', 'anonymous')
            query_hash = hash(str(query_embedding))

            # Simulate cache behavior
            cache_key = f"{user_id}:{query_hash}:{limit}"
            if cache_key in user_cache:
                # Cache hit - faster response
                await asyncio.sleep(0.01)
                return user_cache[cache_key]
            else:
                # Cache miss - slower response
                await asyncio.sleep(0.05)
                results = [
                    MemoryResponse(
                        id=uuid4(),
                        content=f"Result {i} for user {user_id}",
                        similarity_score=0.8 - i * 0.1,
                        metadata={"user_id": user_id, "result_index": i}
                    )
                    for i in range(min(limit, 8))
                ]
                user_cache[cache_key] = results
                return results

        mock_provider.query = user_aware_query

        # Create store with realistic provider configuration
        with patch('src.memory_service.unified_store.ImportanceScoring') as mock_importance:
            store = UnifiedVectorStore(
                providers=[realistic_pgvector_provider],
                embedding_model=AsyncMock(),
                adm_enabled=False
            )
        store._providers = [mock_provider]

        # Simulate different user types
        user_sessions = {}
        performance_by_user = {}

        for profile_name in ['power_user', 'casual_user', 'researcher', 'automated_system']:
            session_queries = usage_simulator.generate_user_session(profile_name)
            user_sessions[profile_name] = session_queries
            performance_by_user[profile_name] = []

            # Execute user session
            for query_data in session_queries[:15]:  # Limit for test performance
                start_time = time.time()

                filters = {'user_id': f"{profile_name}_user"}
                results = await store.query(
                    mock_embedding,
                    limit=query_data['expected_results'],
                    filters=filters
                )

                response_time = time.time() - start_time
                performance_by_user[profile_name].append(response_time)

        # Analyze user behavior patterns
        behavior_analysis = {}

        for profile_name, performance_data in performance_by_user.items():
            if performance_data:
                behavior_analysis[profile_name] = {
                    'avg_response_time': statistics.mean(performance_data),
                    'query_count': len(performance_data),
                    'response_time_variance': statistics.variance(performance_data) if len(performance_data) > 1 else 0,
                    'cache_efficiency': sum(1 for t in performance_data if t < 0.02) / len(performance_data)
                }

        # Validate behavioral insights
        assert len(behavior_analysis) == 4, "Should analyze all user types"

        # Power users should have better cache efficiency due to repeated queries
        power_user_cache = behavior_analysis['power_user']['cache_efficiency']
        casual_user_cache = behavior_analysis['casual_user']['cache_efficiency']

        # Automated systems should have highest cache efficiency
        automated_cache = behavior_analysis['automated_system']['cache_efficiency']

        print("\nUser Behavior Analysis Results:")
        for profile, analysis in behavior_analysis.items():
            print(f"  {profile}:")
            print(f"    Avg Response Time: {analysis['avg_response_time']:.3f}s")
            print(f"    Cache Efficiency: {analysis['cache_efficiency']:.2%}")
            print(f"    Query Variance: {analysis['response_time_variance']:.4f}")

        # Validate expected behavior patterns
        assert automated_cache >= casual_user_cache, "Automated systems should have better cache efficiency"
        assert len(user_cache) > 0, "Should have populated cache during simulation"

    @pytest.mark.asyncio
    async def test_performance_degradation_detection(self, realistic_pgvector_provider, mock_embedding):
        """Test detection of performance degradation over time."""

        # Mock provider with gradually degrading performance
        operation_count = 0

        async def degrading_query(query_embedding, limit, filters):
            nonlocal operation_count
            operation_count += 1

            # Simulate gradual performance degradation
            base_latency = 0.02
            degradation_factor = operation_count * 0.001  # Gets slower over time

            await asyncio.sleep(base_latency + degradation_factor)

            return [
                MemoryResponse(
                    id=uuid4(),
                    content=f"Result {i}",
                    similarity_score=0.9,
                    metadata={"operation": operation_count}
                )
                for i in range(min(limit, 5))
            ]

        mock_provider = AsyncMock()
        mock_provider.query = degrading_query

        # Create store with realistic provider configuration
        with patch('src.memory_service.unified_store.ImportanceScoring') as mock_importance:
            store = UnifiedVectorStore(
                providers=[realistic_pgvector_provider],
                embedding_model=AsyncMock(),
                adm_enabled=False
            )
        store._providers = [mock_provider]

        # Execute queries over time to capture degradation
        response_times = []
        timestamps = []

        for i in range(30):
            start_time = time.time()

            await store.query(mock_embedding, limit=5, filters={})

            response_time = time.time() - start_time
            response_times.append(response_time)
            timestamps.append(start_time)

            # Small delay between queries
            await asyncio.sleep(0.001)

        # Analyze performance trend
        def analyze_trend(times):
            """Analyze performance trend using linear regression."""
            x = np.arange(len(times))
            y = np.array(times)

            # Simple linear regression
            slope = np.corrcoef(x, y)[0, 1] * (np.std(y) / np.std(x))

            return slope

        trend_slope = analyze_trend(response_times)

        # Split into windows for detailed analysis
        window_size = 10
        window_averages = []

        for i in range(0, len(response_times) - window_size + 1, window_size):
            window = response_times[i:i + window_size]
            window_averages.append(statistics.mean(window))

        # Calculate degradation metrics
        if len(window_averages) >= 2:
            initial_performance = window_averages[0]
            final_performance = window_averages[-1]
            degradation_percentage = ((final_performance - initial_performance) / initial_performance) * 100
        else:
            degradation_percentage = 0

        print("\nPerformance Degradation Analysis:")
        print(f"  Initial Avg Response Time: {window_averages[0]:.3f}s")
        print(f"  Final Avg Response Time: {window_averages[-1]:.3f}s")
        print(f"  Performance Degradation: {degradation_percentage:.1f}%")
        print(f"  Trend Slope: {trend_slope:.6f}")
        print(f"  Total Operations: {operation_count}")

        # Validate degradation detection
        assert trend_slope > 0, "Should detect positive trend (degradation)"
        assert degradation_percentage > 10, f"Should detect significant degradation: {degradation_percentage}%"
        assert window_averages[-1] > window_averages[0], "Final performance should be worse than initial"

    @pytest.mark.asyncio
    async def test_resource_utilization_intelligence(self, realistic_pgvector_provider, mock_embedding):
        """Test intelligent analysis of resource utilization patterns."""

        # Mock provider with resource usage simulation
        memory_usage = []
        cpu_usage = []

        async def resource_aware_query(query_embedding, limit, filters):
            # Simulate resource usage based on query complexity
            query_complexity = len(str(filters)) + limit

            # Mock memory usage (MB)
            memory_used = 50 + (query_complexity * 2) + np.random.normal(0, 5)
            memory_usage.append(max(0, memory_used))

            # Mock CPU usage (percentage)
            cpu_used = 20 + (query_complexity * 1.5) + np.random.normal(0, 3)
            cpu_usage.append(min(100, max(0, cpu_used)))

            # Response time correlates with resource usage
            response_time = (memory_used / 1000) + (cpu_used / 10000)
            await asyncio.sleep(response_time)

            return [
                MemoryResponse(
                    id=uuid4(),
                    content=f"Resource-intensive result {i}",
                    similarity_score=0.85,
                    metadata={"complexity": query_complexity}
                )
                for i in range(min(limit, 8))
            ]

        mock_provider = AsyncMock()
        mock_provider.query = resource_aware_query

        # Create store with realistic provider configuration
        with patch('src.memory_service.unified_store.ImportanceScoring') as mock_importance:
            store = UnifiedVectorStore(
                providers=[realistic_pgvector_provider],
                embedding_model=AsyncMock(),
                adm_enabled=False
            )
        store._providers = [mock_provider]

        # Test various query complexities
        complexity_scenarios = [
            # Simple queries
            (5, {}),
            (3, {}),
            (7, {}),

            # Medium complexity
            (10, {"category": "test"}),
            (15, {"user_id": "user1", "date": "2025"}),
            (12, {"category": "analysis"}),

            # High complexity
            (25, {"complex_filter": True, "multi_field": "value", "nested": {"data": True}}),
            (30, {"analytics": True, "time_range": "month", "aggregation": "sum"}),
            (20, {"search_type": "semantic", "boost": 1.5})
        ]

        response_times = []
        query_complexities = []

        for limit, filters in complexity_scenarios:
            start_time = time.time()

            await store.query(mock_embedding, limit=limit, filters=filters)

            response_time = time.time() - start_time
            response_times.append(response_time)
            query_complexities.append(len(str(filters)) + limit)

        # Analyze resource utilization patterns
        resource_analysis = {
            'memory_stats': {
                'avg_usage': statistics.mean(memory_usage),
                'peak_usage': max(memory_usage),
                'usage_variance': statistics.variance(memory_usage)
            },
            'cpu_stats': {
                'avg_usage': statistics.mean(cpu_usage),
                'peak_usage': max(cpu_usage),
                'usage_variance': statistics.variance(cpu_usage)
            },
            'performance_correlation': {
                'memory_performance_correlation': np.corrcoef(memory_usage, response_times)[0, 1],
                'cpu_performance_correlation': np.corrcoef(cpu_usage, response_times)[0, 1],
                'complexity_performance_correlation': np.corrcoef(query_complexities, response_times)[0, 1]
            }
        }

        # Generate optimization recommendations
        optimization_recommendations = []

        if resource_analysis['memory_stats']['peak_usage'] > 100:
            optimization_recommendations.append("Consider memory optimization for complex queries")

        if resource_analysis['cpu_stats']['avg_usage'] > 50:
            optimization_recommendations.append("High CPU usage detected - consider query optimization")

        if resource_analysis['performance_correlation']['complexity_performance_correlation'] > 0.7:
            optimization_recommendations.append("Strong complexity-performance correlation - implement query caching")

        print("\nResource Utilization Intelligence:")
        print(f"  Memory - Avg: {resource_analysis['memory_stats']['avg_usage']:.1f}MB, Peak: {resource_analysis['memory_stats']['peak_usage']:.1f}MB")
        print(f"  CPU - Avg: {resource_analysis['cpu_stats']['avg_usage']:.1f}%, Peak: {resource_analysis['cpu_stats']['peak_usage']:.1f}%")
        print(f"  Memory-Performance Correlation: {resource_analysis['performance_correlation']['memory_performance_correlation']:.3f}")
        print(f"  Complexity-Performance Correlation: {resource_analysis['performance_correlation']['complexity_performance_correlation']:.3f}")
        print(f"  Optimization Recommendations: {len(optimization_recommendations)}")

        for i, rec in enumerate(optimization_recommendations, 1):
            print(f"    {i}. {rec}")

        # Validate resource intelligence
        assert len(memory_usage) == len(complexity_scenarios), "Should track memory for all queries"
        assert len(cpu_usage) == len(complexity_scenarios), "Should track CPU for all queries"
        assert resource_analysis['memory_stats']['avg_usage'] > 0, "Should have positive memory usage"
        assert resource_analysis['cpu_stats']['avg_usage'] > 0, "Should have positive CPU usage"

        # Resource usage should correlate with query complexity
        complexity_correlation = resource_analysis['performance_correlation']['complexity_performance_correlation']
        assert complexity_correlation > 0.3, f"Should show correlation between complexity and performance: {complexity_correlation}"


if __name__ == "__main__":
    # Run behavioral intelligence tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])
