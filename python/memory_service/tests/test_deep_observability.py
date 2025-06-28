"""
Deep Observability Tests for Core Nexus Memory Service

Advanced testing suite that provides comprehensive observability, tracing,
performance profiling, and operational intelligence for production systems.

These tests validate and enhance the system's ability to provide deep insights
into its own behavior, performance patterns, and operational characteristics.
"""

import asyncio
import contextvars
import gc
import logging
import statistics
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import numpy as np
import psutil
import pytest
from memory_service.models import MemoryResponse

# Import the actual service components
from memory_service.unified_store import UnifiedVectorStore

# Disable logging during tests
logging.getLogger().setLevel(logging.CRITICAL)


@dataclass
class TraceSpan:
    """Represents a trace span for distributed tracing."""
    span_id: str
    parent_id: str | None
    operation_name: str
    start_time: float
    end_time: float | None = None
    duration: float | None = None
    tags: dict[str, Any] = field(default_factory=dict)
    logs: list[dict[str, Any]] = field(default_factory=list)
    status: str = "active"

    def finish(self):
        """Finish the span and calculate duration."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.status = "finished"

    def log(self, event: str, payload: dict[str, Any] = None):
        """Add a log entry to the span."""
        self.logs.append({
            "timestamp": time.time(),
            "event": event,
            "payload": payload or {}
        })

    def set_tag(self, key: str, value: Any):
        """Set a tag on the span."""
        self.tags[key] = value


@dataclass
class PerformanceProfile:
    """Comprehensive performance profile."""
    operation_name: str
    start_time: float
    end_time: float
    duration: float
    cpu_usage_start: float
    cpu_usage_end: float
    memory_usage_start: float
    memory_usage_end: float
    memory_delta: float
    gc_collections: int
    thread_count: int
    io_stats: dict[str, Any]
    custom_metrics: dict[str, Any] = field(default_factory=dict)


class DistributedTracer:
    """Distributed tracing implementation for observability testing."""

    def __init__(self):
        self.spans: dict[str, TraceSpan] = {}
        self.active_spans: dict[str, str] = {}  # thread_id -> span_id
        self.trace_context = contextvars.ContextVar('trace_context', default=None)

    def start_span(self, operation_name: str, parent_span_id: str | None = None) -> TraceSpan:
        """Start a new trace span."""
        span_id = str(uuid4())

        if parent_span_id is None:
            # Check for active span in current context
            current_context = self.trace_context.get()
            if current_context:
                parent_span_id = current_context.get('span_id')

        span = TraceSpan(
            span_id=span_id,
            parent_id=parent_span_id,
            operation_name=operation_name,
            start_time=time.time()
        )

        self.spans[span_id] = span
        thread_id = threading.get_ident()
        self.active_spans[thread_id] = span_id

        # Set trace context
        self.trace_context.set({'span_id': span_id, 'trace_id': span_id if not parent_span_id else self.trace_context.get().get('trace_id', span_id)})

        return span

    def finish_span(self, span_id: str):
        """Finish a trace span."""
        if span_id in self.spans:
            self.spans[span_id].finish()

            # Remove from active spans
            thread_id = threading.get_ident()
            if self.active_spans.get(thread_id) == span_id:
                del self.active_spans[thread_id]

    def get_trace_tree(self, root_span_id: str) -> dict[str, Any]:
        """Get the complete trace tree starting from root span."""
        root_span = self.spans.get(root_span_id)
        if not root_span:
            return {}

        def build_tree(span_id: str) -> dict[str, Any]:
            span = self.spans[span_id]
            children = [
                build_tree(child_span.span_id)
                for child_span in self.spans.values()
                if child_span.parent_id == span_id
            ]

            return {
                "span_id": span.span_id,
                "operation_name": span.operation_name,
                "duration": span.duration,
                "start_time": span.start_time,
                "end_time": span.end_time,
                "tags": span.tags,
                "logs": span.logs,
                "children": children
            }

        return build_tree(root_span_id)

    def get_performance_insights(self) -> dict[str, Any]:
        """Generate performance insights from trace data."""
        finished_spans = [s for s in self.spans.values() if s.status == "finished"]

        if not finished_spans:
            return {}

        # Operation performance analysis
        operation_stats = defaultdict(list)
        for span in finished_spans:
            operation_stats[span.operation_name].append(span.duration)

        insights = {
            "total_spans": len(finished_spans),
            "operation_performance": {},
            "slowest_operations": [],
            "trace_depth_analysis": self._analyze_trace_depth(),
            "concurrency_patterns": self._analyze_concurrency_patterns()
        }

        # Calculate statistics for each operation
        for operation, durations in operation_stats.items():
            insights["operation_performance"][operation] = {
                "count": len(durations),
                "avg_duration": statistics.mean(durations),
                "min_duration": min(durations),
                "max_duration": max(durations),
                "p95_duration": np.percentile(durations, 95),
                "p99_duration": np.percentile(durations, 99)
            }

        # Find slowest operations
        all_spans_with_duration = [(s.operation_name, s.duration, s.span_id) for s in finished_spans if s.duration]
        insights["slowest_operations"] = sorted(all_spans_with_duration, key=lambda x: x[1], reverse=True)[:5]

        return insights

    def _analyze_trace_depth(self) -> dict[str, Any]:
        """Analyze the depth of trace trees."""
        root_spans = [s for s in self.spans.values() if s.parent_id is None]

        def get_depth(span_id: str, current_depth: int = 0) -> int:
            children = [s for s in self.spans.values() if s.parent_id == span_id]
            if not children:
                return current_depth
            return max(get_depth(child.span_id, current_depth + 1) for child in children)

        depths = [get_depth(span.span_id) for span in root_spans]

        return {
            "max_depth": max(depths) if depths else 0,
            "avg_depth": statistics.mean(depths) if depths else 0,
            "depth_distribution": {d: depths.count(d) for d in set(depths)}
        }

    def _analyze_concurrency_patterns(self) -> dict[str, Any]:
        """Analyze concurrency patterns in traces."""
        if not self.spans:
            return {}

        # Find overlapping spans
        time_ranges = [(s.start_time, s.end_time or time.time(), s.span_id) for s in self.spans.values()]
        time_ranges.sort()

        max_concurrent = 0
        current_concurrent = 0
        concurrent_events = []

        for start_time, end_time, span_id in time_ranges:
            # Count how many spans are active at this start time
            concurrent_at_start = sum(1 for s, e, _ in time_ranges if s <= start_time < e)
            max_concurrent = max(max_concurrent, concurrent_at_start)

            concurrent_events.append((start_time, concurrent_at_start))

        return {
            "max_concurrent_spans": max_concurrent,
            "avg_concurrency": statistics.mean([c for _, c in concurrent_events]) if concurrent_events else 0,
            "concurrency_timeline": concurrent_events[:20]  # First 20 events
        }


class PerformanceProfiler:
    """Advanced performance profiler for deep system analysis."""

    def __init__(self):
        self.profiles: list[PerformanceProfile] = []
        self.active_profiles: dict[str, dict[str, Any]] = {}

    @asynccontextmanager
    async def profile_operation(self, operation_name: str):
        """Context manager for profiling operations."""
        profile_id = str(uuid4())

        # Capture initial state
        process = psutil.Process()
        gc_stats_before = gc.get_stats()

        start_profile = {
            "profile_id": profile_id,
            "operation_name": operation_name,
            "start_time": time.time(),
            "cpu_usage_start": process.cpu_percent(),
            "memory_info_start": process.memory_info(),
            "thread_count_start": process.num_threads(),
            "gc_stats_before": gc_stats_before
        }

        self.active_profiles[profile_id] = start_profile

        try:
            yield profile_id
        finally:
            # Capture final state
            end_time = time.time()
            gc_stats_after = gc.get_stats()
            memory_info_end = process.memory_info()

            profile = PerformanceProfile(
                operation_name=operation_name,
                start_time=start_profile["start_time"],
                end_time=end_time,
                duration=end_time - start_profile["start_time"],
                cpu_usage_start=start_profile["cpu_usage_start"],
                cpu_usage_end=process.cpu_percent(),
                memory_usage_start=start_profile["memory_info_start"].rss,
                memory_usage_end=memory_info_end.rss,
                memory_delta=memory_info_end.rss - start_profile["memory_info_start"].rss,
                gc_collections=sum(stat['collections'] for stat in gc_stats_after) -
                              sum(stat['collections'] for stat in gc_stats_before),
                thread_count=process.num_threads(),
                io_stats=self._get_io_stats(process)
            )

            self.profiles.append(profile)
            del self.active_profiles[profile_id]

    def _get_io_stats(self, process) -> dict[str, Any]:
        """Get I/O statistics for the process."""
        try:
            io_counters = process.io_counters()
            return {
                "read_count": io_counters.read_count,
                "write_count": io_counters.write_count,
                "read_bytes": io_counters.read_bytes,
                "write_bytes": io_counters.write_bytes
            }
        except (AttributeError, psutil.AccessDenied):
            return {}

    def get_performance_summary(self) -> dict[str, Any]:
        """Get comprehensive performance summary."""
        if not self.profiles:
            return {}

        operation_stats = defaultdict(list)
        for profile in self.profiles:
            operation_stats[profile.operation_name].append(profile)

        summary = {
            "total_operations": len(self.profiles),
            "operation_breakdown": {},
            "resource_utilization": self._analyze_resource_utilization(),
            "performance_trends": self._analyze_performance_trends(),
            "memory_analysis": self._analyze_memory_patterns(),
            "optimization_opportunities": self._identify_optimization_opportunities()
        }

        # Per-operation analysis
        for operation, profiles in operation_stats.items():
            durations = [p.duration for p in profiles]
            memory_deltas = [p.memory_delta for p in profiles]

            summary["operation_breakdown"][operation] = {
                "count": len(profiles),
                "avg_duration": statistics.mean(durations),
                "max_duration": max(durations),
                "avg_memory_delta": statistics.mean(memory_deltas),
                "total_memory_delta": sum(memory_deltas),
                "gc_collections_total": sum(p.gc_collections for p in profiles)
            }

        return summary

    def _analyze_resource_utilization(self) -> dict[str, Any]:
        """Analyze resource utilization patterns."""
        if not self.profiles:
            return {}

        cpu_usage = [p.cpu_usage_end for p in self.profiles]
        memory_usage = [p.memory_usage_end for p in self.profiles]
        memory_deltas = [p.memory_delta for p in self.profiles]

        return {
            "cpu": {
                "avg_usage": statistics.mean(cpu_usage),
                "max_usage": max(cpu_usage),
                "min_usage": min(cpu_usage)
            },
            "memory": {
                "avg_usage_mb": statistics.mean(memory_usage) / 1024 / 1024,
                "max_usage_mb": max(memory_usage) / 1024 / 1024,
                "avg_delta_mb": statistics.mean(memory_deltas) / 1024 / 1024,
                "total_delta_mb": sum(memory_deltas) / 1024 / 1024
            }
        }

    def _analyze_performance_trends(self) -> dict[str, Any]:
        """Analyze performance trends over time."""
        if len(self.profiles) < 5:
            return {"insufficient_data": True}

        # Sort by start time
        sorted_profiles = sorted(self.profiles, key=lambda p: p.start_time)

        # Calculate moving averages
        window_size = min(5, len(sorted_profiles) // 2)
        moving_averages = []

        for i in range(len(sorted_profiles) - window_size + 1):
            window = sorted_profiles[i:i + window_size]
            avg_duration = statistics.mean(p.duration for p in window)
            moving_averages.append((window[-1].start_time, avg_duration))

        # Detect trend
        if len(moving_averages) >= 2:
            durations = [avg for _, avg in moving_averages]
            trend_slope = (durations[-1] - durations[0]) / len(durations)

            if trend_slope > 0.01:
                trend = "degrading"
            elif trend_slope < -0.01:
                trend = "improving"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "trend": trend,
            "moving_averages": moving_averages,
            "trend_slope": trend_slope if 'trend_slope' in locals() else 0
        }

    def _analyze_memory_patterns(self) -> dict[str, Any]:
        """Analyze memory usage patterns."""
        if not self.profiles:
            return {}

        memory_deltas = [p.memory_delta for p in self.profiles]
        positive_deltas = [d for d in memory_deltas if d > 0]
        negative_deltas = [d for d in memory_deltas if d < 0]

        gc_collections = [p.gc_collections for p in self.profiles]

        return {
            "memory_leaks_detected": len(positive_deltas) > len(negative_deltas) * 1.5,
            "avg_positive_delta_mb": statistics.mean(positive_deltas) / 1024 / 1024 if positive_deltas else 0,
            "avg_negative_delta_mb": statistics.mean(negative_deltas) / 1024 / 1024 if negative_deltas else 0,
            "total_gc_collections": sum(gc_collections),
            "operations_triggering_gc": sum(1 for gc in gc_collections if gc > 0),
            "memory_efficiency": len(negative_deltas) / len(memory_deltas) if memory_deltas else 0
        }

    def _identify_optimization_opportunities(self) -> list[str]:
        """Identify optimization opportunities based on profiling data."""
        opportunities = []

        if not self.profiles:
            return opportunities

        # Analyze durations
        durations = [p.duration for p in self.profiles]
        avg_duration = statistics.mean(durations)

        if avg_duration > 0.1:
            opportunities.append("High average operation duration - consider caching or optimization")

        # Analyze memory usage
        memory_deltas = [p.memory_delta for p in self.profiles]
        total_memory_delta = sum(memory_deltas)

        if total_memory_delta > 50 * 1024 * 1024:  # 50MB
            opportunities.append("High memory usage detected - consider memory optimization")

        # Analyze GC patterns
        gc_collections = [p.gc_collections for p in self.profiles]
        total_gc = sum(gc_collections)

        if total_gc > len(self.profiles) * 0.5:  # More than 0.5 GC per operation
            opportunities.append("Frequent garbage collection - optimize object allocation")

        # Analyze operation distribution
        operation_counts = defaultdict(int)
        for profile in self.profiles:
            operation_counts[profile.operation_name] += 1

        most_frequent_op = max(operation_counts.items(), key=lambda x: x[1])
        if most_frequent_op[1] > len(self.profiles) * 0.3:
            opportunities.append(f"High frequency operation '{most_frequent_op[0]}' - consider caching")

        return opportunities


class TestDeepObservability:
    """
    Deep Observability Test Suite
    
    Tests comprehensive observability capabilities including:
    - Distributed tracing validation
    - Performance profiling accuracy
    - Resource utilization monitoring
    - Operational intelligence generation
    - Observability data correlation
    """

    @pytest.fixture
    def distributed_tracer(self):
        """Create a distributed tracer for testing."""
        return DistributedTracer()

    @pytest.fixture
    def performance_profiler(self):
        """Create a performance profiler for testing."""
        return PerformanceProfiler()

    @pytest.fixture
    def mock_embedding(self):
        """Generate a mock embedding vector."""
        return np.random.rand(1536).tolist()

    @pytest.mark.asyncio
    async def test_distributed_tracing_correlation(self, distributed_tracer, mock_embedding):
        """Test distributed tracing across multiple service layers."""

        # Mock provider with tracing integration
        async def traced_store(content, embedding, metadata):
            span = distributed_tracer.start_span("provider.store")
            span.set_tag("content_length", len(content))
            span.set_tag("has_metadata", bool(metadata))

            try:
                # Simulate storage operation
                await asyncio.sleep(0.02)

                # Simulate database interaction
                db_span = distributed_tracer.start_span("database.insert", span.span_id)
                db_span.set_tag("table", "memories")
                await asyncio.sleep(0.01)
                db_span.log("inserting_record", {"table": "memories"})
                distributed_tracer.finish_span(db_span.span_id)

                # Simulate embedding storage
                embed_span = distributed_tracer.start_span("embedding.store", span.span_id)
                embed_span.set_tag("vector_dimension", len(embedding))
                await asyncio.sleep(0.005)
                distributed_tracer.finish_span(embed_span.span_id)

                memory_id = uuid4()
                span.set_tag("memory_id", str(memory_id))
                span.log("storage_complete", {"memory_id": str(memory_id)})

                return memory_id

            finally:
                distributed_tracer.finish_span(span.span_id)

        async def traced_query(query_embedding, limit, filters):
            span = distributed_tracer.start_span("provider.query")
            span.set_tag("query_limit", limit)
            span.set_tag("filter_count", len(filters))

            try:
                # Simulate query planning
                plan_span = distributed_tracer.start_span("query.plan", span.span_id)
                await asyncio.sleep(0.003)
                plan_span.log("query_planned", {"strategy": "vector_similarity"})
                distributed_tracer.finish_span(plan_span.span_id)

                # Simulate vector search
                search_span = distributed_tracer.start_span("vector.search", span.span_id)
                search_span.set_tag("search_type", "cosine_similarity")
                await asyncio.sleep(0.015)
                search_span.log("search_complete", {"candidates_found": limit})
                distributed_tracer.finish_span(search_span.span_id)

                # Simulate result ranking
                rank_span = distributed_tracer.start_span("results.rank", span.span_id)
                await asyncio.sleep(0.005)
                distributed_tracer.finish_span(rank_span.span_id)

                results = [
                    MemoryResponse(
                        id=uuid4(),
                        content=f"Traced result {i}",
                        similarity_score=0.9 - i * 0.1,
                        metadata={"trace_test": True}
                    )
                    for i in range(min(limit, 5))
                ]

                span.set_tag("results_count", len(results))
                return results

            finally:
                distributed_tracer.finish_span(span.span_id)

        # Setup mock provider with tracing
        mock_provider = AsyncMock()
        mock_provider.store = traced_store
        mock_provider.query = traced_query

        store = UnifiedVectorStore({})
        store._providers = [mock_provider]

        # Execute traced operations
        print("\nTesting distributed tracing correlation...")

        # Trace a complete workflow
        root_span = distributed_tracer.start_span("memory_service.workflow")

        try:
            # Store some memories
            store_operations = []
            for i in range(3):
                memory_id = await store.store(
                    f"Traced content {i}",
                    mock_embedding,
                    {"test_id": i, "workflow": "tracing_test"}
                )
                store_operations.append(memory_id)

            # Query the memories
            query_results = await store.query(
                mock_embedding,
                limit=10,
                filters={"workflow": "tracing_test"}
            )

            root_span.set_tag("workflow_complete", True)
            root_span.set_tag("memories_stored", len(store_operations))
            root_span.set_tag("query_results", len(query_results))

        finally:
            distributed_tracer.finish_span(root_span.span_id)

        # Analyze trace data
        trace_tree = distributed_tracer.get_trace_tree(root_span.span_id)
        performance_insights = distributed_tracer.get_performance_insights()

        # Validate tracing completeness
        assert trace_tree["span_id"] == root_span.span_id, "Should have correct root span"
        assert len(trace_tree["children"]) > 0, "Should have child spans"

        # Validate trace hierarchy
        def count_spans_recursive(node):
            return 1 + sum(count_spans_recursive(child) for child in node.get("children", []))

        total_spans = count_spans_recursive(trace_tree)
        assert total_spans >= 10, f"Should have sufficient trace spans: {total_spans}"

        # Validate performance insights
        assert performance_insights["total_spans"] > 5, "Should track multiple spans"
        assert "operation_performance" in performance_insights, "Should provide operation performance data"

        # Check for expected operations
        operations = performance_insights["operation_performance"].keys()
        expected_operations = ["provider.store", "provider.query", "database.insert", "vector.search"]

        for expected_op in expected_operations:
            assert any(expected_op in op for op in operations), f"Should trace {expected_op}"

        print(f"  Total Spans Created: {total_spans}")
        print(f"  Unique Operations: {len(performance_insights['operation_performance'])}")
        print(f"  Max Trace Depth: {performance_insights['trace_depth_analysis']['max_depth']}")
        print(f"  Max Concurrent Spans: {performance_insights['concurrency_patterns']['max_concurrent_spans']}")

    @pytest.mark.asyncio
    async def test_comprehensive_performance_profiling(self, performance_profiler, mock_embedding):
        """Test comprehensive performance profiling across operations."""

        # Mock provider with varying performance characteristics
        operation_counter = 0

        async def performance_varied_store(content, embedding, metadata):
            nonlocal operation_counter
            operation_counter += 1

            # Simulate varying performance based on content size and operation count
            base_delay = 0.01
            content_factor = len(content) * 0.0001
            load_factor = operation_counter * 0.002

            total_delay = base_delay + content_factor + load_factor
            await asyncio.sleep(total_delay)

            # Simulate memory allocation
            temp_data = [0] * (len(content) * 10)  # Temporary memory allocation

            return uuid4()

        async def performance_varied_query(query_embedding, limit, filters):
            # Simulate query complexity impact
            complexity = len(str(filters)) + limit
            delay = 0.015 + (complexity * 0.001)

            await asyncio.sleep(delay)

            # Simulate result processing
            results = []
            for i in range(min(limit, 8)):
                # Each result processing adds slight overhead
                await asyncio.sleep(0.001)
                results.append(MemoryResponse(
                    id=uuid4(),
                    content=f"Performance test result {i}",
                    similarity_score=0.9 - i * 0.1,
                    metadata={"performance_test": True}
                ))

            return results

        # Setup mock provider
        mock_provider = AsyncMock()
        mock_provider.store = performance_varied_store
        mock_provider.query = performance_varied_query

        store = UnifiedVectorStore({})
        store._providers = [mock_provider]

        # Execute profiled operations
        print("\nTesting comprehensive performance profiling...")

        # Profile store operations with varying sizes
        store_content_sizes = [100, 500, 1000, 2000, 5000]

        for size in store_content_sizes:
            content = "A" * size  # Variable content size

            async with performance_profiler.profile_operation(f"store_size_{size}") as profile_id:
                await store.store(
                    content,
                    mock_embedding,
                    {"content_size": size, "test_type": "performance"}
                )

        # Profile query operations with varying complexity
        query_complexities = [
            (5, {}),  # Simple
            (10, {"test_type": "performance"}),  # Medium
            (20, {"test_type": "performance", "content_size": 1000, "complex": True}),  # Complex
            (50, {"test_type": "performance", "detailed": True, "multi_filter": "value"})  # Very complex
        ]

        for limit, filters in query_complexities:
            complexity_name = f"query_limit_{limit}_filters_{len(filters)}"

            async with performance_profiler.profile_operation(complexity_name) as profile_id:
                await store.query(mock_embedding, limit=limit, filters=filters)

        # Profile concurrent operations
        async def concurrent_operation_batch():
            tasks = []
            for i in range(5):
                task = store.query(mock_embedding, limit=10, filters={"concurrent": True})
                tasks.append(task)
            await asyncio.gather(*tasks)

        async with performance_profiler.profile_operation("concurrent_batch") as profile_id:
            await concurrent_operation_batch()

        # Analyze performance profiles
        performance_summary = performance_profiler.get_performance_summary()

        # Validate profiling completeness
        assert performance_summary["total_operations"] >= 10, "Should profile multiple operations"
        assert "operation_breakdown" in performance_summary, "Should provide operation breakdown"
        assert "resource_utilization" in performance_summary, "Should track resource utilization"

        # Validate operation categorization
        operation_breakdown = performance_summary["operation_breakdown"]

        # Check for store operations with different sizes
        store_operations = [op for op in operation_breakdown.keys() if "store_size" in op]
        assert len(store_operations) >= 4, f"Should profile multiple store sizes: {store_operations}"

        # Check for query operations with different complexities
        query_operations = [op for op in operation_breakdown.keys() if "query_limit" in op]
        assert len(query_operations) >= 3, f"Should profile multiple query complexities: {query_operations}"

        # Validate performance correlation
        store_op_data = [(op, data) for op, data in operation_breakdown.items() if "store_size" in op]
        if len(store_op_data) >= 2:
            # Check if larger content correlates with longer duration
            store_op_data.sort(key=lambda x: int(x[0].split("_")[-1]))  # Sort by size

            durations = [data["avg_duration"] for _, data in store_op_data]
            # Should show some correlation between size and duration
            assert durations[-1] >= durations[0], "Larger content should take longer to process"

        # Validate resource utilization tracking
        resource_util = performance_summary["resource_utilization"]
        assert "cpu" in resource_util, "Should track CPU utilization"
        assert "memory" in resource_util, "Should track memory utilization"
        assert resource_util["memory"]["avg_usage_mb"] > 0, "Should show positive memory usage"

        # Check for optimization opportunities
        optimization_opportunities = performance_summary.get("optimization_opportunities", [])

        print(f"  Total Operations Profiled: {performance_summary['total_operations']}")
        print(f"  Operation Categories: {len(operation_breakdown)}")
        print(f"  Avg Memory Usage: {resource_util['memory']['avg_usage_mb']:.1f}MB")
        print(f"  Optimization Opportunities: {len(optimization_opportunities)}")

        for i, opportunity in enumerate(optimization_opportunities, 1):
            print(f"    {i}. {opportunity}")

        # Validate memory analysis
        memory_analysis = performance_summary.get("memory_analysis", {})
        if memory_analysis:
            print(f"  Memory Leaks Detected: {memory_analysis.get('memory_leaks_detected', False)}")
            print(f"  GC Collections: {memory_analysis.get('total_gc_collections', 0)}")
            print(f"  Memory Efficiency: {memory_analysis.get('memory_efficiency', 0):.2%}")

    @pytest.mark.asyncio
    async def test_observability_data_correlation(self, distributed_tracer, performance_profiler, mock_embedding):
        """Test correlation between different observability data sources."""

        # Create instrumented provider that generates both tracing and profiling data
        async def instrumented_operation(operation_name: str, base_delay: float):
            # Start tracing
            trace_span = distributed_tracer.start_span(operation_name)

            try:
                # Start profiling
                async with performance_profiler.profile_operation(operation_name) as profile_id:
                    # Add tracing metadata
                    trace_span.set_tag("profile_id", profile_id)
                    trace_span.set_tag("operation_type", "instrumented")

                    # Simulate work with variable duration
                    actual_delay = base_delay + np.random.normal(0, base_delay * 0.1)
                    await asyncio.sleep(max(0.001, actual_delay))

                    # Log operation progress
                    trace_span.log("operation_halfway", {"progress": 50})

                    # Simulate additional work
                    await asyncio.sleep(actual_delay * 0.5)

                    trace_span.log("operation_complete", {"progress": 100})

                    return f"result_for_{operation_name}"

            finally:
                distributed_tracer.finish_span(trace_span.span_id)

        # Execute correlated operations
        print("\nTesting observability data correlation...")

        operations = [
            ("store_operation", 0.02),
            ("query_operation", 0.03),
            ("complex_query", 0.05),
            ("batch_operation", 0.04),
            ("store_operation", 0.025),  # Repeat to test pattern detection
            ("query_operation", 0.035)   # Repeat to test pattern detection
        ]

        correlation_results = []

        for operation_name, delay in operations:
            result = await instrumented_operation(operation_name, delay)
            correlation_results.append(result)

        # Analyze correlation between tracing and profiling data
        trace_insights = distributed_tracer.get_performance_insights()
        profile_summary = performance_profiler.get_performance_summary()

        # Correlate operation performance across data sources
        correlation_analysis = {
            "data_source_alignment": {},
            "performance_consistency": {},
            "operation_coverage": {},
            "timing_correlation": {}
        }

        # Check data source alignment
        trace_operations = set(trace_insights["operation_performance"].keys())
        profile_operations = set(profile_summary["operation_breakdown"].keys())

        common_operations = trace_operations.intersection(profile_operations)
        correlation_analysis["operation_coverage"] = {
            "trace_only": len(trace_operations - profile_operations),
            "profile_only": len(profile_operations - trace_operations),
            "common": len(common_operations),
            "alignment_percentage": len(common_operations) / len(trace_operations) if trace_operations else 0
        }

        # Analyze timing correlation for common operations
        for operation in common_operations:
            trace_data = trace_insights["operation_performance"][operation]
            profile_data = profile_summary["operation_breakdown"][operation]

            # Compare average durations
            trace_avg = trace_data["avg_duration"]
            profile_avg = profile_data["avg_duration"]

            timing_difference = abs(trace_avg - profile_avg) / max(trace_avg, profile_avg)

            correlation_analysis["timing_correlation"][operation] = {
                "trace_avg_duration": trace_avg,
                "profile_avg_duration": profile_avg,
                "timing_difference_percentage": timing_difference * 100,
                "timing_consistent": timing_difference < 0.1  # Less than 10% difference
            }

        # Check for performance consistency indicators
        consistent_operations = sum(
            1 for op_data in correlation_analysis["timing_correlation"].values()
            if op_data["timing_consistent"]
        )

        correlation_analysis["performance_consistency"] = {
            "consistent_operations": consistent_operations,
            "total_common_operations": len(common_operations),
            "consistency_percentage": consistent_operations / len(common_operations) if common_operations else 0
        }

        # Validate correlation quality
        assert correlation_analysis["operation_coverage"]["alignment_percentage"] >= 0.8, \
            "Should have high alignment between trace and profile data"

        assert correlation_analysis["performance_consistency"]["consistency_percentage"] >= 0.7, \
            "Should have consistent timing between data sources"

        # Check for expected operations
        expected_ops = ["store_operation", "query_operation", "complex_query"]
        for expected_op in expected_ops:
            assert expected_op in common_operations, f"Should track {expected_op} in both systems"

        print(f"  Operation Alignment: {correlation_analysis['operation_coverage']['alignment_percentage']:.2%}")
        print(f"  Timing Consistency: {correlation_analysis['performance_consistency']['consistency_percentage']:.2%}")
        print(f"  Common Operations: {len(common_operations)}")

        # Display timing correlation details
        for operation, timing_data in correlation_analysis["timing_correlation"].items():
            consistency_status = "✓" if timing_data["timing_consistent"] else "✗"
            print(f"  {operation}: {consistency_status} Trace:{timing_data['trace_avg_duration']:.3f}s "
                  f"Profile:{timing_data['profile_avg_duration']:.3f}s "
                  f"Diff:{timing_data['timing_difference_percentage']:.1f}%")

    @pytest.mark.asyncio
    async def test_real_time_observability_intelligence(self, distributed_tracer, performance_profiler, mock_embedding):
        """Test real-time observability intelligence and anomaly detection."""

        # Create adaptive provider that changes behavior over time
        operation_history = deque(maxlen=20)  # Keep last 20 operations
        anomaly_trigger_count = 0

        async def adaptive_provider_operation(operation_type: str):
            nonlocal anomaly_trigger_count

            # Calculate baseline performance from history
            if len(operation_history) >= 5:
                recent_durations = [op["duration"] for op in operation_history if op["type"] == operation_type]
                if recent_durations:
                    baseline_duration = statistics.mean(recent_durations)
                    baseline_std = statistics.stdev(recent_durations) if len(recent_durations) > 1 else 0
                else:
                    baseline_duration = 0.02
                    baseline_std = 0.005
            else:
                baseline_duration = 0.02
                baseline_std = 0.005

            # Introduce anomalies occasionally
            if anomaly_trigger_count % 15 == 14:  # Every 15th operation
                # Performance anomaly
                anomaly_duration = baseline_duration * 3 + np.random.uniform(0.1, 0.2)
                anomaly_type = "performance_spike"
            elif anomaly_trigger_count % 12 == 11:  # Every 12th operation
                # Memory anomaly
                anomaly_duration = baseline_duration * 1.5
                anomaly_type = "memory_spike"
                # Simulate memory leak
                temp_memory = [0] * 100000  # Large temporary allocation
            else:
                # Normal operation
                anomaly_duration = baseline_duration + np.random.normal(0, baseline_std)
                anomaly_type = "normal"

            anomaly_trigger_count += 1

            # Start instrumentation
            trace_span = distributed_tracer.start_span(f"adaptive_{operation_type}")

            start_time = time.time()

            try:
                async with performance_profiler.profile_operation(f"adaptive_{operation_type}") as profile_id:
                    trace_span.set_tag("operation_number", anomaly_trigger_count)
                    trace_span.set_tag("expected_duration", baseline_duration)
                    trace_span.set_tag("anomaly_type", anomaly_type)

                    # Simulate the operation
                    await asyncio.sleep(max(0.001, anomaly_duration))

                    actual_duration = time.time() - start_time

                    # Record operation for baseline calculation
                    operation_history.append({
                        "type": operation_type,
                        "duration": actual_duration,
                        "timestamp": time.time(),
                        "anomaly_type": anomaly_type
                    })

                    # Detect anomaly in real-time
                    if len(operation_history) >= 5:
                        recent_similar = [op for op in operation_history if op["type"] == operation_type][-5:]
                        if len(recent_similar) >= 3:
                            avg_recent = statistics.mean(op["duration"] for op in recent_similar[:-1])
                            if actual_duration > avg_recent * 2:
                                trace_span.set_tag("anomaly_detected", True)
                                trace_span.log("performance_anomaly", {
                                    "current_duration": actual_duration,
                                    "baseline_duration": avg_recent,
                                    "deviation_factor": actual_duration / avg_recent
                                })

                    return {"duration": actual_duration, "anomaly_type": anomaly_type}

            finally:
                distributed_tracer.finish_span(trace_span.span_id)

        # Execute adaptive operations
        print("\nTesting real-time observability intelligence...")

        operation_types = ["store", "query", "update", "delete"]
        intelligence_results = []

        # Run multiple rounds to build baseline and detect anomalies
        for round_num in range(4):
            round_results = []

            for operation_type in operation_types:
                for _ in range(5):  # 5 operations per type per round
                    result = await adaptive_provider_operation(operation_type)
                    round_results.append((operation_type, result))

            intelligence_results.append(round_results)

            # Brief pause between rounds
            await asyncio.sleep(0.01)

        # Analyze real-time intelligence
        trace_insights = distributed_tracer.get_performance_insights()
        profile_summary = performance_profiler.get_performance_summary()

        # Detect anomalies from trace data
        anomaly_analysis = {
            "detected_anomalies": [],
            "baseline_establishment": {},
            "performance_trends": {},
            "real_time_alerts": []
        }

        # Check for anomaly detection in traces
        for span in distributed_tracer.spans.values():
            if span.tags.get("anomaly_detected"):
                anomaly_analysis["detected_anomalies"].append({
                    "operation": span.operation_name,
                    "duration": span.duration,
                    "expected_duration": span.tags.get("expected_duration"),
                    "deviation_factor": span.logs[-1]["payload"].get("deviation_factor") if span.logs else None
                })

        # Analyze baseline establishment
        for operation_type in operation_types:
            type_operations = [op for op in operation_history if op["type"] == operation_type]
            if type_operations:
                durations = [op["duration"] for op in type_operations]
                anomaly_analysis["baseline_establishment"][operation_type] = {
                    "sample_count": len(durations),
                    "baseline_duration": statistics.mean(durations),
                    "duration_variance": statistics.variance(durations) if len(durations) > 1 else 0,
                    "anomaly_count": sum(1 for op in type_operations if op["anomaly_type"] != "normal")
                }

        # Check performance trends
        performance_trends = profile_summary.get("performance_trends", {})
        if performance_trends and not performance_trends.get("insufficient_data"):
            anomaly_analysis["performance_trends"] = {
                "trend_direction": performance_trends["trend"],
                "trend_slope": performance_trends.get("trend_slope", 0),
                "trend_reliability": len(performance_trends.get("moving_averages", []))
            }

        # Validate intelligence capabilities
        assert len(anomaly_analysis["detected_anomalies"]) > 0, "Should detect performance anomalies"
        assert len(anomaly_analysis["baseline_establishment"]) == len(operation_types), \
            "Should establish baselines for all operation types"

        # Check anomaly detection accuracy
        total_anomalies_injected = sum(
            baseline["anomaly_count"] for baseline in anomaly_analysis["baseline_establishment"].values()
        )

        detection_rate = len(anomaly_analysis["detected_anomalies"]) / max(1, total_anomalies_injected)

        print(f"  Total Operations: {len(operation_history)}")
        print(f"  Anomalies Injected: {total_anomalies_injected}")
        print(f"  Anomalies Detected: {len(anomaly_analysis['detected_anomalies'])}")
        print(f"  Detection Rate: {detection_rate:.2%}")

        # Display baseline information
        for operation_type, baseline in anomaly_analysis["baseline_establishment"].items():
            print(f"  {operation_type}: Baseline {baseline['baseline_duration']:.3f}s "
                  f"(±{baseline['duration_variance']:.6f}) "
                  f"Anomalies: {baseline['anomaly_count']}")

        # Validate detection quality
        assert detection_rate >= 0.3, f"Anomaly detection rate too low: {detection_rate}"

        # Check for expected operation baselines
        for operation_type in operation_types:
            baseline = anomaly_analysis["baseline_establishment"][operation_type]
            assert baseline["sample_count"] >= 10, f"Insufficient samples for {operation_type}"
            assert baseline["baseline_duration"] > 0, f"Invalid baseline for {operation_type}"


if __name__ == "__main__":
    # Run deep observability tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])
