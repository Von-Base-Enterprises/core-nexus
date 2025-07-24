#!/usr/bin/env python3
"""
Test script to verify Google ADK installation and basic functionality.
Run this locally before deploying to production.
"""

import asyncio
import sys
import traceback


def test_imports():
    """Test that all ADK imports work correctly."""
    print("Testing ADK imports...")
    
    try:
        # Core imports
        from google.adk.agents import Agent, LlmAgent
        print("✅ Agent imports successful")
        
        from google.adk.runners import Runner
        print("✅ Runner import successful")
        
        from google.adk.sessions import InMemorySessionService
        print("✅ Session service import successful")
        
        from google.adk.tools import FunctionTool, ToolContext
        print("✅ Tool imports successful")
        
        # Workflow agents
        from google.adk.agents import SequentialAgent, ParallelAgent, LoopAgent
        print("✅ Workflow agent imports successful")
        
        # Types
        from google.genai import types
        print("✅ Types import successful")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print(f"Make sure you've installed: pip install google-adk")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        traceback.print_exc()
        return False


def test_basic_agent_creation():
    """Test creating a basic ADK agent."""
    print("\nTesting basic agent creation...")
    
    try:
        from google.adk.agents import Agent
        
        # Create minimal agent
        test_agent = Agent(
            name="test_agent",
            model="gemini-2.0-flash-exp",
            instructions="You are a test agent. When asked anything, respond with 'Hello from ADK!'"
        )
        
        print(f"✅ Created agent: {test_agent.name}")
        return test_agent
        
    except Exception as e:
        print(f"❌ Failed to create agent: {e}")
        traceback.print_exc()
        return None


def test_tool_creation():
    """Test creating ADK tools."""
    print("\nTesting tool creation...")
    
    try:
        from google.adk.tools import FunctionTool
        
        # Define a simple tool
        def get_current_time() -> str:
            """Get the current time."""
            from datetime import datetime
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Convert to ADK tool
        time_tool = FunctionTool(get_current_time)
        
        print("✅ Created function tool successfully")
        return time_tool
        
    except Exception as e:
        print(f"❌ Failed to create tool: {e}")
        traceback.print_exc()
        return None


async def test_runner_and_session():
    """Test creating runner and session service."""
    print("\nTesting runner and session setup...")
    
    try:
        from google.adk.agents import Agent
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        
        # Create components
        agent = Agent(
            name="runner_test_agent",
            model="gemini-2.0-flash-exp",
            instructions="You are a helpful assistant."
        )
        
        session_service = InMemorySessionService()
        runner = Runner(
            agent=agent,
            session_service=session_service
        )
        
        print("✅ Created runner and session service successfully")
        
        # Test a simple query (requires API key)
        try:
            print("\nAttempting test query...")
            result = await runner.run_async("Say hello")
            print(f"✅ Query successful! Response: {result}")
        except Exception as e:
            print(f"⚠️  Query failed (this is expected without API key): {e}")
            
        return True
        
    except Exception as e:
        print(f"❌ Failed to create runner: {e}")
        traceback.print_exc()
        return False


def test_workflow_agents():
    """Test workflow agent creation."""
    print("\nTesting workflow agents...")
    
    try:
        from google.adk.agents import Agent, SequentialAgent, ParallelAgent
        
        # Create sub-agents
        agent1 = Agent(name="agent1", model="gemini-2.0-flash-exp", instructions="First agent")
        agent2 = Agent(name="agent2", model="gemini-2.0-flash-exp", instructions="Second agent")
        
        # Sequential workflow
        sequential = SequentialAgent(
            name="sequential_workflow",
            sub_agents=[agent1, agent2]
        )
        print("✅ Created SequentialAgent")
        
        # Parallel workflow
        parallel = ParallelAgent(
            name="parallel_workflow",
            sub_agents=[agent1, agent2]
        )
        print("✅ Created ParallelAgent")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create workflow agents: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Google ADK Installation Test")
    print("=" * 60)
    
    # Check Python version
    print(f"Python version: {sys.version}")
    if sys.version_info < (3, 8):
        print("⚠️  Warning: ADK requires Python 3.8 or higher")
    
    # Run tests
    tests_passed = 0
    total_tests = 5
    
    # Test 1: Imports
    if test_imports():
        tests_passed += 1
    
    # Test 2: Basic agent
    if test_basic_agent_creation():
        tests_passed += 1
    
    # Test 3: Tools
    if test_tool_creation():
        tests_passed += 1
    
    # Test 4: Workflow agents
    if test_workflow_agents():
        tests_passed += 1
    
    # Test 5: Runner and session (async)
    if asyncio.run(test_runner_and_session()):
        tests_passed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("✅ All tests passed! ADK is properly installed.")
        print("\nNext steps:")
        print("1. Set GEMINI_API_KEY environment variable")
        print("2. Run: python jarvis_adk_agent.py")
        return 0
    else:
        print("❌ Some tests failed. Check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())