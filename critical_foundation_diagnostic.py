#!/usr/bin/env python3
"""
CRITICAL FOUNDATION DIAGNOSTIC
Identifies why memories aren't being saved or retrieved at all.
This is Priority 1 before any ChromaDB work.
"""

import asyncio
import asyncpg
import json
import requests
import time
from datetime import datetime

# Configuration
PGVECTOR_CONFIG = {
    "host": "dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com",
    "port": 5432,
    "database": "nexus_memory_db",
    "user": "nexus_memory_db_user",
    "password": "2DeDeiIowX5mxkYhQzatzQXGY9Ajl34V"
}

RENDER_SERVICE_URL = "https://core-nexus-memory-service.onrender.com"

class CriticalFoundationDiagnostic:
    def __init__(self):
        self.connection = None
        self.results = {
            "diagnostic_started": datetime.now().isoformat(),
            "tests": {},
            "critical_findings": [],
            "recommendations": []
        }
    
    async def connect_to_database(self):
        """Connect to PostgreSQL database"""
        try:
            print("🔗 Connecting to PostgreSQL database...")
            self.connection = await asyncpg.connect(**PGVECTOR_CONFIG)
            print("✅ Connected to PostgreSQL successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to PostgreSQL: {e}")
            return False
    
    async def test_direct_database_count(self):
        """Test 1: Check actual database content"""
        print("\n📊 TEST 1: Direct Database Analysis")
        print("=" * 40)
        
        try:
            # Get total count
            total_count = await self.connection.fetchval("SELECT COUNT(*) FROM vector_memories")
            print(f"Total memories in database: {total_count}")
            
            # Get recent memories
            recent_memories = await self.connection.fetch("""
                SELECT id, content, created_at, LENGTH(content) as content_length
                FROM vector_memories 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            
            print(f"Recent memories:")
            for i, memory in enumerate(recent_memories, 1):
                print(f"  {i}. ID: {memory['id']}")
                print(f"     Content: {memory['content'][:50]}...")
                print(f"     Created: {memory['created_at']}")
                print(f"     Length: {memory['content_length']} chars")
                print()
            
            # Check for any patterns in creation dates
            date_distribution = await self.connection.fetch("""
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM vector_memories 
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                LIMIT 10
            """)
            
            print("Memory creation by date:")
            for row in date_distribution:
                print(f"  {row['date']}: {row['count']} memories")
            
            self.results["tests"]["direct_database"] = {
                "total_count": total_count,
                "recent_memories": len(recent_memories),
                "status": "success"
            }
            
            if total_count == 0:
                self.results["critical_findings"].append("CRITICAL: Database is completely empty")
            elif total_count > 1000:
                self.results["critical_findings"].append(f"Database has {total_count} memories but API returns 0 - retrieval broken")
            
            return True
            
        except Exception as e:
            print(f"❌ Direct database test failed: {e}")
            self.results["tests"]["direct_database"] = {
                "status": "failed",
                "error": str(e)
            }
            return False
    
    def test_api_memory_creation(self):
        """Test 2: Create memory via API and track it"""
        print("\n📝 TEST 2: API Memory Creation Tracking")
        print("=" * 40)
        
        try:
            # Create test memory
            test_content = f"CRITICAL FOUNDATION TEST: {datetime.now().isoformat()}"
            print(f"Creating test memory: {test_content}")
            
            create_response = requests.post(
                f"{RENDER_SERVICE_URL}/memories",
                json={
                    "content": test_content,
                    "metadata": {
                        "foundation_test": True,
                        "test_timestamp": datetime.now().isoformat()
                    }
                },
                timeout=30
            )
            
            if create_response.status_code == 200:
                create_data = create_response.json()
                memory_id = create_data.get("id")
                print(f"✅ Memory created successfully with ID: {memory_id}")
                
                # Immediately try to retrieve it via API
                print(f"Attempting to retrieve memory {memory_id} via API...")
                
                get_response = requests.get(
                    f"{RENDER_SERVICE_URL}/memories/{memory_id}",
                    timeout=30
                )
                
                if get_response.status_code == 200:
                    print("✅ Memory retrieved successfully via API")
                    retrieved_data = get_response.json()
                    print(f"Retrieved content: {retrieved_data.get('content', 'NO CONTENT')[:50]}...")
                else:
                    print(f"❌ Failed to retrieve memory via API: {get_response.status_code}")
                    print(f"Response: {get_response.text}")
                    self.results["critical_findings"].append(f"Memory {memory_id} created but cannot be retrieved via API")
                
                # Try to find it in general queries
                print("Testing if memory appears in general queries...")
                query_response = requests.get(
                    f"{RENDER_SERVICE_URL}/memories",
                    params={"limit": 20, "query": "CRITICAL FOUNDATION TEST"},
                    timeout=30
                )
                
                if query_response.status_code == 200:
                    query_data = query_response.json()
                    memories = query_data.get("memories", [])
                    found_in_query = any(m.get("id") == memory_id for m in memories)
                    
                    if found_in_query:
                        print("✅ Memory found in general queries")
                    else:
                        print(f"❌ Memory NOT found in general queries (returned {len(memories)} memories)")
                        self.results["critical_findings"].append("Created memory not appearing in general queries")
                else:
                    print(f"❌ General query failed: {query_response.status_code}")
                
                self.results["tests"]["api_creation"] = {
                    "memory_id": memory_id,
                    "created": True,
                    "retrievable": get_response.status_code == 200,
                    "found_in_queries": found_in_query if 'found_in_query' in locals() else False,
                    "status": "success"
                }
                
                return memory_id
                
            else:
                print(f"❌ Failed to create memory: {create_response.status_code}")
                print(f"Response: {create_response.text}")
                self.results["tests"]["api_creation"] = {
                    "status": "failed",
                    "error": f"HTTP {create_response.status_code}"
                }
                self.results["critical_findings"].append("Cannot create memories via API")
                return None
                
        except Exception as e:
            print(f"❌ API creation test failed: {e}")
            self.results["tests"]["api_creation"] = {
                "status": "failed",
                "error": str(e)
            }
            return None
    
    async def test_direct_database_lookup(self, memory_id):
        """Test 3: Check if API-created memory exists in database"""
        print("\n🔍 TEST 3: Direct Database Lookup")
        print("=" * 40)
        
        if not memory_id:
            print("⚠️ No memory ID to test - skipping")
            return False
        
        try:
            print(f"Looking for memory {memory_id} directly in database...")
            
            # Look for the memory in the database
            db_memory = await self.connection.fetchrow("""
                SELECT id, content, created_at, metadata
                FROM vector_memories 
                WHERE id = $1
            """, memory_id)
            
            if db_memory:
                print("✅ Memory found in database!")
                print(f"Content: {db_memory['content']}")
                print(f"Created: {db_memory['created_at']}")
                print(f"Metadata: {db_memory['metadata']}")
                
                self.results["tests"]["database_lookup"] = {
                    "memory_found": True,
                    "status": "success"
                }
                
                # This means the issue is in the API retrieval layer
                self.results["critical_findings"].append("Memory exists in database but API cannot retrieve it - API layer broken")
                
            else:
                print("❌ Memory NOT found in database!")
                self.results["tests"]["database_lookup"] = {
                    "memory_found": False,
                    "status": "success"
                }
                self.results["critical_findings"].append("Memory not saved to database despite API success - storage layer broken")
            
            return db_memory is not None
            
        except Exception as e:
            print(f"❌ Database lookup failed: {e}")
            self.results["tests"]["database_lookup"] = {
                "status": "failed",
                "error": str(e)
            }
            return False
    
    async def test_direct_database_insert(self):
        """Test 4: Bypass API and insert directly into database"""
        print("\n🔧 TEST 4: Direct Database Insert")
        print("=" * 40)
        
        try:
            test_content = f"DIRECT DATABASE TEST: {datetime.now().isoformat()}"
            print(f"Inserting directly into database: {test_content}")
            
            # Create a fake embedding (1536 dimensions of zeros)
            fake_embedding = [0.0] * 1536
            
            # Insert directly
            insert_result = await self.connection.fetchval("""
                INSERT INTO vector_memories (content, embedding, metadata, created_at)
                VALUES ($1, $2, $3, $4)
                RETURNING id
            """, 
                test_content,
                fake_embedding,
                {"direct_test": True, "timestamp": datetime.now().isoformat()},
                datetime.now()
            )
            
            print(f"✅ Direct insert successful with ID: {insert_result}")
            
            # Immediately query it back
            retrieved = await self.connection.fetchrow("""
                SELECT content, created_at FROM vector_memories WHERE id = $1
            """, insert_result)
            
            if retrieved:
                print("✅ Direct insert verified - memory can be retrieved from database")
                print(f"Retrieved content: {retrieved['content']}")
                
                # Now test if API can find this directly-inserted memory
                print("Testing if API can retrieve directly-inserted memory...")
                
                api_response = requests.get(
                    f"{RENDER_SERVICE_URL}/memories/{insert_result}",
                    timeout=30
                )
                
                if api_response.status_code == 200:
                    print("✅ API can retrieve directly-inserted memory")
                    self.results["critical_findings"].append("Direct database insert works and API can retrieve it - API creation layer may be broken")
                else:
                    print("❌ API cannot retrieve directly-inserted memory")
                    self.results["critical_findings"].append("API cannot retrieve memories even when they exist in database - API retrieval layer broken")
                
                self.results["tests"]["direct_insert"] = {
                    "insert_successful": True,
                    "retrievable_via_db": True,
                    "retrievable_via_api": api_response.status_code == 200,
                    "status": "success"
                }
                
                return insert_result
                
            else:
                print("❌ Could not retrieve directly-inserted memory")
                self.results["tests"]["direct_insert"] = {
                    "status": "failed",
                    "error": "Insert returned ID but memory not retrievable"
                }
                return None
                
        except Exception as e:
            print(f"❌ Direct insert failed: {e}")
            self.results["tests"]["direct_insert"] = {
                "status": "failed",
                "error": str(e)
            }
            return None
    
    def test_api_query_endpoints(self):
        """Test 5: Comprehensive API endpoint testing"""
        print("\n🌐 TEST 5: API Endpoint Analysis")
        print("=" * 40)
        
        endpoints_to_test = [
            {"url": "/health", "method": "GET", "description": "Health check"},
            {"url": "/memories", "method": "GET", "description": "Get all memories"},
            {"url": "/memories", "method": "GET", "params": {"limit": 1}, "description": "Get 1 memory"},
            {"url": "/memories", "method": "GET", "params": {"query": ""}, "description": "Empty query"},
            {"url": "/memories", "method": "GET", "params": {"query": "test"}, "description": "Search query"},
        ]
        
        endpoint_results = {}
        
        for endpoint in endpoints_to_test:
            try:
                print(f"Testing {endpoint['method']} {endpoint['url']} - {endpoint['description']}")
                
                if endpoint["method"] == "GET":
                    response = requests.get(
                        f"{RENDER_SERVICE_URL}{endpoint['url']}",
                        params=endpoint.get("params", {}),
                        timeout=30
                    )
                
                print(f"  Status: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if "memories" in data:
                            print(f"  Memories returned: {len(data['memories'])}")
                        if "providers" in data:
                            print(f"  Provider status: {[p for p in data['providers'].keys()]}")
                    except:
                        print(f"  Response: {response.text[:100]}...")
                else:
                    print(f"  Error: {response.text[:200]}")
                
                endpoint_results[f"{endpoint['method']} {endpoint['url']}"] = {
                    "status_code": response.status_code,
                    "description": endpoint['description'],
                    "success": response.status_code == 200
                }
                
            except Exception as e:
                print(f"  Exception: {e}")
                endpoint_results[f"{endpoint['method']} {endpoint['url']}"] = {
                    "status_code": None,
                    "description": endpoint['description'],
                    "error": str(e),
                    "success": False
                }
        
        self.results["tests"]["api_endpoints"] = endpoint_results
        
        # Analyze patterns
        failed_endpoints = [k for k, v in endpoint_results.items() if not v["success"]]
        if failed_endpoints:
            self.results["critical_findings"].append(f"Failed endpoints: {failed_endpoints}")
    
    def generate_critical_recommendations(self):
        """Generate recommendations based on findings"""
        print("\n📋 CRITICAL RECOMMENDATIONS")
        print("=" * 30)
        
        findings = self.results["critical_findings"]
        recommendations = []
        
        if "Database is completely empty" in str(findings):
            recommendations.append("EMERGENCY: Database is empty - complete data loss")
            recommendations.append("Action: Investigate backup and recovery options immediately")
        
        elif "Memory exists in database but API cannot retrieve it" in str(findings):
            recommendations.append("CRITICAL: API retrieval layer is broken")
            recommendations.append("Action: Debug GET /memories endpoints and query logic")
            recommendations.append("Action: Check if unified_store.query_memories is working")
        
        elif "Memory not saved to database despite API success" in str(findings):
            recommendations.append("CRITICAL: Storage layer is broken")
            recommendations.append("Action: Debug store_memory function and database transactions")
            recommendations.append("Action: Check if embeddings are being generated correctly")
        
        if "API cannot retrieve memories even when they exist" in str(findings):
            recommendations.append("URGENT: Complete API breakdown")
            recommendations.append("Action: Rebuild query endpoints from scratch")
        
        # Always recommend these
        recommendations.extend([
            "STOP all ChromaDB work until foundation is fixed",
            "Add comprehensive logging to all storage and retrieval operations",
            "Implement transaction verification for all database operations"
        ])
        
        self.results["recommendations"] = recommendations
        
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")
    
    async def run_complete_diagnostic(self):
        """Run all diagnostic tests"""
        print("🚨 CRITICAL FOUNDATION DIAGNOSTIC")
        print("Priority 1: Fix storage before ChromaDB replication")
        print("=" * 60)
        
        if not await self.connect_to_database():
            return None
        
        try:
            # Test 1: Check database content
            await self.test_direct_database_count()
            
            # Test 2: Create memory via API
            memory_id = self.test_api_memory_creation()
            
            # Test 3: Check if API memory exists in database
            if memory_id:
                await self.test_direct_database_lookup(memory_id)
            
            # Test 4: Direct database insert
            await self.test_direct_database_insert()
            
            # Test 5: API endpoint analysis
            self.test_api_query_endpoints()
            
            # Generate recommendations
            self.generate_critical_recommendations()
            
            return self.results
            
        finally:
            if self.connection:
                await self.connection.close()
                print("🔗 Database connection closed")

async def main():
    """Main entry point"""
    try:
        diagnostic = CriticalFoundationDiagnostic()
        results = await diagnostic.run_complete_diagnostic()
        
        if results:
            # Save results
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            results_file = f"critical_foundation_diagnostic_{timestamp}.json"
            
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            print(f"\n📄 Diagnostic results saved to: {results_file}")
            
            # Determine severity
            critical_count = len(results["critical_findings"])
            print(f"\n🚨 CRISIS LEVEL: {critical_count} critical findings identified")
            
            if critical_count >= 3:
                print("🚨 CATASTROPHIC: Foundation completely broken")
                return 1
            elif critical_count >= 1:
                print("❌ CRITICAL: Major foundation issues")
                return 1
            else:
                print("✅ Foundation appears functional")
                return 0
        else:
            print("\n❌ Diagnostic failed to complete")
            return 1
            
    except Exception as e:
        print(f"❌ Critical diagnostic failed: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))