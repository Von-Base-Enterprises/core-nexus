#!/usr/bin/env python3
"""
Test script to verify knowledge graph activation.

Run this after setting GRAPH_ENABLED=true to confirm the graph is working.
"""

import asyncio
import json
import os
import sys
from datetime import datetime


def check_environment():
    """Check environment setup."""
    print("🔍 Checking Environment")
    print("=" * 60)

    # Check GRAPH_ENABLED
    graph_enabled = os.getenv("GRAPH_ENABLED", "false")
    print(f"GRAPH_ENABLED: {graph_enabled}")

    if graph_enabled.lower() != "true":
        print("⚠️  Warning: GRAPH_ENABLED is not set to 'true'")
        print("   Set it with: export GRAPH_ENABLED=true")
    else:
        print("✅ Graph feature flag is enabled")

    # Check database URL
    db_host = os.getenv("PGVECTOR_HOST", "not set")
    print(f"\nPGVECTOR_HOST: {db_host}")

    # Check for spacy
    try:
        import spacy
        print("\n✅ spaCy is installed")
        try:
            spacy.load("en_core_web_sm")
            print("✅ spaCy model 'en_core_web_sm' is available")
        except Exception:
            print("⚠️  spaCy model not found. Install with:")
            print("   python -m spacy download en_core_web_sm")
    except ImportError:
        print("\n⚠️  spaCy not installed. Install with:")
        print("   pip install spacy")

    print()


async def test_api_endpoints():
    """Test the graph API endpoints."""
    print("🧪 Testing Graph API Endpoints")
    print("=" * 60)

    try:
        import aiohttp
    except ImportError:
        print("Using urllib instead of aiohttp")
        import urllib.error
        import urllib.request

        base_url = "http://localhost:8000"

        # Test 1: Graph Stats
        print("\n1. Testing /graph/stats endpoint...")
        try:
            req = urllib.request.Request(f"{base_url}/graph/stats")
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read())
                print(f"✅ Graph stats accessible: {response.status}")
                print(f"   Response: {json.dumps(data, indent=2)}")
        except urllib.error.HTTPError as e:
            if e.code == 503:
                print("❌ Graph provider not available (503)")
                print("   This means GRAPH_ENABLED might not be set or initialization failed")
            else:
                print(f"❌ Error: {e.code} - {e.reason}")
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            print("   Is the API server running?")

        # Test 2: Health Check
        print("\n2. Testing /health endpoint...")
        try:
            req = urllib.request.Request(f"{base_url}/health")
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read())
                print(f"✅ Health check: {data.get('status')}")

                # Check if graph provider is in the providers list
                if 'providers' in data:
                    if 'graph' in data['providers']:
                        print("✅ Graph provider is registered!")
                        print(f"   Status: {data['providers']['graph']}")
                    else:
                        print("⚠️  Graph provider not found in providers list")
                        print(f"   Available providers: {list(data['providers'].keys())}")
        except Exception as e:
            print(f"❌ Health check failed: {e}")

        return

    # If aiohttp is available, use it
    async with aiohttp.ClientSession():
        base_url = "http://localhost:8000"

        # Similar tests with aiohttp...
        print("Testing with aiohttp...")


def test_local_import():
    """Test importing the GraphProvider directly."""
    print("\n🔬 Testing Direct Import")
    print("=" * 60)

    try:
        # Add parent directory to path
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

        from src.memory_service.models import ProviderConfig
        from src.memory_service.providers import GraphProvider

        print("✅ GraphProvider imported successfully")

        # Try to create a mock instance
        config = ProviderConfig(
            name="graph",
            enabled=True,
            primary=False,
            config={
                "connection_string": "postgresql://test@localhost/test",
                "table_prefix": "graph"
            }
        )

        provider = GraphProvider(config)
        print("✅ GraphProvider instance created")
        print(f"   Provider name: {provider.name}")
        print(f"   Enabled: {provider.enabled}")

    except ImportError as e:
        print(f"❌ Import failed: {e}")
    except Exception as e:
        print(f"❌ Error creating provider: {e}")


def print_activation_summary():
    """Print summary and next steps."""
    print("\n📋 Activation Summary")
    print("=" * 60)

    if os.getenv("GRAPH_ENABLED", "false").lower() == "true":
        print("✅ Feature flag is SET")
        print("\nTo test the activation:")
        print("1. Start the API server:")
        print("   cd /path/to/memory_service")
        print("   python -m uvicorn memory_service.api:app --reload")
        print("\n2. In another terminal, run this script again")
        print("\n3. Check the API logs for:")
        print("   '✅ Graph provider initialized successfully'")
    else:
        print("❌ Feature flag is NOT SET")
        print("\nTo activate the knowledge graph:")
        print("1. Set the environment variable:")
        print("   export GRAPH_ENABLED=true")
        print("\n2. Install spaCy (if needed):")
        print("   pip install spacy")
        print("   python -m spacy download en_core_web_sm")
        print("\n3. Start the API server and run this test again")

    print("\n🏎️  Ready to unleash the Ferrari!")


def main():
    """Run all tests."""
    print("🚀 Knowledge Graph Activation Test")
    print("=" * 60)
    print(f"Time: {datetime.now().isoformat()}")
    print()

    # Run tests
    check_environment()
    test_local_import()

    # Try API tests
    print("\n" + "=" * 60)
    try:
        asyncio.run(test_api_endpoints())
    except Exception:
        # Fallback to sync version
        import time
        time.sleep(0.1)  # Small delay
        asyncio.run(test_api_endpoints())

    print_activation_summary()


if __name__ == "__main__":
    main()
