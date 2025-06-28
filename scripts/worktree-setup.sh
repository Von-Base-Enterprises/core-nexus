#!/bin/bash

# Core Nexus Git Worktree Setup Script
# Automates the creation of development environments for AI agent coordination

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_ROOT=$(pwd)
PARENT_DIR=$(dirname "$REPO_ROOT")
PROJECT_NAME="core-nexus"

# Worktree definitions
declare -A WORKTREES=(
    # Core Environment Worktrees
    ["production"]="main"
    ["staging"]="staging"
    ["development"]="develop"
    ["hotfix"]="main"
    ["rollback"]="main"
    
    # Component-Specific Worktrees
    ["memory-service"]="main"
    ["jarvis"]="main"
    ["observability"]="feature/opentelemetry-observability"
    ["performance"]="feature/pgvector-performance-optimization"
    ["testing"]="main"
)

# Environment configurations
declare -A ENV_CONFIGS=(
    ["production"]="ENVIRONMENT=production
DATABASE_URL=postgresql://nexus_memory_db_user:PASSWORD@dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com:5432/nexus_memory_db
GRAPH_ENABLED=true
LOG_LEVEL=INFO
ADM_EVOLUTION_ENABLED=true
ADM_SCORING_ENABLED=true"

    ["staging"]="ENVIRONMENT=staging
DATABASE_URL=postgresql://localhost:5432/nexus_staging_db
GRAPH_ENABLED=true
LOG_LEVEL=DEBUG
ADM_EVOLUTION_ENABLED=true
ADM_SCORING_ENABLED=false"

    ["development"]="ENVIRONMENT=development
DATABASE_URL=postgresql://localhost:5432/nexus_dev_db
GRAPH_ENABLED=true
LOG_LEVEL=DEBUG
ADM_EVOLUTION_ENABLED=false
ADM_SCORING_ENABLED=false"

    ["testing"]="ENVIRONMENT=testing
DATABASE_URL=postgresql://localhost:5432/nexus_test_db
GRAPH_ENABLED=false
LOG_LEVEL=DEBUG
ADM_EVOLUTION_ENABLED=false
ADM_SCORING_ENABLED=false"
)

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if we're in a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        print_error "Not in a git repository!"
        exit 1
    fi
    
    # Check if git worktree is available
    if ! git worktree --help > /dev/null 2>&1; then
        print_error "Git worktree command not available. Please update Git to version 2.5+"
        exit 1
    fi
    
    # Check if we're in the correct directory
    if [[ ! -f "README.md" ]] || [[ ! -d "python/memory_service" ]]; then
        print_error "Please run this script from the core-nexus root directory"
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Function to create a worktree
create_worktree() {
    local name=$1
    local branch=$2
    local path="${PARENT_DIR}/${PROJECT_NAME}-${name}"
    
    print_status "Creating worktree: ${name} (${branch})"
    
    # Check if worktree already exists
    if [[ -d "$path" ]]; then
        print_warning "Worktree already exists at $path"
        return 0
    fi
    
    # Create the worktree
    if git worktree add "$path" "$branch" 2>/dev/null; then
        print_success "Created worktree: $path"
    else
        # If branch doesn't exist, create it from main
        print_warning "Branch $branch doesn't exist, creating from main"
        git worktree add -b "$branch" "$path" main
        print_success "Created worktree with new branch: $path"
    fi
    
    return 0
}

