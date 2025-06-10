"""
Memory Quality Dashboard

Real-time analytics and monitoring for the Core Nexus Memory Service.
Provides insights into memory quality, ADM performance, and system evolution.
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any

from .unified_store import UnifiedVectorStore

logger = logging.getLogger(__name__)


@dataclass
class MemoryMetrics:
    """Comprehensive memory service metrics."""
    total_memories: int
    avg_importance_score: float
    avg_adm_score: float
    memories_last_24h: int
    queries_last_24h: int
    avg_query_time_ms: float
    provider_distribution: dict[str, int]
    top_users: list[dict[str, Any]]
    quality_distribution: dict[str, int]
    evolution_stats: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class QualityTrend:
    """Quality trend data point."""
    timestamp: datetime
    avg_quality: float
    avg_relevance: float
    avg_intelligence: float
    memory_count: int


class MemoryDashboard:
    """
    Real-time dashboard for memory service monitoring and analytics.

    Provides insights into memory quality, performance, and evolution patterns.
    """

    def __init__(self, unified_store: UnifiedVectorStore):
        self.unified_store = unified_store
        self.quality_trends: list[QualityTrend] = []
        self.alert_thresholds = {
            'low_quality_threshold': 0.3,
            'high_query_time_threshold': 5000,  # ms
            'low_usage_threshold': 0.1,
            'evolution_success_threshold': 0.7
        }

    async def get_comprehensive_metrics(self) -> MemoryMetrics:
        """
        Get comprehensive memory service metrics.

        Aggregates data from all providers and analysis engines.
        """
        try:
            # Get provider health data
            health_data = await self.unified_store.health_check()

            # Calculate total memories across providers
            total_memories = 0
            provider_distribution = {}

            for provider_name, provider_health in health_data['providers'].items():
                if provider_health['status'] == 'healthy' and 'details' in provider_health:
                    count = provider_health['details'].get('total_vectors', 0)
                    provider_distribution[provider_name] = count
                    total_memories += count
                else:
                    provider_distribution[provider_name] = 0

            # Get recent activity metrics
            memories_24h = await self._get_recent_memory_count(hours=24)
            queries_24h = self.unified_store.stats.get('total_queries', 0)  # TODO: Make time-aware

            # Calculate average scores
            avg_importance = self._calculate_avg_importance()
            avg_adm = self.unified_store.stats.get('avg_adm_score', 0.0)
            avg_query_time = self.unified_store.stats.get('avg_query_time', 0.0)

            # Get top users
            top_users = await self._get_top_users(limit=10)

            # Get quality distribution
            quality_dist = await self._get_quality_distribution()

            # Get evolution statistics
            evolution_stats = await self._get_evolution_statistics()

            return MemoryMetrics(
                total_memories=total_memories,
                avg_importance_score=avg_importance,
                avg_adm_score=avg_adm,
                memories_last_24h=memories_24h,
                queries_last_24h=queries_24h,
                avg_query_time_ms=avg_query_time,
                provider_distribution=provider_distribution,
                top_users=top_users,
                quality_distribution=quality_dist,
                evolution_stats=evolution_stats
            )

        except Exception as e:
            logger.error(f"Failed to get comprehensive metrics: {e}")
            # Return default metrics on error
            return MemoryMetrics(
                total_memories=0,
                avg_importance_score=0.0,
                avg_adm_score=0.0,
                memories_last_24h=0,
                queries_last_24h=0,
                avg_query_time_ms=0.0,
                provider_distribution={},
                top_users=[],
                quality_distribution={},
                evolution_stats={}
            )

    async def get_quality_trends(self, days: int = 7) -> list[dict[str, Any]]:
        """
        Get memory quality trends over time.

        Shows how memory quality has evolved over the specified period.
        """
        try:
            # For now, return mock trend data
            # TODO: Implement actual trend calculation from stored metrics
            trends = []
            start_date = datetime.utcnow() - timedelta(days=days)

            for i in range(days):
                date = start_date + timedelta(days=i)
                # Mock data - replace with actual calculations
                trend = {
                    'date': date.isoformat(),
                    'avg_quality': 0.65 + (i * 0.02),  # Improving trend
                    'avg_relevance': 0.70 + (i * 0.01),
                    'avg_intelligence': 0.60 + (i * 0.03),
                    'memory_count': 50 + (i * 10),
                    'queries': 200 + (i * 30)
                }
                trends.append(trend)

            return trends

        except Exception as e:
            logger.error(f"Failed to get quality trends: {e}")
            return []

    async def get_provider_performance(self) -> dict[str, dict[str, Any]]:
        """
        Get detailed performance metrics for each provider.

        Includes health, performance, and feature comparison.
        """
        try:
            provider_performance = {}

            for name, provider in self.unified_store.providers.items():
                try:
                    # Get provider statistics
                    stats = await provider.get_stats()
                    health = stats.get('health', {})

                    # Calculate performance metrics
                    perf_data = {
                        'name': name,
                        'status': health.get('status', 'unknown'),
                        'primary': provider == self.unified_store.primary_provider,
                        'enabled': provider.enabled,
                        'features': stats.get('features', []),
                        'total_vectors': health.get('total_vectors', 0),
                        'avg_query_time': health.get('avg_query_time', 0),
                        'last_health_check': datetime.utcnow().isoformat(),
                        'configuration': {
                            'retry_count': provider.config.retry_count,
                            'timeout_seconds': provider.config.timeout_seconds
                        }
                    }

                    # Add provider-specific metrics
                    if name == 'pgvector':
                        perf_data.update({
                            'embedding_dimensions': health.get('embedding_dimensions', 0),
                            'distance_metric': health.get('distance_metric', 'unknown'),
                            'index_type': health.get('index_type', 'unknown'),
                            'connection_pool_size': health.get('connection_pool_size', 0)
                        })
                    elif name == 'pinecone':
                        perf_data.update({
                            'index_fullness': health.get('index_fullness', 0),
                            'dimension': health.get('dimension', 0),
                            'namespaces': health.get('namespaces', 0)
                        })
                    elif name == 'chromadb':
                        perf_data.update({
                            'collection_name': health.get('collection_name', 'unknown'),
                            'storage_type': health.get('storage_type', 'unknown')
                        })

                    provider_performance[name] = perf_data

                except Exception as e:
                    logger.warning(f"Failed to get stats for provider {name}: {e}")
                    provider_performance[name] = {
                        'name': name,
                        'status': 'error',
                        'error': str(e)
                    }

            return provider_performance

        except Exception as e:
            logger.error(f"Failed to get provider performance: {e}")
            return {}

    async def get_adm_performance(self) -> dict[str, Any]:
        """
        Get ADM scoring engine performance metrics.

        Shows how well the automated decision making is performing.
        """
        try:
            if not self.unified_store.adm_enabled or not self.unified_store.adm_engine:
                return {'status': 'disabled', 'message': 'ADM scoring not enabled'}

            # Get ADM engine metrics
            adm_metrics = await self.unified_store.adm_engine.get_performance_metrics()

            # Add system-level ADM stats
            adm_metrics.update({
                'system_adm_calculations': self.unified_store.stats.get('adm_calculations', 0),
                'system_avg_adm_score': self.unified_store.stats.get('avg_adm_score', 0.0),
                'enabled': self.unified_store.adm_enabled,
                'last_update': datetime.utcnow().isoformat()
            })

            return adm_metrics

        except Exception as e:
            logger.error(f"Failed to get ADM performance: {e}")
            return {'status': 'error', 'error': str(e)}

    async def get_memory_insights(self, limit: int = 50) -> dict[str, Any]:
        """
        Get insights about memory patterns and usage.

        Identifies trends, patterns, and optimization opportunities.
        """
        try:
            insights = {
                'high_value_memories': [],
                'underutilized_memories': [],
                'popular_topics': {},
                'user_patterns': {},
                'quality_alerts': [],
                'optimization_suggestions': []
            }

            # Get high-value memories (high importance + high access)
            insights['high_value_memories'] = await self._get_high_value_memories(limit=10)

            # Get underutilized memories (high quality, low access)
            insights['underutilized_memories'] = await self._get_underutilized_memories(limit=10)

            # Analyze topic popularity
            insights['popular_topics'] = await self._analyze_topic_popularity()

            # Get user patterns
            insights['user_patterns'] = await self._analyze_user_patterns(limit=10)

            # Check for quality alerts
            insights['quality_alerts'] = await self._check_quality_alerts()

            # Generate optimization suggestions
            insights['optimization_suggestions'] = await self._generate_optimization_suggestions()

            return insights

        except Exception as e:
            logger.error(f"Failed to get memory insights: {e}")
            return {}

    async def export_metrics(self, format: str = 'json') -> str:
        """
        Export comprehensive metrics in specified format.

        Supports JSON, CSV formats for external analysis.
        """
        try:
            metrics = await self.get_comprehensive_metrics()
            provider_perf = await self.get_provider_performance()
            adm_perf = await self.get_adm_performance()
            insights = await self.get_memory_insights()

            export_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'metrics': metrics.to_dict(),
                'provider_performance': provider_perf,
                'adm_performance': adm_perf,
                'insights': insights,
                'system_info': {
                    'version': '0.1.0',
                    'providers_enabled': list(self.unified_store.providers.keys()),
                    'adm_enabled': self.unified_store.adm_enabled
                }
            }

            if format.lower() == 'json':
                return json.dumps(export_data, indent=2, default=str)
            elif format.lower() == 'csv':
                # TODO: Implement CSV export
                return "CSV export not yet implemented"
            else:
                raise ValueError(f"Unsupported export format: {format}")

        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")
            return json.dumps({'error': str(e)}, indent=2)

    # Helper methods

    async def _get_recent_memory_count(self, hours: int = 24) -> int:
        """Get count of memories created in the last N hours."""
        try:
            # TODO: Implement actual time-based counting
            # For now, return a mock value
            return 42
        except Exception:
            return 0

    def _calculate_avg_importance(self) -> float:
        """Calculate average importance score across all memories."""
        # TODO: Implement actual calculation
        return 0.65

    async def _get_top_users(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get top users by memory count and activity."""
        try:
            # TODO: Implement actual user analysis
            return [
                {'user_id': 'user_123', 'memory_count': 45, 'avg_importance': 0.7},
                {'user_id': 'user_456', 'memory_count': 32, 'avg_importance': 0.6}
            ]
        except Exception:
            return []

    async def _get_quality_distribution(self) -> dict[str, int]:
        """Get distribution of memories by quality score ranges."""
        try:
            # TODO: Implement actual quality distribution calculation
            return {
                'excellent': 25,  # 0.8-1.0
                'good': 40,       # 0.6-0.8
                'fair': 30,       # 0.4-0.6
                'poor': 5         # 0.0-0.4
            }
        except Exception:
            return {}

    async def _get_evolution_statistics(self) -> dict[str, Any]:
        """Get memory evolution and adaptation statistics."""
        try:
            # TODO: Implement actual evolution tracking
            return {
                'total_evolutions': 123,
                'successful_evolutions': 89,
                'evolution_success_rate': 0.72,
                'last_evolution': datetime.utcnow().isoformat(),
                'evolution_strategies': {
                    'reinforcement': 45,
                    'diversification': 30,
                    'consolidation': 20,
                    'pruning': 5
                }
            }
        except Exception:
            return {}

    async def _get_high_value_memories(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get high-value memories for insights."""
        try:
            # TODO: Implement actual high-value memory identification
            return []
        except Exception:
            return []

    async def _get_underutilized_memories(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get underutilized but high-quality memories."""
        try:
            # TODO: Implement actual underutilization analysis
            return []
        except Exception:
            return []

    async def _analyze_topic_popularity(self) -> dict[str, int]:
        """Analyze topic popularity from memory metadata."""
        try:
            # TODO: Implement actual topic analysis
            return {
                'technical': 45,
                'personal': 32,
                'business': 28,
                'learning': 20
            }
        except Exception:
            return {}

    async def _analyze_user_patterns(self, limit: int = 10) -> dict[str, Any]:
        """Analyze user behavior patterns."""
        try:
            # TODO: Implement actual user pattern analysis
            return {
                'most_active_hours': [9, 10, 14, 15, 16],
                'avg_session_length': 45.5,
                'memory_creation_patterns': 'increasing',
                'query_patterns': 'consistent'
            }
        except Exception:
            return {}

    async def _check_quality_alerts(self) -> list[dict[str, Any]]:
        """Check for quality-related alerts."""
        try:
            alerts = []

            # Check average quality
            avg_adm = self.unified_store.stats.get('avg_adm_score', 0.0)
            if avg_adm < self.alert_thresholds['low_quality_threshold']:
                alerts.append({
                    'type': 'low_quality',
                    'severity': 'warning',
                    'message': f'Average ADM score ({avg_adm:.2f}) below threshold',
                    'timestamp': datetime.utcnow().isoformat()
                })

            # Check query performance
            avg_query_time = self.unified_store.stats.get('avg_query_time', 0.0)
            if avg_query_time > self.alert_thresholds['high_query_time_threshold']:
                alerts.append({
                    'type': 'performance',
                    'severity': 'warning',
                    'message': f'Query time ({avg_query_time:.1f}ms) above threshold',
                    'timestamp': datetime.utcnow().isoformat()
                })

            return alerts

        except Exception:
            return []

    async def _generate_optimization_suggestions(self) -> list[dict[str, Any]]:
        """Generate optimization suggestions based on current metrics."""
        try:
            suggestions = []

            # Check provider distribution
            provider_stats = self.unified_store.stats.get('provider_usage', {})
            total_usage = sum(provider_stats.values())

            if total_usage > 0:
                for provider, usage in provider_stats.items():
                    usage_ratio = usage / total_usage
                    if usage_ratio < self.alert_thresholds['low_usage_threshold']:
                        suggestions.append({
                            'type': 'provider_optimization',
                            'priority': 'medium',
                            'suggestion': f'Provider {provider} has low usage ({usage_ratio:.1%}), consider rebalancing',
                            'action': 'review_provider_configuration'
                        })

            # Check ADM performance
            if self.unified_store.adm_enabled:
                adm_calculations = self.unified_store.stats.get('adm_calculations', 0)
                if adm_calculations < 10:
                    suggestions.append({
                        'type': 'adm_optimization',
                        'priority': 'low',
                        'suggestion': 'ADM system needs more data for accurate performance assessment',
                        'action': 'increase_memory_volume'
                    })

            return suggestions

        except Exception:
            return []
