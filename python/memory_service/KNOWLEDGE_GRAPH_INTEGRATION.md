# Knowledge Graph Integration - Core Nexus Memory Service

## Overview
The Knowledge Graph Provider extends Core Nexus with entity extraction and relationship inference capabilities, transforming isolated memories into connected intelligence.

## Current Status
- **DISABLED BY DEFAULT**: GraphProvider initialization is commented out (api.py:127-129)
- **Production Safe**: System operates normally without graph provider
- **Ready for Activation**: Can be enabled via configuration when needed

## Components
1. **GraphProvider** (providers.py:543-987) - Entity extraction and relationship inference
2. **Data Models** (models.py:118-219) - Graph data structures
3. **Database Schema** (init-db.sql:219-354) - PostgreSQL graph tables
4. **API Endpoints** (api.py:1217-1448) - RESTful graph operations

## Key Features
- Entity extraction with spaCy/regex fallback
- Relationship inference based on co-occurrence
- ADM scoring for relationship strength
- Same UUID namespace for perfect memory correlation
- Lazy initialization to prevent startup conflicts

## Activation
To enable the Knowledge Graph:
1. Install spaCy: \
2. Download model: \
3. Uncomment GraphProvider initialization in api.py (lines 127-129)
4. Set environment variable: \

The implementation is production-ready but disabled by default for stability.
