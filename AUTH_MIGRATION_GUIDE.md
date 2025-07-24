# Authentication System Migration Guide

## Overview

This guide documents the authentication improvements made to the Core Nexus Memory Service to fix error handling and add rate limiting headers.

## Changes Made

### 1. Created Authentication Middleware (`auth.py`)
- **Location**: `python/memory_service/src/memory_service/auth.py`
- **Features**:
  - API key validation via X-API-Key or Authorization Bearer headers
  - Returns proper 401 status codes for authentication failures (fixes 500 error issue)
  - Rate limiting with configurable limits
  - Rate limit headers in all responses
  - Support for bypass endpoints (health, docs, metrics)

### 2. Updated API Integration (`api.py`)
- Added import for auth module
- Integrated authentication middleware before CORS middleware
- Configured bypass endpoints for public access

### 3. Documentation Updates
- Created comprehensive `docs/API_AUTHENTICATION.md`
- Updated `README.md` with authentication section
- Added links to authentication documentation

### 4. Test Scripts
- `test_auth_locally.py` - For local development testing
- `test_auth_production.py` - For production verification

## Environment Variables

The authentication system uses these environment variables:

```bash
# API Keys (comma-separated list)
API_KEYS=dev-key-12345,prod-key-67890,test-key-11111

# Admin key for special operations
ADMIN_KEY=admin-super-secret-key

# Rate limiting configuration
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_BURST=10
```

## Deployment Steps

1. **Review Changes**
   ```bash
   git status
   git diff
   ```

2. **Commit Changes**
   ```bash
   git add python/memory_service/src/memory_service/auth.py
   git add python/memory_service/src/memory_service/api.py
   git add docs/API_AUTHENTICATION.md
   git add README.md
   git add test_auth_*.py
   git add AUTH_MIGRATION_GUIDE.md
   
   git commit -m "feat: Add authentication middleware with proper error handling and rate limiting

   - Fix 500 error on missing API key (now returns 401)
   - Add rate limit headers to all API responses
   - Support both X-API-Key and Bearer token authentication
   - Create comprehensive authentication documentation
   - Add test scripts for verification"
   ```

3. **Push and Create PR**
   ```bash
   git push origin main
   # Create PR on GitHub
   ```

4. **Deploy to Render**
   - After PR is merged, Render should auto-deploy
   - Or manually trigger deployment from Render dashboard

5. **Verify Deployment**
   ```bash
   python3 test_auth_production.py
   ```

## Verification

Run the production test script to verify all changes are working:

```bash
python3 test_auth_production.py
```

Expected results:
- ✅ Missing API Key → 401 (not 500)
- ✅ Invalid API Key → 401 (not 500)  
- ✅ Valid API Key → 200 with rate limit headers
- ✅ Bearer Token → 200
- ✅ Health Endpoint → 200 (no auth required)
- ✅ POST with Auth → 200 with rate limit headers

## Rollback Plan

If issues occur after deployment:

1. **Quick Fix**: Set environment variable to bypass auth temporarily
   ```bash
   AUTH_ENABLED=false
   ```

2. **Full Rollback**: Revert the commit and redeploy
   ```bash
   git revert <commit-hash>
   git push origin main
   ```

## Client Updates

Clients should be updated to:

1. **Handle 401 responses** instead of 500 for auth failures
2. **Monitor rate limit headers** to avoid hitting limits
3. **Implement retry logic** with exponential backoff for 429 responses

Example client update:
```python
response = requests.get(url, headers={'X-API-Key': api_key})

if response.status_code == 401:
    # Handle authentication error
    raise AuthenticationError("Invalid or missing API key")
elif response.status_code == 429:
    # Handle rate limit
    retry_after = int(response.headers.get('Retry-After', 60))
    time.sleep(retry_after)
    # Retry request
```

## Support

For issues or questions:
- Check `docs/API_AUTHENTICATION.md` for detailed documentation
- Run test scripts to diagnose problems
- Check service logs for authentication errors
- Contact the Core Nexus team