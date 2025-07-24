# Core Nexus Authentication Guide

## Overview

Core Nexus uses API key authentication with rate limiting to ensure secure and fair access to the Memory Service API. This guide covers everything you need to know about authenticating with the service.

## Quick Start

### Using X-API-Key Header (Recommended)

```bash
curl -H "X-API-Key: your-api-key" \
     https://core-nexus-memory-service.onrender.com/memories
```

### Using Bearer Token

```bash
curl -H "Authorization: Bearer your-api-key" \
     https://core-nexus-memory-service.onrender.com/memories
```

## Authentication Methods

### 1. X-API-Key Header

The preferred method for API authentication:

```python
import requests

headers = {
    "X-API-Key": "your-api-key"
}

response = requests.get(
    "https://core-nexus-memory-service.onrender.com/memories",
    headers=headers
)
```

### 2. Bearer Token

Alternative method using standard Authorization header:

```javascript
const response = await fetch('https://core-nexus-memory-service.onrender.com/memories', {
    headers: {
        'Authorization': 'Bearer your-api-key'
    }
});
```

## Rate Limiting

All authenticated requests are subject to rate limiting to ensure fair usage and service stability.

### Default Limits

- **Requests per minute**: 60
- **Burst capacity**: 10 additional requests
- **Reset window**: 60 seconds (rolling window)

### Rate Limit Headers

Every response includes rate limit information:

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1753117200
```

- `X-RateLimit-Limit`: Maximum requests allowed per minute
- `X-RateLimit-Remaining`: Requests remaining in current window
- `X-RateLimit-Reset`: Unix timestamp when the limit resets

### Handling Rate Limits

When rate limited, you'll receive a 429 response:

```json
{
    "detail": "Rate limit exceeded",
    "error_code": "RATE_001"
}
```

Headers will include:
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 45
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1753117245
```

## Error Responses

### Missing API Key (401)

```json
{
    "detail": "API key required. Provide via X-API-Key header.",
    "error_code": "AUTH_001"
}
```

### Invalid API Key (401)

```json
{
    "detail": "Invalid API key",
    "error_code": "AUTH_002"
}
```

### Rate Limit Exceeded (429)

```json
{
    "detail": "Rate limit exceeded",
    "error_code": "RATE_001"
}
```

## Bypass Endpoints

The following endpoints do not require authentication:

- `/health` - Service health check
- `/docs` - Interactive API documentation
- `/openapi.json` - OpenAPI specification
- `/metrics` - Prometheus metrics
- `/metrics/fastapi` - FastAPI metrics

## Best Practices

### 1. Secure Your API Keys

- Never commit API keys to version control
- Use environment variables for storage
- Rotate keys regularly
- Use different keys for different environments

```python
import os

api_key = os.environ.get('CORE_NEXUS_API_KEY')
if not api_key:
    raise ValueError("API key not found in environment")
```

### 2. Handle Rate Limits Gracefully

Implement exponential backoff when rate limited:

```python
import time
import requests
from typing import Optional

def make_request_with_retry(url: str, headers: dict, max_retries: int = 3) -> Optional[requests.Response]:
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)
        
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            print(f"Rate limited. Waiting {retry_after} seconds...")
            time.sleep(retry_after)
            continue
            
        return response
    
    return None
```

### 3. Monitor Your Usage

Track your API usage using the rate limit headers:

```python
def check_rate_limit_status(response):
    limit = response.headers.get('X-RateLimit-Limit')
    remaining = response.headers.get('X-RateLimit-Remaining')
    reset = response.headers.get('X-RateLimit-Reset')
    
    if remaining and int(remaining) < 10:
        print(f"Warning: Only {remaining} requests remaining!")
```

### 4. Use Connection Pooling

For better performance, reuse connections:

```python
import requests

# Create a session for connection pooling
session = requests.Session()
session.headers.update({'X-API-Key': 'your-api-key'})

# Reuse the session for multiple requests
response1 = session.get(f"{base_url}/memories")
response2 = session.get(f"{base_url}/memories/query")
```

## Troubleshooting

### Common Issues

1. **Getting 401 Unauthorized**
   - Verify your API key is correct
   - Check you're using the right header name
   - Ensure no extra spaces in the key

2. **Getting 429 Too Many Requests**
   - Check the Retry-After header
   - Implement proper backoff logic
   - Consider caching responses

3. **No rate limit headers**
   - Ensure you're hitting authenticated endpoints
   - Check if you're going through a proxy that strips headers

### Debug Checklist

```bash
# Test authentication
curl -v -H "X-API-Key: your-api-key" \
     https://core-nexus-memory-service.onrender.com/memories

# Check rate limit headers
curl -I -H "X-API-Key: your-api-key" \
     https://core-nexus-memory-service.onrender.com/memories

# Test without authentication (should fail)
curl -v https://core-nexus-memory-service.onrender.com/memories
```

## Integration Examples

### Python SDK

```python
from core_nexus import CoreNexusClient

client = CoreNexusClient(
    api_key="your-api-key",
    base_url="https://core-nexus-memory-service.onrender.com"
)

# The SDK handles authentication and rate limiting automatically
memories = client.memories.list()
```

### JavaScript/TypeScript

```typescript
import { CoreNexus } from '@vonbase/core-nexus';

const client = new CoreNexus({
    apiKey: process.env.CORE_NEXUS_API_KEY,
    baseUrl: 'https://core-nexus-memory-service.onrender.com'
});

// Automatic retry on rate limit
const memories = await client.memories.list();
```

## Security Considerations

1. **HTTPS Only**: All API requests must use HTTPS
2. **Key Rotation**: Implement regular key rotation
3. **Least Privilege**: Use separate keys with minimal permissions
4. **Audit Logging**: Monitor API key usage for anomalies
5. **IP Allowlisting**: Contact support for IP-based restrictions

## Support

For authentication issues or to request higher rate limits:
- Email: support@vonbase.com
- Documentation: https://docs.core-nexus.ai
- Status Page: https://status.core-nexus.ai