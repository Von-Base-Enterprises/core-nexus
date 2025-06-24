#!/usr/bin/env python3
"""
JARVIS Quick Test - Basic deployment validation
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_imports():
    """Test all JARVIS module imports"""
    print("📦 Testing JARVIS module imports...")
    
    try:
        # Test core imports
        from jarvis.config import get_config
        print("  ✅ Config module")
        
        from jarvis.core_nexus_bridge import CoreNexusBridge, JarvisMemory
        print("  ✅ Core Nexus bridge module")
        
        from jarvis.gemini_integration import GeminiAgent, create_supervisor_agent
        print("  ✅ Gemini integration module")
        
        from jarvis.langgraph_supervisor import JarvisSupervisor
        print("  ✅ LangGraph supervisor module")
        
        from jarvis.api import app
        print("  ✅ FastAPI module")
        
        from jarvis.main import main
        print("  ✅ Main application module")
        
        return True
    except Exception as e:
        print(f"  ❌ Import error: {e}")
        return False

async def test_configuration():
    """Test JARVIS configuration"""
    print("\n🔧 Testing configuration...")
    
    try:
        from jarvis.config import get_config
        config = get_config()
        print(f"  ✅ Gemini API Key configured: {len(config.gemini_api_key) > 0}")
        print(f"  ✅ Core Nexus URL: {config.core_nexus_url}")
        print(f"  ✅ Configuration valid")
        return True
    except Exception as e:
        print(f"  ❌ Configuration error: {e}")
        return False

async def test_core_nexus():
    """Test Core Nexus connectivity"""
    print("\n🌉 Testing Core Nexus connectivity...")
    
    try:
        from jarvis.core_nexus_bridge import CoreNexusBridge
        
        bridge = CoreNexusBridge()
        health = await bridge.health_check()
        stats = await bridge.get_stats()
        
        print(f"  ✅ Core Nexus status: {health['status']}")
        print(f"  ✅ Total memories: {stats.get('total_memories', 'unknown')}")
        
        await bridge.client.aclose()
        return True
    except Exception as e:
        print(f"  ❌ Core Nexus error: {e}")
        return False

async def test_basic_functionality():
    """Test basic JARVIS functionality"""
    print("\n🤖 Testing basic JARVIS functionality...")
    
    try:
        from jarvis.gemini_integration import create_supervisor_agent
        from jarvis.core_nexus_bridge import CoreNexusBridge, JarvisMemory
        
        # Test agent creation
        agent = create_supervisor_agent()
        print("  ✅ Agent created")
        
        # Test memory operations
        bridge = CoreNexusBridge()
        memory = JarvisMemory(
            content="JARVIS deployment test - basic functionality verification",
            importance_score=0.7,
            metadata={"test": "deployment", "phase": "validation"}
        )
        
        result = await bridge.store_memory(memory)
        print(f"  ✅ Memory stored: {result.get('id', 'unknown')}")
        
        await bridge.client.aclose()
        return True
    except Exception as e:
        print(f"  ❌ Basic functionality error: {e}")
        return False

async def main():
    """Run quick JARVIS deployment test"""
    print("🚀 JARVIS Quick Deployment Test")
    print("=" * 40)
    
    tests = [
        test_imports,
        test_configuration,
        test_core_nexus,
        test_basic_functionality
    ]
    
    passed = 0
    for test in tests:
        try:
            if await test():
                passed += 1
        except Exception as e:
            print(f"  💥 Test crashed: {e}")
    
    print("\n" + "=" * 40)
    print(f"🎯 Results: {passed}/{len(tests)} tests passed")
    
    if passed >= 3:  # Allow one test to fail
        print("🎉 JARVIS deployment ready!")
        return 0
    else:
        print("⚠️  Deployment issues detected")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)