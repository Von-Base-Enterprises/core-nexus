# Core Nexus API Authentication Guide

This document describes the authentication requirements and methods for accessing the Core Nexus Memory Service API.

## Overview

The Core Nexus Memory Service uses API key authentication to secure endpoints and implements rate limiting to ensure fair usage and system stability.

## Authentication Methods

### 1. API Key Authentication (Recommended)

The primary authentication method uses API keys provided via HTTP headers.

#### Header Format
```http
X-API-Key: your-api-key-here
```

#### Example Request
```bash
curl -H "X-API-Key: dev-key-12345" \
     https://core-nexus-memory-service.onrender.com/memories
```

### 2. Bearer Token Authentication

Alternatively, you can use the Authorization header with Bearer token format:

#### Header Format
```http
Authorization: Bearer your-api-key-here
```

#### Example Request
```bash
curl -H "Authorization: Bearer dev-key-12345" \
     https://core-nexus-memory-service.onrender.com/memories
```

## Rate Limiting

All authenticated requests are subject to rate limiting to ensure service availability.

### Rate Limit Headers

Every API response includes rate limit information in the following headers:

- **X-RateLimit-Limit**: Maximum number of requests allowed per minute
- **X-RateLimit-Remaining**: Number of requests remaining in the current window
- **X-RateLimit-Reset**: Unix timestamp when the rate limit window resets
- **Retry-After**: (Only on 429 responses) Seconds to wait before retrying

### Example Response Headers
```http
HTTP/2 200 OK
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1753113600
X-API-Key-Valid: true
X-Is-Admin: false
```

### Rate Limit Exceeded Response
```http
HTTP/2 429 Too Many Requests
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1753113600
Retry-After: 42

{
  "detail": "Rate limit exceeded",
  "error_code": "RATE_LIMIT"
}
```

## Error Responses

### Missing API Key
```http
HTTP/2 401 Unauthorized
WWW-Authenticate: Bearer

{
  "detail": "API key required. Provide via X-API-Key header.",
  "error_code": "AUTH_001"
}
```

### Invalid API Key
```http
HTTP/2 401 Unauthorized
WWW-Authenticate: Bearer

{
  "detail": "Invalid API key",
  "error_code": "AUTH_002"
}
```

## Endpoints That Don't Require Authentication

The following endpoints are publicly accessible without authentication:

- `/health` - Service health check
- `/metrics` - Prometheus metrics
- `/metrics/fastapi` - FastAPI specific metrics
- `/docs` - Interactive API documentation
- `/openapi.json` - OpenAPI schema
- `/redoc` - ReDoc API documentation

## Environment Configuration

### API Keys Configuration

Set API keys via the `API_KEYS` environment variable (comma-separated):
```bash
API_KEYS=key1,key2,key3
```

### Admin Key Configuration

Set a special admin key for privileged operations:
```bash
ADMIN_KEY=your-super-secret-admin-key
```

### Rate Limiting Configuration

Configure rate limits via environment variables:
```bash
RATE_LIMIT_PER_MINUTE=60  # Requests per minute per API key
RATE_LIMIT_BURST=10       # Burst capacity
```

## Best Practices

1. **Secure Storage**: Never commit API keys to version control. Use environment variables or secret management systems.

2. **Key Rotation**: Regularly rotate API keys, especially if they may have been exposed.

3. **Rate Limit Handling**: Implement exponential backoff when receiving 429 responses:
   ```python
   import time
   import requests
   
   def make_request_with_retry(url, headers, max_retries=3):
       for attempt in range(max_retries):
           response = requests.get(url, headers=headers)
           
           if response.status_code == 429:
               retry_after = int(response.headers.get('Retry-After', 60))
               time.sleep(retry_after)
               continue
               
           return response
       
       raise Exception("Max retries exceeded")
   ```

4. **Monitor Usage**: Check the rate limit headers in responses to avoid hitting limits:
   ```python
   response = requests.get(url, headers={'X-API-Key': 'your-key'})
   remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
   
   if remaining < 10:
       print(f"Warning: Only {remaining} requests remaining")
   ```

## SDK Integration

When using the Core Nexus Python SDK, authentication is handled automatically:

```python
from core_nexus import CoreNexusClient

# API key is automatically added to all requests
client = CoreNexusClient(
    api_key="your-api-key",
    base_url="https://core-nexus-memory-service.onrender.com"
)

# Make authenticated requests
memories = client.memories.list(limit=100)
```

## Troubleshooting

### Common Issues

1. **Getting 401 errors despite providing API key**
   - Verify the key is correct and active
   - Check header name spelling (X-API-Key, not X-Api-Key)
   - Ensure no extra spaces in the key value

2. **Frequent rate limit errors**
   - Implement request batching where possible
   - Use webhooks for real-time updates instead of polling
   - Consider requesting a higher rate limit for production use

3. **Authentication works locally but not in production**
   - Verify environment variables are properly set in production
   - Check for differences in header handling between environments
   - Ensure HTTPS is used in production (some proxies strip headers from HTTP)

## Security Considerations

1. **HTTPS Only**: Always use HTTPS in production to prevent API key interception
2. **Principle of Least Privilege**: Create separate API keys for different applications/environments
3. **IP Whitelisting**: For additional security, consider implementing IP-based access controls
4. **Audit Logging**: All authentication attempts (successful and failed) are logged for security monitoring

## Migration from Previous Versions

If you were using the service before authentication was required:

1. Obtain API keys from your administrator
2. Update all API calls to include the X-API-Key header
3. Update error handling to handle 401 responses
4. Implement rate limit handling for 429 responses

## Contact

For API key requests, rate limit increases, or authentication issues, please contact the Core Nexus team or open an issue in the [GitHub repository](https://github.com/Von-Base-Enterprises/core-nexus).