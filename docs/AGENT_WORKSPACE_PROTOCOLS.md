# Agent Workspace Protocols

## 🎯 Overview

This document provides specific workspace protocols for each AI agent working on the Core Nexus project. These protocols ensure safe, efficient, and coordinated development across multiple worktrees while preventing conflicts and maintaining system integrity.

## 🏷️ Workspace Ownership Matrix

| Worktree | Primary Agent | Secondary Agent | Component Focus | Safety Level |
|----------|---------------|-----------------|-----------------|---------------|
| `core-nexus-production` | Auto-Deploy Agent | - | Production validation | 🔴 CRITICAL |
| `core-nexus-staging` | QA Agent | Testing Agent | Integration testing | 🟡 HIGH |
| `core-nexus-development` | Integration Agent | - | Feature integration | 🟡 HIGH |
| `core-nexus-memory-service` | Memory Agent | Performance Agent | Memory Service API | 🟢 STANDARD |
| `core-nexus-jarvis` | JARVIS Agent | - | AI agent development | 🟢 STANDARD |
| `core-nexus-performance` | Performance Agent | Memory Agent | Optimization | 🟢 STANDARD |
| `core-nexus-observability` | Observability Agent | - | Monitoring/metrics | 🟢 STANDARD |
| `core-nexus-testing` | Testing Agent | QA Agent | Test development | 🟢 STANDARD |
| `core-nexus-hotfix` | Hotfix Agent | - | Emergency fixes | 🔴 CRITICAL |
| `core-nexus-rollback` | Auto-Deploy Agent | - | Stable reference | 🔴 READ-ONLY |

---

## 🔴 Critical Workspaces (Production & Hotfix)

### Production Workspace (`core-nexus-production`)

**Agent**: Auto-Deploy Agent  
**Branch**: `main`  
**Safety Level**: 🔴 CRITICAL

#### Pre-Work Checklist
```bash
# 1. Verify production stability
curl -s https://core-nexus-memory-service.onrender.com/health || exit 1

# 2. Check staging test results
cd ../core-nexus-staging && ./ci-check.sh || exit 1

# 3. Verify no active hotfixes
git branch -a | grep -q "hotfix/" && echo "HOTFIX ACTIVE - ABORT" && exit 1

# 4. Lock production workspace
echo "LOCKED: $(date) - Production validation in progress" > .workspace-lock
```

#### Allowed Operations
- ✅ Health checks and monitoring
- ✅ Configuration validation
- ✅ Performance monitoring
- ✅ Deployment readiness verification
- ❌ Code changes (except critical documentation)
- ❌ Dependency updates
- ❌ Experimental features

#### Mandatory Testing Protocol
```bash
# Full CI pipeline before any changes
make ci || exit 1

# Production simulation tests
poetry run pytest tests/test_production_fidelity.py || exit 1

# Performance validation
poetry run pytest tests/test_performance.py || exit 1

# Security validation
make security-check || exit 1
```

#### Post-Work Checklist
```bash
# 1. Verify system health
./ci-check.sh && echo "Production workspace stable"

# 2. Update deployment status
echo "VALIDATED: $(date) - Ready for deployment" > .deployment-status

# 3. Unlock workspace
rm .workspace-lock

# 4. Notify other agents
echo "$(date): AUTO-DEPLOY: Production validation complete" >> ../docs/AGENT_ACTIVITY.log
```

### Hotfix Workspace (`core-nexus-hotfix`)

**Agent**: Hotfix Agent  
**Branch**: `main` (creates hotfix branches)  
**Safety Level**: 🔴 CRITICAL

#### Emergency Response Protocol
```bash
# 1. Immediate isolation
echo "HOTFIX_ACTIVE: $(date) - Critical issue response" > .emergency-mode

# 2. Create hotfix branch
git checkout -b "hotfix/$(date +%Y%m%d-%H%M%S)-[ISSUE_ID]"

# 3. Implement minimal fix
# [Implement only the critical fix - no refactoring]

# 4. Immediate testing
make test || exit 1
./ci-check.sh || exit 1

# 5. Fast-track validation
poetry run pytest tests/test_critical_path.py || exit 1
```

