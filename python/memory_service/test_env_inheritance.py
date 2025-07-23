#!/usr/bin/env python3
"""
Test if the issue is with os.getenv vs os.environ
"""

import asyncio
import httpx
import json

async def test_env_methods():
    headers = {"X-API-Key": "dev-key-12345"}
    base_url = "https://core-nexus-memory-service.onrender.com"
    
    print("=" * 60)
    print("Environment Variable Access Methods Test")
    print("=" * 60)
    
    # Create a test script that checks env vars in different ways
    test_code = """
import os
import sys

# Method 1: os.getenv
env1 = os.getenv('OPENAI_API_KEY')
env2 = os.getenv('GEMINI_API_KEY')
env3 = os.getenv('GRAPH_ENABLED')
env4 = os.getenv('RENDER')

# Method 2: os.environ.get
env5 = os.environ.get('OPENAI_API_KEY')
env6 = os.environ.get('GEMINI_API_KEY')

# Method 3: Direct access (would error if not present)
try:
    env7 = os.environ['RENDER_SERVICE_NAME']
except KeyError:
    env7 = 'KEY_ERROR'

# Check if any Render-specific vars exist
render_vars = [k for k in os.environ.keys() if 'RENDER' in k]
graph_vars = [k for k in os.environ.keys() if 'GRAPH' in k]
api_vars = [k for k in os.environ.keys() if 'API' in k or 'KEY' in k]

result = {
    'os_getenv': {
        'OPENAI_API_KEY': bool(env1),
        'GEMINI_API_KEY': bool(env2),
        'GRAPH_ENABLED': env3,
        'RENDER': bool(env4)
    },
    'os_environ_get': {
        'OPENAI_API_KEY': bool(env5),
        'GEMINI_API_KEY': bool(env6)
    },
    'direct_access': {
        'RENDER_SERVICE_NAME': env7
    },
    'found_vars': {
        'render_vars': render_vars,
        'graph_vars': graph_vars,
        'api_var_count': len(api_vars)
    },
    'total_env_vars': len(os.environ),
    'python_version': sys.version
}

print(result)
"""
    
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        # Check if we can access system info
        print("\n1. Checking system information...")
        try:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                data = response.json()
                print(f"   Uptime: {data.get('uptime_seconds', 0):.1f} seconds")
                print(f"   Status: {data.get('status', 'unknown')}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Try to find any clue about the deployment environment
        print("\n2. Checking for deployment clues...")
        
        # Check if it's using the mock key from render.yaml
        try:
            response = await client.get(f"{base_url}/debug/startup-logs")
            if response.status_code == 200:
                data = response.json()
                logs = data.get('logs', [])
                for log in logs:
                    if 'mock_key_for_demo' in log:
                        print("   ⚠️  Found reference to mock_key_for_demo!")
                        print("   This suggests render.yaml values are being used")
                        break
        except:
            pass
        
        # Final diagnosis
        print("\n3. Diagnosis:")
        print("   Based on the evidence:")
        print("   - Environment variables are NOT being passed to the application")
        print("   - The service is running but without access to Render env vars")
        print("   - This could be due to:")
        print("     1. Render not injecting env vars properly")
        print("     2. Python process isolation")
        print("     3. Startup script not preserving environment")
        
        print("\n4. Checking if manual API key works...")
        # Test with a manual API key in the request
        test_memory = {
            "content": "Test with ADK and ML models",
            "tags": ["manual-test"],
            "metadata": {"api_key_test": True}
        }
        
        try:
            # Some APIs allow passing keys in headers
            test_headers = headers.copy()
            # test_headers['X-OpenAI-API-Key'] = 'test'  # Don't actually do this
            
            response = await client.post(
                f"{base_url}/memories",
                json=test_memory,
                headers=test_headers
            )
            print(f"   Memory creation: {response.status_code}")
        except Exception as e:
            print(f"   Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_env_methods())