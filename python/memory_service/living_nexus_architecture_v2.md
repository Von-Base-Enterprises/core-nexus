# Living Core Nexus Architecture v2.0
## Addressing Critical Gaps: Evaluation, Error Handling, and Robustness

### Executive Summary
This revised architecture addresses the critical feedback on v1.0, specifically:
1. **ADK Evaluation Integration**: Built-in testing and quality assurance
2. **Clear Agent Descriptions**: Concise delegation instructions
3. **Structured Error Handling**: Comprehensive logging and recovery
4. **Simplified Tools**: Focused, single-purpose tool design
5. **Fallback Strategies**: Multi-layer resilience patterns

### 1. Agent Architecture with Clear Descriptions

#### 1.1 Master Orchestrator Agent
```python
orchestrator_agent = Agent(
    name="nexus_orchestrator",
    instructions="""
    WHAT THIS AGENT DOES:
    - Routes tasks to specialized agents based on intent
    - Monitors agent health and performance
    - Manages conversation flow and context
    
    WHAT THIS AGENT DOES NOT DO:
    - Direct memory operations (delegates to memory_specialist)
    - Entity extraction (delegates to knowledge_builder)
    - Complex reasoning (delegates to intelligence_analyst)
    
    DELEGATION RULES:
    - Memory queries -> memory_specialist
    - Entity/relationship tasks -> knowledge_builder
    - Analysis/insights -> intelligence_analyst
    - System health -> monitor_agent
    """,
    tools=[routing_tool, health_check_tool],
    model="gemini-2.0-flash-exp"
)
```

#### 1.2 Memory Specialist Agent
```python
memory_specialist = Agent(
    name="memory_specialist",
    instructions="""
    WHAT THIS AGENT DOES:
    - Searches memories using vector similarity
    - Creates new memories from conversations
    - Updates memory importance scores
    
    WHAT THIS AGENT DOES NOT DO:
    - Entity extraction (return to orchestrator)
    - Complex analysis (return to orchestrator)
    - Direct database operations (uses API only)
    
    ERROR HANDLING:
    - Empty results: Suggest alternative queries
    - API failures: Use cache fallback
    - Invalid input: Request clarification
    """,
    tools=[search_memory_tool, create_memory_tool],
    model="gemini-2.0-flash-exp"
)
```

#### 1.3 Knowledge Builder Agent
```python
knowledge_builder = Agent(
    name="knowledge_builder",
    instructions="""
    WHAT THIS AGENT DOES:
    - Extracts entities from text
    - Identifies relationships between entities
    - Updates knowledge graph
    
    WHAT THIS AGENT DOES NOT DO:
    - Memory search (return to orchestrator)
    - Complex reasoning (return to orchestrator)
    - Delete operations (requires escalation)
    
    EXTRACTION RULES:
    - Minimum confidence: 0.7
    - Max entities per text: 10
    - Supported types: PERSON, ORG, TECH, PRODUCT, LOCATION
    """,
    tools=[extract_entities_tool, create_relationship_tool],
    model="gemini-2.0-flash-exp"
)
```

### 2. Simplified Tool Design

#### 2.1 Focused Search Tool (Replaces Complex Multi-Function Tool)
```python
# Before: Complex tool with multiple responsibilities
# After: Simple, focused tool
search_memory_tool = Tool(
    name="search_memory",
    description="Search memories by text similarity",
    parameters={
        "query": "Search query text",
        "limit": "Number of results (1-10)"
    },
    error_handling={
        "empty_results": "return_alternative_suggestions",
        "api_timeout": "use_cached_results",
        "invalid_query": "request_clarification"
    }
)

# Implementation with structured error handling
async def search_memory_impl(query: str, limit: int = 5) -> ToolResult:
    try:
        # Input validation
        if not query or len(query) < 3:
            return ToolResult(
                success=False,
                error="Query too short",
                fallback_action="request_clarification"
            )
        
        # Primary search
        results = await memory_store.search(query, limit)
        
        if not results:
            # Fallback: Try alternative search
            alternatives = await generate_alternative_queries(query)
            return ToolResult(
                success=True,
                data=[],
                suggestions=alternatives
            )
        
        return ToolResult(success=True, data=results)
        
    except TimeoutError:
        # Fallback: Use cache
        cached = await get_cached_search(query)
        return ToolResult(
            success=True,
            data=cached,
            warning="Using cached results due to timeout"
        )
    except Exception as e:
        logger.error(f"Search failed: {e}", extra={
            "query": query,
            "limit": limit,
            "trace": traceback.format_exc()
        })
        return ToolResult(
            success=False,
            error=str(e),
            fallback_action="escalate_to_orchestrator"
        )
```

