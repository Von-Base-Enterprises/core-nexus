#!/usr/bin/env python3
"""
Check the OpenAPI spec to see what endpoints are available.
"""

import asyncio
import httpx
import json

async def check_spec():
    headers = {"X-API-Key": "dev-key-12345"}
    base_url = "https://core-nexus-memory-service.onrender.com"
    
    print("=" * 60)
    print("API Specification Check")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        # Get OpenAPI spec
        print("\nFetching OpenAPI specification...")
        try:
            response = await client.get(f"{base_url}/openapi.json")
            if response.status_code == 200:
                spec = response.json()
                
                print(f"\nAPI Title: {spec.get('info', {}).get('title', 'Unknown')}")
                print(f"API Version: {spec.get('info', {}).get('version', 'Unknown')}")
                
                print("\nAvailable Endpoints:")
                paths = spec.get('paths', {})
                
                # Group by path prefix
                endpoint_groups = {}
                for path, methods in paths.items():
                    prefix = path.split('/')[1] if len(path.split('/')) > 1 else 'root'
                    if prefix not in endpoint_groups:
                        endpoint_groups[prefix] = []
                    
                    for method in methods:
                        if method in ['get', 'post', 'put', 'delete', 'patch']:
                            endpoint_groups[prefix].append(f"{method.upper()} {path}")
                
                # Print grouped endpoints
                for group, endpoints in sorted(endpoint_groups.items()):
                    print(f"\n{group.upper()}:")
                    for endpoint in sorted(endpoints):
                        print(f"  - {endpoint}")
                
                # Look for graph-related endpoints specifically
                print("\n\nGraph-Related Endpoints:")
                graph_endpoints = []
                for path in paths:
                    if 'graph' in path.lower():
                        graph_endpoints.append(path)
                
                if graph_endpoints:
                    for endpoint in graph_endpoints:
                        print(f"  - {endpoint}")
                        methods = paths[endpoint]
                        for method, details in methods.items():
                            if method in ['get', 'post', 'put', 'delete', 'patch']:
                                summary = details.get('summary', 'No summary')
                                print(f"      {method.upper()}: {summary}")
                else:
                    print("  No graph-specific endpoints found")
                
            else:
                print(f"Failed to fetch spec: {response.status_code}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_spec())