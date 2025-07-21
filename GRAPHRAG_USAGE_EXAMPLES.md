# GraphRAG Usage Examples

## Overview

Core Nexus GraphRAG combines vector similarity search with knowledge graph relationships to provide advanced multi-hop reasoning and entity-aware memory retrieval.

## API Endpoints

### 1. Graph Statistics
```bash
GET /graph/stats

curl -X GET "https://core-nexus-memory-service.onrender.com/graph/stats" \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
{
  "statistics": {
    "total_nodes": 157,
    "total_relationships": 27,
    "entity_types": 6,
    "relationship_types": 13
  }
}
```

### 2. Entity Exploration
```bash
GET /graph/explore/{entity_name}

curl -X GET "https://core-nexus-memory-service.onrender.com/graph/explore/Von%20Base%20Enterprises" \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
{
  "entity": "Von Base Enterprises",
  "max_depth": 2,
  "memories_found": 5,
  "memories": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "content": "Von Base Enterprises announced the Core Nexus project...",
      "importance": 0.9,
      "similarity": 0.85
    }
  ]
}
```

### 3. Graph Queries
```bash
POST /graph/query

# Query by entity type (case-insensitive)
curl -X POST "https://core-nexus-memory-service.onrender.com/graph/query" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query_type": "entities_by_type",
    "entity_type": "ORGANIZATION",
    "limit": 10
  }'

# Query by entity name
curl -X POST "https://core-nexus-memory-service.onrender.com/graph/query" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_name": "Claude",
    "entity_type": "technology"
  }'
```

**Response:**
```json
{
  "nodes": [
    {
      "id": "3334c82b-02c9-43e1-a506-6df0c724b900",
      "entity_name": "Von Base Enterprises",
      "entity_type": "ORGANIZATION",
      "importance_score": 0.9,
      "mention_count": 9,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "relationships": [
    {
      "id": "rel-123",
      "from_node": {
        "id": "node-1",
        "name": "Von Base Enterprises",
        "type": "ORGANIZATION"
      },
      "to_node": {
        "id": "node-2",
        "name": "Core Nexus",
        "type": "PROJECT"
      },
      "type": "develops",
      "strength": 0.95,
      "confidence": 0.9,
      "occurrence_count": 5
    }
  ],
  "query_time_ms": 25.3,
  "total_nodes": 1,
  "total_relationships": 3
}
```

### 4. Path Finding (Coming Soon)
```bash
GET /graph/path/{from_entity}/{to_entity}

curl -X GET "https://core-nexus-memory-service.onrender.com/graph/path/Tyvon/Core%20Nexus" \
  -H "X-API-Key: your-api-key"
```

### 5. Live Knowledge Graph Stats
```bash
GET /api/knowledge-graph/live-stats

curl -X GET "https://core-nexus-memory-service.onrender.com/api/knowledge-graph/live-stats" \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
{
  "entity_count": 157,
  "relationship_count": 27,
  "top_entities": [
    {
      "name": "Von Base Enterprises",
      "type": "ORGANIZATION",
      "importance": 0.9,
      "connections": 12
    }
  ],
  "entity_types": {
    "other": 84,
    "TECHNOLOGY": 49,
    "PERSON": 14,
    "ORGANIZATION": 5,
    "PROJECT": 4,
    "CONCEPT": 1
  },
  "status": "live"
}
```

## Use Cases

### 1. Find All Memories About an Organization
```python
# Find all memories related to Von Base Enterprises
response = await session.get(
    f"{API_URL}/graph/explore/Von Base Enterprises",
    headers=headers
)
```

### 2. Discover Technology Stack
```python
# Find all technology entities
query = {
    "query_type": "entities_by_type",
    "entity_type": "technology",
    "limit": 20
}
response = await session.post(
    f"{API_URL}/graph/query",
    headers=headers,
    json=query
)
```

### 3. Trace Relationships
```python
# Find how entities are connected
query = {
    "entity_name": "Claude",
    "include_relationships": True
}
response = await session.post(
    f"{API_URL}/graph/query",
    headers=headers,
    json=query
)
```

### 4. Context-Aware Memory Retrieval
When storing memories, the system automatically:
- Extracts entities (people, organizations, technologies, etc.)
- Creates relationships between entities
- Links memories to relevant entities
- Enables graph-enhanced retrieval

## Entity Types

The system recognizes these entity types:
- **PERSON**: Individual people
- **ORGANIZATION**: Companies, institutions
- **TECHNOLOGY**: Software, frameworks, tools
- **PROJECT**: Specific projects or initiatives
- **CONCEPT**: Abstract concepts or ideas
- **LOCATION**: Places, addresses
- **EVENT**: Meetings, launches, milestones
- **PRODUCT**: Specific products or services

## Relationship Types

Common relationships detected:
- **works_at**: Person → Organization
- **develops**: Organization → Technology/Project
- **uses**: Entity → Technology
- **leads**: Person → Project/Team
- **affiliated_with**: Person → Organization
- **located_at**: Entity → Location
- **relates_to**: Generic relationship

## Best Practices

1. **Entity Names**: Use exact entity names for best results
2. **Case Sensitivity**: Entity types are case-insensitive
3. **Memory Quality**: Higher importance scores improve entity extraction
4. **Relationship Strength**: Closer entities in text create stronger relationships

## Advanced Features (Coming Soon)

1. **Multi-hop Queries**: Find paths between entities
2. **Subgraph Extraction**: Get entire knowledge subgraphs
3. **Temporal Queries**: Track entity evolution over time
4. **Relationship Inference**: Discover implicit connections
5. **Graph Embeddings**: Similarity search in graph space