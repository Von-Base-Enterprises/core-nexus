#!/usr/bin/env python3
"""
Monitor Core Nexus deployment and verify the fix is live
"""

import time
import urllib.request
import json
from datetime import datetime

API_URL = "https://core-nexus-memory-service.onrender.com"

def check_deployment_status():
    """Check if the fix has been deployed"""
    try:
        # Test empty query
        data = json.dumps({
            "query": "",
            "limit": 100,
            "min_similarity": 0.0
        }).encode('utf-8')
        
        req = urllib.request.Request(
            f"{API_URL}/memories/query",
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read())
            
            # Check if trust metrics are present (indicates new version)
            has_trust_metrics = 'trust_metrics' in result
            has_fix_applied = result.get('trust_metrics', {}).get('fix_applied', False) if has_trust_metrics else False
            memories_count = len(result.get('memories', []))
            total_found = result.get('total_found', 0)
            
            return {
                'deployed': has_trust_metrics and has_fix_applied,
                'memories_returned': memories_count,
                'total_found': total_found,
                'has_trust_metrics': has_trust_metrics,
                'fix_applied': has_fix_applied
            }
    except Exception as e:
        return {
            'deployed': False,
            'error': str(e)
        }

def main():
    print("🚀 MONITORING CORE NEXUS DEPLOYMENT")
    print("=" * 50)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Checking: {API_URL}")
    print("\nWaiting for deployment to complete...")
    print("(This typically takes 2-5 minutes on Render)")
    
    start_time = time.time()
    check_count = 0
    
    while True:
        check_count += 1
        status = check_deployment_status()
        
        if status.get('deployed'):
            print(f"\n✅ DEPLOYMENT SUCCESSFUL!")
            print(f"Time taken: {int(time.time() - start_time)} seconds")
            print(f"Memories returned: {status['memories_returned']}")
            print(f"Total available: {status['total_found']}")
            print("\n🎉 THE FIX IS LIVE!")
            print("Empty queries now return all memories!")
            break
        else:
            # Show progress
            elapsed = int(time.time() - start_time)
            if 'error' in status:
                print(f"\r⏳ Check #{check_count} ({elapsed}s): Service updating... Error: {status['error'][:50]}", end='')
            else:
                print(f"\r⏳ Check #{check_count} ({elapsed}s): Old version still running (returns {status.get('memories_returned', 0)} memories)", end='')
            
            if elapsed > 600:  # 10 minutes timeout
                print("\n\n⚠️ Deployment is taking longer than expected.")
                print("Check https://dashboard.render.com for deployment status.")
                break
            
            time.sleep(10)  # Check every 10 seconds

if __name__ == "__main__":
    main()