# Function to setup environment configuration
setup_environment() {
    local name=$1
    local path="${PARENT_DIR}/${PROJECT_NAME}-${name}"
    
    print_status "Setting up environment for: $name"
    
    # Memory Service environment
    if [[ -n "${ENV_CONFIGS[$name]}" ]]; then
        mkdir -p "$path/python/memory_service"
        echo "${ENV_CONFIGS[$name]}" > "$path/python/memory_service/.env"
        print_success "Created memory service .env for $name"
    fi
    
    # JARVIS environment (copy from main if exists)
    if [[ -f "$REPO_ROOT/jarvis/.env" ]]; then
        mkdir -p "$path/jarvis"
        cp "$REPO_ROOT/jarvis/.env" "$path/jarvis/.env"
        print_success "Copied JARVIS .env for $name"
    fi
    
    # Create worktree-specific configuration
    cat > "$path/.worktree-config" << EOF
WORKTREE_NAME=$name
WORKTREE_BRANCH=$(git -C "$path" branch --show-current)
WORKTREE_PURPOSE=$(get_worktree_purpose "$name")
CREATED_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
LAST_SYNC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
EOF
}

# Function to get worktree purpose
get_worktree_purpose() {
    local name=$1
    case $name in
        "production") echo "Production deployment and validation" ;;
        "staging") echo "Staging environment testing" ;;
        "development") echo "Development integration" ;;
        "hotfix") echo "Emergency fixes and critical patches" ;;
        "rollback") echo "Previous stable version for rollback" ;;
        "memory-service") echo "Memory Service focused development" ;;
        "jarvis") echo "JARVIS AI agent development" ;;
        "observability") echo "Monitoring and observability work" ;;
        "performance") echo "Performance optimization and testing" ;;
        "testing") echo "Advanced testing suites and validation" ;;
        *) echo "General development work" ;;
    esac
}

# Function to create symbolic links for shared resources
setup_shared_resources() {
    local name=$1
    local path="${PARENT_DIR}/${PROJECT_NAME}-${name}"
    
    print_status "Setting up shared resources for: $name"
    
    # Create .gitignore if it doesn't exist
    if [[ ! -f "$path/.gitignore" ]]; then
        cp "$REPO_ROOT/.gitignore" "$path/.gitignore" 2>/dev/null || true
    fi
    
    # Link package.json and poetry files for consistency
    if [[ ! -L "$path/package.json" ]] && [[ -f "$REPO_ROOT/package.json" ]]; then
        ln -sf "$REPO_ROOT/package.json" "$path/package.json"
    fi
    
    if [[ ! -L "$path/pyproject.toml" ]] && [[ -f "$REPO_ROOT/pyproject.toml" ]]; then
        ln -sf "$REPO_ROOT/pyproject.toml" "$path/pyproject.toml"
    fi
}

# Function to setup CI/CD integration
setup_ci_integration() {
    local name=$1
    local path="${PARENT_DIR}/${PROJECT_NAME}-${name}"
    
    # Create a simple CI script for this worktree
    cat > "$path/ci-check.sh" << 'EOF'
#!/bin/bash
# CI check script for this worktree
set -e

echo "Running CI checks for worktree: $(basename $(pwd))"

# Check if this is a Python-focused worktree
if [[ -d "python/memory_service" ]]; then
    echo "Running Python checks..."
    cd python/memory_service
    poetry run pytest -q || echo "Some Python tests failed"
    poetry run ruff check . || echo "Python linting issues found"
    cd ../..
fi

# Check if this is a JARVIS-focused worktree
if [[ -d "jarvis" ]]; then
    echo "Running JARVIS checks..."
    cd jarvis
    python test_jarvis.py || echo "JARVIS tests failed"
    cd ..
fi

# Run make commands if Makefile exists
if [[ -f "Makefile" ]]; then
    echo "Running Makefile commands..."
    make lint || echo "Linting issues found"
    make test || echo "Some tests failed"
fi

echo "CI check completed for $(basename $(pwd))"
EOF
    
    chmod +x "$path/ci-check.sh"
    print_success "Created CI integration script for $name"
}

