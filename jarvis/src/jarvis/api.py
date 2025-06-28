"""
JARVIS FastAPI Server
REST API for interacting with the JARVIS AI Agent System
"""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import structlog
import uvicorn

from .config import get_config
from .langgraph_supervisor import get_supervisor
from .core_nexus_bridge import get_bridge
from .gemini_integration import GeminiAgent
from .strategic_intelligence_processor import StrategicIntelligenceProcessor

logger = structlog.get_logger(__name__)
config = get_config()

# Request/Response Models
class TaskRequest(BaseModel):
    """Request model for JARVIS task processing"""
    task: str = Field(..., description="The task for JARVIS to process")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for the task")
    priority: Optional[str] = Field("medium", description="Task priority: low, medium, high")

class TaskResponse(BaseModel):
    """Response model for JARVIS task processing"""
    task_id: str
    success: bool
    task: str
    final_decision: Optional[Dict[str, Any]] = None
    agent_outputs: Dict[str, Any] = {}
    learning_opportunities: List[str] = []
    improvement_suggestions: List[str] = []
    iterations: int = 0
    duration: float = 0.0
    error: Optional[str] = None

class ChatRequest(BaseModel):
    """Request model for direct chat with JARVIS"""
    message: str = Field(..., description="Message to send to JARVIS")
    agent: Optional[str] = Field("supervisor", description="Which agent to chat with")

class ChatResponse(BaseModel):
    """Response model for JARVIS chat"""
    agent: str
    response: str
    thinking: Optional[str] = None
    confidence: float
    reasoning_steps: List[str] = []
    timestamp: datetime

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    jarvis_version: str
    core_nexus_status: Dict[str, Any]
    active_tasks: int
    
