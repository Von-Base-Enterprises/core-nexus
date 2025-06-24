"""
JARVIS Main Entry Point
Command-line interface and application runner
"""

import asyncio
import sys
import argparse
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich.table import Table
import structlog

from .config import get_config
from .langgraph_supervisor import get_supervisor
from .core_nexus_bridge import get_bridge
from .api import main as api_main

console = Console()
logger = structlog.get_logger(__name__)

async def test_jarvis_connection():
    """Test JARVIS connections and setup"""
    console.print(Panel.fit("🤖 JARVIS Connection Test", style="bold blue"))
    
    try:
        # Test Core Nexus connection
        console.print("🔄 Testing Core Nexus connection...")
        bridge = await get_bridge()
        health = await bridge.health_check()
        stats = await bridge.get_stats()
        
        console.print(f"✅ Core Nexus: {health['status']}")
        console.print(f"📊 Total memories: {stats.get('total_memories', 'unknown')}")
        
        # Test JARVIS supervisor
        console.print("\n🔄 Initializing JARVIS supervisor...")
        supervisor = await get_supervisor()
        console.print("✅ JARVIS supervisor ready")
        
        # Test Gemini integration
        console.print("\n🔄 Testing Gemini AI integration...")
        test_result = await supervisor.supervisor_agent.think_and_respond(
            "Hello, this is a test of your capabilities. Please respond with a brief acknowledgment."
        )
        console.print(f"✅ Gemini AI: Response received (confidence: {test_result.confidence_score:.2f})")
        
        console.print(Panel.fit("🎉 All systems operational!", style="bold green"))
        return True
        
    except Exception as e:
        console.print(f"❌ Connection test failed: {str(e)}", style="bold red")
        return False

async def interactive_mode():
    """Interactive JARVIS command-line interface"""
    console.print(Panel.fit("🤖 JARVIS Interactive Mode", style="bold blue"))
    console.print("Type 'help' for commands, 'quit' to exit\n")
    
    try:
        supervisor = await get_supervisor()
        bridge = await get_bridge()
        
        while True:
            user_input = Prompt.ask("[bold cyan]JARVIS>[/bold cyan]")
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                console.print("👋 Goodbye!", style="bold blue")
                break
            elif user_input.lower() == 'help':
                show_help()
                continue
            elif user_input.lower() == 'status':
                await show_status(bridge)
                continue
            elif user_input.lower() == 'stats':
                await show_stats(bridge)
                continue
            elif user_input.lower().startswith('task '):
                task = user_input[5:].strip()
                await process_task_interactive(supervisor, task)
                continue
            elif user_input.lower().startswith('chat '):
                message = user_input[5:].strip()
                await chat_interactive(supervisor, message)
                continue
            elif user_input.lower().startswith('search '):
                query = user_input[7:].strip()
                await search_memories_interactive(bridge, query)
                continue
            
            # Default: process as a task
            if user_input.strip():
                await process_task_interactive(supervisor, user_input)
    
    except KeyboardInterrupt:
        console.print("\n👋 Goodbye!", style="bold blue")
    except Exception as e:
        console.print(f"❌ Error in interactive mode: {str(e)}", style="bold red")

def show_help():
    """Show help information"""
    table = Table(title="JARVIS Commands")
    table.add_column("Command", style="cyan")
    table.add_column("Description", style="white")
    
    table.add_row("help", "Show this help message")
    table.add_row("status", "Show JARVIS system status")
    table.add_row("stats", "Show system statistics")
    table.add_row("task <description>", "Process a task through JARVIS workflow")
    table.add_row("chat <message>", "Direct chat with JARVIS supervisor")
    table.add_row("search <query>", "Search Core Nexus memories")
    table.add_row("quit/exit/q", "Exit JARVIS")
    table.add_row("<anything else>", "Process as a task")
    
    console.print(table)

async def show_status(bridge):
    """Show JARVIS system status"""
    try:
        health = await bridge.health_check()
        
        table = Table(title="🤖 JARVIS System Status")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="white")
        table.add_column("Details", style="dim")
        
        table.add_row("JARVIS", "✅ Online", "All systems operational")
        table.add_row("Core Nexus", f"✅ {health['status']}", f"Uptime: {health.get('uptime_seconds', 0):.0f}s")
        table.add_row("Memory Service", "✅ Connected", f"Total memories: {health.get('total_memories', 'unknown')}")
        
        console.print(table)
        
    except Exception as e:
        console.print(f"❌ Failed to get status: {str(e)}", style="bold red")

async def show_stats(bridge):
    """Show detailed system statistics"""
    try:
        stats = await bridge.get_stats()
        jarvis_memories = await bridge.get_recent_jarvis_memories(limit=10)
        
        table = Table(title="📊 JARVIS Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Total Memories", str(stats.get('total_memories', 'unknown')))
        table.add_row("JARVIS Memories", str(len(jarvis_memories)))
        table.add_row("Average Query Time", f"{stats.get('avg_query_time_ms', 0):.0f}ms")
        table.add_row("System Uptime", f"{stats.get('uptime_seconds', 0):.0f}s")
        
        console.print(table)
        
    except Exception as e:
        console.print(f"❌ Failed to get stats: {str(e)}", style="bold red")

