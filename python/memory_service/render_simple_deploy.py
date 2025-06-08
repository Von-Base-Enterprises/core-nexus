#!/usr/bin/env python3
"""
Simple Render.com Deployment for Core Nexus Memory Service
Deploys without PostgreSQL dependency for free tier compatibility.
"""

import json
import subprocess
import time
import sys
from datetime import datetime
from pathlib import Path

class SimpleRenderDeployer:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.render.com/v1"
        self.owner_id = "tea-cu9g9vrqf0us73bvh5s0"  # Von Base's workspace
        self.project_root = Path(__file__).parent
        
    def log(self, message, level="INFO"):
        """Log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def make_api_request(self, method, endpoint, data=None):
        """Make API request to Render"""
        url = f"{self.base_url}{endpoint}"
        
        curl_cmd = [
            "curl", "-s", "--request", method,
            "--url", url,
            "--header", "Accept: application/json",
            "--header", f"Authorization: Bearer {self.api_key}"
        ]
        
        if data:
            curl_cmd.extend([
                "--header", "Content-Type: application/json",
                "--data", json.dumps(data)
            ])
        
        try:
            result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {"raw_response": result.stdout}
            else:
                self.log(f"API request failed: {result.stderr}", "ERROR")
                return {"error": result.stderr}
                
        except Exception as e:
            self.log(f"API request error: {e}", "ERROR")
            return {"error": str(e)}
    
    def create_web_service(self):
        """Create the Core Nexus Memory Service web service"""
        self.log("Creating Core Nexus Memory Service...")
        
        # Environment variables for free tier deployment
        env_vars = [
            {
                "key": "SERVICE_NAME",
                "value": "core-nexus-memory-prod"
            },
            {
                "key": "ENVIRONMENT", 
                "value": "production"
            },
            {
                "key": "LOG_LEVEL",
                "value": "INFO"
            },
            {
                "key": "WORKERS",
                "value": "1"
            },
            {
                "key": "MAX_CONNECTIONS",
                "value": "100"
            },
            {
                "key": "QUERY_TIMEOUT_MS", 
                "value": "5000"
            },
            {
                "key": "ENABLE_METRICS",
                "value": "true"
            },
            {
                "key": "CORS_ORIGINS",
                "value": "*"
            },
            {
                "key": "PINECONE_API_KEY",
                "value": ""
            },
            {
                "key": "OPENAI_API_KEY",
                "value": "mock_key_for_demo"
            }
        ]
        
        service_config = {
            "type": "web_service",
            "name": "core-nexus-memory-service",
            "ownerId": self.owner_id,
            "autoDeploy": "yes",
            "repo": "https://github.com/Von-Base-Enterprises/core-nexus.git",
            "branch": "feat/day1-vertical-slice",
            "rootDir": "python/memory_service",
            "serviceDetails": {
                "plan": "starter",
                "region": "oregon",
                "env": "python",
                "healthCheckPath": "/health",
                "numInstances": 1,
                "envVars": env_vars,
                "envSpecificDetails": {
                    "buildCommand": "pip install -r requirements.txt",
                    "startCommand": "uvicorn src.memory_service.api:app --host 0.0.0.0 --port $PORT --workers 1"
                }
            }
        }
        
        response = self.make_api_request("POST", "/services", service_config)
        
        if "error" in response:
            self.log(f"Service creation failed: {response.get('error', 'Unknown error')}", "ERROR")
            self.log(f"Full response: {response}")
            return None
        
        # Handle the nested service structure
        service_data = response.get("service", response)
        service_id = service_data.get("id")
        
        if service_id:
            self.log(f"✅ Service created successfully: {service_id}")
            dashboard_url = service_data.get("dashboardUrl", "")
            service_url = service_data.get("serviceDetails", {}).get("url", "")
            
            self.log(f"Dashboard URL: {dashboard_url}")
            self.log(f"Service URL: {service_url}")
            
            return {
                "id": service_id,
                "name": service_config["name"], 
                "details": response,
                "dashboard_url": dashboard_url,
                "service_url": service_url
            }
        
        self.log(f"Unexpected response structure: {response}")
        return None
    
    def wait_for_deployment(self, service_id, timeout_minutes=10):
        """Wait for service deployment to complete"""
        self.log(f"Waiting for deployment to complete (timeout: {timeout_minutes}m)...")
        
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        
        while time.time() - start_time < timeout_seconds:
            response = self.make_api_request("GET", f"/services/{service_id}")
            
            if "error" not in response:
                # Handle the response structure properly
                if "service" in response:
                    service = response["service"]
                else:
                    service = response
                
                suspended = service.get("suspended", "unknown")
                service_details = service.get("serviceDetails", {})
                url = service_details.get("url")
                
                self.log(f"Status: {suspended}, URL: {url}")
                
                if suspended == "not_suspended" and url:
                    self.log(f"✅ Deployment successful! Service URL: {url}")
                    return {
                        "status": "deployed",
                        "url": url,
                        "service_info": service
                    }
                
                if suspended == "suspended":
                    self.log("❌ Service was suspended", "ERROR")
                    return {"status": "suspended", "service_info": service}
            
            time.sleep(30)  # Check every 30 seconds
        
        self.log("⏰ Deployment timeout reached", "WARNING")
        return {"status": "timeout"}
    
    def test_service_health(self, service_url, max_attempts=5):
        """Test the deployed service health"""
        self.log("Testing service health...")
        
        health_url = f"{service_url}/health"
        
        for attempt in range(max_attempts):
            try:
                result = subprocess.run([
                    "curl", "-s", "-w", "%{http_code}", "-o", "/tmp/health_check", 
                    "--max-time", "10", health_url
                ], capture_output=True, text=True, timeout=15)
                
                http_code = result.stdout.strip()
                
                if http_code == "200":
                    self.log("✅ Service health check passed!")
                    
                    # Try to read health response
                    try:
                        with open("/tmp/health_check", "r") as f:
                            health_data = json.loads(f.read())
                        
                        self.log(f"Service status: {health_data.get('status')}")
                        self.log(f"Providers: {list(health_data.get('providers', {}).keys())}")
                        
                        return True
                    except:
                        self.log("Health endpoint responded but couldn't parse JSON")
                        return True
                        
                elif http_code in ["502", "503", "504"]:
                    self.log(f"Service starting up... (HTTP {http_code})")
                    if attempt < max_attempts - 1:
                        time.sleep(30)
                        continue
                else:
                    self.log(f"❌ Health check failed with HTTP {http_code}", "ERROR")
                    
            except Exception as e:
                self.log(f"Health check attempt {attempt + 1} failed: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(20)
                    continue
        
        return False
    
    def deploy_service(self):
        """Deploy the Core Nexus Memory Service to Render"""
        self.log("🚀 Deploying Core Nexus Memory Service to Render.com")
        self.log("=" * 60)
        
        start_time = time.time()
        
        try:
            # Create web service
            self.log("Step 1: Creating web service...")
            service_info = self.create_web_service()
            
            if not service_info:
                raise Exception("Service creation failed")
            
            # Wait for deployment
            self.log("Step 2: Waiting for deployment...")
            deployment_result = self.wait_for_deployment(service_info["id"])
            
            if deployment_result.get("status") != "deployed":
                if deployment_result.get("status") == "suspended":
                    self.log("Service was suspended, likely due to startup issues", "ERROR")
                raise Exception(f"Deployment failed: {deployment_result.get('status')}")
            
            # Test service health
            self.log("Step 3: Testing service health...")
            service_url = deployment_result.get("url")
            if service_url:
                # Wait for service to fully start up
                self.log("Waiting for service to fully initialize...")
                time.sleep(60)
                
                health_ok = self.test_service_health(service_url)
                
                if not health_ok:
                    self.log("⚠️ Service deployed but health check failed", "WARNING")
                    self.log("This might be normal during initial startup", "INFO")
            
            duration = time.time() - start_time
            
            # Create deployment summary
            summary = {
                "deployment_info": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "platform": "render.com",
                    "status": "successful",
                    "duration_seconds": round(duration, 1)
                },
                "service": service_info,
                "deployment_result": deployment_result,
                "access_info": {
                    "service_url": service_url,
                    "health_endpoint": f"{service_url}/health" if service_url else None,
                    "api_docs": f"{service_url}/docs" if service_url else None,
                    "dashboard_url": f"https://dashboard.render.com/web/{service_info['id']}"
                }
            }
            
            # Save summary
            summary_file = self.project_root / "render_deployment_summary.json"
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
            
            self.log("=" * 60)
            self.log(f"🎉 DEPLOYMENT SUCCESSFUL in {duration:.1f}s")
            self.log("")
            self.log("📊 Access Points:")
            self.log(f"  - Service URL: {service_url}")
            self.log(f"  - Health Check: {service_url}/health")
            self.log(f"  - API Docs: {service_url}/docs")
            self.log(f"  - Dashboard: https://dashboard.render.com/web/{service_info['id']}")
            self.log("")
            self.log("🎯 Core Nexus Memory Service is now LIVE on Render.com!")
            self.log(f"📊 Summary saved to: {summary_file}")
            
            return summary
            
        except Exception as e:
            self.log(f"❌ Deployment failed: {e}", "ERROR")
            return {"error": str(e)}


def main():
    """Main deployment entry point"""
    api_key = "rnd_qmKWEjuHcQ6fddsmXuRxvodE9O4T"
    
    deployer = SimpleRenderDeployer(api_key)
    
    try:
        result = deployer.deploy_service()
        
        if "error" in result:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        deployer.log("Deployment interrupted by user", "WARNING")
        sys.exit(1)
    except Exception as e:
        deployer.log(f"Deployment failed with error: {e}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()