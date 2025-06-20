#!/usr/bin/env python3
"""
Run emergency ChromaDB sync to fix the critical data redundancy failure
This will sync all 1,149 memories from pgvector to ChromaDB
"""

import asyncio
import os
import sys
import subprocess
from datetime import datetime

def check_environment():
    """Check if we have the necessary environment for sync"""
    print("🔍 Checking sync environment...")
    
    # Check if emergency script exists
    script_path = "python/memory_service/emergency_chromadb_sync_v2.py"
    if not os.path.exists(script_path):
        print(f"❌ Emergency sync script not found at {script_path}")
        return False
        
    # Check if we're in the right directory
    if not os.path.exists("python/memory_service"):
        print("❌ Not in correct directory - need to be in project root")
        return False
        
    print("✅ Environment check passed")
    return True

def run_sync():
    """Execute the emergency sync"""
    print("🚀 RUNNING EMERGENCY CHROMADB SYNC")
    print("="*60)
    print(f"Start time: {datetime.now().isoformat()}")
    print()
    
    # The emergency sync script needs proper environment variables
    # Since we don't have the password, let's use a different approach
    
    # Check if we can use the production service's own connection
    print("🔧 Attempting sync via production service configuration...")
    
    script_path = "python/memory_service/sync_chromadb_safe.py"
    
    if os.path.exists(script_path):
        print(f"Found safe sync script: {script_path}")
        
        try:
            # Change to the correct directory
            os.chdir("python/memory_service")
            
            # Run the safe sync script that uses production config
            print("Executing sync...")
            result = subprocess.run([
                "poetry", "run", "python", "sync_chromadb_safe.py"
            ], capture_output=True, text=True, timeout=600)  # 10 minute timeout
            
            print("STDOUT:")
            print(result.stdout)
            
            if result.stderr:
                print("STDERR:")
                print(result.stderr)
                
            if result.returncode == 0:
                print("✅ Sync completed successfully!")
                return True
            else:
                print(f"❌ Sync failed with return code: {result.returncode}")
                return False
                
        except subprocess.TimeoutExpired:
            print("⏰ Sync timed out after 10 minutes")
            return False
        except Exception as e:
            print(f"❌ Sync failed with exception: {e}")
            return False
    else:
        print(f"❌ Safe sync script not found: {script_path}")
        return False

async def verify_sync():
    """Verify that the sync was successful"""
    print("\n🔍 Verifying sync results...")
    
    import httpx
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get("https://core-nexus-memory-service.onrender.com/health")
            
            if response.status_code == 200:
                health_data = response.json()
                providers = health_data.get("providers", {})
                
                pgvector_count = providers.get("pgvector", {}).get("details", {}).get("details", {}).get("total_vectors", 0)
                chromadb_count = providers.get("chromadb", {}).get("details", {}).get("details", {}).get("total_vectors", 0)
                
                print(f"Post-sync counts:")
                print(f"  pgvector: {pgvector_count} vectors")
                print(f"  ChromaDB: {chromadb_count} vectors")
                print(f"  Sync gap: {pgvector_count - chromadb_count}")
                
                if chromadb_count > 0:
                    sync_percentage = (chromadb_count / pgvector_count) * 100 if pgvector_count > 0 else 0
                    print(f"  Sync completion: {sync_percentage:.1f}%")
                    
                    if sync_percentage >= 95:
                        print("🎉 SYNC SUCCESS: ChromaDB is now synchronized!")
                        return True
                    else:
                        print("⚠️ Partial sync - need to investigate")
                        return False
                else:
                    print("❌ SYNC FAILED: ChromaDB still empty")
                    return False
                    
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return False

async def main():
    """Main execution"""
    print("🚨 EMERGENCY CHROMADB SYNC OPERATION")
    print("="*60)
    print("Goal: Sync 1,149 memories from pgvector to ChromaDB")
    print("Critical: This fixes the catastrophic data redundancy failure")
    print()
    
    # Check environment
    if not check_environment():
        print("❌ Environment check failed - cannot proceed")
        return
        
    # Run the sync
    sync_success = run_sync()
    
    if sync_success:
        # Verify the results
        verification_success = await verify_sync()
        
        if verification_success:
            print("\n🎉 EMERGENCY SYNC COMPLETE!")
            print("="*40)
            print("✅ Data redundancy restored")
            print("✅ ChromaDB synchronized with pgvector")
            print("✅ System now has backup protection")
        else:
            print("\n⚠️ SYNC VERIFICATION FAILED")
            print("="*40)
            print("Sync may have partially completed")
            print("Manual investigation required")
    else:
        print("\n❌ EMERGENCY SYNC FAILED")
        print("="*40)
        print("ChromaDB sync did not complete")
        print("Manual intervention required")
        
        print("\nAlternative approaches:")
        print("1. Check database credentials and try emergency_chromadb_sync_v2.py")
        print("2. Use production database access for direct sync")
        print("3. Create admin endpoint in the service for sync operations")

if __name__ == "__main__":
    asyncio.run(main())