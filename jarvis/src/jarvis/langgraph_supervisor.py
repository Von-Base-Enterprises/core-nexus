"""
JARVIS LangGraph Supervisor Architecture
Multi-agent orchestration system using LangGraph with Gemini AI
"""

import asyncio
from typing import Dict, List, Any, Optional, Union, Literal, TypedDict, Annotated
from datetime import datetime, timezone
import operator
import structlog
from dataclasses import dataclass

from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

from .config import get_config
from .gemini_integration import GeminiAgent, create_supervisor_agent, create_analysis_agent, create_planning_agent
from .core_nexus_bridge import get_bridge, JarvisMemory

logger = structlog.get_logger(__name__)
config = get_config()

# Helper functions for datetime handling in JSON-serializable state
def now_iso() -> str:
    """Get current UTC timestamp as ISO string for JSON serialization"""
    return datetime.now(timezone.utc).isoformat()

def parse_iso_datetime(iso_string: str) -> datetime:
    """Parse ISO timestamp string back to datetime object"""
    return datetime.fromisoformat(iso_string.replace('Z', '+00:00'))

def calculate_duration(start_iso: str, end_iso: Optional[str] = None) -> float:
    """Calculate duration in seconds between ISO timestamp strings"""
    start_dt = parse_iso_datetime(start_iso)
    end_dt = datetime.now(timezone.utc) if end_iso is None else parse_iso_datetime(end_iso)
    return (end_dt - start_dt).total_seconds()

# State definition for JARVIS workflow
class JarvisState(TypedDict):
    """JARVIS workflow state"""
    # Message history
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Current task and context
    current_task: str
    task_context: Dict[str, Any]
    
    # Agent assignments
    next_agent: str
    completed_agents: List[str]
    
    # Memory and knowledge
    relevant_memories: List[Dict[str, Any]]
    system_insights: List[Dict[str, Any]]
    
    # Decision tracking
    supervisor_decision: str
    agent_outputs: Dict[str, Any]
    
    # Metadata (using ISO strings for JSON serialization)
    iteration_count: int
    start_time: str  # ISO timestamp string
    last_update: str  # ISO timestamp string
    
    # Self-improvement tracking
    learning_opportunities: List[str]
    improvement_suggestions: List[str]

@dataclass
class AgentResult:
    """Result from an agent execution"""
    agent_name: str
    success: bool
    output: Any
    confidence: float
    reasoning: List[str]
    next_suggestions: List[str]
    errors: List[str] = None

