"""Emergency database initialization endpoint"""

async def initialize_database_indexes(store):
    """Create missing pgvector indexes"""
    pgvector_provider = store.providers.get('pgvector')

    if not pgvector_provider or not pgvector_provider.enabled:
        return {"error": "pgvector provider not available"}

    try:
        async with pgvector_provider.connection_pool.acquire() as conn:
            # Create the critical vector index
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_vector_memories_embedding 
                ON vector_memories 
                USING ivfflat (embedding vector_cosine_ops) 
                WITH (lists = 100)
            """)

            # Create supporting indexes
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_vector_memories_metadata 
                ON vector_memories USING GIN (metadata)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_vector_memories_importance 
                ON vector_memories (importance_score DESC)
            """)

            # Update statistics
            await conn.execute("ANALYZE vector_memories")

            # Verify indexes were created
            indexes = await conn.fetch("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'vector_memories'
            """)

            return {
                "success": True,
                "indexes_created": [idx['indexname'] for idx in indexes],
                "message": "Database indexes created successfully!"
            }

    except Exception as e:
        return {"error": str(e)}

# Add this endpoint to api.py:
@app.post("/admin/init-database")
async def init_database(
    admin_key: str,
    store: UnifiedVectorStore = Depends(get_store)
):
    """Initialize database with required indexes"""
    # Simple security check
    if admin_key != "emergency-fix-2024":
        raise HTTPException(status_code=403, detail="Invalid admin key")

    result = await initialize_database_indexes(store)
    return result
