#!/bin/bash

# Core Nexus Worktree Cleanup Script
# Handles cleanup, maintenance, and emergency procedures for the worktree system

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
CLEANUP_LOG="$REPO_ROOT/.worktree-cleanup.log"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[CLEANUP]${NC} $1"
    echo "$(date): [CLEANUP] $1" >> "$CLEANUP_LOG"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    echo "$(date): [SUCCESS] $1" >> "$CLEANUP_LOG"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    echo "$(date): [WARNING] $1" >> "$CLEANUP_LOG"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    echo "$(date): [ERROR] $1" >> "$CLEANUP_LOG"
}

print_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
    echo "$(date): [INFO] $1" >> "$CLEANUP_LOG"
}

# Function to get all worktrees
get_worktrees() {
    git worktree list --porcelain | awk '/^worktree/ {print $2}' | grep -v "^$REPO_ROOT$"
}

# Function to check if worktree is safe to remove
is_safe_to_remove() {
    local worktree_path=$1
    local worktree_name=$(basename "$worktree_path" | sed "s/^${PROJECT_NAME}-//")
    
    # Never remove these critical worktrees automatically
    case $worktree_name in
        "production"|"rollback"|"hotfix")
            return 1
            ;;
        *)
            return 0
            ;;
    esac
}

# Function to backup worktree before cleanup
backup_worktree() {
    local worktree_path=$1
    local worktree_name=$(basename "$worktree_path" | sed "s/^${PROJECT_NAME}-//")
    local backup_dir="$REPO_ROOT/worktree-backups"
    local backup_path="$backup_dir/${worktree_name}-$(date +%Y%m%d-%H%M%S)"
    
    print_status "Creating backup of worktree: $worktree_name"
    
    mkdir -p "$backup_dir"
    
    # Create archive of worktree
    cd "$worktree_path"
    
    # Save git status and important files
    git status > "$backup_path-status.txt"
    git log --oneline -10 > "$backup_path-commits.txt"
    git stash list > "$backup_path-stashes.txt"
    
    # Archive modified files
    if [[ -n "$(git status --porcelain)" ]]; then
        git stash push -m "Cleanup backup $(date)"
        echo "Stashed changes for backup" >> "$backup_path-info.txt"
    fi
    
    # Copy important configuration files
    if [[ -f ".env" ]]; then
        cp .env "$backup_path-env.bak"
    fi
    
    if [[ -f ".worktree-config" ]]; then
        cp .worktree-config "$backup_path-config.bak"
    fi
    
    print_success "Backup created at: $backup_path-*"
}

# Function to remove abandoned worktrees
remove_abandoned_worktrees() {
    print_status "🧹 Scanning for abandoned worktrees..."
    
    local removed_count=0
    
    # Check git's worktree list for broken entries
    git worktree list --porcelain | while read -r line; do
        if [[ $line =~ ^worktree ]]; then
            local worktree_path=$(echo "$line" | awk '{print $2}')
            if [[ ! -d "$worktree_path" ]] && [[ "$worktree_path" != "$REPO_ROOT" ]]; then
                print_warning "Found broken worktree reference: $worktree_path"
                git worktree remove "$worktree_path" 2>/dev/null || git worktree prune
                ((removed_count++))
                print_success "Removed broken worktree reference: $worktree_path"
            fi
        fi
    done
    
    # Check for orphaned directories
    if [[ -d "$PARENT_DIR" ]]; then
        for dir in "$PARENT_DIR"/${PROJECT_NAME}-*; do
            if [[ -d "$dir" ]]; then
                local dir_name=$(basename "$dir")
                if ! git worktree list | grep -q "$dir"; then
                    print_warning "Found orphaned directory: $dir"
                    if is_safe_to_remove "$dir"; then
                        read -p "Remove orphaned directory $dir? (y/N): " -n 1 -r
                        echo
                        if [[ $REPLY =~ ^[Yy]$ ]]; then
                            rm -rf "$dir"
                            ((removed_count++))
                            print_success "Removed orphaned directory: $dir"
                        fi
                    else
                        print_warning "Skipping critical directory: $dir (manual removal required)"
                    fi
                fi
            fi
        done
    fi
    
    if [[ $removed_count -eq 0 ]]; then
        print_success "No abandoned worktrees found"
    else
        print_success "Removed $removed_count abandoned worktrees"
    fi
}

