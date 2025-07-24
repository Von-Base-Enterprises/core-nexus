#!/usr/bin/env python3
"""
Check the actual Redis URL being used in production.
Call this via the API to see what REDIS_URL environment variable contains.
"""
import os

def get_redis_info():
    redis_url = os.getenv('REDIS_URL', 'NOT_SET')
    return {
        "redis_url": redis_url,
        "redis_url_length": len(redis_url),
        "is_localhost": 'localhost' in redis_url,
        "is_render_redis": 'render' in redis_url or 'red-' in redis_url,
        "environment_vars_count": len([k for k in os.environ.keys() if 'REDIS' in k.upper()])
    }

if __name__ == "__main__":
    import json
    print(json.dumps(get_redis_info(), indent=2))