#!/usr/bin/env python3
"""
Core Nexus Memory Service Client Library
Simple client for agents to integrate with the deployed memory service.
"""

import json
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass

@dataclass
class MemoryResult:
    """Result from memory operations"""
    id: str
    content: str
    metadata: Dict[str, Any]
    importance_score: float
    similarity_score: Optional[float] = None
    created_at: Optional[str] = None

@dataclass
class QueryResult:
    """Result from memory queries"""
    memories: List[MemoryResult]
    total_found: int
    query_time_ms: float
    providers_used: List[str]

class CoreNexusClient:
    """
    Client for Core Nexus Memory Service
    
    Provides simple methods for agents to:
    - Store memories
    - Query memories  
    - Check service health
    - Get statistics
    """
    
    def __init__(self, base_url: str = "https://core-nexus-memory-service.onrender.com", timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self._session_id = f"agent_{int(time.time())}"
    
    def _make_request(self, endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to the service"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if data:
                data_bytes = json.dumps(data).encode('utf-8')
                req = urllib.request.Request(url, data=data_bytes, headers={
                    'Content-Type': 'application/json',
                    'User-Agent': f'CoreNexusClient/{self._session_id}'
                })
            else:
                req = urllib.request.Request(url, headers={
                    'User-Agent': f'CoreNexusClient/{self._session_id}'
                })
            
            if method != "GET":
                req.get_method = lambda: method
            
            response = urllib.request.urlopen(req, timeout=self.timeout)
            response_data = response.read().decode('utf-8')
            
            return {
                "success": True,
                "status_code": response.getcode(),
                "data": json.loads(response_data) if response_data else {}
            }
            
        except urllib.error.HTTPError as e:
            error_data = {}
            try:
                error_data = json.loads(e.read().decode('utf-8'))
            except:
                pass
            
            raise CoreNexusError(f"HTTP {e.code}: {e.reason}", e.code, error_data)
        except urllib.error.URLError as e:
            raise CoreNexusError(f"Connection error: {e.reason}")
        except Exception as e:
            raise CoreNexusError(f"Request failed: {str(e)}")
    
    def is_healthy(self) -> bool:
        """Check if the service is healthy and responsive"""
        try:
            result = self._make_request("/health")
            health_data = result["data"]
            return health_data.get("status") == "healthy"
        except:
            return False
    
    def get_health_details(self) -> Dict[str, Any]:
        """Get detailed health information"""
        result = self._make_request("/health")
        return result["data"]
    
    def store_memory(self, content: str, metadata: Optional[Dict[str, Any]] = None, 
                    importance_score: Optional[float] = None, user_id: Optional[str] = None,
                    conversation_id: Optional[str] = None) -> MemoryResult:
        """
        Store a memory in the service
        
        Args:
            content: The text content to store
            metadata: Additional metadata (optional)
            importance_score: Manual importance score 0-1 (optional)
            user_id: User identifier (optional)
            conversation_id: Conversation identifier (optional)
            
        Returns:
            MemoryResult with the stored memory details
        """
        payload = {
            "content": content,
            "metadata": metadata or {},
        }
        
        if importance_score is not None:
            payload["importance_score"] = importance_score
        if user_id:
            payload["user_id"] = user_id
        if conversation_id:
            payload["conversation_id"] = conversation_id
        
        result = self._make_request("/memories", method="POST", data=payload)
        memory_data = result["data"]
        
        return MemoryResult(
            id=memory_data["id"],
            content=memory_data["content"],
            metadata=memory_data.get("metadata", {}),
            importance_score=memory_data.get("importance_score", 0.5),
            created_at=memory_data.get("created_at")
        )
    
    def query_memories(self, query: str, limit: int = 10, min_similarity: float = 0.3,
                      filters: Optional[Dict[str, Any]] = None, user_id: Optional[str] = None,
                      conversation_id: Optional[str] = None) -> QueryResult:
        """
        Query memories using natural language
        
        Args:
            query: Natural language query
            limit: Maximum number of results (1-100)
            min_similarity: Minimum similarity threshold (0-1)
            filters: Additional metadata filters (optional)
            user_id: Filter by user (optional)
            conversation_id: Filter by conversation (optional)
            
        Returns:
            QueryResult with matching memories
        """
        payload = {
            "query": query,
            "limit": min(max(limit, 1), 100),
            "min_similarity": max(min(min_similarity, 1.0), 0.0),
        }
        
        if filters:
            payload["filters"] = filters
        if user_id:
            payload["user_id"] = user_id
        if conversation_id:
            payload["conversation_id"] = conversation_id
        
        result = self._make_request("/memories/query", method="POST", data=payload)
        query_data = result["data"]
        
        memories = []
        for mem in query_data.get("memories", []):
            memories.append(MemoryResult(
                id=mem["id"],
                content=mem["content"],
                metadata=mem.get("metadata", {}),
                importance_score=mem.get("importance_score", 0.5),
                similarity_score=mem.get("similarity_score"),
                created_at=mem.get("created_at")
            ))
        
        return QueryResult(
            memories=memories,
            total_found=query_data.get("total_found", 0),
            query_time_ms=query_data.get("query_time_ms", 0),
            providers_used=query_data.get("providers_used", [])
        )
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory service statistics"""
        result = self._make_request("/memories/stats")
        return result["data"]
    
    def get_providers(self) -> Dict[str, Any]:
        """Get information about available vector providers"""
        result = self._make_request("/providers")
        return result["data"]
    
    def wait_for_service(self, max_wait_seconds: int = 300, check_interval: int = 10) -> bool:
        """
        Wait for the service to become healthy (useful for cold starts)
        
        Args:
            max_wait_seconds: Maximum time to wait
            check_interval: Seconds between health checks
            
        Returns:
            True if service becomes healthy, False if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait_seconds:
            if self.is_healthy():
                return True
            time.sleep(check_interval)
        
        return False

class CoreNexusError(Exception):
    """Exception raised by Core Nexus operations"""
    
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}

# Convenience functions for quick usage
def create_client(service_url: str = "https://core-nexus-memory-service.onrender.com") -> CoreNexusClient:
    """Create a new Core Nexus client"""
    return CoreNexusClient(service_url)

def store_memory(content: str, metadata: Optional[Dict[str, Any]] = None, **kwargs) -> MemoryResult:
    """Quick function to store a memory"""
    client = create_client()
    return client.store_memory(content, metadata, **kwargs)

def query_memories(query: str, limit: int = 10, **kwargs) -> QueryResult:
    """Quick function to query memories"""
    client = create_client()
    return client.query_memories(query, limit, **kwargs)

def is_service_healthy() -> bool:
    """Quick function to check service health"""
    client = create_client()
    return client.is_healthy()

# Example usage for agents
if __name__ == "__main__":
    print("🤖 Core Nexus Client Library - Example Usage")
    print("=" * 50)
    
    # Create client
    client = create_client()
    
    # Check if service is healthy
    print("🏥 Checking service health...")
    if client.is_healthy():
        print("✅ Service is healthy!")
        
        # Get health details
        health = client.get_health_details()
        print(f"   Total memories: {health.get('total_memories', 0)}")
        print(f"   Uptime: {health.get('uptime_seconds', 0):.0f}s")
        
        # Store a test memory
        print("\n💾 Storing test memory...")
        memory = client.store_memory(
            content="This is a test memory from the Core Nexus client library",
            metadata={"test": True, "agent": "example"}
        )
        print(f"✅ Memory stored with ID: {memory.id}")
        
        # Query memories
        print("\n🔍 Querying memories...")
        results = client.query_memories("test memory", limit=5)
        print(f"✅ Found {len(results.memories)} memories in {results.query_time_ms:.2f}ms")
        
        for i, mem in enumerate(results.memories):
            print(f"   {i+1}. {mem.content[:50]}... (score: {mem.similarity_score:.3f})")
    
    else:
        print("❌ Service is not healthy (may be starting up)")
        print("💡 Try waiting a few minutes for the service to fully start")
        
        # Example of waiting for service
        print("\n⏳ Waiting for service to become healthy...")
        if client.wait_for_service(max_wait_seconds=60, check_interval=5):
            print("✅ Service is now healthy!")
        else:
            print("⚠️ Service did not become healthy within timeout")
    
    print("\n📚 For more information, see: https://core-nexus-memory-service.onrender.com/docs")