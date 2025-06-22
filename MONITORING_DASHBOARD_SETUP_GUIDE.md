# Advanced Monitoring Dashboard Setup Guide
**Core Nexus PGVector Performance Optimization System**

**Version**: 1.0  
**Date**: June 22, 2025  
**Components**: Advanced Monitoring Dashboard + Web Interface  

---

## 🎯 Overview

The Advanced Monitoring Dashboard provides comprehensive real-time monitoring, alerting, and performance analysis for the Core Nexus PostgreSQL vector optimization system.

### Key Features
- **Real-time Performance Monitoring**: P95 latency, throughput, error rates
- **Historical Data Tracking**: SQLite-based performance history
- **Intelligent Alerting**: Configurable thresholds with severity levels
- **Web Dashboard Interface**: Real-time visual dashboard with charts
- **Performance Reporting**: Automated performance analysis and recommendations
- **Data Export**: JSON/CSV export for external analysis

### System Components
- **`advanced_monitoring_dashboard.py`**: Core monitoring engine (645 lines)
- **`web_dashboard.py`**: Web interface with real-time updates (400+ lines)
- **`monitoring_dashboard.db`**: SQLite database for historical data
- **Real-time WebSocket**: Live performance updates

---

## 🚀 Quick Setup

### 1. Install Dependencies
```bash
# Install required Python packages
pip install fastapi uvicorn websockets sqlite3

# Or install from requirements
pip install -r requirements.txt
```

### 2. Initialize Monitoring System
```bash
# Initialize the monitoring dashboard
python3 advanced_monitoring_dashboard.py

# Expected output:
# ✅ Monitoring database initialized
# ✅ Performance baseline established  
# ✅ Advanced monitoring dashboard initialized
```

### 3. Start Web Dashboard (Optional)
```bash
# Start web dashboard on port 8080
python3 web_dashboard.py

# Access dashboard at: http://localhost:8080
```

### 4. Start Continuous Monitoring
```bash
# Start continuous monitoring (60-second intervals)
python3 advanced_monitoring_dashboard.py monitor 60

# Or custom interval (30 seconds)
python3 advanced_monitoring_dashboard.py monitor 30
```

---

## 📊 Dashboard Usage

### Command Line Interface

#### Take Performance Snapshot
```bash
# Single performance measurement
python3 advanced_monitoring_dashboard.py snapshot

# Output:
# {
#   "timestamp": "2025-06-22T03:30:00",
#   "p95_latency_ms": 18.5,
#   "throughput_qps": 105.2,
#   "error_rate": 0.001,
#   "performance_grade": "EXCELLENT"
# }
```

#### Generate Performance Report
```bash
# 24-hour performance report
python3 advanced_monitoring_dashboard.py report

# Custom time period (48 hours)
python3 advanced_monitoring_dashboard.py report 48

# Output: Comprehensive JSON report with statistics and recommendations
```

#### Export Dashboard Data
```bash
# Export as JSON
python3 advanced_monitoring_dashboard.py export json

# Export as CSV
python3 advanced_monitoring_dashboard.py export csv

# Output: dashboard_export_[timestamp].json/csv
```

#### Continuous Monitoring
```bash
# Start monitoring with default 60-second intervals
python3 advanced_monitoring_dashboard.py monitor

# Custom interval (30 seconds)
python3 advanced_monitoring_dashboard.py monitor 30

# Real-time output:
# ✅ Performance: P95=18.2ms, QPS=108.5, Errors=0.1%
# ⚠️ ALERT: WARNING: P95 latency 26.1ms exceeds 25.0ms
```

### Web Dashboard Interface

#### Access Dashboard
```bash
# Start web dashboard
python3 web_dashboard.py

# Open browser to: http://localhost:8080
```

#### Dashboard Features
- **Real-time Metrics**: P95 latency, throughput, error rate, connections
- **Performance Chart**: Historical performance visualization
- **Alert Panel**: Recent alerts with severity indicators
- **Status Indicators**: Visual health status (green/yellow/red)
- **Responsive Design**: Mobile-friendly interface

