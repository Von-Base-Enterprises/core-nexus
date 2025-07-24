# Authentication System Rollback Plan

## Overview

This document outlines the procedures for rolling back the authentication system in case of critical issues in production.

## Quick Rollback (Emergency)

If authentication is causing service outages, follow these steps:

### Option 1: Disable Authentication via Environment Variable

1. **Add bypass environment variable** to Render:
   ```
   DISABLE_AUTH=true
   ```

2. **Modify auth.py** to check for this variable:
   ```python
   if os.getenv('DISABLE_AUTH', 'false').lower() == 'true':
       return await call_next(request)
   ```

### Option 2: Revert to Previous Version

1. **Identify last working commit**:
   ```bash
   # Last known working commit before auth changes
   SAFE_COMMIT="fc0985f"
   ```

2. **Force push to main**:
   ```bash
   git checkout main
   git reset --hard fc0985f
   git push --force-with-lease origin main
   ```

3. **Monitor deployment** on Render dashboard

## Rollback Procedures

### Step 1: Assess the Situation

Before rolling back, determine:
- Is the entire service down?
- Are only authenticated endpoints affected?
- Is it a configuration issue or code issue?

### Step 2: Temporary Mitigation

If only authentication is problematic:

1. **Update API keys** in Render environment:
   ```
   API_KEYS=emergency-key-12345,bypass-key-67890
   ```

2. **Increase rate limits** temporarily:
   ```
   RATE_LIMIT_PER_MINUTE=1000
   ```

### Step 3: Full Rollback Process

1. **Create rollback branch**:
   ```bash
   git checkout -b rollback/auth-system
   git revert 783efd1  # Auth middleware commit
   git revert 4ee48c3  # Import fix commit
   ```

2. **Test locally**:
   ```bash
   cd python/memory_service
   poetry install
   poetry run uvicorn src.memory_service.api:app --reload
   ```

3. **Deploy rollback**:
   ```bash
   git checkout main
   git merge rollback/auth-system
   git push origin main
   ```

### Step 4: Communication

1. **Notify stakeholders**:
   - Email: team@vonbase.com
   - Slack: #core-nexus-alerts
   - Status page update

2. **Document issues**:
   - What failed?
   - When did it fail?
   - What was the impact?

## Hotfix Procedures

For non-breaking fixes:

1. **Create hotfix branch**:
   ```bash
   git checkout -b hotfix/auth-issue
   ```

2. **Make minimal changes**:
   - Fix only the critical issue
   - Don't refactor or add features

3. **Test thoroughly**:
   ```bash
   python3 test_auth_comprehensive.py
   ```

4. **Deploy hotfix**:
   ```bash
   git checkout main
   git merge hotfix/auth-issue
   git push origin main
   ```

## Monitoring During Rollback

### Key Metrics to Watch

1. **Service Health**:
   ```bash
   curl https://core-nexus-memory-service.onrender.com/health
   ```

2. **Error Rates**:
   - Check Render logs for 500 errors
   - Monitor `/metrics` endpoint

3. **Authentication Status**:
   ```bash
   # Should return 401 if auth is working
   curl https://core-nexus-memory-service.onrender.com/memories
   
   # Should return 200 if auth is disabled
   ```

## Post-Rollback Actions

1. **Root Cause Analysis**:
   - Review deployment logs
   - Check error patterns
   - Identify what went wrong

2. **Fix Forward Plan**:
   - Address the root cause
   - Add more tests
   - Improve deployment process

3. **Update Documentation**:
   - Document lessons learned
   - Update rollback procedures
   - Improve monitoring

## Emergency Contacts

- **Infrastructure**: ops@vonbase.com
- **On-call Engineer**: +1-XXX-XXX-XXXX
- **Render Support**: https://render.com/support

## Prevention Measures

To avoid future rollbacks:

1. **Staged Rollouts**:
   - Deploy to staging first
   - Canary deployments
   - Feature flags

2. **Better Testing**:
   - Integration tests
   - Load testing
   - Chaos engineering

3. **Monitoring**:
   - Real-time alerts
   - Automated rollback triggers
   - Health check endpoints

## Command Reference

```bash
# Check current deployed commit
git ls-remote origin main

# View auth-related commits
git log --oneline --grep="auth"

# Emergency disable (add to api.py temporarily)
if True:  # EMERGENCY: Bypass all auth
    response = await call_next(request)
    return response

# Test auth is disabled
curl https://core-nexus-memory-service.onrender.com/memories
# Should return 200 OK
```

## Rollback Decision Matrix

| Symptom | Severity | Action |
|---------|----------|--------|
| All endpoints return 500 | Critical | Full rollback |
| Auth endpoints fail | High | Disable auth temporarily |
| Rate limiting too strict | Medium | Update env vars |
| Missing headers | Low | Deploy hotfix |

Remember: **It's better to rollback quickly and fix properly than to debug in production.**