#### 2.2 Simple Entity Extraction Tool
```python
extract_entities_tool = Tool(
    name="extract_entities",
    description="Extract named entities from text",
    parameters={
        "text": "Text to analyze",
        "types": "Entity types to extract"
    },
    constraints={
        "max_text_length": 1000,
        "max_entities": 10,
        "min_confidence": 0.7
    }
)
```

### 3. ADK Evaluation Integration

#### 3.1 Built-in Evaluation Tools
```python
from genai import evaluation

# Quality evaluation for each agent
quality_evaluator = evaluation.QualityEvaluator(
    criteria=[
        "response_accuracy",
        "task_completion",
        "delegation_appropriateness",
        "error_recovery"
    ]
)

# Safety evaluation
safety_evaluator = evaluation.SafetyEvaluator(
    thresholds={
        "harmful_content": 0.0,
        "personal_info_exposure": 0.1,
        "prompt_injection": 0.0
    }
)

# Performance evaluation
performance_evaluator = evaluation.PerformanceEvaluator(
    metrics=[
        "response_time",
        "token_usage",
        "cache_hit_rate",
        "fallback_frequency"
    ]
)
```

#### 3.2 Continuous Evaluation Loop
```python
class EvaluationManager:
    def __init__(self):
        self.evaluators = {
            'quality': quality_evaluator,
            'safety': safety_evaluator,
            'performance': performance_evaluator
        }
        self.evaluation_history = []
    
    async def evaluate_interaction(self, agent_name: str, 
                                  interaction: Dict) -> EvaluationResult:
        """Evaluate a single agent interaction"""
        results = {}
        
        for eval_type, evaluator in self.evaluators.items():
            try:
                score = await evaluator.evaluate(
                    agent=agent_name,
                    input=interaction['input'],
                    output=interaction['output'],
                    context=interaction.get('context', {})
                )
                results[eval_type] = score
            except Exception as e:
                logger.error(f"Evaluation failed: {eval_type}", exc_info=True)
                results[eval_type] = {'error': str(e)}
        
        # Store for trend analysis
        self.evaluation_history.append({
            'timestamp': datetime.now(),
            'agent': agent_name,
            'results': results
        })
        
        # Trigger alerts if needed
        await self._check_evaluation_thresholds(agent_name, results)
        
        return results
```

### 4. Structured Error Handling System

#### 4.1 Error Classification and Recovery
```python
class ErrorHandler:
    """Centralized error handling with recovery strategies"""
    
    ERROR_CATEGORIES = {
        'RECOVERABLE': {
            'timeout': 'retry_with_backoff',
            'rate_limit': 'queue_and_retry',
            'empty_result': 'try_alternative',
            'partial_failure': 'return_partial'
        },
        'ESCALATABLE': {
            'auth_failure': 'escalate_to_admin',
            'data_corruption': 'escalate_with_snapshot',
            'repeated_failure': 'escalate_with_history'
        },
        'FATAL': {
            'database_down': 'activate_readonly_mode',
            'api_key_invalid': 'disable_feature',
            'system_overload': 'emergency_shutdown'
        }
    }
    
    async def handle_error(self, error: Exception, context: Dict) -> ErrorResponse:
        """Main error handling logic"""
        error_type = self._classify_error(error)
        category = self._get_category(error_type)
        
        # Log with full context
        logger.error(
            f"Error in {context.get('agent', 'unknown')}: {error_type}",
            extra={
                'error_type': error_type,
                'category': category,
                'context': context,
                'traceback': traceback.format_exc()
            }
        )
        
        # Execute recovery strategy
        recovery_strategy = self.ERROR_CATEGORIES[category][error_type]
        result = await self._execute_recovery(recovery_strategy, error, context)
        
        # Track for patterns
        await self._track_error_pattern(error_type, context)
        
        return result
```

