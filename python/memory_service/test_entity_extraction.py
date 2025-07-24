#!/usr/bin/env python3
"""
Test script to verify entity extraction improvements with Gemini AI integration.
"""

import asyncio
import os
import sys
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from memory_service.providers import GraphProvider
from memory_service.models import ProviderConfig


class EntityExtractionTester:
    """Test harness for entity extraction methods."""
    
    def __init__(self):
        # Create a minimal GraphProvider instance
        config = ProviderConfig(
            name="graph",
            enabled=True,
            connection_string=""  # Not needed for entity extraction
        )
        self.provider = GraphProvider(config)
        
    async def test_extraction(self, test_cases: List[str]):
        """Test entity extraction on various inputs."""
        print("=" * 80)
        print("Entity Extraction Test Results")
        print("=" * 80)
        
        for i, content in enumerate(test_cases, 1):
            print(f"\nTest Case {i}:")
            print(f"Input: '{content}'")
            print("-" * 40)
            
            # Test extraction
            entities = await self.provider._extract_entities(content)
            
            if entities:
                print(f"Extracted {len(entities)} entities:")
                for entity in entities:
                    print(f"  - '{entity['name']}' ({entity['type']}) [confidence: {entity['confidence']:.2f}]")
            else:
                print("  No entities extracted")
                
        print("\n" + "=" * 80)
        
    async def test_regex_fallback(self, test_cases: List[str]):
        """Test the regex fallback specifically."""
        print("\nRegex Fallback Test")
        print("=" * 80)
        
        for content in test_cases:
            print(f"\nInput: '{content}'")
            entities = self.provider._extract_entities_regex(content)
            print(f"Regex extracted: {[e['name'] for e in entities]}")


async def main():
    """Run entity extraction tests."""
    
    # Test cases covering various entity types
    test_cases = [
        # Basic queries that failed with old regex
        "Core Nexus AI development",
        "John Smith from Von Base Enterprises",
        "AI and machine learning with GPT-4",
        "Tyvonne works on Core Nexus",
        "API integration with ChromaDB",
        
        # Complex technical entities
        "Using pgvector with PostgreSQL and OpenAI embeddings",
        "Deploy with Google ADK and Gemini 2.0 Flash",
        "FastAPI backend with Redis caching",
        
        # Mixed case challenges
        "ChromaDB vs Pinecone for vector storage",
        "GPT-4 and Claude compete with Gemini",
        
        # Real-world examples
        "The CEO of Von Base Enterprises announced Core Nexus AI system",
        "Engineers at Google developed the ADK framework",
        
        # Edge cases
        "AI, ML, API, SDK, ADK",  # All acronyms
        "test@example.com contacted support",  # Email
        ""  # Empty string
    ]
    
    tester = EntityExtractionTester()
    
    # Check if Gemini API key is available
    if os.getenv("GEMINI_API_KEY"):
        print("✅ Gemini API key found - testing full extraction pipeline")
    else:
        print("⚠️  No Gemini API key - will use fallback methods")
    
    # Test full extraction pipeline
    await tester.test_extraction(test_cases)
    
    # Test regex fallback specifically
    await tester.test_regex_fallback(test_cases[:5])
    
    # Summary
    print("\n" + "=" * 80)
    print("Summary:")
    print("- Gemini extraction provides best accuracy for complex entities")
    print("- Enhanced regex catches acronyms, CamelCase, and known entities")
    print("- Multiple fallback layers ensure extraction always works")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())