class JarvisSupervisor:
    """JARVIS Supervisor using LangGraph orchestration"""
    
    def __init__(self):
        self.logger = logger.bind(component="jarvis_supervisor")
        
        # Initialize agents
        self.supervisor_agent = create_supervisor_agent()
        self.analysis_agent = create_analysis_agent()
        self.planning_agent = create_planning_agent()
        
        # Agent mapping
        self.agents = {
            "supervisor": self.supervisor_agent,
            "analysis": self.analysis_agent,
            "planning": self.planning_agent,
        }
        
        # Initialize the workflow graph
        self.workflow = self._create_workflow()
        
        # Set up checkpointing for persistence (memory fallback)
        self.checkpointer = self._setup_checkpointer()
        
        # Compile the graph
        self.app = self.workflow.compile(checkpointer=self.checkpointer)
        
        self.logger.info("JARVIS Supervisor initialized", 
                        agents=list(self.agents.keys()))
    
    def _setup_checkpointer(self):
        """Set up checkpointer for state persistence"""
        try:
            # Try PostgreSQL first if available
            if config.database_url:
                from langgraph.checkpoint.postgres import PostgresCheckpointSaver
                return PostgresCheckpointSaver.from_conn_string(config.database_url)
        except Exception as e:
            self.logger.warning("PostgreSQL checkpointer unavailable, using memory", error=str(e))
        
        # Fallback to memory checkpointer
        try:
            from langgraph.checkpoint.memory import MemoryCheckpointSaver
            self.logger.info("Using memory checkpointer for state persistence")
            return MemoryCheckpointSaver()
        except ImportError:
            # No checkpointing available
            self.logger.info("No checkpointing available, running stateless")
            return None
    
    def _create_workflow(self) -> StateGraph:
        """Create the JARVIS workflow graph"""
        
        # Create the state graph
        workflow = StateGraph(JarvisState)
        
        # Add nodes
        workflow.add_node("supervisor", self._supervisor_node)
        workflow.add_node("analysis", self._analysis_node)
        workflow.add_node("planning", self._planning_node)
        workflow.add_node("memory_sync", self._memory_sync_node)
        workflow.add_node("decision_maker", self._decision_maker_node)
        workflow.add_node("self_improvement", self._self_improvement_node)
        
        # Define the workflow edges
        workflow.set_entry_point("supervisor")
        
        # Supervisor decides which agent to use
        workflow.add_conditional_edges(
            "supervisor",
            self._route_next_agent,
            {
                "analysis": "analysis",
                "planning": "planning", 
                "memory_sync": "memory_sync",
                "decision_maker": "decision_maker",
                "self_improvement": "self_improvement",
                "end": END
            }
        )
        
        # Analysis agent can go to planning or back to supervisor
        workflow.add_conditional_edges(
            "analysis",
            self._should_continue_analysis,
            {
                "planning": "planning",
                "supervisor": "supervisor",
                "end": END
            }
        )
        
        # Planning agent returns to supervisor for decision
        workflow.add_edge("planning", "supervisor")
        
        # Memory sync returns to supervisor
        workflow.add_edge("memory_sync", "supervisor")
        
        # Decision maker can trigger self-improvement or end
        workflow.add_conditional_edges(
            "decision_maker",
            self._should_self_improve,
            {
                "self_improvement": "self_improvement",
                "end": END
            }
        )
        
        # Self-improvement returns to supervisor for next iteration
        workflow.add_edge("self_improvement", "supervisor")
        
        return workflow
    
    async def _supervisor_node(self, state: JarvisState) -> Dict[str, Any]:
        """Supervisor node - central decision making"""
        try:
            self.logger.info("Supervisor node processing", 
                           task=state.get("current_task", "unknown"))
            
            # Get supervisor agent
            supervisor = self.agents["supervisor"]
            
            # Prepare context for supervisor
            context = f"""
            Current Task: {state.get('current_task', 'No task specified')}
            Completed Agents: {state.get('completed_agents', [])}
            Iteration: {state.get('iteration_count', 0)}
            Available Agents: {list(self.agents.keys())}
            
            Previous Agent Outputs:
            {state.get('agent_outputs', {})}
            
            System Insights:
            {state.get('system_insights', [])}
            """
            
            # Get supervisor decision
            result = await supervisor.process_with_memory_context(
                f"Based on the current state, what should be the next action? Context: {context}",
                f"supervisor decision {state.get('current_task', '')}"
            )
            
            # Update state with supervisor decision
            updates = {
                "supervisor_decision": result.final_response,
                "messages": [AIMessage(content=result.final_response, name="supervisor")],
                "last_update": now_iso(),
                "iteration_count": state.get("iteration_count", 0) + 1
            }
            
            # Store supervisor insights
            if result.confidence_score > 0.7:
                await self._store_supervisor_insight(result, state)
            
            self.logger.info("Supervisor decision made", 
                           decision=result.final_response[:100],
                           confidence=result.confidence_score)
            
            return updates
            
        except Exception as e:
            self.logger.error("Supervisor node failed", error=str(e))
            return {
                "supervisor_decision": f"Error in supervisor: {str(e)}",
                "next_agent": "end"
            }
    
    async def _analysis_node(self, state: JarvisState) -> Dict[str, Any]:
        """Analysis agent node - system analysis and monitoring"""
        try:
            self.logger.info("Analysis node processing")
            
            # Get analysis agent
            analysis_agent = self.agents["analysis"]
            
            # Get current system stats
            bridge = await get_bridge()
            system_stats = await bridge.get_stats()
            health_status = await bridge.health_check()
            
            # Prepare analysis context
            context = f"""
            Current System Statistics: {system_stats}
            Health Status: {health_status}
            Task Context: {state.get('task_context', {})}
            
            Please analyze the current system state and provide insights.
            """
            
            # Get analysis
            result = await analysis_agent.think_and_respond(
                f"Analyze system state: {context}"
            )
            
            # Update state
            analysis_output = {
                "analysis_result": result.final_response,
                "system_metrics": system_stats,
                "health_data": health_status,
                "confidence": result.confidence_score,
                "reasoning": result.reasoning_steps
            }
            
            updates = {
                "agent_outputs": {**state.get("agent_outputs", {}), "analysis": analysis_output},
                "system_insights": state.get("system_insights", []) + [analysis_output],
                "completed_agents": state.get("completed_agents", []) + ["analysis"],
                "messages": [AIMessage(content=result.final_response, name="analysis")],
                "last_update": now_iso()
            }
            
            # Store analysis insights
            await bridge.store_system_analysis(
                result.final_response,
                {"system_stats": system_stats, "health": health_status},
                result.confidence_score * 0.8  # Slightly lower importance for analysis
            )
            
            self.logger.info("Analysis completed", 
                           confidence=result.confidence_score)
            
            return updates
            
        except Exception as e:
            self.logger.error("Analysis node failed", error=str(e))
            return {
                "agent_outputs": {**state.get("agent_outputs", {}), "analysis": {"error": str(e)}},
                "completed_agents": state.get("completed_agents", []) + ["analysis"]
            }
    
    async def _planning_node(self, state: JarvisState) -> Dict[str, Any]:
        """Planning agent node - strategic planning and optimization"""
        try:
            self.logger.info("Planning node processing")
            
            # Get planning agent
            planning_agent = self.agents["planning"]
            
            # Get analysis results for context
            analysis_output = state.get("agent_outputs", {}).get("analysis", {})
            
            # Prepare planning context
            context = f"""
            Current Task: {state.get('current_task')}
            Analysis Results: {analysis_output}
            System Insights: {state.get('system_insights', [])}
            
            Based on the analysis, create a strategic plan for improvement.
            """
            
            # Get planning recommendations
            result = await planning_agent.process_with_memory_context(
                f"Create improvement plan: {context}",
                f"planning strategy {state.get('current_task', '')}"
            )
            
            # Update state
            planning_output = {
                "plan": result.final_response,
                "confidence": result.confidence_score,
                "reasoning": result.reasoning_steps,
                "next_steps": result.reasoning_steps[-3:] if len(result.reasoning_steps) > 3 else result.reasoning_steps
            }
            
            updates = {
                "agent_outputs": {**state.get("agent_outputs", {}), "planning": planning_output},
                "completed_agents": state.get("completed_agents", []) + ["planning"],
                "messages": [AIMessage(content=result.final_response, name="planning")],
                "improvement_suggestions": state.get("improvement_suggestions", []) + [result.final_response],
                "last_update": now_iso()
            }
            
            # Store planning insights
            bridge = await get_bridge()
            await bridge.store_jarvis_insight(
                f"Planning Strategy: {result.final_response}",
                result.confidence_score * 0.9,  # High importance for planning
                "planning",
                {"task": state.get("current_task"), "analysis_context": analysis_output}
            )
            
            self.logger.info("Planning completed", 
                           confidence=result.confidence_score)
            
            return updates
            
        except Exception as e:
            self.logger.error("Planning node failed", error=str(e))
            return {
                "agent_outputs": {**state.get("agent_outputs", {}), "planning": {"error": str(e)}},
                "completed_agents": state.get("completed_agents", []) + ["planning"]
            }
    
    async def _memory_sync_node(self, state: JarvisState) -> Dict[str, Any]:
        """Memory synchronization node - sync with Core Nexus"""
        try:
            self.logger.info("Memory sync node processing")
            
            bridge = await get_bridge()
            
            # Get relevant memories for current task
            task = state.get("current_task", "")
            relevant_memories = await bridge.get_contextual_memories(task, limit=5)
            
            # Get recent JARVIS memories
            recent_memories = await bridge.get_recent_jarvis_memories(limit=10)
            
            updates = {
                "relevant_memories": relevant_memories,
                "completed_agents": state.get("completed_agents", []) + ["memory_sync"],
                "messages": [SystemMessage(content=f"Synced {len(relevant_memories)} relevant memories")],
                "last_update": now_iso()
            }
            
            self.logger.info("Memory sync completed", 
                           relevant_count=len(relevant_memories),
                           recent_count=len(recent_memories))
            
            return updates
            
        except Exception as e:
            self.logger.error("Memory sync failed", error=str(e))
            return {
                "relevant_memories": [],
                "completed_agents": state.get("completed_agents", []) + ["memory_sync"]
            }
    
    async def _decision_maker_node(self, state: JarvisState) -> Dict[str, Any]:
        """Decision maker node - final decision synthesis"""
        try:
            self.logger.info("Decision maker node processing")
            
            # Synthesize all agent outputs
            agent_outputs = state.get("agent_outputs", {})
            supervisor_decision = state.get("supervisor_decision", "")
            
            # Create comprehensive decision
            decision_context = f"""
            Supervisor Decision: {supervisor_decision}
            Analysis Results: {agent_outputs.get('analysis', {})}
            Planning Results: {agent_outputs.get('planning', {})}
            Improvement Suggestions: {state.get('improvement_suggestions', [])}
            """
            
            # Use supervisor for final decision
            supervisor = self.agents["supervisor"]
            result = await supervisor.think_and_respond(
                f"Make final decision based on all available information: {decision_context}"
            )
            
            updates = {
                "agent_outputs": {**agent_outputs, "final_decision": {
                    "decision": result.final_response,
                    "confidence": result.confidence_score,
                    "reasoning": result.reasoning_steps
                }},
                "messages": [AIMessage(content=f"Final Decision: {result.final_response}", name="decision_maker")],
                "last_update": now_iso()
            }
            
            self.logger.info("Final decision made", 
                           confidence=result.confidence_score)
            
            return updates
            
        except Exception as e:
            self.logger.error("Decision maker failed", error=str(e))
            return {
                "agent_outputs": {**state.get("agent_outputs", {}), "final_decision": {"error": str(e)}}
            }
    
    async def _self_improvement_node(self, state: JarvisState) -> Dict[str, Any]:
        """Self-improvement node - learn and adapt"""
        try:
            self.logger.info("Self-improvement node processing")
            
            # Analyze the entire workflow for learning opportunities
            start_time_iso = state.get("start_time", now_iso())
            workflow_analysis = {
                "iteration_count": state.get("iteration_count", 0),
                "agents_used": state.get("completed_agents", []),
                "decisions_made": state.get("agent_outputs", {}),
                "task_completion": state.get("current_task", ""),
                "start_time": start_time_iso,
                "total_duration": calculate_duration(start_time_iso)
            }
            
            # Use supervisor to identify improvements
            supervisor = self.agents["supervisor"]
            result = await supervisor.think_and_respond(
                f"Analyze this workflow execution and identify learning opportunities: {workflow_analysis}"
            )
            
            # Store the learning
            bridge = await get_bridge()
            await bridge.store_jarvis_insight(
                f"Self-Improvement Analysis: {result.final_response}",
                0.9,  # High importance for self-improvement
                "self_improvement",
                {"workflow_analysis": workflow_analysis}
            )
            
            updates = {
                "learning_opportunities": state.get("learning_opportunities", []) + result.reasoning_steps,
                "messages": [AIMessage(content=f"Self-Improvement: {result.final_response}", name="self_improvement")],
                "last_update": now_iso()
            }
            
            self.logger.info("Self-improvement analysis completed")
            
            return updates
            
        except Exception as e:
            self.logger.error("Self-improvement failed", error=str(e))
            return {
                "learning_opportunities": state.get("learning_opportunities", []) + [f"Error in self-improvement: {str(e)}"]
            }
    
    def _route_next_agent(self, state: JarvisState) -> str:
        """Route to the next agent based on supervisor decision"""
        completed_agents = state.get("completed_agents", [])
        supervisor_decision = state.get("supervisor_decision", "").lower()
        iteration_count = state.get("iteration_count", 0)
        
        self.logger.info("Routing decision analysis",
                        iteration=iteration_count,
                        completed_agents=completed_agents,
                        supervisor_decision=supervisor_decision[:100],
                        max_iterations=config.max_iterations)
        
        # If we've done too many iterations, end
        if iteration_count > config.max_iterations:
            self.logger.warning("Max iterations exceeded, ending workflow",
                              iteration=iteration_count,
                              max_allowed=config.max_iterations)
            return "end"
        
        # Route based on what hasn't been done yet and supervisor decision
        if "analysis" not in completed_agents and ("analyze" in supervisor_decision or "analysis" in supervisor_decision):
            next_route = "analysis"
        elif "planning" not in completed_agents and ("plan" in supervisor_decision or "planning" in supervisor_decision):
            next_route = "planning"
        elif "memory" in supervisor_decision or "sync" in supervisor_decision:
            next_route = "memory_sync"
        elif len(completed_agents) >= 2:  # If we have enough information, make decision
            next_route = "decision_maker"
        else:
            next_route = "end"
        
        self.logger.info("Route decision made",
                        next_agent=next_route,
                        reasoning=f"Completed: {completed_agents}, Decision contains: {[word for word in ['analyze', 'analysis', 'plan', 'planning', 'memory', 'sync'] if word in supervisor_decision]}")
        
        return next_route
    
    def _should_continue_analysis(self, state: JarvisState) -> str:
        """Decide if analysis should continue to planning"""
        analysis_output = state.get("agent_outputs", {}).get("analysis", {})
        confidence = analysis_output.get("confidence", 0)
        
        next_step = "planning" if confidence > 0.7 else "supervisor"
        
        self.logger.info("Analysis continuation decision",
                        confidence=confidence,
                        threshold=0.7,
                        next_step=next_step)
        
        return next_step
    
    def _should_self_improve(self, state: JarvisState) -> str:
        """Decide if self-improvement should be triggered"""
        iteration_count = state.get("iteration_count", 0)
        
        if config.self_improvement_enabled:
            # Trigger self-improvement every few iterations
            should_improve = iteration_count > 0 and iteration_count % 3 == 0
            next_step = "self_improvement" if should_improve else "end"
        else:
            next_step = "end"
        
        self.logger.info("Self-improvement decision",
                        iteration=iteration_count,
                        self_improvement_enabled=config.self_improvement_enabled,
                        trigger_condition=f"iteration % 3 == 0",
                        next_step=next_step)
        
        return next_step
    
    async def _store_supervisor_insight(self, result, state: JarvisState):
        """Store supervisor insights in memory"""
        try:
            bridge = await get_bridge()
            await bridge.store_jarvis_insight(
                f"Supervisor Decision: {result.final_response}",
                result.confidence_score,
                "supervisor",
                {
                    "task": state.get("current_task"),
                    "iteration": state.get("iteration_count"),
                    "reasoning": result.reasoning_steps
                }
            )
        except Exception as e:
            self.logger.error("Failed to store supervisor insight", error=str(e))
    
    async def process_task(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a task through the JARVIS workflow"""
        try:
            self.logger.info("Processing task", task=task)
            
            # Initialize state
            current_time_iso = now_iso()
            initial_state = JarvisState(
                messages=[HumanMessage(content=task)],
                current_task=task,
                task_context=context or {},
                next_agent="supervisor",
                completed_agents=[],
                relevant_memories=[],
                system_insights=[],
                supervisor_decision="",
                agent_outputs={},
                iteration_count=0,
                start_time=current_time_iso,
                last_update=current_time_iso,
                learning_opportunities=[],
                improvement_suggestions=[]
            )
            
            # Execute the workflow
            config_dict = {"configurable": {"thread_id": f"jarvis-{datetime.now().isoformat()}"}}
            
            # Accumulate state from workflow stream
            accumulated_state = initial_state.copy()
            step_count = 0
            
            async for step in self.app.astream(initial_state, config_dict):
                step_count += 1
                
                # Each step is a dict with node_name: state_updates
                for node_name, state_updates in step.items():
                    current_iteration = state_updates.get("iteration_count", accumulated_state.get("iteration_count", 0))
                    
                    self.logger.info("Workflow step execution",
                                   step=step_count,
                                   node=node_name,
                                   iteration=current_iteration,
                                   updates=list(state_updates.keys()))
                    
                    # Merge state updates into accumulated state
                    for key, value in state_updates.items():
                        if key == "agent_outputs":
                            # Merge agent outputs
                            accumulated_state["agent_outputs"] = {
                                **accumulated_state.get("agent_outputs", {}),
                                **value
                            }
                        elif key == "completed_agents":
                            # Merge completed agents list
                            existing = accumulated_state.get("completed_agents", [])
                            new_agents = [a for a in value if a not in existing]
                            accumulated_state["completed_agents"] = existing + new_agents
                        elif key == "learning_opportunities":
                            # Merge learning opportunities
                            accumulated_state["learning_opportunities"] = accumulated_state.get("learning_opportunities", []) + value
                        elif key == "improvement_suggestions":
                            # Merge improvement suggestions
                            accumulated_state["improvement_suggestions"] = accumulated_state.get("improvement_suggestions", []) + value
                        elif key == "system_insights":
                            # Merge system insights
                            accumulated_state["system_insights"] = accumulated_state.get("system_insights", []) + value
                        elif key == "messages":
                            # Append new messages
                            accumulated_state["messages"] = accumulated_state.get("messages", []) + value
                        else:
                            # Direct update for other fields
                            accumulated_state[key] = value
            
            # Extract the final result from accumulated state
            if step_count > 0:
                result = {
                    "success": True,
                    "task": task,
                    "final_decision": accumulated_state.get("agent_outputs", {}).get("final_decision"),
                    "agent_outputs": accumulated_state.get("agent_outputs", {}),
                    "learning_opportunities": accumulated_state.get("learning_opportunities", []),
                    "improvement_suggestions": accumulated_state.get("improvement_suggestions", []),
                    "iterations": accumulated_state.get("iteration_count", 0),
                    "duration": calculate_duration(initial_state["start_time"])
                }
                
                self.logger.info("Workflow execution details",
                               steps_executed=step_count,
                               agents_completed=accumulated_state.get("completed_agents", []),
                               has_final_decision=bool(accumulated_state.get("agent_outputs", {}).get("final_decision")),
                               agent_outputs_keys=list(accumulated_state.get("agent_outputs", {}).keys()))
            else:
                result = {
                    "success": False,
                    "task": task,
                    "error": "No workflow steps executed"
                }
            
            self.logger.info("Task processing completed", 
                           task=task, 
                           success=result["success"], 
                           duration=result.get("duration", 0),
                           final_decision_present=bool(result.get("final_decision")))
            
            return result
            
        except Exception as e:
            self.logger.error("Task processing failed", task=task, error=str(e))
            return {
                "success": False,
                "task": task,
                "error": str(e)
            }

# Global supervisor instance
_supervisor_instance: Optional[JarvisSupervisor] = None

async def get_supervisor() -> JarvisSupervisor:
    """Get the global JARVIS supervisor instance"""
    global _supervisor_instance
    if _supervisor_instance is None:
        _supervisor_instance = JarvisSupervisor()
    return _supervisor_instance