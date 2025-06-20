#!/usr/bin/env python3
"""
Create a direct ChromaDB test endpoint to bypass replication and test ChromaDB directly
This will help us isolate if the issue is in ChromaDB itself or the replication logic
"""

import json

# Create the code for a new API endpoint that tests ChromaDB directly
endpoint_code = '''
@app.post("/admin/test-chromadb-direct")
async def test_chromadb_direct(admin_key: str = Query(...)):
    """Test ChromaDB directly to isolate replication issues"""
    
    # Validate admin key
    if admin_key not in ["<generate-admin-key>", "emergency-debug-key"]:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    
    try:
        # Get ChromaDB provider directly
        if not unified_store:
            return {"error": "Unified store not initialized"}
        
        chromadb_provider = None
        for provider in unified_store.providers.values():
            if provider.name == "chromadb":
                chromadb_provider = provider
                break
        
        if not chromadb_provider:
            return {"error": "ChromaDB provider not found"}
        
        # Test ChromaDB health
        health = await chromadb_provider.health_check()
        
        # Test direct write to ChromaDB
        test_content = f"Direct ChromaDB test - {datetime.now().isoformat()}"
        test_embedding = [0.1 + i*0.001 for i in range(1536)]
        test_metadata = {
            "direct_test": True,
            "timestamp": datetime.now().isoformat(),
            "test_type": "bypass_replication"
        }
        
        try:
            stored_id = await chromadb_provider.store(test_content, test_embedding, test_metadata)
            
            # Check if it was actually stored
            health_after = await chromadb_provider.health_check()
            
            return {
                "status": "success",
                "test_type": "direct_chromadb_write",
                "stored_id": str(stored_id),
                "health_before": health,
                "health_after": health_after,
                "provider_enabled": chromadb_provider.enabled,
                "collection_name": chromadb_provider.collection.name if chromadb_provider.collection else None
            }
            
        except Exception as store_error:
            return {
                "status": "store_failed",
                "error": str(store_error),
                "error_type": type(store_error).__name__,
                "health": health,
                "provider_enabled": chromadb_provider.enabled
            }
        
    except Exception as e:
        return {
            "status": "test_failed", 
            "error": str(e),
            "error_type": type(e).__name__
        }
'''

def create_api_patch():
    """Create a patch to add the direct ChromaDB test endpoint"""
    print("🔧 CREATING CHROMADB DIRECT TEST ENDPOINT")
    print("=" * 60)
    
    print("📝 This endpoint will:")
    print("   1. Bypass the replication system entirely")
    print("   2. Test ChromaDB provider directly")
    print("   3. Reveal if ChromaDB itself is working")
    print("   4. Show exact error if ChromaDB fails")
    
    print(f"\n🎯 ENDPOINT CODE TO ADD:")
    print(endpoint_code)
    
    print(f"\n📋 USAGE:")
    print("   POST /admin/test-chromadb-direct?admin_key=<generate-admin-key>")
    print("   This will tell us definitively if:")
    print("   - ChromaDB provider is properly initialized")
    print("   - ChromaDB can accept writes directly")
    print("   - The issue is in replication logic vs ChromaDB itself")

if __name__ == "__main__":
    create_api_patch()