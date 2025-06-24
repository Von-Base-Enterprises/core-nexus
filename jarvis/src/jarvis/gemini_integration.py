"""
Gemini AI Integration for JARVIS
Advanced AI capabilities with thinking, reasoning, and function calling
"""

import asyncio
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from typing import Dict, List, Any, Optional, Union, Callable
import json
import structlog
from datetime import datetime, timezone
from dataclasses import dataclass
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import get_config
from .core_nexus_bridge import get_bridge, JarvisMemory

logger = structlog.get_logger(__name__)
config = get_config()

@dataclass
class ThinkingResult:
    """Result from Gemini's thinking process"""
    thinking_content: str
    final_response: str
    function_calls: List[Dict[str, Any]]
    confidence_score: float
    reasoning_steps: List[str]

class GeminiAgent:
    """Gemini AI Agent with thinking capabilities and Core Nexus integration"""
    
    def __init__(self, agent_name: str = "JARVIS-Supervisor", system_prompt: Optional[str] = None):
        self.agent_name = agent_name
        self.logger = logger.bind(agent=agent_name)
        
        # Configure Gemini
        genai.configure(api_key=config.gemini_api_key)
        
        # Initialize the model with enhanced capabilities
        self.model = genai.GenerativeModel(
            model_name=config.gemini_model,
            system_instruction=system_prompt or self._get_default_system_prompt(),
            safety_settings={
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        )
        
        # Function registry for tool calling
        self.functions: Dict[str, Callable] = {}
        self._register_core_functions()
        
        # Conversation history
        self.chat_history: List[Dict[str, Any]] = []
    
    def _get_default_system_prompt(self) -> str:
        """Get the default JARVIS system prompt"""
        return f"""
You are JARVIS, an advanced AI agent designed to optimize and improve systems autonomously.

CORE IDENTITY:
- Agent Name: {self.agent_name}
- Purpose: Autonomous system optimization and self-improvement
- Architecture: LangGraph + Gemini AI + Core Nexus Memory Service
- Capabilities: Analysis, planning, execution, learning, and adaptation

THINKING PROCESS:
- Use deep reasoning to analyze complex problems step-by-step
- Break down decisions into clear reasoning steps
- Consider multiple approaches before selecting the best solution
- Evaluate potential consequences and risks

MEMORY INTEGRATION:
- You have access to Core Nexus Memory Service for persistent storage
- Store important insights, learnings, and system knowledge
- Retrieve relevant context from previous experiences
- Build upon accumulated knowledge over time

CORE FUNCTIONS:
- store_memory: Save important information to Core Nexus
- search_memories: Find relevant past experiences and knowledge
- analyze_system_state: Evaluate current system performance
- plan_improvements: Develop optimization strategies

BEHAVIOR GUIDELINES:
1. Always think through problems step-by-step
2. Store valuable insights in memory for future reference
3. Search memory for relevant context before making decisions
4. Prioritize system stability and reliability
5. Learn from successes and failures
6. Continuously improve your decision-making process

RESPONSE FORMAT:
- Provide clear, actionable responses
- Explain your reasoning process
- Include confidence scores for your decisions
- Suggest next steps or follow-up actions

Current timestamp: {datetime.now(timezone.utc).isoformat()}
"""
    
    def _register_core_functions(self):
        """Register core JARVIS functions for tool calling"""
        
        async def store_memory_func(content: str, importance_score: float, metadata: Dict[str, Any] = None):
            """Store information in Core Nexus memory"""
            if metadata is None:
                metadata = {}
            
            metadata.update({
                "agent": self.agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            bridge = await get_bridge()
            memory = JarvisMemory(
                content=content,
                importance_score=importance_score,
                metadata=metadata
            )
            
            result = await bridge.store_memory(memory)
            self.logger.info("Stored memory via function call", memory_id=result.get("id"))
            return result
        
        async def search_memories_func(query: str, limit: int = 5):
            """Search Core Nexus memories for relevant information"""
            bridge = await get_bridge()
            memories = await bridge.search_memories(query, limit)
            self.logger.info("Searched memories via function call", query=query, count=len(memories))
            return memories
        
        async def get_system_stats_func():
            """Get current Core Nexus system statistics"""
            bridge = await get_bridge()
            stats = await bridge.get_stats()
            self.logger.info("Retrieved system stats via function call")
            return stats
        
        self.functions = {
            "store_memory": store_memory_func,
            "search_memories": search_memories_func,
            "get_system_stats": get_system_stats_func
        }
    
    def register_function(self, name: str, func: Callable):
        """Register a custom function for tool calling"""
        self.functions[name] = func
        self.logger.info("Registered custom function", function_name=name)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def think_and_respond(self, user_input: str, context: Optional[str] = None) -> ThinkingResult:
        """Process input with thinking capabilities and return structured result"""
        try:
            # Prepare the prompt with context
            full_prompt = user_input
            if context:
                full_prompt = f"Context: {context}\n\nUser Input: {user_input}"
            
            # Add conversation history context
            if self.chat_history:
                recent_history = self.chat_history[-3:]  # Last 3 exchanges
                history_context = "\n".join([
                    f"Previous: {h['user']} -> {h['assistant'][:100]}..."
                    for h in recent_history
                ])
                full_prompt = f"Recent History:\n{history_context}\n\n{full_prompt}"
            
            self.logger.info("Processing input with AI reasoning", 
                           agent=self.agent_name, 
                           input_preview=user_input[:100])
            
            # Generate response
            response = await asyncio.to_thread(
                self.model.generate_content,
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    top_p=0.8,
                    max_output_tokens=4096,
                    response_mime_type="text/plain"
                )
            )
            
            # Parse the response
            response_text = response.text if response.text else ""
            thinking_content = ""
            final_response = response_text
            
            # Extract thinking content if present
            if "<thinking>" in response_text and "</thinking>" in response_text:
                thinking_start = response_text.find("<thinking>") + len("<thinking>")
                thinking_end = response_text.find("</thinking>")
                thinking_content = response_text[thinking_start:thinking_end].strip()
                final_response = response_text[thinking_end + len("</thinking>"):].strip()
            
            # Process any function calls
            function_calls = []
            if hasattr(response, 'candidates') and response.candidates:
                for candidate in response.candidates:
                    if hasattr(candidate, 'content') and candidate.content and hasattr(candidate.content, 'parts') and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, 'function_call') and part.function_call:
                                function_calls.append({
                                    "name": part.function_call.name,
                                    "args": dict(part.function_call.args) if part.function_call.args else {}
                                })
            
            # Calculate confidence score based on response quality
            confidence_score = self._calculate_confidence(response_text, thinking_content)
            
            # Extract reasoning steps
            reasoning_steps = self._extract_reasoning_steps(thinking_content or response_text)
            
            # Store conversation in history
            self.chat_history.append({
                "user": user_input,
                "assistant": final_response,
                "thinking": thinking_content,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            # Keep history manageable
            if len(self.chat_history) > 10:
                self.chat_history = self.chat_history[-10:]
            
            result = ThinkingResult(
                thinking_content=thinking_content,
                final_response=final_response,
                function_calls=function_calls,
                confidence_score=confidence_score,
                reasoning_steps=reasoning_steps
            )
            
            self.logger.info("Generated AI response", 
                           agent=self.agent_name,
                           confidence=confidence_score,
                           thinking_length=len(thinking_content),
                           response_length=len(final_response))
            
            return result
            
        except Exception as e:
            self.logger.error("Failed to generate AI response", 
                            agent=self.agent_name, error=str(e))
            raise
    
    def _calculate_confidence(self, response: str, thinking: str) -> float:
        """Calculate confidence score based on response characteristics"""
        confidence = 0.5  # Base confidence
        
        # Higher confidence for longer thinking processes
        if len(thinking) > 200:
            confidence += 0.2
        
        # Higher confidence for structured responses
        if any(marker in response for marker in ["1.", "2.", "3.", "•", "-"]):
            confidence += 0.1
        
        # Higher confidence for specific terms indicating certainty
        certainty_terms = ["definitely", "clearly", "obviously", "certainly"]
        if any(term in response.lower() for term in certainty_terms):
            confidence += 0.1
        
        # Lower confidence for uncertainty terms
        uncertainty_terms = ["maybe", "perhaps", "might", "possibly", "unsure"]
        if any(term in response.lower() for term in uncertainty_terms):
            confidence -= 0.1
        
        return max(0.1, min(1.0, confidence))
    
    def _extract_reasoning_steps(self, content: str) -> List[str]:
        """Extract reasoning steps from content"""
        if not content:
            return []
        
        steps = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for numbered steps, bullet points, or clear reasoning indicators
            if (line.startswith(('1.', '2.', '3.', '4.', '5.')) or
                line.startswith(('•', '-', '*')) or
                any(indicator in line.lower() for indicator in ['first', 'second', 'then', 'next', 'finally'])):
                steps.append(line)
        
        return steps[:10]  # Limit to 10 steps
    
    async def process_with_memory_context(self, user_input: str, 
                                        memory_query: Optional[str] = None) -> ThinkingResult:
        """Process input with relevant memory context"""
        try:
            # Get relevant memories for context
            bridge = await get_bridge()
            
            if memory_query:
                memories = await bridge.search_memories(memory_query, limit=3)
            else:
                # Use the user input as the memory query
                memories = await bridge.search_memories(user_input[:100], limit=3)
            
            # Build context from memories
            context = ""
            if memories and isinstance(memories, list):
                context = "Relevant past experiences and knowledge:\n"
                for i, memory in enumerate(memories, 1):
                    if memory and isinstance(memory, dict) and 'content' in memory:
                        context += f"{i}. {memory['content'][:200]}...\n"
                context += "\n"
            
            # Process with context
            return await self.think_and_respond(user_input, context)
            
        except Exception as e:
            self.logger.error("Failed to process with memory context", error=str(e))
            # Fallback to processing without context
            return await self.think_and_respond(user_input)

# Agent factory functions
def create_supervisor_agent() -> GeminiAgent:
    """Create the main JARVIS supervisor agent"""
    system_prompt = """
You are the JARVIS Supervisor Agent, the central intelligence coordinating all system operations.

RESPONSIBILITIES:
- Coordinate other specialized agents (Memory, Analysis, Planning, Execution)
- Make high-level strategic decisions
- Monitor overall system health and performance
- Plan system improvements and optimizations
- Learn from experiences and adapt strategies

DECISION-MAKING PROCESS:
1. Analyze the current situation using available data
2. Search memory for relevant past experiences
3. Consider multiple approaches and their trade-offs
4. Select the best approach based on system goals
5. Coordinate with specialized agents as needed
6. Monitor results and store learnings

Always prioritize system stability and user value.
"""
    
    return GeminiAgent("JARVIS-Supervisor", system_prompt)

def create_analysis_agent() -> GeminiAgent:
    """Create a specialized analysis agent"""
    system_prompt = """
You are the JARVIS Analysis Agent, specialized in system performance analysis and monitoring.

RESPONSIBILITIES:
- Analyze system metrics and performance data
- Identify patterns, trends, and anomalies
- Evaluate system health and capacity
- Generate insights about system behavior
- Recommend optimizations based on data

Focus on data-driven analysis and actionable insights.
"""
    
    return GeminiAgent("JARVIS-Analysis", system_prompt)

def create_planning_agent() -> GeminiAgent:
    """Create a specialized planning agent"""
    system_prompt = """
You are the JARVIS Planning Agent, specialized in strategic planning and optimization.

RESPONSIBILITIES:
- Develop improvement strategies and implementation plans
- Break down complex goals into actionable steps
- Optimize resource allocation and scheduling
- Plan system upgrades and migrations
- Design contingency plans for potential issues

Focus on strategic thinking and systematic planning.
"""
    
    return GeminiAgent("JARVIS-Planning", system_prompt)