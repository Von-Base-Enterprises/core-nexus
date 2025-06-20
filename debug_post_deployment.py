#!/usr/bin/env python3
"""
Debug why replication is still not working after deployment
"""

import asyncio
import httpx
import json
from datetime import datetime

API_BASE = "https://core-nexus-memory-service.onrender.com"

async def debug_post_deployment():
    """Debug replication after confirmed deployment"""
    print("🔍 POST-DEPLOYMENT REPLICATION DEBUG")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Confirm deployment happened
        print("1. ✅ Confirming deployment...")
        response = await client.get(f"{API_BASE}/health")
        
        if response.status_code == 200:
            health_data = response.json()
            uptime = health_data.get("uptime_seconds", 0)
            uptime_minutes = uptime / 60
            
            print(f"Service uptime: {uptime_minutes:.1f} minutes")
            if uptime_minutes < 10:
                print("✅ CONFIRMED: Recent deployment (uptime < 10 minutes)")
            else:
                print("❌ Deployment may not have occurred")
                return
                
        # 2. Deep dive into provider status
        print("\n2. 🔍 Provider detailed analysis...")
        providers = health_data.get("providers", {})
        
        for name, config in providers.items():
            print(f"\n{name.upper()} PROVIDER:")
            print(f"  Status: {config.get('status')}")
            print(f"  Primary: {config.get('primary', False)}")
            
            details = config.get("details", {})
            if isinstance(details, dict):
                for key, value in details.items():
                    if key == "details" and isinstance(value, dict):
                        for subkey, subvalue in value.items():
                            print(f"    {subkey}: {subvalue}")
                    else:
                        print(f"  {key}: {value}")
                        
        # 3. Check if ChromaDB is actually enabled
        chromadb_config = providers.get("chromadb", {})
        if chromadb_config.get("status") != "healthy":
            print(f"\n❌ PROBLEM: ChromaDB status is '{chromadb_config.get('status')}'")
            if "error" in chromadb_config:
                print(f"   Error: {chromadb_config['error']}")
            return
            
        # 4. Test replication with detailed error tracking
        print("\n3. 🧪 Testing replication with error tracking...")
        
        test_content = f"🔍 Post-deployment test {datetime.now().isoformat()}"
        
        try:
            create_response = await client.post(
                f"{API_BASE}/memories",
                json={
                    "content": test_content,
                    "metadata": {
                        "post_deployment_test": True,
                        "timestamp": datetime.now().isoformat()
                    }
                }
            )
            
            print(f"Create response status: {create_response.status_code}")
            
            if create_response.status_code == 200:
                memory_data = create_response.json()
                memory_id = memory_data.get("id")
                print(f"✅ Memory created: {memory_id}")
                
                # Check response for any replication info
                print(f"Response keys: {list(memory_data.keys())}")
                
                # Wait and check both providers
                print("⏳ Waiting 10 seconds for replication...")
                await asyncio.sleep(10)
                
                # Get updated counts
                response = await client.get(f"{API_BASE}/health")
                if response.status_code == 200:
                    new_health = response.json()
                    new_providers = new_health.get("providers", {})
                    
                    pgvector_count = new_providers.get("pgvector", {}).get("details", {}).get("details", {}).get("total_vectors", 0)
                    chromadb_count = new_providers.get("chromadb", {}).get("details", {}).get("details", {}).get("total_vectors", 0)
                    
                    print(f"\nFinal counts:")
                    print(f"  pgvector: {pgvector_count}")
                    print(f"  chromadb: {chromadb_count}")
                    
                    if chromadb_count > 0:
                        print("🎉 SUCCESS: ChromaDB is receiving data!")
                    else:
                        print("❌ FAILURE: ChromaDB still empty")
                        print("\n🔍 Possible remaining issues:")
                        print("   1. ChromaDB provider not in secondary providers list")
                        print("   2. ChromaDB storage operation failing silently")
                        print("   3. Configuration issue preventing ChromaDB writes")
                        print("   4. Exception in replication code being caught and ignored")
                        
            else:
                print(f"❌ Memory creation failed: {create_response.status_code}")
                print(f"Response: {create_response.text}")
                
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            
        # 5. Check if we can access any admin/debug endpoints
        print("\n4. 🔍 Checking for admin endpoints...")
        debug_endpoints = ["/admin/providers", "/debug/replication", "/admin/sync"]
        
        for endpoint in debug_endpoints:
            try:
                response = await client.get(f"{API_BASE}{endpoint}")
                if response.status_code != 404:
                    print(f"Found {endpoint}: {response.status_code}")
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            print(f"  Data: {json.dumps(data, indent=2)[:300]}...")
                        except:
                            print(f"  Data: {response.text[:300]}...")
            except:
                pass

async def main():
    try:
        await debug_post_deployment()
        
        print("\n" + "="*60)
        print("📋 POST-DEPLOYMENT ANALYSIS")
        print("="*60)
        print("Status: Deployment confirmed but replication still failing")
        print("Next steps:")
        print("1. Check if ChromaDB provider is in secondary providers list")
        print("2. Verify ChromaDB initialization in the deployed code")
        print("3. Look for silent exceptions in replication code")
        print("4. Consider adding admin endpoint to debug replication")
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())