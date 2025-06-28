# Core Nexus AI Agent Coordination Protocol

## 🤖 Overview

This document establishes the coordination framework for multiple AI agents working simultaneously on the Core Nexus project. The goal is to achieve **exponential progress through synchronized, conflict-free development** across multiple worktrees.

## 🎯 Core Principles

### 1. **Isolation First**
- Each agent operates in dedicated worktrees to prevent conflicts
- Component ownership ensures clear responsibility boundaries
- Environment isolation prevents cross-contamination

### 2. **Communication Through Documentation**
- All agent communication happens through structured documentation
- Status updates are mandatory before and after work sessions
- Real-time coordination through shared status files

### 3. **Synchronization Points**
- Regular sync checkpoints ensure consistency
- Automated conflict detection prevents merge issues
- Coordinated integration through staging workflows

### 4. **Fail-Safe Operations**
- Rollback capabilities for any agent's work
- Backup and restore procedures for critical changes
- Emergency stop protocols for system-wide issues

---

## 🏗️ Agent Role Assignments

### Core Environment Agents

#### **Auto-Deploy Agent**
- **Worktree**: `core-nexus-production`
- **Branch**: `main`
- **Responsibilities**:
  - Monitor production deployment readiness
  - Validate production environment configurations
  - Execute automated deployments to Render.com
  - Monitor production health and performance
- **Key Commands**:
  ```bash
  cd ../core-nexus-production
  ./ci-check.sh && make test && make deploy-check
  ```

#### **QA Agent**
- **Worktree**: `core-nexus-staging`
- **Branch**: `staging`
- **Responsibilities**:
  - Execute comprehensive testing suites
  - Validate staging environment functionality
  - Coordinate integration testing between components
  - Manage test data and environments
- **Key Commands**:
  ```bash
  cd ../core-nexus-staging
  make test && poetry run pytest tests/test_comprehensive.py
  ```

#### **Integration Agent**
- **Worktree**: `core-nexus-development`
- **Branch**: `develop`
- **Responsibilities**:
  - Coordinate feature branch integrations
  - Manage dependency updates and conflicts
  - Ensure code quality standards
  - Facilitate branch merges
- **Key Commands**:
  ```bash
  cd ../core-nexus-development
  git merge feature/branch-name && make ci
  ```

### Component-Specific Agents

#### **Memory Agent**
- **Worktree**: `core-nexus-memory-service`
- **Branch**: `main` or feature branches
- **Responsibilities**:
  - Memory Service API development
  - Vector database optimization
  - Provider integration (pgvector, Pinecone, ChromaDB)
  - Performance monitoring and tuning
- **Key Commands**:
  ```bash
  cd ../core-nexus-memory-service/python/memory_service
  poetry run uvicorn src.memory_service.api:app --reload
  ```

#### **JARVIS Agent**
- **Worktree**: `core-nexus-jarvis`
- **Branch**: `main` or feature branches
- **Responsibilities**:
  - JARVIS AI agent development
  - LangGraph workflow optimization
  - Gemini integration improvements
  - AI orchestration features
- **Key Commands**:
  ```bash
  cd ../core-nexus-jarvis/jarvis
  python test_jarvis.py && python deploy.py
  ```

#### **Performance Agent**
- **Worktree**: `core-nexus-performance`
- **Branch**: `feature/pgvector-performance-optimization`
- **Responsibilities**:
  - Database performance optimization
  - Vector search performance tuning
  - Caching and optimization strategies
  - Benchmark testing and analysis
- **Key Commands**:
  ```bash
  cd ../core-nexus-performance
  poetry run pytest tests/test_performance.py
  ```

#### **Observability Agent**
- **Worktree**: `core-nexus-observability`
- **Branch**: `feature/opentelemetry-observability`
- **Responsibilities**:
  - Monitoring and alerting setup
  - OpenTelemetry integration
  - Grafana dashboard development
  - Performance metrics collection
- **Key Commands**:
  ```bash
  cd ../core-nexus-observability/python/memory_service/observability
  docker-compose up -d
  ```

### Support Agents

#### **Hotfix Agent**
- **Worktree**: `core-nexus-hotfix`
- **Branch**: `main` (creates hotfix branches as needed)
- **Responsibilities**:
  - Emergency bug fixes
  - Critical security patches
  - Production incident response
  - Rapid deployment coordination
- **Key Commands**:
  ```bash
  cd ../core-nexus-hotfix
  git checkout -b hotfix/critical-fix && make test
  ```

#### **Testing Agent**
- **Worktree**: `core-nexus-testing`
- **Branch**: `main`
- **Responsibilities**:
  - Advanced testing suite development
  - Chaos engineering tests
  - Behavioral intelligence validation
  - Test automation and CI/CD integration
- **Key Commands**:
  ```bash
  cd ../core-nexus-testing/python/memory_service/tests
  poetry run python run_advanced_test_suite.py
  ```

