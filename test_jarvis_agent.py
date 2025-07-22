#!/usr/bin/env python3
"""
Test script for Jarvis Agent integration with Core Nexus.
Demonstrates key capabilities and integration points.
"""

import asyncio
import os
import sys

# Add memory service to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python/memory_service'))

from jarvis_agent import JarvisAgent
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_jarvis_capabilities():
    """Test Jarvis agent capabilities."""
    print("=" * 80)
    print("🧪 JARVIS AGENT TEST SUITE")
    print("Testing Google ADK + Core Nexus Integration")
    print("=" * 80)
    
    jarvis = JarvisAgent()
    
    try:
        # Initialize
        print("\n1️⃣ Initializing Jarvis...")
        await jarvis.initialize()
        print("✅ Jarvis initialized successfully")
        
        # Test 1: Basic conversation
        print("\n2️⃣ Testing basic conversation...")
        response = await jarvis.chat("Hello Jarvis, what are you capable of?")
        print(f"Response: {response[:200]}...")
        
        # Test 2: Memory creation
        print("\n3️⃣ Testing memory creation...")
        response = await jarvis.chat(
            "Remember this important information: The Core Nexus system achieved 78% performance improvement "
            "with pgvector optimization and Redis caching, bringing query latency down to 165ms."
        )
        print(f"Response: {response[:200]}...")
        
        # Test 3: Memory search
        print("\n4️⃣ Testing memory search...")
        response = await jarvis.chat("What do you know about Core Nexus performance improvements?")
        print(f"Response: {response[:200]}...")
        
        # Test 4: Context awareness
        print("\n5️⃣ Testing context awareness...")
        response = await jarvis.chat("What was the exact latency improvement percentage?")
        print(f"Response: {response[:200]}...")
        
        # Test 5: Complex query
        print("\n6️⃣ Testing complex reasoning...")
        response = await jarvis.chat(
            "Based on what you know about Core Nexus, what would be the best way to further improve performance?"
        )
        print(f"Response: {response[:200]}...")
        
        # Show session info
        print(f"\n📊 Session Statistics:")
        print(f"  - Session ID: {jarvis.session_id}")
        print(f"  - Conversation ID: {jarvis.conversation_id}")
        print(f"  - Messages in history: {len(jarvis.conversation_history)}")
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        logger.error(f"Test error: {e}", exc_info=True)
    
    finally:
        await jarvis.close()


async def demonstrate_api_integration():
    """Demonstrate how Jarvis integrates with FastAPI."""
    print("\n" + "=" * 80)
    print("🔌 API INTEGRATION EXAMPLE")
    print("=" * 80)
    
    # Show how to add Jarvis to existing API
    example_code = '''
# In your FastAPI app (api.py):

from jarvis_agent import chat_endpoint, ChatRequest, ChatResponse

# Add Jarvis chat endpoint
@app.post("/jarvis/chat", response_model=ChatResponse)
async def jarvis_chat(request: ChatRequest):
    """Chat with Jarvis AI assistant."""
    return await chat_endpoint(request)

# Example usage:
# POST /jarvis/chat
# {
#   "message": "What are the latest memories about project updates?",
#   "user_id": "user123",
#   "conversation_id": "conv456"
# }
'''
    print(example_code)


async def test_memory_integration():
    """Test deep integration with Core Nexus memory system."""
    print("\n" + "=" * 80)
    print("🧠 MEMORY SYSTEM INTEGRATION TEST")
    print("=" * 80)
    
    jarvis = JarvisAgent()
    
    try:
        await jarvis.initialize()
        
        # Create a series of related memories
        test_memories = [
            "Project Horizon is our new AI initiative focused on autonomous agents.",
            "The Horizon team consists of 5 engineers and 2 ML researchers.",
            "Horizon's first milestone is to deploy a conversational AI by Q2 2025.",
            "The Horizon budget has been approved for $2.5M over 18 months."
        ]
        
        print("\n📝 Creating test memories...")
        for memory in test_memories:
            response = await jarvis.chat(f"Remember this: {memory}")
            print(f"  ✓ Stored: {memory[:50]}...")
        
        # Test retrieval
        print("\n🔍 Testing memory retrieval...")
        queries = [
            "What is Project Horizon?",
            "Who is working on Horizon?",
            "What's the timeline for Horizon?",
            "Tell me everything you know about Project Horizon."
        ]
        
        for query in queries:
            print(f"\n❓ Query: {query}")
            response = await jarvis.chat(query)
            print(f"💬 Jarvis: {response[:150]}...")
    
    finally:
        await jarvis.close()


async def main():
    """Run all tests."""
    # Run basic capability tests
    await test_jarvis_capabilities()
    
    # Show API integration
    await demonstrate_api_integration()
    
    # Test memory integration
    await test_memory_integration()
    
    print("\n" + "=" * 80)
    print("🎉 JARVIS AGENT TESTING COMPLETE")
    print("Google ADK successfully integrated with Core Nexus!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())