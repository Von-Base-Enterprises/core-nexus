# 🚀 PRODUCTION TRACKING SYSTEM

## Current Production Status (Last Updated: 2025-01-06)

### Deployment Configuration
- **Platform**: Render.com
- **Branch**: `main` ✅ (switched from feat/day1-vertical-slice)
- **Last Deployed Commit**: `b0444b1` (pending new deployment)
- **Pending Deployment**: `078321d` (EMERGENCY FIX: Allow empty search queries)

### Active Branches
```bash
# Update daily with: git branch -r | grep -v HEAD
main (default) ✅
feat/day1-vertical-slice ❌ (NEEDS DELETION - old deployment branch)
```

### Open PRs
1. None currently (good state)

### Production Health
- **API**: https://core-nexus-memory-service.onrender.com
- **Data**: 1,008 memories in pgvector
- **Issues**: Stats display bug (fix pending deployment)

## Branch Management Rules

1. **Feature Branches**
   - Name format: `feat/description` or `fix/description`
   - Must be deleted after merge
   - Max lifetime: 7 days

2. **PR Rules**
   - Max 3 open PRs at once
   - Review within 24 hours
   - Delete branch after merge

3. **Production Deploy**
   - Only from `main` branch
   - Tag releases: `v1.0.0`, `v1.0.1`, etc.
   - Monitor for 30 mins post-deploy

## Daily Checklist

- [ ] Check Render deployment status
- [ ] Verify production branch is `main`
- [ ] Count open PRs (max 3)
- [ ] Delete merged branches
- [ ] Update this tracking doc

## Monitoring Commands

```bash
# Check production status
curl https://core-nexus-memory-service.onrender.com/health

# Check deployment commit
curl https://core-nexus-memory-service.onrender.com/debug/env | jq '.render.RENDER_GIT_COMMIT'

# List remote branches
git branch -r

# Delete old branch
git push origin --delete feat/day1-vertical-slice
```