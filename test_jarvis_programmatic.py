#!/usr/bin/env python3
"""
Programmatic test for Jarvis functionality
"""

import asyncio
import os
from datetime import datetime
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

class TestJarvis:
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

async def test_jarvis():
    """Test Jarvis with various queries."""
    print("=" * 80)
    print("🧪 JARVIS PROGRAMMATIC TEST")
    print("=" * 80)
    
    jarvis = TestJarvis()
    
    # Test queries
    test_cases = [
        {
            "query": "Hello Jarvis, what are you?",
            "expected_topics": ["AI assistant", "Core Nexus"]
        },
        {
            "query": "What is Core Nexus's performance like?",
            "expected_topics": ["sub-200ms", "latency", "performance"]
        },
        {
            "query": "What storage backends does Core Nexus support?",
            "expected_topics": ["PostgreSQL", "ChromaDB", "Pinecone"]
        },
        {
            "query": "How does the knowledge graph work?",
            "expected_topics": ["entity", "relationships", "graph"]
        },
        {
            "query": "What optimizations were applied to pgvector?",
            "expected_topics": ["indexes", "optimization", "pgvector"]
        }
    ]
    
    # Run tests
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}: {test['query']}")
        print("="*60)
        
        try:
            response = await jarvis.chat(test['query'])
            print(f"\n🤖 Jarvis: {response[:300]}...")
            
            # Check if expected topics are mentioned
            topics_found = []
            for topic in test['expected_topics']:
                if topic.lower() in response.lower():
                    topics_found.append(topic)
            
            if topics_found:
                print(f"\n✅ Found expected topics: {', '.join(topics_found)}")
            else:
                print(f"\n⚠️  Missing expected topics: {', '.join(test['expected_topics'])}")
                
        except Exception as e:
            print(f"\n❌ Error: {e}")
    
    # Test conversation context
    print(f"\n{'='*60}")
    print("Testing Conversation Context")
    print("="*60)
    
    await jarvis.chat("My name is Alice and I work on Project Horizon.")
    response = await jarvis.chat("What's my name?")
    
    if "alice" in response.lower():
        print("✅ Context maintained: Jarvis remembered the name")
    else:
        print("❌ Context lost: Jarvis didn't remember the name")
    
    print(f"\n🤖 Jarvis: {response}")
    
    # Show conversation history
    print(f"\n{'='*60}")
    print(f"Conversation History: {len(jarvis.conversation_history)} messages")
    print("="*60)
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    asyncio.run(test_jarvis())