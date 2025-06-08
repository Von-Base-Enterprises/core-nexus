-- Core Nexus Memory Service Database Initialization
-- Sets up pgvector extension and optimized schema

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable other useful extensions for production
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Create optimized memory table with partitioning
CREATE TABLE IF NOT EXISTS vector_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    user_id TEXT,
    conversation_id TEXT,
    importance_score FLOAT DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT NOW(),
    last_accessed TIMESTAMP DEFAULT NOW(),
    access_count INTEGER DEFAULT 0
) PARTITION BY RANGE (created_at);

-- Create monthly partitions for the next year (automated scaling)
CREATE TABLE vector_memories_2024_01 PARTITION OF vector_memories
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE TABLE vector_memories_2024_02 PARTITION OF vector_memories
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
CREATE TABLE vector_memories_2024_03 PARTITION OF vector_memories
    FOR VALUES FROM ('2024-03-01') TO ('2024-04-01');
CREATE TABLE vector_memories_2024_04 PARTITION OF vector_memories
    FOR VALUES FROM ('2024-04-01') TO ('2024-05-01');
CREATE TABLE vector_memories_2024_05 PARTITION OF vector_memories
    FOR VALUES FROM ('2024-05-01') TO ('2024-06-01');
CREATE TABLE vector_memories_2024_06 PARTITION OF vector_memories
    FOR VALUES FROM ('2024-06-01') TO ('2024-07-01');
CREATE TABLE vector_memories_2024_07 PARTITION OF vector_memories
    FOR VALUES FROM ('2024-07-01') TO ('2024-08-01');
CREATE TABLE vector_memories_2024_08 PARTITION OF vector_memories
    FOR VALUES FROM ('2024-08-01') TO ('2024-09-01');
CREATE TABLE vector_memories_2024_09 PARTITION OF vector_memories
    FOR VALUES FROM ('2024-09-01') TO ('2024-10-01');
CREATE TABLE vector_memories_2024_10 PARTITION OF vector_memories
    FOR VALUES FROM ('2024-10-01') TO ('2024-11-01');
CREATE TABLE vector_memories_2024_11 PARTITION OF vector_memories
    FOR VALUES FROM ('2024-11-01') TO ('2024-12-01');
CREATE TABLE vector_memories_2024_12 PARTITION OF vector_memories
    FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');

-- Create 2025 partitions
CREATE TABLE vector_memories_2025_01 PARTITION OF vector_memories
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE vector_memories_2025_02 PARTITION OF vector_memories
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
CREATE TABLE vector_memories_2025_03 PARTITION OF vector_memories
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');
CREATE TABLE vector_memories_2025_04 PARTITION OF vector_memories
    FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');
CREATE TABLE vector_memories_2025_05 PARTITION OF vector_memories
    FOR VALUES FROM ('2025-05-01') TO ('2025-06-01');
CREATE TABLE vector_memories_2025_06 PARTITION OF vector_memories
    FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');

-- Create indexes on main table (will be inherited by partitions)
CREATE INDEX IF NOT EXISTS vector_memories_embedding_hnsw_idx 
    ON vector_memories USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS vector_memories_user_id_idx 
    ON vector_memories (user_id);
CREATE INDEX IF NOT EXISTS vector_memories_conversation_id_idx 
    ON vector_memories (conversation_id);
CREATE INDEX IF NOT EXISTS vector_memories_importance_idx 
    ON vector_memories (importance_score);
CREATE INDEX IF NOT EXISTS vector_memories_created_at_idx 
    ON vector_memories (created_at);
CREATE INDEX IF NOT EXISTS vector_memories_last_accessed_idx 
    ON vector_memories (last_accessed);

