# Knowledge Graph Safe Activation Plan

## Objective
Safely activate the dormant knowledge graph implementation while maintaining production stability.

## Current State (Per Agent 1's Analysis)
- ✅ 443 lines of GraphProvider fully implemented
- ✅ 7 API endpoints ready but returning 503
- ✅ All database schemas in place
- ❌ GraphProvider never instantiated in api.py
- ❌ No active data processing

## Activation Strategy

### Phase 1: Feature Flag Implementation (Immediate)
Add environment-based control for gradual rollout:

```python
# In api.py lifespan function (after line 126):
if os.getenv("GRAPH_ENABLED", "false").lower() == "true":
    # Build connection string from pgvector config
    graph_connection = (
        f"postgresql://{pgvector_config.config['user']}:"
        f"{pgvector_config.config['password']}@"
        f"{pgvector_config.config['host']}:"
        f"{pgvector_config.config['port']}/"
        f"{pgvector_config.config['database']}"
    )
    
    graph_config = ProviderConfig(
        name="graph",
        enabled=True,
        primary=False,
        config={
            "connection_string": graph_connection,
            "table_prefix": "graph"
        }
    )
    
    try:
        from .providers import GraphProvider
        graph_provider = GraphProvider(graph_config)
        providers.append(graph_provider)
        logger.info("Graph provider initialized successfully")
    except Exception as e:
        logger.error(f"Graph provider failed to initialize: {e}")
        # Continue without graph - non-breaking
```

### Phase 2: Database Preparation
1. Verify graph tables exist:
   ```sql
   SELECT table_name FROM information_schema.tables 
   WHERE table_name IN ('graph_nodes', 'graph_relationships', 'memory_entity_map');
   ```

2. Check indexes are created:
   ```sql
   SELECT indexname FROM pg_indexes 
   WHERE tablename LIKE 'graph_%';
   ```

### Phase 3: Gradual Activation

#### Step 1: Development Testing
```bash
# Local environment
export GRAPH_ENABLED=true
export LOG_LEVEL=DEBUG
python -m uvicorn memory_service.api:app --reload
```

#### Step 2: Test Endpoints
```bash
# Health check
curl http://localhost:8000/graph/stats

# Sync a test memory
curl -X POST http://localhost:8000/graph/sync/test-memory-id

# Explore entities
curl http://localhost:8000/graph/explore/TestEntity
```

#### Step 3: Production Canary (5%)
```yaml
# render.yaml or environment config
envVars:
  - key: GRAPH_ENABLED
    value: true  # Only on canary instance
  - key: GRAPH_CANARY_PERCENT
    value: "5"
```

#### Step 4: Monitor & Scale
- Monitor error rates
- Check performance metrics  
- Gradually increase to 25%, 50%, 100%

### Phase 4: Rollback Plan

If issues arise:
1. **Immediate**: Set `GRAPH_ENABLED=false`
2. **API Level**: GraphProvider skipped, endpoints return 503
3. **No Data Loss**: Graph tables remain intact
4. **Clean State**: Can re-enable anytime

### Phase 5: Success Metrics

Monitor these KPIs:
- API latency impact (should be <10ms)
- Entity extraction accuracy (>80%)
- Memory usage increase (<20%)
- Error rate (<0.1%)

## Implementation Checklist

- [ ] Add feature flag code to api.py
- [ ] Verify database tables exist
- [ ] Install spacy model: `python -m spacy download en_core_web_sm`
- [ ] Test locally with GRAPH_ENABLED=true
- [ ] Deploy with flag disabled
- [ ] Enable for canary testing
- [ ] Monitor metrics for 24 hours
- [ ] Gradual rollout to 100%

## Risk Assessment

**Low Risk Because:**
- Non-breaking: System works without graph
- Isolated: Graph operations are independent
- Reversible: One env var to disable
- Tested: Comprehensive test suite exists

**Mitigations:**
- Feature flag for instant disable
- Comprehensive error handling
- Lazy initialization prevents startup failures
- Separate connection pool from main data

## Timeline

- **Day 1**: Add feature flag, test locally
- **Day 2**: Deploy disabled, verify no impact
- **Day 3**: Enable canary (5%)
- **Day 4-5**: Monitor and increase to 25%
- **Day 6-7**: Scale to 100% if metrics good

## The Payoff

Once activated:
- Memories become interconnected
- Entity-based queries work
- Relationship insights available
- Knowledge evolution tracking
- True intelligence layer activated

**From Ferrari in garage → Ferrari on the track! 🏎️**