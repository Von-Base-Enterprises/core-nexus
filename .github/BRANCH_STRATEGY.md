# Core Nexus Branch Strategy

## Branch Naming Convention

- `main` - Production-ready code
- `feat/*` - New features
- `fix/*` - Bug fixes
- `chore/*` - Maintenance tasks
- `docs/*` - Documentation updates

## Workflow

1. Create feature branch from main
2. Make changes in small, focused commits
3. Push branch and create PR
4. Merge to main after review
5. Delete feature branch after merge

## Protection Rules

The `main` branch should have:
- Require pull request reviews
- Dismiss stale PR approvals
- Require status checks to pass
- Require branches to be up to date
- Include administrators in restrictions

## Cleanup Policy

- Delete branches after merge
- Run `git remote prune origin` weekly
- Keep only active feature branches