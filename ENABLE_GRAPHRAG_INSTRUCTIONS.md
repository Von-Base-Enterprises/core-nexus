# Enabling GraphRAG in Core Nexus Production

## Quick Steps to Enable GraphRAG

### 1. Set Environment Variable in Render

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Navigate to the `core-nexus-memory-service` service
3. Click on "Environment" in the left sidebar
4. Add new environment variable:
   - **Key**: `GRAPH_ENABLED`
   - **Value**: `true`
5. Click "Save Changes"
6. The service will automatically redeploy

### 2. Verify Deployment (After ~5 minutes)

Once deployed, test that GraphRAG is working:

```bash
# Test graph statistics endpoint
curl -X GET "https://core-nexus-memory-service.onrender.com/graph/stats" \
  -H "X-API-Key: test-key-67890"

# Should return graph statistics instead of error
```

### 3. Test GraphRAG Endpoints

After enabling, these endpoints will be functional:

1. **Graph Statistics**
   ```bash
   GET /graph/stats
   ```

2. **Entity Exploration**
   ```bash
   GET /graph/explore/Von%20Base%20Enterprises
   ```

3. **Path Finding**
   ```bash
   GET /graph/path/Tyvon/Core%20Nexus
   ```

4. **Graph Queries**
   ```bash
   POST /graph/query
   {
     "query_type": "entities_by_type",
     "entity_type": "ORGANIZATION"
   }
   ```

## What This Enables

Once `GRAPH_ENABLED=true` is set:

1. **Multi-hop Reasoning**: Queries can traverse entity relationships
2. **Entity Disambiguation**: Understanding context through connections
3. **Evidence Chains**: See the path of relationships that led to answers
4. **Enhanced Search**: Combines vector similarity with graph structure

## Current Graph Status

As of testing:
- **155 entities** already extracted and stored
- **27 relationships** mapped between entities
- **Top entities**: Von Base Enterprises, Core Nexus, GPT-4, Pinecone
- **Entity types**: Organizations, Technologies, People, Projects, Concepts

## Troubleshooting

If graph endpoints still return errors after enabling:

1. Check deployment logs in Render
2. Verify the environment variable is set correctly
3. Look for initialization messages:
   - "Graph provider enabled via GRAPH_ENABLED environment variable"
   - "Graph provider initialized successfully - Knowledge graph is ACTIVE!"

## Architecture Note

The GraphProvider reuses the pgvector connection pool for efficiency and security. No additional database configuration is needed - all graph tables (`graph_nodes`, `graph_relationships`) are already created in the PostgreSQL database.