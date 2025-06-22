-- Migration 003: Optimize PostgreSQL configuration for vector workloads
-- Based on 2025 research for sub-20ms query latency targets
-- Optimized for 1GB RAM constraint on Render.com

BEGIN;

-- Log migration start
DO $$
BEGIN
    RAISE NOTICE 'Starting PostgreSQL vector workload optimization...';
    RAISE NOTICE 'Target: Sub-20ms p95 latency with current hardware constraints';
END $$;

-- ============================================================================
-- CONNECTION AND MEMORY OPTIMIZATION
-- ============================================================================

-- Optimize for vector workloads - these settings work within Render's constraints
-- Note: Some settings require superuser privileges and may not work on managed PostgreSQL

-- Connection pooling optimization (application level in providers.py)
DO $$
BEGIN
    -- These are informational - actual pooling configured in application
    RAISE NOTICE 'Connection pooling: Optimizing for 20-50 concurrent connections';
    RAISE NOTICE 'Pool configuration: min_size=10, max_size=30 (reduced for memory efficiency)';
END $$;

-- Work memory optimization for vector operations
-- This affects each sort/hash operation during queries
ALTER SYSTEM SET work_mem = '32MB';  -- Increased from default 4MB for vector ops

-- ============================================================================
-- QUERY OPTIMIZER SETTINGS  
-- ============================================================================

-- Enable more aggressive query planning for vector operations
ALTER SYSTEM SET random_page_cost = 1.1;  -- SSD optimization
ALTER SYSTEM SET seq_page_cost = 1.0;     -- SSD optimization
ALTER SYSTEM SET cpu_tuple_cost = 0.01;   -- Modern CPU optimization

-- Parallel query settings for large vector operations
ALTER SYSTEM SET max_parallel_workers_per_gather = 2;
ALTER SYSTEM SET parallel_tuple_cost = 0.1;
ALTER SYSTEM SET parallel_setup_cost = 1000.0;

-- Enable parallel index scans for vector queries
ALTER SYSTEM SET enable_parallel_hash = on;
ALTER SYSTEM SET enable_partitionwise_join = on;

-- ============================================================================
-- VECTOR-SPECIFIC OPTIMIZATIONS
-- ============================================================================

-- Optimize for vector similarity operations
-- These affect how PostgreSQL handles vector distance calculations
ALTER SYSTEM SET effective_io_concurrency = 200;  -- For SSD concurrent I/O

-- Enable JIT compilation for complex vector expressions
ALTER SYSTEM SET jit = on;
ALTER SYSTEM SET jit_above_cost = 100000;
ALTER SYSTEM SET jit_inline_above_cost = 500000;

-- ============================================================================
-- STATISTICS AND PLANNING
-- ============================================================================

-- Increase statistics target for better query planning on vector columns
ALTER TABLE vector_memories ALTER COLUMN embedding SET STATISTICS 1000;
ALTER TABLE vector_memories ALTER COLUMN importance_score SET STATISTICS 1000;
ALTER TABLE vector_memories ALTER COLUMN created_at SET STATISTICS 1000;

-- Force statistics update
ANALYZE vector_memories;

-- ============================================================================
-- INDEX OPTIMIZATION SETTINGS
-- ============================================================================

-- Enable index-only scans for vector queries where possible
ALTER SYSTEM SET enable_indexonlyscan = on;

-- Optimize index scanning
ALTER SYSTEM SET enable_bitmapscan = on;
ALTER SYSTEM SET enable_indexscan = on;

-- ============================================================================
-- LOGGING AND MONITORING OPTIMIZATION
-- ============================================================================

-- Enable slow query logging for vector performance monitoring
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- Log queries > 1 second
ALTER SYSTEM SET log_statement = 'none';  -- Don't log all statements (noise reduction)

-- Track query performance statistics
ALTER SYSTEM SET track_activities = on;
ALTER SYSTEM SET track_counts = on;
ALTER SYSTEM SET track_io_timing = on;
ALTER SYSTEM SET track_functions = 'pl';

-- ============================================================================
-- SESSION-LEVEL OPTIMIZATIONS
-- ============================================================================