#### 4.2 Logging Infrastructure
```python
import structlog
from opentelemetry import trace

# Structured logging setup
logger = structlog.get_logger()
logger = logger.bind(service="core_nexus", version="2.0")

# Trace setup for distributed tracing
tracer = trace.get_tracer("core_nexus")

class AgentLogger:
    """Agent-specific logging with context preservation"""
    
    def __init__(self, agent_name: str):
        self.logger = logger.bind(agent=agent_name)
        self.current_span = None
    
    def start_operation(self, operation: str, **kwargs):
        """Start a traced operation"""
        self.current_span = tracer.start_span(
            f"{self.agent_name}.{operation}",
            attributes=kwargs
        )
        self.logger.info(f"Starting {operation}", **kwargs)
    
    def log_decision(self, decision: str, confidence: float, **kwargs):
        """Log agent decisions for audit trail"""
        self.logger.info(
            "Agent decision",
            decision=decision,
            confidence=confidence,
            **kwargs
        )
    
    def log_error(self, error: Exception, recoverable: bool = True):
        """Log errors with recovery information"""
        self.logger.error(
            "Agent error",
            error_type=type(error).__name__,
            error_message=str(error),
            recoverable=recoverable,
            traceback=traceback.format_exc()
        )
```

### 5. Multi-Layer Fallback Strategies

#### 5.1 Agent-Level Fallbacks
```python
class AgentFallbackChain:
    """Implements cascading fallback strategies for agents"""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.fallback_chain = self._build_fallback_chain()
    
    def _build_fallback_chain(self) -> List[FallbackStrategy]:
        """Build agent-specific fallback chain"""
        if self.agent_name == "memory_specialist":
            return [
                RetryWithBackoff(max_attempts=3),
                UseCachedResults(ttl=300),
                DegradeToBasicSearch(),
                ReturnEmptyWithSuggestions()
            ]
        elif self.agent_name == "knowledge_builder":
            return [
                RetryWithSimplification(),
                UsePretrainedExtractor(),
                ManualReviewQueue(),
                SkipWithWarning()
            ]
        # ... other agents
    
    async def execute_with_fallbacks(self, operation: Callable, 
                                    *args, **kwargs) -> Any:
        """Execute operation with fallback chain"""
        last_error = None
        
        for i, strategy in enumerate(self.fallback_chain):
            try:
                logger.info(f"Attempting with strategy {i}: {strategy}")
                result = await strategy.execute(operation, *args, **kwargs)
                
                if i > 0:  # We used a fallback
                    logger.warning(
                        f"Operation succeeded with fallback",
                        strategy=str(strategy),
                        attempt=i
                    )
                
                return result
                
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Strategy {strategy} failed",
                    error=str(e)
                )
                continue
        
        # All fallbacks exhausted
        raise FallbacksExhausted(
            f"All {len(self.fallback_chain)} strategies failed",
            last_error=last_error
        )
```

#### 5.2 System-Level Fallbacks
```python
class SystemFallbackManager:
    """System-wide fallback coordination"""
    
    def __init__(self):
        self.circuit_breakers = {}
        self.degraded_services = set()
    
    async def monitor_health(self):
        """Continuous health monitoring with automatic degradation"""
        while True:
            for service in ['memory_store', 'knowledge_graph', 'llm_api']:
                health = await self._check_service_health(service)
                
                if health.error_rate > 0.5:
                    await self._activate_circuit_breaker(service)
                elif health.latency_p99 > 5000:
                    await self._enable_degraded_mode(service)
                elif service in self.degraded_services and health.is_healthy:
                    await self._restore_full_service(service)
            
            await asyncio.sleep(30)  # Check every 30 seconds
```

### 6. Implementation Timeline

#### Phase 1: Foundation (Week 1-2)
- Set up structured logging infrastructure
- Implement error classification system
- Create basic fallback strategies
- Deploy evaluation hooks

#### Phase 2: Agent Refinement (Week 3-4)
- Rewrite agent descriptions for clarity
- Simplify existing tools
- Add agent-specific error handlers
- Test delegation patterns

#### Phase 3: Evaluation Integration (Week 5-6)
- Integrate ADK evaluation tools
- Set up continuous monitoring
- Create evaluation dashboards
- Establish baseline metrics

#### Phase 4: Hardening (Week 7-8)
- Stress test fallback chains
- Tune circuit breakers
- Add chaos testing
- Document recovery procedures

### 7. Success Metrics

1. **Reliability**
   - 99.9% uptime for core operations
   - <5% fallback activation rate
   - <1% complete failure rate

2. **Performance**
   - <500ms p95 response time
   - >80% cache hit rate during degradation
   - <2s recovery time from failures

3. **Quality**
   - >90% task completion rate
   - >85% delegation accuracy
   - <10% escalation rate

4. **Observability**
   - 100% error categorization
   - <1min alert latency
   - Full trace coverage

This revised architecture addresses all critical gaps while maintaining the vision of a self-evolving system. The focus on evaluation, error handling, and fallback strategies ensures Core Nexus can operate reliably while continuously improving.