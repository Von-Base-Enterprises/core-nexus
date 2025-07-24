#!/usr/bin/env python3
"""
Performance Regression Check for Core Nexus

This script checks if current performance metrics are within acceptable bounds.
Used in CI/CD to prevent performance regressions.
"""

import json
import sys
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PerformanceChecker:
    def __init__(self, baseline_file="simple_baseline_data.json"):
        self.baseline_file = baseline_file
        self.thresholds = {
            "latency_p50_max": 200,      # P50 should be < 200ms
            "latency_p95_max": 400,      # P95 should be < 400ms
            "latency_mean_max": 150,     # Mean should be < 150ms
            "min_recall": 0.95,          # Recall should be > 95%
            "probes_expected": 3,        # Probes should be set to 3
            "max_latency_increase": 1.2  # Allow 20% degradation from baseline
        }
        
    def load_baseline(self):
        """Load baseline metrics from file."""
        try:
            with open(self.baseline_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Baseline file not found: {self.baseline_file}")
            return None
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in baseline file: {self.baseline_file}")
            return None
    
    def check_latency(self, metrics):
        """Check if latency metrics are within bounds."""
        issues = []
        
        api_metrics = metrics.get('api_metrics', {})
        latency = api_metrics.get('latency', {})
        
        # Check absolute thresholds
        if latency.get('mean', 0) > self.thresholds['latency_mean_max']:
            issues.append(f"Mean latency {latency['mean']:.0f}ms exceeds threshold {self.thresholds['latency_mean_max']}ms")
        
        if latency.get('p50', 0) > self.thresholds['latency_p50_max']:
            issues.append(f"P50 latency {latency['p50']:.0f}ms exceeds threshold {self.thresholds['latency_p50_max']}ms")
        
        if latency.get('p95', 0) > self.thresholds['latency_p95_max']:
            issues.append(f"P95 latency {latency['p95']:.0f}ms exceeds threshold {self.thresholds['latency_p95_max']}ms")
        
        return issues
    
    def check_probes(self, metrics):
        """Check if probes configuration is correct."""
        issues = []
        
        db_stats = metrics.get('db_stats', {})
        current_probes = db_stats.get('current_probes', 1)
        
        if current_probes != self.thresholds['probes_expected']:
            issues.append(f"Probes set to {current_probes}, expected {self.thresholds['probes_expected']}")
        
        # Also check probes test results
        probes_results = metrics.get('probes_results', {})
        if probes_results:
            # Check if optimal probes (2-3) have good latency
            for probes in [2, 3]:
                if probes in probes_results:
                    avg_latency = probes_results[probes].get('avg_latency_ms', 0)
                    if avg_latency > 150:
                        issues.append(f"Probes={probes} latency {avg_latency:.0f}ms is too high")
        
        return issues
    
    def check_recall(self, recall_file="simple_recall_results.json"):
        """Check if recall metrics are acceptable."""
        issues = []
        
        try:
            with open(recall_file, 'r') as f:
                recall_data = json.load(f)
            
            single_test = recall_data.get('single_query_test', {})
            multi_test = recall_data.get('multi_query_test', {})
            
            # Check single query recall
            if single_test.get('recall', 0) < self.thresholds['min_recall']:
                issues.append(f"Single query recall {single_test['recall']:.1%} below threshold {self.thresholds['min_recall']:.1%}")
            
            # Check multi query average recall
            if multi_test.get('avg_recall', 0) < self.thresholds['min_recall']:
                issues.append(f"Average recall {multi_test['avg_recall']:.1%} below threshold {self.thresholds['min_recall']:.1%}")
            
        except FileNotFoundError:
            logger.warning(f"Recall results file not found: {recall_file}")
        except Exception as e:
            logger.error(f"Error checking recall: {e}")
        
        return issues
    
    def generate_report(self, metrics, issues):
        """Generate performance check report."""
        report = f"""
# 🔍 Performance Regression Check Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Status: {'❌ FAILED' if issues else '✅ PASSED'}

"""
        
        if metrics:
            api_metrics = metrics.get('api_metrics', {})
            latency = api_metrics.get('latency', {})
            db_stats = metrics.get('db_stats', {})
            
            report += f"""## Current Metrics
- Mean latency: {latency.get('mean', 0):.0f}ms
- P50 latency: {latency.get('p50', 0):.0f}ms  
- P95 latency: {latency.get('p95', 0):.0f}ms
- Probes setting: {db_stats.get('current_probes', 'unknown')}
- Total memories: {db_stats.get('total_memories', 0):,}

"""
        
        if issues:
            report += "## Issues Found\n"
            for issue in issues:
                report += f"- ❌ {issue}\n"
        else:
            report += "## All Checks Passed\n"
            report += "- ✅ Latency within acceptable bounds\n"
            report += "- ✅ Probes configuration correct\n"
            report += "- ✅ Recall meets requirements\n"
        
        report += f"""
## Thresholds
- Max mean latency: {self.thresholds['latency_mean_max']}ms
- Max P50 latency: {self.thresholds['latency_p50_max']}ms
- Max P95 latency: {self.thresholds['latency_p95_max']}ms
- Min recall: {self.thresholds['min_recall']:.1%}
- Expected probes: {self.thresholds['probes_expected']}
"""
        
        return report
    
    def run_check(self):
        """Run all performance checks."""
        logger.info("🔍 Running performance regression checks...")
        
        # Load baseline metrics
        metrics = self.load_baseline()
        if not metrics:
            logger.error("Cannot load baseline metrics")
            return False
        
        issues = []
        
        # Run checks
        issues.extend(self.check_latency(metrics))
        issues.extend(self.check_probes(metrics))
        issues.extend(self.check_recall())
        
        # Generate report
        report = self.generate_report(metrics, issues)
        
        # Save report
        with open('performance_check_report.md', 'w') as f:
            f.write(report)
        
        # Print summary
        print(report)
        
        if issues:
            logger.error(f"❌ Performance regression detected: {len(issues)} issues found")
            return False
        else:
            logger.info("✅ All performance checks passed")
            return True


def main():
    """Run performance regression check."""
    checker = PerformanceChecker()
    success = checker.run_check()
    
    # Exit with appropriate code for CI/CD
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()