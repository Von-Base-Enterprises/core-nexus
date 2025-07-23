#!/usr/bin/env python3
"""
Monitor ADK deployment to Core Nexus production.
Checks for successful installation and availability.
"""

import time
import requests
import json
from datetime import datetime


def check_health():
    """Check basic health endpoint."""
    try:
        response = requests.get("https://core-nexus-memory-service.onrender.com/health", timeout=10)
        if response.status_code == 200:
            return True, response.json()
        return False, None
    except Exception as e:
        return False, str(e)


def check_adk_endpoint():
    """Check ADK test endpoint."""
    try:
        response = requests.get("https://core-nexus-memory-service.onrender.com/test/adk", timeout=10)
        if response.status_code == 200:
            return True, response.json()
        elif response.status_code == 404:
            return False, "ADK endpoint not found (deployment pending)"
        else:
            return False, f"Status code: {response.status_code}"
    except Exception as e:
        return False, str(e)


def monitor_deployment():
    """Monitor the deployment progress."""
    print("=" * 60)
    print("Core Nexus ADK Deployment Monitor")
    print("=" * 60)
    
    start_time = time.time()
    adk_available = False
    check_count = 0
    max_checks = 60  # 30 minutes max
    
    while check_count < max_checks and not adk_available:
        check_count += 1
        current_time = datetime.now().strftime("%H:%M:%S")
        
        print(f"\n[{current_time}] Check #{check_count}")
        
        # Check health
        health_ok, health_data = check_health()
        if health_ok:
            print("✅ Service is healthy")
        else:
            print(f"❌ Service health check failed: {health_data}")
        
        # Check ADK endpoint
        adk_ok, adk_data = check_adk_endpoint()
        if adk_ok:
            print("✅ ADK endpoint available!")
            print(json.dumps(adk_data, indent=2))
            
            if adk_data.get("adk_available"):
                print("\n🎉 ADK successfully deployed!")
                adk_available = True
                break
            else:
                print("⚠️  ADK endpoint exists but ADK not fully operational")
        else:
            print(f"⏳ ADK endpoint not ready: {adk_data}")
        
        if not adk_available and check_count < max_checks:
            print(f"\nWaiting 30 seconds before next check...")
            time.sleep(30)
    
    # Final summary
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    
    if adk_available:
        print(f"✅ DEPLOYMENT SUCCESSFUL!")
        print(f"Total deployment time: {elapsed/60:.1f} minutes")
        print("\nNext steps:")
        print("1. Test ADK functionality with: python test_adk_installation.py")
        print("2. Migrate Jarvis to ADK framework")
        print("3. Begin implementing Living Core Nexus architecture")
    else:
        print(f"❌ DEPLOYMENT TIMEOUT after {elapsed/60:.1f} minutes")
        print("Check Render dashboard for deployment logs")
    
    print("=" * 60)


if __name__ == "__main__":
    monitor_deployment()