#### Hotfix Deployment Protocol
```bash
# 1. Create emergency tag
git tag "emergency-$(date +%Y%m%d-%H%M%S)"

# 2. Notify all agents
echo "EMERGENCY_DEPLOYMENT: $(date) - Hotfix deployed" >> ../docs/EMERGENCY.log

# 3. Coordinate with production
cd ../core-nexus-production
git fetch origin && git merge hotfix/[BRANCH_NAME]

# 4. Verify fix
curl -s https://core-nexus-memory-service.onrender.com/health
```

---

## 🟡 High-Importance Workspaces (Staging & Integration)

### Staging Workspace (`core-nexus-staging`)

**Agent**: QA Agent  
**Branch**: `staging`  
**Safety Level**: 🟡 HIGH

#### Testing Protocol
```bash
# 1. Environment preparation
docker-compose -f docker-compose.staging.yml up -d

# 2. Database migration testing
cd python/memory_service
poetry run python run_migrations.py --dry-run

# 3. Comprehensive test suite
poetry run pytest tests/ --maxfail=5

# 4. Advanced testing suites
poetry run python tests/run_advanced_test_suite.py

# 5. Integration testing
make test-integration
```

#### Quality Gates
```bash
# Code quality validation
make lint || exit 1
make type-check || exit 1

# Performance benchmarks
poetry run pytest tests/test_performance.py --benchmark-only

# Security scanning
make security-check

# Dependency vulnerability check
poetry audit
```

#### Environment Validation
```bash
# Memory Service validation
curl -s http://localhost:8000/health | jq '.status' | grep -q "healthy"

# JARVIS validation
cd ../jarvis && python test_jarvis.py

# Database connectivity
poetry run python -c "from src.memory_service.config import get_database_url; print('DB OK')"
```

### Development Workspace (`core-nexus-development`)

**Agent**: Integration Agent  
**Branch**: `develop`  
**Safety Level**: 🟡 HIGH

#### Integration Workflow
```bash
# 1. Feature branch preparation
git fetch origin
git checkout develop
git pull origin develop

# 2. Feature branch integration
git merge --no-ff feature/[BRANCH_NAME]

# 3. Conflict resolution
if git status | grep -q "both modified"; then
    echo "CONFLICTS DETECTED - Manual resolution required"
    # [Resolve conflicts with component owners]
fi

# 4. Post-merge validation
make ci || git reset --hard HEAD~1
```

#### Component Integration Testing
```bash
# Memory Service + JARVIS integration
cd python/memory_service && poetry run uvicorn src.memory_service.api:app &
cd jarvis && python -c "import core_nexus_bridge; bridge.test_connection()"

# Performance impact assessment
poetry run pytest tests/test_integration_performance.py
```

---

## 🟢 Standard Workspaces (Component Development)

### Memory Service Workspace (`core-nexus-memory-service`)

**Agent**: Memory Agent  
**Secondary**: Performance Agent  
**Safety Level**: 🟢 STANDARD

#### Development Environment Setup
```bash
# 1. Activate development environment
cd python/memory_service
poetry install

# 2. Database setup
export PGVECTOR_PASSWORD="dev_password"
docker-compose up -d postgres

# 3. Run migrations
poetry run python run_migrations.py

# 4. Start development server
poetry run uvicorn src.memory_service.api:app --reload --port 8000
```

#### Component-Specific Testing
```bash
# Unit tests
poetry run pytest tests/test_api_endpoints.py -v

# Provider tests
poetry run pytest tests/test_providers.py

# Graph integration tests
if [[ "$GRAPH_ENABLED" == "true" ]]; then
    poetry run pytest tests/test_graph_integration.py
fi

# Performance tests
poetry run pytest tests/test_performance.py --benchmark-only
```

#### Code Quality Standards
```bash
# Linting and formatting
poetry run ruff check src/
poetry run black src/
poetry run isort src/

# Type checking
poetry run mypy src/

# Security checks
poetry run bandit -r src/
```

#### Provider Coordination
```bash
# When working with multiple providers
echo "PROVIDER_WORK: $(date) - [PROVIDER_NAME] - [CHANGES]" >> .provider-work.log

# Test provider failover
poetry run pytest tests/test_provider_failover.py

# Validate provider compatibility
poetry run python src/memory_service/providers.py --validate-all
```

