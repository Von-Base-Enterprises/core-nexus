"""
Performance Analytics and Auto-Tuning Engine for Core Nexus Memory Service

Provides comprehensive performance monitoring, analysis, and automatic optimization
for the memory service optimized for 1GB RAM PostgreSQL deployment.
"""

import asyncio
import json
import logging
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple, Callable
from datetime import datetime, timedelta
from enum import Enum

from .config import config

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of performance metrics"""
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    SUCCESS_RATE = "success_rate"
    MEMORY_USAGE = "memory_usage"
    CACHE_HIT_RATE = "cache_hit_rate"
    PROVIDER_HEALTH = "provider_health"


@dataclass
class MetricPoint:
    """Single metric measurement"""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceAlert:
    """Performance alert definition"""
    id: str
    metric_type: MetricType
    threshold: float
    operator: str  # '>', '<', '>=', '<=', '=='
    message: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    triggered_at: Optional[float] = None
    resolved_at: Optional[float] = None
    is_active: bool = False


@dataclass
class OptimizationRecommendation:
    """Auto-tuning recommendation"""
    id: str
    category: str  # 'configuration', 'scaling', 'architecture'
    title: str
    description: str
    impact: str  # 'low', 'medium', 'high'
    effort: str  # 'low', 'medium', 'high'
    confidence: float  # 0.0 to 1.0
    implementation: Dict[str, Any]
    created_at: float = field(default_factory=time.time)


class MetricsCollector:
    """Collects and stores performance metrics"""
    
    def __init__(self, max_points_per_metric: int = 1000):
        self.max_points_per_metric = max_points_per_metric
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_points_per_metric))
        self.metric_metadata: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def record_metric(
        self, 
        metric_name: str, 
        value: float, 
        labels: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record a metric point"""
        async with self._lock:
            point = MetricPoint(
                timestamp=time.time(),
                value=value,
                labels=labels or {},
                metadata=metadata or {}
            )
            
            self.metrics[metric_name].append(point)
            
            # Update metric metadata
            if metric_name not in self.metric_metadata:
                self.metric_metadata[metric_name] = {
                    'first_recorded': point.timestamp,
                    'total_points': 0,
                    'min_value': value,
                    'max_value': value
                }
            
            meta = self.metric_metadata[metric_name]
            meta['total_points'] += 1
            meta['last_recorded'] = point.timestamp
            meta['min_value'] = min(meta['min_value'], value)
            meta['max_value'] = max(meta['max_value'], value)
    
    async def get_metric_values(
        self, 
        metric_name: str, 
        time_range_seconds: Optional[int] = None
    ) -> List[MetricPoint]:
        """Get metric values within time range"""
        async with self._lock:
            if metric_name not in self.metrics:
                return []
            
            points = list(self.metrics[metric_name])
            
            if time_range_seconds is not None:
                cutoff_time = time.time() - time_range_seconds
                points = [p for p in points if p.timestamp >= cutoff_time]
            
            return points
    
    async def get_metric_statistics(
        self, 
        metric_name: str, 
        time_range_seconds: Optional[int] = None
    ) -> Dict[str, float]:
        """Get statistical summary of metric"""
        points = await self.get_metric_values(metric_name, time_range_seconds)
        
        if not points:
            return {}
        
        values = [p.value for p in points]
        
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'std_dev': statistics.stdev(values) if len(values) > 1 else 0.0,
            'p50': statistics.median(values),
            'p95': values[int(len(values) * 0.95)] if len(values) > 20 else max(values),
            'p99': values[int(len(values) * 0.99)] if len(values) > 100 else max(values)
        }
    
    async def get_all_metric_names(self) -> List[str]:
        """Get all tracked metric names"""
        async with self._lock:
            return list(self.metrics.keys())