class MemoryRequest(BaseModel):
    """Request model for memory operations"""
    content: str = Field(..., description="Memory content to store")
    importance_score: float = Field(..., ge=0.0, le=1.0, description="Importance score (0-1)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class MemorySearchRequest(BaseModel):
    """Request model for memory search"""
    query: str = Field(..., description="Search query")
    limit: int = Field(10, ge=1, le=50, description="Maximum number of results")

class StrategicIntelligenceRequest(BaseModel):
    """Request model for strategic intelligence analysis"""
    task: str = Field(..., description="Strategic query for analysis")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for analysis")
    priority: Optional[str] = Field("high", description="Analysis priority")

class StrategicIntelligenceResponse(BaseModel):
    """Response model for strategic intelligence analysis"""
    success: bool
    analysis_id: str
    executive_summary: str
    strategic_recommendations: List[str]
    confidence_assessment: Dict[str, Any]
    implementation_plan: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    domain_analyses: Dict[str, Any]
    processing_time: float
    intelligence_sources: List[str]
    error: Optional[str] = None

# Application state
app_state = {
    "active_tasks": {},
    "task_counter": 0,
    "startup_time": datetime.now(timezone.utc)
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting JARVIS API server", version="0.1.0")
    
    try:
        # Initialize Core Nexus connection
        bridge = await get_bridge()
        health = await bridge.health_check()
        logger.info("Core Nexus connection established", health=health["status"])
        
        # Initialize JARVIS supervisor
        supervisor = await get_supervisor()
        logger.info("JARVIS supervisor initialized")
        
    except Exception as e:
        logger.error("Failed to initialize JARVIS", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down JARVIS API server")

# Create FastAPI app
app = FastAPI(
    title="JARVIS - Core Nexus AI Agent API",
    description="Autonomous AI agent system built with LangGraph + Gemini AI + Core Nexus Memory",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Check Core Nexus health
        bridge = await get_bridge()
        core_nexus_status = await bridge.health_check()
        
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now(timezone.utc),
            jarvis_version="0.1.0",
            core_nexus_status=core_nexus_status,
            active_tasks=len(app_state["active_tasks"])
        )
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

@app.post("/tasks", response_model=TaskResponse)
async def process_task(request: TaskRequest, background_tasks: BackgroundTasks):
    """Process a task through JARVIS workflow"""
    try:
        # Generate task ID
        app_state["task_counter"] += 1
        task_id = f"jarvis-task-{app_state['task_counter']}-{int(datetime.now().timestamp())}"
        
        logger.info("Received task request", task_id=task_id, task=request.task[:100])
        
        # Add to active tasks
        app_state["active_tasks"][task_id] = {
            "task": request.task,
            "status": "processing",
            "start_time": datetime.now(timezone.utc)
        }
        
        # Process task
        supervisor = await get_supervisor()
        result = await supervisor.process_task(request.task, request.context)
        
        # Update task status
        app_state["active_tasks"][task_id]["status"] = "completed" if result["success"] else "failed"
        app_state["active_tasks"][task_id]["end_time"] = datetime.now(timezone.utc)
        
        # Clean up completed task (keep for a short time for debugging)
        background_tasks.add_task(cleanup_task, task_id, delay=300)  # 5 minutes
        
        return TaskResponse(
            task_id=task_id,
            success=result["success"],
            task=result["task"],
            final_decision=result.get("final_decision"),
            agent_outputs=result.get("agent_outputs", {}),
            learning_opportunities=result.get("learning_opportunities", []),
            improvement_suggestions=result.get("improvement_suggestions", []),
            iterations=result.get("iterations", 0),
            duration=result.get("duration", 0.0),
            error=result.get("error")
        )
        
    except Exception as e:
        logger.error("Task processing failed", error=str(e))
        
        # Update task status
        if task_id in app_state["active_tasks"]:
            app_state["active_tasks"][task_id]["status"] = "failed"
            app_state["active_tasks"][task_id]["error"] = str(e)
        
        raise HTTPException(status_code=500, detail=f"Task processing failed: {str(e)}")

@app.post("/chat", response_model=ChatResponse)
async def chat_with_jarvis(request: ChatRequest):
    """Direct chat with JARVIS agents"""
    try:
        logger.info("Chat request received", agent=request.agent, message=request.message[:100])
        
        # Get the appropriate agent
        supervisor = await get_supervisor()
        
        if request.agent == "supervisor":
            agent = supervisor.supervisor_agent
        elif request.agent == "analysis":
            agent = supervisor.analysis_agent
        elif request.agent == "planning":
            agent = supervisor.planning_agent
        else:
            raise HTTPException(status_code=400, detail=f"Unknown agent: {request.agent}")
        
        # Process the message
        result = await agent.process_with_memory_context(request.message)
        
        return ChatResponse(
            agent=request.agent,
            response=result.final_response,
            thinking=result.thinking_content,
            confidence=result.confidence_score,
            reasoning_steps=result.reasoning_steps,
            timestamp=datetime.now(timezone.utc)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Chat processing failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get the status of a specific task"""
    if task_id not in app_state["active_tasks"]:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return app_state["active_tasks"][task_id]

@app.get("/tasks")
async def list_tasks():
    """List all active and recent tasks"""
    return {
        "active_tasks": app_state["active_tasks"],
        "total_tasks_processed": app_state["task_counter"]
    }

@app.post("/memories", response_model=Dict[str, Any])
async def store_memory(request: MemoryRequest):
    """Store a memory in Core Nexus"""
    try:
        bridge = await get_bridge()
        
        from .core_nexus_bridge import JarvisMemory
        memory = JarvisMemory(
            content=request.content,
            importance_score=request.importance_score,
            metadata=request.metadata or {}
        )
        
        result = await bridge.store_memory(memory)
        return result
        
    except Exception as e:
        logger.error("Memory storage failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Memory storage failed: {str(e)}")

@app.post("/memories/search")
async def search_memories(request: MemorySearchRequest):
    """Search memories in Core Nexus"""
    try:
        bridge = await get_bridge()
        memories = await bridge.search_memories(request.query, request.limit)
        
        return {
            "query": request.query,
            "memories": memories,
            "count": len(memories)
        }
        
    except Exception as e:
        logger.error("Memory search failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Memory search failed: {str(e)}")

@app.get("/stats")
async def get_jarvis_stats():
    """Get JARVIS system statistics"""
    try:
        bridge = await get_bridge()
        core_nexus_stats = await bridge.get_stats()
        
        # Get JARVIS-specific memories
        jarvis_memories = await bridge.get_recent_jarvis_memories(limit=100)
        
        uptime = (datetime.now(timezone.utc) - app_state["startup_time"]).total_seconds()
        
        return {
            "jarvis_stats": {
                "uptime_seconds": uptime,
                "total_tasks_processed": app_state["task_counter"],
                "active_tasks": len(app_state["active_tasks"]),
                "jarvis_memories": len(jarvis_memories)
            },
            "core_nexus_stats": core_nexus_stats
        }
        
    except Exception as e:
        logger.error("Stats retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Stats retrieval failed: {str(e)}")

@app.get("/insights")
async def get_jarvis_insights():
    """Get recent JARVIS insights and learnings"""
    try:
        bridge = await get_bridge()
        
        # Get different types of JARVIS insights
        supervisor_insights = await bridge.search_memories("agent_type:supervisor", limit=10)
        analysis_insights = await bridge.search_memories("agent_type:analysis", limit=10)
        planning_insights = await bridge.search_memories("agent_type:planning", limit=10)
        learning_insights = await bridge.search_memories("agent_type:self_improvement", limit=10)
        
        return {
            "supervisor_insights": supervisor_insights,
            "analysis_insights": analysis_insights,
            "planning_insights": planning_insights,
            "learning_insights": learning_insights,
            "total_insights": len(supervisor_insights) + len(analysis_insights) + len(planning_insights) + len(learning_insights)
        }
        
    except Exception as e:
        logger.error("Insights retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Insights retrieval failed: {str(e)}")

@app.post("/strategic-intelligence", response_model=StrategicIntelligenceResponse)
async def process_strategic_intelligence(request: StrategicIntelligenceRequest, background_tasks: BackgroundTasks):
    """Process strategic intelligence analysis through JARVIS Strategic Intelligence Framework"""
    try:
        # Generate analysis ID
        app_state["task_counter"] += 1
        analysis_id = f"strategic-{app_state['task_counter']}-{int(datetime.now().timestamp())}"
        
        logger.info("Strategic intelligence request received", 
                   analysis_id=analysis_id, 
                   task=request.task[:100],
                   priority=request.priority)
        
        # Get JARVIS supervisor with Strategic Intelligence Processor
        supervisor = await get_supervisor()
        
        # Process through strategic intelligence node directly
        start_time = datetime.now(timezone.utc)
        
        # Create JARVIS state for strategic intelligence processing
        from .langgraph_supervisor import JarvisState
        strategic_state: JarvisState = {
            "messages": [],
            "current_task": request.task,
            "task_context": request.context or {},
            "next_agent": "strategic_intelligence",
            "completed_agents": [],
            "relevant_memories": [],
            "system_insights": [],
            "supervisor_decision": "",
            "agent_outputs": {},
            "iteration_count": 0,
            "start_time": start_time.isoformat(),
            "last_update": start_time.isoformat(),
            "learning_opportunities": [],
            "improvement_suggestions": []
        }
        
        # Process through strategic intelligence
        result = await supervisor._strategic_intelligence_node(strategic_state)
        
        # Calculate processing time
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        # Extract strategic intelligence result
        strategic_result = result.get("strategic_intelligence_result", {})
        
        # Store result for learning (background task)
        background_tasks.add_task(
            store_strategic_analysis_memory,
            analysis_id,
            request.task,
            strategic_result,
            processing_time
        )
        
        # Return structured strategic intelligence response
        return StrategicIntelligenceResponse(
            success=strategic_result.get("success", True),
            analysis_id=analysis_id,
            executive_summary=strategic_result.get("executive_summary", "Strategic analysis completed"),
            strategic_recommendations=strategic_result.get("strategic_recommendations", []),
            confidence_assessment=strategic_result.get("confidence_assessment", {}),
            implementation_plan=strategic_result.get("implementation_plan", {}),
            risk_assessment=strategic_result.get("risk_assessment", {}),
            domain_analyses=strategic_result.get("domain_analyses", {}),
            processing_time=processing_time,
            intelligence_sources=strategic_result.get("intelligence_sources", ["jarvis_strategic_intelligence"]),
            error=strategic_result.get("error")
        )
        
    except Exception as e:
        logger.error("Strategic intelligence processing failed", 
                    analysis_id=analysis_id if 'analysis_id' in locals() else "unknown", 
                    error=str(e))
        
        # Return error response
        return StrategicIntelligenceResponse(
            success=False,
            analysis_id=analysis_id if 'analysis_id' in locals() else f"error-{int(datetime.now().timestamp())}",
            executive_summary=f"Strategic intelligence analysis failed: {str(e)}",
            strategic_recommendations=["Retry analysis after resolving technical issues"],
            confidence_assessment={"overall_confidence": 0, "decision_recommendation": "DEFER"},
            implementation_plan={"immediate_actions": ["Technical issue resolution required"]},
            risk_assessment={"high_risks": ["Analysis system unavailable"]},
            domain_analyses={},
            processing_time=0.0,
            intelligence_sources=[],
            error=str(e)
        )

async def store_strategic_analysis_memory(analysis_id: str, task: str, result: dict, processing_time: float):
    """Store strategic analysis in memory for learning (background task)"""
    try:
        bridge = await get_bridge()
        
        from .core_nexus_bridge import JarvisMemory
        memory = JarvisMemory(
            content=f"""Strategic Intelligence Analysis Complete
            
Analysis ID: {analysis_id}
Task: {task}

Executive Summary:
{result.get('executive_summary', 'No summary available')}

Strategic Recommendations:
{'; '.join(result.get('strategic_recommendations', []))}

Confidence Assessment: {result.get('confidence_assessment', {})}
Processing Time: {processing_time:.2f}s
""",
            importance_score=0.9,  # High importance for strategic analysis
            metadata={
                "agent_type": "strategic_intelligence",
                "analysis_id": analysis_id,
                "task_type": "strategic_analysis",
                "processing_time": processing_time,
                "success": result.get("success", True),
                "confidence": result.get("confidence_assessment", {}).get("overall_confidence", 0),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        await bridge.store_memory(memory)
        logger.info("Strategic analysis stored in memory", analysis_id=analysis_id)
        
    except Exception as e:
        logger.error("Failed to store strategic analysis memory", 
                    analysis_id=analysis_id, error=str(e))

async def cleanup_task(task_id: str, delay: int = 0):
    """Clean up completed task from memory"""
    if delay > 0:
        await asyncio.sleep(delay)
    
    if task_id in app_state["active_tasks"]:
        del app_state["active_tasks"][task_id]
        logger.debug("Cleaned up task", task_id=task_id)

def main():
    """Main entry point for the JARVIS API server"""
    uvicorn.run(
        "jarvis.api:app",
        host=config.api_host,
        port=config.api_port,
        reload=config.debug_mode,
        log_level=config.log_level.lower()
    )

if __name__ == "__main__":
    main()