### JARVIS Workspace (`core-nexus-jarvis`)

**Agent**: JARVIS Agent  
**Safety Level**: 🟢 STANDARD

#### LangGraph Development
```bash
# 1. Environment setup
cd jarvis
poetry install
export GEMINI_API_KEY="[KEY]"

# 2. Workflow testing
python test_jarvis.py

# 3. Performance validation
python -c "
import time
from src.jarvis.langgraph_supervisor import supervisor
start = time.time()
result = supervisor.invoke({'query': 'test query'})
print(f'Response time: {time.time() - start:.2f}s')
"
```

#### AI Integration Testing
```bash
# Memory Service integration
python -c "
from src.jarvis.core_nexus_bridge import CoreNexusBridge
bridge = CoreNexusBridge()
result = bridge.query_memories('test query')
print(f'Integration test: {len(result)} memories retrieved')
"

# Gemini API validation
python -c "
from src.jarvis.gemini_integration import GeminiClient
client = GeminiClient()
response = client.generate('Hello world')
print(f'Gemini test: {response[:50]}...')
"
```

### Performance Workspace (`core-nexus-performance`)

**Agent**: Performance Agent  
**Secondary**: Memory Agent  
**Safety Level**: 🟢 STANDARD

#### Performance Testing Protocol
```bash
# 1. Baseline establishment
cd python/memory_service
poetry run pytest tests/test_performance.py --benchmark-save=baseline

# 2. Load testing
poetry run python performance_tests/load_test.py --requests=1000

# 3. Vector performance testing
poetry run pytest tests/test_vector_performance.py

# 4. Database optimization testing
poetry run python optimize_database.py --test-mode
```

#### Optimization Validation
```bash
# Memory usage monitoring
python -c "
import psutil, gc
gc.collect()
print(f'Memory usage: {psutil.Process().memory_info().rss / 1024 / 1024:.1f} MB')
"

# Query performance validation
poetry run python -c "
from src.memory_service.api import app
import time
start = time.time()
# [Run performance critical operations]
print(f'Operation time: {time.time() - start:.3f}s')
"
```

### Observability Workspace (`core-nexus-observability`)

**Agent**: Observability Agent  
**Safety Level**: 🟢 STANDARD

#### Monitoring Stack Setup
```bash
# 1. Start observability stack
cd python/memory_service/observability
docker-compose up -d

# 2. Verify services
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets | length'
curl -s http://localhost:3000/api/health

# 3. Configure dashboards
./scripts/setup-dashboards.sh
```

#### Metrics Validation
```bash
# Check metrics endpoint
curl -s http://localhost:8000/metrics | grep -c "memory_service"

# Validate OpenTelemetry
python -c "
from opentelemetry import trace
tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span('test'):
    print('OpenTelemetry working')
"

# Test alerting
curl -X POST http://localhost:9093/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '{"alerts": [{"labels": {"alertname": "test"}}]}'
```

### Testing Workspace (`core-nexus-testing`)

**Agent**: Testing Agent  
**Secondary**: QA Agent  
**Safety Level**: 🟢 STANDARD

#### Advanced Testing Protocol
```bash
# 1. Chaos engineering tests
poetry run pytest tests/test_chaos_engineering.py

# 2. Behavioral intelligence tests
poetry run pytest tests/test_behavioral_intelligence.py

# 3. Data science validation
poetry run pytest tests/test_data_science_validation.py

# 4. Deep observability tests
poetry run pytest tests/test_deep_observability.py
```

---

## 🛡️ Safety Protocols

### Workspace Locking Mechanism

```bash
# Check for locks before starting work
if [[ -f ".workspace-lock" ]]; then
    echo "Workspace locked: $(cat .workspace-lock)"
    exit 1
fi

# Create lock when starting critical work
echo "LOCKED: $(date) - [AGENT_NAME] - [WORK_DESCRIPTION]" > .workspace-lock

# Always remove lock when finished
trap 'rm -f .workspace-lock' EXIT
```

### Backup Before Major Changes