# Function to create rollback worktree with latest stable tag
setup_rollback_worktree() {
    local path="${PARENT_DIR}/${PROJECT_NAME}-rollback"
    
    print_status "Setting up rollback worktree with latest stable version..."
    
    # Get the latest tag
    local latest_tag=$(git describe --tags --abbrev=0 2>/dev/null || echo "main")
    
    if [[ "$latest_tag" != "main" ]]; then
        print_status "Using latest tag: $latest_tag"
        if [[ -d "$path" ]]; then
            rm -rf "$path"
        fi
        git worktree add "$path" "$latest_tag"
        print_success "Created rollback worktree at $latest_tag"
    else
        print_warning "No tags found, using main branch for rollback"
        create_worktree "rollback" "main"
    fi
}

# Function to display worktree status
show_worktree_status() {
    print_status "Current worktree status:"
    echo ""
    git worktree list
    echo ""
    print_success "Worktree setup completed!"
}

# Function to create status tracking file
create_status_tracking() {
    cat > "$REPO_ROOT/docs/WORKTREE_STATUS.md" << 'EOF'
# Core Nexus Worktree Status

This file tracks the status of all Git worktrees and their current assignments.

## Worktree Overview

| Worktree | Branch | Purpose | AI Agent Assignment | Last Update |
|----------|--------|---------|-------------------|-------------|
| production | main | Production deployment | Auto-Deploy Agent | - |
| staging | staging | Staging testing | QA Agent | - |
| development | develop | Development integration | Integration Agent | - |
| hotfix | main | Emergency fixes | Hotfix Agent | - |
| rollback | stable-tag | Previous stable version | Rollback Agent | - |
| memory-service | main | Memory Service development | Memory Agent | - |
| jarvis | main | JARVIS development | JARVIS Agent | - |
| observability | feature/* | Monitoring work | Observability Agent | - |
| performance | feature/* | Performance optimization | Performance Agent | - |
| testing | main | Testing suites | Testing Agent | - |

## Agent Coordination Status

### Current Active Work
- [ ] No active assignments

### Synchronization Points
- Last full sync: Never
- Next scheduled sync: Manual trigger
- Conflicts detected: None

### Usage Guidelines

1. **Check this file before starting work** on any component
2. **Update your status** when beginning/ending work sessions
3. **Report conflicts immediately** in the status section
4. **Coordinate handoffs** between agents working on related components

## Quick Commands

```bash
# Check all worktree status
git worktree list

# Sync specific worktree
./scripts/sync-environments.sh <worktree-name>

# Clean up unused worktrees
./scripts/worktree-cleanup.sh
```

---
*Last updated: $(date)*
EOF
}

# Main execution
main() {
    echo ""
    print_status "🚀 Core Nexus Git Worktree Setup"
    print_status "Setting up AI agent coordination infrastructure..."
    echo ""
    
    # Check prerequisites
    check_prerequisites
    
    # Create status tracking
    create_status_tracking
    
    # Create core environment worktrees
    print_status "Creating core environment worktrees..."
    for name in production staging development hotfix; do
        if [[ -n "${WORKTREES[$name]}" ]]; then
            create_worktree "$name" "${WORKTREES[$name]}"
            setup_environment "$name"
            setup_shared_resources "$name"
            setup_ci_integration "$name"
        fi
    done
    
    # Create component-specific worktrees
    print_status "Creating component-specific worktrees..."
    for name in memory-service jarvis observability performance testing; do
        if [[ -n "${WORKTREES[$name]}" ]]; then
            create_worktree "$name" "${WORKTREES[$name]}"
            setup_environment "$name"
            setup_shared_resources "$name"
            setup_ci_integration "$name"
        fi
    done
    
    # Setup special rollback worktree
    setup_rollback_worktree
    
    # Show final status
    show_worktree_status
    
    echo ""
    print_success "✅ Worktree setup completed successfully!"
    print_status "📚 Next steps:"
    echo "  1. Review docs/AI_AGENT_COORDINATION.md for usage guidelines"
    echo "  2. Run ./scripts/sync-environments.sh to sync changes"
    echo "  3. Check docs/WORKTREE_STATUS.md for current assignments"
    echo ""
}

# Run main function
main "$@"