---

## 📋 Communication Protocols

### 1. **Work Session Initialization**

Before starting any work, agents MUST:

```bash
# 1. Check worktree status
./scripts/sync-environments.sh --status

# 2. Update status file
echo "$(date): [AGENT_NAME] Starting work on [COMPONENT] - [BRIEF_DESCRIPTION]" >> docs/AGENT_ACTIVITY.log

# 3. Sync your worktree
./scripts/sync-environments.sh [your-worktree-name]

# 4. Verify no conflicts
./scripts/sync-environments.sh --conflicts
```

### 2. **Progress Reporting**

During work sessions, update progress every 30 minutes:

```bash
# Update work log
echo "$(date): [AGENT_NAME] Progress: [SPECIFIC_ACCOMPLISHMENTS]" >> docs/AGENT_ACTIVITY.log

# Update status in worktree config
cd ../core-nexus-[your-worktree]
echo "CURRENT_TASK=[TASK_DESCRIPTION]" >> .worktree-config
echo "PROGRESS_PERCENTAGE=[0-100]" >> .worktree-config
```

### 3. **Work Session Completion**

At the end of each work session:

```bash
# 1. Commit all changes
git add . && git commit -m "[AGENT_NAME]: [DESCRIPTIVE_COMMIT_MESSAGE]"

# 2. Update completion log
echo "$(date): [AGENT_NAME] Completed: [ACCOMPLISHMENTS] - Ready for: [NEXT_STEPS]" >> docs/AGENT_ACTIVITY.log

# 3. Update status file
./scripts/sync-environments.sh --update-status

# 4. Check integration readiness
./scripts/sync-environments.sh --readiness
```

---

## ⚡ Synchronization Strategies

### Real-Time Coordination

#### **Status Polling**
```bash
# Every 15 minutes, check for updates from other agents
./scripts/sync-environments.sh --status | grep -E "(Modified|Conflict)"
```

#### **Conflict Detection**
```bash
# Before major operations, check for conflicts
if ! ./scripts/sync-environments.sh --conflicts; then
    echo "CONFLICT DETECTED - Halting operations"
    exit 1
fi
```

#### **Integration Checkpoints**
- **Every 2 hours**: Full synchronization across all worktrees
- **Before major changes**: Coordination checkpoint with all active agents
- **End of day**: Complete status update and conflict resolution

### Automated Synchronization

#### **Hourly Auto-Sync** (Recommended Cron Job)
```bash
# Add to crontab: 0 * * * * /path/to/core-nexus/scripts/sync-environments.sh --all
```

#### **Pre-Commit Hooks**
```bash
# .git/hooks/pre-commit
#!/bin/bash
./scripts/sync-environments.sh --conflicts || exit 1
```

---

## 🚨 Conflict Resolution Procedures

### Level 1: Automatic Resolution

**File Conflicts**:
```bash
# 1. Stash current changes
git stash push -m "Conflict resolution stash"

# 2. Pull latest changes
git pull origin [branch-name]

# 3. Apply stashed changes with conflict resolution
git stash pop

# 4. Resolve conflicts and commit
git add . && git commit -m "Resolve conflicts with [other-agent]"
```

### Level 2: Coordination Required

**Branch Conflicts**:
```bash
# 1. Notify other agents
echo "$(date): [AGENT_NAME] CONFLICT: Multiple agents on branch [branch-name]" >> docs/CONFLICTS.log

# 2. Request temporary pause
echo "$(date): [AGENT_NAME] REQUESTING PAUSE: [reason]" >> docs/AGENT_ACTIVITY.log

# 3. Coordinate handoff through status files
```

### Level 3: Emergency Escalation

**System-Wide Issues**:
```bash
# 1. Trigger emergency stop
echo "EMERGENCY_STOP: $(date) - [AGENT_NAME] - [CRITICAL_ISSUE]" >> docs/EMERGENCY.log

# 2. Rollback to stable state
cd ../core-nexus-rollback
git checkout [stable-tag]

# 3. Document incident and recovery steps
```

---

## 🔄 Handoff Procedures

### Standard Handoff

When an agent completes work on a component:

```bash
# 1. Complete all pending commits
git add . && git commit -m "[AGENT_NAME]: Handoff ready - [SUMMARY]"

# 2. Create handoff documentation
cat > HANDOFF_[NEXT_AGENT].md << EOF
# Handoff from [CURRENT_AGENT] to [NEXT_AGENT]
Date: $(date)
Component: [COMPONENT_NAME]
Last Changes: [SUMMARY]
Next Steps: [RECOMMENDATIONS]
Known Issues: [ISSUES]
Test Status: [PASS/FAIL/PENDING]
Dependencies: [DEPENDENCIES]
EOF

# 3. Update agent assignment
sed -i "s/CURRENT_AGENT=[CURRENT_AGENT]/CURRENT_AGENT=[NEXT_AGENT]/" .worktree-config

# 4. Notify in activity log
echo "$(date): [CURRENT_AGENT] HANDOFF to [NEXT_AGENT] - [COMPONENT]" >> docs/AGENT_ACTIVITY.log
```

