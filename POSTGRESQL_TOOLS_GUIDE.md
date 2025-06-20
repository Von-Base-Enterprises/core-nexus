# PostgreSQL Tools and Database Connection Guide

## Summary

Your Render PostgreSQL database is **fully operational** and accessible. Since traditional PostgreSQL command-line tools (`psql`, `pg_dump`, etc.) are not installed locally, I've created Python-based alternatives that provide the same functionality.

## Database Configuration

**Connection Details:**
- **Host**: `dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com`
- **Port**: `5432`
- **Database**: `nexus_memory_db`
- **User**: `nexus_memory_db_user`
- **Password**: Available via `PGVECTOR_PASSWORD` environment variable

**Current Status:**
- ✅ Database connection: **Working**
- ✅ pgvector extension: **Installed (v0.7.2)**
- ✅ Vector data: **1,152 memories with 100% embeddings**
- ✅ Knowledge graph: **141 nodes, 27 relationships**
- ⚠️ uuid-ossp extension: Missing (not critical)

## Available Tools

### 1. Python-Based Database Tools

Since `psql` is not available, use these Python scripts:

#### **Basic Connection Test**
```bash
cd python/memory_service
poetry run python test_pgvector_connection.py
```

#### **Database Explorer** (psql replacement)
```bash
# Full database exploration
poetry run python ../../postgresql_explorer.py
```

#### **Comprehensive Toolkit** (multi-purpose tool)
```bash
# Health check
poetry run python ../../pg_toolkit.py health

# Interactive query mode (like psql)
poetry run python ../../pg_toolkit.py query

# Vector search testing
poetry run python ../../pg_toolkit.py test

# Full exploration
poetry run python ../../pg_toolkit.py explore

# Backup table structures
poetry run python ../../pg_toolkit.py backup

# Export data
poetry run python ../../pg_toolkit.py export
```

### 2. Connection Methods

#### **Method 1: Direct Connection String**
```python
import asyncpg

conn_str = "postgresql://nexus_memory_db_user:PASSWORD@dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com:5432/nexus_memory_db"
conn = await asyncpg.connect(conn_str)
```

#### **Method 2: Parameter-based Connection**
```python
import asyncpg

conn = await asyncpg.connect(
    host="dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com",
    port=5432,
    database="nexus_memory_db",
    user="nexus_memory_db_user",
    password="PASSWORD_FROM_ENV"
)
```

#### **Method 3: Using Environment Variables**
```bash
export PGHOST=dpg-d12n0np5pdvs73ctmm40-a.oregon-postgres.render.com
export PGPORT=5432
export PGDATABASE=nexus_memory_db
export PGUSER=nexus_memory_db_user
export PGPASSWORD=your_password_here
```

### 3. Database Schema Overview

**Main Tables:**
- `vector_memories`: Primary storage (1,152 rows, 30 MB)
- `graph_nodes`: Knowledge graph entities (141 rows)
- `graph_relationships`: Entity relationships (27 rows)
- `memory_entity_map`: Memory-entity mappings (151 rows)

**Key Indexes:**
- HNSW vector index for similarity search
- GIN index on metadata (JSONB)
- B-tree indexes on importance, created_at, etc.

## Common Operations

### Database Queries
```sql
-- Count total memories
SELECT COUNT(*) FROM vector_memories;

-- Find recent memories
SELECT content, importance_score, created_at 
FROM vector_memories 
ORDER BY created_at DESC 
LIMIT 10;

-- Vector similarity search
SELECT content, 1 - (embedding <=> $1) as similarity
FROM vector_memories 
ORDER BY embedding <=> $1 
LIMIT 5;

-- Knowledge graph exploration
SELECT entity_name, entity_type, mention_count 
FROM graph_nodes 
ORDER BY mention_count DESC;
```

### Performance Monitoring
```sql
-- Table sizes
SELECT pg_size_pretty(pg_total_relation_size('vector_memories'));

-- Index usage
SELECT indexrelname, idx_scan, idx_tup_read 
FROM pg_stat_user_indexes 
WHERE relname = 'vector_memories';
```

### Data Export
```sql
-- Export memories as JSON
SELECT row_to_json(t) 
FROM (
    SELECT id, content, metadata, importance_score, created_at
    FROM vector_memories 
    ORDER BY created_at DESC
) t;
```

## Troubleshooting

### Connection Issues
1. **Verify credentials**: Check `PGVECTOR_PASSWORD` environment variable
2. **Network connectivity**: Ensure no firewall blocking port 5432
3. **SSL requirements**: Try adding `?sslmode=require` to connection string

### Performance Issues
1. **Check index usage**: Use `pg_stat_user_indexes` queries
2. **Monitor query performance**: Enable logging with `log_statement = 'all'`
3. **Vector search optimization**: Ensure HNSW index is being used

### Vector Operations
```sql
-- Check vector dimensions
SELECT embedding FROM vector_memories WHERE embedding IS NOT NULL LIMIT 1;

-- Test vector operations
SELECT embedding <=> '[0,0,0,...]'::vector FROM vector_memories LIMIT 1;
```

## Recommended Workflows

### 1. Daily Health Check
```bash
poetry run python ../../pg_toolkit.py health
```

### 2. Data Exploration
```bash
poetry run python ../../pg_toolkit.py query
```
Then use SQL commands interactively.

### 3. Performance Analysis
```bash
poetry run python ../../pg_toolkit.py explore
```

### 4. Backup Operations
```bash
poetry run python ../../pg_toolkit.py backup > database_schema.sql
```

## Security Notes

- Database credentials are stored in environment variables
- Connection uses SSL by default
- User has appropriate permissions for application operations
- No admin privileges required for normal operations

## Next Steps

1. **Install PostgreSQL client tools** (if you get sudo access):
   ```bash
   sudo apt update && sudo apt install postgresql-client
   ```

2. **Set up automated monitoring**: Use the health check script in cron
3. **Create data backup strategy**: Regular exports using the toolkit
4. **Monitor performance**: Track query performance and index usage

The database is fully functional and ready for production use!