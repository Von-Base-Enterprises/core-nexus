"""
Core Nexus Memory Bridge
Bidirectional integration between JARVIS and Core Nexus Memory Service
"""

import asyncio
import httpx
import json
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import get_config

logger = structlog.get_logger(__name__)
config = get_config()

@dataclass
class JarvisMemory:
    """JARVIS Memory Object for Core Nexus integration"""
    content: str
    importance_score: float
    metadata: Dict[str, Any]
    memory_id: Optional[str] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        
        # Ensure importance_score is within valid range (0-1)
        self.importance_score = max(0.0, min(1.0, self.importance_score))
        
        # Ensure metadata contains JARVIS-specific fields
        if "source" not in self.metadata:
            self.metadata["source"] = "jarvis"
        if "agent_type" not in self.metadata:
            self.metadata["agent_type"] = "supervisor"
        if "timestamp" not in self.metadata:
            self.metadata["timestamp"] = self.created_at.isoformat()

class CoreNexusBridge:
    """Bridge between JARVIS and Core Nexus Memory Service"""
    
    def __init__(self):
        self.base_url = config.core_nexus_url.rstrip('/')
        self.timeout = config.core_nexus_timeout
        self.client = httpx.AsyncClient(timeout=self.timeout)
        self.logger = logger.bind(component="core_nexus_bridge")
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def health_check(self) -> Dict[str, Any]:
        """Check Core Nexus health status"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error("Core Nexus health check failed", error=str(e))
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_stats(self) -> Dict[str, Any]:
        """Get Core Nexus statistics"""
        try:
            response = await self.client.get(f"{self.base_url}/stats")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error("Failed to get Core Nexus stats", error=str(e))
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def store_memory(self, memory: JarvisMemory) -> Dict[str, Any]:
        """Store a memory in Core Nexus"""
        try:
            payload = {
                "content": memory.content,
                "importance_score": memory.importance_score,
                "metadata": memory.metadata
            }
            
            self.logger.info("Storing JARVIS memory in Core Nexus", 
                           content_preview=memory.content[:100],
                           importance=memory.importance_score)
            
            response = await self.client.post(f"{self.base_url}/memories", json=payload)
            response.raise_for_status()
            result = response.json()
            
            # Update the memory object with the returned ID
            if "id" in result:
                memory.memory_id = result["id"]
            
            return result
            
        except Exception as e:
            self.logger.error("Failed to store memory in Core Nexus", 
                            error=str(e), 
                            memory_content=memory.content[:100])
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def search_memories(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search memories in Core Nexus using semantic search"""
        try:
            params = {"query": query, "limit": limit}
            
            self.logger.info("Searching Core Nexus memories", 
                           query=query, limit=limit)
            
            response = await self.client.get(f"{self.base_url}/memories", params=params)
            response.raise_for_status()
            result = response.json()
            
            memories = result.get("memories", [])
            self.logger.info("Found memories in Core Nexus", 
                           query=query, count=len(memories))
            
            return memories
            
        except Exception as e:
            self.logger.error("Failed to search memories in Core Nexus", 
                            error=str(e), query=query)
            raise
    
    async def get_recent_jarvis_memories(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent JARVIS-specific memories"""
        try:
            # Search for JARVIS-specific memories
            memories = await self.search_memories("source:jarvis", limit=limit)
            
            # Filter and sort by JARVIS metadata
            jarvis_memories = []
            for memory in memories:
                metadata = memory.get("metadata", {})
                if metadata.get("source") == "jarvis":
                    jarvis_memories.append(memory)
            
            # Sort by timestamp (most recent first)
            jarvis_memories.sort(key=lambda x: x.get("metadata", {}).get("timestamp", ""), reverse=True)
            
            return jarvis_memories[:limit]
            
        except Exception as e:
            self.logger.error("Failed to get recent JARVIS memories", error=str(e))
            return []
    
    async def get_contextual_memories(self, context: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get memories relevant to current context"""
        try:
            # Use semantic search to find relevant memories
            memories = await self.search_memories(context, limit=limit)
            
            self.logger.info("Retrieved contextual memories", 
                           context=context[:50], count=len(memories))
            
            return memories
            
        except Exception as e:
            self.logger.error("Failed to get contextual memories", 
                            error=str(e), context=context[:50])
            return []
    
    async def store_jarvis_insight(self, insight: str, importance: float = 0.8, 
                                 agent_type: str = "supervisor", 
                                 additional_metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Store a JARVIS insight or learning experience"""
        metadata = {
            "source": "jarvis",
            "agent_type": agent_type,
            "insight_type": "learning",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if additional_metadata:
            metadata.update(additional_metadata)
        
        memory = JarvisMemory(
            content=insight,
            importance_score=importance,
            metadata=metadata
        )
        
        return await self.store_memory(memory)
    
    async def store_system_analysis(self, analysis: str, metrics: Dict[str, Any], 
                                  importance: float = 0.7) -> Dict[str, Any]:
        """Store system analysis results"""
        metadata = {
            "source": "jarvis", 
            "agent_type": "analysis",
            "analysis_type": "system_performance",
            "metrics": metrics,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        memory = JarvisMemory(
            content=analysis,
            importance_score=importance,
            metadata=metadata
        )
        
        return await self.store_memory(memory)
    
    async def get_system_knowledge(self, topic: str) -> List[Dict[str, Any]]:
        """Get accumulated knowledge about a specific topic"""
        try:
            # Search for topic-specific knowledge
            memories = await self.search_memories(f"{topic} system knowledge", limit=10)
            
            # Filter for high-importance system knowledge
            knowledge_memories = []
            for memory in memories:
                importance = memory.get("importance_score", 0)
                if importance >= 0.6:  # High-importance threshold
                    knowledge_memories.append(memory)
            
            return knowledge_memories
            
        except Exception as e:
            self.logger.error("Failed to get system knowledge", 
                            error=str(e), topic=topic)
            return []

# Global bridge instance for reuse
_bridge_instance: Optional[CoreNexusBridge] = None

async def get_bridge() -> CoreNexusBridge:
    """Get the global Core Nexus bridge instance"""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = CoreNexusBridge()
    return _bridge_instance