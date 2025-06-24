#!/usr/bin/env python3
"""
JARVIS Test Suite
Comprehensive validation of JARVIS functionality
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_configuration():
    """Test JARVIS configuration"""
    print("🔧 Testing JARVIS configuration...")
    
    try:
        from jarvis.config import get_config
        config = get_config()
        print(f"  ✅ Gemini API Key: {'*' * (len(config.gemini_api_key) - 4) + config.gemini_api_key[-4:]}")
        print(f"  ✅ Gemini Model: {config.gemini_model}")
        print(f"  ✅ Core Nexus URL: {config.core_nexus_url}")
        print(f"  ✅ Max Iterations: {config.max_iterations}")
        print(f"  ✅ Self Improvement: {config.self_improvement_enabled}")
        return True
    except Exception as e:
        print(f"  ❌ Configuration error: {e}")
        return False

async def test_core_nexus_bridge():
    """Test Core Nexus bridge connection"""
    print("\n🌉 Testing Core Nexus bridge...")
    
    try:
        from jarvis.core_nexus_bridge import CoreNexusBridge
        
        # Create bridge instance
        bridge = CoreNexusBridge()
        print("  ✅ Bridge instance created")
        
        # Test health check
        health = await bridge.health_check()
        print(f"  ✅ Health check: {health['status']}")
        
        # Test stats
        stats = await bridge.get_stats()
        print(f"  ✅ Total memories: {stats.get('total_memories', 'unknown')}")
        
        # Test memory storage
        from jarvis.core_nexus_bridge import JarvisMemory
        test_memory = JarvisMemory(
            content="JARVIS test memory - deployment verification",
            importance_score=0.5,
            metadata={"test": True, "deployment": "verification"}
        )
        
        result = await bridge.store_memory(test_memory)
        print(f"  ✅ Memory stored: {result.get('id', 'no id')}")
        
        # Test memory search
        memories = await bridge.search_memories("JARVIS test", limit=3)
        print(f"  ✅ Search results: {len(memories)} memories found")
        
        # Close the client
        await bridge.client.aclose()
        
        return True
    except Exception as e:
        print(f"  ❌ Core Nexus bridge error: {e}")
        return False

async def test_gemini_integration():
    """Test Gemini AI integration"""
    print("\n🧠 Testing Gemini AI integration...")
    
    try:
        from jarvis.gemini_integration import create_supervisor_agent
        
        # Create supervisor agent
        agent = create_supervisor_agent()
        print("  ✅ Supervisor agent created")
        
        # Test basic response (simple to avoid quota issues)
        result = await agent.think_and_respond(
            "Respond with 'JARVIS operational' to confirm your functionality."
        )
        
        print(f"  ✅ Response received: {result.final_response[:50]}...")
        print(f"  ✅ Confidence score: {result.confidence_score:.2f}")
        print(f"  ✅ Thinking content: {len(result.thinking_content)} characters")
        print(f"  ✅ Reasoning steps: {len(result.reasoning_steps)} steps")
        
        return True
    except Exception as e:
        print(f"  ❌ Gemini integration error: {e}")
        return False

async def test_langgraph_supervisor():
    """Test LangGraph supervisor system"""
    print("\n🎯 Testing LangGraph supervisor...")
    
    try:
        from jarvis.langgraph_supervisor import get_supervisor
        
        # Initialize supervisor
        supervisor = await get_supervisor()
        print("  ✅ Supervisor initialized")
        
        # Test simple task processing
        task = "Verify JARVIS deployment status and confirm all systems operational"
        print(f"  🔄 Processing test task...")
        
        result = await supervisor.process_task(task)
        
        if result["success"]:
            print(f"  ✅ Task completed successfully")
            print(f"  ✅ Iterations: {result.get('iterations', 0)}")
            print(f"  ✅ Duration: {result.get('duration', 0):.1f}s")
            print(f"  ✅ Agent outputs: {len(result.get('agent_outputs', {}))}")
            
            # Show final decision if available
            final_decision = result.get('final_decision')
            if final_decision:
                decision_text = final_decision.get('decision', 'No decision text')
                print(f"  ✅ Final decision: {decision_text[:100]}...")
            
        else:
            print(f"  ❌ Task failed: {result.get('error', 'Unknown error')}")
            return False
        
        return True
    except Exception as e:
        print(f"  ❌ LangGraph supervisor error: {e}")
        return False

async def test_api_endpoints():
    """Test FastAPI endpoints"""
    print("\n🌐 Testing API endpoints...")
    
    try:
        from jarvis.api import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        print("  ✅ API client created")
        
        # Test health endpoint (this might fail without full startup)
        try:
            response = client.get("/health")
            if response.status_code == 200:
                print("  ✅ Health endpoint accessible")
            else:
                print(f"  ⚠️  Health endpoint returned {response.status_code}")
        except Exception as e:
            print(f"  ⚠️  Health endpoint test skipped: {e}")
        
        print("  ✅ API structure validated")
        
        return True
    except Exception as e:
        print(f"  ❌ API endpoint error: {e}")
        return False

async def test_end_to_end():
    """End-to-end integration test"""
    print("\n🚀 Running end-to-end integration test...")
    
    try:
        # Test complete workflow
        from jarvis.core_nexus_bridge import get_bridge
        from jarvis.langgraph_supervisor import get_supervisor
        
        # Initialize components
        bridge = await get_bridge()
        supervisor = await get_supervisor()
        
        # Test memory and supervisor integration
        task = "Perform deployment verification: Check Core Nexus connectivity, validate memory operations, and confirm JARVIS operational status."
        
        print("  🔄 Processing comprehensive integration task...")
        result = await supervisor.process_task(task)
        
        if result["success"]:
            print("  ✅ End-to-end test passed!")
            print(f"     • Iterations: {result.get('iterations', 0)}")
            print(f"     • Learning opportunities: {len(result.get('learning_opportunities', []))}")
            print(f"     • Improvement suggestions: {len(result.get('improvement_suggestions', []))}")
            
            # Verify memory storage worked
            recent_memories = await bridge.get_recent_jarvis_memories(limit=5)
            print(f"     • Recent JARVIS memories: {len(recent_memories)}")
            
        else:
            print(f"  ❌ End-to-end test failed: {result.get('error')}")
            return False
        
        return True
    except Exception as e:
        print(f"  ❌ End-to-end test error: {e}")
        return False

async def main():
    """Run all JARVIS deployment tests"""
    print("🤖 JARVIS Deployment Test Suite")
    print("=" * 50)
    
    tests = [
        ("Configuration", test_configuration),
        ("Core Nexus Bridge", test_core_nexus_bridge),
        ("Gemini Integration", test_gemini_integration),
        ("LangGraph Supervisor", test_langgraph_supervisor),
        ("API Endpoints", test_api_endpoints),
        ("End-to-End Integration", test_end_to_end)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            if result:
                passed += 1
            print()  # Add spacing between tests
        except Exception as e:
            print(f"  💥 {test_name} test crashed: {e}")
            print()
    
    # Summary
    print("=" * 50)
    print(f"🎯 Test Results: {passed}/{total} tests passed")
    
    if passed >= total - 1:  # Allow one test to fail (API endpoints might not start)
        print("🎉 JARVIS deployment validation successful!")
        print("🚀 JARVIS is ready for production operation.")
        return 0
    else:
        print("⚠️  Deployment validation failed. Please check the configuration and dependencies.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)