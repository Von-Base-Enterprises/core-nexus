#!/usr/bin/env python3
"""
Monitor query performance of Core Nexus Memory Service.
"""

import json
import time
import urllib.request
import statistics
from datetime import datetime


def test_query_performance(api_key="dev-key-12345", num_tests=5):
    """Run performance tests on the query endpoint."""
    base_url = "https://core-nexus-memory-service.onrender.com"
    
    test_queries = [
        ("Empty query", "", 10),
        ("Single word", "test", 5),
        ("Multi word", "production performance", 5),
        ("Technical query", "vector database optimization", 5)
    ]
    
    results = {}
    
    for query_name, query_text, limit in test_queries:
        times = []
        print(f"\nTesting: {query_name}")
        
        for i in range(num_tests):
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": api_key
            }
            
            data = json.dumps({
                "query": query_text,
                "limit": limit
            }).encode('utf-8')
            
            req = urllib.request.Request(
                f"{base_url}/memories/query",
                data=data,
                headers=headers,
                method="POST"
            )
            
            start_time = time.time()
            try:
                response = urllib.request.urlopen(req)
                response_data = json.loads(response.read().decode('utf-8'))
                end_time = time.time()
                
                query_time = response_data.get('query_time_ms', 0)
                total_time = (end_time - start_time) * 1000
                
                times.append({
                    'query_time_ms': query_time,
                    'total_time_ms': total_time,
                    'network_time_ms': total_time - query_time
                })
                
                print(f"  Test {i+1}: Query={query_time:.1f}ms, Total={total_time:.1f}ms")
                
            except Exception as e:
                print(f"  Test {i+1}: ERROR - {e}")
            
            time.sleep(0.5)  # Small delay between tests
        
        if times:
            results[query_name] = {
                'avg_query_time': statistics.mean([t['query_time_ms'] for t in times]),
                'avg_total_time': statistics.mean([t['total_time_ms'] for t in times]),
                'min_query_time': min([t['query_time_ms'] for t in times]),
                'max_query_time': max([t['query_time_ms'] for t in times]),
                'samples': len(times)
            }
    
    return results


def main():
    """Run performance monitoring."""
    print("🚀 Core Nexus Query Performance Monitor")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    results = test_query_performance()
    
    print("\n" + "=" * 50)
    print("📊 PERFORMANCE SUMMARY")
    print("=" * 50)
    
    for query_type, metrics in results.items():
        print(f"\n{query_type}:")
        print(f"  Average Query Time: {metrics['avg_query_time']:.1f}ms")
        print(f"  Min/Max Query Time: {metrics['min_query_time']:.1f}ms / {metrics['max_query_time']:.1f}ms")
        print(f"  Average Total Time: {metrics['avg_total_time']:.1f}ms")
    
    # Performance assessment
    print("\n" + "=" * 50)
    print("🎯 PERFORMANCE ASSESSMENT")
    print("=" * 50)
    
    all_query_times = []
    for metrics in results.values():
        all_query_times.append(metrics['avg_query_time'])
    
    overall_avg = statistics.mean(all_query_times) if all_query_times else 0
    
    if overall_avg < 100:
        print(f"✅ EXCELLENT: Average query time {overall_avg:.1f}ms < 100ms target")
    elif overall_avg < 300:
        print(f"⚠️ ACCEPTABLE: Average query time {overall_avg:.1f}ms (target: <100ms)")
    else:
        print(f"❌ NEEDS OPTIMIZATION: Average query time {overall_avg:.1f}ms >> 100ms target")
    
    # Save results
    with open('performance_report.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'results': results,
            'overall_average_ms': overall_avg
        }, f, indent=2)
    
    print("\n📄 Results saved to performance_report.json")


if __name__ == "__main__":
    main()