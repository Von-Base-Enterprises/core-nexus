#!/usr/bin/env python3
"""
Jarvis: Conversational AI Agent for Core Nexus
Uses Google ADK for state-of-the-art conversational AI with memory integration.

This agent provides:
- Natural conversational interface to Core Nexus memories
- Session management with conversation history
- Intelligent memory retrieval and context building
- Memory creation from conversations
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import uuid4
import logging

# Google ADK imports
from google import genai
from google.genai import types
from google.genai.chats import ChatSession
from google.genai.errors import GenAIError

# Add the source directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from memory_service.unified_store import UnifiedMemoryStore
from memory_service.models import MemoryInput, QueryRequest
from memory_service.logging_config import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger("jarvis_agent")

# Configure Google ADK
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyAIl8F81WwFfx5_62y19KuO12ermaDC6FQ")

# Initialize the client
client = genai.Client(api_key=GEMINI_API_KEY)

# Jarvis system prompt
JARVIS_SYSTEM_PROMPT = """You are Jarvis, an intelligent AI assistant powered by Core Nexus.

Your capabilities include:
- Accessing and searching through the Core Nexus memory system
- Understanding context from previous conversations
- Creating new memories from important information in conversations
- Providing intelligent responses based on stored knowledge
- Learning and adapting from user interactions

Key behaviors:
1. When asked about past information, search the memory system
2. Identify important information in conversations and suggest storing it
3. Maintain conversation continuity using session history
4. Be helpful, concise, and accurate
5. Acknowledge when you don't have information rather than making it up

