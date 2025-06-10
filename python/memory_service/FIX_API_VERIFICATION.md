# API Fix for Data Verification

## Add this to the memory creation endpoint in api.py:

```python
@app.post("/memories", response_model=MemoryResponse)
async def create_memory(
    request: MemoryRequest,
    store: UnifiedVectorStore = Depends(get_store)
):
    """Store a memory with verification"""
    try:
        # Store the memory
        memory_result = await store.add(
            content=request.content,
            metadata=request.metadata,
            importance_score=request.importance_score,
            user_id=request.user_id,
            conversation_id=request.conversation_id
        )
        
        # CRITICAL: Verify the memory was actually stored
        verification_start = time.time()
        max_retries = 3
        verified = False
        
        for attempt in range(max_retries):
            if attempt > 0:
                await asyncio.sleep(0.5)  # Brief wait between retries
            
            # Try to retrieve the memory
            search_results = await store.search(
                query="",  # Empty query to get all
                limit=100,
                min_similarity=0.0
            )
            
            # Check if our memory is in the results
            for result in search_results:
                if result.get("id") == memory_result["id"]:
                    verified = True
                    break
            
            if verified:
                break
        
        if not verified:
            # Memory creation failed - data not persisted
            logger.error(f"Memory {memory_result['id']} created but not retrievable")
            raise HTTPException(
                status_code=500,
                detail="Memory storage verification failed - data not persisted"
            )
        
        logger.info(f"Memory {memory_result['id']} created and verified in {(time.time() - verification_start)*1000:.0f}ms")
        
        return MemoryResponse(**memory_result)
        
    except Exception as e:
        logger.error(f"Memory creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```
