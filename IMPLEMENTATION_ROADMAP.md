# Core Nexus Implementation Roadmap
## From Vector Storage to True Memory System

---

## 🎯 WEEK 1: Fix Core Functionality

### Day 1-2: Fix Query System
```python
# Current Problem: Queries return 0 despite 1096 memories in DB
# Root Cause: Schema/table issues, connection pool timing

# FIX 1: Direct query method in PgVectorProvider
async def query_direct(self, limit: int = 100) -> list[MemoryResponse]:
    """Direct query bypassing all vector operations for debugging."""
    query = f"""
        SELECT id, content, metadata, importance_score, created_at
        FROM {self.table_name}
        WHERE content IS NOT NULL
        ORDER BY created_at DESC
        LIMIT %s
    """
    # Implementation...

# FIX 2: Add connection pool retry logic
async def ensure_connection(self, max_retries: int = 3):
    """Ensure connection pool is ready before queries."""
    for i in range(max_retries):
        if self.connection_pool:
            return True
        await asyncio.sleep(1)
    return False
```

### Day 3-4: Enable Monitoring
```python
# Uncomment and fix these in api.py:
from .metrics import metrics_collector, get_metrics, record_request
from .tracking import UsageCollector
from .dashboard import MemoryDashboard

# Add proper initialization
usage_collector = UsageCollector(unified_store=unified_store)
memory_dashboard = MemoryDashboard(unified_store)

# Create metrics endpoint that actually works
@app.get("/metrics/detailed")
async def detailed_metrics():
    return {
        "memory_stats": await unified_store.get_detailed_stats(),
        "query_performance": await metrics_collector.get_query_metrics(),
        "usage_patterns": await usage_collector.get_patterns()
    }
```

### Day 5: Implement Basic Deduplication
```python
# Add to memory_service/deduplication.py
class MemoryDeduplicator:
    def __init__(self, similarity_threshold: float = 0.95):
        self.threshold = similarity_threshold
    
    async def find_similar(self, content: str, embedding: list[float]) -> list[MemoryMatch]:
        """Find memories similar to the given content."""
        # Use cosine similarity on embeddings
        # Check content hash for exact matches
        # Return list of potential duplicates
    
    async def merge_memories(self, primary: MemoryResponse, duplicates: list[MemoryResponse]) -> MemoryResponse:
        """Merge duplicate memories into a single consolidated memory."""
        # Combine metadata
        # Keep highest importance score
        # Preserve all timestamps
        # Create audit trail
```

---

## 📅 WEEK 2-4: Build Real Memory Features

### 1. Memory Consolidation System
```python
# memory_service/consolidation.py
class MemoryConsolidator:
    """Consolidates related memories to prevent bloat and improve retrieval."""
    
    async def consolidate_user_memories(self, user_id: str):
        """Periodically consolidate memories for a user."""
        # Group similar memories
        clusters = await self.cluster_memories(user_id)
        
        for cluster in clusters:
            if len(cluster) > 1:
                # Create consolidated memory
                consolidated = await self.merge_cluster(cluster)
                
                # Archive originals
                await self.archive_memories(cluster)
                
                # Store consolidated version
                await self.store_consolidated(consolidated)
    
    async def merge_cluster(self, memories: list[MemoryResponse]) -> ConsolidatedMemory:
        """Merge a cluster of related memories."""
        return ConsolidatedMemory(
            content=self.synthesize_content(memories),
            metadata=self.merge_metadata(memories),
            source_memories=[m.id for m in memories],
            confidence_score=self.calculate_confidence(memories),
            last_accessed=max(m.last_accessed for m in memories)
        )
```

### 2. Temporal Versioning
```python
# models.py additions
class MemoryVersion(BaseModel):
    """Represents a version of a memory."""
    memory_id: UUID
    version: int
    content: str
    metadata: dict[str, Any]
    valid_from: datetime
    valid_to: Optional[datetime]
    change_reason: Optional[str]

# providers.py additions
async def update_memory_with_version(self, memory_id: UUID, new_content: str, reason: str):
    """Update memory while preserving version history."""
    async with self.connection_pool.acquire() as conn:
        # Archive current version
        await conn.execute("""
            INSERT INTO memory_versions 
            SELECT *, NOW() as valid_to, $1 as change_reason
            FROM vector_memories WHERE id = $2
        """, reason, memory_id)
        
        # Update current memory
        await conn.execute("""
            UPDATE vector_memories 
            SET content = $1, version = version + 1, updated_at = NOW()
            WHERE id = $2
        """, new_content, memory_id)
```

### 3. Memory Decay Implementation
```python
# memory_service/decay.py
class MemoryDecayManager:
    """Implements forgetting mechanisms to maintain system efficiency."""
    
    def __init__(self):
        self.decay_rate = 0.1  # 10% decay per period
        self.access_boost = 0.3  # 30% boost when accessed
        self.min_importance = 0.1  # Minimum before deletion
    
    async def apply_decay(self):
        """Apply decay to all memories based on age and access patterns."""
        cutoff_date = datetime.now() - timedelta(days=30)
        
        # Decay memories not accessed recently
        await conn.execute("""
            UPDATE vector_memories
            SET importance_score = GREATEST(
                importance_score * (1 - $1),
                $2
            )
            WHERE last_accessed < $3
            AND importance_score > $2
        """, self.decay_rate, self.min_importance, cutoff_date)
        
        # Delete memories below threshold
        await conn.execute("""
            DELETE FROM vector_memories
            WHERE importance_score < $1
            AND created_at < $2
        """, self.min_importance, cutoff_date)
    
    async def boost_on_access(self, memory_id: UUID):
        """Boost importance when memory is accessed."""
        await conn.execute("""
            UPDATE vector_memories
            SET importance_score = LEAST(
                importance_score + $1,
                1.0
            ),
            last_accessed = NOW(),
            access_count = access_count + 1
            WHERE id = $2
        """, self.access_boost, memory_id)
```

