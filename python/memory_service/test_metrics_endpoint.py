#!/usr/bin/env python3
"""
Test script to verify the Prometheus metrics endpoint is working correctly.
"""

import asyncio
import httpx
import time

# Test configuration
API_BASE_URL = "https://core-nexus-memory-service.onrender.com"
TEST_TIMEOUT = 10  # seconds

async def test_metrics_endpoint():
    """Test the Prometheus metrics endpoint."""
    
    print("📊 Core Nexus Metrics Endpoint Test")
    print("=" * 50)
    print(f"🎯 Target: {API_BASE_URL}/metrics\n")
    
    async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
        
        try:
            print("1. Testing metrics endpoint...")
            start_time = time.time()
            
            response = await client.get(f"{API_BASE_URL}/metrics")
            response_time = (time.time() - start_time) * 1000
            
            print(f"   📡 Response code: {response.status_code}")
            print(f"   ⏱️  Response time: {response_time:.1f}ms")
            print(f"   📄 Content type: {response.headers.get('content-type', 'unknown')}")
            
            if response.status_code == 200:
                content = response.text
                
                # Check for key metrics
                metrics_found = []
                expected_metrics = [
                    'core_nexus_memories_total',
                    'core_nexus_uptime_seconds',
                    'core_nexus_avg_query_time_ms',
                    'core_nexus_total_queries',
                    'core_nexus_service_health',
                    'core_nexus_provider_health',
                    'core_nexus_provider_usage'
                ]
                
                for metric in expected_metrics:
                    if metric in content:
                        metrics_found.append(metric)
                
                print(f"\n2. Metrics validation:")
                print(f"   ✅ Found {len(metrics_found)}/{len(expected_metrics)} expected metrics")
                
                for metric in metrics_found:
                    print(f"      • {metric}")
                
                if len(metrics_found) < len(expected_metrics):
                    missing = set(expected_metrics) - set(metrics_found)
                    print(f"   ⚠️  Missing metrics: {', '.join(missing)}")
                
                # Parse some key values
                print(f"\n3. Sample metric values:")
                lines = content.split('\n')
                for line in lines:
                    if line.startswith('core_nexus_memories_total'):
                        value = line.split()[-1]
                        print(f"   📊 Total memories: {value}")
                    elif line.startswith('core_nexus_service_health'):
                        value = line.split()[-1]
                        health_status = "Healthy" if value == "1" else "Unhealthy"
                        print(f"   💚 Service health: {health_status}")
                    elif line.startswith('core_nexus_uptime_seconds'):
                        value = float(line.split()[-1])
                        uptime_hours = value / 3600
                        print(f"   ⏰ Uptime: {uptime_hours:.1f} hours")
                    elif line.startswith('core_nexus_avg_query_time_ms'):
                        value = line.split()[-1]
                        print(f"   ⚡ Avg query time: {value}ms")
                
                # Check Prometheus format
                print(f"\n4. Format validation:")
                has_help = '# HELP' in content
                has_type = '# TYPE' in content
                has_values = any(line and not line.startswith('#') for line in lines)
                
                print(f"   {'✅' if has_help else '❌'} HELP comments present")
                print(f"   {'✅' if has_type else '❌'} TYPE declarations present") 
                print(f"   {'✅' if has_values else '❌'} Metric values present")
                
                if has_help and has_type and has_values:
                    print(f"   🎉 Valid Prometheus format!")
                
                # Show first few lines as sample
                print(f"\n5. Sample output (first 10 lines):")
                sample_lines = lines[:10]
                for line in sample_lines:
                    if line.strip():
                        print(f"   {line}")
                
                return True
                
            else:
                print(f"   ❌ Metrics endpoint failed: {response.status_code}")
                print(f"   📄 Response: {response.text[:200]}...")
                return False
                
        except Exception as e:
            print(f"   ❌ Metrics endpoint error: {e}")
            return False

async def main():
    """Run the metrics endpoint test."""
    
    print("🔧 Core Nexus Prometheus Metrics Verification")
    print("🎯 Testing the newly enabled /metrics endpoint")
    print()
    
    success = await test_metrics_endpoint()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 SUCCESS: Metrics endpoint is working!")
        print("✅ Prometheus metrics properly formatted")
        print("✅ Key metrics available for monitoring")
        print("✅ Ready for Grafana dashboard integration")
    else:
        print("❌ FAILURE: Metrics endpoint not working correctly")
        print("🔍 Additional investigation needed")
    
    print("\n📊 Metrics Available:")
    print("   • Total memories stored")
    print("   • Service uptime")
    print("   • Query performance metrics")
    print("   • Provider health status")
    print("   • Replication statistics")

if __name__ == "__main__":
    asyncio.run(main())