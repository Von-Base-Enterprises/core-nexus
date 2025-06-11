# GraphProvider Connection Fix

## Problem
The GraphProvider was failing to initialize in production with the error:
```
"GraphProvider requires either connection_pool or connection_string"
```

This occurred even though `GRAPH_ENABLED=true` was set in Render.

## Root Cause
The original implementation tried to share pgvector's connection pool:
```python
"connection_pool": pgvector_provider.connection_pool
```

However, pgvector initializes its pool asynchronously. When GraphProvider tried to access it during initialization, the pool was often still `None`, causing the initialization to fail.

## Solution
Pass a connection string instead of trying to share the pool:

```python
# Build connection string from pgvector config
pg_config = pgvector_config.config
connection_string = (
    f"postgresql://{pg_config['user']}:{pg_config['password']}@"
    f"{pg_config['host']}:{pg_config['port']}/{pg_config['database']}"
)

graph_config = ProviderConfig(
    name="graph",
    enabled=True,
    primary=False,
    config={
        "connection_string": connection_string,  # Pass string, not pool
        "table_prefix": "graph"
    }
)
```

## Benefits
1. **No timing dependencies**: GraphProvider can initialize independently
2. **Simpler code**: No need to check if pool exists or wait for it
3. **More reliable**: Connection string is always available immediately
4. **Same database**: Still uses the same PostgreSQL instance as pgvector

## Implementation Details
- GraphProvider creates its own pool with min_size=2, max_size=10
- Graph tables (graph_nodes, graph_relationships, etc.) already exist from init-db.sql
- No database changes required
- Backward compatible - GraphProvider already supports connection strings

## Testing
Run `test_graph_fix.py` to verify the configuration logic.

## Deployment
1. This change only affects `api.py` line 172
2. Commit and push to main branch
3. Render will auto-deploy
4. GraphProvider will initialize successfully
5. Knowledge Graph features will be active in production