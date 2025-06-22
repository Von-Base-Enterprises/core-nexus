-- Migration 007: Create Optimized Vector Tables for 10x Performance Optimization
-- Core Nexus Vector Optimization Infrastructure
-- Date: 2025-06-22

-- =====================================================
-- OPTIMIZED VECTOR STORAGE TABLE
-- =====================================================

-- Create the optimized vector table with 1,536D embeddings
CREATE TABLE IF NOT EXISTS vector_memories_optimized (
    id UUID PRIMARY KEY,
    content TEXT NOT NULL,
    embedding VECTOR(1536),  -- OpenAI text-embedding-3-small dimensions
    metadata JSONB DEFAULT '{}',
    
    -- Migration tracking fields
    migration_status TEXT DEFAULT 'pending' CHECK (migration_status IN ('pending', 'migrating', 'migrated', 'verified', 'failed')),
    migration_timestamp TIMESTAMP,
    migration_batch_id UUID,
    
    -- Quality metrics
    original_dimensions INTEGER,
    accuracy_score DECIMAL(5,4),  -- Search accuracy preservation score
    
    -- Standard fields
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT content_not_empty CHECK (LENGTH(content) > 0),
    CONSTRAINT valid_accuracy CHECK (accuracy_score IS NULL OR (accuracy_score >= 0 AND accuracy_score <= 1))
);

-- Add comments for documentation
COMMENT ON TABLE vector_memories_optimized IS 'Optimized vector storage with 1,536D OpenAI embeddings for 12.5x performance improvement';
COMMENT ON COLUMN vector_memories_optimized.embedding IS 'OpenAI text-embedding-3-small 1,536-dimensional vector';
COMMENT ON COLUMN vector_memories_optimized.migration_status IS 'Tracks migration progress: pending -> migrating -> migrated -> verified';
COMMENT ON COLUMN vector_memories_optimized.accuracy_score IS 'Search accuracy preservation score (0.0-1.0)';

-- =====================================================
-- MIGRATION TRACKING INFRASTRUCTURE
-- =====================================================

-- Migration batch tracking
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
    performance_improvement DECIMAL(5,2), -- Percentage improvement
    
    -- Batch status
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'rollback')),
    error_message TEXT,
    
    -- Timing
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- API usage tracking
    openai_api_calls INTEGER DEFAULT 0,
    api_cost_estimate DECIMAL(10,4), -- Estimated cost in USD
    
    CONSTRAINT positive_vectors CHECK (total_vectors >= 0 AND migrated_vectors >= 0 AND failed_vectors >= 0),
    CONSTRAINT valid_batch_number CHECK (batch_number > 0)
);

COMMENT ON TABLE migration_batches IS 'Tracks migration batches with metrics and status';

-- Migration progress summary
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
);

COMMENT ON TABLE migration_progress IS 'Overall migration progress tracking and metrics';

-- =====================================================
-- PERFORMANCE MONITORING TABLES
-- =====================================================

-- Query performance tracking
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
);

COMMENT ON TABLE query_performance_metrics IS 'Real-time query performance monitoring for original vs optimized vectors';

-- A/B testing results
CREATE TABLE IF NOT EXISTS ab_test_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Test details
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    test_variant TEXT NOT NULL CHECK (test_variant IN ('original', 'optimized')),
    
    -- Query details
    query_content TEXT,
    query_timestamp TIMESTAMP DEFAULT NOW(),
    
    -- Results
    latency_ms DECIMAL(10,3) NOT NULL,
    result_count INTEGER,
    user_satisfaction_score INTEGER CHECK (user_satisfaction_score BETWEEN 1 AND 5),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE ab_test_results IS 'A/B testing results comparing original vs optimized vector performance';

-- =====================================================
-- OPTIMIZED INDEXES
-- =====================================================

-- Primary HNSW index for vector similarity search
-- Using optimized parameters: m=32, ef_construction=128
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_vector_memories_optimized_embedding_hnsw
ON vector_memories_optimized 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 32, ef_construction = 128);

-- Migration status index for batch processing
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_vector_memories_optimized_migration_status
ON vector_memories_optimized (migration_status, migration_timestamp);

-- Batch tracking index
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_vector_memories_optimized_batch
ON vector_memories_optimized (migration_batch_id);

-- Content search index
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_vector_memories_optimized_content_gin
ON vector_memories_optimized 
USING gin (to_tsvector('english', content));