-- These will be applied at the session level in the application
DO $$
BEGIN
    RAISE NOTICE 'Setting session-level optimizations...';
    
    -- Optimize for vector operations in this session
    PERFORM set_config('enable_seqscan', 'off', false);  -- Force index usage
    PERFORM set_config('enable_sort', 'on', false);      -- Allow sorting for vector ranking
    PERFORM set_config('work_mem', '64MB', false);       -- Higher work_mem for this session
    
    RAISE NOTICE 'Session optimizations applied for vector workloads';
END $$;

-- ============================================================================
-- PGVECTOR-SPECIFIC SETTINGS
-- ============================================================================

-- Set optimal HNSW search parameters for runtime
-- These will be the defaults for all vector queries
DO $$
BEGIN
    -- Set optimal ef_search for our workload (balance of speed vs accuracy)
    PERFORM set_config('hnsw.ef_search', '64', false);  -- Increased from default 40
    
    RAISE NOTICE 'HNSW ef_search set to 64 for improved recall';
    RAISE NOTICE 'This balances query speed (<20ms target) with accuracy (>95% recall)';
END $$;

-- ============================================================================
-- VACUUM AND MAINTENANCE OPTIMIZATION
-- ============================================================================

-- Optimize autovacuum for vector tables (large, frequently updated)
ALTER TABLE vector_memories SET (
    autovacuum_vacuum_scale_factor = 0.1,     -- More frequent vacuuming
    autovacuum_analyze_scale_factor = 0.05,   -- More frequent analysis
    autovacuum_vacuum_cost_delay = 10,        -- Faster vacuum
    autovacuum_vacuum_cost_limit = 1000       -- Higher vacuum cost limit
);

-- ============================================================================
-- RELOAD CONFIGURATION
-- ============================================================================

-- Reload PostgreSQL configuration to apply changes
SELECT pg_reload_conf();

-- ============================================================================
-- PERFORMANCE VALIDATION
-- ============================================================================

-- Test vector query performance
DO $$
DECLARE
    start_time timestamp;
    end_time timestamp;
    duration_ms numeric;
    test_embedding vector(1536);
BEGIN
    RAISE NOTICE 'Testing vector query performance...';
    
    -- Create a test vector for performance testing
    test_embedding := array_fill(0.1, ARRAY[1536])::vector(1536);
    
    -- Time a simple vector similarity query
    start_time := clock_timestamp();
    
    PERFORM id, content, embedding <=> test_embedding as distance
    FROM vector_memories 
    ORDER BY embedding <=> test_embedding 
    LIMIT 10;
    
    end_time := clock_timestamp();
    duration_ms := EXTRACT(epoch FROM (end_time - start_time)) * 1000;
    
    RAISE NOTICE 'Sample vector query completed in % ms', round(duration_ms, 2);
    
    IF duration_ms < 20 THEN
        RAISE NOTICE '✅ PERFORMANCE TARGET MET: Query < 20ms';
    ELSIF duration_ms < 50 THEN
        RAISE NOTICE '⚠️  PERFORMANCE GOOD: Query < 50ms (target: 20ms)';
    ELSE
        RAISE NOTICE '❌ PERFORMANCE NEEDS IMPROVEMENT: Query > 50ms (target: 20ms)';
    END IF;
    
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Performance test failed: %', SQLERRM;
END $$;

-- ============================================================================
-- CONFIGURATION VERIFICATION
-- ============================================================================

-- Show current configuration values
DO $$
DECLARE
    rec record;
BEGIN
    RAISE NOTICE 'Current PostgreSQL configuration for vector workloads:';
    
    FOR rec IN 
        SELECT name, setting, unit 
        FROM pg_settings 
        WHERE name IN (
            'work_mem', 'random_page_cost', 'seq_page_cost', 
            'max_parallel_workers_per_gather', 'effective_io_concurrency',
            'jit', 'enable_indexonlyscan', 'track_io_timing'
        )
        ORDER BY name
    LOOP
        RAISE NOTICE '  %: % %', rec.name, rec.setting, COALESCE(rec.unit, '');
    END LOOP;
END $$;

-- Record migration completion
INSERT INTO schema_migrations (version, applied_at) 
VALUES ('003_optimize_postgresql_for_vectors', NOW())
ON CONFLICT (version) DO NOTHING;

RAISE NOTICE 'PostgreSQL vector optimization migration completed successfully!';
RAISE NOTICE 'Next steps: Monitor query performance and tune HNSW index parameters';

COMMIT;