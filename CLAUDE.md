# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### All-in-One Commands (via Makefile)
```bash
make install          # Install all dependencies (TypeScript + Python)
make dev              # Start all development servers
make test             # Run all tests
make lint             # Run all linters
make format           # Auto-format all code
make type-check       # Run type checking
make ci               # Full CI pipeline (test + lint + type-check)
make build            # Build all packages
```

### Python-Specific Commands
```bash
cd python/memory_service
poetry run uvicorn src.memory_service.api:app --reload  # Start FastAPI server
poetry run pytest                                        # Run tests
poetry run pytest -xvs tests/test_specific.py          # Run single test file
poetry run ruff check .                                 # Lint
poetry run black .                                      # Format
poetry run mypy .                                       # Type check
```

### TypeScript-Specific Commands
```bash
yarn test             # Run all TypeScript tests
yarn test:watch       # Run tests in watch mode
yarn lint             # Lint TypeScript code
yarn lint:fix         # Fix linting issues
yarn type-check       # TypeScript type checking
yarn build            # Build all packages
```

### Running Single Tests
- Python: `poetry run pytest -xvs tests/test_file.py::test_function`
- TypeScript: `yarn test path/to/test.spec.ts`

## High-Level Architecture

### Core Components

1. **Memory Service** (`python/memory_service/`): Production-ready REST API for memory storage
   - Multi-provider vector storage (pgvector, ChromaDB, Pinecone)
   - Semantic search using OpenAI embeddings
   - Knowledge graph capabilities (feature-flagged with GRAPH_ENABLED)
   - High availability with provider failover

2. **Unified Store Pattern**: The memory service uses a multi-provider abstraction
   - `providers.py`: Individual vector store implementations
   - `unified_store.py`: Aggregates providers with fallback support
   - `models.py`: Pydantic v2 models for validation
   - `api.py`: FastAPI endpoints

3. **Deployment Architecture**:
   - Primary deployment on Render.com
   - PostgreSQL with pgvector extension for production
   - Keep-alive worker to prevent cold starts
   - Monitoring stack with Prometheus/Grafana

### Key Design Decisions

1. **Provider Abstraction**: All vector stores implement a common interface, allowing seamless switching and fallback between providers.

2. **Embedding Strategy**: Uses OpenAI's text-embedding-3-small model with 1536 dimensions. Embeddings are cached and reused where possible.

3. **Query Processing**: Empty queries are allowed and return all memories. Search queries use cosine similarity with configurable thresholds.

4. **Error Handling**: Multi-level fallback - if primary provider fails, automatically tries secondary providers before returning error.

## Environment Variables

Required for production:
```bash
OPENAI_API_KEY        # OpenAI API key for embeddings
PGVECTOR_PASSWORD     # PostgreSQL password (no default)
GEMINI_API_KEY        # Gemini API key for embeddings
RENDER_API_KEY        # Render API key
PINECONE_API_KEY      # Pinecone API key
```

Optional configuration:
```bash
GRAPH_ENABLED=true   # Enable knowledge graph features
LOG_LEVEL=INFO        # Logging verbosity
PGVECTOR_HOST=dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com
PGVECTOR_PORT=5432
PGVECTOR_DATABASE=nexus_memory_db
PGVECTOR_USER=nexus_memory_db_user
PINECONE_ENVIRONMENT=us-east-1-aws
PINECONE_INDEX_NAME=nexus-memories
CHROMADB_HOST=localhost
CHROMADB_PORT=8000
ADM_EVOLUTION_ENABLED=true
ADM_SCORING_ENABLED=true
CACHE_TTL=3600
LOG_LEVEL=INFO
MAX_RETRIES=3
REQUEST_TIMEOUT=10
```

## Critical Files to Understand

1. `python/memory_service/src/memory_service/unified_store.py`: Core memory storage logic
2. `python/memory_service/src/memory_service/api.py`: REST API endpoints
3. `python/memory_service/src/memory_service/providers.py`: Vector store implementations
4. `render.yaml`: Production deployment configuration
5. `Makefile`: Unified command interface

## Testing Approach

- Unit tests use pytest with async support
- Integration tests require PostgreSQL with pgvector
- Mock providers available for testing without external dependencies
- Always run `make test` before committing changes

## Production Considerations

1. The service is deployed on Render with automatic scaling
2. Database migrations are handled via `init-db.sql`
3. Health checks at `/health` endpoint
4. Metrics exposed at `/metrics` for Prometheus
5. Recent fixes addressed empty query handling and bulk import/export functionality