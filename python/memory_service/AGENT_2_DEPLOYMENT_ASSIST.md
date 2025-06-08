# 🤝 Agent 2 Deployment Assistance for Agent 1
## Knowledge Graph Integration - Deployment Support

**From**: Agent 2 (Knowledge Graph Specialist)  
**To**: Agent 1 (Infrastructure Lead)  
**Re**: Graph-specific deployment requirements and assistance

---

## 📦 My Graph-Specific Requirements

### 1. **Python Dependencies I Added**
```bash
# Add these to requirements.txt if not already present:
spacy>=3.5.0
neo4j>=5.0.0
asyncpg>=0.27.0
sentence-transformers>=2.2.0

# Optional but recommended:
aiohttp>=3.8.0  # For async HTTP in utility scripts
```

### 2. **spaCy Model Download**
```dockerfile
# Add to Dockerfile after pip install:
RUN python -m spacy download en_core_web_sm
```

### 3. **Environment Variables for Graph**
```env
# Optional - GraphProvider works without these but better with:
GRAPH_ENABLED=true
SPACY_MODEL=en_core_web_sm
NEO4J_URI=neo4j://localhost:7687  # If using Neo4j
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
```

---

## 🗄️ Database Migration Support

### PostgreSQL Tables I Need
I've already added these to `init-db.sql` (lines 88-158), but here's a verification script:

```sql
-- Quick check if graph tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('graph_nodes', 'graph_relationships', 'memory_entity_map');
```

### If Tables Missing:
```bash
# Run just the graph portion
psql -U postgres -d core_nexus -f init-db.sql
```

---

## 🔧 Minimal Code Changes Needed

### In `src/memory_service/providers.py`:
The GraphProvider is already implemented (lines 780-1050). Just ensure it's imported in the API startup.

### In `src/memory_service/api.py` startup:
```python
# Around line 111, after other providers
if os.getenv("GRAPH_ENABLED", "true").lower() == "true":
    try:
        graph_config = ProviderConfig(
            name="graph",
            enabled=True,
            primary=False,  # Never primary - we enhance, not replace
            config={
                "spacy_model": os.getenv("SPACY_MODEL", "en_core_web_sm"),
                "enable_neo4j": os.getenv("NEO4J_URI") is not None
            }
        )
        graph_provider = GraphProvider(graph_config)
        providers.append(graph_provider)
        logger.info("Graph provider initialized")
    except Exception as e:
        logger.warning(f"Graph provider failed to initialize: {e}")
        # Non-critical - system works without graph
```

---

## 🚀 Deployment Verification

### Health Check for Graph:
```bash
# After deployment, verify graph endpoints:
curl https://core-nexus-memory-service.onrender.com/graph/stats

# Should return:
# {"health": "healthy", "statistics": {...}}
```

### Quick Test Script:
```python
# test_graph_deployment.py
import requests

base_url = "https://core-nexus-memory-service.onrender.com"

# Test graph stats endpoint
response = requests.get(f"{base_url}/graph/stats")
print(f"Graph Stats: {response.status_code}")

# Test health with graph provider
response = requests.get(f"{base_url}/health")
health_data = response.json()
print(f"Graph Provider in health check: {'graph' in health_data.get('providers', {})}")
```

---

## 📝 My Utility Scripts (Optional Deployment)

These are standalone tools that don't need to be deployed with the main service:

1. **keep_alive.py** - Can run separately to prevent cold starts
2. **race_to_1000.py** - Testing tool for load generation
3. **demo_queries.py** - Demo script for showcasing
4. **neo4j_streaming_pipeline.py** - Advanced integration (future)

---

## 🎯 What I Can Do to Help

### 1. **Testing Support**
I can create test scripts that verify the graph integration without touching core functionality:
```bash
python test_graph_integration.py --non-invasive
```

### 2. **Documentation**
I've already created:
- API endpoint documentation for graph routes
- Integration guide for GraphProvider
- Performance benchmarks

### 3. **Monitoring**
I can add graph-specific metrics to the `/metrics` endpoint:
```python
# Graph metrics to add
graph_metrics = {
    "graph_entities_total": len(entity_cache),
    "graph_relationships_total": relationship_count,
    "graph_extraction_time_ms": avg_extraction_time
}
```

### 4. **Debugging**
If deployment issues arise, I can help debug graph-specific problems:
- Entity extraction failures
- Relationship inference issues  
- Graph query performance

---

## ⚠️ What I WON'T Touch

Respecting Agent 1's ownership:
- ❌ Core deployment configuration
- ❌ Primary provider settings
- ❌ Database connection management
- ❌ Service authentication/security
- ❌ Load balancer or routing rules
- ❌ CI/CD pipeline changes

---

## 💡 Suggested Deployment Strategy

1. **Phase 1**: Deploy without GraphProvider
   - Ensure core service is stable
   - Verify vector providers working

2. **Phase 2**: Add GraphProvider
   - Enable with environment variable
   - Monitor for any performance impact
   - Graph is non-critical enhancement

3. **Phase 3**: Full Graph Integration
   - Enable entity extraction
   - Activate relationship inference
   - Monitor ADM scoring impact

---

## 🆘 How Agent 1 Can Call for Help

If you need graph-specific assistance:

```python
# In any error logs, look for:
"GraphProvider" or "entity_extraction" or "relationship_inference"

# Graph-specific errors I can help with:
- "spaCy model not found" → I'll provide fallback
- "Graph tables missing" → I'll verify schema
- "Entity extraction timeout" → I'll optimize regex
- "Relationship inference slow" → I'll tune algorithms
```

---

## 📊 Success Metrics

Once deployed, graph integration success looks like:
- ✅ `/graph/stats` returns 200 OK
- ✅ No increase in main API latency (< 10% overhead)
- ✅ Entity extraction working (check logs for "entities extracted")
- ✅ Health check shows graph provider as "healthy"

---

**Standing by to assist with any graph-specific deployment issues! The Knowledge Graph layer is designed to enhance, not complicate, the deployment. 🚀**

*- Agent 2*