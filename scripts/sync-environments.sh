#!/bin/bash

# Core Nexus Environment Synchronization Script
# Manages synchronization between worktrees and detects conflicts for AI agent coordination

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
REPO_ROOT=$(pwd)
PARENT_DIR=$(dirname "$REPO_ROOT")
PROJECT_NAME="core-nexus"
STATUS_FILE="$REPO_ROOT/docs/WORKTREE_STATUS.md"
SYNC_LOG_FILE="$REPO_ROOT/.worktree-sync.log"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[SYNC]${NC} $1"
    echo "$(date): [SYNC] $1" >> "$SYNC_LOG_FILE"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    echo "$(date): [SUCCESS] $1" >> "$SYNC_LOG_FILE"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    echo "$(date): [WARNING] $1" >> "$SYNC_LOG_FILE"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    echo "$(date): [ERROR] $1" >> "$SYNC_LOG_FILE"
}

print_conflict() {
    echo -e "${CYAN}[CONFLICT]${NC} $1"
    echo "$(date): [CONFLICT] $1" >> "$SYNC_LOG_FILE"
}

# Function to get all worktrees
get_worktrees() {
    git worktree list --porcelain | awk '/^worktree/ {print $2}'
}

# Function to get worktree name from path
get_worktree_name() {
    local path=$1
    basename "$path" | sed "s/^${PROJECT_NAME}-//"
}

# Function to check if worktree is clean
is_worktree_clean() {
    local path=$1
    cd "$path"
    if [[ -n "$(git status --porcelain)" ]]; then
        return 1
    fi
    return 0
}

# Function to get worktree status
get_worktree_status() {
    local path=$1
    local name=$(get_worktree_name "$path")
    
    cd "$path"
    local branch=$(git branch --show-current)
    local commit=$(git rev-parse --short HEAD)
    local clean_status="Clean"
    
    if ! is_worktree_clean "$path"; then
        clean_status="Modified"
    fi
    
    # Check for unpushed commits
    local unpushed=""
    if git log origin/"$branch".."$branch" --oneline 2>/dev/null | grep -q .; then
        unpushed=" (unpushed)"
    fi
    
    echo "$name|$branch|$commit$unpushed|$clean_status"
}

# Function to detect conflicts between worktrees
detect_conflicts() {
    print_status "🔍 Detecting conflicts between worktrees..."
    
    local conflicts_found=false
    local temp_file=$(mktemp)
    
    # Get status of all worktrees
    for worktree in $(get_worktrees); do
        if [[ -d "$worktree" ]]; then
            get_worktree_status "$worktree" >> "$temp_file"
        fi
    done
    
    # Check for conflicts
    echo -e "\n${CYAN}Worktree Status Overview:${NC}"
    echo "Name|Branch|Commit|Status"
    echo "---|---|---|---"
    
    while IFS='|' read -r name branch commit status; do
        echo "$name|$branch|$commit|$status"
        
        # Check for modification conflicts
        if [[ "$status" == "Modified" ]]; then
            print_warning "Worktree '$name' has uncommitted changes"
            conflicts_found=true
        fi
        
        # Check for branch conflicts (multiple worktrees on same branch with changes)
        local same_branch_count=$(grep "|$branch|" "$temp_file" | wc -l)
        if [[ $same_branch_count -gt 1 ]] && [[ "$status" == "Modified" ]]; then
            print_conflict "Multiple worktrees working on branch '$branch' with changes"
            conflicts_found=true
        fi
    done < "$temp_file"
    
    rm "$temp_file"
    
    if [[ "$conflicts_found" == "true" ]]; then
        print_error "⚠️  Conflicts detected! Review worktree status before proceeding."
        return 1
    else
        print_success "✅ No conflicts detected between worktrees"
        return 0
    fi
}