#### API Endpoints
```bash
# Current performance
curl http://localhost:8080/api/performance/current

# Performance history (24 hours)
curl http://localhost:8080/api/performance/history?hours=24

# Recent alerts
curl http://localhost:8080/api/alerts/recent?hours=12

# Health check
curl http://localhost:8080/api/health
```

---

## ⚙️ Configuration

### Alert Thresholds
```python
# Default alert thresholds (configurable)
alert_thresholds = {
    "p95_latency_warning": 25.0,   # ms
    "p95_latency_critical": 50.0,  # ms
    "throughput_warning": 80.0,    # QPS
    "throughput_critical": 50.0,   # QPS
    "error_rate_warning": 0.05,    # 5%
    "error_rate_critical": 0.10,   # 10%
}
```

### Monitoring Intervals
```bash
# High-frequency monitoring (every 30 seconds)
python3 advanced_monitoring_dashboard.py monitor 30

# Standard monitoring (every 60 seconds)  
python3 advanced_monitoring_dashboard.py monitor 60

# Low-frequency monitoring (every 5 minutes)
python3 advanced_monitoring_dashboard.py monitor 300
```

### Database Configuration
```python
# SQLite database location (configurable)
DB_PATH = "monitoring_dashboard.db"

# Data retention (automatic cleanup)
# Keeps last 7 days of performance data
# Keeps last 30 days of alerts
```

---

## 📈 Performance Metrics

### Primary Metrics
- **P95 Latency**: 95th percentile query response time
- **Throughput**: Queries per second (QPS)
- **Error Rate**: Percentage of failed queries
- **Connection Count**: Active database connections

### Secondary Metrics
- **P50/P99 Latency**: Additional latency percentiles
- **Average/Max Latency**: Latency distribution
- **Concurrent QPS**: Multi-threaded throughput
- **System Resources**: CPU and memory usage (when available)

### Performance Grades
- **EXCELLENT**: P95 <20ms, QPS >100, Errors <1%
- **GOOD**: P95 <30ms, QPS >80, Errors <5%
- **FAIR**: P95 <50ms, QPS >50, Errors <10%
- **POOR**: Above fair thresholds

---

## 🚨 Alerting System

### Alert Severity Levels

#### CRITICAL (🚨)
- P95 latency >50ms
- Throughput <50 QPS
- Error rate >10%

#### WARNING (⚠️)
- P95 latency >25ms
- Throughput <80 QPS
- Error rate >5%

### Alert Processing
```bash
# Alerts are:
# 1. Logged to console with severity indicators
# 2. Stored in SQLite database with timestamps
# 3. Displayed in web dashboard alert panel
# 4. Available via API for external integrations
```

### Sample Alerts
```
🚨 CRITICAL: P95 latency 67.3ms exceeds 50.0ms
⚠️ WARNING: Throughput 75.2 QPS below 80.0 QPS
⚠️ WARNING: Error rate 6.2% exceeds 5.0%
```

---

## 📊 Reporting and Analysis

### Automated Reports
```json
{
  "report_period": "24 hours",
  "data_points": 1440,
  "performance_summary": {
    "p95_latency": {
      "min": 15.2,
      "max": 28.1,
      "avg": 19.7,
      "median": 18.9
    },
    "throughput": {
      "min": 95.3,
      "max": 112.8,
      "avg": 104.2,
      "median": 105.1
    }
  },
  "performance_grade": "EXCELLENT",
  "recommendations": [
    "Performance is within target ranges - continue monitoring"
  ]
}
```

### Performance Recommendations
- **Excellent Performance**: Continue current optimization
- **Latency Issues**: Consider HNSW parameter tuning or configuration review
- **Throughput Issues**: Investigate connection pool or index maintenance
- **High Error Rate**: Check application and database logs

---

## 🔧 Integration Examples

