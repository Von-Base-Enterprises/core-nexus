# 📋 Knowledge Graph Integration - PR Plan

## 🎯 Overview
This PR introduces the Knowledge Graph Provider to Core Nexus, transforming isolated memories into connected intelligence by extracting entities and relationships from stored content.

## 📝 Commit Strategy

### Commit 1: Database Schema for Knowledge Graph
**Files:**
- `init-db.sql`

**Changes:**
- Added `graph_nodes` table for storing entities
- Added `graph_relationships` table for entity connections
- Added `memory_entity_map` for linking memories to entities
- Added indexes for performance optimization
- Added helper functions for graph operations

**Commit Message:**
```
feat(db): Add PostgreSQL schema for knowledge graph

- Create graph_nodes table for entity storage with embeddings
- Create graph_relationships table with ADM scoring
- Create memory_entity_map for memory-entity correlation
- Add performance indexes for graph queries
- Add helper functions for common graph operations
```

### Commit 2: Data Models for Knowledge Graph
**Files:**
- `src/memory_service/models.py`

**Changes:**
- Added EntityType and RelationshipType enums
- Added GraphNode, GraphRelationship models
- Added EntityExtraction, GraphQuery, GraphResponse models
- Added EntityInsights for analytics

**Commit Message:**
```
feat(models): Add data models for knowledge graph functionality

- Define entity and relationship type enums
- Add GraphNode model with importance scoring
- Add GraphRelationship model with ADM integration
- Add query/response models for graph API
- Add EntityInsights model for graph analytics
```

### Commit 3: GraphProvider Implementation
**Files:**
- `src/memory_service/providers.py`

**Changes:**
- Implemented GraphProvider class following provider pattern
- Added entity extraction with spaCy/regex fallback
- Added relationship inference based on context
- Added lazy async pool initialization
- Implemented all required provider methods

**Commit Message:**
```
feat(providers): Implement GraphProvider for knowledge graph

- Add GraphProvider following existing provider patterns
- Implement entity extraction with spaCy and regex fallback
- Add relationship inference based on co-occurrence
- Use lazy initialization for async connection pool
- Integrate with ADM scoring for relationship strength
```

### Commit 4: API Integration (Currently Disabled)
**Files:**
- `src/memory_service/api.py`

**Changes:**
- Added GraphProvider initialization code (temporarily disabled)
- Added 7 graph-specific API endpoints
- Integrated with existing FastAPI patterns

**Commit Message:**
```
feat(api): Add knowledge graph API endpoints (disabled)

- Add GraphProvider to startup sequence (disabled for stability)
- Add /graph/sync endpoint for memory synchronization
- Add /graph/explore for entity relationship traversal
- Add /graph/insights for memory graph analytics
- Add /graph/stats for graph health monitoring
- Note: Endpoints ready but provider disabled pending stable deployment
```

### Commit 5: Dependencies and Documentation
**Files:**
- `requirements.txt`
- Various documentation files (optional, can be .gitignored)

**Changes:**
- Added spacy>=3.5.0 for entity extraction
- Added notes about spacy model download

**Commit Message:**
```
feat(deps): Add spaCy dependency for entity extraction

- Add spacy>=3.5.0 to requirements.txt
- Add comment about downloading en_core_web_sm model
- asyncpg already present for PostgreSQL connection
```

## 🔄 PR Structure

### Title
```
feat: Add Knowledge Graph Provider for connected intelligence
```

### Description
```markdown
## Summary
This PR introduces the Knowledge Graph Provider to Core Nexus, enabling automatic extraction of entities and relationships from memories to create a connected intelligence layer.

## What's New
- **Entity Extraction**: Automatically extracts people, organizations, technologies, and concepts from memory content
- **Relationship Inference**: Discovers connections between entities based on context and co-occurrence
- **ADM Integration**: Uses Darwin-Gödel scoring for relationship strength
- **PostgreSQL Storage**: Leverages existing PostgreSQL infrastructure with new graph tables
- **7 New API Endpoints**: Complete graph query and exploration capabilities

## Implementation Details
- Follows existing provider architecture pattern
- Non-breaking: system works without graph provider
- Graceful degradation: falls back to regex if spaCy unavailable
- Lazy initialization: prevents async conflicts during startup
- Same UUID namespace: perfect correlation with vector memories

## Current Status
- ✅ Database schema complete
- ✅ Models defined
- ✅ GraphProvider implemented
- ✅ API endpoints ready
- ⚠️ Provider initialization disabled in API startup (line 117-118)

The GraphProvider is fully implemented but temporarily disabled in the API startup to ensure stable deployment. Once the core service is stable, simply set `GRAPH_ENABLED=true` to activate.

## Testing
- Local testing scripts included but not committed
- Comprehensive verification performed
- No blocking issues found

## Next Steps
1. Deploy with GraphProvider disabled
2. Verify core service stability
3. Enable GraphProvider with environment variable
4. Run entity extraction on existing memories

## Related Issues
- Addresses need for relationship understanding in memories
- Enables future features like semantic search and knowledge discovery
```

## 📁 Files to Include/Exclude

### Include in Commits:
```
✅ init-db.sql
✅ src/memory_service/models.py
✅ src/memory_service/providers.py
✅ src/memory_service/api.py (with disabled GraphProvider)
✅ requirements.txt
```

### Exclude (add to .gitignore):
```
❌ All test scripts (test_*.py)
❌ All documentation files (*.md)
❌ All utility scripts (keep_alive.py, race_to_1000.py, etc.)
❌ All status/log files (*.log, *.json)
❌ deployment_steps.md and verification scripts
```

## 🚀 Execution Steps

1. **Check current branch**:
   ```bash
   git branch --show-current
   # Should be: feat/day1-vertical-slice
   ```

2. **Create new branch for PR**:
   ```bash
   git checkout -b feat/knowledge-graph-integration
   ```

3. **Stage and commit files**:
   ```bash
   # Commit 1: Database
   git add init-db.sql
   git commit -m "feat(db): Add PostgreSQL schema for knowledge graph"

   # Commit 2: Models
   git add src/memory_service/models.py
   git commit -m "feat(models): Add data models for knowledge graph functionality"

   # Commit 3: Provider
   git add src/memory_service/providers.py
   git commit -m "feat(providers): Implement GraphProvider for knowledge graph"

   # Commit 4: API (disabled)
   git add src/memory_service/api.py
   git commit -m "feat(api): Add knowledge graph API endpoints (disabled)"

   # Commit 5: Dependencies
   git add requirements.txt
   git commit -m "feat(deps): Add spaCy dependency for entity extraction"
   ```

4. **Push branch**:
   ```bash
   git push origin feat/knowledge-graph-integration
   ```

5. **Create PR on GitHub**:
   - Base: `main` or `develop` (check repo structure)
   - Compare: `feat/knowledge-graph-integration`
   - Use the PR description template above

## ⚠️ Important Notes

1. **GraphProvider is disabled**: Line 117-118 in api.py shows it's disabled for stability
2. **No breaking changes**: Existing functionality unchanged
3. **Clean commit history**: 5 logical commits showing progression
4. **Documentation**: Extensive but not committed (can share separately)

## ✅ Ready to Execute?

This plan:
- Focuses solely on knowledge graph integration
- Maintains clean separation of concerns
- Follows conventional commit standards
- Provides clear PR documentation
- Ensures non-breaking deployment

Would you like me to proceed with these commits, or would you like to adjust the plan?