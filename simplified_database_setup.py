#!/usr/bin/env python3
"""
Simplified Database Setup for Vector Optimization

Creates the essential database infrastructure without complex parsing.
"""

import asyncio
import asyncpg
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimplifiedDatabaseSetup:
    """Simplified database setup for vector optimization."""
    
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
    
    async def create_optimized_table(self):
        """Create the optimized vector table."""
        logger.info("🏗️ Creating optimized vector table...")
        
        async with self.connection_pool.acquire() as conn:
            try:
                # Create the optimized table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS vector_memories_optimized (
                        id UUID PRIMARY KEY,
                        content TEXT NOT NULL,
                        embedding VECTOR(1536),
                        metadata JSONB DEFAULT '{}',
                        
                        -- Migration tracking fields
                        migration_status TEXT DEFAULT 'pending' CHECK (migration_status IN ('pending', 'migrating', 'migrated', 'verified', 'failed')),
                        migration_timestamp TIMESTAMP,
                        migration_batch_id UUID,
                        
                        -- Quality metrics
                        original_dimensions INTEGER,
                        accuracy_score DECIMAL(5,4),
                        
                        -- Standard fields
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW(),
                        
                        -- Constraints
                        CONSTRAINT content_not_empty CHECK (LENGTH(content) > 0),
                        CONSTRAINT valid_accuracy CHECK (accuracy_score IS NULL OR (accuracy_score >= 0 AND accuracy_score <= 1))
                    )
                """)
                
                logger.info("✅ Optimized vector table created")
                
            except Exception as e:
                logger.error(f"❌ Failed to create optimized table: {e}")
                raise
    
    async def create_tracking_tables(self):
        """Create migration tracking tables."""
        logger.info("📊 Creating migration tracking tables...")
        
        async with self.connection_pool.acquire() as conn:
            try:
                # Migration batches table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS migration_batches (
                        batch_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        batch_number INTEGER NOT NULL,
                        start_vector_id UUID,
                        end_vector_id UUID,
                        
                        -- Batch metrics
                        total_vectors INTEGER NOT NULL DEFAULT 0,
                        migrated_vectors INTEGER DEFAULT 0,
                        failed_vectors INTEGER DEFAULT 0,
                        
                        -- Quality metrics
                        avg_accuracy_score DECIMAL(5,4),
                        min_accuracy_score DECIMAL(5,4),
                        performance_improvement DECIMAL(5,2),
                        
                        -- Batch status
                        status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'rollback')),
                        error_message TEXT,
                        
                        -- Timing
                        started_at TIMESTAMP,
                        completed_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT NOW(),
                        
                        -- API usage tracking
                        openai_api_calls INTEGER DEFAULT 0,
                        api_cost_estimate DECIMAL(10,4),
                        
                        CONSTRAINT positive_vectors CHECK (total_vectors >= 0 AND migrated_vectors >= 0 AND failed_vectors >= 0),
                        CONSTRAINT valid_batch_number CHECK (batch_number > 0)
                    )
                """)
                
                # Migration progress table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS migration_progress (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        
                        -- Overall progress
                        total_vectors_to_migrate INTEGER NOT NULL,
                        total_vectors_migrated INTEGER DEFAULT 0,
                        total_batches INTEGER DEFAULT 0,
                        completed_batches INTEGER DEFAULT 0,
                        failed_batches INTEGER DEFAULT 0,
                        
                        -- Quality metrics
                        overall_accuracy_score DECIMAL(5,4),
                        overall_performance_improvement DECIMAL(5,2),
                        
                        -- Migration status
                        migration_status TEXT DEFAULT 'not_started' CHECK (migration_status IN ('not_started', 'in_progress', 'completed', 'paused', 'failed')),
                        
                        -- Timing
                        migration_started_at TIMESTAMP,
                        migration_completed_at TIMESTAMP,
                        estimated_completion_at TIMESTAMP,
                        
                        -- Resource usage
                        total_api_calls INTEGER DEFAULT 0,
                        total_estimated_cost DECIMAL(10,4),
                        
                        -- Metadata
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                
                logger.info("✅ Migration tracking tables created")
                
            except Exception as e:
                logger.error(f"❌ Failed to create tracking tables: {e}")
                raise
    
    async def create_monitoring_tables(self):
        """Create monitoring tables."""
        logger.info("📈 Creating monitoring tables...")
        
        async with self.connection_pool.acquire() as conn:
            try:
                # Query performance monitoring
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS query_performance_metrics (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        
                        -- Query details
                        query_type TEXT NOT NULL CHECK (query_type IN ('search', 'insert', 'update', 'delete')),
                        table_type TEXT NOT NULL CHECK (table_type IN ('original', 'optimized')),
                        
                        -- Performance metrics
                        latency_ms DECIMAL(10,3) NOT NULL,
                        result_count INTEGER,
                        vector_dimensions INTEGER,
                        
                        -- Query metadata
                        query_timestamp TIMESTAMP DEFAULT NOW(),
                        user_session_id TEXT,
                        query_params JSONB DEFAULT '{}',
                        
                        -- System metrics
                        cpu_usage_percent DECIMAL(5,2),
                        memory_usage_mb DECIMAL(10,2),
                        
                        CONSTRAINT positive_latency CHECK (latency_ms >= 0)
                    )
                """)
                
                logger.info("✅ Monitoring tables created")
                
            except Exception as e:
                logger.error(f"❌ Failed to create monitoring tables: {e}")
                raise
    
    async def create_indexes(self):
        """Create indexes for the optimized tables."""
        logger.info("🔧 Creating indexes...")
        
        async with self.connection_pool.acquire() as conn:
            try:
                # Primary HNSW index for vector similarity search
                logger.info("🔧 Creating HNSW index (this may take a few minutes)...")
                await conn.execute("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_vector_memories_optimized_embedding_hnsw
                    ON vector_memories_optimized 
                    USING hnsw (embedding vector_cosine_ops) 
                    WITH (m = 32, ef_construction = 128)
                """)
                
                # Migration status index
                await conn.execute("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_vector_memories_optimized_migration_status
                    ON vector_memories_optimized (migration_status, migration_timestamp)
                """)
                
                # Batch tracking index
                await conn.execute("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_vector_memories_optimized_batch
                    ON vector_memories_optimized (migration_batch_id)
                """)
                
                # Performance monitoring indexes
                await conn.execute("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_query_performance_metrics_timestamp
                    ON query_performance_metrics (query_timestamp DESC)
                """)
                
                logger.info("✅ All indexes created successfully")
                
            except Exception as e:
                logger.error(f"❌ Failed to create indexes: {e}")
                raise
    
    async def initialize_migration_progress(self):
        """Initialize migration progress tracking."""
        logger.info("📊 Initializing migration progress...")
        
        async with self.connection_pool.acquire() as conn:
            try:
                # Get current vector count
                vector_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM vector_memories WHERE embedding IS NOT NULL"
                )
                
                # Initialize migration progress
                await conn.execute("""
                    INSERT INTO migration_progress (
                        total_vectors_to_migrate,
                        migration_status
                    ) VALUES ($1, 'not_started')
                    ON CONFLICT DO NOTHING
                """, vector_count)
                
                logger.info(f"✅ Migration progress initialized: {vector_count} vectors to migrate")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize migration progress: {e}")
                raise
    
    async def create_test_data(self):
        """Create test data to validate the infrastructure."""
        logger.info("🧪 Creating test data...")
        
        async with self.connection_pool.acquire() as conn:
            try:
                # Insert a test vector (convert list to proper vector string format)
                test_embedding = [0.1] * 1536
                test_vector_str = '[' + ','.join(map(str, test_embedding)) + ']'
                
                await conn.execute("""
                    INSERT INTO vector_memories_optimized (
                        id, content, embedding, migration_status, original_dimensions
                    ) VALUES (
                        gen_random_uuid(), 
                        'Test vector for infrastructure validation', 
                        $1::vector, 
                        'verified', 
                        19226
                    )
                """, test_vector_str)
                
                # Test the HNSW index
                test_query_start = time.perf_counter()
                result = await conn.fetchrow("""
                    SELECT id, content, embedding <=> $1::vector as distance
                    FROM vector_memories_optimized
                    ORDER BY embedding <=> $1::vector
                    LIMIT 1
                """, test_vector_str)
                test_query_time = (time.perf_counter() - test_query_start) * 1000
                
                logger.info(f"✅ Test query successful: {test_query_time:.2f}ms latency")
                
                # Insert test performance metrics
                await conn.execute("""
                    INSERT INTO query_performance_metrics (
                        query_type, table_type, latency_ms, result_count, vector_dimensions
                    ) VALUES (
                        'search', 'optimized', $1, 1, 1536
                    )
                """, test_query_time)
                
                logger.info("✅ Test data created successfully")
                
            except Exception as e:
                logger.error(f"❌ Failed to create test data: {e}")
                raise
    
    async def validate_setup(self) -> Dict[str, Any]:
        """Validate the complete setup."""
        logger.info("🔍 Validating database setup...")
        
        validation_results = {
            'optimized_table_exists': False,
            'tracking_tables_exist': False,
            'monitoring_tables_exist': False,
            'indexes_created': False,
            'migration_progress_initialized': False,
            'test_data_created': False
        }
        
        async with self.connection_pool.acquire() as conn:
            try:
                # Check tables
                tables = await conn.fetch("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('vector_memories_optimized', 'migration_batches', 'migration_progress', 'query_performance_metrics')
                """)
                
                table_names = [row['table_name'] for row in tables]
                validation_results['optimized_table_exists'] = 'vector_memories_optimized' in table_names
                validation_results['tracking_tables_exist'] = all(t in table_names for t in ['migration_batches', 'migration_progress'])
                validation_results['monitoring_tables_exist'] = 'query_performance_metrics' in table_names
                
                # Check indexes
                indexes = await conn.fetch("""
                    SELECT indexname 
                    FROM pg_indexes 
                    WHERE tablename = 'vector_memories_optimized'
                """)
                
                index_names = [row['indexname'] for row in indexes]
                hnsw_exists = any('hnsw' in name for name in index_names)
                validation_results['indexes_created'] = hnsw_exists and len(index_names) >= 2
                
                # Check migration progress
                progress_count = await conn.fetchval("SELECT COUNT(*) FROM migration_progress")
                validation_results['migration_progress_initialized'] = progress_count > 0
                
                # Check test data
                test_count = await conn.fetchval("SELECT COUNT(*) FROM vector_memories_optimized")
                validation_results['test_data_created'] = test_count > 0
                
                # Get stats
                vector_count = await conn.fetchval("SELECT COUNT(*) FROM vector_memories WHERE embedding IS NOT NULL")
                
                validation_results['statistics'] = {
                    'original_vectors': vector_count,
                    'optimized_vectors': test_count,
                    'tables_created': len(table_names),
                    'indexes_created': len(index_names)
                }
                
                logger.info(f"✅ Validation complete: {vector_count} original vectors, {test_count} test vectors")
                
            except Exception as e:
                logger.error(f"❌ Validation failed: {e}")
                raise
        
        return validation_results
    
    async def run_complete_setup(self) -> Dict[str, Any]:
        """Run the complete simplified database setup."""
        start_time = time.time()
        logger.info("🚀 Starting simplified database setup...")
        
        try:
            # Connect to database
            await self.connect_to_database()
            
            # Create tables
            await self.create_optimized_table()
            await self.create_tracking_tables()
            await self.create_monitoring_tables()
            
            # Create indexes
            await self.create_indexes()
            
            # Initialize data
            await self.initialize_migration_progress()
            await self.create_test_data()
            
            # Validate setup
            validation_results = await self.validate_setup()
            
            results = {
                'setup_duration_seconds': time.time() - start_time,
                'setup_timestamp': datetime.now().isoformat(),
                'validation_results': validation_results,
                'status': 'success' if all(validation_results.values()) else 'partial_success'
            }
            
            logger.info(f"🎉 Database setup completed in {results['setup_duration_seconds']:.1f} seconds")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Database setup failed: {e}")
            raise
        finally:
            if self.connection_pool:
                await self.connection_pool.close()

