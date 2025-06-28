# AI Agent Onboarding Guide

## 🚀 Welcome to Core Nexus Development

This guide will help you get started as an AI agent working on the Core Nexus project. The system uses Git worktrees to enable multiple AI agents to work simultaneously without conflicts.

---

## 📋 Quick Start Checklist

### Phase 1: Initial Setup (Required for ALL agents)
- [ ] 1. Read this entire onboarding guide
- [ ] 2. Check your role assignment in the [Agent Assignments](#-agent-role-assignments) section
- [ ] 3. Initialize worktree system (first agent only) or verify it's set up
- [ ] 4. Navigate to your assigned worktree
- [ ] 5. Configure your environment
- [ ] 6. Read your workspace protocols
- [ ] 7. Perform initial system check

### Phase 2: Development Readiness
- [ ] 8. Update status tracking
- [ ] 9. Check for conflicts with other agents
- [ ] 10. Begin coordinated development
- [ ] 11. Follow mandatory check-in procedures

---

## 🎯 Agent Role Assignments

### 🔴 Critical Operations Agents

#### **Auto-Deploy Agent**
- **Worktree**: `core-nexus-production`
- **Branch**: `main`
- **Responsibilities**: Production validation, deployment readiness, health monitoring
- **Navigation**: `cd ../core-nexus-production`
- **Critical**: Read safety protocols in `docs/AGENT_WORKSPACE_PROTOCOLS.md`

#### **Hotfix Agent**  
- **Worktree**: `core-nexus-hotfix`
- **Branch**: `main` (creates hotfix branches as needed)
- **Responsibilities**: Emergency fixes, critical patches, incident response
- **Navigation**: `cd ../core-nexus-hotfix`
- **Critical**: Emergency procedures in `docs/AI_AGENT_COORDINATION.md`

### 🟡 Integration & Testing Agents

#### **QA Agent**
- **Worktree**: `core-nexus-staging`
- **Branch**: `staging`
- **Responsibilities**: Comprehensive testing, integration validation, quality gates
- **Navigation**: `cd ../core-nexus-staging`

#### **Integration Agent**
- **Worktree**: `core-nexus-development` 
- **Branch**: `develop`
- **Responsibilities**: Feature integration, dependency coordination, merge management
- **Navigation**: `cd ../core-nexus-development`

#### **Testing Agent**
- **Worktree**: `core-nexus-testing`
- **Branch**: `main`
- **Responsibilities**: Advanced testing suites, chaos engineering, test automation
- **Navigation**: `cd ../core-nexus-testing`

### 🟢 Component Development Agents

#### **Memory Agent**
- **Worktree**: `core-nexus-memory-service`
- **Branch**: `main` or feature branches
- **Responsibilities**: Memory Service API, vector databases, provider optimization
- **Navigation**: `cd ../core-nexus-memory-service`

#### **JARVIS Agent**
- **Worktree**: `core-nexus-jarvis`
- **Branch**: `main` or feature branches  
- **Responsibilities**: JARVIS AI development, LangGraph workflows, Gemini integration
- **Navigation**: `cd ../core-nexus-jarvis`

#### **Performance Agent**
- **Worktree**: `core-nexus-performance`
- **Branch**: `feature/pgvector-performance-optimization`
- **Responsibilities**: Database optimization, performance tuning, benchmarking
- **Navigation**: `cd ../core-nexus-performance`

#### **Observability Agent**
- **Worktree**: `core-nexus-observability`
- **Branch**: `feature/opentelemetry-observability`
- **Responsibilities**: Monitoring, metrics, alerting, dashboard development
- **Navigation**: `cd ../core-nexus-observability`

---

## 🛠️ Step-by-Step Setup

### Step 1: Verify Repository Access

```bash
# Check you're in the correct repository
pwd
# Should show: /path/to/core-nexus

# Verify worktree infrastructure exists
ls scripts/worktree-*.sh
# Should show: worktree-setup.sh, sync-environments.sh, worktree-cleanup.sh

ls docs/AI_AGENT_*.md
# Should show: AI_AGENT_COORDINATION.md
```

### Step 2: Check Worktree System Status

```bash
# Check if worktrees are already initialized
./scripts/sync-environments.sh --status

# If you see "Worktrees not yet initialized", proceed to Step 3
# If worktrees exist, skip to Step 4
```

### Step 3: Initialize Worktree System (First Agent Only)

**⚠️ Important**: Only ONE agent should run this. Check with other agents first!

```bash
# Initialize the complete worktree system
./scripts/worktree-setup.sh

# This creates 10 worktrees:
# - 5 core environment worktrees (production, staging, development, hotfix, rollback)  
# - 5 component worktrees (memory-service, jarvis, performance, observability, testing)
```

### Step 4: Navigate to Your Assigned Worktree

Based on your role assignment above:

```bash
# Example for Memory Agent:
cd ../core-nexus-memory-service

# Example for JARVIS Agent:
cd ../core-nexus-jarvis

# Example for QA Agent:
cd ../core-nexus-staging

# Verify you're in the correct worktree:
pwd && git branch --show-current
```

### Step 5: Configure Your Environment

```bash
# Check if environment file exists
ls -la .env

# If no .env file exists, copy and customize the template:
cp ../core-nexus/.env.worktree-template .env

# Edit the .env file with your specific settings:
# - Set WORKTREE_NAME to your worktree name
# - Set ENVIRONMENT to your environment type
# - Configure database and API keys as needed
```

### Step 6: Verify Component Setup

```bash
# For Memory Service components:
if [[ -d "python/memory_service" ]]; then
    cd python/memory_service
    poetry install
    poetry run python -c "print('Memory Service environment ready')"
    cd ../..
fi

# For JARVIS components:
if [[ -d "jarvis" ]]; then
    cd jarvis  
    python -c "print('JARVIS environment ready')"
    cd ..
fi

# Test basic functionality:
make test || echo "Some tests may fail until dependencies are configured"
```

---

## 📊 Coordination Protocols

### Before Starting Work (MANDATORY)

```bash
# 1. Sync with latest changes
./scripts/sync-environments.sh [your-worktree-name]

# 2. Check for conflicts
./scripts/sync-environments.sh --conflicts

# 3. Update activity log
echo "$(date): [YOUR_AGENT_NAME] Starting work session - [BRIEF_DESCRIPTION]" >> ../core-nexus/docs/AGENT_ACTIVITY.log

# 4. Check status dashboard
cat ../core-nexus/docs/WORKTREE_STATUS.md
```

### During Work (Every 30 Minutes)

```bash
# Update progress log
echo "$(date): [YOUR_AGENT_NAME] Progress: [SPECIFIC_ACCOMPLISHMENTS]" >> ../core-nexus/docs/AGENT_ACTIVITY.log

# Update worktree config
echo "CURRENT_TASK=[TASK_DESCRIPTION]" >> .worktree-config
echo "PROGRESS_PERCENTAGE=[0-100]" >> .worktree-config
```

### After Completing Work (MANDATORY)

```bash
# 1. Commit all changes
git add . && git commit -m "[YOUR_AGENT_NAME]: [DESCRIPTIVE_SUMMARY]"

# 2. Update completion log  
echo "$(date): [YOUR_AGENT_NAME] Completed: [ACCOMPLISHMENTS] - Ready for: [NEXT_STEPS]" >> ../core-nexus/docs/AGENT_ACTIVITY.log

# 3. Update system status
../core-nexus/scripts/sync-environments.sh --update-status

# 4. Check integration readiness
../core-nexus/scripts/sync-environments.sh --readiness
```

---

## 🚨 Emergency Procedures

### If You Detect a Conflict

```bash
# 1. Stop current work immediately
echo "$(date): [YOUR_AGENT_NAME] CONFLICT DETECTED: [DESCRIPTION]" >> ../core-nexus/docs/CONFLICTS.log

# 2. Check conflict status
../core-nexus/scripts/sync-environments.sh --conflicts

# 3. If serious, request coordination pause
echo "$(date): [YOUR_AGENT_NAME] REQUESTING PAUSE: [REASON]" >> ../core-nexus/docs/AGENT_ACTIVITY.log
```

### If You Encounter a Critical Issue

```bash
# 1. Document emergency
echo "EMERGENCY: $(date) - [YOUR_AGENT_NAME] - [CRITICAL_ISSUE]" >> ../core-nexus/docs/EMERGENCY.log

# 2. Preserve current state
git stash push -m "Emergency backup $(date)"
git tag "emergency-$(date +%s)"

# 3. Switch to rollback if needed
cd ../core-nexus-rollback
```

### If System Becomes Unresponsive

```bash
# Emergency cleanup
../core-nexus/scripts/worktree-cleanup.sh --emergency
```

---

## 📚 Essential Documentation

### Must Read (Before Starting Work)
1. **`docs/AI_AGENT_COORDINATION.md`** - Complete coordination protocols
2. **`docs/AGENT_WORKSPACE_PROTOCOLS.md`** - Your specific workspace guidelines
3. **`CLAUDE.md`** - Development commands and worktree management

### Quick Reference
4. **`docs/WORKTREE_STATUS.md`** - Real-time system status
5. **`docs/AGENT_ACTIVITY.log`** - Agent activity tracking
6. **`.env.worktree-template`** - Environment configuration guide

### Component-Specific
- **Memory Service**: `python/memory_service/README.md`
- **JARVIS**: `jarvis/README.md`  
- **Testing**: `python/memory_service/tests/README_ADVANCED_TESTS.md`

---

## ⚡ Common Commands Reference

### Daily Workflow
```bash
# Morning startup
../core-nexus/scripts/sync-environments.sh --status
../core-nexus/scripts/sync-environments.sh [your-worktree]
git status && git log --oneline -5

# Development
make test && make lint
poetry run uvicorn src.memory_service.api:app --reload  # For Memory Service
python test_jarvis.py  # For JARVIS

# End of day
git add . && git commit -m "[AGENT]: [SUMMARY]"
../core-nexus/scripts/sync-environments.sh --update-status
```

### Troubleshooting
```bash
# Check worktree health
git worktree list
../core-nexus/scripts/sync-environments.sh --validate

# Reset if needed
../core-nexus/scripts/worktree-cleanup.sh --all

# Get help
../core-nexus/scripts/worktree-setup.sh --help
../core-nexus/scripts/sync-environments.sh --help
```

---

## 🎯 Success Criteria

### You're Ready When:
- [ ] You can navigate to your assigned worktree
- [ ] Your environment is configured and tested
- [ ] You can run basic commands (make test, etc.)
- [ ] You understand your coordination protocols
- [ ] You can update status tracking
- [ ] You know emergency procedures

### Development Quality Standards:
- [ ] Always run `make lint && make test` before committing
- [ ] Include agent name in all commit messages
- [ ] Update activity logs every 30 minutes during active work
- [ ] Check for conflicts before major operations
- [ ] Follow workspace-specific safety protocols

---

## 🤝 Coordination Best Practices

### Communication Excellence
- **Be Specific**: Include exact component, change type, and impact in all logs
- **Be Frequent**: Update status every 30 minutes during active sessions
- **Be Proactive**: Report potential conflicts immediately
- **Be Clear**: Use descriptive commit messages with agent identification

### Conflict Prevention
- **Check Before Acting**: Always run conflict checks before major changes
- **Coordinate Handoffs**: Use handoff documentation when switching components
- **Respect Ownership**: Follow component ownership guidelines
- **Sync Regularly**: Pull latest changes frequently

### Quality Maintenance
- **Test Everything**: Run tests before committing any changes
- **Document Changes**: Update relevant documentation with code changes
- **Monitor Impact**: Check system health after significant changes
- **Clean Up**: Use cleanup scripts monthly for maintenance

---

## 📞 Getting Help

### If You're Stuck:
1. **Check Status**: `../core-nexus/scripts/sync-environments.sh --status`
2. **Review Logs**: `tail -20 ../core-nexus/docs/AGENT_ACTIVITY.log`
3. **Validate System**: `../core-nexus/scripts/worktree-cleanup.sh --validate`
4. **Emergency Reset**: `../core-nexus/scripts/worktree-cleanup.sh --emergency`

### Documentation Hierarchy:
1. **This Guide** - For getting started
2. **AI_AGENT_COORDINATION.md** - For detailed protocols  
3. **AGENT_WORKSPACE_PROTOCOLS.md** - For workspace-specific rules
4. **CLAUDE.md** - For development commands
5. **Component READMEs** - For component-specific guidance

---

## 🎉 Ready to Start!

You're now ready to begin coordinated development on Core Nexus! Remember:

1. **Always check status before starting work**
2. **Update logs during work sessions**  
3. **Commit frequently with descriptive messages**
4. **Follow your workspace protocols**
5. **Coordinate with other agents proactively**

**Welcome to the team! Let's build amazing AI systems together! 🤖✨**

---

*Last Updated: $(date)*  
*Version: 1.0*  
*Next Review: Weekly*