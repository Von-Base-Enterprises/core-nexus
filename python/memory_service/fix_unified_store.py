# Replace the query_memories method in unified_store.py with this


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
