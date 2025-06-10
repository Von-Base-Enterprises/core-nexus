#!/usr/bin/env python3
"""
COMPREHENSIVE FIX FOR EMPTY QUERY BUG

This file contains the exact code changes needed to fix the empty query bug.
Copy these changes into the appropriate files and deploy.
"""

print("""
===============================================================================
EMPTY QUERY BUG FIX - IMPLEMENTATION PLAN
===============================================================================

PROBLEM: Empty queries return 0 results because zero vector + cosine similarity = NaN

SOLUTION: Add a dedicated method for non-vector queries and use it for empty queries

FILES TO MODIFY:
1. providers.py - Add get_recent_memories method to PgVectorProvider
2. unified_store.py - Update query_memories to use new method for empty queries

===============================================================================
""")

# STEP 1: Add this method to PgVectorProvider class in providers.py (around line 420)
PROVIDERS_PY_ADDITION = '''
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
'''

# STEP 2: Replace the query_memories method in unified_store.py (starting around line 223)
UNIFIED_STORE_PY_REPLACEMENT = '''
    async def query_memories(self, request: QueryRequest) -> QueryResponse:
        """
        Query memories across providers with intelligent routing.
        
        FIXED: Empty queries now return recent memories instead of using zero vector.
        """
        start_time = time.time()
        
        try:
            # Check cache first
            cache_key = self._get_cache_key(request)
            if cache_key in self.query_cache:
                cached_result = self.query_cache[cache_key]
                if time.time() - cached_result['timestamp'] < 300:  # 5 min cache
                    logger.debug(f"Cache hit for query: {request.query[:50]}...")
                    return cached_result['response']
            
            # FIXED: Handle empty queries differently
            if not request.query or request.query.strip() == "":
                logger.info("Empty query detected - returning recent memories")
                
                # Use pgvector provider's direct query method if available
                memories = []
                total_found = 0
                providers_used = []
                
                # Try pgvector first as it's the primary provider
                if 'pgvector' in self.providers and self.providers['pgvector'].enabled:
                    provider = self.providers['pgvector']
                    try:
                        # Use the new method that doesn't require vector similarity
                        if hasattr(provider, 'get_recent_memories'):
                            memories = await provider.get_recent_memories(
                                limit=request.limit or 10,
                                offset=0
                            )
                            # Get total count if stored
                            total_found = getattr(provider, '_last_total_count', len(memories))
                            providers_used = ['pgvector']
                            logger.info(f"Retrieved {len(memories)} recent memories from pgvector")
                        else:
                            # Fallback to connection pool query if method doesn't exist yet
                            if hasattr(provider, 'connection_pool') and provider.connection_pool:
                                async with provider.connection_pool.acquire() as conn:
                                    rows = await conn.fetch(f"""
                                        SELECT id, content, metadata, importance_score, created_at
                                        FROM {provider.table_name}
                                        ORDER BY created_at DESC
                                        LIMIT $1
                                    """, request.limit or 10)
                                    
                                    total_found = await conn.fetchval(f"SELECT COUNT(*) FROM {provider.table_name}")
                                    
                                    memories = []
                                    for row in rows:
                                        memory = MemoryResponse(
                                            id=row['id'],
                                            content=row['content'],
                                            metadata=row['metadata'] if isinstance(row['metadata'], dict) else {},
                                            embedding=[],
                                            importance_score=float(row['importance_score']),
                                            similarity_score=None,
                                            created_at=row['created_at'].isoformat() if row['created_at'] else ''
                                        )
                                        memories.append(memory)
                                    providers_used = ['pgvector']
                    except Exception as e:
                        logger.error(f"Failed to get recent memories from pgvector: {e}")
                
                # If pgvector failed, try other providers
                if not memories:
                    for provider_name, provider in self.providers.items():
                        if provider.enabled and provider_name != 'pgvector':
                            try:
                                # For other providers, use a small non-zero vector as workaround
                                small_vector = [0.001] * self.embedding_model.dimension
                                memories = await provider.query(small_vector, request.limit or 10, {})
                                providers_used = [provider_name]
                                total_found = len(memories)  # Approximate
                                break
                            except Exception as e:
                                logger.error(f"Provider {provider_name} failed: {e}")
                
                query_time = (time.time() - start_time) * 1000
                
                response = QueryResponse(
                    memories=memories[:request.limit or 10],
                    total_found=total_found,
                    query_time_ms=query_time,
                    providers_used=providers_used
                )
                
                # Cache result
                self.query_cache[cache_key] = {
                    'response': response,
                    'timestamp': time.time()
                }
                
                # Update stats
                self.stats['total_queries'] += 1
                self.stats['avg_query_time'] = (
                    (self.stats['avg_query_time'] * (self.stats['total_queries'] - 1) + query_time) / 
                    self.stats['total_queries']
                )
                
                logger.info(f"Empty query returned {len(memories)} memories in {query_time:.1f}ms")
                return response
            
            # For non-empty queries, continue with normal vector similarity search
            query_embedding = await self._generate_embedding(request.query)
            
            # Determine which providers to query
            providers_to_query = self._select_providers(request)
            
            # Query providers
            if len(providers_to_query) == 1:
                memories = await self._query_provider(
                    providers_to_query[0], 
                    query_embedding, 
                    request
                )
                providers_used = [providers_to_query[0].name]
            else:
                memories, providers_used = await self._query_multiple_providers(
                    providers_to_query, 
                    query_embedding, 
                    request
                )
            
            # Filter and sort results
            filtered_memories = self._filter_and_rank_memories(memories, request)
            
            query_time = (time.time() - start_time) * 1000
            
            # Update stats
            self.stats['total_queries'] += 1
            self.stats['avg_query_time'] = (
                (self.stats['avg_query_time'] * (self.stats['total_queries'] - 1) + query_time) / 
                self.stats['total_queries']
            )
            
            response = QueryResponse(
                memories=filtered_memories[:request.limit],
                total_found=len(filtered_memories),
                query_time_ms=query_time,
                providers_used=providers_used
            )
            
            # Cache result
            self.query_cache[cache_key] = {
                'response': response,
                'timestamp': time.time()
            }
            
            logger.info(f"Query returned {len(filtered_memories)} memories in {query_time:.1f}ms")
            return response
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise
'''

