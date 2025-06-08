#!/usr/bin/env python3
"""
Deployment Monitor for Core Nexus Memory Service
Tracks the deployment progress on Render.com
"""

import time
import urllib.request
import urllib.error
from datetime import datetime

def check_deployment_status():
    """Monitor deployment progress"""
    url = "https://core-nexus-memory-service.onrender.com/health"
    
    print("🔍 Monitoring Core Nexus deployment progress...")
    print(f"📍 Target: {url}")
    print("=" * 60)
    
    attempt = 1
    start_time = time.time()
    
    while True:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'DeploymentMonitor/1.0'})
            response = urllib.request.urlopen(req, timeout=10)
            
            if response.getcode() == 200:
                elapsed = time.time() - start_time
                print(f"\n🎉 SUCCESS! Service is live after {elapsed:.1f}s")
                print(f"✅ Health check returned: {response.getcode()}")
                print(f"🔗 Service URL: https://core-nexus-memory-service.onrender.com")
                print(f"📊 Metrics: https://core-nexus-memory-service.onrender.com/metrics")
                print(f"💾 Database: https://core-nexus-memory-service.onrender.com/db/stats")
                break
            else:
                print(f"⚠️ [{attempt:2d}] Got {response.getcode()}, still deploying...")
                
        except urllib.error.HTTPError as e:
            timestamp = datetime.now().strftime("%H:%M:%S")
            if e.code == 502:
                print(f"🔄 [{attempt:2d}] {timestamp} - Building/Starting (502 Bad Gateway)")
            elif e.code == 503:
                print(f"🚀 [{attempt:2d}] {timestamp} - Service Unavailable (503)")
            else:
                print(f"❓ [{attempt:2d}] {timestamp} - HTTP {e.code}: {e.reason}")
                
        except urllib.error.URLError as e:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"🌐 [{attempt:2d}] {timestamp} - Connection Error: {e.reason}")
            
        except Exception as e:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"⚠️ [{attempt:2d}] {timestamp} - Error: {e}")
        
        # Check if we've been waiting too long
        elapsed = time.time() - start_time
        if elapsed > 600:  # 10 minutes
            print(f"\n⏰ Timeout after {elapsed:.1f}s")
            print("💡 Deployment may be taking longer than expected")
            print("🔗 Check Render dashboard: https://dashboard.render.com")
            break
        
        attempt += 1
        time.sleep(15)  # Check every 15 seconds

if __name__ == "__main__":
    check_deployment_status()