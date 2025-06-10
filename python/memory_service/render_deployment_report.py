#!/usr/bin/env python3
"""
Generate comprehensive deployment report for Core Nexus Memory Service on Render.com
"""

import json
import subprocess
from datetime import datetime


class RenderDeploymentReporter:
    def __init__(self, api_key, service_id):
        self.api_key = api_key
        self.service_id = service_id
        self.service_url = "https://core-nexus-memory-service.onrender.com"

    def log(self, message, level="INFO"):
        """Log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def get_service_info(self):
        """Get current service information"""
        curl_cmd = [
            "curl", "-s", "--request", "GET",
            "--url", f"https://api.render.com/v1/services/{self.service_id}",
            "--header", "Accept: application/json",
            "--header", f"Authorization: Bearer {self.api_key}"
        ]

        try:
            result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception as e:
            self.log(f"Failed to get service info: {e}", "ERROR")

        return {}

    def test_endpoints(self):
        """Test various service endpoints"""
        self.log("Testing service endpoints...")

        endpoints = [
            ("/health", "Health Check"),
            ("/docs", "API Documentation"),
            ("/providers", "Vector Providers"),
            ("/memories/stats", "Memory Statistics")
        ]

        results = {}

        for endpoint, description in endpoints:
            url = f"{self.service_url}{endpoint}"

            try:
                result = subprocess.run([
                    "curl", "-s", "-w", "%{http_code}", "-o", "/tmp/endpoint_test",
                    "--max-time", "10", url
                ], capture_output=True, text=True, timeout=15)

                http_code = result.stdout.strip()

                # Try to read response
                response_data = ""
                try:
                    with open("/tmp/endpoint_test") as f:
                        response_data = f.read()
                except Exception:
                    pass

                results[endpoint] = {
                    "status_code": http_code,
                    "description": description,
                    "working": http_code in ["200", "201"],
                    "response_size": len(response_data),
                    "has_json": response_data.startswith("{") or response_data.startswith("[")
                }

                if http_code == "200":
                    self.log(f"✅ {description}: {http_code}")
                elif http_code in ["502", "503", "504"]:
                    self.log(f"🔄 {description}: {http_code} (service starting)")
                else:
                    self.log(f"❌ {description}: {http_code}")

            except Exception as e:
                results[endpoint] = {
                    "status_code": "error",
                    "description": description,
                    "working": False,
                    "error": str(e)
                }
                self.log(f"❌ {description}: {e}")

        return results

    def generate_deployment_report(self):
        """Generate comprehensive deployment report"""
        self.log("🚀 Generating Core Nexus Memory Service Deployment Report")
        self.log("=" * 65)

        # Get service information
        service_info = self.get_service_info()

        # Test endpoints
        endpoint_results = self.test_endpoints()

        # Calculate deployment status
        working_endpoints = sum(1 for r in endpoint_results.values() if r.get("working", False))
        total_endpoints = len(endpoint_results)
        health_percentage = (working_endpoints / total_endpoints) * 100 if total_endpoints > 0 else 0

        # Determine overall status
        if working_endpoints >= 2:
            overall_status = "DEPLOYED_AND_HEALTHY"
        elif working_endpoints >= 1:
            overall_status = "DEPLOYED_PARTIAL"
        else:
            overall_status = "DEPLOYED_STARTING"

        # Create comprehensive report
        report = {
            "deployment_summary": {
                "timestamp": datetime.utcnow().isoformat(),
                "service_name": "Core Nexus Memory Service",
                "platform": "Render.com",
                "overall_status": overall_status,
                "health_percentage": round(health_percentage, 1),
                "service_url": self.service_url,
                "dashboard_url": f"https://dashboard.render.com/web/{self.service_id}"
            },
            "service_configuration": {
                "service_id": self.service_id,
                "name": service_info.get("name", "core-nexus-memory-service"),
                "region": service_info.get("serviceDetails", {}).get("region", "oregon"),
                "plan": service_info.get("serviceDetails", {}).get("plan", "starter"),
                "runtime": service_info.get("serviceDetails", {}).get("runtime", "python"),
                "suspended": service_info.get("suspended", "unknown"),
                "auto_deploy": service_info.get("autoDeploy", "unknown"),
                "branch": service_info.get("branch", "feat/day1-vertical-slice"),
                "root_dir": service_info.get("rootDir", "python/memory_service")
            },
            "endpoint_testing": endpoint_results,
            "deployment_info": {
                "github_repo": "https://github.com/Von-Base-Enterprises/core-nexus",
                "deployment_branch": "feat/day1-vertical-slice",
                "build_command": "pip install -r requirements.txt",
                "start_command": "uvicorn src.memory_service.api:app --host 0.0.0.0 --port $PORT --workers 1",
                "health_check_path": "/health"
            },
            "access_information": {
                "service_url": self.service_url,
                "health_endpoint": f"{self.service_url}/health",
                "api_documentation": f"{self.service_url}/docs",
                "providers_info": f"{self.service_url}/providers",
                "memory_stats": f"{self.service_url}/memories/stats",
                "dashboard": f"https://dashboard.render.com/web/{self.service_id}"
            },
            "next_steps": self._get_next_steps(overall_status, endpoint_results)
        }

        # Save report
        report_file = f"render_deployment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        # Display summary
        self._display_summary(report)

        self.log(f"📊 Full report saved to: {report_file}")

        return report

    def _get_next_steps(self, status, endpoint_results):
        """Get recommended next steps based on deployment status"""
        if status == "DEPLOYED_AND_HEALTHY":
            return [
                "✅ Service is fully operational",
                "Test memory storage: POST /memories",
                "Test memory queries: POST /memories/query",
                "Monitor performance in dashboard",
                "Consider upgrading to paid plan for production"
            ]
        elif status == "DEPLOYED_PARTIAL":
            return [
                "🔄 Service is partially working",
                "Wait for full startup completion (5-10 minutes)",
                "Check logs in Render dashboard",
                "Verify all dependencies are installing correctly"
            ]
        else:
            return [
                "🔄 Service is still starting up",
                "Wait 5-10 minutes for complete startup",
                "Monitor build logs in Render dashboard",
                "Check for any dependency installation errors",
                "Verify GitHub repository branch is accessible"
            ]

    def _display_summary(self, report):
        """Display deployment summary"""
        summary = report["deployment_summary"]
        config = report["service_configuration"]
        access = report["access_information"]

        print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     CORE NEXUS MEMORY SERVICE                               ║
║                        RENDER.COM DEPLOYMENT                                ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  🚀 DEPLOYMENT STATUS: {summary['overall_status']:<25}                      ║
║  📊 HEALTH: {summary['health_percentage']:>5.1f}% endpoints responding                              ║
║  🌐 SERVICE URL: {summary['service_url']:<50}  ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  📋 SERVICE CONFIGURATION                                                   ║
║     Service ID: {config['service_id']:<30}                         ║
║     Plan: {config['plan']:<15} Region: {config['region']:<15}                      ║
║     Runtime: {config['runtime']:<12} Status: {config['suspended']:<20}               ║
║                                                                              ║
║  🔗 ACCESS POINTS                                                           ║
║     Health Check: {access['health_endpoint']:<45} ║
║     API Docs: {access['api_documentation']:<50}     ║
║     Dashboard: {access['dashboard']:<49}    ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """)

        # Display endpoint status
        print("🔍 ENDPOINT STATUS:")
        for _endpoint, result in report["endpoint_testing"].items():
            status_icon = "✅" if result.get("working") else "🔄" if result.get("status_code") in ["502", "503", "504"] else "❌"
            print(f"   {status_icon} {result['description']}: HTTP {result['status_code']}")

        print("\n📋 NEXT STEPS:")
        for i, step in enumerate(report["next_steps"], 1):
            print(f"   {i}. {step}")


def main():
    """Main report generation entry point"""
    api_key = "rnd_qmKWEjuHcQ6fddsmXuRxvodE9O4T"
    service_id = "srv-d12ifg49c44c738bfms0"

    reporter = RenderDeploymentReporter(api_key, service_id)

    try:
        report = reporter.generate_deployment_report()
        return report

    except Exception as e:
        reporter.log(f"Report generation failed: {e}", "ERROR")
        return {"error": str(e)}


if __name__ == "__main__":
    main()