# Function to clean up temporary files
cleanup_temp_files() {
    print_status "🗑️  Cleaning up temporary files..."
    
    local cleaned_count=0
    
    # Clean up in main repository
    cd "$REPO_ROOT"
    
    # Remove log files older than 7 days
    find . -name "*.log" -mtime +7 -type f 2>/dev/null | while read -r logfile; do
        rm -f "$logfile"
        ((cleaned_count++))
        print_info "Removed old log file: $logfile"
    done
    
    # Clean up temporary stash files
    find . -name ".git-stash-*" -type f 2>/dev/null | while read -r stashfile; do
        rm -f "$stashfile"
        ((cleaned_count++))
        print_info "Removed temporary stash file: $stashfile"
    done
    
    # Clean up lock files
    find . -name ".workspace-lock" -type f 2>/dev/null | while read -r lockfile; do
        local lock_age=$(stat -c %Y "$lockfile" 2>/dev/null || echo 0)
        local current_time=$(date +%s)
        local age_hours=$(( (current_time - lock_age) / 3600 ))
        
        if [[ $age_hours -gt 24 ]]; then
            rm -f "$lockfile"
            ((cleaned_count++))
            print_warning "Removed stale lock file: $lockfile (${age_hours}h old)"
        fi
    done
    
    # Clean up each worktree
    for worktree in $(get_worktrees); do
        if [[ -d "$worktree" ]]; then
            cd "$worktree"
            
            # Clean git repository
            git gc --quiet 2>/dev/null || true
            
            # Remove Python cache files
            find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
            find . -name "*.pyc" -type f -delete 2>/dev/null || true
            find . -name "*.pyo" -type f -delete 2>/dev/null || true
            
            # Remove Node.js cache files
            rm -rf node_modules/.cache 2>/dev/null || true
            
            # Clean Docker volumes if present
            if [[ -f "docker-compose.yml" ]]; then
                docker-compose down --volumes --remove-orphans 2>/dev/null || true
            fi
        fi
    done
    
    print_success "Cleaned up temporary files across all worktrees"
}

# Function to optimize git repositories
optimize_git_repos() {
    print_status "⚡ Optimizing Git repositories..."
    
    # Optimize main repository
    cd "$REPO_ROOT"
    print_info "Optimizing main repository..."
    git gc --aggressive --quiet
    git repack -ad --quiet
    git prune --quiet
    
    # Optimize each worktree
    for worktree in $(get_worktrees); do
        if [[ -d "$worktree" ]]; then
            local worktree_name=$(basename "$worktree" | sed "s/^${PROJECT_NAME}-//")
            print_info "Optimizing worktree: $worktree_name"
            cd "$worktree"
            git gc --quiet
            git prune --quiet
        fi
    done
    
    print_success "Git repository optimization completed"
}

# Function to validate worktree integrity
validate_worktree_integrity() {
    print_status "🔍 Validating worktree integrity..."
    
    local issues_found=0
    
    # Check main repository
    cd "$REPO_ROOT"
    if ! git fsck --quiet 2>/dev/null; then
        print_error "Main repository integrity issues detected"
        ((issues_found++))
    fi
    
    # Check each worktree
    for worktree in $(get_worktrees); do
        if [[ -d "$worktree" ]]; then
            local worktree_name=$(basename "$worktree" | sed "s/^${PROJECT_NAME}-//")
            cd "$worktree"
            
            # Check git integrity
            if ! git fsck --quiet 2>/dev/null; then
                print_error "Integrity issues in worktree: $worktree_name"
                ((issues_found++))
            fi
            
            # Check for required files
            if [[ ! -f ".git" ]]; then
                print_error "Missing .git file in worktree: $worktree_name"
                ((issues_found++))
            fi
            
            # Check branch consistency
            local branch=$(git branch --show-current)
            if [[ -z "$branch" ]]; then
                print_warning "Detached HEAD in worktree: $worktree_name"
            fi
        else
            print_error "Worktree directory not found: $worktree"
            ((issues_found++))
        fi
    done
    
    if [[ $issues_found -eq 0 ]]; then
        print_success "All worktrees passed integrity validation"
    else
        print_error "$issues_found integrity issues found"
    fi
    
    return $issues_found
}

# Function to generate cleanup report
generate_cleanup_report() {
    local report_file="$REPO_ROOT/worktree-cleanup-report-$(date +%Y%m%d-%H%M%S).txt"
    
    print_status "📊 Generating cleanup report..."
    
    cat > "$report_file" << EOF
Core Nexus Worktree Cleanup Report
Generated: $(date)

=== SYSTEM OVERVIEW ===
Repository: $REPO_ROOT
Total Worktrees: $(git worktree list | wc -l)
Parent Directory: $PARENT_DIR

=== WORKTREE STATUS ===
EOF
    
    git worktree list >> "$report_file"
    
    cat >> "$report_file" << EOF

=== DISK USAGE ===
Main Repository: $(du -sh "$REPO_ROOT" | cut -f1)
EOF
    
    for worktree in $(get_worktrees); do
        if [[ -d "$worktree" ]]; then
            local worktree_name=$(basename "$worktree" | sed "s/^${PROJECT_NAME}-//")
            echo "Worktree $worktree_name: $(du -sh "$worktree" | cut -f1)" >> "$report_file"
        fi
    done
    
    cat >> "$report_file" << EOF

=== GIT STATISTICS ===
Total Objects: $(git count-objects -v | grep 'count' | awk '{print $2}')
Repository Size: $(git count-objects -vH | grep size-pack | awk '{print $2$3}')
Unreachable Objects: $(git count-objects -v | grep 'count-loose' | awk '{print $2}')

=== CLEANUP ACTIONS PERFORMED ===
EOF
    
    tail -20 "$CLEANUP_LOG" >> "$report_file"
    
    cat >> "$report_file" << EOF

=== RECOMMENDATIONS ===
- Run cleanup monthly for optimal performance
- Monitor disk usage in worktrees
- Regular integrity checks recommended
- Keep backups of critical worktrees

Report saved to: $report_file
EOF
    
    print_success "Cleanup report generated: $report_file"
}

