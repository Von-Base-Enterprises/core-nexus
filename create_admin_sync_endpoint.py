#!/usr/bin/env python3
"""
Create an admin endpoint in the API to debug and force ChromaDB sync
This will help us understand why replication is failing
"""

admin_endpoint_code = '''
@app.post("/admin/debug-replication")
async def debug_replication(
    admin_key: str = None,
    store: UnifiedVectorStore = Depends(get_store)
):
    """Debug replication system and force sync of recent memories"""
    
    # Simple admin check
    if admin_key != "debug-replication-2025":
        raise HTTPException(status_code=401, detail="Admin key required")
    
    try:
        debug_info = {
            "timestamp": datetime.now().isoformat(),
            "providers": {},
            "replication_test": {},
            "sync_attempt": {}
        }
        
        # 1. Check provider configuration
        for name, provider in store.providers.items():
            debug_info["providers"][name] = {
                "name": provider.name,
                "enabled": provider.enabled,
                "is_primary": provider == store.primary_provider,
                "config": provider.config.name if hasattr(provider.config, 'name') else str(type(provider.config))
            }
            
        # 2. Check secondary providers list
        secondary_providers = [p for p in store.providers.values() 
                             if p != store.primary_provider and p.enabled]
        debug_info["secondary_providers_count"] = len(secondary_providers)
        debug_info["secondary_providers"] = [p.name for p in secondary_providers]
        
        # 3. Test replication manually
        test_content = f"Manual replication test {datetime.now().isoformat()}"
        test_embedding = [0.1] * 1536  # Mock embedding
        test_metadata = {
            "manual_test": True,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Try to replicate manually
            replication_results = []
            for provider in secondary_providers:
                try:
                    result_id = await store._store_with_retry(
                        provider, test_content, test_embedding, test_metadata
                    )
                    replication_results.append({
                        "provider": provider.name,
                        "success": True,
                        "id": str(result_id)
                    })
                except Exception as e:
                    replication_results.append({
                        "provider": provider.name,
                        "success": False,
                        "error": str(e)
                    })
                    
            debug_info["replication_test"]["results"] = replication_results
            debug_info["replication_test"]["success_count"] = sum(1 for r in replication_results if r["success"])
            
        except Exception as e:
            debug_info["replication_test"]["error"] = str(e)
            
        # 4. Try to sync one existing memory
        try:
            # Get a recent memory from pgvector
            pgvector = store.providers.get('pgvector')
            if pgvector and pgvector.enabled:
                # Get one memory for sync test
                async with pgvector.connection_pool.acquire() as conn:
                    row = await conn.fetchrow("""
                        SELECT id, content, embedding, metadata 
                        FROM vector_memories 
                        ORDER BY created_at DESC 
                        LIMIT 1
                    """)
                    
                    if row:
                        # Try to sync this memory to ChromaDB
                        chromadb = store.providers.get('chromadb')
                        if chromadb and chromadb.enabled:
                            try:
                                sync_result = await chromadb.store(
                                    content=row['content'],
                                    embedding=list(row['embedding']),
                                    metadata=dict(row['metadata']) if row['metadata'] else {}
                                )
                                debug_info["sync_attempt"] = {
                                    "success": True,
                                    "original_id": str(row['id']),
                                    "chromadb_id": str(sync_result),
                                    "content_length": len(row['content'])
                                }
                            except Exception as e:
                                debug_info["sync_attempt"] = {
                                    "success": False,
                                    "error": str(e),
                                    "original_id": str(row['id'])
                                }
                        else:
                            debug_info["sync_attempt"]["error"] = "ChromaDB provider not available"
                    else:
                        debug_info["sync_attempt"]["error"] = "No memories found in pgvector"
            else:
                debug_info["sync_attempt"]["error"] = "pgvector provider not available"
                
        except Exception as e:
            debug_info["sync_attempt"]["error"] = f"Sync test failed: {str(e)}"
            
        return {
            "status": "debug_complete",
            "debug_info": debug_info,
            "recommendations": [
                "Check if ChromaDB is in secondary_providers list",
                "Verify ChromaDB store() method is working",
                "Check for silent exceptions in replication code",
                "Verify ChromaDB initialization and configuration"
            ]
        }
        
    except Exception as e:
        logger.error(f"Debug replication failed: {e}")
        raise HTTPException(status_code=500, detail=f"Debug failed: {str(e)}")


@app.post("/admin/force-sync-recent")
async def force_sync_recent(
    admin_key: str = None,
    limit: int = 10,
    store: UnifiedVectorStore = Depends(get_store)
):
    """Force sync recent memories to ChromaDB"""
    
    if admin_key != "debug-replication-2025":
        raise HTTPException(status_code=401, detail="Admin key required")
    
    try:
        sync_results = {
            "timestamp": datetime.now().isoformat(),
            "target_count": limit,
            "synced": 0,
            "failed": 0,
            "errors": []
        }
        
        # Get recent memories from pgvector
        pgvector = store.providers.get('pgvector')
        chromadb = store.providers.get('chromadb')
        
        if not pgvector or not pgvector.enabled:
            raise HTTPException(status_code=503, detail="pgvector not available")
        if not chromadb or not chromadb.enabled:
            raise HTTPException(status_code=503, detail="ChromaDB not available")
            
        async with pgvector.connection_pool.acquire() as conn:
            rows = await conn.fetch(f"""
                SELECT id, content, embedding, metadata, created_at
                FROM vector_memories 
                ORDER BY created_at DESC 
                LIMIT {limit}
            """)
            
            for row in rows:
                try:
                    result_id = await chromadb.store(
                        content=row['content'],
                        embedding=list(row['embedding']),
                        metadata={
                            **(dict(row['metadata']) if row['metadata'] else {}),
                            "synced_from_pgvector": True,
                            "original_id": str(row['id']),
                            "sync_timestamp": datetime.now().isoformat()
                        }
                    )
                    sync_results["synced"] += 1
                    
                except Exception as e:
                    sync_results["failed"] += 1
                    sync_results["errors"].append({
                        "memory_id": str(row['id']),
                        "error": str(e)
                    })
                    
        return {
            "status": "sync_complete",
            "results": sync_results
        }
        
    except Exception as e:
        logger.error(f"Force sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")
'''

def main():
    print("🔧 ADMIN ENDPOINT CODE FOR DEBUGGING REPLICATION")
    print("="*60)
    print("This code needs to be added to the API to debug replication issues.")
    print()
    print("The endpoints will:")
    print("1. /admin/debug-replication - Debug why replication is failing")
    print("2. /admin/force-sync-recent - Force sync recent memories")
    print()
    print("To add these endpoints:")
    print("1. Add the code to python/memory_service/src/memory_service/api.py")
    print("2. Deploy the changes")
    print("3. Test the endpoints with admin key: 'debug-replication-2025'")
    print()
    print("Example usage:")
    print("curl -X POST 'https://core-nexus-memory-service.onrender.com/admin/debug-replication' \\")
    print("     -d 'admin_key=debug-replication-2025'")
    print()
    print("For now, let me try a different approach to force sync...")

if __name__ == "__main__":
    main()