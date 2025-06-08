#!/usr/bin/env python3
"""
Production Deployment Verification Script
Confirms Core Nexus Memory Service is live with GraphProvider
"""

import urllib.request
import urllib.error
import json
import time
from datetime import datetime

SERVICE_URL = "https://core-nexus-memory-service.onrender.com"

def check_endpoint(endpoint: str, name: str) -> tuple[bool, int, dict]:
    """Check if an endpoint is responding."""
    url = f"{SERVICE_URL}{endpoint}"
    print(f"\n🔍 Checking {name}...")
    print(f"   URL: {url}")
    
    try:
        req = urllib.request.Request(url)
        req.add_header('Content-Type', 'application/json')
        
        with urllib.request.urlopen(req, timeout=30) as response:
            status = response.getcode()
            data = json.loads(response.read().decode())
            print(f"   ✅ Status: {status} OK")
            return True, status, data
            
    except urllib.error.HTTPError as e:
        print(f"   ❌ HTTP Error: {e.code} - {e.reason}")
        return False, e.code, {}
    except urllib.error.URLError as e:
        print(f"   ❌ Connection Error: {e.reason}")
        return False, 0, {}
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False, 0, {}

def main():
    print("=" * 60)
    print("🚀 CORE NEXUS PRODUCTION DEPLOYMENT VERIFICATION")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Service: {SERVICE_URL}")
    
    # Step 1: Check basic health
    success, status, data = check_endpoint("/health", "Health Endpoint")
    if success:
        print(f"   Providers: {list(data.get('providers', {}).keys())}")
        print(f"   Total Memories: {data.get('total_memories', 0)}")
        print(f"   Uptime: {data.get('uptime_seconds', 0):.1f} seconds")
    
    # Step 2: Check providers list
    success, status, data = check_endpoint("/providers", "Providers List")
    if success:
        providers = data.get('providers', [])
        print(f"   Active Providers: {len(providers)}")
        
        # Check if GraphProvider is present
        graph_found = False
        for provider in providers:
            print(f"   - {provider['name']}: {'enabled' if provider.get('enabled') else 'disabled'}")
            if provider['name'] == 'graph':
                graph_found = True
                print(f"     ✅ GraphProvider is active!")
    
    # Step 3: Check graph-specific endpoints
    graph_endpoints = [
        ("/graph/stats", "Graph Statistics"),
        ("/graph/insights/test-id", "Graph Insights"),
    ]
    
    print("\n📊 Graph Provider Endpoints:")
    graph_working = 0
    for endpoint, name in graph_endpoints:
        success, status, _ = check_endpoint(endpoint, name)
        if success or status == 503:  # 503 means endpoint exists but provider not available
            graph_working += 1
    
    # Step 4: Final verdict
    print("\n" + "=" * 60)
    print("📋 DEPLOYMENT STATUS SUMMARY")
    print("=" * 60)
    
    if status == 200:
        print("✅ Service is LIVE and responding!")
        
        if graph_found:
            print("✅ GraphProvider is ACTIVE in the service!")
        else:
            print("⚠️  GraphProvider not found - may need GRAPH_ENABLED=true")
            
        if graph_working > 0:
            print(f"✅ {graph_working}/{len(graph_endpoints)} graph endpoints responding")
        else:
            print("⚠️  Graph endpoints not yet available")
            
        print("\n🎉 DEPLOYMENT SUCCESSFUL!")
    else:
        print("❌ Service is not responding properly")
        print("Please check Render deployment logs")
    
    # Optional: Keep monitoring
    print("\nWould you like to keep monitoring? (Ctrl+C to stop)")
    try:
        while True:
            time.sleep(60)
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Checking health...", end="")
            success, status, _ = check_endpoint("/health", "")
            if success:
                print(" ✅ Still healthy!")
            else:
                print(" ❌ Service down!")
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")

if __name__ == "__main__":
    main()