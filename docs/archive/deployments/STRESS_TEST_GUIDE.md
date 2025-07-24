# Core Nexus Stress Testing Guide - Break It!

## 1. **Concurrent Write Bombardment**
```python
# Hit it with 100 simultaneous memory writes
import asyncio
import aiohttp
import uuid

async def store_memory(session, i):
    data = {
        "content": f"Concurrent test {i} - {uuid.uuid4()}",
        "metadata": {"test_id": i, "timestamp": str(datetime.now())}
    }
    async with session.post("https://core-nexus-memory-service.onrender.com/memories", json=data) as resp:
        return await resp.json()

async def bombard():
    async with aiohttp.ClientSession() as session:
        tasks = [store_memory(session, i) for i in range(100)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        failures = [r for r in results if isinstance(r, Exception)]
        print(f"Failures: {len(failures)}/100")

# Run this multiple times rapidly
```

## 2. **Edge Case Content Attacks**

### Massive Content
```bash
# 1MB of text in a single memory
curl -X POST https://core-nexus-memory-service.onrender.com/memories \
  -H "Content-Type: application/json" \
  -d '{"content": "'$(python3 -c "print('A' * 1048576)")'"}'
```

### Special Characters & SQL Injection Attempts
```json
{
  "content": "'; DROP TABLE memories; --",
  "metadata": {
    "test": "'; DELETE FROM vector_memories WHERE 1=1; --",
    "nested": {
      "sql": "1' OR '1'='1",
      "xss": "<script>alert('xss')</script>"
    }
  }
}
```

### Unicode Torture Test
```json
{
  "content": "🔥💣 Z̴̡̺̻̣̤̱̰̘̟̮͇̈́̈́̄͐̏̎̄͋a̸̢̨̺̯̦͚̙̮̅̀̇̎̔̄̋̾̕͝͝l̵̨̗̣̗̖̩̯̭̑͊͂̐́͊̉̍͘g̸̱̺͔̈́̈́̽̈́̊̄̚o̵̥̅̿̃̔̂̓̌͗̄͝ ̶̨̨̭͖̼̮̘̻̀̓͂͋t̷̖̉̌ë̷́́x̸̱͐t̵̰́ 这是中文 العربية 🚀🎭🎪",
  "metadata": {"emoji": "🤖", "rtl": "مرحبا", "zalgo": "h̸̡̪̯ͨ͊̽̅̾̎ȩ̬̩̾͛ͪ̈́̀́͘ ̶̧̨̱̹̭̯ͧ̾ͬc̷̙̲̝͖ͭ̏ͥͮ͟o͚̪̰̺̻̥͍̲̰m̸̜̗̠̺̬̲̜̥̪̆̋ͭͩ͑ę̴̪̠̭̭s̪̭̱̼̼̉̈́ͪ͋̽̚"}
}
```

## 3. **Read-After-Write Race Condition Test**
```python
# Store and immediately query 1000 times
async def race_test():
    for i in range(1000):
        # Store
        memory_id = await store_memory(f"Race test {i}")
        
        # Immediately query with exact match
        result = await query_memories(f"Race test {i}", limit=1)
        
        if not result or result[0]['id'] != memory_id:
            print(f"FAILED at iteration {i}")
            break
```

## 4. **Vector Dimension Attacks**

### Wrong Dimension Count
```python
# Send 1500 dimensions instead of 1536
bad_embedding = [0.1] * 1500
# Send 2000 dimensions
huge_embedding = [0.1] * 2000
```

### NaN and Infinity Values
```python
# These should break cosine similarity
poison_vectors = [
    [float('nan')] * 1536,
    [float('inf')] * 1536,
    [float('-inf')] * 1536,
    [float('inf'), float('-inf'), float('nan')] + [0.1] * 1533
]
```

## 5. **Query Bombs**

### Massive Limit
```bash
# Request 1 million results
curl -X POST .../memories/query \
  -d '{"query": "", "limit": 1000000}'
```

### Complex Metadata Filters
```json
{
  "query": "test",
  "filters": {
    "nested.deep.value": "test",
    "$or": [
      {"importance_score": {"$gt": 0.9}},
      {"metadata.priority": {"$in": [1,2,3,4,5,6,7,8,9,10]}}
    ]
  }
}
```

## 6. **Connection Pool Exhaustion**
```python
# Open 100 connections and hold them
async def exhaust_pool():
    connections = []
    for i in range(100):
        conn = aiohttp.ClientSession()
        connections.append(conn)
        # Don't close them!
    
    # Now try to query
    await query_memories("test")  # Should timeout or fail
```

## 7. **Memory Leak Test**
```python
# Create memories with increasingly large metadata
for size in [1, 10, 100, 1000, 10000]:
    metadata = {f"key_{i}": "value" * 100 for i in range(size)}
    await store_memory(f"Memory leak test {size}", metadata=metadata)
```

## 8. **Time-Based Attacks**

### Clock Skew
```json
{
  "content": "Time traveler",
  "metadata": {
    "created_at": "1970-01-01T00:00:00Z",
    "future_date": "2099-12-31T23:59:59Z"
  }
}
```

### Rapid Update/Delete
```python
# Create, update importance, then delete rapidly
memory_id = await create_memory("Temporary")
await update_importance(memory_id, 0.9)
await delete_memory(memory_id)
await query_memory(memory_id)  # Should fail gracefully
```

## 9. **Graph Provider Attacks** (if enabled)

### Circular Relationships
```json
{
  "content": "Entity A relates to Entity B relates to Entity C relates to Entity A",
  "metadata": {"entities": ["A", "B", "C"], "circular": true}
}
```

### Entity Explosion
```python
# Create memory with 1000 entities
entities = [f"Entity_{i}" for i in range(1000)]
content = " ".join(entities)
```

## 10. **The Ultimate Chaos Test**
```python
async def chaos_monkey():
    """Do everything wrong at once"""
    tasks = [
        bombard_writes(),
        massive_queries(),
        invalid_vectors(),
        connection_spam(),
        rapid_deletes(),
        metadata_bombs(),
        unicode_torture(),
        sql_injection_attempts()
    ]
    
    # Run all attacks simultaneously
    await asyncio.gather(*tasks, return_exceptions=True)
```

## Expected Failure Points

1. **Connection Pool Exhaustion** - Should see timeouts after ~20 connections
2. **Memory Limits** - Large content might hit PostgreSQL limits
3. **Vector Validation** - Wrong dimensions should fail gracefully
4. **Query Performance** - Large limits might timeout
5. **Transaction Deadlocks** - Concurrent writes to same memory

## How to Know You Broke It

- 500 errors instead of graceful handling
- Timeouts longer than 30 seconds
- Memory leak (service memory usage grows)
- Inconsistent data (write says success but can't read)
- Service crash/restart
- Database connection errors

## Recovery Test

After breaking it, the service should:
1. Auto-recover within 2 minutes
2. Not lose any successfully written data
3. Return to normal performance
4. Clear any stuck connections

**Goal: Find the limits and ensure graceful degradation, not catastrophic failure!**