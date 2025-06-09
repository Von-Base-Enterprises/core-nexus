#!/usr/bin/env python3
"""
Test runner for Knowledge Graph tests.

Runs all graph-related tests and generates a comprehensive report.
"""

import sys
import os
import time
import subprocess
import json
from datetime import datetime
from pathlib import Path


class TestRunner:
    """Runs tests and collects results."""
    
    def __init__(self):
        self.results = {
            'timestamp': datetime.utcnow().isoformat(),
            'tests': {},
            'summary': {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'skipped': 0
            }
        }
    
    def run_test_file(self, test_file: str) -> dict:
        """Run a single test file and collect results."""
        print(f"\n{'='*60}")
        print(f"Running: {test_file}")
        print('='*60)
        
        start_time = time.time()
        
        try:
            # Run pytest with JSON output
            cmd = [
                sys.executable, '-m', 'pytest',
                test_file,
                '-v',
                '--tb=short',
                '--no-header',
                '-q'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            duration = time.time() - start_time
            
            # Parse output
            output_lines = result.stdout.strip().split('\n')
            passed = sum(1 for line in output_lines if '::' in line and 'PASSED' in line)
            failed = sum(1 for line in output_lines if '::' in line and 'FAILED' in line)
            skipped = sum(1 for line in output_lines if '::' in line and 'SKIPPED' in line)
            
            test_result = {
                'file': test_file,
                'duration': duration,
                'passed': passed,
                'failed': failed,
                'skipped': skipped,
                'return_code': result.returncode,
                'output': result.stdout,
                'errors': result.stderr
            }
            
            # Update summary
            self.results['summary']['total'] += passed + failed + skipped
            self.results['summary']['passed'] += passed
            self.results['summary']['failed'] += failed
            self.results['summary']['skipped'] += skipped
            
            return test_result
            
        except subprocess.TimeoutExpired:
            return {
                'file': test_file,
                'duration': 300,
                'error': 'Test timed out after 5 minutes',
                'failed': 1
            }
        except Exception as e:
            return {
                'file': test_file,
                'duration': time.time() - start_time,
                'error': str(e),
                'failed': 1
            }
    
    def run_all_tests(self):
        """Run all graph tests."""
        test_dir = Path(__file__).parent / 'tests'
        test_files = [
            'tests/test_graph_provider.py',
            'tests/test_graph_integration.py',
            'tests/test_graph_performance.py'
        ]
        
        print("Knowledge Graph Test Suite")
        print(f"Running {len(test_files)} test files...")
        
        for test_file in test_files:
            if os.path.exists(test_file):
                result = self.run_test_file(test_file)
                self.results['tests'][test_file] = result
            else:
                print(f"Warning: Test file not found: {test_file}")
                self.results['tests'][test_file] = {
                    'error': 'File not found',
                    'failed': 1
                }
        
        self.print_summary()
        self.save_report()
    
    def print_summary(self):
        """Print test summary."""
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print('='*60)
        
        summary = self.results['summary']
        total = summary['total']
        
        if total > 0:
            pass_rate = (summary['passed'] / total) * 100
            print(f"Total tests: {total}")
            print(f"Passed: {summary['passed']} ({pass_rate:.1f}%)")
            print(f"Failed: {summary['failed']}")
            print(f"Skipped: {summary['skipped']}")
        else:
            print("No tests were run.")
        
        print("\nTest File Results:")
        for test_file, result in self.results['tests'].items():
            status = "✓" if result.get('failed', 0) == 0 else "✗"
            duration = result.get('duration', 0)
            print(f"  {status} {test_file}: {duration:.2f}s")
            
            if 'error' in result:
                print(f"     Error: {result['error']}")
    
    def save_report(self):
        """Save detailed test report."""
        report_file = 'test_report_graph.json'
        
        try:
            with open(report_file, 'w') as f:
                json.dump(self.results, f, indent=2)
            print(f"\nDetailed report saved to: {report_file}")
        except Exception as e:
            print(f"Failed to save report: {e}")


def check_dependencies():
    """Check if required dependencies are available."""
    print("Checking dependencies...")
    
    dependencies = {
        'pytest': 'pip install pytest',
        'asyncio': 'Built-in',
    }
    
    missing = []
    
    for package, install_cmd in dependencies.items():
        try:
            __import__(package)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} - Install with: {install_cmd}")
            missing.append(package)
    
    # Check optional dependencies
    optional = ['spacy', 'sentence_transformers']
    for package in optional:
        try:
            __import__(package)
            print(f"  ✓ {package} (optional)")
        except ImportError:
            print(f"  ⚠ {package} (optional) - Not installed")
    
    if missing:
        print(f"\nError: Missing required dependencies: {', '.join(missing)}")
        return False
    
    return True


def setup_test_environment():
    """Set up test environment."""
    # Add parent directory to path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Set environment variables for testing
    os.environ['TESTING'] = 'true'
    os.environ['LOG_LEVEL'] = 'WARNING'  # Reduce log noise during tests


def main():
    """Main test runner entry point."""
    print("Core Nexus Knowledge Graph - Test Suite")
    print("=" * 60)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Setup environment
    setup_test_environment()
    
    # Run tests
    runner = TestRunner()
    runner.run_all_tests()
    
    # Exit with appropriate code
    if runner.results['summary']['failed'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()