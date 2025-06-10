#!/usr/bin/env python3
"""
Core Nexus Memory Service - Code Quality & Completeness Check
Verifies code structure, TODOs, and implementation completeness without external dependencies
"""

import re
import sys
from pathlib import Path


class CodeQualityChecker:
    """Check code quality and completeness without dependencies"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.src_dir = project_root / "src"
        self.issues = []
        self.stats = {
            'total_files': 0,
            'total_lines': 0,
            'todo_count': 0,
            'placeholder_count': 0,
            'function_count': 0,
            'class_count': 0,
            'critical_issues': 0
        }

    def log_issue(self, severity: str, category: str, file_path: str, line_num: int, message: str):
        """Log a code quality issue"""
        self.issues.append({
            'severity': severity,
            'category': category,
            'file': str(file_path),
            'line': line_num,
            'message': message
        })

        if severity == 'CRITICAL':
            self.stats['critical_issues'] += 1

    def check_file_completeness(self, file_path: Path) -> None:
        """Check a single Python file for completeness"""
        try:
            with open(file_path, encoding='utf-8') as f:
                lines = f.readlines()

            self.stats['total_files'] += 1
            self.stats['total_lines'] += len(lines)

            # Check for incomplete patterns
            incomplete_patterns = {
                r'TODO|FIXME|XXX': 'TODO',
                r'NotImplementedError|raise NotImplementedError': 'NOT_IMPLEMENTED',
                r'pass\s*#|pass\s*$': 'PLACEHOLDER_PASS',
                r'coming soon|not implemented|placeholder': 'PLACEHOLDER_TEXT',
                r'your[_-].*[_-](key|token|password|secret)': 'PLACEHOLDER_CREDENTIALS',
                r'def\s+\w+\([^)]*\):\s*pass\s*$': 'EMPTY_FUNCTION'
            }

            for line_num, line in enumerate(lines, 1):
                line_clean = line.strip()

                # Count functions and classes
                if re.match(r'^\s*def\s+', line):
                    self.stats['function_count'] += 1
                elif re.match(r'^\s*class\s+', line):
                    self.stats['class_count'] += 1

                # Check for incomplete patterns
                for pattern, category in incomplete_patterns.items():
                    if re.search(pattern, line, re.IGNORECASE):
                        severity = 'CRITICAL' if category in ['NOT_IMPLEMENTED', 'EMPTY_FUNCTION'] else 'WARNING'
                        self.log_issue(severity, category, file_path, line_num, line_clean)

                        if category == 'TODO':
                            self.stats['todo_count'] += 1
                        elif category in ['PLACEHOLDER_PASS', 'PLACEHOLDER_TEXT', 'PLACEHOLDER_CREDENTIALS']:
                            self.stats['placeholder_count'] += 1

        except Exception as e:
            self.log_issue('ERROR', 'FILE_READ', file_path, 0, f"Failed to read file: {e}")

    def check_api_completeness(self) -> None:
        """Check if API has all claimed endpoints"""
        api_file = self.src_dir / "memory_service" / "api.py"

        if not api_file.exists():
            self.log_issue('CRITICAL', 'MISSING_FILE', api_file, 0, "API file not found")
            return

        try:
            with open(api_file) as f:
                content = f.read()

            # Expected endpoints from documentation
            expected_endpoints = [
                '/health',
                '/memories',
                '/memories/query',
                '/memories/batch',
                '/dashboard/metrics',
                '/dashboard/quality-trends',
                '/dashboard/provider-performance',
                '/dashboard/insights',
                '/adm/performance',
                '/adm/analyze',
                '/analytics/usage',
                '/analytics/export',
                '/analytics/feedback',
                '/providers'
            ]

            missing_endpoints = []
            for endpoint in expected_endpoints:
                # Look for route definition (could be @app.get, @app.post, etc.)
                pattern = rf'@app\.(get|post|put|delete|patch)\(["\'].*{re.escape(endpoint)}.*["\']'
                if not re.search(pattern, content):
                    missing_endpoints.append(endpoint)

            if missing_endpoints:
                self.log_issue('CRITICAL', 'MISSING_ENDPOINTS', api_file, 0,
                             f"Missing API endpoints: {missing_endpoints}")
            else:
                print(f"✅ All {len(expected_endpoints)} expected API endpoints found")

        except Exception as e:
            self.log_issue('ERROR', 'API_CHECK', api_file, 0, f"Failed to check API: {e}")

    def check_docker_completeness(self) -> None:
        """Check Docker configuration completeness"""
        required_files = [
            'Dockerfile',
            'docker-compose.yml',
            'requirements.txt',
            '.env.example',
            'init-db.sql'
        ]

        for filename in required_files:
            file_path = self.project_root / filename
            if not file_path.exists():
                self.log_issue('WARNING', 'MISSING_DOCKER_FILE', file_path, 0,
                             f"Missing Docker file: {filename}")
            else:
                # Check if file has content
                try:
                    if file_path.stat().st_size == 0:
                        self.log_issue('WARNING', 'EMPTY_FILE', file_path, 0, f"Empty file: {filename}")
                except Exception:
                    pass

    def check_provider_implementations(self) -> None:
        """Check that provider classes are properly implemented"""
        providers_file = self.src_dir / "memory_service" / "providers.py"

        if not providers_file.exists():
            self.log_issue('CRITICAL', 'MISSING_PROVIDERS', providers_file, 0, "Providers file not found")
            return

        try:
            with open(providers_file) as f:
                content = f.read()

            # Check for provider classes
            expected_providers = ['PineconeProvider', 'ChromaProvider', 'PgVectorProvider']

            for provider in expected_providers:
                class_pattern = rf'class {provider}\('
                if not re.search(class_pattern, content):
                    self.log_issue('CRITICAL', 'MISSING_PROVIDER_CLASS', providers_file, 0,
                                 f"Missing provider class: {provider}")
                else:
                    # Check if class has required methods
                    required_methods = ['store', 'query', 'health_check', 'get_stats']
                    for method in required_methods:
                        method_pattern = rf'async def {method}\('
                        if not re.search(method_pattern, content):
                            # Check if it's missing or has NotImplementedError
                            if f'def {method}' in content and 'NotImplementedError' in content:
                                self.log_issue('CRITICAL', 'UNIMPLEMENTED_METHOD', providers_file, 0,
                                             f"{provider}.{method} raises NotImplementedError")

        except Exception as e:
            self.log_issue('ERROR', 'PROVIDER_CHECK', providers_file, 0, f"Failed to check providers: {e}")

    def check_adm_implementation(self) -> None:
        """Check ADM scoring implementation"""
        adm_file = self.src_dir / "memory_service" / "adm.py"

        if not adm_file.exists():
            self.log_issue('CRITICAL', 'MISSING_ADM', adm_file, 0, "ADM file not found")
            return

        try:
            with open(adm_file) as f:
                content = f.read()

            # Check for key ADM classes
            expected_classes = [
                'DataQualityAnalyzer',
                'DataRelevanceAnalyzer',
                'DataIntelligenceAnalyzer',
                'ADMScoringEngine'
            ]

            for class_name in expected_classes:
                if f'class {class_name}' not in content:
                    self.log_issue('CRITICAL', 'MISSING_ADM_CLASS', adm_file, 0,
                                 f"Missing ADM class: {class_name}")

            # Check for Darwin-Gödel evolution concepts
            evolution_concepts = ['EvolutionStrategy', 'evolution', 'Darwin', 'Gödel']
            found_concepts = sum(1 for concept in evolution_concepts if concept.lower() in content.lower())

            if found_concepts < 2:
                self.log_issue('WARNING', 'LIMITED_EVOLUTION', adm_file, 0,
                             "Limited Darwin-Gödel evolution implementation")

        except Exception as e:
            self.log_issue('ERROR', 'ADM_CHECK', adm_file, 0, f"Failed to check ADM: {e}")

    def analyze_code_structure(self) -> None:
        """Analyze overall code structure"""
        # Check if all main modules exist
        required_modules = [
            'models.py',
            'unified_store.py',
            'providers.py',
            'adm.py',
            'api.py',
            'dashboard.py',
            'tracking.py',
            'temporal.py'
        ]

        memory_service_dir = self.src_dir / "memory_service"

        if not memory_service_dir.exists():
            self.log_issue('CRITICAL', 'MISSING_MODULE_DIR', memory_service_dir, 0,
                         "memory_service module directory not found")
            return

        for module in required_modules:
            module_path = memory_service_dir / module
            if not module_path.exists():
                self.log_issue('CRITICAL', 'MISSING_MODULE', module_path, 0, f"Missing module: {module}")
            else:
                self.check_file_completeness(module_path)

    def run_comprehensive_check(self) -> bool:
        """Run all checks and return if code is production ready"""
        print("🔍 Core Nexus Memory Service - Code Quality Check")
        print("="*60)

        # Run all checks
        self.analyze_code_structure()
        self.check_api_completeness()
        self.check_docker_completeness()
        self.check_provider_implementations()
        self.check_adm_implementation()

        # Also check main Python files in root
        for py_file in self.project_root.glob("*.py"):
            if py_file.name not in ['comprehensive_verification.py', 'code_quality_check.py']:
                self.check_file_completeness(py_file)

        # Generate report
        self.generate_report()

        # Determine if ready for production
        critical_count = self.stats['critical_issues']
        total_issues = len(self.issues)

        return critical_count == 0 and total_issues < 10

    def generate_report(self) -> None:
        """Generate comprehensive report"""
        print("\n📊 CODE QUALITY REPORT")
        print(f"Files analyzed: {self.stats['total_files']}")
        print(f"Total lines: {self.stats['total_lines']}")
        print(f"Functions found: {self.stats['function_count']}")
        print(f"Classes found: {self.stats['class_count']}")
        print(f"TODO items: {self.stats['todo_count']}")
        print(f"Placeholders: {self.stats['placeholder_count']}")
        print(f"Critical issues: {self.stats['critical_issues']}")

        # Group issues by severity
        critical_issues = [i for i in self.issues if i['severity'] == 'CRITICAL']
        warning_issues = [i for i in self.issues if i['severity'] == 'WARNING']
        error_issues = [i for i in self.issues if i['severity'] == 'ERROR']

        if critical_issues:
            print(f"\n🚨 CRITICAL ISSUES ({len(critical_issues)}):")
            for issue in critical_issues[:10]:  # Show first 10
                print(f"  ❌ {issue['category']}: {issue['message'][:80]}...")
                print(f"     File: {issue['file']}:{issue['line']}")
            if len(critical_issues) > 10:
                print(f"  ... and {len(critical_issues) - 10} more critical issues")

        if warning_issues:
            print(f"\n⚠️  WARNINGS ({len(warning_issues)}):")
            for issue in warning_issues[:5]:  # Show first 5
                print(f"  ⚠️  {issue['category']}: {issue['message'][:80]}...")

        if error_issues:
            print(f"\n❌ ERRORS ({len(error_issues)}):")
            for issue in error_issues:
                print(f"  ❌ {issue['category']}: {issue['message']}")

        print("\n" + "="*60)

        # Final assessment
        if self.stats['critical_issues'] == 0:
            if len(self.issues) == 0:
                print("✅ CODE IS PRODUCTION READY!")
                print("   No critical issues found. Code structure is complete.")
            elif len(self.issues) < 10:
                print("⚠️  MINOR ISSUES - Address before production")
                print("   Code is mostly ready but has some minor issues.")
            else:
                print("❌ TOO MANY ISSUES - Needs cleanup")
                print("   Code has many issues that should be addressed.")
        else:
            print("🚨 NOT PRODUCTION READY - CRITICAL FAILURES")
            print("   Critical issues must be resolved before deployment.")

        # Save detailed report
        report_data = {
            'timestamp': __import__('time').strftime('%Y-%m-%d %H:%M:%S'),
            'stats': self.stats,
            'issues': self.issues,
            'production_ready': self.stats['critical_issues'] == 0 and len(self.issues) < 10
        }

        try:
            import json
            with open(self.project_root / 'code_quality_report.json', 'w') as f:
                json.dump(report_data, f, indent=2)
            print("\n📄 Detailed report saved to: code_quality_report.json")
        except Exception as e:
            print(f"⚠️  Could not save detailed report: {e}")

def main():
    """Run code quality check"""
    project_root = Path(__file__).parent
    checker = CodeQualityChecker(project_root)

    try:
        is_ready = checker.run_comprehensive_check()
        return 0 if is_ready else 1
    except Exception as e:
        print(f"🚨 Code quality check failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
