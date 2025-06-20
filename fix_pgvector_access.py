#!/usr/bin/env python3
"""
Fix pgvector access by adding admin endpoints to restore production memory access
This will allow us to bypass the environment variable issue and restore the 1,152 memories
"""

admin_endpoints_code = '''
from fastapi import HTTPException, Query
import asyncpg
import urllib.parse

@app.post("/admin/restore-pgvector-access")
async def restore_pgvector_access(
    admin_key: str = Query(..., description="Admin authentication key"),
    database_url: str = Query(None, description="Optional manual database URL"),
    password: str = Query(None, description="Optional manual password")
):
    """Emergency endpoint to restore pgvector access when env vars fail"""
    
    # Simple admin authentication
    if admin_key != "restore-pgvector-2025":
        raise HTTPException(status_code=401, detail="Invalid admin key")
    
    global unified_store
    
    try:
        logger.info("🚨 EMERGENCY: Attempting to restore pgvector access")
        
        # Try multiple methods to get connection info
        connection_methods = []
        
        # Method 1: Manual override
        if database_url and password:
            connection_methods.append(("manual_override", {
                "database_url": database_url,
                "password": password
            }))
            
        # Method 2: Environment DATABASE_URL
        env_database_url = os.getenv("DATABASE_URL")
        if env_database_url:
            connection_methods.append(("env_database_url", {
                "database_url": env_database_url
            }))
            
        # Method 3: Direct environment variables with common password names
        for pwd_var in ["PGVECTOR_PASSWORD", "PGPASSWORD", "DATABASE_PASSWORD", "POSTGRES_PASSWORD"]:
            pwd = os.getenv(pwd_var)
            if pwd:
                connection_methods.append((f"env_{pwd_var.lower()}", {
                    "host": os.getenv("PGVECTOR_HOST", "dpg-d12n0np5pdvs73ctmm40-a"),
                    "port": int(os.getenv("PGVECTOR_PORT", "5432")),
                    "database": os.getenv("PGVECTOR_DATABASE", "nexus_memory_db"),
                    "user": os.getenv("PGVECTOR_USER", "nexus_memory_db_user"),
                    "password": pwd
                }))
                break
        
        restoration_results = {
            "timestamp": datetime.now().isoformat(),
            "methods_tried": len(connection_methods),
            "connections_tested": [],
            "success": False,
            "memory_count": 0,
            "pgvector_status": "failed"
        }
        
        # Try each connection method
        for method_name, config in connection_methods:
            try:
                logger.info(f"Trying connection method: {method_name}")
                
                if "database_url" in config:
                    # Parse DATABASE_URL
                    parsed = urllib.parse.urlparse(config["database_url"])
                    host = parsed.hostname
                    port = parsed.port or 5432
                    database = parsed.path[1:] if parsed.path and len(parsed.path) > 1 else "nexus_memory_db"
                    user = parsed.username
                    password = config.get("password") or parsed.password
                else:
                    # Use direct config
                    host = config["host"]
                    port = config["port"]
                    database = config["database"]
                    user = config["user"]
                    password = config["password"]
                
                if not password:
                    restoration_results["connections_tested"].append({
                        "method": method_name,
                        "success": False,
                        "error": "No password available"
                    })
                    continue
                
                # Test connection
                conn_string = f"postgresql://{user}:{password}@{host}:{port}/{database}?sslmode=require"
                conn = await asyncpg.connect(conn_string)
                
                # Test basic query
                memory_count = await conn.fetchval("SELECT COUNT(*) FROM vector_memories")
                
                await conn.close()
                
                # Success! Now create and initialize a new pgvector provider
                from .providers import PgVectorProvider
                from .models import ProviderConfig
                
                pgvector_config = ProviderConfig(
                    name="pgvector",
                    enabled=True,
                    primary=True,
                    config={
                        "host": host,
                        "port": port,
                        "database": database,
                        "user": user,
                        "password": password,
                        "table_name": "vector_memories",
                        "embedding_dim": 1536,
                        "distance_metric": "cosine"
                    }
                )
                
                new_pgvector_provider = PgVectorProvider(pgvector_config)
                await new_pgvector_provider.initialize()
                
                # Replace the provider in the unified store
                if unified_store:
                    # Remove old disabled pgvector if it exists
                    unified_store.providers = {k: v for k, v in unified_store.providers.items() if k != "pgvector"}
                    
                    # Add the new working provider
                    unified_store.providers["pgvector"] = new_pgvector_provider
                    unified_store.primary_provider = new_pgvector_provider
                    
                    logger.info("✅ Successfully restored pgvector provider in unified store")
                
                restoration_results.update({
                    "success": True,
                    "method_used": method_name,
                    "memory_count": memory_count,
                    "pgvector_status": "restored",
                    "host": host,
                    "port": port,
                    "database": database,
                    "user": user
                })
                
                restoration_results["connections_tested"].append({
                    "method": method_name,
                    "success": True,
                    "memory_count": memory_count
                })
                
                break  # Success, stop trying other methods
                
            except Exception as e:
                restoration_results["connections_tested"].append({
                    "method": method_name,
                    "success": False,
                    "error": str(e)
                })
                logger.warning(f"Connection method {method_name} failed: {e}")
                continue
        
        if restoration_results["success"]:
            logger.info(f"🎉 PGVECTOR ACCESS RESTORED! {restoration_results['memory_count']} memories available")
            return {
                "status": "success",
                "message": f"pgvector access restored with {restoration_results['memory_count']} memories",
                "details": restoration_results
            }
        else:
            logger.error("❌ All connection methods failed")
            return {
                "status": "failed",
                "message": "Could not restore pgvector access",
                "details": restoration_results
            }
            
    except Exception as e:
        logger.error(f"Emergency restoration failed: {e}")
        raise HTTPException(status_code=500, detail=f"Restoration failed: {str(e)}")


@app.get("/admin/pgvector-diagnosis")
async def pgvector_diagnosis(admin_key: str = Query(...)):
    """Diagnose pgvector connection issues"""
    
    if admin_key != "restore-pgvector-2025":
        raise HTTPException(status_code=401, detail="Invalid admin key")
    
    diagnosis = {
        "timestamp": datetime.now().isoformat(),
        "environment_variables": {},
        "provider_status": {},
        "connection_tests": []
    }
    
    # Check environment variables
    env_vars_to_check = [
        "DATABASE_URL", "PGVECTOR_PASSWORD", "PGPASSWORD", "DATABASE_PASSWORD", 
        "POSTGRES_PASSWORD", "PGVECTOR_HOST", "PGVECTOR_PORT", "PGVECTOR_DATABASE", "PGVECTOR_USER"
    ]
    
    for var in env_vars_to_check:
        value = os.getenv(var)
        diagnosis["environment_variables"][var] = "SET" if value else "NOT_SET"
    
    # Check current provider status
    global unified_store
    if unified_store:
        for name, provider in unified_store.providers.items():
            diagnosis["provider_status"][name] = {
                "enabled": provider.enabled,
                "is_primary": provider == unified_store.primary_provider,
                "type": type(provider).__name__
            }
    
    return {
        "status": "diagnosis_complete",
        "diagnosis": diagnosis,
        "recommendations": [
            "Use /admin/restore-pgvector-access to restore connection",
            "Set DATABASE_URL or PGVECTOR_PASSWORD in environment",
            "Check Render dashboard for database credentials",
            "Verify PostgreSQL service is running"
        ]
    }
'''

def main():
    print("🔧 PGVECTOR ACCESS RESTORATION ENDPOINTS")
    print("=" * 60)
    print("This code creates admin endpoints to restore pgvector access")
    print("when environment variables are not properly set.")
    print()
    print("New endpoints:")
    print("1. POST /admin/restore-pgvector-access - Emergency restoration")
    print("2. GET /admin/pgvector-diagnosis - Diagnose connection issues")
    print()
    print("Admin key: 'restore-pgvector-2025'")
    print()
    print("To implement:")
    print("1. Add this code to api.py")
    print("2. Deploy changes")
    print("3. Call the restore endpoint")
    print("4. Access to 1,152 memories will be restored")
    print()
    print("Example usage:")
    print("curl -X POST 'https://core-nexus-memory-service.onrender.com/admin/restore-pgvector-access?admin_key=restore-pgvector-2025'")

if __name__ == "__main__":
    main()