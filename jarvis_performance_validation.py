#!/usr/bin/env python3
"""
JARVIS Performance Validation Suite
Validates the workflow optimization performance claims using Pareto analysis
"""

import asyncio
import httpx
import json
import time
from datetime import datetime
from typing import List, Dict, Any
import statistics

class JarvisPerformanceValidator:
    """Validates JARVIS optimization performance using scientific methodology"""
    
    def __init__(self, jarvis_url: str = "https://jarvis-ai-agent-aa4m.onrender.com"):
        self.jarvis_url = jarvis_url
        self.results = []
        
    async def validate_simple_tasks(self) -> List[Dict[str, Any]]:
        """Test simple tasks - target: 1-2 iterations, <5s"""
        simple_tasks = [
            "Check system health status",
            "Provide current time and date",
            "Show system uptime",
            "Get memory count",
            "Basic status report",
            "Quick health check",
            "Display service status",
            "Show active connections",
            "Get system info",
            "Simple diagnostic check"
        ]
        
        print(f"🧪 Testing {len(simple_tasks)} simple tasks...")
        results = []
        
        async with httpx.AsyncClient(timeout=60) as client:
            for i, task in enumerate(simple_tasks, 1):
                print(f"  [{i:2d}/10] {task[:30]}...")
                
                start_time = time.time()
                try:
                    response = await client.post(
                        f"{self.jarvis_url}/tasks",
                        json={"task": task, "priority": "medium"}
                    )
                    end_time = time.time()
                    
                    if response.status_code == 200:
                        data = response.json()
                        result = {
                            "task": task,
                            "type": "simple",
                            "success": data["success"],
                            "iterations": data["iterations"],
                            "duration": data["duration"],
                            "wall_time": end_time - start_time,
                            "target_iterations": "1-2",
                            "target_duration": "<5s",
                            "meets_iteration_target": data["iterations"] <= 2,
                            "meets_duration_target": data["duration"] <= 5.0
                        }
                        results.append(result)
                        print(f"    ✅ {data['iterations']} iterations, {data['duration']:.1f}s")
                    else:
                        print(f"    ❌ HTTP {response.status_code}")
                        
                except Exception as e:
                    print(f"    ❌ Error: {str(e)}")
                
                # Rate limiting - avoid overwhelming the service
                await asyncio.sleep(2)
        
        return results
    
    async def validate_complex_tasks(self) -> List[Dict[str, Any]]:
        """Test complex tasks - target: 2-5 iterations, <20s"""
        complex_tasks = [
            "Analyze system performance and identify optimization opportunities",
            "Create a comprehensive monitoring strategy for the memory service",
            "Develop a scalability plan for handling 10x more data",
            "Design a disaster recovery strategy for the Core Nexus system",
            "Evaluate and recommend improvements to the vector storage architecture"
        ]
        
        print(f"🧪 Testing {len(complex_tasks)} complex tasks...")
        results = []
        
        async with httpx.AsyncClient(timeout=120) as client:
            for i, task in enumerate(complex_tasks, 1):
                print(f"  [{i}/5] {task[:50]}...")
                
                start_time = time.time()
                try:
                    response = await client.post(
                        f"{self.jarvis_url}/tasks",
                        json={"task": task, "priority": "high"}
                    )
                    end_time = time.time()
                    
                    if response.status_code == 200:
                        data = response.json()
                        result = {
                            "task": task,
                            "type": "complex",
                            "success": data["success"],
                            "iterations": data["iterations"],
                            "duration": data["duration"],
                            "wall_time": end_time - start_time,
                            "target_iterations": "2-5",
                            "target_duration": "<20s",
                            "meets_iteration_target": 2 <= data["iterations"] <= 5,
                            "meets_duration_target": data["duration"] <= 20.0
                        }
                        results.append(result)
                        print(f"    ✅ {data['iterations']} iterations, {data['duration']:.1f}s")
                    else:
                        print(f"    ❌ HTTP {response.status_code}")
                        
                except Exception as e:
                    print(f"    ❌ Error: {str(e)}")
                
                # Longer delay for complex tasks
                await asyncio.sleep(3)
        
        return results
    
    def generate_performance_report(self, simple_results: List[Dict], complex_results: List[Dict]) -> Dict[str, Any]:
        """Generate comprehensive performance validation report"""
        all_results = simple_results + complex_results
        
        # Calculate statistics
        simple_iterations = [r["iterations"] for r in simple_results if r["success"]]
        complex_iterations = [r["iterations"] for r in complex_results if r["success"]]
        simple_durations = [r["duration"] for r in simple_results if r["success"]]
        complex_durations = [r["duration"] for r in complex_results if r["success"]]
        
        # Success rates
        simple_success_rate = sum(1 for r in simple_results if r["success"]) / len(simple_results) * 100
        complex_success_rate = sum(1 for r in complex_results if r["success"]) / len(complex_results) * 100
        
        # Target achievement rates
        simple_iteration_success = sum(1 for r in simple_results if r.get("meets_iteration_target", False)) / len(simple_results) * 100
        complex_iteration_success = sum(1 for r in complex_results if r.get("meets_iteration_target", False)) / len(complex_results) * 100
        
        simple_duration_success = sum(1 for r in simple_results if r.get("meets_duration_target", False)) / len(simple_results) * 100
        complex_duration_success = sum(1 for r in complex_results if r.get("meets_duration_target", False)) / len(complex_results) * 100
        
        report = {
            "validation_timestamp": datetime.now().isoformat(),
            "optimization_claim": "91% iteration reduction (11 → 1-2 iterations)",
            "test_summary": {
                "simple_tasks_tested": len(simple_results),
                "complex_tasks_tested": len(complex_results),
                "total_tasks_tested": len(all_results)
            },
            "performance_metrics": {
                "simple_tasks": {
                    "success_rate": f"{simple_success_rate:.1f}%",
                    "avg_iterations": statistics.mean(simple_iterations) if simple_iterations else 0,
                    "max_iterations": max(simple_iterations) if simple_iterations else 0,
                    "avg_duration": f"{statistics.mean(simple_durations):.2f}s" if simple_durations else "N/A",
                    "max_duration": f"{max(simple_durations):.2f}s" if simple_durations else "N/A",
                    "iteration_target_achievement": f"{simple_iteration_success:.1f}%",
                    "duration_target_achievement": f"{simple_duration_success:.1f}%"
                },
                "complex_tasks": {
                    "success_rate": f"{complex_success_rate:.1f}%",
                    "avg_iterations": statistics.mean(complex_iterations) if complex_iterations else 0,
                    "max_iterations": max(complex_iterations) if complex_iterations else 0,
                    "avg_duration": f"{statistics.mean(complex_durations):.2f}s" if complex_durations else "N/A",
                    "max_duration": f"{max(complex_durations):.2f}s" if complex_durations else "N/A",
                    "iteration_target_achievement": f"{complex_iteration_success:.1f}%",
                    "duration_target_achievement": f"{complex_duration_success:.1f}%"
                }
            },
            "optimization_validation": {
                "pre_optimization_baseline": "11 iterations average",
                "post_optimization_simple": f"{statistics.mean(simple_iterations):.1f} iterations" if simple_iterations else "N/A",
                "post_optimization_complex": f"{statistics.mean(complex_iterations):.1f} iterations" if complex_iterations else "N/A",
                "improvement_simple": f"{((11 - statistics.mean(simple_iterations)) / 11 * 100):.1f}%" if simple_iterations else "N/A",
                "improvement_complex": f"{((11 - statistics.mean(complex_iterations)) / 11 * 100):.1f}%" if complex_iterations else "N/A",
                "optimization_validated": all([
                    simple_iteration_success >= 80,  # 80% of simple tasks meet target
                    complex_iteration_success >= 80,  # 80% of complex tasks meet target
                    statistics.mean(simple_iterations) <= 2 if simple_iterations else False,
                    statistics.mean(complex_iterations) <= 5 if complex_iterations else False
                ])
            },
            "detailed_results": all_results
        }
        
        return report
    
    async def run_validation(self) -> Dict[str, Any]:
        """Run complete performance validation suite"""
        print("🚀 JARVIS Performance Validation Suite")
        print("=" * 50)
        print("Validating workflow optimization claims...")
        print()
        
        # Test simple tasks
        simple_results = await self.validate_simple_tasks()
        print()
        
        # Test complex tasks  
        complex_results = await self.validate_complex_tasks()
        print()
        
        # Generate report
        report = self.generate_performance_report(simple_results, complex_results)
        
        # Print summary
        print("📊 VALIDATION RESULTS")
        print("-" * 30)
        print(f"✅ Simple Tasks: {report['performance_metrics']['simple_tasks']['iteration_target_achievement']} meet iteration targets")
        print(f"✅ Complex Tasks: {report['performance_metrics']['complex_tasks']['iteration_target_achievement']} meet iteration targets")
        print(f"⚡ Average Simple Task: {report['performance_metrics']['simple_tasks']['avg_iterations']:.1f} iterations")
        print(f"⚡ Average Complex Task: {report['performance_metrics']['complex_tasks']['avg_iterations']:.1f} iterations")
        print(f"🎯 Optimization Validated: {report['optimization_validation']['optimization_validated']}")
        print()
        
        return report

async def main():
    """Main validation function"""
    validator = JarvisPerformanceValidator()
    report = await validator.run_validation()
    
    # Save report
    report_file = f"jarvis_performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"📄 Full report saved to: {report_file}")
    return report

if __name__ == "__main__":
    asyncio.run(main())