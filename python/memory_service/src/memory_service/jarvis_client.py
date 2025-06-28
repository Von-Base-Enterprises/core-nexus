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
        
        # Enhanced timeout configuration
        self.health_check_timeout = 5.0
        self.reasoning_timeout = config.jarvis.REASONING_TIMEOUT
        self.connection_timeout = 10.0
        self.read_timeout = max(self.reasoning_timeout * 1.5, 30.0)  # 1.5x reasoning timeout or 30s minimum
        
        # Fallback tracking
        self.consecutive_failures = 0
        self.last_success_time = time.time()
        self.degraded_mode = False
        
        # Create HTTP client with enhanced timeout and connection settings
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Core-Nexus-Memory-Service/1.0",
            "Connection": "keep-alive"
        }
        if config.jarvis.API_KEY:
            headers["Authorization"] = f"Bearer {config.jarvis.API_KEY}"
        
        # Enhanced timeout configuration with different timeouts for different operations
        timeout_config = httpx.Timeout(
            connect=self.connection_timeout,
            read=self.read_timeout,
            write=10.0,
            pool=5.0
        )
        
        # Connection limits to prevent resource exhaustion
        limits = httpx.Limits(
            max_keepalive_connections=10,
            max_connections=20,
            keepalive_expiry=60
        )
        
        self.client = httpx.AsyncClient(
            timeout=timeout_config,
            headers=headers,
            limits=limits
            # HTTP/2 disabled for compatibility - can be enabled with: pip install httpx[http2]
        )
        
        logger.info(f"JARVIS client initialized: url={self.base_url}, enabled={self.enabled}, connection_timeout={self.connection_timeout}, read_timeout={self.read_timeout}, reasoning_timeout={self.reasoning_timeout}")
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def health_check(self) -> bool:
        """Check if JARVIS service is healthy with enhanced error handling"""
        if not self.enabled:
            logger.debug("JARVIS service disabled - health check returning False")
            return False
        
        try:
            # Use separate timeout for health checks
            health_timeout = httpx.Timeout(
                connect=3.0,
                read=self.health_check_timeout,
                write=2.0,
                pool=1.0
            )
            
            start_time = time.time()
            response = await self.client.get(
                f"{self.base_url}/health", 
                timeout=health_timeout
            )
            
            response_time = time.time() - start_time
            is_healthy = response.status_code == 200
            
            if is_healthy:
                self.consecutive_failures = 0
                self.last_success_time = time.time()
                if self.degraded_mode:
                    logger.info("JARVIS service recovered - exiting degraded mode")
                    self.degraded_mode = False
                logger.debug(f"JARVIS health check successful: response_time={response_time:.2f}s")
            else:
                self._handle_failure("health_check", f"HTTP {response.status_code}")
                logger.warning(f"JARVIS health check failed: HTTP {response.status_code}, response_time={response_time:.2f}s")
            
            return is_healthy
            
        except httpx.TimeoutException as e:
            self._handle_failure("health_check", f"timeout after {self.health_check_timeout}s")
            logger.warning(f"JARVIS health check timed out: {e}")
            return False
        except httpx.ConnectError as e:
            self._handle_failure("health_check", f"connection error: {e}")
            logger.warning(f"JARVIS health check connection failed: {e}")
            return False
        except Exception as e:
            self._handle_failure("health_check", f"unexpected error: {e}")
            logger.warning(f"JARVIS health check failed with unexpected error: {e}")
            return False
    
    def _handle_failure(self, operation: str, error_detail: str):
        """Handle failure tracking and degraded mode activation"""
        self.consecutive_failures += 1
        
        # Activate degraded mode after 3 consecutive failures
        if self.consecutive_failures >= 3 and not self.degraded_mode:
            self.degraded_mode = True
            logger.warning(f"JARVIS entering degraded mode after {self.consecutive_failures} consecutive failures. Last error: {error_detail}")
        
        logger.debug(f"JARVIS {operation} failure {self.consecutive_failures}: {error_detail}")
    
    def get_service_status(self) -> dict:
        """Get detailed service status information"""
        current_time = time.time()
        time_since_last_success = current_time - self.last_success_time
        
        return {
            "enabled": self.enabled,
            "healthy": self.consecutive_failures == 0,
            "degraded_mode": self.degraded_mode,
            "consecutive_failures": self.consecutive_failures,
            "time_since_last_success_seconds": time_since_last_success,
            "base_url": self.base_url,
            "timeout_config": {
                "connection_timeout": self.connection_timeout,
                "read_timeout": self.read_timeout,
                "reasoning_timeout": self.reasoning_timeout,
                "health_check_timeout": self.health_check_timeout
            }
        }
    
    async def analyze_query_results(
        self, 
        query: str, 
        memories: List[MemoryResponse],
        additional_context: Optional[Dict[str, Any]] = None,
        use_retry: bool = True
    ) -> Optional[JarvisAnalysisResult]:
        """
        Send query and retrieved memories to JARVIS for reasoning analysis with enhanced error handling
        
        Args:
            query: The original user query
            memories: Retrieved memories from vector search
            additional_context: Additional context for analysis
            use_retry: Whether to use retry logic for failures
        
        Returns:
            JarvisAnalysisResult or None if analysis fails
        """
        if not self.enabled:
            logger.debug("JARVIS integration disabled, skipping analysis")
            return None
        
        # Check if in degraded mode and provide fallback
        if self.degraded_mode:
            logger.warning("JARVIS in degraded mode - providing fallback response")
            return self._create_fallback_analysis_result(query, memories, "Service in degraded mode")
        
        # Progressive timeout strategy based on memory count and query complexity
        timeout_multiplier = 1.0
        if len(memories) > 10:
            timeout_multiplier = 1.5
        elif len(query) > 500:  # Complex query
            timeout_multiplier = 1.3
        
        effective_timeout = min(self.reasoning_timeout * timeout_multiplier, 45.0)  # Cap at 45 seconds
        
        retry_count = 0
        max_retries = self.max_retries if use_retry else 1
        
        while retry_count < max_retries:
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
                    "timestamp": time.time(),
                    "retry_attempt": retry_count,
                    "timeout_seconds": effective_timeout
                }
                
                # Add additional context if provided
                if additional_context:
                    context.update(additional_context)
                
                # Create task for JARVIS with enhanced description
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
                
                Note: Analysis timeout is {effective_timeout}s - prioritize key insights if processing time is limited.
                """
                
                task_request = JarvisTaskRequest(
                    task=task_description.strip(),
                    context=context,
                    priority="high" if retry_count > 0 else config.jarvis.TASK_PRIORITY
                )
                
                logger.info(f"Sending query to JARVIS for analysis: query={query[:100]}, memory_count={len(memories)}, retry={retry_count}, timeout={effective_timeout}s")
                
                # Enhanced timeout configuration for reasoning
                reasoning_timeout = httpx.Timeout(
                    connect=self.connection_timeout,
                    read=effective_timeout,
                    write=10.0,
                    pool=5.0
                )
                
                # Call JARVIS /tasks endpoint
                response = await self.client.post(
                    f"{self.base_url}/tasks",
                    json=task_request.to_dict(),
                    timeout=reasoning_timeout
                )
                
                response.raise_for_status()
                result_data = response.json()
                
                analysis_time = time.time() - start_time
                
                # Success - reset failure tracking
                if result_data.get('success', False):
                    self.consecutive_failures = 0
                    self.last_success_time = time.time()
                    logger.info(f"JARVIS analysis completed successfully in {analysis_time:.2f}s, task_id={result_data.get('task_id', 'unknown')}, retry={retry_count}")
                    return JarvisAnalysisResult(result_data)
                else:
                    logger.warning(f"JARVIS analysis returned unsuccessful result: {result_data.get('error', 'Unknown error')}")
                    if retry_count < max_retries - 1:
                        retry_count += 1
                        await asyncio.sleep(min(2 ** retry_count, 5))  # Exponential backoff, max 5s
                        continue
                    else:
                        self._handle_failure("analysis", f"unsuccessful result: {result_data.get('error', 'Unknown error')}")
                        return self._create_fallback_analysis_result(query, memories, f"Analysis unsuccessful: {result_data.get('error', 'Unknown error')}")
                
            except httpx.TimeoutException as e:
                error_msg = f"timeout after {effective_timeout}s"
                logger.warning(f"JARVIS analysis timed out: {error_msg}, retry={retry_count}")
                
                if retry_count < max_retries - 1:
                    retry_count += 1
                    # Increase timeout for retry
                    effective_timeout = min(effective_timeout * 1.5, 60.0)
                    await asyncio.sleep(min(2 ** retry_count, 5))
                    continue
                else:
                    self._handle_failure("analysis", error_msg)
                    return self._create_fallback_analysis_result(query, memories, error_msg)
                    
            except httpx.HTTPStatusError as e:
                error_msg = f"HTTP {e.response.status_code} - {e.response.text[:200]}"
                logger.warning(f"JARVIS HTTP error: {error_msg}, retry={retry_count}")
                
                # Don't retry on client errors (4xx)
                if 400 <= e.response.status_code < 500:
                    self._handle_failure("analysis", error_msg)
                    return self._create_fallback_analysis_result(query, memories, error_msg)
                
                if retry_count < max_retries - 1:
                    retry_count += 1
                    await asyncio.sleep(min(2 ** retry_count, 5))
                    continue
                else:
                    self._handle_failure("analysis", error_msg)
                    return self._create_fallback_analysis_result(query, memories, error_msg)
                    
            except httpx.ConnectError as e:
                error_msg = f"connection error: {e}"
                logger.warning(f"JARVIS connection failed: {error_msg}, retry={retry_count}")
                
                if retry_count < max_retries - 1:
                    retry_count += 1
                    await asyncio.sleep(min(2 ** retry_count, 8))  # Longer delay for connection issues
                    continue
                else:
                    self._handle_failure("analysis", error_msg)
                    return self._create_fallback_analysis_result(query, memories, error_msg)
                    
            except Exception as e:
                error_msg = f"unexpected error: {e}"
                logger.error(f"JARVIS analysis failed: {error_msg}, retry={retry_count}")
                
                if retry_count < max_retries - 1:
                    retry_count += 1
                    await asyncio.sleep(min(2 ** retry_count, 5))
                    continue
                else:
                    self._handle_failure("analysis", error_msg)
                    return self._create_fallback_analysis_result(query, memories, error_msg)
        
        # Should not reach here, but provide fallback just in case
        return self._create_fallback_analysis_result(query, memories, "Maximum retries exceeded")
    
    def _create_fallback_analysis_result(self, query: str, memories: List[MemoryResponse], error_reason: str) -> JarvisAnalysisResult:
        """Create a fallback analysis result when JARVIS is unavailable"""
        
        # Create basic summary from available memories
        memory_summary = ""
        if memories:
            memory_summary = f"Based on {len(memories)} retrieved memories:\n"
            for i, memory in enumerate(memories[:3], 1):
                content_preview = memory.content[:150] + "..." if len(memory.content) > 150 else memory.content
                memory_summary += f"{i}. {content_preview}\n"
            
            if len(memories) > 3:
                memory_summary += f"... and {len(memories) - 3} additional memories.\n"
        else:
            memory_summary = "No memories were retrieved for this query."
        
        # Create fallback analysis
        fallback_analysis = f"""
        ## Fallback Analysis (JARVIS Unavailable)

        **Query**: {query}

        **Status**: JARVIS analysis service is temporarily unavailable ({error_reason})

        ### Available Information
        {memory_summary}

        ### Fallback Recommendations
        1. **Manual Review**: Examine the retrieved memories manually for immediate insights
        2. **Retry Later**: The JARVIS service may recover - consider retrying the analysis
        3. **Alternative Analysis**: Use the raw memory content for decision-making
        4. **Service Recovery**: Monitor service status for automatic recovery

        ### Confidence Assessment
        - **Analysis Quality**: LIMITED - Basic fallback only
        - **Recommendation**: Review memories manually and retry when service recovers
        - **Risk Level**: MEDIUM - Analysis capability reduced

        *This is a fallback response. Full AI analysis will be available when JARVIS service recovers.*
        """
        
        # Create fallback result that matches JarvisAnalysisResult structure
        fallback_data = {
            "success": False,
            "task_id": f"fallback_{int(time.time())}",
            "final_decision": {
                "decision": fallback_analysis.strip(),
                "confidence": 0.3,
                "fallback_mode": True
            },
            "agent_outputs": {
                "analysis": {
                    "analysis_result": memory_summary,
                    "fallback_reason": error_reason
                }
            },
            "learning_opportunities": [],
            "improvement_suggestions": ["Retry when JARVIS service is available"],
            "iterations": 0,
            "duration": 0.1,
            "error": f"JARVIS service unavailable: {error_reason}"
        }
        
        logger.info(f"Created fallback analysis result: query_preview={query[:50]}, memory_count={len(memories)}, reason={error_reason}")
        return JarvisAnalysisResult(fallback_data)
    
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