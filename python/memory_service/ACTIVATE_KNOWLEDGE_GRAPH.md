# 🚀 How to Activate the Knowledge Graph

## Quick Start (TL;DR)

```bash
# 1. Set the feature flag
export GRAPH_ENABLED=true

# 2. Install dependencies (if needed)
pip install spacy
python -m spacy download en_core_web_sm

# 3. Start the service
python -m uvicorn memory_service.api:app --reload

# 4. Verify activation
curl http://localhost:8000/graph/stats
```

## What You're Activating

The Knowledge Graph transforms Core Nexus from a memory storage system into an **intelligence system** by:
- Extracting entities (people, organizations, technologies) from memories
- Inferring relationships between entities
- Building a connected graph of knowledge
- Enabling relationship-based queries

## Detailed Activation Steps

### 1. Environment Setup

Set the feature flag to enable the graph:

```bash
# For local development
export GRAPH_ENABLED=true

# For production (Render.com)
# Add to Environment Variables in dashboard:
# GRAPH_ENABLED = true
```

### 2. Verify Prerequisites

The graph provider requires:
- PostgreSQL with pgvector (already configured)
- spaCy for entity extraction (optional, has fallback)

```bash
# Check if spaCy is installed
python -c "import spacy; print('spaCy installed')"

# Install if needed
pip install spacy
python -m spacy download en_core_web_sm
```

### 3. Start the Service

```bash
# From the memory_service directory
python -m uvicorn memory_service.api:app --reload --log-level info
```

Look for this in the logs:
```
✅ Graph provider initialized successfully - Knowledge graph is ACTIVE!
```

### 4. Verify Activation

Run the test script:
```bash
python test_graph_activation.py
```

Or manually check endpoints:

```bash
# Check graph stats
curl http://localhost:8000/graph/stats

# Check health (should show 'graph' in providers)
curl http://localhost:8000/health | jq .providers
```

## API Endpoints Now Available

Once activated, these endpoints become functional:

1. **Sync Memory to Graph**
   ```bash
   curl -X POST http://localhost:8000/graph/sync/{memory_id}
   ```

2. **Explore Entity Relationships**
   ```bash
   curl http://localhost:8000/graph/explore/OpenAI
   ```

3. **Get Graph Statistics**
   ```bash
   curl http://localhost:8000/graph/stats
   ```

4. **Query Graph**
   ```bash
   curl -X POST http://localhost:8000/graph/query \
     -H "Content-Type: application/json" \
     -d '{"entity_name": "OpenAI", "limit": 10}'
   ```

## Production Deployment

### Render.com

1. Go to your service dashboard
2. Navigate to "Environment"
3. Add: `GRAPH_ENABLED = true`
4. Deploy the changes
5. Monitor logs for activation message

### Docker

```dockerfile
ENV GRAPH_ENABLED=true
```

### Kubernetes

```yaml
env:
  - name: GRAPH_ENABLED
    value: "true"
```

## Rollback (If Needed)

To disable the graph instantly:

```bash
# Set to false or remove the variable
export GRAPH_ENABLED=false

# Or in production, update the environment variable
```

The service will continue running normally without graph functionality.

## What Happens When Activated

1. **On Startup**: GraphProvider initializes with the same PostgreSQL connection
2. **On Memory Storage**: Entities are extracted and relationships inferred
3. **On Queries**: Graph-based search becomes available
4. **Performance**: Minimal impact (<10ms per operation)

## Monitoring

Watch these metrics:
- API latency (should remain stable)
- Memory usage (slight increase expected)
- Entity extraction rate
- Error logs for any issues

## Common Issues

### "Graph provider not available" (503 error)
- Check `GRAPH_ENABLED=true` is set
- Verify PostgreSQL is accessible
- Check logs for initialization errors

### "spaCy model not found"
- Run: `python -m spacy download en_core_web_sm`
- The system will fall back to regex if spaCy fails

### High latency on first request
- Normal - spaCy model loads on first use
- Subsequent requests will be fast

## Success Indicators

You'll know it's working when:
- ✅ `/graph/stats` returns data instead of 503
- ✅ Logs show "Graph provider initialized successfully"
- ✅ Health check includes 'graph' in providers list
- ✅ Entity extraction happens automatically on new memories

## The Result

With the Knowledge Graph active, Core Nexus transforms from:
- 🗄️ Memory storage → 🧠 Intelligence system
- 📄 Isolated data → 🕸️ Connected knowledge
- 🔍 Keyword search → 🎯 Relationship understanding

**You've just activated the Ferrari! 🏎️💨**