"""
JARVIS AI Agent Integration Client

Provides HTTP client for calling JARVIS reasoning endpoints from the memory service.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import config
from .models import MemoryResponse

logger = logging.getLogger(__name__)


class JarvisTaskRequest:
    """Request model for JARVIS task processing"""
    
    def __init__(self, task: str, context: Optional[Dict[str, Any]] = None, priority: str = "medium"):
        self.task = task
        self.context = context or {}
        self.priority = priority
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "context": self.context,
            "priority": self.priority
        }


class JarvisAnalysisResult:
    """Result from JARVIS reasoning analysis"""
    
    def __init__(self, raw_response: Dict[str, Any]):
        self.raw_response = raw_response
        self.success = raw_response.get("success", False)
        self.task_id = raw_response.get("task_id", "")
        self.analysis = raw_response.get("final_decision", {})
        self.agent_outputs = raw_response.get("agent_outputs", {})
        self.learning_opportunities = raw_response.get("learning_opportunities", [])
        self.improvement_suggestions = raw_response.get("improvement_suggestions", [])
        self.iterations = raw_response.get("iterations", 0)
        self.duration = raw_response.get("duration", 0.0)
        self.error = raw_response.get("error")
    
    def get_summary(self) -> str:
        """Get a summary of the analysis"""
        if not self.success:
            return f"Analysis failed: {self.error}"
        
        # Extract key insights from different agents
        summary_parts = []
        
        if self.analysis and isinstance(self.analysis, dict):
            decision = self.analysis.get("decision", "")
            if decision:
                summary_parts.append(f"Decision: {decision}")
        
        # Add analysis insights
        analysis_output = self.agent_outputs.get("analysis", {})
        if analysis_output and isinstance(analysis_output, dict):
            analysis_result = analysis_output.get("analysis_result", "")
            if analysis_result:
                summary_parts.append(f"Analysis: {analysis_result}")
        
        # Add planning insights
        planning_output = self.agent_outputs.get("planning", {})
        if planning_output and isinstance(planning_output, dict):
            plan = planning_output.get("plan", "")
            if plan:
                summary_parts.append(f"Strategy: {plan}")
        
        return " | ".join(summary_parts) if summary_parts else "Analysis completed successfully"
    
    def get_structured_analysis(self) -> Dict[str, Any]:
        """Get structured analysis for API response"""
        return {
            "success": self.success,
            "task_id": self.task_id,
            "summary": self.get_summary(),
            "decision": self.analysis,
            "agent_outputs": self.agent_outputs,
            "performance": {
                "iterations": self.iterations,
                "duration_seconds": self.duration,
                "learning_opportunities": len(self.learning_opportunities),
                "improvement_suggestions": len(self.improvement_suggestions)
            },
            "error": self.error
        }


class JarvisClient:
    """HTTP client for JARVIS AI agent integration"""
    
    def __init__(self):
        self.base_url = config.jarvis.URL.rstrip('/')
        self.timeout = config.jarvis.TIMEOUT
        self.max_retries = config.jarvis.MAX_RETRIES
        self.enabled = config.jarvis.ENABLED
        
        # Create HTTP client with timeout and auth if configured
        headers = {"Content-Type": "application/json"}
        if config.jarvis.API_KEY:
            headers["Authorization"] = f"Bearer {config.jarvis.API_KEY}"
        
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            headers=headers
        )
        
        logger.info(f"JARVIS client initialized", 
                   url=self.base_url, 
                   enabled=self.enabled,
                   timeout=self.timeout)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def health_check(self) -> bool:
        """Check if JARVIS service is healthy"""
        if not self.enabled:
            return False
        
        try:
            response = await self.client.get(f"{self.base_url}/health", timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"JARVIS health check failed: {e}")
            return False
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def analyze_query_results(
        self, 
        query: str, 
        memories: List[MemoryResponse],
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Optional[JarvisAnalysisResult]:
        """
        Send query and retrieved memories to JARVIS for reasoning analysis
        
        Args:
            query: The original user query
            memories: Retrieved memories from vector search
            additional_context: Additional context for analysis
        
        Returns:
            JarvisAnalysisResult or None if analysis fails
        """
        if not self.enabled:
            logger.debug("JARVIS integration disabled, skipping analysis")
            return None
        
        try:
            start_time = time.time()
            
            # Prepare context for JARVIS
            context = {
                "original_query": query,
                "retrieved_memories": [
                    {
                        "id": str(memory.id),
                        "content": memory.content,
                        "importance_score": memory.importance_score,
                        "similarity_score": memory.similarity_score,
                        "metadata": memory.metadata,
                        "created_at": memory.created_at.isoformat() if memory.created_at else None
                    }
                    for memory in memories[:config.jarvis.MAX_CONTEXT_MEMORIES]  # Limit context size
                ],
                "memory_count": len(memories),
                "analysis_type": "query_reasoning",
                "timestamp": time.time()
            }
            
            # Add additional context if provided
            if additional_context:
                context.update(additional_context)
            
            # Create task for JARVIS
            task_description = f"""
            Analyze the following query and retrieved memories to provide intelligent insights:
            
            Query: {query}
            
            Retrieved {len(memories)} relevant memories from the knowledge base.
            
            Please provide:
            1. Analysis of the query intent and context
            2. Key insights from the retrieved memories
            3. Strategic recommendations or next steps
            4. Any patterns or connections identified
            
            Focus on providing actionable intelligence rather than just summarizing the memories.
            """
            
            task_request = JarvisTaskRequest(
                task=task_description.strip(),
                context=context,
                priority=config.jarvis.TASK_PRIORITY
            )
            
            logger.info(f"Sending query to JARVIS for analysis", 
                       query=query[:100], 
                       memory_count=len(memories))
            
            # Call JARVIS /tasks endpoint
            response = await self.client.post(
                f"{self.base_url}/tasks",
                json=task_request.to_dict(),
                timeout=config.jarvis.REASONING_TIMEOUT
            )
            
            response.raise_for_status()
            result_data = response.json()
            
            analysis_time = time.time() - start_time
            logger.info(f"JARVIS analysis completed in {analysis_time:.2f}s",
                       task_id=result_data.get("task_id", "unknown"),
                       success=result_data.get("success", False))
            
            return JarvisAnalysisResult(result_data)
            
        except httpx.TimeoutException:
            logger.error(f"JARVIS analysis timed out after {config.jarvis.REASONING_TIMEOUT}s")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"JARVIS HTTP error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"JARVIS analysis failed: {e}")
            return None
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Global client instance
_jarvis_client: Optional[JarvisClient] = None


async def get_jarvis_client() -> JarvisClient:
    """Get the global JARVIS client instance"""
    global _jarvis_client
    if _jarvis_client is None:
        _jarvis_client = JarvisClient()
    return _jarvis_client


async def cleanup_jarvis_client():
    """Cleanup the global JARVIS client"""
    global _jarvis_client
    if _jarvis_client is not None:
        await _jarvis_client.close()
        _jarvis_client = None