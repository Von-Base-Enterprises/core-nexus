# 🚀 Deployment Steps for Graph Provider

## 1. Commit the Changes

First, add and commit the core changes:

```bash
# Add the essential files for GraphProvider
git add init-db.sql
git add requirements.txt
git add src/memory_service/api.py
git add src/memory_service/models.py
git add src/memory_service/providers.py

# Commit with clear message
git commit -m "feat: Add Knowledge Graph Provider integration

- Added GraphProvider with entity extraction and relationship inference
- Integrated with existing provider architecture
- Added graph tables to PostgreSQL schema
- Added spacy dependency for NLP
- Implemented lazy async pool initialization
- Added 7 new graph API endpoints"
```

## 2. Push to Repository

```bash
# Push to your branch
git push origin feat/day1-vertical-slice
```

## 3. Trigger Render Deployment

Since Render is connected to your GitHub repository, you can:

### Option A: Auto-deploy (if enabled)
- If auto-deploy is enabled for this branch, pushing will trigger deployment

### Option B: Manual trigger
1. Go to https://dashboard.render.com
2. Find your service: `core-nexus-memory-service`
3. Click "Manual Deploy" → "Deploy latest commit"

### Option C: Via Render CLI (if installed)
```bash
render deploy
```

## 4. Monitor Deployment

Watch the deployment logs in Render dashboard or use:

```bash
# If you have Render CLI
render logs --tail
```

## 5. Verify Service is Live

Once deployed, run this verification script:

```bash
# Save as verify_production.sh
#!/bin/bash

SERVICE_URL="https://core-nexus-memory-service.onrender.com"

echo "🔍 Verifying Core Nexus Production Deployment..."
echo "================================================"

# 1. Check health endpoint
echo -n "1. Health Check: "
HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $SERVICE_URL/health)
if [ $HEALTH_RESPONSE -eq 200 ]; then
    echo "✅ 200 OK"
    curl -s $SERVICE_URL/health | jq .
else
    echo "❌ Status: $HEALTH_RESPONSE"
fi

# 2. Check if GraphProvider is in providers list
echo -e "\n2. GraphProvider Status:"
PROVIDERS=$(curl -s $SERVICE_URL/providers | jq -r '.providers[].name' 2>/dev/null)
if echo "$PROVIDERS" | grep -q "graph"; then
    echo "✅ GraphProvider is active!"
else
    echo "⚠️  GraphProvider not found in providers list"
fi

# 3. Check graph stats endpoint
echo -e "\n3. Graph Stats Endpoint:"
GRAPH_STATS=$(curl -s -o /dev/null -w "%{http_code}" $SERVICE_URL/graph/stats)
if [ $GRAPH_STATS -eq 200 ]; then
    echo "✅ Graph endpoints available"
else
    echo "❌ Graph endpoints not responding: $GRAPH_STATS"
fi

# 4. Check metrics
echo -e "\n4. Service Metrics:"
curl -s $SERVICE_URL/metrics | grep "memory_service" | head -5

echo -e "\n✅ Deployment verification complete!"
```

## 6. Run Keep-Alive Service (Optional)

After deployment is confirmed:

```bash
python3 keep_alive.py
```

This will prevent cold starts and keep the service warm.