async def main():
    """Main execution."""
    print("🏗️ Core Nexus Simplified Database Setup")
    print("=" * 45)
    print("Phase 4.1: Essential Database Infrastructure")
    print()
    
    try:
        setup_manager = SimplifiedDatabaseSetup()
        results = await setup_manager.run_complete_setup()
        
        # Print summary
        print("\n🏆 DATABASE SETUP RESULTS")
        print("=" * 30)
        print(f"✅ Status: {results['status'].upper()}")
        print(f"✅ Duration: {results['setup_duration_seconds']:.1f} seconds")
        
        validation = results['validation_results']
        print(f"\n📊 VALIDATION RESULTS")
        print("=" * 25)
        print(f"✅ Optimized Table: {validation['optimized_table_exists']}")
        print(f"✅ Tracking Tables: {validation['tracking_tables_exist']}")
        print(f"✅ Monitoring Tables: {validation['monitoring_tables_exist']}")
        print(f"✅ Indexes Created: {validation['indexes_created']}")
        print(f"✅ Migration Progress: {validation['migration_progress_initialized']}")
        print(f"✅ Test Data: {validation['test_data_created']}")
        
        stats = validation['statistics']
        print(f"\n📈 STATISTICS")
        print("=" * 15)
        print(f"📊 Original Vectors: {stats['original_vectors']}")
        print(f"📊 Test Vectors: {stats['optimized_vectors']}")
        print(f"📊 Tables Created: {stats['tables_created']}")
        print(f"📊 Indexes Created: {stats['indexes_created']}")
        
        if results['status'] == 'success':
            print("\n🚀 STATUS: DATABASE INFRASTRUCTURE READY!")
            print("✅ All components successfully set up")
            print("🎯 Ready to proceed to Phase 4.2: Production Migration Tooling")
        else:
            print("\n⚠️ STATUS: PARTIAL SUCCESS")
            print("❌ Some components may need attention")
        
    except Exception as e:
        logger.error(f"❌ Database setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())