-- Performance monitoring indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_query_performance_metrics_timestamp
ON query_performance_metrics (query_timestamp DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_query_performance_metrics_type
ON query_performance_metrics (table_type, query_type, query_timestamp DESC);

-- Batch tracking indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_migration_batches_status
ON migration_batches (status, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_migration_batches_batch_number
ON migration_batches (batch_number);

-- =====================================================
-- FUNCTIONS AND TRIGGERS
-- =====================================================

-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to optimized table
DROP TRIGGER IF EXISTS update_vector_memories_optimized_updated_at ON vector_memories_optimized;
CREATE TRIGGER update_vector_memories_optimized_updated_at
    BEFORE UPDATE ON vector_memories_optimized
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply updated_at trigger to migration progress
DROP TRIGGER IF EXISTS update_migration_progress_updated_at ON migration_progress;
CREATE TRIGGER update_migration_progress_updated_at
    BEFORE UPDATE ON migration_progress
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Migration status validation function
CREATE OR REPLACE FUNCTION validate_migration_status_transition()
RETURNS TRIGGER AS $$
BEGIN
    -- Ensure valid status transitions
    IF OLD.migration_status = 'verified' AND NEW.migration_status != 'verified' THEN
        RAISE EXCEPTION 'Cannot change status from verified to %', NEW.migration_status;
    END IF;
    
    -- Set migration timestamp when status changes to migrated
    IF NEW.migration_status = 'migrated' AND OLD.migration_status != 'migrated' THEN
        NEW.migration_timestamp = NOW();
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply migration status validation trigger
DROP TRIGGER IF EXISTS validate_migration_status ON vector_memories_optimized;
CREATE TRIGGER validate_migration_status
    BEFORE UPDATE ON vector_memories_optimized
    FOR EACH ROW
    EXECUTE FUNCTION validate_migration_status_transition();

-- =====================================================
-- VIEWS FOR MONITORING
-- =====================================================

-- Migration progress overview
CREATE OR REPLACE VIEW migration_overview AS
SELECT 
    mp.migration_status,
    mp.total_vectors_to_migrate,
    mp.total_vectors_migrated,
    ROUND((mp.total_vectors_migrated::DECIMAL / mp.total_vectors_to_migrate * 100), 2) as progress_percentage,
    mp.completed_batches,
    mp.failed_batches,
    mp.overall_accuracy_score,
    mp.overall_performance_improvement,
    mp.total_api_calls,
    mp.total_estimated_cost,
    mp.migration_started_at,
    mp.estimated_completion_at,
    EXTRACT(EPOCH FROM (NOW() - mp.migration_started_at))/3600 as hours_elapsed
FROM migration_progress mp
ORDER BY mp.created_at DESC
LIMIT 1;

COMMENT ON VIEW migration_overview IS 'Current migration progress overview with key metrics';

-- Performance comparison view
CREATE OR REPLACE VIEW performance_comparison AS
WITH original_metrics AS (
    SELECT 
        AVG(latency_ms) as avg_latency,
        COUNT(*) as query_count,
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) as p95_latency
    FROM query_performance_metrics 
    WHERE table_type = 'original' 
    AND query_timestamp > NOW() - INTERVAL '24 hours'
),
optimized_metrics AS (
    SELECT 
        AVG(latency_ms) as avg_latency,
        COUNT(*) as query_count,
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) as p95_latency
    FROM query_performance_metrics 
    WHERE table_type = 'optimized' 
    AND query_timestamp > NOW() - INTERVAL '24 hours'
)
SELECT 
    o.avg_latency as original_avg_latency,
    opt.avg_latency as optimized_avg_latency,
    ROUND(((o.avg_latency - opt.avg_latency) / o.avg_latency * 100), 2) as avg_improvement_percent,
    o.p95_latency as original_p95_latency,
    opt.p95_latency as optimized_p95_latency,
    ROUND(((o.p95_latency - opt.p95_latency) / o.p95_latency * 100), 2) as p95_improvement_percent,
    o.query_count as original_queries,
    opt.query_count as optimized_queries
FROM original_metrics o, optimized_metrics opt;

COMMENT ON VIEW performance_comparison IS '24-hour performance comparison between original and optimized vectors';

-- Recent batch status
CREATE OR REPLACE VIEW recent_batch_status AS
SELECT 
    batch_number,
    status,
    total_vectors,
    migrated_vectors,
    failed_vectors,
    ROUND((migrated_vectors::DECIMAL / total_vectors * 100), 2) as completion_percentage,
    avg_accuracy_score,
    performance_improvement,
    openai_api_calls,
    api_cost_estimate,
    started_at,
    completed_at,
    CASE 
        WHEN completed_at IS NOT NULL THEN 
            EXTRACT(EPOCH FROM (completed_at - started_at))/60
        ELSE 
            EXTRACT(EPOCH FROM (NOW() - started_at))/60 
    END as duration_minutes
FROM migration_batches 
ORDER BY batch_number DESC 
LIMIT 20;

COMMENT ON VIEW recent_batch_status IS 'Status of recent migration batches with timing and metrics';

-- =====================================================
-- GRANTS AND PERMISSIONS
-- =====================================================

-- Grant permissions to the application user
GRANT SELECT, INSERT, UPDATE, DELETE ON vector_memories_optimized TO nexus_memory_db_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON migration_batches TO nexus_memory_db_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON migration_progress TO nexus_memory_db_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON query_performance_metrics TO nexus_memory_db_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ab_test_results TO nexus_memory_db_user;

-- Grant view access
GRANT SELECT ON migration_overview TO nexus_memory_db_user;
GRANT SELECT ON performance_comparison TO nexus_memory_db_user;
GRANT SELECT ON recent_batch_status TO nexus_memory_db_user;

-- =====================================================
-- INITIAL DATA SETUP
-- =====================================================

-- Initialize migration progress tracking
INSERT INTO migration_progress (
    total_vectors_to_migrate,
    migration_status
) 
SELECT 
    COUNT(*) as total_vectors,
    'not_started' as status
FROM vector_memories 
WHERE embedding IS NOT NULL
ON CONFLICT DO NOTHING;

-- =====================================================
-- VALIDATION QUERIES
-- =====================================================

-- Verify table creation
DO $$
BEGIN
    -- Check if optimized table exists and has correct structure
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'vector_memories_optimized'
    ) THEN
        RAISE EXCEPTION 'vector_memories_optimized table was not created successfully';
    END IF;
    
    -- Check if HNSW index exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'vector_memories_optimized' 
        AND indexname = 'idx_vector_memories_optimized_embedding_hnsw'
    ) THEN
        RAISE WARNING 'HNSW index may still be building concurrently';
    END IF;
    
    RAISE NOTICE 'Migration 007: Database infrastructure setup completed successfully';
END
$$;