# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### All-in-One Commands (via Makefile)
```bash
make install          # Install all dependencies (Yarn + Poetry)
make dev              # Start all development servers  
make test             # Run all tests (primarily Python via Poetry)
make lint             # Run all linters (ESLint + Python)
make format           # Auto-format all code
make type-check       # Run type checking
make ci               # Full CI pipeline (test + lint + type-check)
make build            # Build all packages
```

### Direct Package Manager Commands
```bash
# Yarn v4 commands (for linting and formatting)
yarn install          # Install Node.js dependencies for linting/formatting
yarn lint              # Run ESLint on JavaScript/TypeScript files
yarn format            # Format code with Prettier
yarn ci                # Run yarn CI pipeline

# Poetry commands (for Python services)
cd python/memory_service
poetry install         # Install Python dependencies
poetry run pytest     # Run Python tests
poetry run ruff check  # Python linting
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

### Code Quality Commands
```bash
yarn lint             # Lint JavaScript/TypeScript files (primarily for config files)
yarn lint:fix         # Fix linting issues automatically
yarn format           # Format code with Prettier
yarn format:check     # Check code formatting without changes
```

### Running Single Tests
- Python: `poetry run pytest -xvs tests/test_file.py::test_function`
- JARVIS: `cd jarvis && python test_jarvis.py`

### Database Backup Commands
```bash
# Set environment variable for secure access
export PGVECTOR_PASSWORD="your_password_here"

# Test database connection
poetry run python ../../secure_backup_system.py health

# Create a full backup
poetry run python ../../secure_backup_system.py full_backup

# Create a named backup
poetry run python ../../secure_backup_system.py full_backup "backup_name"

# List all backups with integrity status
poetry run python ../../secure_backup_system.py list

# Verify backup integrity
poetry run python ../../secure_backup_system.py verify "backup_name"

# Run automated scheduler (daily backups + retention)
poetry run python ../../backup_scheduler.py start
```

## Git Worktree Management

The Core Nexus project uses Git worktrees for AI agent coordination and parallel development. This enables multiple AI agents to work simultaneously without conflicts.

### Worktree Setup and Management
```bash
# Initialize the complete worktree system
./scripts/worktree-setup.sh

# Check status of all worktrees
./scripts/sync-environments.sh --status

# Sync all worktrees
./scripts/sync-environments.sh --all

# Sync specific worktree
./scripts/sync-environments.sh memory-service

# Check for conflicts between worktrees
./scripts/sync-environments.sh --conflicts

# Check integration readiness
./scripts/sync-environments.sh --readiness

# Update status tracking
./scripts/sync-environments.sh --update-status
```

### Worktree Structure
The system creates dedicated worktrees for different purposes:

**Core Environment Worktrees:**
- `core-nexus-production` - Production validation (main branch)
- `core-nexus-staging` - Integration testing (staging branch) 
- `core-nexus-development` - Feature integration (develop branch)
- `core-nexus-hotfix` - Emergency fixes (main branch)
- `core-nexus-rollback` - Stable reference (latest tag)

**Component-Specific Worktrees:**
- `core-nexus-memory-service` - Memory Service development
- `core-nexus-jarvis` - JARVIS AI agent development
- `core-nexus-performance` - Performance optimization work
- `core-nexus-observability` - Monitoring and observability
- `core-nexus-testing` - Advanced testing suites

### AI Agent Coordination
```bash
# Before starting work (MANDATORY)
./scripts/sync-environments.sh --status
./scripts/sync-environments.sh [your-worktree-name]
./scripts/sync-environments.sh --conflicts

# During work (every 30 minutes)
echo "$(date): [AGENT_NAME] Progress: [ACCOMPLISHMENTS]" >> docs/AGENT_ACTIVITY.log

# After completing work (MANDATORY)
git add . && git commit -m "[AGENT_NAME]: [SUMMARY]"
./scripts/sync-environments.sh --update-status
./scripts/sync-environments.sh --readiness
```

### Worktree Navigation
```bash
# Switch to your assigned worktree
cd ../core-nexus-[worktree-name]

# Example: Memory Agent workflow
cd ../core-nexus-memory-service
poetry run uvicorn src.memory_service.api:app --reload

# Example: JARVIS Agent workflow  
cd ../core-nexus-jarvis
python test_jarvis.py

# Return to main repository
cd ../core-nexus
```

### Cleanup and Maintenance
```bash
# Complete cleanup (recommended monthly)
./scripts/worktree-cleanup.sh --all

# Remove abandoned worktrees
./scripts/worktree-cleanup.sh --remove-abandoned

# Clean temporary files
./scripts/worktree-cleanup.sh --temp-files

# Optimize git repositories
./scripts/worktree-cleanup.sh --optimize

# Validate integrity
./scripts/worktree-cleanup.sh --validate

# Emergency cleanup
./scripts/worktree-cleanup.sh --emergency
```

### Important Files for AI Agents
- `docs/AI_AGENT_COORDINATION.md` - Complete coordination protocols
- `docs/AGENT_WORKSPACE_PROTOCOLS.md` - Workspace-specific guidelines  
- `docs/WORKTREE_STATUS.md` - Real-time status dashboard
- `docs/AGENT_ACTIVITY.log` - Agent activity tracking
- `.env.worktree-template` - Environment configuration template

### Emergency Procedures
```bash
# Emergency stop all agents
echo "EMERGENCY_STOP: $(date) - [REASON]" >> docs/EMERGENCY.log

# Switch to safe rollback state
cd ../core-nexus-rollback

# Emergency cleanup
./scripts/worktree-cleanup.sh --emergency

# Check system health
make ci && ./scripts/sync-environments.sh --status
```

**CRITICAL**: Always check `docs/WORKTREE_STATUS.md` before starting work and update `docs/AGENT_ACTIVITY.log` during work sessions.

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