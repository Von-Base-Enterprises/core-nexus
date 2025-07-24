#!/usr/bin/env python3
"""Simple test for Jarvis without imports"""

import asyncio
import os
import sys

# Add memory service to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python/memory_service/src'))

async def test_basic_chat():
    """Test basic Jarvis functionality"""
    try:
        # Test Google Generative AI
        import google.generativeai as genai
        
        # Configure
        api_key = os.getenv("GEMINI_API_KEY", "AIzaSyAIl8F81WwFfx5_62y19KuO12ermaDC6FQ")
        genai.configure(api_key=api_key)
        
        # Create model
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Test generation
        print("Testing Gemini API...")
        response = model.generate_content("Say hello in 5 words or less")
        print(f"Gemini response: {response.text}")
        
        # Now test with Core Nexus context
        prompt = """You are Jarvis, an AI assistant for Core Nexus.
        
User: What is Core Nexus?

Response:"""
        
        response = model.generate_content(prompt)
        print(f"\nJarvis response: {response.text}")
        
        print("\n✅ Basic Gemini test passed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_basic_chat())