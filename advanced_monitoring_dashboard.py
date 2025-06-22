#!/usr/bin/env python3
"""
Advanced Monitoring Dashboard for Core Nexus PGVector Optimization System

Provides comprehensive real-time monitoring, alerting, and performance analysis
for the PostgreSQL vector optimization system.
"""

import asyncio
import asyncpg
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import sqlite3
from dataclasses import dataclass, asdict
import statistics

# Add memory service to path
sys.path.append(str(Path(__file__).parent / "python" / "memory_service" / "src"))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class PerformanceSnapshot:
    """Single performance measurement snapshot"""
    timestamp: datetime
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    avg_latency_ms: float
    max_latency_ms: float
    throughput_qps: float
    concurrent_qps: float
    error_rate: float
    connection_count: int
    cpu_usage: float
    memory_usage_mb: float
    
class AdvancedMonitoringDashboard:
    """Comprehensive monitoring dashboard for optimization system"""
    
    def __init__(self, db_path: str = "monitoring_dashboard.db"):
        self.db_path = db_path
        self.alert_thresholds = {
            "p95_latency_warning": 25.0,  # ms
            "p95_latency_critical": 50.0,  # ms
            "throughput_warning": 80.0,  # QPS
            "throughput_critical": 50.0,  # QPS
            "error_rate_warning": 0.05,  # 5%
            "error_rate_critical": 0.10,  # 10%
        }
        self.monitoring_active = False
        
    async def initialize_dashboard(self):
        """Initialize monitoring dashboard and database"""
        logger.info("=== INITIALIZING ADVANCED MONITORING DASHBOARD ===")
        
        # Initialize SQLite database for historical data
        await self._initialize_database()
        
        # Initialize performance baseline
        await self._establish_baseline()
        
        logger.info("✅ Advanced monitoring dashboard initialized")
    
    async def _initialize_database(self):
        """Initialize SQLite database for monitoring data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create performance snapshots table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                p50_latency_ms REAL,
                p95_latency_ms REAL,
                p99_latency_ms REAL,
                avg_latency_ms REAL,
                max_latency_ms REAL,
                throughput_qps REAL,
                concurrent_qps REAL,
                error_rate REAL,
                connection_count INTEGER,
                cpu_usage REAL,
                memory_usage_mb REAL
            )
        ''')
        
        # Create alerts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                metric TEXT NOT NULL,
                value REAL NOT NULL,
                threshold REAL NOT NULL,
                message TEXT,
                acknowledged BOOLEAN DEFAULT FALSE
            )
        ''')
        
        # Create optimization events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS optimization_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                description TEXT,
                performance_before TEXT,
                performance_after TEXT,
                success BOOLEAN
            )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info("✅ Monitoring database initialized")
    
    async def _establish_baseline(self):
        """Establish performance baseline for comparison"""
        try:
            from memory_service.performance_monitor import VectorPerformanceMonitor
            from memory_service.config import DatabaseConfig
            
            # Create connection pool
            conn_str = f"postgresql://{DatabaseConfig.USER}:{DatabaseConfig.PASSWORD}@{DatabaseConfig.HOST}:{DatabaseConfig.PORT}/{DatabaseConfig.DATABASE}"
            pool = await asyncpg.create_pool(conn_str, min_size=2, max_size=5)
            
            # Run baseline measurement
            monitor = VectorPerformanceMonitor(pool, "vector_memories")
            baseline_results = await monitor.run_comprehensive_benchmark()
            
            await pool.close()
            
            # Store baseline
            baseline_data = {
                "timestamp": datetime.now().isoformat(),
                "baseline_results": baseline_results,
                "optimization_status": "baseline_established"
            }
            
            with open("monitoring_baseline.json", "w") as f:
                json.dump(baseline_data, f, indent=2, default=str)
            
            logger.info("✅ Performance baseline established")
            
        except Exception as e:
            logger.warning(f"⚠️ Could not establish baseline: {e}")
    
    async def start_continuous_monitoring(self, interval_seconds: int = 60):
        """Start continuous performance monitoring"""
        logger.info(f"🚀 Starting continuous monitoring (interval: {interval_seconds}s)")
        
        self.monitoring_active = True
        
        try:
            while self.monitoring_active:
                # Take performance snapshot
                snapshot = await self._take_performance_snapshot()
                
                if snapshot:
                    # Store snapshot
                    await self._store_snapshot(snapshot)
                    
                    # Check for alerts
                    await self._check_alerts(snapshot)
                    
                    # Log current status
                    await self._log_current_status(snapshot)
                
                # Wait for next interval
                await asyncio.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            logger.info("🛑 Monitoring stopped by user")
        except Exception as e:
            logger.error(f"❌ Monitoring error: {e}")
        finally:
            self.monitoring_active = False
    
    async def _take_performance_snapshot(self) -> Optional[PerformanceSnapshot]:
        """Take a comprehensive performance snapshot"""
        try:
            from memory_service.performance_monitor import VectorPerformanceMonitor
            from memory_service.config import DatabaseConfig
            
            # Create connection pool
            conn_str = f"postgresql://{DatabaseConfig.USER}:{DatabaseConfig.PASSWORD}@{DatabaseConfig.HOST}:{DatabaseConfig.PORT}/{DatabaseConfig.DATABASE}"
            pool = await asyncpg.create_pool(conn_str, min_size=2, max_size=5, command_timeout=10)
            
            # Run quick benchmark
            monitor = VectorPerformanceMonitor(pool, "vector_memories")
            results = await monitor.run_quick_benchmark()
            
            # Get system metrics
            system_metrics = await self._get_system_metrics(pool)
            
            await pool.close()
            
            # Create snapshot
            snapshot = PerformanceSnapshot(
                timestamp=datetime.now(),
                p50_latency_ms=results.get("p50_latency_ms", 0),
                p95_latency_ms=results.get("p95_latency_ms", 0),
                p99_latency_ms=results.get("p99_latency_ms", 0),
                avg_latency_ms=results.get("avg_latency_ms", 0),
                max_latency_ms=results.get("max_latency_ms", 0),
                throughput_qps=results.get("throughput_qps", 0),
                concurrent_qps=results.get("concurrent_qps", 0),
                error_rate=results.get("error_rate", 0),
                connection_count=system_metrics.get("connection_count", 0),
                cpu_usage=system_metrics.get("cpu_usage", 0),
                memory_usage_mb=system_metrics.get("memory_usage_mb", 0)
            )
            
            return snapshot
            
        except Exception as e:
            logger.error(f"❌ Failed to take performance snapshot: {e}")
            return None
    
    async def _get_system_metrics(self, pool) -> Dict[str, Any]:
        """Get system-level metrics from database"""
        try:
            async with pool.acquire() as conn:
                # Get connection count
                connection_count = await conn.fetchval("""
                    SELECT COUNT(*) 
                    FROM pg_stat_activity 
                    WHERE datname = current_database()
                """)
                
                # Get database size
                db_size = await conn.fetchval("""
                    SELECT pg_database_size(current_database())
                """)
                
                # Get cache hit ratio
                cache_hit_ratio = await conn.fetchval("""
                    SELECT 
                        CASE 
                            WHEN blks_read + blks_hit = 0 THEN 0
                            ELSE blks_hit::float / (blks_read + blks_hit)
                        END
                    FROM pg_stat_database 
                    WHERE datname = current_database()
                """)
                
                return {
                    "connection_count": connection_count,
                    "db_size_bytes": db_size,
                    "cache_hit_ratio": cache_hit_ratio,
                    "cpu_usage": 0,  # Would need system integration
                    "memory_usage_mb": 0  # Would need system integration
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to get system metrics: {e}")
            return {}
    
    async def _store_snapshot(self, snapshot: PerformanceSnapshot):
        """Store performance snapshot in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO performance_snapshots (
                    timestamp, p50_latency_ms, p95_latency_ms, p99_latency_ms,
                    avg_latency_ms, max_latency_ms, throughput_qps, concurrent_qps,
                    error_rate, connection_count, cpu_usage, memory_usage_mb
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                snapshot.timestamp.isoformat(),
                snapshot.p50_latency_ms,
                snapshot.p95_latency_ms,
                snapshot.p99_latency_ms,
                snapshot.avg_latency_ms,
                snapshot.max_latency_ms,
                snapshot.throughput_qps,
                snapshot.concurrent_qps,
                snapshot.error_rate,
                snapshot.connection_count,
                snapshot.cpu_usage,
                snapshot.memory_usage_mb
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Failed to store snapshot: {e}")
    
    async def _check_alerts(self, snapshot: PerformanceSnapshot):
        """Check performance metrics against alert thresholds"""
        alerts = []
        
        # Check P95 latency
        if snapshot.p95_latency_ms > self.alert_thresholds["p95_latency_critical"]:
            alerts.append({
                "type": "performance_degradation",
                "severity": "critical",
                "metric": "p95_latency_ms",
                "value": snapshot.p95_latency_ms,
                "threshold": self.alert_thresholds["p95_latency_critical"],
                "message": f"CRITICAL: P95 latency {snapshot.p95_latency_ms:.1f}ms exceeds {self.alert_thresholds['p95_latency_critical']}ms"
            })
        elif snapshot.p95_latency_ms > self.alert_thresholds["p95_latency_warning"]:
            alerts.append({
                "type": "performance_degradation",
                "severity": "warning",
                "metric": "p95_latency_ms",
                "value": snapshot.p95_latency_ms,
                "threshold": self.alert_thresholds["p95_latency_warning"],
                "message": f"WARNING: P95 latency {snapshot.p95_latency_ms:.1f}ms exceeds {self.alert_thresholds['p95_latency_warning']}ms"
            })
        
        # Check throughput
        if snapshot.throughput_qps < self.alert_thresholds["throughput_critical"]:
            alerts.append({
                "type": "throughput_degradation",
                "severity": "critical",
                "metric": "throughput_qps",
                "value": snapshot.throughput_qps,
                "threshold": self.alert_thresholds["throughput_critical"],
                "message": f"CRITICAL: Throughput {snapshot.throughput_qps:.1f} QPS below {self.alert_thresholds['throughput_critical']} QPS"
            })
        elif snapshot.throughput_qps < self.alert_thresholds["throughput_warning"]:
            alerts.append({
                "type": "throughput_degradation",
                "severity": "warning",
                "metric": "throughput_qps",
                "value": snapshot.throughput_qps,
                "threshold": self.alert_thresholds["throughput_warning"],
                "message": f"WARNING: Throughput {snapshot.throughput_qps:.1f} QPS below {self.alert_thresholds['throughput_warning']} QPS"
            })
        
        # Check error rate
        if snapshot.error_rate > self.alert_thresholds["error_rate_critical"]:
            alerts.append({
                "type": "error_rate_high",
                "severity": "critical",
                "metric": "error_rate",
                "value": snapshot.error_rate,
                "threshold": self.alert_thresholds["error_rate_critical"],
                "message": f"CRITICAL: Error rate {snapshot.error_rate:.1%} exceeds {self.alert_thresholds['error_rate_critical']:.1%}"
            })
        elif snapshot.error_rate > self.alert_thresholds["error_rate_warning"]:
            alerts.append({
                "type": "error_rate_high",
                "severity": "warning",
                "metric": "error_rate",
                "value": snapshot.error_rate,
                "threshold": self.alert_thresholds["error_rate_warning"],
                "message": f"WARNING: Error rate {snapshot.error_rate:.1%} exceeds {self.alert_thresholds['error_rate_warning']:.1%}"
            })
        
        # Store and process alerts
        for alert in alerts:
            await self._store_alert(alert, snapshot.timestamp)
            await self._process_alert(alert)
    
    async def _store_alert(self, alert: Dict[str, Any], timestamp: datetime):
        """Store alert in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO alerts (
                    timestamp, alert_type, severity, metric, value, threshold, message
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                timestamp.isoformat(),
                alert["type"],
                alert["severity"],
                alert["metric"],
                alert["value"],
                alert["threshold"],
                alert["message"]
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Failed to store alert: {e}")
    
    async def _process_alert(self, alert: Dict[str, Any]):
        """Process and log alert"""
        severity_icon = "🚨" if alert["severity"] == "critical" else "⚠️"
        logger.warning(f"{severity_icon} ALERT: {alert['message']}")
        
        # In a production system, this would send notifications
        # via email, Slack, PagerDuty, etc.
    
    async def _log_current_status(self, snapshot: PerformanceSnapshot):
        """Log current performance status"""
        status_icon = "✅" if snapshot.p95_latency_ms < 25 and snapshot.throughput_qps > 80 else "⚠️"
        
        logger.info(
            f"{status_icon} Performance: P95={snapshot.p95_latency_ms:.1f}ms, "
            f"QPS={snapshot.throughput_qps:.1f}, Errors={snapshot.error_rate:.1%}"
        )
    
    async def generate_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        logger.info(f"📊 Generating performance report for last {hours} hours")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get performance data for specified period
            since_timestamp = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            cursor.execute('''
                SELECT * FROM performance_snapshots 
                WHERE timestamp > ? 
                ORDER BY timestamp
            ''', (since_timestamp,))
            
            snapshots = cursor.fetchall()
            
            if not snapshots:
                return {"error": "No performance data available for specified period"}
            
            # Calculate statistics
            p95_values = [row[3] for row in snapshots if row[3] is not None]
            throughput_values = [row[7] for row in snapshots if row[7] is not None]
            error_rates = [row[9] for row in snapshots if row[9] is not None]
            
            # Get alerts for period
            cursor.execute('''
                SELECT alert_type, severity, COUNT(*) as count
                FROM alerts 
                WHERE timestamp > ?
                GROUP BY alert_type, severity
            ''', (since_timestamp,))
            
            alerts_summary = cursor.fetchall()
            
            conn.close()
            
            # Generate report
            report = {
                "report_period": f"{hours} hours",
                "data_points": len(snapshots),
                "performance_summary": {
                    "p95_latency": {
                        "min": min(p95_values) if p95_values else 0,
                        "max": max(p95_values) if p95_values else 0,
                        "avg": statistics.mean(p95_values) if p95_values else 0,
                        "median": statistics.median(p95_values) if p95_values else 0
                    },
                    "throughput": {
                        "min": min(throughput_values) if throughput_values else 0,
                        "max": max(throughput_values) if throughput_values else 0,
                        "avg": statistics.mean(throughput_values) if throughput_values else 0,
                        "median": statistics.median(throughput_values) if throughput_values else 0
                    },
                    "error_rate": {
                        "min": min(error_rates) if error_rates else 0,
                        "max": max(error_rates) if error_rates else 0,
                        "avg": statistics.mean(error_rates) if error_rates else 0
                    }
                },
                "alerts_summary": [
                    {"type": row[0], "severity": row[1], "count": row[2]}
                    for row in alerts_summary
                ],
                "performance_grade": self._calculate_performance_grade(p95_values, throughput_values, error_rates),
                "recommendations": self._generate_recommendations(p95_values, throughput_values, error_rates)
            }
            
            # Save report
            timestamp = int(time.time())
            report_file = f"performance_report_{timestamp}.json"
            
            with open(report_file, "w") as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"📊 Performance report saved: {report_file}")
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Failed to generate performance report: {e}")
            return {"error": str(e)}
    
    def _calculate_performance_grade(self, p95_values: List[float], 
                                   throughput_values: List[float], 
                                   error_rates: List[float]) -> str:
        """Calculate overall performance grade"""
        if not p95_values or not throughput_values:
            return "UNKNOWN"
        
        avg_p95 = statistics.mean(p95_values)
        avg_throughput = statistics.mean(throughput_values)
        avg_error_rate = statistics.mean(error_rates) if error_rates else 0
        
        # Grade based on targets
        if avg_p95 < 20 and avg_throughput > 100 and avg_error_rate < 0.01:
            return "EXCELLENT"
        elif avg_p95 < 30 and avg_throughput > 80 and avg_error_rate < 0.05:
            return "GOOD"
        elif avg_p95 < 50 and avg_throughput > 50 and avg_error_rate < 0.10:
            return "FAIR"
        else:
            return "POOR"
    
    def _generate_recommendations(self, p95_values: List[float], 
                                throughput_values: List[float], 
                                error_rates: List[float]) -> List[str]:
        """Generate performance improvement recommendations"""
        recommendations = []
        
        if p95_values:
            avg_p95 = statistics.mean(p95_values)
            if avg_p95 > 50:
                recommendations.append("CRITICAL: P95 latency is high - consider emergency optimization review")
            elif avg_p95 > 25:
                recommendations.append("Consider HNSW index parameter tuning or PostgreSQL configuration review")
        
        if throughput_values:
            avg_throughput = statistics.mean(throughput_values)
            if avg_throughput < 50:
                recommendations.append("CRITICAL: Throughput is very low - investigate system bottlenecks")
            elif avg_throughput < 100:
                recommendations.append("Consider connection pool optimization or index maintenance")
        
        if error_rates:
            avg_error_rate = statistics.mean(error_rates)
            if avg_error_rate > 0.05:
                recommendations.append("High error rate detected - investigate application and database logs")
        
        if not recommendations:
            recommendations.append("Performance is within target ranges - continue monitoring")
        
        return recommendations
    
    async def export_dashboard_data(self, format: str = "json") -> str:
        """Export dashboard data for external visualization"""
        logger.info(f"📤 Exporting dashboard data in {format} format")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get recent performance data (last 7 days)
            since_timestamp = (datetime.now() - timedelta(days=7)).isoformat()
            
            cursor.execute('''
                SELECT * FROM performance_snapshots 
                WHERE timestamp > ? 
                ORDER BY timestamp
            ''', (since_timestamp,))
            
            snapshots = cursor.fetchall()
            
            # Get column names
            column_names = [description[0] for description in cursor.description]
            
            # Convert to list of dictionaries
            data = [dict(zip(column_names, row)) for row in snapshots]
            
            conn.close()
            
            # Export data
            timestamp = int(time.time())
            
            if format.lower() == "json":
                export_file = f"dashboard_export_{timestamp}.json"
                with open(export_file, "w") as f:
                    json.dump(data, f, indent=2, default=str)
            elif format.lower() == "csv":
                import csv
                export_file = f"dashboard_export_{timestamp}.csv"
                with open(export_file, "w", newline='') as f:
                    if data:
                        writer = csv.DictWriter(f, fieldnames=data[0].keys())
                        writer.writeheader()
                        writer.writerows(data)
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            logger.info(f"📤 Dashboard data exported: {export_file}")
            
            return export_file
            
        except Exception as e:
            logger.error(f"❌ Failed to export dashboard data: {e}")
            return ""
    
    def stop_monitoring(self):
        """Stop continuous monitoring"""
        logger.info("🛑 Stopping monitoring dashboard")
        self.monitoring_active = False

async def main():
    """Main dashboard function"""
    logger.info("🚀 Starting Advanced Monitoring Dashboard")
    
    # Initialize dashboard
    dashboard = AdvancedMonitoringDashboard()
    await dashboard.initialize_dashboard()
    
    try:
        # Check command line arguments
        if len(sys.argv) > 1:
            command = sys.argv[1].lower()
            
            if command == "monitor":
                # Start continuous monitoring
                interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
                await dashboard.start_continuous_monitoring(interval)
                
            elif command == "report":
                # Generate performance report
                hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
                report = await dashboard.generate_performance_report(hours)
                print(json.dumps(report, indent=2, default=str))
                
            elif command == "export":
                # Export dashboard data
                format = sys.argv[2] if len(sys.argv) > 2 else "json"
                export_file = await dashboard.export_dashboard_data(format)
                print(f"Data exported to: {export_file}")
                
            elif command == "snapshot":
                # Take single performance snapshot
                snapshot = await dashboard._take_performance_snapshot()
                if snapshot:
                    print(json.dumps(asdict(snapshot), indent=2, default=str))
                    
            else:
                print(f"Unknown command: {command}")
                print("Available commands: monitor, report, export, snapshot")
                
        else:
            # Default: show current status
            snapshot = await dashboard._take_performance_snapshot()
            if snapshot:
                print("=== CURRENT PERFORMANCE STATUS ===")
                print(f"Timestamp: {snapshot.timestamp}")
                print(f"P95 Latency: {snapshot.p95_latency_ms:.1f}ms")
                print(f"Throughput: {snapshot.throughput_qps:.1f} QPS")
                print(f"Error Rate: {snapshot.error_rate:.1%}")
                print(f"Connections: {snapshot.connection_count}")
                
                # Performance grade
                grade = dashboard._calculate_performance_grade(
                    [snapshot.p95_latency_ms], 
                    [snapshot.throughput_qps], 
                    [snapshot.error_rate]
                )
                print(f"Performance Grade: {grade}")
            else:
                print("❌ Unable to take performance snapshot")
    
    except KeyboardInterrupt:
        logger.info("🛑 Dashboard stopped by user")
    except Exception as e:
        logger.error(f"❌ Dashboard error: {e}")

if __name__ == "__main__":
    asyncio.run(main())