class AlertManager:
    """Manages performance alerts and notifications"""
    
    def __init__(self):
        self.alerts: Dict[str, PerformanceAlert] = {}
        self.alert_history: List[Dict[str, Any]] = []
        self.notification_callbacks: List[Callable] = []
        self._evaluation_interval = 30  # seconds
        self._is_monitoring = False
    
    def add_alert(self, alert: PerformanceAlert):
        """Add a performance alert"""
        self.alerts[alert.id] = alert
        logger.info(f"Added performance alert: {alert.id}")
    
    def remove_alert(self, alert_id: str):
        """Remove a performance alert"""
        if alert_id in self.alerts:
            del self.alerts[alert_id]
            logger.info(f"Removed performance alert: {alert_id}")
    
    def add_notification_callback(self, callback: Callable):
        """Add notification callback for alerts"""
        self.notification_callbacks.append(callback)
    
    async def start_monitoring(self, metrics_collector: MetricsCollector):
        """Start alert monitoring"""
        if self._is_monitoring:
            return
        
        self._is_monitoring = True
        asyncio.create_task(self._monitor_alerts(metrics_collector))
        logger.info("Alert monitoring started")
    
    async def stop_monitoring(self):
        """Stop alert monitoring"""
        self._is_monitoring = False
        logger.info("Alert monitoring stopped")
    
    async def _monitor_alerts(self, metrics_collector: MetricsCollector):
        """Background alert monitoring loop"""
        while self._is_monitoring:
            try:
                await self._evaluate_alerts(metrics_collector)
                await asyncio.sleep(self._evaluation_interval)
            except Exception as e:
                logger.error(f"Alert monitoring error: {e}")
                await asyncio.sleep(5)  # Brief pause on error
    
    async def _evaluate_alerts(self, metrics_collector: MetricsCollector):
        """Evaluate all alerts against current metrics"""
        for alert in self.alerts.values():
            try:
                await self._evaluate_single_alert(alert, metrics_collector)
            except Exception as e:
                logger.error(f"Error evaluating alert {alert.id}: {e}")
    
    async def _evaluate_single_alert(self, alert: PerformanceAlert, metrics_collector: MetricsCollector):
        """Evaluate a single alert"""
        # Get recent metric values (last 5 minutes)
        metric_name = f"{alert.metric_type.value}"
        points = await metrics_collector.get_metric_values(metric_name, 300)
        
        if not points:
            return
        
        # Use latest value for evaluation
        latest_value = points[-1].value
        
        # Evaluate condition
        triggered = self._evaluate_condition(latest_value, alert.threshold, alert.operator)
        
        if triggered and not alert.is_active:
            # Alert triggered
            alert.is_active = True
            alert.triggered_at = time.time()
            await self._send_alert_notification(alert, "triggered", latest_value)
            
            self.alert_history.append({
                'alert_id': alert.id,
                'action': 'triggered',
                'value': latest_value,
                'threshold': alert.threshold,
                'timestamp': alert.triggered_at
            })
            
        elif not triggered and alert.is_active:
            # Alert resolved
            alert.is_active = False
            alert.resolved_at = time.time()
            await self._send_alert_notification(alert, "resolved", latest_value)
            
            self.alert_history.append({
                'alert_id': alert.id,
                'action': 'resolved',
                'value': latest_value,
                'threshold': alert.threshold,
                'timestamp': alert.resolved_at
            })
    
    def _evaluate_condition(self, value: float, threshold: float, operator: str) -> bool:
        """Evaluate alert condition"""
        if operator == '>':
            return value > threshold
        elif operator == '<':
            return value < threshold
        elif operator == '>=':
            return value >= threshold
        elif operator == '<=':
            return value <= threshold
        elif operator == '==':
            return abs(value - threshold) < 1e-6
        else:
            logger.warning(f"Unknown operator: {operator}")
            return False
    
    async def _send_alert_notification(self, alert: PerformanceAlert, action: str, value: float):
        """Send alert notification"""
        notification = {
            'alert_id': alert.id,
            'action': action,
            'severity': alert.severity,
            'message': alert.message,
            'current_value': value,
            'threshold': alert.threshold,
            'timestamp': time.time()
        }
        
        for callback in self.notification_callbacks:
            try:
                await callback(notification)
            except Exception as e:
                logger.error(f"Notification callback failed: {e}")
        
        logger.warning(f"ALERT {action.upper()}: {alert.message} (value: {value}, threshold: {alert.threshold})")
    
    async def get_active_alerts(self) -> List[PerformanceAlert]:
        """Get all active alerts"""
        return [alert for alert in self.alerts.values() if alert.is_active]
    
    async def get_alert_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent alert history"""
        return self.alert_history[-limit:]


class AutoTuner:
    """Automatic performance tuning engine"""
    
    def __init__(self):
        self.recommendations: List[OptimizationRecommendation] = []
        self.applied_optimizations: List[str] = []
        self.analysis_interval = 300  # 5 minutes
        self._is_tuning = False
        self._last_analysis = 0
    
    async def start_auto_tuning(self, metrics_collector: MetricsCollector):
        """Start automatic performance tuning"""
        if self._is_tuning:
            return
        
        self._is_tuning = True
        asyncio.create_task(self._auto_tune_loop(metrics_collector))
        logger.info("Auto-tuning started")
    
    async def stop_auto_tuning(self):
        """Stop automatic performance tuning"""
        self._is_tuning = False
        logger.info("Auto-tuning stopped")
    
    async def _auto_tune_loop(self, metrics_collector: MetricsCollector):
        """Background auto-tuning loop"""
        while self._is_tuning:
            try:
                if time.time() - self._last_analysis > self.analysis_interval:
                    await self._analyze_performance(metrics_collector)
                    self._last_analysis = time.time()
                
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Auto-tuning error: {e}")
                await asyncio.sleep(30)
    
    async def _analyze_performance(self, metrics_collector: MetricsCollector):
        """Analyze performance and generate recommendations"""
        logger.info("Analyzing performance for auto-tuning opportunities...")
        
        # Get recent performance data
        latency_stats = await metrics_collector.get_metric_statistics("latency", 1800)  # 30 min
        memory_stats = await metrics_collector.get_metric_statistics("memory_usage", 1800)
        cache_stats = await metrics_collector.get_metric_statistics("cache_hit_rate", 1800)
        
        # Analyze latency
        await self._analyze_latency(latency_stats)
        
        # Analyze memory usage
        await self._analyze_memory_usage(memory_stats)
        
        # Analyze cache performance
        await self._analyze_cache_performance(cache_stats)
        
        # Analyze connection pool performance
        await self._analyze_connection_pool()
        
        logger.info(f"Performance analysis complete. Generated {len(self.recommendations)} recommendations.")
    
    async def _analyze_latency(self, stats: Dict[str, float]):
        """Analyze latency metrics and generate recommendations"""
        if not stats:
            return
        
        mean_latency = stats.get('mean', 0)
        p95_latency = stats.get('p95', 0)
        
        # High average latency
        if mean_latency > 500:  # 500ms
            recommendation = OptimizationRecommendation(
                id=f"latency_high_{int(time.time())}",
                category="performance",
                title="High Average Latency Detected",
                description=f"Average query latency is {mean_latency:.1f}ms, which is above optimal threshold",
                impact="high",
                effort="medium",
                confidence=0.9,
                implementation={
                    "action": "optimize_query_execution",
                    "suggested_changes": [
                        "Enable query result caching",
                        "Optimize database connection pooling",
                        "Consider query parallelization"
                    ]
                }
            )
            self.recommendations.append(recommendation)
        
        # High P95 latency indicates tail latency issues
        if p95_latency > 1000:  # 1 second
            recommendation = OptimizationRecommendation(
                id=f"latency_p95_{int(time.time())}",
                category="performance",
                title="High Tail Latency (P95) Detected",
                description=f"95th percentile latency is {p95_latency:.1f}ms, indicating performance inconsistency",
                impact="medium",
                effort="medium",
                confidence=0.8,
                implementation={
                    "action": "optimize_tail_latency",
                    "suggested_changes": [
                        "Implement circuit breaker patterns",
                        "Add query timeout mechanisms",
                        "Optimize slow query patterns"
                    ]
                }
            )
            self.recommendations.append(recommendation)
    
    async def _analyze_memory_usage(self, stats: Dict[str, float]):
        """Analyze memory usage and generate recommendations"""
        if not stats:
            return
        
        mean_memory = stats.get('mean', 0)
        max_memory = stats.get('max', 0)
        
        # High memory usage
        if mean_memory > 0.8:  # 80% of available memory
            recommendation = OptimizationRecommendation(
                id=f"memory_high_{int(time.time())}",
                category="resource",
                title="High Memory Usage Detected",
                description=f"Average memory usage is {mean_memory:.1%}, approaching limits",
                impact="high",
                effort="low",
                confidence=0.9,
                implementation={
                    "action": "optimize_memory_usage",
                    "suggested_changes": [
                        "Increase cache eviction frequency",
                        "Implement vector compression",
                        "Optimize batch processing sizes"
                    ]
                }
            )
            self.recommendations.append(recommendation)
        
        # Memory spikes
        if max_memory > 0.95:  # 95% memory usage spikes
            recommendation = OptimizationRecommendation(
                id=f"memory_spikes_{int(time.time())}",
                category="stability",
                title="Memory Usage Spikes Detected",
                description=f"Memory usage peaked at {max_memory:.1%}, risking system stability",
                impact="high",
                effort="medium",
                confidence=0.85,
                implementation={
                    "action": "prevent_memory_spikes",
                    "suggested_changes": [
                        "Implement memory pressure monitoring",
                        "Add graceful degradation mechanisms",
                        "Optimize large query handling"
                    ]
                }
            )
            self.recommendations.append(recommendation)
    
    async def _analyze_cache_performance(self, stats: Dict[str, float]):
        """Analyze cache performance and generate recommendations"""
        if not stats:
            return
        
        mean_hit_rate = stats.get('mean', 0)
        min_hit_rate = stats.get('min', 0)
        
        # Low cache hit rate
        if mean_hit_rate < 0.7:  # 70% hit rate
            recommendation = OptimizationRecommendation(
                id=f"cache_low_hit_rate_{int(time.time())}",
                category="performance",
                title="Low Cache Hit Rate",
                description=f"Cache hit rate is {mean_hit_rate:.1%}, below optimal threshold",
                impact="medium",
                effort="low",
                confidence=0.8,
                implementation={
                    "action": "optimize_caching",
                    "suggested_changes": [
                        "Increase cache size allocation",
                        "Implement smarter cache warming",
                        "Optimize cache key strategies"
                    ]
                }
            )
            self.recommendations.append(recommendation)
    
    async def _analyze_connection_pool(self):
        """Analyze connection pool performance"""
        # This would analyze connection pool metrics
        # For now, provide general recommendations based on configuration
        
        current_pool_size = config.database.POOL_MAX_SIZE
        
        if current_pool_size < 30:  # For 1GB RAM, we can handle more connections
            recommendation = OptimizationRecommendation(
                id=f"connection_pool_size_{int(time.time())}",
                category="configuration",
                title="Connection Pool Size Optimization",
                description="Current connection pool size may be suboptimal for 1GB RAM configuration",
                impact="medium",
                effort="low",
                confidence=0.7,
                implementation={
                    "action": "optimize_connection_pool",
                    "suggested_changes": [
                        f"Consider increasing pool size to 50-60 connections",
                        "Monitor connection utilization",
                        "Implement connection health checks"
                    ]
                }
            )
            self.recommendations.append(recommendation)
    
    async def get_recommendations(self, category: Optional[str] = None) -> List[OptimizationRecommendation]:
        """Get optimization recommendations"""
        if category:
            return [r for r in self.recommendations if r.category == category]
        return self.recommendations.copy()
    
    async def apply_recommendation(self, recommendation_id: str) -> bool:
        """Apply an optimization recommendation"""
        recommendation = next((r for r in self.recommendations if r.id == recommendation_id), None)
        if not recommendation:
            return False
        
        try:
            # This would implement the actual optimization
            # For now, just mark as applied
            self.applied_optimizations.append(recommendation_id)
            logger.info(f"Applied optimization recommendation: {recommendation.title}")
            return True
        except Exception as e:
            logger.error(f"Failed to apply recommendation {recommendation_id}: {e}")
            return False


class PerformanceAnalyticsEngine:
    """
    Main performance analytics and auto-tuning engine
    """
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager()
        self.auto_tuner = AutoTuner()
        self._is_running = False
        
        # Setup default alerts
        self._setup_default_alerts()
        
        # Setup notification callback
        self.alert_manager.add_notification_callback(self._handle_alert_notification)
    
    def _setup_default_alerts(self):
        """Setup default performance alerts"""
        # High latency alert
        self.alert_manager.add_alert(PerformanceAlert(
            id="high_latency",
            metric_type=MetricType.LATENCY,
            threshold=1000.0,  # 1 second
            operator=">",
            message="High query latency detected",
            severity="high"
        ))
        
        # Low success rate alert
        self.alert_manager.add_alert(PerformanceAlert(
            id="low_success_rate",
            metric_type=MetricType.SUCCESS_RATE,
            threshold=0.95,  # 95%
            operator="<",
            message="Low query success rate detected",
            severity="critical"
        ))
        
        # High memory usage alert
        self.alert_manager.add_alert(PerformanceAlert(
            id="high_memory_usage",
            metric_type=MetricType.MEMORY_USAGE,
            threshold=0.9,  # 90%
            operator=">",
            message="High memory usage detected",
            severity="medium"
        ))
        
        # Low cache hit rate alert
        self.alert_manager.add_alert(PerformanceAlert(
            id="low_cache_hit_rate",
            metric_type=MetricType.CACHE_HIT_RATE,
            threshold=0.7,  # 70%
            operator="<",
            message="Low cache hit rate detected",
            severity="medium"
        ))
    
    async def _handle_alert_notification(self, notification: Dict[str, Any]):
        """Handle alert notifications"""
        # This could integrate with external monitoring systems
        # For now, just log
        logger.warning(f"Performance Alert: {notification}")
    
    async def start(self):
        """Start the analytics engine"""
        if self._is_running:
            return
        
        self._is_running = True
        
        # Start alert monitoring
        await self.alert_manager.start_monitoring(self.metrics_collector)
        
        # Start auto-tuning
        await self.auto_tuner.start_auto_tuning(self.metrics_collector)
        
        logger.info("Performance Analytics Engine started")
    
    async def stop(self):
        """Stop the analytics engine"""
        if not self._is_running:
            return
        
        self._is_running = False
        
        # Stop monitoring and tuning
        await self.alert_manager.stop_monitoring()
        await self.auto_tuner.stop_auto_tuning()
        
        logger.info("Performance Analytics Engine stopped")
    
    async def record_query_performance(
        self, 
        latency_ms: float, 
        success: bool, 
        provider: str,
        memory_usage: Optional[float] = None
    ):
        """Record query performance metrics"""
        await self.metrics_collector.record_metric("latency", latency_ms, {"provider": provider})
        await self.metrics_collector.record_metric("success_rate", 1.0 if success else 0.0, {"provider": provider})
        
        if memory_usage is not None:
            await self.metrics_collector.record_metric("memory_usage", memory_usage)
    
    async def record_cache_performance(self, hit_rate: float, cache_type: str):
        """Record cache performance metrics"""
        await self.metrics_collector.record_metric("cache_hit_rate", hit_rate, {"cache_type": cache_type})
    
    async def record_provider_health(self, provider: str, health_score: float):
        """Record provider health metrics"""
        await self.metrics_collector.record_metric("provider_health", health_score, {"provider": provider})
    
    async def get_performance_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive performance dashboard data"""
        # Get recent statistics (last hour)
        time_range = 3600  # 1 hour
        
        latency_stats = await self.metrics_collector.get_metric_statistics("latency", time_range)
        memory_stats = await self.metrics_collector.get_metric_statistics("memory_usage", time_range)
        cache_stats = await self.metrics_collector.get_metric_statistics("cache_hit_rate", time_range)
        success_stats = await self.metrics_collector.get_metric_statistics("success_rate", time_range)
        
        # Get active alerts
        active_alerts = await self.alert_manager.get_active_alerts()
        
        # Get recent recommendations
        recommendations = await self.auto_tuner.get_recommendations()
        recent_recommendations = [r for r in recommendations if time.time() - r.created_at < 86400]  # Last 24h
        
        return {
            "timestamp": time.time(),
            "performance_summary": {
                "latency": latency_stats,
                "memory_usage": memory_stats,
                "cache_performance": cache_stats,
                "success_rate": success_stats
            },
            "alerts": {
                "active_count": len(active_alerts),
                "active_alerts": [asdict(alert) for alert in active_alerts],
                "recent_history": await self.alert_manager.get_alert_history(20)
            },
            "optimization": {
                "recommendation_count": len(recent_recommendations),
                "recommendations": [asdict(rec) for rec in recent_recommendations[:10]],
                "applied_optimizations": len(self.auto_tuner.applied_optimizations)
            },
            "system_health": {
                "is_running": self._is_running,
                "uptime_seconds": time.time() - (self._start_time if hasattr(self, '_start_time') else time.time()),
                "metric_count": len(await self.metrics_collector.get_all_metric_names())
            }
        }
    
    async def get_detailed_analysis(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """Get detailed performance analysis"""
        time_range_seconds = time_range_hours * 3600
        
        # Get all metrics
        all_metrics = await self.metrics_collector.get_all_metric_names()
        detailed_metrics = {}
        
        for metric_name in all_metrics:
            detailed_metrics[metric_name] = await self.metrics_collector.get_metric_statistics(
                metric_name, time_range_seconds
            )
        
        # Performance trends
        trends = await self._analyze_performance_trends(time_range_seconds)
        
        # Resource utilization
        utilization = await self._analyze_resource_utilization(time_range_seconds)
        
        return {
            "analysis_period_hours": time_range_hours,
            "detailed_metrics": detailed_metrics,
            "performance_trends": trends,
            "resource_utilization": utilization,
            "recommendations": await self.auto_tuner.get_recommendations(),
            "optimization_opportunities": await self._identify_optimization_opportunities()
        }
    
    async def _analyze_performance_trends(self, time_range_seconds: int) -> Dict[str, Any]:
        """Analyze performance trends over time"""
        # Simplified trend analysis
        latency_points = await self.metrics_collector.get_metric_values("latency", time_range_seconds)
        
        if len(latency_points) < 2:
            return {"trend": "insufficient_data"}
        
        # Calculate trend direction
        recent_avg = statistics.mean([p.value for p in latency_points[-10:]])
        earlier_avg = statistics.mean([p.value for p in latency_points[:10]])
        
        trend_direction = "improving" if recent_avg < earlier_avg else "degrading"
        trend_magnitude = abs(recent_avg - earlier_avg) / earlier_avg if earlier_avg > 0 else 0
        
        return {
            "latency_trend": trend_direction,
            "trend_magnitude": trend_magnitude,
            "recent_avg_latency": recent_avg,
            "earlier_avg_latency": earlier_avg
        }
    
    async def _analyze_resource_utilization(self, time_range_seconds: int) -> Dict[str, Any]:
        """Analyze resource utilization patterns"""
        memory_points = await self.metrics_collector.get_metric_values("memory_usage", time_range_seconds)
        
        if not memory_points:
            return {"status": "no_data"}
        
        memory_values = [p.value for p in memory_points]
        
        return {
            "memory": {
                "avg_utilization": statistics.mean(memory_values),
                "peak_utilization": max(memory_values),
                "min_utilization": min(memory_values),
                "utilization_variance": statistics.variance(memory_values) if len(memory_values) > 1 else 0
            }
        }
    
    async def _identify_optimization_opportunities(self) -> List[Dict[str, Any]]:
        """Identify immediate optimization opportunities"""
        opportunities = []
        
        # Check recent performance
        recent_latency = await self.metrics_collector.get_metric_statistics("latency", 1800)  # 30 min
        
        if recent_latency and recent_latency.get('mean', 0) > 300:
            opportunities.append({
                "type": "latency_optimization",
                "description": "Recent queries showing high latency",
                "priority": "high",
                "estimated_impact": "20-30% latency reduction"
            })
        
        # Check cache performance
        recent_cache = await self.metrics_collector.get_metric_statistics("cache_hit_rate", 1800)
        
        if recent_cache and recent_cache.get('mean', 1.0) < 0.8:
            opportunities.append({
                "type": "cache_optimization",
                "description": "Cache hit rate below optimal threshold",
                "priority": "medium",
                "estimated_impact": "10-15% latency reduction"
            })
        
        return opportunities


# Singleton instance
analytics_engine = PerformanceAnalyticsEngine()