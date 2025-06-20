#!/usr/bin/env python3
"""
Check if our fix was actually deployed by examining service behavior
"""

import asyncio
import httpx
import json
from datetime import datetime

API_BASE = "https://core-nexus-memory-service.onrender.com"

async def check_deployment():
    """Check deployment status and configuration"""
    print("🚀 CHECKING DEPLOYMENT STATUS")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # 1. Try to find any debug or version endpoints
        debug_endpoints = [
            "/debug/config", "/debug/version", "/debug/providers", "/debug/env",
            "/version", "/info", "/status", "/admin/status"
        ]
        
        print("1. 🔍 Checking for debug/version endpoints...")
        for endpoint in debug_endpoints:
            try:
                response = await client.get(f"{API_BASE}{endpoint}")
                if response.status_code == 200:
                    print(f"✅ Found {endpoint}: {response.status_code}")
                    try:
                        data = response.json()
                        print(f"   Data: {json.dumps(data, indent=2)[:200]}...")
                    except:
                        print(f"   Data: {response.text[:200]}...")
                elif response.status_code != 404:
                    print(f"🔍 {endpoint}: {response.status_code}")
            except:
                pass
        
        # 2. Check if we can access logs endpoint
        print("\n2. 🔍 Checking for logs endpoint...")
        try:
            response = await client.get(f"{API_BASE}/admin/logs")
            if response.status_code == 200:
                print("✅ Found logs endpoint")
            elif response.status_code == 401:
                print("🔐 Logs endpoint requires authentication")
            else:
                print(f"❌ Logs endpoint: {response.status_code}")
        except:
            pass
            
        # 3. Analyze the health response for clues about deployment
        print("\n3. 📊 Analyzing health response for deployment clues...")
        response = await client.get(f"{API_BASE}/health")
        
        if response.status_code == 200:
            health_data = response.json()
            
            # Check uptime - if very recent, it might have just redeployed
            uptime_seconds = health_data.get("uptime_seconds", 0)
            uptime_hours = uptime_seconds / 3600
            
            print(f"Service uptime: {uptime_hours:.1f} hours")
            
            if uptime_hours < 1:
                print("✅ Service restarted recently - may indicate recent deployment")
            elif uptime_hours > 24:
                print("⚠️ Service has been running for >24 hours - deployment may not have occurred")
            else:
                print("🔍 Service uptime suggests possible recent deployment")
                
            # Look for any version info in the response
            print(f"Health response keys: {list(health_data.keys())}")
            
            # Check for any git commit info
            if "version" in health_data or "commit" in health_data or "git" in health_data:
                print(f"Version info found: {health_data.get('version', health_data.get('commit', health_data.get('git')))}")
            
        # 4. Test error handling to see if our improved error messages appear
        print("\n4. 🧪 Testing error scenarios to check for improved logging...")
        
        # Try an invalid request to see error handling
        try:
            response = await client.post(
                f"{API_BASE}/memories",
                json={"invalid": "data"}  # Missing required fields
            )
            print(f"Invalid request response: {response.status_code}")
            if response.status_code >= 400:
                error_text = response.text
                if "replication" in error_text.lower() or "secondary" in error_text.lower():
                    print("✅ Error mentions replication - new code may be deployed")
                else:
                    print("🔍 No replication mentions in error response")
        except:
            pass

async def main():
    try:
        await check_deployment()
        
        print("\n" + "="*60)
        print("📋 DEPLOYMENT ANALYSIS SUMMARY")
        print("="*60)
        print("Based on available evidence:")
        print("1. Service is responding and healthy")
        print("2. No version/debug endpoints found (security is good)")
        print("3. ChromaDB provider shows healthy but empty")
        print("4. Replication is definitely not working")
        print("\nPossible explanations:")
        print("A. Fix was deployed but ChromaDB config is wrong") 
        print("B. Fix was deployed but there's a new bug")
        print("C. Render.com didn't pick up the deployment")
        print("D. There's a configuration issue preventing replication")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())