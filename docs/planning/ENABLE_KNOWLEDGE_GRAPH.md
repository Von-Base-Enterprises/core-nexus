# How to Enable Knowledge Graph

## Current Status
The knowledge graph code is FULLY IMPLEMENTED but DISABLED. All code exists, but the GraphProvider is not being instantiated.

## To Enable:

1. **Edit api.py** (around line 127-129):
   Replace:
   ```python
   # Add Graph Provider for knowledge graph functionality - TEMPORARILY DISABLED
   # TODO: Re-enable once deployment is stable
   logger.info("Graph provider temporarily disabled for stable deployment")
   ```
   
   With:
   ```python
   # Add Graph Provider for knowledge graph functionality
   if pgvector_config.enabled:
       try:
           # Use the same connection string as pgvector
           graph_config = ProviderConfig(
               provider_type="graph",
               enabled=True,
               primary=False,
               config={
                   'connection_string': pgvector_config.config.get('connection_string'),
                   'table_prefix': 'graph'
               }
           )
           graph_provider = GraphProvider(graph_config)
           await graph_provider.initialize()
           providers.append(graph_provider)
           logger.info("Graph provider initialized successfully")
       except Exception as e:
           logger.error(f"Graph provider failed to initialize: {e}")
   ```

2. **Install spaCy** (optional but recommended):
   ```bash
   pip install spacy
   python -m spacy download en_core_web_sm
   ```

3. **Run Database Migrations**:
   ```bash
   psql $DATABASE_URL < python/memory_service/init-db.sql
   ```

4. **Test the Endpoints**:
   ```bash
   # Sync a memory to graph
   curl -X POST https://your-service.com/graph/sync/{memory_id}
   
   # Explore entity relationships
   curl https://your-service.com/graph/explore/{entity_name}
   
   # Get graph stats
   curl https://your-service.com/graph/stats
   ```

## What You Get:
- Entity extraction from memories
- Relationship mapping
- Graph-based queries
- Knowledge insights
- Connected intelligence from isolated memories