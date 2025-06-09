# Core Nexus Production Action Plan

**Status**: IMMEDIATE ACTION REQUIRED  
**Priority**: Fix query functionality and security vulnerabilities

## 🚨 Critical Issues (Fix Today)

### 1. Query Returns Empty Results
**Impact**: Core functionality broken - users can't retrieve memories  
**Root Cause**: Missing pgvector indexes  
**Fix**:
```bash
# 1. Get PSQL connection from Render dashboard
# 2. Connect to database
psql postgresql://user:pass@host:5432/nexus_memory_db

# 3. Run the fix script
\i python/memory_service/fix_pgvector_queries.sql

# 4. Test queries work
```

### 2. Security Vulnerabilities (5 total: 3 high, 2 moderate)
**Action**: Visit https://github.com/Von-Base-Enterprises/core-nexus/security/dependabot
**Fix**:
```bash
cd /home/vonbase/dev/core-nexus
poetry update
# Review changes
git add pyproject.toml poetry.lock
git commit -m "fix: Update dependencies to patch security vulnerabilities"
git push origin main
```

## 📊 Current Production State

- **Service**: https://core-nexus-memory-service.onrender.com
- **Health**: ✅ Operational
- **Memories**: 711 stored
- **Query Performance**: 313ms (target: <100ms)
- **Knowledge Graph**: Ready but disabled (needs GRAPH_ENABLED=true)

## 🎯 Today's Priority Tasks

1. **Fix Queries** (30 min)
   - Run pgvector fix script
   - Verify queries return results
   - Monitor performance improvement

2. **Patch Security** (45 min)
   - Update vulnerable dependencies
   - Test locally
   - Deploy to production

3. **Enable Monitoring** (15 min)
   - Add Papertrail environment variables
   - Configure alerts for errors
   - Test log streaming

4. **Activate Knowledge Graph** (30 min)
   - Set GRAPH_ENABLED=true in Render
   - Run graph schema migrations
   - Test entity extraction

## 🔧 Render Environment Variables to Add

```bash
# Monitoring
PAPERTRAIL_HOST=logs.papertrailapp.com
PAPERTRAIL_PORT=YOUR_PORT_HERE
LOG_LEVEL=INFO

# Knowledge Graph
GRAPH_ENABLED=true

# Performance (if not set)
PYTHONUNBUFFERED=1
WEB_CONCURRENCY=4
```

## 📈 Expected Improvements

After implementing these fixes:
- Queries will return results correctly
- Query performance will improve to <100ms
- Security vulnerabilities will be patched
- Real-time monitoring will be active
- Knowledge graph will extract entities

## 🧪 Verification Commands

```bash
# Test health
curl https://core-nexus-memory-service.onrender.com/health | jq

# Test memory storage
curl -X POST https://core-nexus-memory-service.onrender.com/memories \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Production test memory after optimizations",
    "metadata": {"test": true, "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"} 
  }' | jq

# Test query (should return results)
curl -X POST https://core-nexus-memory-service.onrender.com/memories/query \
  -H "Content-Type: application/json" \
  -d '{"query": "production test", "limit": 5}' | jq

# Test graph status (after enabling)
curl https://core-nexus-memory-service.onrender.com/graph/stats | jq
```

## 📋 Monitoring Dashboard

Once complete, monitor these metrics:
- Query success rate (should be 100%)
- Average query time (target: <100ms)
- Error rate (should be <1%)
- Memory growth rate
- Graph entity extraction rate

---
**Remember**: Fix queries first - it's the most critical issue affecting users!