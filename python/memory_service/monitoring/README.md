# Core Nexus Monitoring Stack

Production-ready monitoring and alerting for the Core Nexus Memory Service.

## 🚀 Quick Start

### 1. Start Monitoring Stack
```bash
cd monitoring
docker-compose up -d
```

### 2. Access Dashboards
- **Grafana**: http://localhost:3000 (admin/admin123)
- **Prometheus**: http://localhost:9090
- **Alertmanager**: http://localhost:9093

### 3. Import Dashboard
1. Open Grafana
2. Go to "+" → Import
3. Upload `grafana/dashboards/core-nexus-latency.json`
4. Or use community dashboard ID **13639** for FastAPI monitoring

## 📊 What's Monitored

### Core Metrics
- **Request Latency**: P50, P95, P99 percentiles
- **Request Rate**: Requests per second by endpoint
- **Error Rate**: HTTP error percentage
- **Memory Count**: Total memories stored
- **Memory Query Performance**: Vector search timing
- **Database Pool**: Connection utilization

### Advanced Metrics
- **ADM Scores**: Importance scoring distribution
- **Similarity Scores**: Query result quality
- **Provider Health**: Vector store status
- **Embedding Generation**: ML model performance

## 🚨 Alerts Configured

### Critical Alerts
- Service completely down (>2min)
- High error rate (>1% for 5min)
- Memory count drops significantly

### Warning Alerts
- High latency (P95 >200ms for 5min)
- Database pool exhaustion (>90%)
- Provider unhealthy
- Slow database queries (>1s)

### Info Alerts
- Cold start detected (service restart)

## 🔧 Configuration

### Production Setup
1. **Edit `prometheus.yml`**: Update target URLs for production
2. **Configure Alertmanager**: Add email/Slack webhooks in `alertmanager.yml`
3. **Set Retention**: Adjust data retention periods

### UptimeRobot Integration
1. Add webhook URL to UptimeRobot alerts
2. Configure webhook receiver in Alertmanager
3. Enable external monitoring metrics

## 📈 Performance Baselines

Based on development testing:
- **Target Query Time**: <500ms (achieved 27ms)
- **Target Storage Time**: <2000ms
- **Target Health Check**: <1000ms
- **Error Rate Threshold**: <1%

## 🏗️ Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   Service   │───▶│  Prometheus  │───▶│   Grafana   │
│  /metrics   │    │   (metrics)  │    │ (dashboards)│
└─────────────┘    └──────────────┘    └─────────────┘
                           │
                           ▼
                   ┌──────────────┐    ┌─────────────┐
                   │ Alertmanager │───▶│   Alerts    │
                   │   (rules)    │    │(email/slack)│
                   └──────────────┘    └─────────────┘

┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│    Logs     │───▶│     Loki     │───▶│   Grafana   │
│  (promtail) │    │ (aggregation)│    │  (queries)  │
└─────────────┘    └──────────────┘    └─────────────┘
```

## 🎯 Agent Team Usage

### For Agent 2 (Knowledge Graph)
Monitor these metrics:
- Memory storage latency (graph operations)
- Entity extraction performance
- Relationship mapping timing

### For Agent 3 (Business Intelligence)
Monitor these metrics:
- Document ingestion rate
- Query complexity impact
- Batch operation performance

### Shared Metrics
- Overall service health
- Database performance
- Vector search optimization

## 📋 Maintenance

### Daily Checks
- Review error rate trends
- Check database connection health
- Verify all providers online

### Weekly Reviews
- Analyze performance trends
- Review slow query reports
- Optimize alerting thresholds

### Monthly Tasks
- Archive old metrics data
- Update dashboard templates
- Review alert fatigue

## 🔍 Troubleshooting

### Common Issues

**503 Errors on Cold Start**
- Normal on Render.com free tier
- UptimeRobot + Cron job prevents this
- Monitor cold start frequency

**High Memory Query Latency**
- Check database pool utilization
- Review slow query logs
- Consider vector index optimization

**Database Connection Issues**
- Monitor pool exhaustion
- Check connection leaks
- Review query complexity

### Debug Commands

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Test alerting rules
curl http://localhost:9090/api/v1/rules

# Query specific metrics
curl "http://localhost:9090/api/v1/query?query=core_nexus_request_latency_seconds"

# View Grafana API
curl -u admin:admin123 http://localhost:3000/api/dashboards/home
```

## 📚 References

- [FastAPI Monitoring Guide](https://fastapi.tiangolo.com/advanced/monitoring/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/naming/)
- [Grafana Dashboard Design](https://grafana.com/docs/grafana/latest/best-practices/)
- [Alertmanager Configuration](https://prometheus.io/docs/alerting/latest/configuration/)