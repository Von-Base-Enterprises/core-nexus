#!/usr/bin/env python3
"""
Monitor Core Nexus authentication deployment fix progress
"""

import urllib.request
import json
import time
import sys

API_URL = "https://core-nexus-memory-service.onrender.com"
TARGET_COMMIT = "783efd1"  # Our authentication fix commit

def check_deployment_status():
    """Check if our fix is deployed"""
    try:
        with urllib.request.urlopen(f"{API_URL}/debug/env") as response:
            env = json.loads(response.read())
            current_commit = env.get('render', {}).get('RENDER_GIT_COMMIT', 'unknown')
            
            print(f"Current commit: {current_commit}")
            print(f"Target commit:  {TARGET_COMMIT}")
            
            if current_commit.startswith(TARGET_COMMIT[:8]):
                print("✅ Fix is deployed!")
                return True
            else:
                print("⏳ Still deploying...")
                return False
    except Exception as e:
        print(f"❌ Error checking deployment: {e}")
        return False

def test_auth_missing_key():
    """Test that missing API key returns 401"""
    req = urllib.request.Request(f"{API_URL}/memories")
    
    try:
        with urllib.request.urlopen(req) as response:
            print(f"❌ Unexpected success: {response.code}")
            return False
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print(f"✅ Missing API key correctly returns 401")
            return True
        elif e.code == 500:
            print(f"❌ Still returning 500 for missing API key")
            return False
        else:
            print(f"⚠️ Unexpected status code: {e.code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_rate_limit_headers():
    """Test that rate limit headers are present"""
    req = urllib.request.Request(
        f"{API_URL}/health",
        headers={'X-API-Key': 'test-key-67890'}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            headers = response.headers
            rate_limit_headers = [h for h in headers.keys() if 'ratelimit' in h.lower()]
            
            if rate_limit_headers:
                print(f"✅ Rate limit headers present: {rate_limit_headers}")
                for h in rate_limit_headers:
                    print(f"   - {h}: {headers[h]}")
                return True
            else:
                print("❌ No rate limit headers found")
                return False
    except Exception as e:
        print(f"❌ Error checking headers: {e}")
        return False

def main():
    print("🚀 MONITORING DEPLOYMENT FIX")
    print("=" * 50)
    
    # Wait for deployment
    max_attempts = 30  # 15 minutes
    for attempt in range(max_attempts):
        print(f"\n📋 Check {attempt + 1}/{max_attempts}")
        
        if check_deployment_status():
            print("\n🎯 TESTING AUTHENTICATION FIXES...")
            
            # Test all fixes
            auth_works = test_auth_missing_key()
            headers_work = test_rate_limit_headers()
            
            if auth_works and headers_work:
                print("\n🎉 ALL AUTHENTICATION FIXES DEPLOYED AND WORKING!")
                print("✅ Missing API keys return 401 (not 500)")
                print("✅ Rate limit headers are present")
                print("✅ Production authentication is fully functional")
                sys.exit(0)
            else:
                print("\n⚠️ Deployment complete but some issues remain")
                
        time.sleep(30)  # Wait 30 seconds
    
    print(f"\n⏰ Timeout after {max_attempts * 30 // 60} minutes")
    print("Deployment may be taking longer than expected")

if __name__ == "__main__":
    main()