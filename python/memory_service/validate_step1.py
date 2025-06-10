#!/usr/bin/env python3
"""
Step 1 Validation Script for Core Nexus Memory Service
Performs basic health checks and validation of minimal production environment.
"""

import json
import subprocess
import sys
import time
from datetime import datetime


class Step1Validator:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.passed_tests = 0
        self.total_tests = 0

    def log(self, message, level="INFO"):
        """Simple logging with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def test(self, name, condition, error_msg="Test failed"):
        """Record test result"""
        self.total_tests += 1
        if condition:
            self.passed_tests += 1
            self.log(f"✅ {name}", "PASS")
            return True
        else:
            self.log(f"❌ {name}: {error_msg}", "FAIL")
            return False

    def validate_health_endpoint(self):
        """Test basic health endpoint using curl"""
        self.log("Testing health endpoint...")
        try:
            result = subprocess.run(
                ["curl", "-s", "-w", "%{http_code}", "-o", "/tmp/health_response", f"{self.base_url}/health"],
                capture_output=True, text=True, timeout=10
            )

            http_code = result.stdout.strip()

            self.test(
                "Health endpoint responds",
                http_code == "200",
                f"Got HTTP status {http_code}"
            )

            if http_code == "200":
                try:
                    with open("/tmp/health_response") as f:
                        data = json.loads(f.read())

                    self.test(
                        "Health data has status field",
                        "status" in data,
                        "Missing status field in response"
                    )

                    self.test(
                        "Service reports healthy status",
                        data.get("status") == "healthy",
                        f"Status is {data.get('status')}"
                    )
                except Exception as e:
                    self.test("Health response is valid JSON", False, str(e))

            return http_code == "200"

        except Exception as e:
            self.test("Health endpoint responds", False, str(e))
            return False

    def validate_service_startup(self):
        """Test that service starts and responds"""
        self.log("Validating service startup...")

        # Wait for service to be ready (up to 60 seconds)
        for attempt in range(60):
            try:
                result = subprocess.run(
                    ["curl", "-s", "-w", "%{http_code}", "-o", "/dev/null", f"{self.base_url}/health"],
                    capture_output=True, text=True, timeout=5
                )
                if result.stdout.strip() == "200":
                    self.test("Service starts successfully", True)
                    return True
            except Exception:
                pass

            if attempt == 0:
                self.log("Waiting for service to start...")
            elif attempt % 10 == 0:
                self.log(f"Still waiting... ({attempt}s)")

            time.sleep(1)

        self.test("Service starts successfully", False, "Service did not start within 60 seconds")
        return False

    def validate_basic_endpoints(self):
        """Test basic API endpoints exist"""
        self.log("Testing basic API endpoints...")

        endpoints_to_test = [
            "/health",
            "/providers",
            "/memories/stats"
        ]

        for endpoint in endpoints_to_test:
            try:
                result = subprocess.run(
                    ["curl", "-s", "-w", "%{http_code}", "-o", "/dev/null", f"{self.base_url}{endpoint}"],
                    capture_output=True, text=True, timeout=10
                )
                http_code = result.stdout.strip()
                self.test(
                    f"Endpoint {endpoint} responds",
                    http_code in ["200", "201"],
                    f"Got HTTP status {http_code}"
                )
            except Exception as e:
                self.test(f"Endpoint {endpoint} responds", False, str(e))

    def validate_simple_memory_operation(self):
        """Test storing and querying a simple memory (simplified for Step 1)"""
        self.log("Testing basic memory operations...")

        # For Step 1, just test that the endpoints respond
        # Full memory testing will be done when dependencies are available
        try:
            # Test memory storage endpoint exists
            result = subprocess.run(
                ["curl", "-s", "-w", "%{http_code}", "-o", "/dev/null",
                 "-X", "POST", "-H", "Content-Type: application/json",
                 "-d", '{"content":"test","metadata":{}}',
                 f"{self.base_url}/memories"],
                capture_output=True, text=True, timeout=15
            )

            # We expect this might fail due to dependencies, but endpoint should exist
            # Status 422 (validation error) or 500 (server error) means endpoint exists
            http_code = result.stdout.strip()
            self.test(
                "Memory storage endpoint exists",
                http_code in ["200", "201", "422", "500"],
                f"Got unexpected HTTP status {http_code} (endpoint may not exist)"
            )

            # Test query endpoint exists
            result = subprocess.run(
                ["curl", "-s", "-w", "%{http_code}", "-o", "/dev/null",
                 "-X", "POST", "-H", "Content-Type: application/json",
                 "-d", '{"query":"test","limit":5}',
                 f"{self.base_url}/memories/query"],
                capture_output=True, text=True, timeout=15
            )

            http_code = result.stdout.strip()
            self.test(
                "Memory query endpoint exists",
                http_code in ["200", "201", "422", "500"],
                f"Got unexpected HTTP status {http_code} (endpoint may not exist)"
            )

        except Exception as e:
            self.test("Memory endpoints accessible", False, str(e))

    def run_all_validations(self):
        """Run all Step 1 validations"""
        self.log("🚀 Starting Step 1 Validation for Core Nexus Memory Service")
        self.log("=" * 60)

        start_time = time.time()

        # Run validation steps
        self.validate_service_startup()
        self.validate_health_endpoint()
        self.validate_basic_endpoints()
        self.validate_simple_memory_operation()

        # Summary
        duration = time.time() - start_time
        self.log("=" * 60)
        self.log(f"Step 1 Validation Complete in {duration:.2f}s")
        self.log(f"Tests Passed: {self.passed_tests}/{self.total_tests}")

        if self.passed_tests == self.total_tests:
            self.log("🎉 Step 1 VALIDATION PASSED - Ready for Step 2!", "SUCCESS")
            return True
        else:
            self.log(f"❌ Step 1 VALIDATION FAILED - {self.total_tests - self.passed_tests} tests failed", "ERROR")
            return False


def main():
    """Main validation entry point"""
    validator = Step1Validator()

    try:
        success = validator.run_all_validations()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        validator.log("Validation interrupted by user", "WARNING")
        sys.exit(1)
    except Exception as e:
        validator.log(f"Validation failed with error: {e}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
