# Core Nexus: THIS WEEK Action Plan
## Monday June 17 - Friday June 21, 2025

---

## 🎯 MISSION: Get Core Nexus Actually Working

**Goal**: By Friday, Core Nexus must reliably store and retrieve memories. Period.

---

## 📅 DAILY OBJECTIVES

### Monday: Fix the Damn Queries
**Morning (2-3 hours)**
```bash
# 1. Test current state
curl https://core-nexus-memory-service.onrender.com/health  # Shows 1096
curl -X POST https://core-nexus-memory-service.onrender.com/memories/query -d '{"query":"","limit":5}'  # Returns 0

# 2. Deploy emergency fix
cd python/memory_service
# Create direct_query_fix.py that bypasses all the fancy stuff
# Just SELECT * FROM vector_memories LIMIT 100
# Deploy it
```

**Afternoon (3-4 hours)**
- Add `/debug/direct-query` endpoint that uses raw SQL
- Test every query method to find which ones work
- Document EXACTLY why queries fail
- Create `QUERY_FIX_PLAN.md` with specific solutions

**Deliverable**: At least ONE endpoint that returns actual memories

### Tuesday: Enable Monitoring & Metrics
**Morning (3 hours)**
```python
# Fix these commented sections in api.py:
# Line 55-58: Uncomment metrics imports
# Line 273-278: Enable usage_collector
# Line 281-284: Enable memory_dashboard

# Create fallback implementations if needed:
class SimpleMetricsCollector:
    def __init__(self):
        self.metrics = {
            'total_queries': 0,
            'total_stores': 0,
            'query_times': []
        }
    
    async def record_query(self, duration: float):
        self.metrics['total_queries'] += 1
        self.metrics['query_times'].append(duration)
```

**Afternoon (3 hours)**
- Create `/metrics/summary` endpoint showing:
  - Total memories
  - Queries per hour
  - Average response time
  - Error rate
  - Memory growth rate
- Set up basic Grafana dashboard (if time permits)

**Deliverable**: Working metrics endpoint with real data

### Wednesday: Implement Basic Deduplication
**Morning (4 hours)**
```python
# Create memory_service/simple_dedup.py
class SimpleDeduplication:
    def __init__(self, threshold: float = 0.95):
        self.threshold = threshold
    
    async def is_duplicate(self, content: str, embedding: list[float]) -> tuple[bool, Optional[UUID]]:
        # 1. Check exact content match (MD5 hash)
        content_hash = hashlib.md5(content.encode()).hexdigest()
        existing = await db.fetch("SELECT id FROM vector_memories WHERE content_hash = $1", content_hash)
        if existing:
            return True, existing[0]['id']
        
        # 2. Check embedding similarity (if enabled)
        if embedding and DEDUP_SEMANTIC_ENABLED:
            similar = await db.fetch("""
                SELECT id, embedding <=> $1 as distance
                FROM vector_memories
                WHERE embedding <=> $1 < $2
                ORDER BY distance
                LIMIT 1
            """, embedding, 1 - self.threshold)
            if similar:
                return True, similar[0]['id']
        
        return False, None
```

**Afternoon (2 hours)**
- Integrate deduplication into store_memory flow
- Add metrics for duplicates prevented
- Test with common phrases

**Deliverable**: No more storing identical memories

### Thursday: Create Basic Memory Management
**All Day (6-8 hours)**
```python
# Create memory_service/memory_manager.py
class MemoryManager:
    """Basic memory lifecycle management."""
    
    async def add_metadata_fields(self):
        """Add missing fields to track memory usage."""
        await db.execute("""
            ALTER TABLE vector_memories 
            ADD COLUMN IF NOT EXISTS last_accessed TIMESTAMP DEFAULT NOW(),
            ADD COLUMN IF NOT EXISTS access_count INTEGER DEFAULT 0,
            ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE
        """)
    
    async def update_on_access(self, memory_id: UUID):
        """Track when memories are accessed."""
        await db.execute("""
            UPDATE vector_memories 
            SET last_accessed = NOW(), 
                access_count = access_count + 1
            WHERE id = $1
        """, memory_id)
    
    async def archive_old_memories(self, days: int = 90):
        """Archive memories not accessed in N days."""
        await db.execute("""
            UPDATE vector_memories 
            SET is_archived = TRUE 
            WHERE last_accessed < NOW() - INTERVAL '$1 days'
            AND is_archived = FALSE
        """, days)
    
    async def get_memory_stats(self) -> dict:
        """Get detailed memory statistics."""
        return await db.fetchrow("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE is_archived) as archived,
                COUNT(*) FILTER (WHERE access_count > 0) as accessed,
                AVG(access_count) as avg_access_count,
                MAX(last_accessed) as most_recent_access
            FROM vector_memories
        """)
```

**Deliverable**: Basic memory lifecycle tracking

### Friday: Testing, Documentation & Deployment
**Morning (3 hours)**
- Create `test_suite.py` with 10 essential tests:
  1. Can store memory
  2. Can retrieve by ID
  3. Can search by content
  4. Deduplication works
  5. Metrics are accurate
  6. Archives old memories
  7. Handles errors gracefully
  8. Performance < 100ms
  9. Handles concurrent requests
  10. Data persists across restarts

**Afternoon (3 hours)**
- Update README.md with ACTUAL features (not marketing)
- Create `CHANGELOG.md` with this week's fixes
- Write `KNOWN_ISSUES.md` with honest assessment
- Deploy all fixes to production
- Run full test suite
- Create `WEEK_1_REPORT.md` with results

**Deliverable**: Stable, documented, tested system

---

## 🚫 NOT THIS WEEK

These are important but not urgent:
- Knowledge graph (it's broken, leave it)
- Multi-agent features (focus on single agent)
- Advanced AI features (get basics working first)
- UI/Dashboard (API first)
- Optimization (make it work, then make it fast)

---

## 📊 Success Criteria

By Friday 5 PM, we must have:

1. **Queries Work**: Can retrieve memories reliably
2. **Metrics Work**: Can see what's happening
3. **Dedup Works**: No more duplicate storage
4. **Basic Management**: Track memory usage
5. **Tests Pass**: Automated validation

If these five things work, we've made more progress than the last 6 months.

---

## 🆘 If Things Go Wrong

**Query fixes not working?**
- Revert to direct SQL queries
- Skip vector search temporarily
- Focus on making SOMETHING work

**Metrics too complex?**
- Use simple in-memory counters
- Log to file if needed
- Just count things

**Dedup taking too long?**
- Start with exact match only
- Add similarity later
- Prevent the obvious duplicates

**Running out of time?**
- Focus on queries first
- Everything else is secondary
- Working > Perfect

---

## 💬 Daily Standup Questions

Every day at 9 AM, answer:
1. What worked yesterday?
2. What's blocking progress?
3. What's the plan for today?
4. Are we on track for Friday?

---

## 🎯 Remember

**This week is about FIXING, not FEATURING.**

Every decision should be guided by: "Does this help store and retrieve memories reliably?"

If the answer is no, it waits until next week.

**Let's stop building castles in the sky and start pouring a solid foundation.**