#!/usr/bin/env python3
"""
Standalone Jarvis for testing without Core Nexus dependencies
"""

import asyncio
import os
from datetime import datetime
from typing import List, Dict, Any
import google.generativeai as genai

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyAIl8F81WwFfx5_62y19KuO12ermaDC6FQ")
genai.configure(api_key=GEMINI_API_KEY)

JARVIS_PROMPT = """You are Jarvis, an intelligent AI assistant powered by Core Nexus.

Core Nexus is an advanced memory and knowledge management system that:
- Stores memories with vector embeddings for semantic search
- Uses pgvector for PostgreSQL-based vector storage
- Achieves sub-200ms query latency with optimized indexes
- Supports multiple storage backends (PostgreSQL, ChromaDB, Pinecone)
- Has a knowledge graph for entity relationships
- Provides Redis caching for performance

You are helpful, concise, and knowledgeable about the Core Nexus system.
"""

class SimpleJarvis:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        self.conversation_history = []
        
    async def chat(self, user_input: str) -> str:
        """Process user input and generate response."""
        # Add to history
        self.conversation_history.append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().isoformat()
        })
        
        # Build context
        context = f"{JARVIS_PROMPT}\n\n"
        
        # Add recent conversation
        if len(self.conversation_history) > 1:
            context += "Recent conversation:\n"
            for msg in self.conversation_history[-5:]:
                context += f"{msg['role'].title()}: {msg['content']}\n"
            context += "\n"
        
        # Generate response
        prompt = context + f"Current user input: {user_input}\n\nResponse:"
        response = self.model.generate_content(prompt)
        
        # Extract text
        response_text = response.text if hasattr(response, 'text') else str(response)
        
        # Add to history
        self.conversation_history.append({
            "role": "assistant", 
            "content": response_text,
            "timestamp": datetime.now().isoformat()
        })
        
        return response_text

async def main():
    """Run Jarvis in interactive mode."""
    print("=" * 70)
    print("🤖 JARVIS - Standalone Test Version")
    print("=" * 70)
    print("Type 'quit' to exit\n")
    
    jarvis = SimpleJarvis()
    
    while True:
        try:
            # Get user input
            user_input = input("\n👤 You: ").strip()
            
            if user_input.lower() in ['quit', 'exit']:
                print("\n🤖 Jarvis: Goodbye!")
                break
                
            # Get response
            print("\n🤖 Jarvis: ", end="", flush=True)
            response = await jarvis.chat(user_input)
            print(response)
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())