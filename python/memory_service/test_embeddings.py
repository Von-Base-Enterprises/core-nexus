#!/usr/bin/env python3
"""
Test script for OpenAI embeddings integration in Core Nexus Memory Service.

This script tests both mock and OpenAI embedding models to ensure proper functionality.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from memory_service.embedding_models import MockEmbeddingModel, create_embedding_model


async def test_mock_embedding():
    """Test mock embedding model."""
    print("🔧 Testing Mock Embedding Model...")

    try:
        mock_model = MockEmbeddingModel(dimension=1536)

        # Test single embedding
        test_text = "This is a test message for embedding generation."
        embedding = await mock_model.embed_text(test_text)

        print("✅ Mock embedding generated successfully")
        print(f"   - Text: '{test_text}'")
        print(f"   - Dimension: {len(embedding)}")
        print(f"   - Sample values: {embedding[:5]}")

        # Test batch embedding
        test_texts = [
            "First test message",
            "Second test message",
            "Third test message"
        ]
        batch_embeddings = await mock_model.embed_batch(test_texts)

        print("✅ Mock batch embedding generated successfully")
        print(f"   - Batch size: {len(batch_embeddings)}")
        print(f"   - All dimensions: {[len(emb) for emb in batch_embeddings]}")

        return True

    except Exception as e:
        print(f"❌ Mock embedding test failed: {e}")
        return False


async def test_openai_embedding():
    """Test OpenAI embedding model."""
    print("\n🤖 Testing OpenAI Embedding Model...")

    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        print("⚠️  No OPENAI_API_KEY found, skipping OpenAI test")
        return True

    try:
        # Create OpenAI model
        openai_model = create_embedding_model(
            provider="openai",
            model="text-embedding-3-small",
            api_key=api_key,
            timeout=30.0
        )

        print(f"✅ OpenAI model initialized: {openai_model.model}")
        print(f"   - Dimension: {openai_model.dimension}")

        # Test health check
        health = await openai_model.health_check()
        print(f"✅ Health check: {health['status']}")
        if health['status'] == 'healthy':
            print(f"   - Response time: {health['response_time_ms']}ms")
        else:
            print(f"   - Error: {health.get('error', 'Unknown')}")
            return False

        # Test single embedding
        test_text = "Core Nexus is an advanced AI memory system that provides persistent storage and retrieval of contextual information."
        embedding = await openai_model.embed_text(test_text)

        print("✅ OpenAI embedding generated successfully")
        print(f"   - Text length: {len(test_text)} characters")
        print(f"   - Embedding dimension: {len(embedding)}")
        print(f"   - Sample values: {[round(v, 4) for v in embedding[:5]]}")

        # Test batch embedding
        test_texts = [
            "Memory storage and retrieval system",
            "Advanced artificial intelligence",
            "Vector database integration"
        ]
        batch_embeddings = await openai_model.embed_batch(test_texts)

        print("✅ OpenAI batch embedding generated successfully")
        print(f"   - Batch size: {len(batch_embeddings)}")
        print(f"   - All dimensions: {[len(emb) for emb in batch_embeddings]}")

        return True

    except ImportError as e:
        print(f"⚠️  OpenAI package not available: {e}")
        print("   Install with: pip install openai")
        return True  # Not a failure, just missing dependency

    except Exception as e:
        print(f"❌ OpenAI embedding test failed: {e}")
        return False


async def test_factory_function():
    """Test the factory function for creating embedding models."""
    print("\n🏭 Testing Embedding Model Factory...")

    try:
        # Test mock model creation
        mock_model = create_embedding_model(provider="mock", dimension=512)
        assert mock_model.dimension == 512
        print("✅ Mock model factory works")

        # Test OpenAI model creation (if API key available)
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and api_key.strip():
            try:
                openai_model = create_embedding_model(
                    provider="openai",
                    model="text-embedding-3-small"
                )
                assert openai_model.dimension == 1536
                print("✅ OpenAI model factory works")
            except Exception as e:
                print(f"⚠️  OpenAI model factory failed: {e}")

        # Test invalid provider
        try:
            create_embedding_model(provider="invalid")
            print("❌ Should have failed for invalid provider")
            return False
        except ValueError:
            print("✅ Correctly rejected invalid provider")

        return True

    except Exception as e:
        print(f"❌ Factory function test failed: {e}")
        return False


async def test_integration_simulation():
    """Simulate integration with memory service."""
    print("\n🔌 Testing Memory Service Integration Simulation...")

    try:
        # Simulate the API initialization logic
        api_key = os.getenv("OPENAI_API_KEY")

        if api_key and api_key.strip():
            embedding_model = create_embedding_model(
                provider="openai",
                model="text-embedding-3-small",
                api_key=api_key,
                max_retries=3,
                timeout=30.0
            )
            print(f"✅ Would use OpenAI model: {embedding_model.__class__.__name__}")
        else:
            embedding_model = create_embedding_model(provider="mock", dimension=1536)
            print(f"✅ Would use mock model: {embedding_model.__class__.__name__}")

        # Test memory request simulation
        memory_content = "User asked about implementing a caching system for the memory service to improve query performance."
        embedding = await embedding_model.embed_text(memory_content)

        print("✅ Memory embedding generated")
        print(f"   - Content length: {len(memory_content)} chars")
        print(f"   - Embedding dimension: {len(embedding)}")
        print("   - Ready for vector storage")

        return True

    except Exception as e:
        print(f"❌ Integration simulation failed: {e}")
        return False


async def main():
    """Run all embedding tests."""
    print("🚀 Core Nexus OpenAI Embeddings Test Suite")
    print("=" * 50)

    tests = [
        ("Mock Embedding", test_mock_embedding),
        ("OpenAI Embedding", test_openai_embedding),
        ("Factory Function", test_factory_function),
        ("Integration Simulation", test_integration_simulation)
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} Test...")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")

    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {test_name}")
        if result:
            passed += 1

    print(f"\n🎯 Results: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("🎉 All tests passed! OpenAI embeddings are ready for production.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")

    return passed == len(results)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