### 4. Feedback Loop System
```python
# memory_service/feedback.py
class MemoryFeedbackSystem:
    """Learn from user interactions to improve memory quality."""
    
    async def record_feedback(self, memory_id: UUID, feedback: FeedbackType, context: dict):
        """Record user feedback on memory usefulness."""
        await conn.execute("""
            INSERT INTO memory_feedback 
            (memory_id, feedback_type, context, timestamp)
            VALUES ($1, $2, $3, NOW())
        """, memory_id, feedback.value, json.dumps(context))
        
        # Adjust importance based on feedback
        if feedback == FeedbackType.HELPFUL:
            await self.decay_manager.boost_on_access(memory_id)
        elif feedback == FeedbackType.NOT_HELPFUL:
            await self.decay_manager.apply_penalty(memory_id)
    
    async def learn_from_patterns(self):
        """Analyze feedback patterns to improve scoring."""
        patterns = await conn.fetch("""
            SELECT 
                m.metadata->>'category' as category,
                AVG(CASE WHEN f.feedback_type = 'helpful' THEN 1 ELSE 0 END) as helpfulness_rate
            FROM memory_feedback f
            JOIN vector_memories m ON f.memory_id = m.id
            GROUP BY m.metadata->>'category'
        """)
        
        # Update scoring weights based on patterns
        await self.update_scoring_weights(patterns)
```

---

## 🚀 MONTH 2-3: Advanced Features

### 1. Fix Knowledge Graph
```python
# Connect existing extraction pipeline
from .gemini_entity_extraction_pipeline import GeminiEntityExtractor

class GraphBuilder:
    def __init__(self):
        self.extractor = GeminiEntityExtractor()
    
    async def process_memory_for_graph(self, memory: MemoryResponse):
        """Extract entities and relationships from memory."""
        # Extract entities
        entities = await self.extractor.extract_entities(memory.content)
        
        # Store in graph
        for entity in entities:
            await self.store_entity(entity)
        
        # Extract relationships
        relationships = await self.extractor.extract_relationships(entities, memory.content)
        
        # Store relationships
        for rel in relationships:
            await self.store_relationship(rel)
```

### 2. Multi-Agent Memory Architecture
```python
# memory_service/multi_agent.py
class MultiAgentMemoryManager:
    """Manages memory isolation and sharing for multiple agents."""
    
    async def create_agent_namespace(self, agent_id: str, config: AgentConfig):
        """Create isolated memory space for an agent."""
        await conn.execute("""
            INSERT INTO agent_namespaces 
            (agent_id, config, created_at)
            VALUES ($1, $2, NOW())
        """, agent_id, json.dumps(config.dict()))
    
    async def share_memory(self, from_agent: str, to_agent: str, memory_id: UUID, permissions: list[str]):
        """Share specific memory between agents."""
        await conn.execute("""
            INSERT INTO shared_memories
            (memory_id, from_agent, to_agent, permissions)
            VALUES ($1, $2, $3, $4)
        """, memory_id, from_agent, to_agent, permissions)
    
    async def query_with_permissions(self, agent_id: str, query: QueryRequest):
        """Query memories respecting agent permissions."""
        # Include own memories and shared memories
        # Filter based on permissions
        # Return combined results
```

### 3. Memory Type System
```python
# models.py additions
class MemoryType(Enum):
    EPISODIC = "episodic"  # Specific events
    SEMANTIC = "semantic"  # General knowledge
    PROCEDURAL = "procedural"  # How-to knowledge

class TypedMemory(MemoryResponse):
    memory_type: MemoryType
    confidence: float
    source_type: str  # conversation, document, api, etc.

# Specialized handlers for each type
class EpisodicMemoryHandler:
    """Handles event-based memories with temporal context."""
    
    async def store_episode(self, event: Event) -> TypedMemory:
        # Extract temporal markers
        # Link to other events
        # Create episodic memory

class SemanticMemoryHandler:
    """Handles fact-based knowledge."""
    
    async def store_fact(self, fact: Fact) -> TypedMemory:
        # Verify against existing knowledge
        # Update belief system
        # Create semantic memory
```

---

## 📊 Success Metrics

### Week 1 Goals:
- ✅ Queries return actual memories (not 0)
- ✅ Response time < 100ms for basic queries
- ✅ Monitoring dashboard shows real metrics
- ✅ Deduplication prevents storing identical content

### Month 1 Goals:
- ✅ Memory count grows logarithmically (not linearly)
- ✅ Retrieval accuracy improves by 20%
- ✅ System automatically forgets outdated info
- ✅ Feedback improves relevance ranking

### Month 3 Goals:
- ✅ Knowledge graph connects related memories
- ✅ Multiple agents can share memories
- ✅ System learns from usage patterns
- ✅ Performance matches or exceeds Mem0 benchmarks

---

## 🔧 Technical Debt to Address

1. **Database Schema**: Migrate from partitioned to optimized structure
2. **Caching**: Implement Redis properly (not in-memory fallback)
3. **Testing**: Create comprehensive test suite with real scenarios
4. **Documentation**: Document actual capabilities, not aspirations
5. **Deployment**: Fix Render configuration for reliability

---

## 📌 Key Principle

**Build incrementally, test thoroughly, ship working features.**

Stop pretending. Start building. The users need a memory system that actually remembers.