You have access to these functions:
- search_memories: Search for relevant memories in Core Nexus
- create_memory: Store important information as a new memory
- get_conversation_history: Retrieve past conversation context
"""

# Function declarations for Jarvis
JARVIS_FUNCTIONS = [
    {
        "name": "search_memories",
        "description": "Search Core Nexus memories for relevant information",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to find relevant memories"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of memories to return",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "create_memory",
        "description": "Create a new memory in Core Nexus from important information",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The content to store as a memory"
                },
                "importance": {
                    "type": "number",
                    "description": "Importance score from 0.0 to 1.0",
                    "default": 0.7
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags to categorize the memory"
                }
            },
            "required": ["content"]
        }
    },
    {
        "name": "get_conversation_history",
        "description": "Retrieve conversation history for context",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of recent messages to retrieve",
                    "default": 10
                }
            }
        }
    }
]


class JarvisAgent:
    """Jarvis conversational AI agent using Google ADK."""
    
    def __init__(self):
        self.client = client
        self.memory_store: Optional[UnifiedMemoryStore] = None
        self.session_id = str(uuid4())
        self.conversation_id = str(uuid4())
        self.user_id = "jarvis_user"  # Default user, can be customized
        self.chat_session: Optional[ChatSession] = None
        self.conversation_history: List[Dict[str, Any]] = []
        
    async def initialize(self):
        """Initialize the agent with memory store connection."""
        # Initialize memory store
        self.memory_store = UnifiedMemoryStore()
        await self.memory_store.initialize()
        
        # Create chat session with Gemini
        try:
            # Configure the model with functions
            model_config = types.GenerateContentConfig(
                temperature=0.7,
                top_p=0.9,
                max_output_tokens=2048,
                response_mime_type="text/plain",
                system_instruction=JARVIS_SYSTEM_PROMPT,
                tools=[types.Tool(function_declarations=JARVIS_FUNCTIONS)]
            )
            
            # Start chat session
            self.chat_session = self.client.models.generate_content(
                model="gemini-2.0-flash-latest",
                config=model_config
            )
            
            logger.info(f"✅ Jarvis initialized with session {self.session_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Jarvis: {e}")
            raise
    
    async def search_memories(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search Core Nexus memories."""
        try:
            # Create query request
            query_request = QueryRequest(
                query_text=query,
                limit=limit,
                conversation_id=self.conversation_id,
                user_id=self.user_id,
                min_similarity=0.7
            )
            
            # Search memories
            result = await self.memory_store.query_memories(query_request)
            
            # Format results
            memories = []
            for memory in result.memories:
                memories.append({
                    "id": str(memory.id),
                    "content": memory.content,
                    "similarity": memory.similarity_score,
                    "created_at": memory.created_at.isoformat() if memory.created_at else None,
                    "importance": memory.importance_score
                })
            
            logger.info(f"🔍 Found {len(memories)} memories for query: {query}")
            return memories
            
        except Exception as e:
            logger.error(f"❌ Memory search failed: {e}")
            return []
    
    async def create_memory(self, content: str, importance: float = 0.7, tags: List[str] = None) -> str:
        """Create a new memory in Core Nexus."""
        try:
            # Create memory input
            memory_input = MemoryInput(
                content=content,
                user_id=self.user_id,
                conversation_id=self.conversation_id,
                importance_score=importance,
                metadata={
                    "source": "jarvis_conversation",
                    "session_id": self.session_id,
                    "tags": tags or [],
                    "created_by": "jarvis_agent"
                }
            )
            
            # Store memory
            memory = await self.memory_store.add_memory(memory_input)
            
            logger.info(f"💾 Created memory: {memory.id}")
            return str(memory.id)
            
        except Exception as e:
            logger.error(f"❌ Memory creation failed: {e}")
            return ""
    
    async def get_conversation_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent conversation history."""
        # Return recent messages from local history
        return self.conversation_history[-limit:]
    
    async def handle_function_call(self, function_call: Dict[str, Any]) -> Any:
        """Handle function calls from Gemini."""
        function_name = function_call.get("name")
        args = function_call.get("args", {})
        
        logger.info(f"🔧 Executing function: {function_name} with args: {args}")
        
        if function_name == "search_memories":
            return await self.search_memories(
                query=args.get("query", ""),
                limit=args.get("limit", 5)
            )
        elif function_name == "create_memory":
            return await self.create_memory(
                content=args.get("content", ""),
                importance=args.get("importance", 0.7),
                tags=args.get("tags", [])
            )
        elif function_name == "get_conversation_history":
            return await self.get_conversation_history(
                limit=args.get("limit", 10)
            )
        else:
            logger.warning(f"Unknown function: {function_name}")
            return None
    
    async def chat(self, user_input: str) -> str:
        """Process user input and generate response."""
        try:
            # Add to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": user_input,
                "timestamp": datetime.now().isoformat()
            })
            
            # Generate response using Gemini
            response = await self.client.models.generate_content_async(
                model="gemini-2.0-flash-latest",
                contents=user_input,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    top_p=0.9,
                    max_output_tokens=2048,
                    system_instruction=JARVIS_SYSTEM_PROMPT,
                    tools=[types.Tool(function_declarations=JARVIS_FUNCTIONS)]
                )
            )
            
            # Check for function calls
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate.content, 'parts'):
                    for part in candidate.content.parts:
                        if hasattr(part, 'function_call'):
                            # Execute function
                            result = await self.handle_function_call(part.function_call)
                            
                            # Generate final response with function result
                            final_response = await self.client.models.generate_content_async(
                                model="gemini-2.0-flash-latest",
                                contents=[
                                    user_input,
                                    f"Function result: {json.dumps(result)}"
                                ],
                                config=types.GenerateContentConfig(
                                    temperature=0.7,
                                    system_instruction=JARVIS_SYSTEM_PROMPT
                                )
                            )
                            response = final_response
            
            # Extract text response
            response_text = response.text if hasattr(response, 'text') else str(response)
            
            # Add to conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": response_text,
                "timestamp": datetime.now().isoformat()
            })
            
            # Store conversation turn as memory if it contains important information
            if len(user_input) > 50 or "remember" in user_input.lower():
                await self.create_memory(
                    content=f"User: {user_input}\nJarvis: {response_text}",
                    importance=0.6,
                    tags=["conversation", "jarvis_chat"]
                )
            
            return response_text
            
        except Exception as e:
            logger.error(f"❌ Chat error: {e}")
            return f"I apologize, but I encountered an error: {str(e)}"
    
    async def close(self):
        """Clean up resources."""
        if self.memory_store:
            await self.memory_store.close()


# Interactive CLI for testing Jarvis
async def interactive_cli():
    """Run Jarvis in interactive CLI mode."""
    print("=" * 70)
    print("🤖 JARVIS - Core Nexus Conversational AI")
    print("Powered by Google ADK + Core Nexus Memory System")
    print("=" * 70)
    print("Type 'quit' or 'exit' to end the conversation")
    print("Type 'help' for available commands")
    print("-" * 70)
    
    jarvis = JarvisAgent()
    
    try:
        # Initialize Jarvis
        print("🔄 Initializing Jarvis...")
        await jarvis.initialize()
        print("✅ Jarvis is ready!\n")
        
        # Interactive loop
        while True:
            try:
                # Get user input
                user_input = input("\n👤 You: ").strip()
                
                # Check for exit commands
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("\n🤖 Jarvis: Goodbye! It was a pleasure assisting you.")
                    break
                
                # Check for help command
                if user_input.lower() == 'help':
                    print("\n🤖 Jarvis: Available commands:")
                    print("  - Ask me anything about stored memories")
                    print("  - Tell me to 'remember' something important")
                    print("  - Ask about our conversation history")
                    print("  - Type 'quit' or 'exit' to end")
                    continue
                
                # Process with Jarvis
                print("\n🤖 Jarvis: ", end="", flush=True)
                response = await jarvis.chat(user_input)
                print(response)
                
            except KeyboardInterrupt:
                print("\n\n🤖 Jarvis: Conversation interrupted. Type 'quit' to exit properly.")
                
            except Exception as e:
                print(f"\n❌ Error: {e}")
                logger.error(f"CLI error: {e}")
    
    finally:
        # Clean up
        await jarvis.close()
        print("\n✅ Jarvis session ended.")


# API endpoint integration for FastAPI
from fastapi import HTTPException
from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = "default_user"
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    session_id: str

# Global Jarvis instance for API
_jarvis_instance: Optional[JarvisAgent] = None

async def get_jarvis_instance() -> JarvisAgent:
    """Get or create Jarvis instance."""
    global _jarvis_instance
    if _jarvis_instance is None:
        _jarvis_instance = JarvisAgent()
        await _jarvis_instance.initialize()
    return _jarvis_instance

async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """FastAPI endpoint for Jarvis chat."""
    try:
        jarvis = await get_jarvis_instance()
        
        # Set user and conversation context
        if request.user_id:
            jarvis.user_id = request.user_id
        if request.conversation_id:
            jarvis.conversation_id = request.conversation_id
        
        # Get response
        response = await jarvis.chat(request.message)
        
        return ChatResponse(
            response=response,
            conversation_id=jarvis.conversation_id,
            session_id=jarvis.session_id
        )
        
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # Run interactive CLI
    asyncio.run(interactive_cli())