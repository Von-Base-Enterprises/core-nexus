#!/usr/bin/env python3
"""Quick check for ADK deployment status."""

import requests
import json
import time

API_KEY = "test-key-67890"
BASE_URL = "https://core-nexus-memory-service.onrender.com"

print("Checking ADK deployment status...")
print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("-" * 50)

# Check health
try:
    response = requests.get(f"{BASE_URL}/health", headers={"X-API-Key": API_KEY})
    if response.status_code == 200:
        data = response.json()
        uptime_hours = data.get("uptime_seconds", 0) / 3600
        print(f"✅ Service healthy (uptime: {uptime_hours:.1f} hours)")
    else:
        print(f"❌ Health check failed: {response.status_code}")
except Exception as e:
    print(f"❌ Error checking health: {e}")

# Check ADK endpoint
try:
    response = requests.get(f"{BASE_URL}/test/adk", headers={"X-API-Key": API_KEY})
    if response.status_code == 200:
        print("\n✅ ADK endpoint available!")
        data = response.json()
        print(json.dumps(data, indent=2))
    elif response.status_code == 404:
        print("\n⏳ ADK endpoint not deployed yet (404)")
        print("   Render is likely still building...")
    else:
        print(f"\n❌ ADK endpoint returned: {response.status_code}")
        print(f"   Response: {response.text}")
except Exception as e:
    print(f"\n❌ Error checking ADK: {e}")

print("\n" + "-" * 50)
print("Note: It typically takes 5-15 minutes for Render to rebuild")
print("after pushing changes. Check https://dashboard.render.com")