# Function to sync specific worktree
sync_worktree() {
    local worktree_path=$1
    local worktree_name=$(get_worktree_name "$worktree_path")
    
    print_status "Syncing worktree: $worktree_name"
    
    cd "$worktree_path"
    
    # Get current branch
    local current_branch=$(git branch --show-current)
    
    # Check if worktree is clean
    if ! is_worktree_clean "$worktree_path"; then
        print_warning "Worktree '$worktree_name' has uncommitted changes. Stashing..."
        git stash push -m "Auto-stash before sync $(date)"
    fi
    
    # Fetch latest changes
    print_status "Fetching latest changes for $worktree_name..."
    git fetch origin
    
    # Check if remote branch exists
    if git ls-remote --heads origin "$current_branch" | grep -q "$current_branch"; then
        # Remote branch exists, try to merge
        local behind_count=$(git rev-list --count HEAD..origin/"$current_branch" 2>/dev/null || echo "0")
        local ahead_count=$(git rev-list --count origin/"$current_branch"..HEAD 2>/dev/null || echo "0")
        
        if [[ $behind_count -gt 0 ]]; then
            print_status "Worktree '$worktree_name' is $behind_count commits behind. Pulling changes..."
            if git pull origin "$current_branch"; then
                print_success "Successfully pulled changes for $worktree_name"
            else
                print_error "Failed to pull changes for $worktree_name. Manual intervention required."
                return 1
            fi
        fi
        
        if [[ $ahead_count -gt 0 ]]; then
            print_warning "Worktree '$worktree_name' is $ahead_count commits ahead of origin"
        fi
    else
        print_warning "Remote branch '$current_branch' doesn't exist for $worktree_name"
    fi
    
    # Check if we stashed anything and try to pop it
    if git stash list | grep -q "Auto-stash before sync"; then
        print_status "Restoring stashed changes for $worktree_name..."
        if git stash pop; then
            print_success "Restored stashed changes for $worktree_name"
        else
            print_error "Conflict restoring stashed changes for $worktree_name. Manual resolution required."
            return 1
        fi
    fi
    
    # Update worktree config
    if [[ -f ".worktree-config" ]]; then
        sed -i "s/LAST_SYNC=.*/LAST_SYNC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")/" .worktree-config
    fi
    
    return 0
}

# Function to sync all worktrees
sync_all_worktrees() {
    print_status "🔄 Syncing all worktrees..."
    
    local success_count=0
    local total_count=0
    
    for worktree in $(get_worktrees); do
        if [[ -d "$worktree" ]] && [[ "$worktree" != "$REPO_ROOT" ]]; then
            ((total_count++))
            if sync_worktree "$worktree"; then
                ((success_count++))
            fi
        fi
    done
    
    print_status "Sync completed: $success_count/$total_count worktrees synchronized"
    
    if [[ $success_count -eq $total_count ]]; then
        print_success "✅ All worktrees synchronized successfully"
        return 0
    else
        print_error "⚠️  Some worktrees failed to synchronize"
        return 1
    fi
}

# Function to update status tracking file
update_status_tracking() {
    print_status "📊 Updating worktree status tracking..."
    
    if [[ ! -f "$STATUS_FILE" ]]; then
        print_warning "Status file not found. Creating new one..."
        cat > "$STATUS_FILE" << 'EOF'
# Core Nexus Worktree Status

This file tracks the status of all Git worktrees and their current assignments.

## Worktree Overview

| Worktree | Branch | Purpose | AI Agent Assignment | Last Update |
|----------|--------|---------|-------------------|-------------|
EOF
    fi
    
    # Create temporary status section
    local temp_status=$(mktemp)
    echo "| Worktree | Branch | Purpose | AI Agent Assignment | Last Update |" > "$temp_status"
    echo "|----------|--------|---------|-------------------|-------------|" >> "$temp_status"
    
    # Get current status for each worktree
    for worktree in $(get_worktrees); do
        if [[ -d "$worktree" ]]; then
            local name=$(get_worktree_name "$worktree")
            cd "$worktree"
            
            local branch=$(git branch --show-current)
            local purpose="General development"
            local agent="Unassigned"
            local last_update=$(date +"%Y-%m-%d %H:%M")
            
            # Read worktree config if exists
            if [[ -f ".worktree-config" ]]; then
                purpose=$(grep "WORKTREE_PURPOSE=" .worktree-config | cut -d'=' -f2- | tr -d '"')
                last_update=$(grep "LAST_SYNC=" .worktree-config | cut -d'=' -f2- | tr -d '"')
            fi
            
            # Determine agent assignment based on name
            case $name in
                "production") agent="Auto-Deploy Agent" ;;
                "staging") agent="QA Agent" ;;
                "development") agent="Integration Agent" ;;
                "hotfix") agent="Hotfix Agent" ;;
                "rollback") agent="Rollback Agent" ;;
                "memory-service") agent="Memory Agent" ;;
                "jarvis") agent="JARVIS Agent" ;;
                "observability") agent="Observability Agent" ;;
                "performance") agent="Performance Agent" ;;
                "testing") agent="Testing Agent" ;;
            esac
            
            echo "| $name | $branch | $purpose | $agent | $last_update |" >> "$temp_status"
        fi
    done
    
    # Update the status file
    # Keep everything before the table and replace the table
    local temp_full=$(mktemp)
    awk '/## Worktree Overview/{print; getline; print; exit} {print}' "$STATUS_FILE" > "$temp_full"
    cat "$temp_status" >> "$temp_full"
    awk '/\| Worktree \| Branch/{found=1; next} found && /^$/{found=0} !found && !/\| .* \|/' "$STATUS_FILE" >> "$temp_full"
    
    mv "$temp_full" "$STATUS_FILE"
    rm "$temp_status"
    
    print_success "Status tracking file updated"
}

