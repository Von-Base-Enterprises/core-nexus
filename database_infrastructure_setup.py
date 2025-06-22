#!/usr/bin/env python3
"""
Database Infrastructure Setup for 10x Vector Optimization

Sets up the production database infrastructure for the optimized vector storage
and migration tracking system.
"""

import asyncio
import asyncpg
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseInfrastructureSetup:
    """Database infrastructure setup for vector optimization."""
    
    def __init__(self):
        """Initialize the database setup manager."""
        self.connection_pool = None
        
        # Database configuration
        self.db_config = {
            'host': os.getenv('PGVECTOR_HOST', 'dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com'),
            'port': int(os.getenv('PGVECTOR_PORT', '5432')),
            'database': os.getenv('PGVECTOR_DATABASE', 'nexus_memory_db'),
            'user': os.getenv('PGVECTOR_USER', 'nexus_memory_db_user'),
            'password': os.getenv('PGVECTOR_PASSWORD')
        }
        
        if not self.db_config['password']:
            raise ValueError("PGVECTOR_PASSWORD environment variable must be set")
    
    async def connect_to_database(self):
        """Connect to the production database."""
        try:
            logger.info("🔌 Connecting to production database...")
            
            conn_str = (
                f"postgresql://{self.db_config['user']}:{self.db_config['password']}@"
                f"{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
            )
            
            self.connection_pool = await asyncpg.create_pool(
                conn_str,
                min_size=1,
                max_size=3,
                command_timeout=60
            )
            
            async with self.connection_pool.acquire() as conn:
                # Test connection and get database info
                db_version = await conn.fetchval("SELECT version()")
                vector_extension = await conn.fetchval(
                    "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
                )
                vector_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM vector_memories WHERE embedding IS NOT NULL"
                )
                
                logger.info(f"✅ Connected to PostgreSQL: {db_version.split()[1]}")
                logger.info(f"✅ pgvector extension: v{vector_extension}")
                logger.info(f"✅ Current vectors in production: {vector_count}")
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            raise
    
    async def execute_migration_sql(self):
        """Execute the migration SQL to create optimized infrastructure."""
        logger.info("🏗️ Executing database migration 007...")
        
        # Read the migration SQL file
        migration_file = Path(__file__).parent / "python/memory_service/migrations/007_create_optimized_vector_tables.sql"
        
        if not migration_file.exists():
            raise FileNotFoundError(f"Migration file not found: {migration_file}")
        
        migration_sql = migration_file.read_text()
        
        # Split migration into main part and concurrent indexes
        sql_parts = migration_sql.split("-- =====================================================\n-- OPTIMIZED INDEXES\n-- =====================================================")
        
        main_sql = sql_parts[0]
        if len(sql_parts) > 1:
            indexes_sql = "-- OPTIMIZED INDEXES\n" + sql_parts[1]
        else:
            indexes_sql = ""
        
        async with self.connection_pool.acquire() as conn:
            try:
                # Execute main migration in a transaction
                logger.info("📋 Executing main migration (tables, functions, views)...")
                async with conn.transaction():
                    await conn.execute(main_sql)
                
                logger.info("✅ Main migration completed successfully")
                
                # Execute concurrent indexes separately (outside transaction)
                if indexes_sql:
                    logger.info("🔧 Creating concurrent indexes...")
                    
                    # Extract individual CREATE INDEX CONCURRENTLY statements
                    index_statements = []
                    for line in indexes_sql.split('\n'):
                        if line.strip().startswith('CREATE INDEX CONCURRENTLY'):
                            index_statements.append(line.strip())
                    
                    for i, index_stmt in enumerate(index_statements):
                        logger.info(f"🔧 Creating index {i+1}/{len(index_statements)}...")
                        await conn.execute(index_stmt)
                    
                    logger.info("✅ All concurrent indexes created successfully")
                
            except Exception as e:
                logger.error(f"❌ Migration failed: {e}")
                raise
    
    async def validate_infrastructure(self) -> Dict[str, Any]:
        """Validate that the infrastructure was set up correctly."""
        logger.info("🔍 Validating database infrastructure...")
        
        validation_results = {
            'tables_created': False,
            'indexes_created': False,
            'views_created': False,
            'triggers_created': False,
            'migration_progress_initialized': False,
            'performance_baseline': {}
        }
        
        async with self.connection_pool.acquire() as conn:
            try:
                # Check if tables were created
                tables_query = """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('vector_memories_optimized', 'migration_batches', 'migration_progress', 'query_performance_metrics', 'ab_test_results')
                """
                
                tables = await conn.fetch(tables_query)
                table_names = [row['table_name'] for row in tables]
                
                expected_tables = ['vector_memories_optimized', 'migration_batches', 'migration_progress', 'query_performance_metrics', 'ab_test_results']
                validation_results['tables_created'] = all(table in table_names for table in expected_tables)
                
                logger.info(f"✅ Tables created: {len(table_names)}/5 - {table_names}")
                
                # Check if indexes were created
                indexes_query = """
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'vector_memories_optimized'
                """
                
                indexes = await conn.fetch(indexes_query)
                index_names = [row['indexname'] for row in indexes]
                
                hnsw_index_exists = any('hnsw' in name for name in index_names)
                validation_results['indexes_created'] = hnsw_index_exists and len(index_names) >= 3
                
                logger.info(f"✅ Indexes created: {len(index_names)} indexes, HNSW: {hnsw_index_exists}")
                
                # Check if views were created
                views_query = """
                SELECT viewname 
                FROM pg_views 
                WHERE schemaname = 'public' 
                AND viewname IN ('migration_overview', 'performance_comparison', 'recent_batch_status')
                """
                
                views = await conn.fetch(views_query)
                view_names = [row['viewname'] for row in views]
                validation_results['views_created'] = len(view_names) >= 3
                
                logger.info(f"✅ Views created: {len(view_names)}/3 - {view_names}")
                
                # Check if triggers were created
                triggers_query = """
                SELECT trigger_name 
                FROM information_schema.triggers 
                WHERE event_object_table = 'vector_memories_optimized'
                """
                
                triggers = await conn.fetch(triggers_query)
                trigger_names = [row['trigger_name'] for row in triggers]
                validation_results['triggers_created'] = len(trigger_names) >= 2
                
                logger.info(f"✅ Triggers created: {len(trigger_names)} triggers")
                
                # Check migration progress initialization
                progress_count = await conn.fetchval("SELECT COUNT(*) FROM migration_progress")
                validation_results['migration_progress_initialized'] = progress_count > 0
                
                if validation_results['migration_progress_initialized']:
                    progress_info = await conn.fetchrow("SELECT * FROM migration_progress ORDER BY created_at DESC LIMIT 1")
                    logger.info(f"✅ Migration progress initialized: {progress_info['total_vectors_to_migrate']} vectors to migrate")
                
                # Get performance baseline from original table
                # Note: We'll estimate dimensions from our previous analysis (19,226D average)
                baseline_query = """
                SELECT 
                    COUNT(*) as vector_count
                FROM vector_memories 
                WHERE embedding IS NOT NULL
                """
                
                baseline = await conn.fetchrow(baseline_query)
                validation_results['performance_baseline'] = {
                    'vector_count': baseline['vector_count'],
                    'avg_dimensions': 19226,  # From our previous validation
                    'max_dimensions': 19292,  # From our previous validation
                    'min_dimensions': 19187   # From our previous validation
                }
                
                logger.info(f"✅ Performance baseline: {baseline['vector_count']} vectors, avg 19,226D (from validation)")
                
            except Exception as e:
                logger.error(f"❌ Validation failed: {e}")
                raise
        
        return validation_results
    
    async def create_initial_test_data(self):
        """Create some initial test data to validate the infrastructure."""
        logger.info("🧪 Creating initial test data...")
        
        async with self.connection_pool.acquire() as conn:
            try:
                # Insert a test vector into the optimized table
                test_embedding = [0.1] * 1536  # Simple test vector
                
                await conn.execute("""
                    INSERT INTO vector_memories_optimized (
                        id, content, embedding, migration_status, original_dimensions
                    ) VALUES (
                        gen_random_uuid(), 
                        'Test vector for infrastructure validation', 
                        $1::vector, 
                        'verified', 
                        19200
                    )
                """, test_embedding)
                
                # Test the HNSW index with a simple query
                test_query_start = time.perf_counter()
                result = await conn.fetchrow("""
                    SELECT id, content, embedding <=> $1::vector as distance
                    FROM vector_memories_optimized
                    ORDER BY embedding <=> $1::vector
                    LIMIT 1
                """, test_embedding)
                test_query_time = (time.perf_counter() - test_query_start) * 1000
                
                logger.info(f"✅ Test query successful: {test_query_time:.2f}ms latency")
                logger.info(f"✅ Test result: {result['content'][:50]}... (distance: {result['distance']:.6f})")
                
                # Insert test performance metrics
                await conn.execute("""
                    INSERT INTO query_performance_metrics (
                        query_type, table_type, latency_ms, result_count, vector_dimensions
                    ) VALUES (
                        'search', 'optimized', $1, 1, 1536
                    )
                """, test_query_time)
                
                logger.info("✅ Test data created and infrastructure validated")
                
            except Exception as e:
                logger.error(f"❌ Test data creation failed: {e}")
                raise
    
    async def setup_monitoring_queries(self):
        """Set up helpful monitoring queries for the infrastructure."""
        logger.info("📊 Setting up monitoring queries...")
        
        monitoring_queries = {
            'migration_overview': "SELECT * FROM migration_overview",
            'performance_comparison': "SELECT * FROM performance_comparison",
            'recent_batches': "SELECT * FROM recent_batch_status",
            'table_sizes': """
                SELECT 
                    schemaname,
                    tablename,
                    attname,
                    n_distinct,
                    correlation,
                    most_common_vals
                FROM pg_stats 
                WHERE tablename IN ('vector_memories', 'vector_memories_optimized')
            """,
            'index_usage': """
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_tup_read,
                    idx_tup_fetch
                FROM pg_stat_user_indexes 
                WHERE tablename IN ('vector_memories', 'vector_memories_optimized')
            """
        }
        
        async with self.connection_pool.acquire() as conn:
            for query_name, query_sql in monitoring_queries.items():
                try:
                    result = await conn.fetch(query_sql)
                    logger.info(f"✅ {query_name}: {len(result)} rows available")
                except Exception as e:
                    logger.warning(f"⚠️ {query_name} query failed: {e}")
    
    async def run_complete_setup(self) -> Dict[str, Any]:
        """Run the complete database infrastructure setup."""
        start_time = time.time()
        logger.info("🚀 Starting complete database infrastructure setup...")
        
        setup_results = {
            'setup_started_at': datetime.now().isoformat(),
            'setup_duration_seconds': 0,
            'connection_successful': False,
            'migration_successful': False,
            'validation_results': {},
            'test_data_created': False,
            'monitoring_setup': False,
            'status': 'failed'
        }
        
        try:
            # Step 1: Connect to database
            await self.connect_to_database()
            setup_results['connection_successful'] = True
            
            # Step 2: Execute migration SQL
            await self.execute_migration_sql()
            setup_results['migration_successful'] = True
            
            # Step 3: Validate infrastructure
            validation_results = await self.validate_infrastructure()
            setup_results['validation_results'] = validation_results
            
            # Step 4: Create test data
            await self.create_initial_test_data()
            setup_results['test_data_created'] = True
            
            # Step 5: Setup monitoring
            await self.setup_monitoring_queries()
            setup_results['monitoring_setup'] = True
            
            # Calculate success
            all_validations_passed = all([
                validation_results['tables_created'],
                validation_results['indexes_created'],
                validation_results['views_created'],
                validation_results['migration_progress_initialized']
            ])
            
            if all_validations_passed:
                setup_results['status'] = 'success'
                logger.info("🎉 Database infrastructure setup completed successfully!")
            else:
                setup_results['status'] = 'partial_success'
                logger.warning("⚠️ Database infrastructure setup completed with some issues")
            
            setup_results['setup_duration_seconds'] = time.time() - start_time
            
            return setup_results
            
        except Exception as e:
            logger.error(f"❌ Database infrastructure setup failed: {e}")
            setup_results['setup_duration_seconds'] = time.time() - start_time
            setup_results['error_message'] = str(e)
            raise
        finally:
            if self.connection_pool:
                await self.connection_pool.close()
    
    def save_setup_results(self, results: Dict[str, Any], filename: str = None):
        """Save setup results to file."""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"database_setup_results_{timestamp}.json"
        
        try:
            import json
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            logger.info(f"💾 Setup results saved to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"❌ Failed to save setup results: {e}")
            raise

async def main():
    """Main execution."""
    print("🏗️ Core Nexus Database Infrastructure Setup")
    print("=" * 50)
    print("Phase 4.1: Production Database Infrastructure")
    print()
    
    try:
        setup_manager = DatabaseInfrastructureSetup()
        results = await setup_manager.run_complete_setup()
        
        # Save results
        filename = setup_manager.save_setup_results(results)
        
        # Print summary
        print("\n🏆 DATABASE INFRASTRUCTURE SETUP RESULTS")
        print("=" * 45)
        print(f"✅ Status: {results['status'].upper()}")
        print(f"✅ Duration: {results['setup_duration_seconds']:.1f} seconds")
        print(f"✅ Connection: {results['connection_successful']}")
        print(f"✅ Migration: {results['migration_successful']}")
        print(f"✅ Test Data: {results['test_data_created']}")
        print(f"✅ Monitoring: {results['monitoring_setup']}")
        
        validation = results['validation_results']
        print(f"\n📊 VALIDATION RESULTS")
        print("=" * 25)
        print(f"✅ Tables Created: {validation['tables_created']}")
        print(f"✅ Indexes Created: {validation['indexes_created']}")
        print(f"✅ Views Created: {validation['views_created']}")
        print(f"✅ Triggers Created: {validation['triggers_created']}")
        print(f"✅ Migration Progress: {validation['migration_progress_initialized']}")
        
        baseline = validation['performance_baseline']
        print(f"\n📈 PERFORMANCE BASELINE")
        print("=" * 25)
        print(f"📊 Vector Count: {baseline['vector_count']}")
        print(f"📊 Avg Dimensions: {baseline['avg_dimensions']:.0f}D")
        print(f"📊 Dimension Range: {baseline['min_dimensions']}-{baseline['max_dimensions']}D")
        
        print(f"\n💾 Complete results: {filename}")
        
        if results['status'] == 'success':
            print("\n🚀 STATUS: INFRASTRUCTURE READY!")
            print("✅ Database infrastructure successfully set up")
            print("🎯 Ready to proceed to Phase 4.2: Production Migration Tooling")
        else:
            print("\n⚠️ STATUS: PARTIAL SUCCESS")
            print("❌ Review validation results and address any issues")
        
    except Exception as e:
        logger.error(f"❌ Database infrastructure setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())