async def process_task_interactive(supervisor, task: str):
    """Process a task in interactive mode"""
    try:
        console.print(f"🔄 Processing task: [cyan]{task}[/cyan]")
        
        with console.status("[bold green]JARVIS is thinking..."):
            result = await supervisor.process_task(task)
        
        if result["success"]:
            console.print("✅ Task completed successfully!", style="bold green")
            
            # Show final decision
            final_decision = result.get("final_decision")
            if final_decision:
                console.print(Panel(
                    final_decision.get("decision", "No decision available"),
                    title="🎯 Final Decision",
                    style="green"
                ))
            
            # Show key insights
            if result.get("improvement_suggestions"):
                console.print("\n💡 Improvement Suggestions:")
                for suggestion in result["improvement_suggestions"][:3]:
                    console.print(f"  • {suggestion[:100]}...")
            
            console.print(f"\n📊 Completed in {result.get('iterations', 0)} iterations ({result.get('duration', 0):.1f}s)")
            
        else:
            console.print(f"❌ Task failed: {result.get('error', 'Unknown error')}", style="bold red")
            
    except Exception as e:
        console.print(f"❌ Error processing task: {str(e)}", style="bold red")

async def chat_interactive(supervisor, message: str):
    """Direct chat with JARVIS in interactive mode"""
    try:
        console.print(f"💬 Chatting with JARVIS: [cyan]{message}[/cyan]")
        
        with console.status("[bold green]JARVIS is thinking..."):
            result = await supervisor.supervisor_agent.process_with_memory_context(message)
        
        # Show response
        console.print(Panel(
            result.final_response,
            title=f"🤖 JARVIS (confidence: {result.confidence_score:.2f})",
            style="blue"
        ))
        
        # Show thinking if available
        if result.thinking_content:
            console.print(Panel(
                result.thinking_content[:500] + "..." if len(result.thinking_content) > 500 else result.thinking_content,
                title="🧠 Thinking Process",
                style="dim"
            ))
            
    except Exception as e:
        console.print(f"❌ Error in chat: {str(e)}", style="bold red")

async def search_memories_interactive(bridge, query: str):
    """Search memories in interactive mode"""
    try:
        console.print(f"🔍 Searching memories: [cyan]{query}[/cyan]")
        
        memories = await bridge.search_memories(query, limit=5)
        
        if memories:
            console.print(f"\n📚 Found {len(memories)} memories:")
            for i, memory in enumerate(memories, 1):
                console.print(f"\n[bold]{i}.[/bold] {memory['content'][:200]}...")
                console.print(f"   [dim]Importance: {memory.get('importance_score', 0):.2f} | Created: {memory.get('created_at', 'unknown')}[/dim]")
        else:
            console.print("🔍 No memories found matching that query")
            
    except Exception as e:
        console.print(f"❌ Error searching memories: {str(e)}", style="bold red")

async def run_single_task(task: str):
    """Run a single task and exit"""
    console.print(Panel.fit(f"🤖 JARVIS Processing Task", style="bold blue"))
    
    try:
        supervisor = await get_supervisor()
        
        console.print(f"📝 Task: {task}")
        console.print("🔄 Processing...\n")
        
        result = await supervisor.process_task(task)
        
        if result["success"]:
            console.print("✅ Task completed successfully!", style="bold green")
            
            final_decision = result.get("final_decision")
            if final_decision:
                console.print(Panel(
                    final_decision.get("decision", "No decision available"),
                    title="🎯 Final Decision",
                    style="green"
                ))
            
            # Show summary
            console.print(f"\n📊 Summary:")
            console.print(f"  • Iterations: {result.get('iterations', 0)}")
            console.print(f"  • Duration: {result.get('duration', 0):.1f}s")
            console.print(f"  • Learning opportunities: {len(result.get('learning_opportunities', []))}")
            console.print(f"  • Improvement suggestions: {len(result.get('improvement_suggestions', []))}")
            
        else:
            console.print(f"❌ Task failed: {result.get('error', 'Unknown error')}", style="bold red")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"❌ Error: {str(e)}", style="bold red")
        sys.exit(1)

def main():
    """Main entry point for JARVIS CLI"""
    parser = argparse.ArgumentParser(description="JARVIS - Core Nexus AI Agent System")
    parser.add_argument("--mode", choices=["api", "interactive", "test", "task"], 
                       default="interactive", help="Run mode")
    parser.add_argument("--task", type=str, help="Single task to process (for task mode)")
    
    args = parser.parse_args()
    
    try:
        if args.mode == "api":
            console.print("🚀 Starting JARVIS API server...")
            api_main()
        elif args.mode == "test":
            asyncio.run(test_jarvis_connection())
        elif args.mode == "task":
            if not args.task:
                console.print("❌ Task mode requires --task argument", style="bold red")
                sys.exit(1)
            asyncio.run(run_single_task(args.task))
        else:  # interactive
            asyncio.run(interactive_mode())
            
    except KeyboardInterrupt:
        console.print("\n👋 Goodbye!", style="bold blue")
    except Exception as e:
        console.print(f"❌ Fatal error: {str(e)}", style="bold red")
        sys.exit(1)

if __name__ == "__main__":
    main()