# Function to check for integration readiness
check_integration_readiness() {
    print_status "🧪 Checking integration readiness..."
    
    local ready_branches=()
    local not_ready_branches=()
    
    for worktree in $(get_worktrees); do
        if [[ -d "$worktree" ]] && [[ "$worktree" != "$REPO_ROOT" ]]; then
            local name=$(get_worktree_name "$worktree")
            cd "$worktree"
            
            # Check if worktree is clean and tests pass
            if is_worktree_clean "$worktree"; then
                # Try to run quick CI check if available
                if [[ -f "ci-check.sh" ]]; then
                    if ./ci-check.sh > /dev/null 2>&1; then
                        ready_branches+=("$name")
                    else
                        not_ready_branches+=("$name (CI failed)")
                    fi
                else
                    ready_branches+=("$name (no CI)")
                fi
            else
                not_ready_branches+=("$name (uncommitted changes)")
            fi
        fi
    done
    
    echo -e "\n${GREEN}Ready for Integration:${NC}"
    for branch in "${ready_branches[@]}"; do
        echo "  ✅ $branch"
    done
    
    echo -e "\n${YELLOW}Not Ready for Integration:${NC}"
    for branch in "${not_ready_branches[@]}"; do
        echo "  ❌ $branch"
    done
}

# Function to show usage
show_usage() {
    echo "Core Nexus Environment Synchronization Script"
    echo ""
    echo "Usage: $0 [OPTIONS] [WORKTREE_NAME]"
    echo ""
    echo "Options:"
    echo "  -a, --all              Sync all worktrees"
    echo "  -s, --status          Show worktree status only"
    echo "  -c, --conflicts       Check for conflicts only"
    echo "  -r, --readiness       Check integration readiness"
    echo "  -u, --update-status   Update status tracking file"
    echo "  -h, --help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --all                    # Sync all worktrees"
    echo "  $0 memory-service           # Sync specific worktree"
    echo "  $0 --conflicts              # Check for conflicts"
    echo "  $0 --status                 # Show status overview"
}

# Main execution
main() {
    # Initialize sync log
    echo "=== Sync session started at $(date) ===" >> "$SYNC_LOG_FILE"
    
    case "${1:-}" in
        -a|--all)
            detect_conflicts && sync_all_worktrees
            update_status_tracking
            check_integration_readiness
            ;;
        -s|--status)
            detect_conflicts
            ;;
        -c|--conflicts)
            detect_conflicts
            ;;
        -r|--readiness)
            check_integration_readiness
            ;;
        -u|--update-status)
            update_status_tracking
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        "")
            print_error "No options provided. Use --help for usage information."
            exit 1
            ;;
        *)
            # Sync specific worktree
            local target_path="${PARENT_DIR}/${PROJECT_NAME}-$1"
            if [[ -d "$target_path" ]]; then
                detect_conflicts && sync_worktree "$target_path"
                update_status_tracking
            else
                print_error "Worktree '$1' not found at $target_path"
                exit 1
            fi
            ;;
    esac
    
    echo "=== Sync session ended at $(date) ===" >> "$SYNC_LOG_FILE"
}

# Run main function
main "$@"