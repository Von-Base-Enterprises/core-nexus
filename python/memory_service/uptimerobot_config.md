# UptimeRobot Configuration for Core Nexus

## Setup Instructions

1. **Create Account**: Go to https://uptimerobot.com and create a free account

2. **Add Monitor**:
   - Monitor Type: `HTTP(S)`
   - Friendly Name: `Core Nexus Memory Service`
   - URL: `https://core-nexus-memory-service.onrender.com/health`
   - Monitoring Interval: `1 minute` (free tier)

3. **Keyword Monitoring**:
   - Enable "Keyword Exists"
   - Keyword: `"status":"healthy"`
   - Case Sensitive: No

4. **Alert Contacts**:
   - Add your email for notifications
   - Set alert threshold: `3 consecutive failures`

5. **Optional Webhooks**:
   - Webhook URL: `https://hooks.slack.com/your-webhook` (if using Slack)
   - Send notification when: `Up & Down`

## Expected Behavior

- ✅ **Normal**: Monitor shows "Up" with 99%+ uptime
- 🟡 **Cold Start**: Brief "Down" periods (30-60s) during idle recovery
- 🔴 **Issue**: Extended downtime (>5 minutes) indicates real problems

## Monitoring Dashboard

UptimeRobot provides:
- Response time graphs
- Uptime percentage
- Alert logs
- Public status page (optional)

## Integration with Grafana

UptimeRobot API can feed metrics to Grafana:
```python
# Example: Pull UptimeRobot metrics
import requests

def get_uptime_metrics():
    api_key = "your-api-key"
    url = f"https://api.uptimerobot.com/v2/getMonitors"
    
    response = requests.post(url, data={
        "api_key": api_key,
        "format": "json"
    })
    
    return response.json()
```

## Cost

- **Free Tier**: 50 monitors, 1-minute intervals
- **Pro Tier**: $7/month for 1-minute intervals on unlimited monitors
- **Enterprise**: Custom pricing for sub-minute monitoring

For Core Nexus, the free tier is sufficient for production monitoring.