print("""
===============================================================================
STEP-BY-STEP IMPLEMENTATION GUIDE
===============================================================================

1. FIRST, add the get_recent_memories method to PgVectorProvider in providers.py:
   - Find the PgVectorProvider class (around line 240)
   - Add the new method after the existing query method (around line 420)
   - This method queries without vector similarity

2. THEN, update the query_memories method in unified_store.py:
   - Find the query_memories method (around line 223)
   - Replace the entire method with the fixed version
   - The key change is the empty query handling section

3. TEST locally if possible:
   - Empty query should return recent memories
   - Non-empty queries should work as before

4. DEPLOY to production:
   - Commit the changes
   - Push to main branch
   - Render will auto-deploy

5. VERIFY the fix:
   curl -X POST https://core-nexus-memory-service.onrender.com/memories/query \\
     -H "Content-Type: application/json" \\
     -d '{"query": "", "limit": 5}'
   
   Should return:
   - "total_found": 1020
   - 5 recent memories in the array

===============================================================================
WHY THIS FIX IS THE BEST APPROACH
===============================================================================

1. SEMANTICALLY CORRECT: Empty query = "show recent memories" is intuitive
2. NO MATH ISSUES: Completely bypasses the cosine similarity problem
3. PERFORMANCE: Direct SQL query is faster than vector search
4. BACKWARDS COMPATIBLE: Non-empty queries still use vector search
5. EXTENSIBLE: Easy to add pagination, filtering, sorting later

===============================================================================
""")

# Save the code snippets to separate files for easy copying
with open('/mnt/c/Users/Tyvon/core-nexus/python/memory_service/fix_providers.py', 'w') as f:
    f.write("# Add this method to PgVectorProvider class in providers.py\n\n")
    f.write(PROVIDERS_PY_ADDITION)

with open('/mnt/c/Users/Tyvon/core-nexus/python/memory_service/fix_unified_store.py', 'w') as f:
    f.write("# Replace the query_memories method in unified_store.py with this\n\n")
    f.write(UNIFIED_STORE_PY_REPLACEMENT)

print("Code snippets saved to:")
print("- fix_providers.py")
print("- fix_unified_store.py")
print("\nCopy the code from these files into the actual source files.")