```bash
# Create checkpoint before significant modifications
git tag "checkpoint-$(date +%Y%m%d-%H%M%S)"
git stash push -m "Pre-change backup $(date)"

# For database changes
poetry run python ../../secure_backup_system.py full_backup "pre-change-$(date +%s)"
```

### Rollback Procedures

```bash
# Quick rollback to last checkpoint
git reset --hard checkpoint-[TIMESTAMP]

# Rollback database changes
poetry run python ../../secure_backup_system.py restore "backup-name"

# Emergency workspace reset
cd ../core-nexus-rollback
cp -r . ../core-nexus-[workspace-name]/
```

---

## 📊 Workspace Monitoring

### Health Check Commands

```bash
# Workspace status
echo "Workspace: $(basename $(pwd))"
echo "Branch: $(git branch --show-current)"
echo "Status: $(git status --porcelain | wc -l) modified files"
echo "Lock: $(test -f .workspace-lock && echo 'LOCKED' || echo 'Available')"

# Component health
if [[ -d "python/memory_service" ]]; then
    cd python/memory_service
    poetry run python -c "from src.memory_service.api import app; print('Memory Service: OK')"
fi

if [[ -d "jarvis" ]]; then
    cd jarvis
    python -c "import src.jarvis.main; print('JARVIS: OK')"
fi
```

### Performance Monitoring

```bash
# Resource usage
echo "CPU: $(top -l 1 | grep "CPU usage" | awk '{print $3}' | cut -d% -f1)%"
echo "Memory: $(ps -o pid,ppid,%mem,%cpu,comm -p $$ | tail -1 | awk '{print $3}')%"
echo "Disk: $(df -h . | tail -1 | awk '{print $5}')"

# Git repository health
echo "Repository size: $(du -sh .git | cut -f1)"
echo "Worktree count: $(git worktree list | wc -l)"
echo "Untracked files: $(git status --porcelain | grep "^??" | wc -l)"
```

---

## 🚨 Emergency Procedures

### Immediate Response Protocol

```bash
# 1. Stop all work immediately
echo "EMERGENCY_STOP: $(date) - [REASON]" >> ../docs/EMERGENCY.log

# 2. Preserve current state
git stash push -m "Emergency preservation $(date)"
git tag "emergency-$(date +%s)"

# 3. Switch to safe state
cd ../core-nexus-rollback
git checkout [STABLE_TAG]

# 4. Notify all agents
echo "EMERGENCY: $(date) - All agents switch to rollback workspace" >> ../docs/AGENT_ACTIVITY.log
```

### Workspace Recovery

```bash
# 1. Assess damage
git status
git log --oneline -10
git stash list

# 2. Attempt recovery
git reflog | head -20  # Find last good state
git reset --hard [GOOD_COMMIT]

# 3. Verify functionality
make test || echo "Recovery failed - manual intervention required"

# 4. Resume normal operations
rm -f .workspace-lock
echo "RECOVERY_COMPLETE: $(date)" >> ../docs/AGENT_ACTIVITY.log
```

---

## 📋 Daily Checklist Templates

### Morning Startup (All Agents)

```bash
# 1. Sync and status check
./scripts/sync-environments.sh --status
./scripts/sync-environments.sh [your-worktree]

# 2. Workspace health check
cd ../core-nexus-[your-worktree]
git status && git log --oneline -5

# 3. Component validation
make test || echo "Test failures detected"

# 4. Start work session
echo "$(date): [AGENT_NAME] Starting work session" >> ../docs/AGENT_ACTIVITY.log
```

### End of Day (All Agents)

```bash
# 1. Commit all work
git add . && git commit -m "[AGENT_NAME]: End of day summary - [ACCOMPLISHMENTS]"

# 2. Update status
./scripts/sync-environments.sh --update-status

# 3. Check integration readiness
./scripts/sync-environments.sh --readiness

# 4. Clean workspace
rm -f .workspace-lock
git clean -fd

# 5. Final status update
echo "$(date): [AGENT_NAME] End of session - [SUMMARY]" >> ../docs/AGENT_ACTIVITY.log
```

---

*These workspace protocols ensure safe, coordinated development across all Core Nexus components while maximizing productivity and maintaining system integrity.*

**Last Updated**: $(date)  
**Version**: 1.0  
**Next Review**: Weekly