# Function for emergency cleanup
emergency_cleanup() {
    print_status "🚨 EMERGENCY CLEANUP MODE ACTIVATED"
    print_warning "This will perform aggressive cleanup actions!"
    
    echo "Emergency actions that will be performed:"
    echo "1. Stop all running processes"
    echo "2. Force cleanup all lock files"
    echo "3. Reset all worktrees to clean state"
    echo "4. Remove all temporary files"
    echo "5. Force git cleanup"
    echo ""
    
    read -p "Continue with emergency cleanup? (yes/NO): " -r
    if [[ ! $REPLY =~ ^yes$ ]]; then
        print_info "Emergency cleanup cancelled"
        exit 0
    fi
    
    print_status "Starting emergency cleanup..."
    
    # Stop any running processes
    pkill -f "uvicorn.*memory_service" 2>/dev/null || true
    pkill -f "docker-compose" 2>/dev/null || true
    
    # Force remove all lock files
    find "$PARENT_DIR" -name ".workspace-lock" -type f -delete 2>/dev/null || true
    find "$PARENT_DIR" -name ".emergency-mode" -type f -delete 2>/dev/null || true
    
    # Clean all worktrees
    for worktree in $(get_worktrees); do
        if [[ -d "$worktree" ]]; then
            cd "$worktree"
            
            # Save current state before cleanup
            git stash push -m "Emergency cleanup backup $(date)" 2>/dev/null || true
            
            # Reset to clean state
            git reset --hard HEAD 2>/dev/null || true
            git clean -fd 2>/dev/null || true
            
            # Remove temporary files
            rm -rf __pycache__ .pytest_cache .mypy_cache 2>/dev/null || true
            rm -f *.log *.pid 2>/dev/null || true
        fi
    done
    
    # Force git cleanup
    cd "$REPO_ROOT"
    git gc --aggressive --prune=now
    git repack -ad
    
    print_success "Emergency cleanup completed"
    print_warning "All worktrees have been reset to clean state"
    print_info "Stashed changes are preserved and can be recovered"
}

# Function to show usage
show_usage() {
    echo "Core Nexus Worktree Cleanup Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -a, --all              Perform complete cleanup (abandoned, temp, optimize)"
    echo "  -r, --remove-abandoned Remove abandoned worktrees"
    echo "  -t, --temp-files       Clean up temporary files"
    echo "  -o, --optimize         Optimize Git repositories"
    echo "  -v, --validate         Validate worktree integrity"
    echo "  -R, --report           Generate cleanup report"
    echo "  -e, --emergency        Emergency cleanup mode"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --all               # Complete cleanup"
    echo "  $0 --remove-abandoned  # Remove abandoned worktrees only"
    echo "  $0 --emergency         # Emergency cleanup"
    echo "  $0 --validate          # Check integrity only"
}

# Main execution
main() {
    # Initialize cleanup log
    echo "=== Cleanup session started at $(date) ===" >> "$CLEANUP_LOG"
    
    case "${1:-}" in
        -a|--all)
            print_status "🧹 Starting complete worktree cleanup..."
            remove_abandoned_worktrees
            cleanup_temp_files
            optimize_git_repos
            validate_worktree_integrity
            generate_cleanup_report
            print_success "✅ Complete cleanup finished"
            ;;
        -r|--remove-abandoned)
            remove_abandoned_worktrees
            ;;
        -t|--temp-files)
            cleanup_temp_files
            ;;
        -o|--optimize)
            optimize_git_repos
            ;;
        -v|--validate)
            validate_worktree_integrity
            ;;
        -R|--report)
            generate_cleanup_report
            ;;
        -e|--emergency)
            emergency_cleanup
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
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
    
    echo "=== Cleanup session ended at $(date) ===" >> "$CLEANUP_LOG"
}

# Run main function
main "$@"