### Emergency Handoff

For urgent handoffs during incidents:

```bash
# 1. Immediate status update
echo "URGENT_HANDOFF: $(date) - [CURRENT_AGENT] to [NEXT_AGENT] - [REASON]" >> docs/EMERGENCY.log

# 2. Quick state preservation
git stash push -m "Emergency handoff state"
git tag "emergency-handoff-$(date +%s)"

# 3. Minimal handoff documentation
echo "[CURRENT_STATE]|[NEXT_STEPS]|[CRITICAL_INFO]" >> docs/EMERGENCY_HANDOFF.log
```

---

## 📊 Monitoring and Status Tracking

### Dashboard Commands

```bash
# Real-time agent activity
tail -f docs/AGENT_ACTIVITY.log

# Worktree status overview
./scripts/sync-environments.sh --status

# Integration readiness check
./scripts/sync-environments.sh --readiness

# Conflict monitoring
./scripts/sync-environments.sh --conflicts
```

### Status File Locations

- **Main Status**: `docs/WORKTREE_STATUS.md`
- **Activity Log**: `docs/AGENT_ACTIVITY.log`
- **Conflict Log**: `docs/CONFLICTS.log`
- **Emergency Log**: `docs/EMERGENCY.log`
- **Sync Log**: `.worktree-sync.log`

### Key Metrics to Monitor

1. **Agent Productivity**: Commits per hour per agent
2. **Conflict Frequency**: Conflicts per day across all worktrees
3. **Integration Success Rate**: Successful merges vs. failed merges
4. **Synchronization Health**: Time since last successful full sync
5. **Test Pass Rate**: CI success rate across all worktrees

---

## 🚀 Best Practices for Exponential Progress

### 1. **Parallel Development Strategy**

```bash
# Optimal agent distribution for maximum velocity:
# - 2 agents on Memory Service (core + optimization)
# - 1 agent on JARVIS development
# - 1 agent on testing and QA
# - 1 agent on observability and monitoring
# - 1 agent on integration and coordination
```

### 2. **Velocity Optimization**

- **Micro-commits**: Commit small, focused changes every 15-30 minutes
- **Continuous sync**: Sync with other agents every hour
- **Parallel testing**: Run tests in isolated environments
- **Shared knowledge**: Document insights in shared files

### 3. **Quality Assurance**

- **Pre-commit validation**: Always run `make lint && make test`
- **Cross-agent review**: Review handoff documentation before accepting
- **Integration testing**: Test component interactions regularly
- **Performance monitoring**: Track performance impact of all changes

### 4. **Communication Excellence**

- **Clear commit messages**: Include agent name and component in all commits
- **Detailed handoffs**: Provide comprehensive context for next agent
- **Proactive conflict resolution**: Address conflicts immediately
- **Regular status updates**: Update progress documentation frequently

---

## 🛠️ Quick Reference Commands

### Essential Daily Commands

```bash
# Morning startup routine
./scripts/sync-environments.sh --all
./scripts/sync-environments.sh --status
./scripts/sync-environments.sh --conflicts

# Work session management
cd ../core-nexus-[your-worktree]
git status && git log --oneline -5
make test && make lint

# End of day cleanup
git add . && git commit -m "[AGENT]: End of session summary"
./scripts/sync-environments.sh --update-status
./scripts/sync-environments.sh --readiness
```

### Emergency Commands

```bash
# Emergency stop all work
echo "EMERGENCY_STOP: $(date) - [REASON]" >> docs/EMERGENCY.log

# Quick rollback
cd ../core-nexus-rollback && git checkout [stable-tag]

# Force sync all worktrees
./scripts/sync-environments.sh --all --force

# Check system health
make ci && ./scripts/sync-environments.sh --status
```

---

## 📞 Support and Escalation

### When to Escalate

1. **Persistent conflicts** that can't be resolved within 30 minutes
2. **System-wide failures** affecting multiple agents
3. **Data corruption** or loss scenarios
4. **Performance degradation** affecting core functionality
5. **Security incidents** or potential vulnerabilities

### Escalation Process

1. **Document the issue** in `docs/EMERGENCY.log`
2. **Preserve current state** with git tags and stashes
3. **Notify all agents** through activity log
4. **Switch to rollback worktree** if necessary
5. **Follow incident response procedures** in `docs/INCIDENT_RESPONSE.md`

---

*This coordination protocol enables multiple AI agents to work together seamlessly, achieving exponential progress while maintaining system stability and code quality.*

**Last Updated**: $(date)  
**Version**: 1.0  
**Next Review**: Weekly