### Prometheus Integration
```python
# Export metrics for Prometheus scraping
# (Custom implementation needed)

from prometheus_client import Gauge, start_http_server

# Define metrics
p95_latency_gauge = Gauge('pg_vector_p95_latency_ms', 'P95 latency in milliseconds')
throughput_gauge = Gauge('pg_vector_throughput_qps', 'Throughput in queries per second')

# Update metrics in monitoring loop
p95_latency_gauge.set(snapshot.p95_latency_ms)
throughput_gauge.set(snapshot.throughput_qps)
```

### Grafana Dashboard
```json
{
  "dashboard": {
    "title": "Core Nexus PGVector Performance",
    "panels": [
      {
        "title": "P95 Latency",
        "type": "stat",
        "targets": [
          {
            "expr": "pg_vector_p95_latency_ms",
            "refId": "A"
          }
        ]
      }
    ]
  }
}
```

### Slack Notifications
```python
# Custom alert webhook (implement as needed)
import requests

async def send_slack_alert(alert):
    webhook_url = "https://hooks.slack.com/services/..."
    
    payload = {
        "text": f"🚨 Performance Alert: {alert['message']}",
        "channel": "#performance-alerts"
    }
    
    requests.post(webhook_url, json=payload)
```

---

## 🚀 Production Deployment

### Deployment Architecture
```bash
# Recommended production setup:

# 1. Monitoring Service (dedicated server/container)
python3 advanced_monitoring_dashboard.py monitor 60

# 2. Web Dashboard (load-balanced, optional)
python3 web_dashboard.py

# 3. Database Backup (automated)
sqlite3 monitoring_dashboard.db ".backup monitoring_backup_$(date +%Y%m%d).db"

# 4. Log Rotation (system cron)
logrotate /etc/logrotate.d/monitoring-dashboard
```

### Systemd Service Configuration
```ini
# /etc/systemd/system/nexus-monitoring.service
[Unit]
Description=Core Nexus Performance Monitoring Dashboard
After=network.target

[Service]
Type=simple
User=nexus
WorkingDirectory=/opt/nexus-monitoring
ExecStart=/usr/bin/python3 advanced_monitoring_dashboard.py monitor 60
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Web Dashboard Service
```ini
# /etc/systemd/system/nexus-web-dashboard.service
[Unit]
Description=Core Nexus Web Dashboard
After=network.target

[Service]
Type=simple
User=nexus
WorkingDirectory=/opt/nexus-monitoring
ExecStart=/usr/bin/python3 web_dashboard.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Nginx Configuration
```nginx
# /etc/nginx/sites-available/nexus-dashboard
server {
    listen 80;
    server_name dashboard.nexus.internal;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 🔧 Troubleshooting

### Common Issues

#### Dashboard Not Starting
```bash
# Check dependencies
pip list | grep -E "(fastapi|uvicorn|sqlite3)"

# Check database permissions
ls -la monitoring_dashboard.db
chmod 664 monitoring_dashboard.db

# Check port availability
netstat -tlnp | grep 8080
```

#### No Performance Data
```bash
# Verify database credentials
echo "PGVECTOR_PASSWORD: ${PGVECTOR_PASSWORD:-NOT_SET}"

# Test database connection
python3 -c "
import asyncio
import asyncpg
import os

async def test():
    try:
        conn = await asyncpg.connect(
            host=os.getenv('PGVECTOR_HOST', 'localhost'),
            database=os.getenv('PGVECTOR_DATABASE', 'nexus_memory_db'),
            user=os.getenv('PGVECTOR_USER', 'nexus_memory_db_user'),
            password=os.getenv('PGVECTOR_PASSWORD')
        )
        print('✅ Database connection successful')
        await conn.close()
    except Exception as e:
        print(f'❌ Database connection failed: {e}')

asyncio.run(test())
"
```

#### High CPU Usage
```bash
# Reduce monitoring frequency
python3 advanced_monitoring_dashboard.py monitor 300  # 5-minute intervals

