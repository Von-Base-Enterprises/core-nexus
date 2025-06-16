#!/usr/bin/env python3
"""
Comprehensive Query Test Suite
Tests every layer of the query functionality to isolate why queries return 0 memories.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import asyncpg
import httpx
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('comprehensive_query_test.log')
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
PGVECTOR_CONFIG = {
    "host": os.getenv("PGVECTOR_HOST", "dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com"),
    "port": int(os.getenv("PGVECTOR_PORT", "5432")),
    "database": os.getenv("PGVECTOR_DATABASE", "nexus_memory_db"),
    "user": os.getenv("PGVECTOR_USER", "nexus_memory_db_user"),
    "password": os.getenv("PGVECTOR_PASSWORD", ""),
}

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


class ComprehensiveQueryTest:
    """Test suite for comprehensive query testing."""
    
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "errors": []
            }
        }
        self.conn = None
        
    async def setup(self):
        """Setup database connection."""
        try:
            self.conn = await asyncpg.connect(**PGVECTOR_CONFIG)
            logger.info("Database connection established")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            self.results["summary"]["errors"].append(f"Database connection failed: {str(e)}")
            return False
            
    async def teardown(self):
        """Cleanup database connection."""
        if self.conn:
            await self.conn.close()
            
    def record_test(self, test_name: str, passed: bool, details: Dict[str, Any]):
        """Record test results."""
        self.results["tests"][test_name] = {
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.results["summary"]["total"] += 1
        if passed:
            self.results["summary"]["passed"] += 1
        else:
            self.results["summary"]["failed"] += 1
            
    async def test_raw_database_queries(self):
        """Test 1: Direct database queries to confirm data exists."""
        test_name = "raw_database_queries"
        logger.info(f"\n{'='*60}")
        logger.info(f"Running Test: {test_name}")
        logger.info(f"{'='*60}")
        
        details = {}
        passed = True
        
        try:
            # Test 1.1: Check if vector_memories table exists
            query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'vector_memories'
            );
            """
            table_exists = await self.conn.fetchval(query)
            details["table_exists"] = table_exists
            logger.info(f"Table 'vector_memories' exists: {table_exists}")
            
            if not table_exists:
                passed = False
                
            # Test 1.2: Get table schema
            query = """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' 
            AND table_name = 'vector_memories'
            ORDER BY ordinal_position;
            """
            schema = await self.conn.fetch(query)
            details["schema"] = [dict(row) for row in schema]
            logger.info(f"Table schema: {json.dumps(details['schema'], indent=2)}")
            
            # Test 1.3: Count total records
            for table_ref in ['vector_memories', 'public.vector_memories']:
                try:
                    query = f"SELECT COUNT(*) FROM {table_ref};"
                    count = await self.conn.fetchval(query)
                    details[f"total_count_{table_ref}"] = count
                    logger.info(f"Total records in {table_ref}: {count}")
                    if count == 0:
                        passed = False
                except Exception as e:
                    details[f"error_{table_ref}"] = str(e)
                    logger.error(f"Error querying {table_ref}: {e}")
                    
            # Test 1.4: Sample records
            query = """
            SELECT id, user_id, content, 
                   array_length(embedding, 1) as embedding_dim,
                   created_at, updated_at
            FROM public.vector_memories
            LIMIT 5;
            """
            samples = await self.conn.fetch(query)
            details["sample_records"] = [dict(row) for row in samples]
            logger.info(f"Sample records: {len(samples)}")
            for sample in samples:
                logger.debug(f"  - ID: {sample['id']}, User: {sample['user_id']}, "
                           f"Content: {sample['content'][:50]}..., "
                           f"Embedding dim: {sample['embedding_dim']}")
                           
            # Test 1.5: Check for NULL embeddings
            query = """
            SELECT COUNT(*) as null_count
            FROM public.vector_memories
            WHERE embedding IS NULL;
            """
            null_count = await self.conn.fetchval(query)
            details["null_embeddings"] = null_count
            logger.info(f"Records with NULL embeddings: {null_count}")
            
            # Test 1.6: Check embedding dimensions
            query = """
            SELECT DISTINCT array_length(embedding, 1) as dim, COUNT(*) as count
            FROM public.vector_memories
            WHERE embedding IS NOT NULL
            GROUP BY dim;
            """
            dims = await self.conn.fetch(query)
            details["embedding_dimensions"] = [dict(row) for row in dims]
            logger.info(f"Embedding dimensions distribution: {details['embedding_dimensions']}")
            
        except Exception as e:
            passed = False
            details["error"] = str(e)
            logger.error(f"Test failed with error: {e}")
            
        self.record_test(test_name, passed, details)
        
    async def test_pgvector_provider_direct(self):
        """Test 2: Test PgVectorProvider methods directly."""
        test_name = "pgvector_provider_direct"
        logger.info(f"\n{'='*60}")
        logger.info(f"Running Test: {test_name}")
        logger.info(f"{'='*60}")
        
        details = {}
        passed = True
        
        try:
            # Import and initialize provider
            from src.memory_service.providers import PgVectorProvider
            
            provider = PgVectorProvider()
            await provider.initialize()
            details["provider_initialized"] = True
            logger.info("PgVectorProvider initialized successfully")
            
            # Test 2.1: Query all memories (empty query)
            logger.info("\nTesting empty query (should return all memories)...")
            memories = await provider.query_memories(
                query_text="",
                user_id="test_user",
                limit=10
            )
            details["empty_query_count"] = len(memories)
            logger.info(f"Empty query returned: {len(memories)} memories")
            if len(memories) == 0:
                passed = False
                
            # Test 2.2: Query with search text
            logger.info("\nTesting search query...")
            search_memories = await provider.query_memories(
                query_text="test",
                user_id="test_user",
                limit=10
            )
            details["search_query_count"] = len(search_memories)
            logger.info(f"Search query returned: {len(search_memories)} memories")
            
            # Test 2.3: Get stats
            logger.info("\nTesting get_stats...")
            stats = await provider.get_stats()
            details["stats"] = stats
            logger.info(f"Provider stats: {json.dumps(stats, indent=2)}")
            
            # Test 2.4: Direct SQL query through provider
            if hasattr(provider, 'pool') and provider.pool:
                async with provider.pool.acquire() as conn:
                    count = await conn.fetchval("SELECT COUNT(*) FROM public.vector_memories")
                    details["direct_pool_count"] = count
                    logger.info(f"Direct pool query count: {count}")
                    
        except Exception as e:
            passed = False
            details["error"] = str(e)
            logger.error(f"Test failed with error: {e}")
            
        self.record_test(test_name, passed, details)
        
    async def test_unified_store(self):
        """Test 3: Test UnifiedStore query methods."""
        test_name = "unified_store"
        logger.info(f"\n{'='*60}")
        logger.info(f"Running Test: {test_name}")
        logger.info(f"{'='*60}")
        
        details = {}
        passed = True
        
        try:
            # Import and initialize store
            from src.memory_service.unified_store import UnifiedStore
            
            store = UnifiedStore()
            await store.initialize()
            details["store_initialized"] = True
            details["active_providers"] = [p.__class__.__name__ for p in store.providers]
            logger.info(f"UnifiedStore initialized with providers: {details['active_providers']}")
            
            # Test 3.1: Query memories
            logger.info("\nTesting UnifiedStore query...")
            memories = await store.query_memories(
                query_text="",
                user_id="test_user",
                limit=10
            )
            details["query_count"] = len(memories)
            logger.info(f"UnifiedStore query returned: {len(memories)} memories")
            if len(memories) == 0:
                passed = False
                
            # Test 3.2: Get stats
            logger.info("\nTesting UnifiedStore stats...")
            stats = await store.get_stats()
            details["stats"] = stats
            logger.info(f"UnifiedStore stats: {json.dumps(stats, indent=2)}")
            
            # Test 3.3: Check fallback behavior
            if hasattr(store, '_execute_with_fallback'):
                logger.info("\nTesting fallback mechanism...")
                result = await store._execute_with_fallback(
                    lambda p: p.query_memories("", "test_user", 10)
                )
                details["fallback_result_count"] = len(result) if result else 0
                logger.info(f"Fallback query returned: {details['fallback_result_count']} memories")
                
        except Exception as e:
            passed = False
            details["error"] = str(e)
            logger.error(f"Test failed with error: {e}")
            
        self.record_test(test_name, passed, details)
        
    async def test_api_endpoints(self):
        """Test 4: Test API endpoints."""
        test_name = "api_endpoints"
        logger.info(f"\n{'='*60}")
        logger.info(f"Running Test: {test_name}")
        logger.info(f"{'='*60}")
        
        details = {}
        passed = True
        
        async with httpx.AsyncClient() as client:
            try:
                # Test 4.1: Health check
                logger.info("\nTesting health endpoint...")
                response = await client.get(f"{API_BASE_URL}/health")
                details["health_status"] = response.status_code
                details["health_response"] = response.json() if response.status_code == 200 else None
                logger.info(f"Health check status: {response.status_code}")
                
                # Test 4.2: Stats endpoint
                logger.info("\nTesting stats endpoint...")
                response = await client.get(f"{API_BASE_URL}/stats")
                details["stats_status"] = response.status_code
                if response.status_code == 200:
                    stats = response.json()
                    details["stats_response"] = stats
                    logger.info(f"Stats response: {json.dumps(stats, indent=2)}")
                    
                # Test 4.3: Query endpoint (empty query)
                logger.info("\nTesting query endpoint with empty query...")
                response = await client.post(
                    f"{API_BASE_URL}/query",
                    json={
                        "query": "",
                        "user_id": "test_user",
                        "limit": 10
                    }
                )
                details["empty_query_status"] = response.status_code
                if response.status_code == 200:
                    memories = response.json()
                    details["empty_query_count"] = len(memories)
                    logger.info(f"Empty query returned: {len(memories)} memories")
                    if len(memories) == 0:
                        passed = False
                else:
                    passed = False
                    details["empty_query_error"] = response.text
                    
                # Test 4.4: Query endpoint (search query)
                logger.info("\nTesting query endpoint with search query...")
                response = await client.post(
                    f"{API_BASE_URL}/query",
                    json={
                        "query": "test",
                        "user_id": "test_user",
                        "limit": 10
                    }
                )
                details["search_query_status"] = response.status_code
                if response.status_code == 200:
                    memories = response.json()
                    details["search_query_count"] = len(memories)
                    logger.info(f"Search query returned: {len(memories)} memories")
                    
            except Exception as e:
                passed = False
                details["error"] = str(e)
                logger.error(f"Test failed with error: {e}")
                
        self.record_test(test_name, passed, details)
        
    async def test_schema_issues(self):
        """Test 5: Check for schema/table issues."""
        test_name = "schema_issues"
        logger.info(f"\n{'='*60}")
        logger.info(f"Running Test: {test_name}")
        logger.info(f"{'='*60}")
        
        details = {}
        passed = True
        
        try:
            # Test 5.1: Check all schemas
            query = """
            SELECT DISTINCT table_schema, table_name
            FROM information_schema.tables
            WHERE table_name LIKE '%memor%'
            ORDER BY table_schema, table_name;
            """
            tables = await self.conn.fetch(query)
            details["memory_tables"] = [dict(row) for row in tables]
            logger.info(f"Found memory-related tables: {details['memory_tables']}")
            
            # Test 5.2: Check search path
            query = "SHOW search_path;"
            search_path = await self.conn.fetchval(query)
            details["search_path"] = search_path
            logger.info(f"Current search path: {search_path}")
            
            # Test 5.3: Check permissions
            query = """
            SELECT privilege_type
            FROM information_schema.table_privileges
            WHERE grantee = %s
            AND table_schema = 'public'
            AND table_name = 'vector_memories';
            """
            privileges = await self.conn.fetch(query, PGVECTOR_CONFIG["user"])
            details["privileges"] = [row["privilege_type"] for row in privileges]
            logger.info(f"User privileges: {details['privileges']}")
            
            # Test 5.4: Check indexes
            query = """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            AND tablename = 'vector_memories';
            """
            indexes = await self.conn.fetch(query)
            details["indexes"] = [dict(row) for row in indexes]
            logger.info(f"Table indexes: {len(indexes)}")
            for idx in indexes:
                logger.debug(f"  - {idx['indexname']}: {idx['indexdef']}")
                
        except Exception as e:
            passed = False
            details["error"] = str(e)
            logger.error(f"Test failed with error: {e}")
            
        self.record_test(test_name, passed, details)
        
    async def test_embedding_queries(self):
        """Test 6: Test with and without embeddings."""
        test_name = "embedding_queries"
        logger.info(f"\n{'='*60}")
        logger.info(f"Running Test: {test_name}")
        logger.info(f"{'='*60}")
        
        details = {}
        passed = True
        
        try:
            # Test 6.1: Query records with embeddings
            query = """
            SELECT id, user_id, content, 
                   array_length(embedding, 1) as embedding_dim
            FROM public.vector_memories
            WHERE embedding IS NOT NULL
            LIMIT 5;
            """
            with_embeddings = await self.conn.fetch(query)
            details["with_embeddings_count"] = len(with_embeddings)
            logger.info(f"Records with embeddings: {len(with_embeddings)}")
            
            # Test 6.2: Query records without embeddings
            query = """
            SELECT id, user_id, content
            FROM public.vector_memories
            WHERE embedding IS NULL
            LIMIT 5;
            """
            without_embeddings = await self.conn.fetch(query)
            details["without_embeddings_count"] = len(without_embeddings)
            logger.info(f"Records without embeddings: {len(without_embeddings)}")
            
            # Test 6.3: Test vector similarity search
            if len(with_embeddings) > 0:
                # Get a sample embedding
                query = """
                SELECT embedding
                FROM public.vector_memories
                WHERE embedding IS NOT NULL
                LIMIT 1;
                """
                sample_embedding = await self.conn.fetchval(query)
                
                if sample_embedding:
                    # Search similar vectors
                    query = """
                    SELECT id, content, 
                           1 - (embedding <=> $1::vector) as similarity
                    FROM public.vector_memories
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> $1::vector
                    LIMIT 5;
                    """
                    similar = await self.conn.fetch(query, sample_embedding)
                    details["similarity_search_count"] = len(similar)
                    logger.info(f"Similarity search returned: {len(similar)} results")
                    for row in similar:
                        logger.debug(f"  - ID: {row['id']}, Similarity: {row['similarity']:.4f}")
                        
        except Exception as e:
            passed = False
            details["error"] = str(e)
            logger.error(f"Test failed with error: {e}")
            
        self.record_test(test_name, passed, details)
        
    async def test_query_variations(self):
        """Test 7: Test empty queries vs search queries."""
        test_name = "query_variations"
        logger.info(f"\n{'='*60}")
        logger.info(f"Running Test: {test_name}")
        logger.info(f"{'='*60}")
        
        details = {}
        passed = True
        
        try:
            # Test different query patterns
            queries = [
                ("empty_string", ""),
                ("null_query", None),
                ("whitespace", "   "),
                ("simple_word", "test"),
                ("multiple_words", "test memory"),
                ("special_chars", "test@#$%"),
            ]
            
            for query_type, query_text in queries:
                try:
                    if query_text is None:
                        sql = """
                        SELECT id, content
                        FROM public.vector_memories
                        ORDER BY created_at DESC
                        LIMIT 5;
                        """
                        results = await self.conn.fetch(sql)
                    else:
                        sql = """
                        SELECT id, content
                        FROM public.vector_memories
                        WHERE content ILIKE $1
                        ORDER BY created_at DESC
                        LIMIT 5;
                        """
                        results = await self.conn.fetch(sql, f"%{query_text}%")
                        
                    details[f"{query_type}_count"] = len(results)
                    logger.info(f"Query '{query_type}' returned: {len(results)} results")
                    
                except Exception as e:
                    details[f"{query_type}_error"] = str(e)
                    logger.error(f"Query '{query_type}' failed: {e}")
                    
        except Exception as e:
            passed = False
            details["error"] = str(e)
            logger.error(f"Test failed with error: {e}")
            
        self.record_test(test_name, passed, details)
        
    async def test_connection_pool_timing(self):
        """Test 8: Check connection pool timing issues."""
        test_name = "connection_pool_timing"
        logger.info(f"\n{'='*60}")
        logger.info(f"Running Test: {test_name}")
        logger.info(f"{'='*60}")
        
        details = {}
        passed = True
        
        try:
            import asyncpg
            import time
            
            # Test 8.1: Create new pool and test immediately
            logger.info("Testing immediate query after pool creation...")
            start_time = time.time()
            pool = await asyncpg.create_pool(**PGVECTOR_CONFIG, min_size=1, max_size=5)
            pool_creation_time = time.time() - start_time
            details["pool_creation_time"] = pool_creation_time
            logger.info(f"Pool created in {pool_creation_time:.3f} seconds")
            
            # Immediate query
            start_time = time.time()
            async with pool.acquire() as conn:
                count = await conn.fetchval("SELECT COUNT(*) FROM public.vector_memories")
            first_query_time = time.time() - start_time
            details["first_query_time"] = first_query_time
            details["immediate_count"] = count
            logger.info(f"First query completed in {first_query_time:.3f} seconds, count: {count}")
            
            # Test 8.2: Multiple rapid queries
            logger.info("\nTesting multiple rapid queries...")
            query_times = []
            for i in range(5):
                start_time = time.time()
                async with pool.acquire() as conn:
                    await conn.fetchval("SELECT COUNT(*) FROM public.vector_memories")
                query_time = time.time() - start_time
                query_times.append(query_time)
                
            details["rapid_query_times"] = query_times
            details["avg_query_time"] = sum(query_times) / len(query_times)
            logger.info(f"Average query time: {details['avg_query_time']:.3f} seconds")
            
            await pool.close()
            
        except Exception as e:
            passed = False
            details["error"] = str(e)
            logger.error(f"Test failed with error: {e}")
            
        self.record_test(test_name, passed, details)
        
    async def test_fallback_mechanisms(self):
        """Test 9: Test all fallback mechanisms."""
        test_name = "fallback_mechanisms"
        logger.info(f"\n{'='*60}")
        logger.info(f"Running Test: {test_name}")
        logger.info(f"{'='*60}")
        
        details = {}
        passed = True
        
        try:
            from src.memory_service.unified_store import UnifiedStore
            
            store = UnifiedStore()
            await store.initialize()
            
            # Test 9.1: Test text search fallback
            logger.info("Testing text search fallback...")
            # This should trigger text search if no embedding
            memories = await store.query_memories(
                query_text="unique_test_string_12345",
                user_id="test_user",
                limit=10
            )
            details["text_search_count"] = len(memories)
            logger.info(f"Text search returned: {len(memories)} memories")
            
            # Test 9.2: Test emergency search
            if hasattr(store, 'emergency_search'):
                logger.info("\nTesting emergency search...")
                emergency_results = await store.emergency_search(
                    query_text="",
                    user_id="test_user",
                    limit=10
                )
                details["emergency_search_count"] = len(emergency_results) if emergency_results else 0
                logger.info(f"Emergency search returned: {details['emergency_search_count']} memories")
                
        except Exception as e:
            passed = False
            details["error"] = str(e)
            logger.error(f"Test failed with error: {e}")
            
        self.record_test(test_name, passed, details)
        
    async def test_stats_data_mismatch(self):
        """Test 10: Test stats vs actual data mismatches."""
        test_name = "stats_data_mismatch"
        logger.info(f"\n{'='*60}")
        logger.info(f"Running Test: {test_name}")
        logger.info(f"{'='*60}")
        
        details = {}
        passed = True
        
        try:
            # Get actual count from database
            actual_count = await self.conn.fetchval("SELECT COUNT(*) FROM public.vector_memories")
            details["actual_count"] = actual_count
            logger.info(f"Actual database count: {actual_count}")
            
            # Get stats from API
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{API_BASE_URL}/stats")
                if response.status_code == 200:
                    stats = response.json()
                    reported_count = stats.get("total_memories", 0)
                    details["reported_count"] = reported_count
                    details["mismatch"] = actual_count != reported_count
                    logger.info(f"Stats reported count: {reported_count}")
                    logger.info(f"Mismatch detected: {details['mismatch']}")
                    
                    if details["mismatch"]:
                        passed = False
                        
            # Check for orphaned records
            query = """
            SELECT COUNT(*) as orphaned_count
            FROM public.vector_memories
            WHERE user_id IS NULL OR user_id = '';
            """
            orphaned = await self.conn.fetchval(query)
            details["orphaned_records"] = orphaned
            logger.info(f"Orphaned records: {orphaned}")
            
        except Exception as e:
            passed = False
            details["error"] = str(e)
            logger.error(f"Test failed with error: {e}")
            
        self.record_test(test_name, passed, details)
        
    async def run_all_tests(self):
        """Run all tests in sequence."""
        logger.info("="*80)
        logger.info("COMPREHENSIVE QUERY TEST SUITE")
        logger.info("="*80)
        logger.info(f"Started at: {datetime.now()}")
        logger.info(f"Database: {PGVECTOR_CONFIG['host']}:{PGVECTOR_CONFIG['port']}/{PGVECTOR_CONFIG['database']}")
        logger.info(f"API URL: {API_BASE_URL}")
        logger.info("="*80)
        
        if not await self.setup():
            logger.error("Failed to setup database connection. Aborting tests.")
            return self.results
            
        # Run all tests
        test_methods = [
            self.test_raw_database_queries,
            self.test_pgvector_provider_direct,
            self.test_unified_store,
            self.test_api_endpoints,
            self.test_schema_issues,
            self.test_embedding_queries,
            self.test_query_variations,
            self.test_connection_pool_timing,
            self.test_fallback_mechanisms,
            self.test_stats_data_mismatch,
        ]
        
        for test_method in test_methods:
            try:
                await test_method()
            except Exception as e:
                logger.error(f"Test {test_method.__name__} crashed: {e}")
                self.record_test(test_method.__name__, False, {"crash_error": str(e)})
                
        await self.teardown()
        
        # Generate summary
        logger.info("\n" + "="*80)
        logger.info("TEST SUMMARY")
        logger.info("="*80)
        logger.info(f"Total tests: {self.results['summary']['total']}")
        logger.info(f"Passed: {self.results['summary']['passed']}")
        logger.info(f"Failed: {self.results['summary']['failed']}")
        logger.info(f"Success rate: {(self.results['summary']['passed'] / self.results['summary']['total'] * 100):.1f}%")
        
        # Identify root cause
        logger.info("\n" + "="*80)
        logger.info("ROOT CAUSE ANALYSIS")
        logger.info("="*80)
        
        failed_tests = [name for name, result in self.results["tests"].items() if not result["passed"]]
        if failed_tests:
            logger.error(f"Failed tests: {', '.join(failed_tests)}")
            
            # Analyze common failure patterns
            if "raw_database_queries" in failed_tests:
                logger.error("❌ DATABASE ISSUE: No data found in database")
            elif "pgvector_provider_direct" in failed_tests:
                logger.error("❌ PROVIDER ISSUE: PgVectorProvider failing to query data")
            elif "unified_store" in failed_tests:
                logger.error("❌ STORE ISSUE: UnifiedStore failing to query data")
            elif "api_endpoints" in failed_tests:
                logger.error("❌ API ISSUE: API endpoints not returning data")
            else:
                logger.error("❌ UNKNOWN ISSUE: Check detailed test results")
                
        else:
            logger.info("✅ All tests passed!")
            
        # Save results to file
        with open("comprehensive_query_test_results.json", "w") as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"\nDetailed results saved to: comprehensive_query_test_results.json")
        
        return self.results


async def main():
    """Main entry point."""
    test_suite = ComprehensiveQueryTest()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())