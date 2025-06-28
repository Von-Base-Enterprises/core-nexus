#!/usr/bin/env python3
"""
Comprehensive Test Runner for Core Nexus Memory Service

Executes all test suites with proper configuration and reporting.
Provides detailed test results, coverage reports, and performance metrics.
"""

import os
import sys
import subprocess
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


class ComprehensiveTestRunner:
    """Comprehensive test runner with reporting and analysis."""
    
    def __init__(self):
        self.start_time = time.time()
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "test_suites": {},
            "coverage": {},
            "performance": {},
            "summary": {}
        }
        self.project_root = Path(__file__).parent
    
    def setup_test_environment(self):
        """Set up test environment and dependencies."""
        print("🔧 Setting up test environment...")
        
        # Set environment variables for testing
        os.environ["TESTING"] = "true"
        os.environ["LOG_LEVEL"] = "WARNING"
        os.environ["PYTHONPATH"] = str(self.project_root)
        
        # Ensure test dependencies are available
        try:
            import pytest
            import pytest_asyncio
            import pytest_cov
            import httpx
            print("✅ Test dependencies verified")
        except ImportError as e:
            print(f"❌ Missing test dependency: {e}")
            print("Please install test dependencies: pip install -r requirements.txt")
            sys.exit(1)
    
    def run_test_suite(self, suite_name: str, test_path: str, markers: List[str] = None) -> Dict[str, Any]:
        """Run a specific test suite and capture results."""
        print(f"\n🧪 Running {suite_name}...")
        
        # Build pytest command
        cmd = [
            "python3", "-m", "pytest",
            test_path,
            "--tb=short",
            "--verbose",
            "--json-report",
            f"--json-report-file=test_results_{suite_name.lower()}.json",
            "--cov=src/memory_service",
            f"--cov-report=html:htmlcov_{suite_name.lower()}",
            "--cov-append",  # Append to overall coverage
        ]
        
        # Add markers if specified
        if markers:
            for marker in markers:
                cmd.extend(["-m", marker])
        
        # Add timeout for slow tests
        cmd.extend(["--timeout=300"])
        
        start_time = time.time()
        
        try:
            # Run the test suite
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            execution_time = time.time() - start_time
            
            # Parse results
            suite_results = {
                "execution_time": execution_time,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0
            }
            
            # Try to load JSON report if available
            json_report_file = self.project_root / f"test_results_{suite_name.lower()}.json"
            if json_report_file.exists():
                try:
                    with open(json_report_file, 'r') as f:
                        json_data = json.load(f)
                        suite_results["detailed_results"] = json_data
                except Exception as e:
                    print(f"Warning: Could not parse JSON report for {suite_name}: {e}")
            
            # Print results
            if suite_results["success"]:
                print(f"✅ {suite_name} completed successfully in {execution_time:.2f}s")
            else:
                print(f"❌ {suite_name} failed in {execution_time:.2f}s")
                print(f"Error output: {result.stderr[:500]}...")
            
            return suite_results
            
        except subprocess.TimeoutExpired:
            print(f"⏰ {suite_name} timed out after 10 minutes")
            return {
                "execution_time": 600,
                "return_code": -1,
                "error": "Timeout",
                "success": False
            }
        except Exception as e:
            print(f"💥 {suite_name} crashed: {e}")
            return {
                "execution_time": time.time() - start_time,
                "return_code": -1,
                "error": str(e),
                "success": False
            }
    
    def run_unit_tests(self) -> Dict[str, Any]:
        """Run all unit tests."""
        return self.run_test_suite(
            "Unit_Tests",
            "tests/",
            markers=["unit"]
        )
    
    def run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests."""
        return self.run_test_suite(
            "Integration_Tests", 
            "tests/",
            markers=["integration"]
        )
    
    def run_api_tests(self) -> Dict[str, Any]:
        """Run API endpoint tests."""
        return self.run_test_suite(
            "API_Tests",
            "tests/test_api_endpoints.py",
            markers=["api"]
        )
    
    def run_performance_tests(self) -> Dict[str, Any]:
        """Run performance tests."""
        return self.run_test_suite(
            "Performance_Tests",
            "tests/",
            markers=["performance"]
        )
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests without markers."""
        return self.run_test_suite(
            "All_Tests",
            "tests/"
        )
    
    def generate_coverage_report(self):
        """Generate comprehensive coverage report."""
        print("\n📊 Generating coverage report...")
        
        try:
            # Generate combined coverage report
            cmd = [
                "python3", "-m", "pytest",
                "--cov=src/memory_service",
                "--cov-report=html:htmlcov_combined",
                "--cov-report=xml:coverage.xml",
                "--cov-report=term-missing",
                "tests/"
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✅ Coverage report generated successfully")
                
                # Extract coverage percentage from output
                for line in result.stdout.split('\n'):
                    if 'TOTAL' in line and '%' in line:
                        parts = line.split()
                        for part in parts:
                            if '%' in part:
                                self.test_results["coverage"]["total_percentage"] = part
                                break
                        break
            else:
                print(f"❌ Coverage report generation failed: {result.stderr}")
                
        except Exception as e:
            print(f"💥 Coverage report generation crashed: {e}")
    
    def analyze_performance_metrics(self):
        """Analyze performance test results."""
        print("\n⚡ Analyzing performance metrics...")
        
        performance_summary = {
            "api_response_times": [],
            "database_query_times": [],
            "memory_operations": [],
            "search_operations": []
        }
        
        # Extract performance data from test results
        for suite_name, suite_results in self.test_results["test_suites"].items():
            if "Performance" in suite_name and suite_results.get("detailed_results"):
                # Extract timing data from test results
                detailed = suite_results["detailed_results"]
                if "tests" in detailed:
                    for test in detailed["tests"]:
                        test_name = test.get("nodeid", "")
                        duration = test.get("duration", 0)
                        
                        if "api" in test_name.lower():
                            performance_summary["api_response_times"].append(duration)
                        elif "query" in test_name.lower():
                            performance_summary["database_query_times"].append(duration) 
                        elif "store" in test_name.lower():
                            performance_summary["memory_operations"].append(duration)
                        elif "search" in test_name.lower():
                            performance_summary["search_operations"].append(duration)
        
        # Calculate performance statistics
        for category, times in performance_summary.items():
            if times:
                performance_summary[f"{category}_avg"] = sum(times) / len(times)
                performance_summary[f"{category}_max"] = max(times)
                performance_summary[f"{category}_min"] = min(times)
        
        self.test_results["performance"] = performance_summary
        print("✅ Performance analysis completed")
    
    def generate_summary(self):
        """Generate comprehensive test summary."""
        print("\n📋 Generating test summary...")
        
        total_suites = len(self.test_results["test_suites"])
        successful_suites = sum(1 for suite in self.test_results["test_suites"].values() if suite.get("success", False))
        total_execution_time = time.time() - self.start_time
        
        # Extract test counts from detailed results
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        
        for suite_results in self.test_results["test_suites"].values():
            if suite_results.get("detailed_results") and "summary" in suite_results["detailed_results"]:
                summary = suite_results["detailed_results"]["summary"]
                total_tests += summary.get("total", 0)
                passed_tests += summary.get("passed", 0)
                failed_tests += summary.get("failed", 0)
        
        summary = {
            "total_execution_time": total_execution_time,
            "test_suites": {
                "total": total_suites,
                "successful": successful_suites,
                "failed": total_suites - successful_suites,
                "success_rate": (successful_suites / total_suites * 100) if total_suites > 0 else 0
            },
            "individual_tests": {
                "total": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0
            },
            "coverage_percentage": self.test_results["coverage"].get("total_percentage", "Unknown"),
            "overall_status": "PASS" if successful_suites == total_suites and failed_tests == 0 else "FAIL"
        }
        
        self.test_results["summary"] = summary
        print("✅ Test summary generated")
    
    def save_results(self):
        """Save comprehensive test results to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = self.project_root / f"comprehensive_test_results_{timestamp}.json"
        
        try:
            with open(results_file, 'w') as f:
                json.dump(self.test_results, f, indent=2, default=str)
            print(f"📁 Test results saved to: {results_file}")
        except Exception as e:
            print(f"❌ Failed to save results: {e}")
    
    def print_final_report(self):
        """Print comprehensive final report."""
        print("\n" + "=" * 80)
        print("🧪 CORE NEXUS MEMORY SERVICE - COMPREHENSIVE TEST REPORT")
        print("=" * 80)
        
        summary = self.test_results["summary"]
        
        print(f"\n⏱️  EXECUTION TIME: {summary['total_execution_time']:.2f} seconds")
        print(f"🎯 OVERALL STATUS: {summary['overall_status']}")
        
        print(f"\n📊 TEST SUITES:")
        print(f"   Total: {summary['test_suites']['total']}")
        print(f"   Successful: {summary['test_suites']['successful']}")
        print(f"   Failed: {summary['test_suites']['failed']}")
        print(f"   Success Rate: {summary['test_suites']['success_rate']:.1f}%")
        
        print(f"\n🧪 INDIVIDUAL TESTS:")
        print(f"   Total: {summary['individual_tests']['total']}")
        print(f"   Passed: {summary['individual_tests']['passed']}")
        print(f"   Failed: {summary['individual_tests']['failed']}")
        print(f"   Success Rate: {summary['individual_tests']['success_rate']:.1f}%")
        
        print(f"\n📈 CODE COVERAGE:")
        print(f"   Coverage: {summary['coverage_percentage']}")
        
        # Performance summary
        if self.test_results["performance"]:
            print(f"\n⚡ PERFORMANCE SUMMARY:")
            perf = self.test_results["performance"]
            if "api_response_times_avg" in perf:
                print(f"   Avg API Response: {perf['api_response_times_avg']:.3f}s")
            if "database_query_times_avg" in perf:
                print(f"   Avg DB Query: {perf['database_query_times_avg']:.3f}s")
        
        # Suite-by-suite breakdown
        print(f"\n📋 SUITE BREAKDOWN:")
        for suite_name, suite_results in self.test_results["test_suites"].items():
            status = "✅ PASS" if suite_results.get("success") else "❌ FAIL"
            time_taken = suite_results.get("execution_time", 0)
            print(f"   {suite_name}: {status} ({time_taken:.2f}s)")
        
        print("\n" + "=" * 80)
        
        if summary["overall_status"] == "PASS":
            print("🎉 ALL TESTS PASSED! Core Nexus is ready for production.")
        else:
            print("⚠️  SOME TESTS FAILED. Review failures before deployment.")
        
        print("=" * 80)
    
    def run_comprehensive_tests(self):
        """Run all test suites comprehensively."""
        print("🚀 Starting Comprehensive Test Suite for Core Nexus Memory Service")
        print("=" * 80)
        
        # Setup
        self.setup_test_environment()
        
        # Run test suites
        print("\n📝 Running test suites...")
        
        self.test_results["test_suites"]["unit_tests"] = self.run_unit_tests()
        self.test_results["test_suites"]["integration_tests"] = self.run_integration_tests()
        self.test_results["test_suites"]["api_tests"] = self.run_api_tests()
        self.test_results["test_suites"]["performance_tests"] = self.run_performance_tests()
        
        # If individual suites had issues, try running all together
        if any(not suite.get("success", False) for suite in self.test_results["test_suites"].values()):
            print("\n🔄 Some individual suites failed, running all tests together...")
            self.test_results["test_suites"]["all_tests_fallback"] = self.run_all_tests()
        
        # Generate reports
        self.generate_coverage_report()
        self.analyze_performance_metrics()
        self.generate_summary()
        
        # Save and display results
        self.save_results()
        self.print_final_report()
        
        # Return exit code based on results
        return 0 if self.test_results["summary"]["overall_status"] == "PASS" else 1


def main():
    """Main entry point for comprehensive testing."""
    runner = ComprehensiveTestRunner()
    
    try:
        exit_code = runner.run_comprehensive_tests()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Testing failed with unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()