# Optimize database queries
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
```

### Performance Tuning
```python
# Monitoring configuration tuning
monitoring_config = {
    "snapshot_interval": 60,      # Seconds between snapshots
    "benchmark_queries": 10,      # Queries per benchmark (vs default 25)
    "connection_pool_size": 3,    # Smaller pool for monitoring
    "query_timeout": 5            # Faster timeout for monitoring queries
}
```

---

## 📚 Advanced Usage

### Custom Alert Thresholds
```python
# Modify alert thresholds in advanced_monitoring_dashboard.py
dashboard = AdvancedMonitoringDashboard()
dashboard.alert_thresholds = {
    "p95_latency_warning": 20.0,   # Stricter latency requirement
    "p95_latency_critical": 40.0,
    "throughput_warning": 120.0,   # Higher throughput expectation  
    "throughput_critical": 80.0,
    "error_rate_warning": 0.02,    # 2% error rate warning
    "error_rate_critical": 0.05,   # 5% error rate critical
}
```

### Data Retention Policy
```python
# Automatic data cleanup (add to monitoring loop)
async def cleanup_old_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Keep last 7 days of performance data
    cutoff = (datetime.now() - timedelta(days=7)).isoformat()
    cursor.execute('DELETE FROM performance_snapshots WHERE timestamp < ?', (cutoff,))
    
    # Keep last 30 days of alerts
    alert_cutoff = (datetime.now() - timedelta(days=30)).isoformat()
    cursor.execute('DELETE FROM alerts WHERE timestamp < ?', (alert_cutoff,))
    
    conn.commit()
    conn.close()
```

### External Monitoring Integration
```python
# Send metrics to external monitoring systems
async def send_metrics_to_datadog(snapshot):
    from datadog import statsd
    
    statsd.gauge('nexus.performance.p95_latency', snapshot.p95_latency_ms)
    statsd.gauge('nexus.performance.throughput', snapshot.throughput_qps)
    statsd.gauge('nexus.performance.error_rate', snapshot.error_rate)
```

---

## 📋 Maintenance

### Daily Operations
- [ ] **Review Dashboard**: Check performance grade and recent alerts
- [ ] **Verify Monitoring**: Confirm continuous monitoring is active
- [ ] **Check Disk Space**: Monitor SQLite database growth

### Weekly Operations
- [ ] **Performance Report**: Generate and review weekly performance report
- [ ] **Alert Analysis**: Review alert patterns and adjust thresholds if needed
- [ ] **Database Maintenance**: Vacuum SQLite database for optimal performance

### Monthly Operations
- [ ] **Trend Analysis**: Analyze long-term performance trends
- [ ] **Threshold Tuning**: Adjust alert thresholds based on actual performance
- [ ] **System Optimization**: Review and optimize monitoring configuration

---

## 🎯 Success Metrics

### Monitoring Effectiveness
- **Data Availability**: >99% successful performance snapshots
- **Alert Accuracy**: <5% false positive alert rate
- **Response Time**: Alert detection within 2 monitoring intervals
- **Dashboard Uptime**: >99.5% web dashboard availability

### Performance Tracking
- **Baseline Accuracy**: ±5% variance from actual performance
- **Trend Detection**: Early identification of performance degradation
- **Optimization Validation**: Measurement of optimization effectiveness
- **Team Adoption**: Regular dashboard usage by operations teams

---

## 📞 Support and Maintenance

### Monitoring Team Contacts
- **Primary**: Performance Engineering Team
- **Secondary**: DevOps Team
- **Emergency**: On-call Engineering

### Documentation Updates
- **Version Control**: Track changes to monitoring configuration
- **Alert Thresholds**: Document any threshold adjustments
- **Performance Baselines**: Update baselines after optimizations

### Future Enhancements
- **Machine Learning**: Predictive performance analysis
- **Advanced Alerting**: Smart alert correlation and noise reduction
- **Multi-Region Monitoring**: Support for distributed deployments
- **Custom Dashboards**: Team-specific performance views

---

**MONITORING DASHBOARD STATUS: PRODUCTION READY** ✅

*This monitoring system provides comprehensive visibility into the Core Nexus PGVector optimization performance with real-time alerts, historical analysis, and visual dashboards for operational excellence.*