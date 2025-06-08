#!/usr/bin/env python3
"""
Core Nexus Keep-Alive Service
Prevents cold starts by pinging the health endpoint
"""

import os
import time
import urllib.request
import urllib.error
import json
from datetime import datetime

class KeepAliveService:
    def __init__(self):
        self.service_url = os.getenv('SERVICE_URL', 'https://core-nexus-memory-service.onrender.com')
        self.health_endpoint = os.getenv('HEALTH_ENDPOINT', '/health')
        self.expected_keyword = os.getenv('EXPECTED_KEYWORD', 'healthy')
        self.timeout = int(os.getenv('TIMEOUT_SECONDS', '30'))
        
    def ping_service(self) -> bool:
        """Ping the service health endpoint"""
        url = f"{self.service_url}{self.health_endpoint}"
        
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'CoreNexus-KeepAlive/1.0'
            })
            
            response = urllib.request.urlopen(req, timeout=self.timeout)
            response_data = response.read().decode('utf-8')
            
            # Check if response contains expected keyword
            if self.expected_keyword in response_data:
                print(f"✅ [{datetime.now().isoformat()}] Service is healthy")
                return True
            else:
                print(f"⚠️ [{datetime.now().isoformat()}] Service responded but not healthy")
                return False
                
        except urllib.error.HTTPError as e:
            print(f"❌ [{datetime.now().isoformat()}] HTTP Error {e.code}: {e.reason}")
            return False
        except urllib.error.URLError as e:
            print(f"❌ [{datetime.now().isoformat()}] Connection Error: {e.reason}")
            return False
        except Exception as e:
            print(f"❌ [{datetime.now().isoformat()}] Unexpected Error: {e}")
            return False
    
    def run_single_check(self):
        """Run a single health check (for Cron Job)"""
        print(f"🚀 Core Nexus Keep-Alive Check - {datetime.now().isoformat()}")
        
        success = self.ping_service()
        
        if success:
            print("💚 Keep-alive successful - service is warm!")
        else:
            print("💔 Keep-alive failed - service may be cold starting")
        
        return success
    
    def run_continuous(self, interval_seconds: int = 300):
        """Run continuous keep-alive (for local development)"""
        print(f"🔄 Starting continuous keep-alive every {interval_seconds}s")
        
        while True:
            self.run_single_check()
            time.sleep(interval_seconds)

def main():
    """Main entry point"""
    service = KeepAliveService()
    
    # For Render Cron Job, run single check
    # For local development, set CONTINUOUS=true
    if os.getenv('CONTINUOUS', '').lower() == 'true':
        interval = int(os.getenv('INTERVAL_SECONDS', '300'))
        service.run_continuous(interval)
    else:
        success = service.run_single_check()
        exit(0 if success else 1)

if __name__ == "__main__":
    main()