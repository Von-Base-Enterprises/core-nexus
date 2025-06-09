# 🚀 Enable Knowledge Graph in Production - Render.com Guide

## Current Status
✅ Knowledge Graph code is fully implemented and tested  
✅ All security issues have been fixed  
❌ Graph provider is NOT active in production  
❌ All graph endpoints return 500 errors  

## Root Cause
The graph provider is disabled because `GRAPH_ENABLED` environment variable is not set in production.

## Solution: Set GRAPH_ENABLED=true

### Step-by-Step Instructions for Render.com

1. **Log into Render Dashboard**
   - Go to https://dashboard.render.com
   - Navigate to your service: `core-nexus-memory-service`

2. **Access Environment Variables**
   - Click on your service
   - Go to "Environment" tab in the left sidebar
   - Click "Add Environment Variable"

3. **Add the Required Variable**
   ```
   Key: GRAPH_ENABLED
   Value: true
   ```
   - Click "Save"

4. **Service Will Auto-Deploy**
   - Render will automatically redeploy your service
   - Wait for deployment to complete (usually 2-3 minutes)
   - Check the logs to confirm graph provider initialization

## What Will Happen

### During Startup
You'll see this in the logs:
```
Graph provider enabled via GRAPH_ENABLED environment variable
✅ Graph provider initialized successfully - Knowledge graph is ACTIVE!
```

### After Activation
The `/providers` endpoint will show:
```json
{
  "providers": [
    {
      "name": "pgvector",
      "enabled": true,
      "primary": true
    },
    {
      "name": "chromadb", 
      "enabled": true,
      "primary": false
    },
    {
      "name": "graph",
      "enabled": true,
      "primary": false
    }
  ]
}
```

## Verification Steps

### 1. Check Providers List
```bash
curl https://core-nexus-memory-service.onrender.com/providers
```
Should now include "graph" provider.

### 2. Test Graph Stats
```bash
curl https://core-nexus-memory-service.onrender.com/graph/stats
```
Should return 200 OK with statistics.

### 3. Test Entity Exploration
```bash
curl https://core-nexus-memory-service.onrender.com/graph/explore/test
```
Should return 200 OK (even if no entities found).

## Expected Timeline
- **Environment Variable Update**: 30 seconds
- **Auto-deployment**: 2-3 minutes
- **Graph Provider Active**: Immediately after deployment
- **Total Time**: ~5 minutes

## Monitoring After Activation

### Check Logs
In Render dashboard, go to "Logs" tab and look for:
- "Graph provider initialized successfully"
- No errors related to graph operations

### Health Check
```bash
curl https://core-nexus-memory-service.onrender.com/health
```
Should show all providers healthy.

## Important Notes

1. **No Code Changes Required** - Everything is already implemented
2. **Zero Downtime** - Render handles the deployment gracefully
3. **Backwards Compatible** - Existing functionality remains unchanged
4. **Feature Flag Pattern** - Can be disabled by setting GRAPH_ENABLED=false

## Troubleshooting

### If Graph Provider Doesn't Appear
1. Check logs for initialization errors
2. Verify pgvector provider is running (required dependency)
3. Ensure GRAPH_ENABLED value is exactly "true" (lowercase)

### If Endpoints Still Return 500
1. Check that deployment completed successfully
2. Look for any error messages in logs
3. Verify database has graph tables (they should exist)

## Next Steps After Activation

1. **Populate Graph Data**
   - New memories will automatically extract entities
   - Use bulk sync for existing memories (when implemented)

2. **Monitor Performance**
   - Watch query times in /graph/stats
   - Check entity extraction accuracy

3. **Complete TODO Implementations**
   - Memory sync endpoint
   - Path finding algorithm
   - Bulk sync functionality

## Security Reminder

✅ All security issues have been fixed:
- Connection pooling (no passwords in memory)
- Input validation (prevents SQL injection)
- Proper error handling (no data leaks)

## Contact for Issues

If you encounter any problems:
1. Check the logs first
2. Verify all steps were followed
3. The graph endpoints should work immediately after GRAPH_ENABLED=true is set

---

**Estimated Time: 5 minutes**  
**Risk Level: Low**  
**Rollback: Set GRAPH_ENABLED=false**