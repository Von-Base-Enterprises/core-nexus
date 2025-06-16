-- Migration 001: Create schema migrations table
-- This table tracks which migrations have been applied

CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Record this migration
INSERT INTO schema_migrations (version) 
VALUES ('001_create_schema_migrations')
ON CONFLICT (version) DO NOTHING;