-- Initialize pgvector extension and tables for Core Nexus Memory Service
-- Run this on your PostgreSQL database to set up vector storage

-- Create the vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create the main memories table with vector support
CREATE TABLE IF NOT EXISTS vector_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding vector(1536) NOT NULL,  -- 1536 dimensions for OpenAI embeddings
    metadata JSONB DEFAULT '{}',
    importance_score FLOAT DEFAULT 0.5,
    user_id VARCHAR(255),
    conversation_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    accessed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 0
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_vector_memories_embedding 
    ON vector_memories USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_vector_memories_user_id 
    ON vector_memories(user_id);

CREATE INDEX IF NOT EXISTS idx_vector_memories_conversation_id 
    ON vector_memories(conversation_id);

CREATE INDEX IF NOT EXISTS idx_vector_memories_created_at 
    ON vector_memories(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_vector_memories_importance 
    ON vector_memories(importance_score DESC);

CREATE INDEX IF NOT EXISTS idx_vector_memories_metadata 
    ON vector_memories USING gin(metadata);

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to auto-update updated_at
CREATE TRIGGER update_vector_memories_updated_at 
    BEFORE UPDATE ON vector_memories
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create a view for memory statistics
CREATE OR REPLACE VIEW memory_stats AS
SELECT 
    COUNT(*) as total_memories,
    AVG(importance_score) as avg_importance,
    MAX(created_at) as latest_memory,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(DISTINCT conversation_id) as unique_conversations
FROM vector_memories;

-- Grant permissions (adjust based on your user)
GRANT ALL ON vector_memories TO nexus_memory_db_user;
GRANT ALL ON memory_stats TO nexus_memory_db_user;

-- Success message
DO $$ 
BEGIN 
    RAISE NOTICE 'pgvector initialization complete! Tables and indexes created.';
END $$;