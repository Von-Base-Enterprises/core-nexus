# Add this method to PgVectorProvider class in providers.py


    async def get_recent_memories(self, limit: int = 10, offset: int = 0) -> List[MemoryResponse]:
        """
        Get recent memories without vector similarity search.
        Used for empty queries to browse all memories.
        """
        if not self.connection_pool:
            return []
            
        async with self.connection_pool.acquire() as conn:
            # Query recent memories ordered by creation time
            query = f"""
                SELECT 
                    id,
                    content,
                    metadata,
                    importance_score,
                    created_at,
                    updated_at
                FROM {self.table_name}
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
            """
            
            rows = await conn.fetch(query, limit, offset)
            
            # Also get total count
            count_query = f"SELECT COUNT(*) FROM {self.table_name}"
            total_count = await conn.fetchval(count_query)
            
            # Convert to MemoryResponse objects
            memories = []
            for row in rows:
                memory = MemoryResponse(
                    id=row['id'],
                    content=row['content'],
                    metadata=row['metadata'] if isinstance(row['metadata'], dict) else {},
                    embedding=[],  # Don't return full embeddings
                    importance_score=float(row['importance_score']),
                    similarity_score=None,  # No similarity for time-based query
                    created_at=row['created_at'].isoformat() if row['created_at'] else '',
                    updated_at=row['updated_at'].isoformat() if row['updated_at'] else None
                )
                memories.append(memory)
                
        # Store total count for later use
        self._last_total_count = total_count
        return memories
