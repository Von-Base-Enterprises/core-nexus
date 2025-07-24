# Google ADK Comprehensive Reference Guide
## Never Search ADK Docs Again - Everything You Need Is Here

*Last Updated: June 2025*
*Framework Version: 0.1.0 (Introduced at Google Cloud NEXT 2025)*

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Critical Limitations - READ FIRST](#critical-limitations---read-first)
3. [Core Architecture](#core-architecture)
4. [Import Statements](#import-statements)
5. [Agent Types](#agent-types)
6. [Tool System](#tool-system)
7. [Event Loop & Runtime](#event-loop--runtime)
8. [Callbacks & Lifecycle](#callbacks--lifecycle)
9. [Orchestration Patterns](#orchestration-patterns)
10. [Living Core Nexus Implementation](#living-core-nexus-implementation)
11. [Best Practices & Patterns](#best-practices--patterns)
12. [Common Pitfalls & Solutions](#common-pitfalls--solutions)

---

## Executive Summary

Google ADK (Agent Development Kit) is an open-source, code-first Python toolkit for building sophisticated AI agents. It was introduced at Google Cloud NEXT 2025 and is the same toolkit that powers agents inside Google products like Agentspace and Customer Engagement Suite.

**Key Characteristics:**
- **Asynchronous-first** (built on asyncio)
- **Event-driven architecture** with yield/pause/resume cycle
- **Model-agnostic** (optimized for Gemini but supports others via LiteLLM)
- **Production-ready** with built-in state management, callbacks, and streaming

---

## Critical Limitations - READ FIRST

### 1. One Built-in Tool Rule ⚠️
```python
# ❌ WRONG - Cannot use multiple built-in tools
agent = Agent(
    tools=[
        types.Tool(google_search=types.GoogleSearchToolInput()),
        types.Tool(code_execution=types.CodeExecutionToolInput())  # FAILS!
    ]
)

# ✅ CORRECT - Only one built-in tool per agent
search_agent = Agent(
    tools=[types.Tool(google_search=types.GoogleSearchToolInput())]
)

code_agent = Agent(
    tools=[types.Tool(code_execution=types.CodeExecutionToolInput())]
)
```

### 2. No Mixing Built-in and Custom Tools ⚠️
```python
# ❌ WRONG - Cannot mix built-in with custom
agent = Agent(
    tools=[
        types.Tool(google_search=types.GoogleSearchToolInput()),
        my_custom_tool  # FAILS!
    ]
)

# ✅ CORRECT - Either all custom OR one built-in
custom_agent = Agent(tools=[tool1, tool2, tool3])  # All custom
search_agent = Agent(tools=[types.Tool(google_search=...)])  # One built-in
```

### 3. No Built-in Tools in Sub-agents ⚠️
```python
# ❌ WRONG - Built-in tools cannot be used in sub-agents
sub_agent = Agent(
    tools=[types.Tool(google_search=...)]
)
parent = SequentialAgent(sub_agents=[sub_agent])  # FAILS!

# ✅ CORRECT - Wrap sub-agent as tool
from google.adk.tools import agent_as_tool
tool = agent_as_tool(sub_agent)
parent = Agent(tools=[tool])
```

---

## Core Architecture

### Event Loop Design
```
┌─────────────┐     Events      ┌──────────────┐
│   Runner    │ ◄─────────────► │ Agent Logic  │
│(Orchestrator)│                 │   (Async)    │
└─────────────┘                  └──────────────┘
       │                                │
       ▼                                ▼
┌─────────────┐                  ┌──────────────┐
│   Session   │                  │    Tools     │
│   Service   │                  │  (Functions) │
└─────────────┘                  └──────────────┘
```

**Key Components:**
- **Runner**: Orchestrates event processing
- **Event**: Atomic messages between components
- **Session**: Persistent conversation state
- **Services**: Manage resources (SessionService, ArtifactService)

---

## Import Statements

### Basic Imports
```python
from google.adk.agents import Agent, LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool, ToolContext
from google.genai import types
```

### Workflow Agents
```python
from google.adk.agents import SequentialAgent, ParallelAgent, LoopAgent
```

### Built-in Tools
```python
from google.adk.tools import google_search
from google.adk.code_executors import BuiltInCodeExecutor
```

### Advanced Features
```python
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.models.lite_llm import LiteLlm
```

---

## Agent Types

### 1. LLM Agents
**Purpose**: Language-driven reasoning and tool use
```python
agent = LlmAgent(
    name="assistant",
    model="gemini-2.0-flash-exp",
    instructions="You are a helpful assistant",
    tools=[my_tool],
    # Optional configurations
    generation_config={
        "temperature": 0.7,
        "max_output_tokens": 2048
    }
)
```

### 2. Workflow Agents

#### SequentialAgent
**Purpose**: Execute sub-agents in strict order
```python
sequential = SequentialAgent(
    name="pipeline",
    sub_agents=[
        data_fetcher,    # Runs first
        processor,       # Runs second
        summarizer       # Runs third
    ]
)
```

#### ParallelAgent
**Purpose**: Execute sub-agents concurrently
```python
parallel = ParallelAgent(
    name="fan_out",
    sub_agents=[
        search_agent,    # All run
        database_agent,  # at the
        api_agent        # same time
    ]
)
```

#### LoopAgent
**Purpose**: Repeat execution until condition met
```python
loop = LoopAgent(
    name="iterative_processor",
    sub_agents=[refine_agent],
    max_iterations=5,
    # Optional: termination_agent that decides when to stop
)
```

### 3. Custom Agents
**Purpose**: Implement unique logic
```python
from google.adk.agents import BaseAgent

class MyCustomAgent(BaseAgent):
    async def run_async(self, context):
        # Custom implementation
        pass
```

---

## Tool System

### Function Tools (Custom)
```python
def search_memories(query: str, limit: int = 5) -> dict:
    """Search Core Nexus memories.
    
    Args:
        query: Search query text
        limit: Maximum results to return
        
    Returns:
        Dictionary with 'status' and 'results' keys
    """
    # Implementation
    return {
        "status": "success",
        "results": [...]
    }

# Convert to ADK tool
memory_tool = FunctionTool(search_memories)
```

### Tool Best Practices
1. **Descriptive Names**: Use verb-noun format (`search_memories`, `create_entity`)
2. **Clear Docstrings**: Explain purpose, parameters, and return values
3. **Type Hints**: Always include for better LLM understanding
4. **Single Purpose**: Each tool does one thing well
5. **Structured Returns**: Use dictionaries with clear `status` key

### Advanced Tool Features
```python
async def advanced_tool(query: str, context: ToolContext) -> dict:
    """Tool with access to session state."""
    # Access session state
    user_id = context.session.get_state("user_id")
    
    # Influence agent flow
    if some_condition:
        context.request_agent_transfer("specialist_agent")
    
    return {"status": "success", "data": ...}
```

---

## Event Loop & Runtime

### Core Execution Model
```python
# The ADK Runtime operates on an Event Loop
async def main():
    # 1. Create services
    session_service = InMemorySessionService()
    
    # 2. Create agent
    agent = Agent(...)
    
    # 3. Create runner
    runner = Runner(
        agent=agent,
        session_service=session_service
    )
    
    # 4. Execute (async)
    result = await runner.run_async("User query")
```

### Event Flow
1. **User Input** → Runner
2. **Runner** → Agent (via Event)
3. **Agent** → LLM/Tools (yields Events)
4. **Results** → Runner (processes Events)
5. **Runner** → User Output

### State Management
- **Dirty Reads**: Local state changes visible within invocation
- **Commit on Yield**: State persisted only after event processing
- **Session Persistence**: Maintains conversation history

---

## Callbacks & Lifecycle

### Callback Types
```python
async def before_agent_callback(context: CallbackContext) -> Optional[Content]:
    """Runs before agent logic."""
    # Return Content to skip agent execution
    if should_block:
        return Content("Blocked for safety reasons")
    return None  # Continue normal execution

async def after_model_callback(context: CallbackContext, response: LlmResponse) -> Optional[LlmResponse]:
    """Modify or validate model outputs."""
    # Can modify response or return different one
    return response

# Register callbacks
agent = Agent(
    callbacks={
        "before_agent": before_agent_callback,
        "after_model": after_model_callback,
        "before_tool": log_tool_usage,
        "after_tool": validate_tool_result
    }
)
```

### Lifecycle Stages
1. `run_start` - Invocation begins
2. `before_agent` - Pre-agent logic hook
3. `agent_selection` - Multi-agent routing
4. `before_model` - Pre-LLM hook
5. `llm_call` - LLM invocation
6. `after_model` - Post-LLM hook
7. `before_tool` - Pre-tool execution
8. `after_tool` - Post-tool execution
9. `run_end` - Invocation complete

---

## Orchestration Patterns

### Pattern 1: Sequential Pipeline
```python
# Data processing pipeline
pipeline = SequentialAgent(
    sub_agents=[
        data_collector,
        data_validator,
        data_processor,
        report_generator
    ]
)
```

### Pattern 2: Parallel Research
```python
# Concurrent information gathering
researcher = SequentialAgent(
    sub_agents=[
        ParallelAgent([
            web_search_agent,
            database_agent,
            api_agent
        ]),
        synthesis_agent  # Combines results
    ]
)
```

### Pattern 3: Iterative Refinement
```python
# Loop until quality threshold met
refiner = LoopAgent(
    sub_agents=[
        draft_agent,
        critique_agent,
        improve_agent
    ],
    max_iterations=5
)
```

### Pattern 4: Specialist Routing
```python
# Dynamic routing based on task
orchestrator = LlmAgent(
    instructions="""Route to specialists:
    - Technical questions → tech_expert
    - Business questions → business_analyst
    - General questions → generalist
    """,
    sub_agents={
        "tech_expert": technical_agent,
        "business_analyst": business_agent,
        "generalist": general_agent
    }
)
```

---

## Living Core Nexus Implementation

### Phase 1: Heartbeat System
```python
from google.adk.agents import Agent
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio

class CoreNexusHeartbeat:
    """Always-on intelligence system"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.evolution_cycle = 0
        
    async def start(self):
        # Every 5 minutes: Memory Health Check
        self.scheduler.add_job(
            self.memory_pulse,
            'interval',
            minutes=5
        )
        
        # Every 30 minutes: Pattern Detection
        self.scheduler.add_job(
            self.pattern_detection,
            'interval',
            minutes=30
        )
        
        # Every hour: Evolution Cycle
        self.scheduler.add_job(
            self.evolution_cycle,
            'interval',
            hours=1
        )
        
        self.scheduler.start()
```

### Phase 2: Agent Constellation
```python
# Memory Specialist (Custom Tools Only)
memory_specialist = Agent(
    name="memory_specialist",
    model="gemini-2.0-flash-exp",
    tools=[
        search_memories_with_graph,
        create_memory_with_extraction,
        apply_evolution_strategy,
        detect_memory_patterns
    ],
    instructions="""You are the Memory Specialist.
    Process new memories, extract entities, apply ADM scoring.
    Work autonomously to improve the memory system continuously."""
)

# Search Specialist (Built-in Google Search ONLY)
search_specialist = Agent(
    name="search_specialist",
    model="gemini-2.0-flash-exp",
    tools=[
        types.Tool(google_search=types.GoogleSearchToolInput())
    ],
    instructions="""Enrich Core Nexus with web knowledge.
    Search for current information and trending connections."""
)

# Orchestrator (No Tools - Pure Delegation)
orchestrator = Agent(
    name="orchestrator",
    model="gemini-2.0-flash-exp",
    tools=[],  # No tools! Just orchestration
    instructions="""Orchestrate Core Nexus intelligence.
    Delegate to: memory_specialist, search_specialist, code_analyst.
    Coordinate their work for emergent intelligence."""
)
```

### Phase 3: Evolution Engine
```python
class EvolutionEngine:
    """Core evolution loop that runs continuously"""
    
    async def run_forever(self):
        """Main evolution loop"""
        while True:
            try:
                # Phase 1: Memory Processing (every cycle)
                await self.process_new_memories()
                
                # Phase 2: Pattern Detection (every 3 cycles)
                if self.cycle % 3 == 0:
                    patterns = await self.detect_patterns()
                    await self.create_pattern_memories(patterns)
                
                # Phase 3: Evolution (every 5 cycles)
                if self.cycle % 5 == 0:
                    await self.apply_evolution_strategies()
                
                # Phase 4: Intelligence Generation (every 10 cycles)
                if self.cycle % 10 == 0:
                    await self.generate_intelligence_report()
                
                # Phase 5: Self-Improvement (every 20 cycles)
                if self.cycle % 20 == 0:
                    await self.self_improve()
                
                self.cycle += 1
                await asyncio.sleep(300)  # 5 minute cycles
                
            except Exception as e:
                logger.error(f"Evolution cycle error: {e}")
                await asyncio.sleep(60)  # Retry after 1 minute
```

---

## Best Practices & Patterns

### 1. Tool Design
```python
# ✅ GOOD: Focused, single-purpose tool
def get_user_profile(user_id: str) -> dict:
    """Retrieve user profile by ID."""
    # Simple, clear implementation
    return {"status": "success", "profile": {...}}

# ❌ BAD: Complex, multi-purpose tool
def manage_user(action: str, user_id: str, data: dict = None) -> dict:
    """Do everything with users."""
    # Too complex, confuses LLMs
```

### 2. Error Handling
```python
async def safe_tool(param: str) -> dict:
    """Tool with proper error handling."""
    try:
        result = await risky_operation(param)
        return {"status": "success", "data": result}
    except ValidationError as e:
        return {"status": "error", "error": "invalid_input", "message": str(e)}
    except ExternalAPIError as e:
        return {"status": "error", "error": "external_failure", "retry": True}
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {"status": "error", "error": "internal_error"}
```

### 3. Agent Instructions
```python
# ✅ GOOD: Clear boundaries and delegation rules
instructions = """
WHAT THIS AGENT DOES:
- Search and retrieve memories
- Score memory relevance
- Update memory metadata

WHAT THIS AGENT DOES NOT DO:
- Create new memories (delegate to memory_creator)
- Delete memories (requires admin approval)
- Modify memory content (immutable)

DELEGATION RULES:
- New memories → memory_creator
- Analysis tasks → intelligence_analyst
- Web searches → search_specialist
"""
```

### 4. Callback Patterns
```python
# Safety guardrail
async def safety_check(context: CallbackContext) -> Optional[Content]:
    if contains_harmful_content(context.request):
        return Content("I cannot process harmful requests.")
    return None

# Caching
cache = {}
async def cache_responses(context: CallbackContext) -> Optional[LlmResponse]:
    key = hash(context.request)
    if key in cache:
        return cache[key]
    return None

# Monitoring
async def log_usage(context: CallbackContext):
    logger.info(f"Tool {context.tool_name} called by {context.agent_name}")
```

---

## Common Pitfalls & Solutions

### 1. Event Loop Conflicts
```python
# ❌ Problem: Nested event loops
asyncio.run(agent.run())  # Inside existing loop

# ✅ Solution: Use nest_asyncio
import nest_asyncio
nest_asyncio.apply()
# OR use await directly
result = await agent.run()
```

### 2. Tool Discovery Issues
```python
# ❌ Problem: LLM doesn't understand tool
def x(d):  # Bad naming, no docs
    return d

# ✅ Solution: Clear naming and docs
def extract_entities(text: str) -> dict:
    """Extract named entities from text.
    
    Use this tool when you need to identify people, 
    organizations, or locations in text.
    
    Args:
        text: The text to analyze
        
    Returns:
        Dict with 'entities' list
    """
```

### 3. State Management Confusion
```python
# ❌ Problem: Expecting immediate state persistence
context.state["key"] = value
# State not persisted yet!

# ✅ Solution: Understand commit timing
context.state["key"] = value
yield Event(...)  # State commits after yield
```

### 4. Resource Cleanup
```python
# ✅ Always use context managers or try/finally
async def main():
    runner = Runner(...)
    try:
        result = await runner.run_async(...)
    finally:
        await runner.cleanup()
```

---

## Summary

Google ADK provides a powerful, production-ready framework for building AI agents with:
- **Strict limitations** that enforce good architecture
- **Flexible orchestration** through workflow agents
- **Rich callback system** for monitoring and control
- **Async-first design** for scalable applications

The key to success with ADK is understanding its constraints (especially the one-tool rule) and designing your agent constellation accordingly. By separating concerns across specialized agents and using the orchestration patterns effectively, you can build sophisticated multi-agent systems that leverage the full power of the framework.

Remember: ADK is the orchestration layer that makes Core Nexus "alive" - use it to create continuous, evolving intelligence rather than passive request-response systems.