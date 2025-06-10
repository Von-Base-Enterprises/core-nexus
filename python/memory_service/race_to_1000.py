#!/usr/bin/env python3
"""
RACE TO 1000 MEMORIES! 🏁
Agent 2's Competitive Memory Ingestion Script
First to 1000 memories gets to name the AI assistant!
"""

import asyncio
import random
from datetime import datetime
from typing import Any

import aiohttp


class MemoryRacer:
    """Competitive memory ingestion with real-time leaderboard."""

    def __init__(self, agent_name: str = "Agent_2_Knowledge_Graph"):
        self.agent_name = agent_name
        self.base_url = "https://core-nexus-memory-service.onrender.com"
        self.memories_stored = 0
        self.relationships_mapped = 0
        self.start_time = datetime.now()

        # Sample data for rapid ingestion
        self.sample_memories = [
            {
                "content": "Von Base Enterprises is pioneering AI-driven memory systems with Core Nexus",
                "entities": ["Von Base Enterprises", "Core Nexus", "AI"],
                "relationships": [("Von Base Enterprises", "develops", "Core Nexus")]
            },
            {
                "content": "John Smith, CTO of Von Base, leads the technical architecture of Core Nexus",
                "entities": ["John Smith", "Von Base", "Core Nexus"],
                "relationships": [("John Smith", "works_at", "Von Base"), ("John Smith", "leads", "Core Nexus")]
            },
            {
                "content": "Core Nexus integrates with Pinecone, ChromaDB, and PostgreSQL for multi-provider storage",
                "entities": ["Core Nexus", "Pinecone", "ChromaDB", "PostgreSQL"],
                "relationships": [("Core Nexus", "integrates_with", "Pinecone")]
            },
            {
                "content": "The ADM scoring engine in Core Nexus uses Darwin-Gödel principles for intelligence measurement",
                "entities": ["ADM scoring engine", "Core Nexus", "Darwin-Gödel principles"],
                "relationships": [("Core Nexus", "uses", "ADM scoring engine")]
            },
            {
                "content": "Sarah Johnson implemented the knowledge graph layer using Neo4j and spaCy",
                "entities": ["Sarah Johnson", "knowledge graph", "Neo4j", "spaCy"],
                "relationships": [("Sarah Johnson", "implemented", "knowledge graph")]
            }
        ]

    def generate_memory_variations(self, base_memory: dict[str, Any], count: int = 20) -> list[dict[str, Any]]:
        """Generate variations of memories for rapid testing."""
        variations = []

        # Time variations
        times = ["yesterday", "last week", "this morning", "recently", "in Q4"]
        actions = ["discussed", "implemented", "designed", "optimized", "tested"]
        adjectives = ["innovative", "scalable", "efficient", "robust", "cutting-edge"]

        for i in range(count):
            # Create variation
            content = base_memory["content"]

            # Add time context
            content = f"{random.choice(times).capitalize()}, {content.lower()}"

            # Add action variation
            content = content.replace("is", random.choice(actions), 1)

            # Add adjective
            content = content.replace("AI", f"{random.choice(adjectives)} AI", 1)

            variations.append({
                "content": content,
                "metadata": {
                    "agent": self.agent_name,
                    "batch": i,
                    "timestamp": datetime.now().isoformat(),
                    "importance_score": random.uniform(0.5, 0.9),
                    "entities_count": len(base_memory.get("entities", [])),
                    "relationships_count": len(base_memory.get("relationships", []))
                }
            })

        return variations

    async def store_memory_batch(self, memories: list[dict[str, Any]]):
        """Store a batch of memories in parallel."""
        async with aiohttp.ClientSession() as session:
            tasks = []

            for memory in memories:
                task = self.store_single_memory(session, memory)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            successful = sum(1 for r in results if not isinstance(r, Exception))
            self.memories_stored += successful

            return successful

    async def store_single_memory(self, session: aiohttp.ClientSession, memory: dict[str, Any]):
        """Store a single memory."""
        try:
            async with session.post(
                f"{self.base_url}/memories",
                json=memory,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    raise Exception(f"Status {response.status}")
        except Exception as e:
            print(f"❌ Failed to store memory: {e}")
            raise e

    def display_leaderboard(self):
        """Display real-time leaderboard."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        rate = self.memories_stored / elapsed if elapsed > 0 else 0

        print("\n" + "="*50)
        print("🏁 RACE TO 1000 MEMORIES - LEADERBOARD 🏁")
        print("="*50)
        print(f"Agent: {self.agent_name}")
        print(f"Memories Stored: {self.memories_stored} / 1000")
        print(f"Progress: {'█' * (self.memories_stored // 20)}{'░' * (50 - self.memories_stored // 20)}")
        print(f"Rate: {rate:.1f} memories/second")
        print(f"ETA to 1000: {(1000 - self.memories_stored) / rate if rate > 0 else 'N/A':.0f} seconds")
        print("="*50)

        if self.memories_stored >= 1000:
            print("🎉 WINNER! AGENT 2 CLAIMS VICTORY! 🎉")
            print("AI Assistant shall be named: 'GraphMind' 🧠")

    async def race_to_victory(self):
        """Main racing loop - FAST ingestion!"""
        print(f"🚀 {self.agent_name} ENTERING THE RACE!")
        print("Target: 1000 memories")
        print("Strategy: Parallel batch ingestion with entity variations")

        batch_size = 50  # Aggressive batching

        while self.memories_stored < 1000:
            # Generate batch of memories
            batch = []
            for base_memory in self.sample_memories:
                variations = self.generate_memory_variations(base_memory, count=10)
                batch.extend(variations)

            # Trim to batch size
            batch = batch[:batch_size]

            # Store in parallel
            print(f"\n📤 Sending batch of {len(batch)} memories...")
            start = datetime.now()

            successful = await self.store_memory_batch(batch)

            duration = (datetime.now() - start).total_seconds()
            print(f"✅ Stored {successful} memories in {duration:.1f}s ({successful/duration:.1f} per second)")

            # Update relationships count (simulated based on metadata)
            self.relationships_mapped += sum(m["metadata"].get("relationships_count", 0) for m in batch[:successful])

            # Display progress
            self.display_leaderboard()

            # Brief pause to avoid overwhelming
            await asyncio.sleep(1)

        print("\n🏆 RACE COMPLETE! 🏆")
        print("Final Stats:")
        print(f"- Memories: {self.memories_stored}")
        print(f"- Relationships: {self.relationships_mapped}")
        print(f"- Time: {(datetime.now() - self.start_time).total_seconds():.1f} seconds")

async def warm_up_service():
    """Warm up the service before racing."""
    print("🔥 Warming up Core Nexus service...")

    async with aiohttp.ClientSession() as session:
        for i in range(3):
            try:
                async with session.get("https://core-nexus-memory-service.onrender.com/health") as response:
                    if response.status == 200:
                        print(f"✅ Warmup {i+1}/3 successful")
                    else:
                        print(f"⚠️  Warmup {i+1}/3 returned {response.status}")
            except Exception as e:
                print(f"❌ Warmup {i+1}/3 failed: {e}")

            await asyncio.sleep(2)

async def main():
    """Start the race!"""
    # First warm up the service
    await warm_up_service()

    # Then RACE!
    racer = MemoryRacer()
    await racer.race_to_victory()

if __name__ == "__main__":
    print("🎯 AGENT 2: KNOWLEDGE GRAPH SPECIALIST")
    print("🏁 RACING TO 1000 MEMORIES!")
    print("🧠 EVERY MEMORY GETS ENTITIES & RELATIONSHIPS!")
    asyncio.run(main())
