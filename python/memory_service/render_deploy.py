#!/usr/bin/env python3
"""
Render.com Deployment Script for Core Nexus Memory Service
Deploys the production-ready memory service to Render cloud platform.
"""

import json
import subprocess
import time
import sys
from datetime import datetime
from pathlib import Path

class RenderDeployer:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.render.com/v1"
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        self.project_root = Path(__file__).parent
        
    def log(self, message, level="INFO"):
        """Log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def make_api_request(self, method, endpoint, data=None):
        """Make API request to Render"""
        url = f"{self.base_url}{endpoint}"
        
        curl_cmd = [
            "curl", "--request", method,
            "--url", url,
            "--header", f"Accept: {self.headers['Accept']}",
            "--header", f"Authorization: {self.headers['Authorization']}"
        ]
        
        if data:
            curl_cmd.extend([
                "--header", f"Content-Type: {self.headers['Content-Type']}",
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
                
        except subprocess.TimeoutExpired:
            self.log("API request timed out", "ERROR")
            return {"error": "Request timeout"}
        except Exception as e:
            self.log(f"API request error: {e}", "ERROR")
            return {"error": str(e)}
    
    def check_existing_services(self):
        """Check for existing Core Nexus services"""
        self.log("Checking existing services...")
        
        response = self.make_api_request("GET", "/services?limit=50")
        
        if "error" in response:
            return []
        
        # Look for existing Core Nexus services
        existing_services = []
        services = response if isinstance(response, list) else [response]
        
        for service_data in services:
            if isinstance(service_data, dict) and "service" in service_data:
                service = service_data["service"]
                name = service.get("name", "").lower()
                if "core" in name and "nexus" in name or "memory" in name:
                    existing_services.append(service)
        
        if existing_services:
            self.log(f"Found {len(existing_services)} existing Core Nexus related services")
            for service in existing_services:
                self.log(f"  - {service.get('name')} ({service.get('id')})")
        
        return existing_services
    
    def create_postgresql_database(self):
        """Create PostgreSQL database for the service"""
        self.log("Creating PostgreSQL database...")
        
        db_config = {
            "name": "core-nexus-memory-db",
            "databaseName": "core_nexus_prod",
            "databaseUser": "core_nexus_user", 
            "plan": "starter",  # Free tier
            "region": "oregon",
            "version": "16"  # PostgreSQL 16 with pgvector support
        }
        
        response = self.make_api_request("POST", "/postgres", db_config)
        
        if "error" in response:
            self.log(f"Database creation failed: {response['error']}", "ERROR")
            return None
        
        database_id = response.get("id")
        if database_id:
            self.log(f"✅ Database created successfully: {database_id}")
            return {
                "id": database_id,
                "name": db_config["name"],
                "connection_info": response
            }
        
        return None
    
    def create_web_service(self, database_info=None):
        """Create the Core Nexus Memory Service web service"""
        self.log("Creating Core Nexus Memory Service...")
        
        # Environment variables for production
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
                "value": "2"
            },
            {
                "key": "MAX_CONNECTIONS",
                "value": "500"
            },
            {
                "key": "QUERY_TIMEOUT_MS", 
                "value": "10000"
            },
            {
                "key": "ENABLE_METRICS",
                "value": "true"
            },
            {
                "key": "CORS_ORIGINS",
                "value": "https://core-nexus-memory.onrender.com,http://localhost:3000"
            }
        ]
        
        # Add database connection if provided
        if database_info:
            env_vars.extend([
                {
                    "key": "POSTGRES_HOST",
                    "value": f"{database_info['name']}.internal"
                },
                {
                    "key": "POSTGRES_PORT", 
                    "value": "5432"
                },
                {
                    "key": "POSTGRES_DB",
                    "value": "core_nexus_prod"
                },
                {
                    "key": "POSTGRES_USER",
                    "value": "core_nexus_user"
                }
            ])
        
        service_config = {
            "name": "core-nexus-memory-service",
            "type": "web_service",
            "autoDeploy": "yes",
            "repo": "https://github.com/Von-Base-Enterprises/core-nexus.git",
            "branch": "feat/day1-vertical-slice",
            "rootDir": "python/memory_service",
            "serviceDetails": {
                "plan": "starter",  # Free tier initially
                "runtime": "python",
                "region": "oregon",
                "env": "python",
                "buildCommand": "pip install -r requirements.txt",
                "startCommand": "uvicorn src.memory_service.api:app --host 0.0.0.0 --port $PORT",
                "envSpecificDetails": {
                    "buildCommand": "pip install -r requirements.txt",
                    "startCommand": "uvicorn src.memory_service.api:app --host 0.0.0.0 --port $PORT"
                },
                "envVars": env_vars,
                "healthCheckPath": "/health"
            }
        }
        
        response = self.make_api_request("POST", "/services", service_config)
        
        if "error" in response:
            self.log(f"Service creation failed: {response['error']}", "ERROR")
            return None
        
        service_id = response.get("id")
        if service_id:
            self.log(f"✅ Service created successfully: {service_id}")
            return {
                "id": service_id,
                "name": service_config["name"], 
                "details": response
            }
        
        return None
    
    def wait_for_deployment(self, service_id, timeout_minutes=15):
        """Wait for service deployment to complete"""
        self.log(f"Waiting for deployment to complete (timeout: {timeout_minutes}m)...")
        
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        
        while time.time() - start_time < timeout_seconds:
            response = self.make_api_request("GET", f"/services/{service_id}")
            
            if "error" not in response:
                service = response.get("service", response)
                status = service.get("suspended", "unknown")
                
                if status == "not_suspended":
                    url = service.get("serviceDetails", {}).get("url")
                    if url:
                        self.log(f"✅ Deployment successful! Service URL: {url}")
                        return {
                            "status": "deployed",
                            "url": url,
                            "service_info": service
                        }
                
                self.log(f"Deployment in progress... (status: {status})")
            
            time.sleep(30)  # Check every 30 seconds
        
        self.log("⏰ Deployment timeout reached", "WARNING")
        return {"status": "timeout"}
    
    def verify_service_health(self, service_url):
        """Verify the deployed service is healthy"""
        self.log("Verifying service health...")
        
        health_url = f"{service_url}/health"
        
        try:
            result = subprocess.run([
                "curl", "-s", "-w", "%{http_code}", "-o", "/tmp/health_check", health_url
            ], capture_output=True, text=True, timeout=10)
            
            http_code = result.stdout.strip()
            
            if http_code == "200":
                self.log("✅ Service health check passed!")
                
                # Try to read health response
                try:
                    with open("/tmp/health_check", "r") as f:
                        health_data = json.loads(f.read())
                    
                    self.log(f"Service status: {health_data.get('status')}")
                    self.log(f"Total memories: {health_data.get('total_memories', 0)}")
                    
                    return True
                except:
                    self.log("Health endpoint responded but couldn't parse JSON")
                    return True
            else:
                self.log(f"❌ Health check failed with HTTP {http_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Health check error: {e}", "ERROR")
            return False
    
    def create_deployment_summary(self, database_info, service_info, deployment_result):
        """Create deployment summary report"""
        summary = {
            "deployment_info": {
                "timestamp": datetime.utcnow().isoformat(),
                "platform": "render.com",
                "status": "successful" if deployment_result.get("status") == "deployed" else "failed"
            },
            "database": database_info,
            "service": service_info,
            "deployment_result": deployment_result,
            "access_info": {
                "service_url": deployment_result.get("url"),
                "health_endpoint": f"{deployment_result.get('url')}/health" if deployment_result.get("url") else None,
                "api_docs": f"{deployment_result.get('url')}/docs" if deployment_result.get("url") else None,
                "dashboard_url": service_info.get("details", {}).get("dashboardUrl") if service_info else None
            }
        }
        
        # Save summary
        summary_file = self.project_root / "render_deployment_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        self.log(f"📊 Deployment summary saved to: {summary_file}")
        return summary
    
    def deploy_complete_service(self):
        """Deploy the complete Core Nexus Memory Service to Render"""
        self.log("🚀 Starting Core Nexus Memory Service Deployment to Render.com")
        self.log("=" * 70)
        
        start_time = time.time()
        
        try:
            # Check existing services
            existing_services = self.check_existing_services()
            
            # Create database
            self.log("Step 1: Creating PostgreSQL database...")
            database_info = self.create_postgresql_database()
            
            if not database_info:
                raise Exception("Database creation failed")
            
            # Wait a moment for database to initialize
            self.log("Waiting for database to initialize...")
            time.sleep(10)
            
            # Create web service
            self.log("Step 2: Creating web service...")
            service_info = self.create_web_service(database_info)
            
            if not service_info:
                raise Exception("Service creation failed")
            
            # Wait for deployment
            self.log("Step 3: Waiting for deployment...")
            deployment_result = self.wait_for_deployment(service_info["id"])
            
            if deployment_result.get("status") != "deployed":
                raise Exception("Deployment failed or timed out")
            
            # Verify service health
            self.log("Step 4: Verifying service health...")
            service_url = deployment_result.get("url")
            if service_url:
                # Wait a bit for service to fully start
                time.sleep(30)
                health_ok = self.verify_service_health(service_url)
                
                if not health_ok:
                    self.log("⚠️ Service deployed but health check failed", "WARNING")
            
            # Create summary
            summary = self.create_deployment_summary(database_info, service_info, deployment_result)
            
            duration = time.time() - start_time
            
            self.log("=" * 70)
            self.log(f"🎉 DEPLOYMENT SUCCESSFUL in {duration:.1f}s")
            self.log("")
            self.log("📊 Access Points:")
            self.log(f"  - Service URL: {service_url}")
            self.log(f"  - Health Check: {service_url}/health")
            self.log(f"  - API Docs: {service_url}/docs")
            self.log(f"  - Dashboard: {service_info.get('details', {}).get('dashboardUrl', 'N/A')}")
            self.log("")
            self.log("🎯 Core Nexus Memory Service is now LIVE on Render.com!")
            
            return summary
            
        except Exception as e:
            self.log(f"❌ Deployment failed: {e}", "ERROR")
            return {"error": str(e)}


def main():
    """Main deployment entry point"""
    api_key = "rnd_qmKWEjuHcQ6fddsmXuRxvodE9O4T"
    
    deployer = RenderDeployer(api_key)
    
    try:
        result = deployer.deploy_complete_service()
        
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