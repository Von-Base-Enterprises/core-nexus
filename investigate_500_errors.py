#!/usr/bin/env python3
"""
Investigate 500 errors in the /memories endpoint to identify and fix service instability
"""

import asyncio
import httpx
import json
from datetime import datetime

API_BASE = "https://core-nexus-memory-service.onrender.com"

async def investigate_service_errors():
    """Comprehensive investigation of service errors"""
    print("🔍 INVESTIGATING SERVICE 500 ERRORS")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        
        # 1. Test different endpoint variations
        print("1. 🧪 Testing memory endpoint variations...")
        
        endpoints_to_test = [
            "/memories",
            "/memories/",
            "/memories?limit=10",
            "/memories?limit=1",
            "/memories/search",
            "/memories/search?q=test",
            "/memories/search?q=",
            "/api/memories",
            "/api/v1/memories"
        ]
        
        for endpoint in endpoints_to_test:
            try:
                # Test GET request
                response = await client.get(f"{API_BASE}{endpoint}")
                print(f"GET {endpoint}: {response.status_code}")
                
                if response.status_code == 500:
                    # Try to get error details
                    try:
                        error_data = response.json()
                        print(f"   Error: {error_data.get('detail', 'No detail available')}")
                    except:
                        error_text = response.text[:200]
                        print(f"   Error text: {error_text}")
                elif response.status_code == 200:
                    try:
                        data = response.json()
                        if isinstance(data, dict):
                            if "memories" in data:
                                memory_count = len(data["memories"])
                                print(f"   ✅ Success: {memory_count} memories returned")
                            else:
                                print(f"   ✅ Success: {list(data.keys())}")
                        else:
                            print(f"   ✅ Success: Response type {type(data)}")
                    except:
                        print(f"   ✅ Success: {len(response.text)} bytes")
                        
            except Exception as e:
                print(f"GET {endpoint}: Exception - {e}")
                
        print()
        
        # 2. Test POST operations (memory creation)
        print("2. 📝 Testing memory creation (POST)...")
        
        test_memories = [
            {
                "content": "Simple test memory",
                "metadata": {"test": True}
            },
            {
                "content": "Test with user ID",
                "metadata": {"test": True},
                "user_id": "test-user"
            },
            {
                "content": "Test with conversation ID", 
                "metadata": {"test": True},
                "conversation_id": "test-conversation"
            }
        ]
        
        for i, memory_data in enumerate(test_memories):
            try:
                response = await client.post(
                    f"{API_BASE}/memories",
                    json=memory_data
                )
                
                print(f"POST test {i+1}: {response.status_code}")
                
                if response.status_code == 500:
                    try:
                        error_data = response.json()
                        print(f"   Error: {error_data.get('detail', 'No detail')}")
                    except:
                        error_text = response.text[:300]
                        print(f"   Error text: {error_text}")
                elif response.status_code == 200:
                    try:
                        data = response.json()
                        memory_id = data.get("id", "unknown")
                        print(f"   ✅ Success: Memory created with ID {memory_id}")
                    except:
                        print(f"   ✅ Success: {len(response.text)} bytes")
                else:
                    print(f"   Unexpected status: {response.text[:100]}")
                    
            except Exception as e:
                print(f"POST test {i+1}: Exception - {e}")
                
        print()
        
        # 3. Check service health and provider status
        print("3. ⚕️ Checking service health details...")
        
        try:
            response = await client.get(f"{API_BASE}/health")
            if response.status_code == 200:
                health_data = response.json()
                
                print(f"Overall status: {health_data.get('status')}")
                print(f"Total memories: {health_data.get('total_memories')}")
                print(f"Uptime: {health_data.get('uptime_seconds', 0)/60:.1f} minutes")
                
                providers = health_data.get("providers", {})
                for name, config in providers.items():
                    status = config.get("status")
                    primary = config.get("primary", False)
                    print(f"Provider {name}: {status} (primary: {primary})")
                    
                    if status != "healthy":
                        print(f"   ❌ {name} error: {config.get('error', 'Unknown')}")
                        
            else:
                print(f"Health check failed: {response.status_code}")
                
        except Exception as e:
            print(f"Health check exception: {e}")
            
        print()
        
        # 4. Test with different HTTP methods
        print("4. 🌐 Testing HTTP methods...")
        
        methods_to_test = [
            ("OPTIONS", "/memories"),
            ("HEAD", "/memories"), 
            ("PUT", "/memories"),
            ("PATCH", "/memories"),
            ("DELETE", "/memories")
        ]
        
        for method, endpoint in methods_to_test:
            try:
                response = await client.request(method, f"{API_BASE}{endpoint}")
                print(f"{method} {endpoint}: {response.status_code}")
                
                if response.status_code >= 500:
                    print(f"   Server error detected in {method}")
                    
            except Exception as e:
                print(f"{method} {endpoint}: Exception - {e}")
                
        print()
        
        # 5. Check for any working endpoints
        print("5. ✅ Finding working endpoints...")
        
        working_endpoints = [
            "/health",
            "/docs", 
            "/openapi.json",
            "/",
            "/metrics",
            "/debug/env"
        ]
        
        for endpoint in working_endpoints:
            try:
                response = await client.get(f"{API_BASE}{endpoint}")
                print(f"GET {endpoint}: {response.status_code}")
                
                if response.status_code == 200:
                    print(f"   ✅ Working endpoint found")
                    
            except Exception as e:
                print(f"GET {endpoint}: Exception - {e}")

async def main():
    try:
        await investigate_service_errors()
        
        print("\n" + "="*60)
        print("📋 ERROR INVESTIGATION SUMMARY")
        print("="*60)
        print("Analysis complete. Key findings:")
        print("1. Identify which specific endpoints are failing")
        print("2. Determine if errors are in GET, POST, or both operations")
        print("3. Check if provider failures are causing cascading errors")
        print("4. Find working endpoints to understand service state")
        
        print("\nNext steps:")
        print("- Fix any provider initialization issues")
        print("- Resolve endpoint routing or authentication problems")
        print("- Ensure database connections are stable")
        print("- Test memory operations after fixes")
        
    except Exception as e:
        print(f"❌ Investigation failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())