-- Compound indexes for common query patterns
CREATE INDEX IF NOT EXISTS vector_memories_user_time_idx 
    ON vector_memories (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS vector_memories_conversation_time_idx 
    ON vector_memories (conversation_id, created_at DESC);

-- JSONB index for metadata queries
CREATE INDEX IF NOT EXISTS vector_memories_metadata_gin_idx 
    ON vector_memories USING gin (metadata);

-- Create memory evolution tracking table
CREATE TABLE IF NOT EXISTS memory_evolution (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id UUID REFERENCES vector_memories(id) ON DELETE CASCADE,
    evolution_type TEXT NOT NULL, -- 'importance_update', 'access_pattern', 'relationship_change'
    old_value JSONB,
    new_value JSONB,
    reason TEXT,
    confidence_score FLOAT DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX memory_evolution_memory_id_idx ON memory_evolution (memory_id);
CREATE INDEX memory_evolution_type_idx ON memory_evolution (evolution_type);
CREATE INDEX memory_evolution_created_at_idx ON memory_evolution (created_at);

-- Create ADM scoring configuration table
CREATE TABLE IF NOT EXISTS adm_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_name TEXT UNIQUE NOT NULL,
    weights JSONB NOT NULL, -- DQ, DR, DI weights
    thresholds JSONB NOT NULL, -- Various thresholds for scoring
    active BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Insert default ADM configuration
INSERT INTO adm_config (config_name, weights, thresholds, active) VALUES (
    'default_adm',
    '{"data_quality": 0.3, "data_relevance": 0.4, "data_intelligence": 0.3}',
    '{"min_quality": 0.5, "min_relevance": 0.6, "min_intelligence": 0.4, "evolution_threshold": 0.1}',
    true
) ON CONFLICT (config_name) DO NOTHING;

-- Create system metrics table for monitoring
CREATE TABLE IF NOT EXISTS system_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name TEXT NOT NULL,
    metric_value FLOAT NOT NULL,
    metadata JSONB DEFAULT '{}',
    recorded_at TIMESTAMP DEFAULT NOW()
) PARTITION BY RANGE (recorded_at);

-- Create system metrics partitions (daily for detailed monitoring)
CREATE TABLE system_metrics_2024_12 PARTITION OF system_metrics
    FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');
CREATE TABLE system_metrics_2025_01 PARTITION OF system_metrics
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE system_metrics_2025_02 PARTITION OF system_metrics
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
CREATE TABLE system_metrics_2025_03 PARTITION OF system_metrics
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');
CREATE TABLE system_metrics_2025_04 PARTITION OF system_metrics
    FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');
CREATE TABLE system_metrics_2025_05 PARTITION OF system_metrics
    FOR VALUES FROM ('2025-05-01') TO ('2025-06-01');

CREATE INDEX system_metrics_name_idx ON system_metrics (metric_name);
CREATE INDEX system_metrics_recorded_at_idx ON system_metrics (recorded_at);

-- Create function for automatic partition creation
CREATE OR REPLACE FUNCTION create_monthly_partition(table_name TEXT, start_date DATE)
RETURNS VOID AS $$
DECLARE
    partition_name TEXT;
    end_date DATE;
BEGIN
    end_date := start_date + INTERVAL '1 month';
    partition_name := table_name || '_' || to_char(start_date, 'YYYY_MM');
    
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
                   partition_name, table_name, start_date, end_date);
END;
$$ LANGUAGE plpgsql;

-- Create function to automatically create partitions
CREATE OR REPLACE FUNCTION maintain_partitions()
RETURNS VOID AS $$
DECLARE
    next_month DATE;
BEGIN
    -- Create partitions for next 3 months
    FOR i IN 1..3 LOOP
        next_month := date_trunc('month', CURRENT_DATE) + (i || ' month')::INTERVAL;
        PERFORM create_monthly_partition('vector_memories', next_month);
        PERFORM create_monthly_partition('system_metrics', next_month);
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Set up automated partition maintenance (requires pg_cron extension in production)
-- SELECT cron.schedule('maintain-partitions', '0 0 1 * *', 'SELECT maintain_partitions();');

-- Create performance monitoring views
CREATE OR REPLACE VIEW memory_performance_summary AS
SELECT 
    DATE(created_at) as date,
    COUNT(*) as memories_created,
    AVG(importance_score) as avg_importance,
    COUNT(DISTINCT user_id) as active_users,
    COUNT(DISTINCT conversation_id) as active_conversations
FROM vector_memories 
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;

CREATE OR REPLACE VIEW top_accessed_memories AS
SELECT 
    id,
    content,
    access_count,
    importance_score,
    last_accessed,
    user_id
FROM vector_memories 
WHERE access_count > 0
ORDER BY access_count DESC, importance_score DESC
LIMIT 100;

-- Grant permissions for application user
-- (Uncomment and modify for production)
-- CREATE USER memory_service_app WITH PASSWORD 'secure_app_password';
-- GRANT USAGE ON SCHEMA public TO memory_service_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO memory_service_app;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO memory_service_app;

-- Display initialization success
SELECT 'Core Nexus Memory Service database initialized successfully!' as status;