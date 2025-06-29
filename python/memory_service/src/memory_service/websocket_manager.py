"""
WebSocket Manager for Real-Time Agent Coordination

Provides real-time bidirectional communication between agents and the coordination engine,
enabling instant notifications, live status updates, and collaborative workflows.
"""

import asyncio
import json
import logging
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from .models import CoordinationMessage, AgentActivity

logger = logging.getLogger(__name__)


class WebSocketMessage(BaseModel):
    """Standard message format for WebSocket communication."""
    
    type: str  # message_type
    agent_id: str
    target_agent_id: Optional[str] = None  # None for broadcast
    data: Dict[str, Any]
    timestamp: datetime
    message_id: str


class AgentConnection(BaseModel):
    """Agent WebSocket connection info."""
    
    model_config = {"arbitrary_types_allowed": True}
    
    agent_id: str
    websocket: WebSocket
    connected_at: datetime
    last_ping: datetime
    agent_type: Optional[str] = None
    workspace: Optional[str] = None


class WebSocketManager:
    """
    Real-time WebSocket communication manager for agent coordination.
    
    Features:
    - Real-time bidirectional messaging
    - Agent presence management
    - Message broadcasting and direct messaging
    - Connection health monitoring
    - Message queuing for offline agents
    """

    def __init__(self, coordination_engine=None):
        self.coordination_engine = coordination_engine
        
        # Active WebSocket connections
        self.active_connections: Dict[str, AgentConnection] = {}
        self.connections_by_type: Dict[str, Set[str]] = defaultdict(set)
        self.connections_by_workspace: Dict[str, Set[str]] = defaultdict(set)
        
        # Message queuing for offline agents
        self.message_queue: Dict[str, List[WebSocketMessage]] = defaultdict(list)
        self.max_queue_size = 100
        
        # Connection health monitoring
        self.ping_interval = 30  # seconds
        self.connection_timeout = 60  # seconds
        
        # Message statistics
        self.message_stats = {
            'total_sent': 0,
            'total_received': 0,
            'broadcasts_sent': 0,
            'direct_messages_sent': 0,
            'connection_events': 0
        }
        
        logger.info("WebSocket Manager initialized")

    async def connect_agent(self, websocket: WebSocket, agent_id: str, agent_type: str = None, workspace: str = None) -> bool:
        """Accept and register a new agent WebSocket connection."""
        try:
            # Accept the WebSocket connection
            await websocket.accept()
            
            # Create connection record
            connection = AgentConnection(
                agent_id=agent_id,
                websocket=websocket,
                connected_at=datetime.utcnow(),
                last_ping=datetime.utcnow(),
                agent_type=agent_type,
                workspace=workspace
            )
            
            # Store connection
            self.active_connections[agent_id] = connection
            
            # Index by type and workspace
            if agent_type:
                self.connections_by_type[agent_type].add(agent_id)
            if workspace:
                self.connections_by_workspace[workspace].add(agent_id)
            
            # Send queued messages
            await self._deliver_queued_messages(agent_id)
            
            # Notify coordination engine of agent connection
            if self.coordination_engine:
                await self.coordination_engine.update_agent_activity(
                    agent_id, 
                    {"status": "online", "last_seen": datetime.utcnow()}
                )
            
            # Broadcast agent connection to other agents
            await self.broadcast_message(
                "agent_connected",
                {
                    "agent_id": agent_id,
                    "agent_type": agent_type,
                    "workspace": workspace,
                    "connected_at": connection.connected_at.isoformat()
                },
                exclude_agent=agent_id
            )
            
            self.message_stats['connection_events'] += 1
            logger.info(f"Agent {agent_id} connected via WebSocket ({agent_type} in {workspace})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect agent {agent_id}: {e}")
            return False

    async def disconnect_agent(self, agent_id: str, reason: str = "normal"):
        """Disconnect and cleanup agent WebSocket connection."""
        try:
            if agent_id not in self.active_connections:
                return
            
            connection = self.active_connections[agent_id]
            
            # Remove from indexes
            if connection.agent_type:
                self.connections_by_type[connection.agent_type].discard(agent_id)
            if connection.workspace:
                self.connections_by_workspace[connection.workspace].discard(agent_id)
            
            # Remove connection
            del self.active_connections[agent_id]
            
            # Notify coordination engine
            if self.coordination_engine:
                await self.coordination_engine.update_agent_activity(
                    agent_id,
                    {"status": "offline", "last_seen": datetime.utcnow()}
                )
            
            # Broadcast disconnection to other agents
            await self.broadcast_message(
                "agent_disconnected",
                {
                    "agent_id": agent_id,
                    "reason": reason,
                    "disconnected_at": datetime.utcnow().isoformat()
                },
                exclude_agent=agent_id
            )
            
            self.message_stats['connection_events'] += 1
            logger.info(f"Agent {agent_id} disconnected: {reason}")
            
        except Exception as e:
            logger.error(f"Error disconnecting agent {agent_id}: {e}")

    async def send_message(self, target_agent_id: str, message_type: str, data: Dict[str, Any], from_agent_id: str = "coordination_engine") -> bool:
        """Send a direct message to a specific agent."""
        try:
            message = WebSocketMessage(
                type=message_type,
                agent_id=from_agent_id,
                target_agent_id=target_agent_id,
                data=data,
                timestamp=datetime.utcnow(),
                message_id=str(uuid4())
            )
            
            # If agent is connected, send immediately
            if target_agent_id in self.active_connections:
                connection = self.active_connections[target_agent_id]
                await connection.websocket.send_text(message.json())
                self.message_stats['direct_messages_sent'] += 1
                self.message_stats['total_sent'] += 1
                logger.debug(f"Sent direct message to {target_agent_id}: {message_type}")
                return True
            else:
                # Queue message for when agent comes online
                await self._queue_message(target_agent_id, message)
                logger.debug(f"Queued message for offline agent {target_agent_id}: {message_type}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send message to {target_agent_id}: {e}")
            return False

    async def broadcast_message(self, message_type: str, data: Dict[str, Any], from_agent_id: str = "coordination_engine", exclude_agent: str = None, target_workspace: str = None, target_agent_type: str = None) -> int:
        """Broadcast a message to multiple agents with filtering options."""
        try:
            message = WebSocketMessage(
                type=message_type,
                agent_id=from_agent_id,
                target_agent_id=None,  # Broadcast
                data=data,
                timestamp=datetime.utcnow(),
                message_id=str(uuid4())
            )
            
            # Determine target agents
            target_agents = set()
            
            if target_workspace:
                target_agents.update(self.connections_by_workspace.get(target_workspace, set()))
            elif target_agent_type:
                target_agents.update(self.connections_by_type.get(target_agent_type, set()))
            else:
                target_agents.update(self.active_connections.keys())
            
            # Exclude specific agent if requested
            if exclude_agent:
                target_agents.discard(exclude_agent)
            
            # Send to all target agents
            sent_count = 0
            failed_agents = []
            
            for agent_id in target_agents:
                try:
                    if agent_id in self.active_connections:
                        connection = self.active_connections[agent_id]
                        await connection.websocket.send_text(message.json())
                        sent_count += 1
                except Exception as e:
                    logger.warning(f"Failed to send broadcast to {agent_id}: {e}")
                    failed_agents.append(agent_id)
            
            # Update statistics
            self.message_stats['broadcasts_sent'] += 1
            self.message_stats['total_sent'] += sent_count
            
            logger.debug(f"Broadcast {message_type} to {sent_count} agents (failed: {len(failed_agents)})")
            return sent_count
            
        except Exception as e:
            logger.error(f"Failed to broadcast message: {e}")
            return 0

    async def handle_agent_message(self, agent_id: str, message_data: Dict[str, Any]):
        """Process incoming message from an agent."""
        try:
            message_type = message_data.get('type', 'unknown')
            data = message_data.get('data', {})
            
            # Update connection activity
            if agent_id in self.active_connections:
                self.active_connections[agent_id].last_ping = datetime.utcnow()
            
            self.message_stats['total_received'] += 1
            
            # Handle different message types
            if message_type == 'ping':
                await self._handle_ping(agent_id)
            elif message_type == 'activity_update':
                await self._handle_activity_update(agent_id, data)
            elif message_type == 'direct_message':
                await self._handle_direct_message(agent_id, data)
            elif message_type == 'task_update':
                await self._handle_task_update(agent_id, data)
            elif message_type == 'conflict_report':
                await self._handle_conflict_report(agent_id, data)
            elif message_type == 'handoff_response':
                await self._handle_handoff_response(agent_id, data)
            else:
                logger.warning(f"Unknown message type from {agent_id}: {message_type}")
                
        except Exception as e:
            logger.error(f"Error handling message from {agent_id}: {e}")

    async def get_connection_status(self) -> Dict[str, Any]:
        """Get current WebSocket connection status and statistics."""
        try:
            # Count connections by type and workspace
            connections_by_type = {
                agent_type: len(agent_ids) 
                for agent_type, agent_ids in self.connections_by_type.items()
            }
            
            connections_by_workspace = {
                workspace: len(agent_ids)
                for workspace, agent_ids in self.connections_by_workspace.items()
            }
            
            # Calculate connection health
            now = datetime.utcnow()
            stale_connections = [
                agent_id for agent_id, conn in self.active_connections.items()
                if (now - conn.last_ping).total_seconds() > self.connection_timeout
            ]
            
            return {
                "total_connections": len(self.active_connections),
                "connections_by_type": connections_by_type,
                "connections_by_workspace": connections_by_workspace,
                "stale_connections": len(stale_connections),
                "queued_messages": sum(len(queue) for queue in self.message_queue.values()),
                "message_statistics": self.message_stats,
                "connection_health": "healthy" if len(stale_connections) == 0 else "degraded"
            }
            
        except Exception as e:
            logger.error(f"Error getting connection status: {e}")
            return {"error": str(e)}

    async def cleanup_stale_connections(self):
        """Clean up stale WebSocket connections that haven't pinged recently."""
        try:
            now = datetime.utcnow()
            stale_agents = []
            
            for agent_id, connection in self.active_connections.items():
                if (now - connection.last_ping).total_seconds() > self.connection_timeout:
                    stale_agents.append(agent_id)
            
            for agent_id in stale_agents:
                await self.disconnect_agent(agent_id, "timeout")
                
            if stale_agents:
                logger.info(f"Cleaned up {len(stale_agents)} stale connections")
                
        except Exception as e:
            logger.error(f"Error cleaning up stale connections: {e}")

    # Private helper methods

    async def _deliver_queued_messages(self, agent_id: str):
        """Deliver queued messages when agent comes online."""
        try:
            if agent_id not in self.message_queue:
                return
            
            connection = self.active_connections.get(agent_id)
            if not connection:
                return
            
            queued_messages = self.message_queue[agent_id]
            delivered = 0
            
            for message in queued_messages:
                try:
                    await connection.websocket.send_text(message.json())
                    delivered += 1
                except Exception as e:
                    logger.warning(f"Failed to deliver queued message to {agent_id}: {e}")
                    break
            
            # Clear delivered messages
            del self.message_queue[agent_id]
            
            if delivered > 0:
                logger.info(f"Delivered {delivered} queued messages to {agent_id}")
                
        except Exception as e:
            logger.error(f"Error delivering queued messages to {agent_id}: {e}")

    async def _queue_message(self, agent_id: str, message: WebSocketMessage):
        """Queue a message for an offline agent."""
        try:
            queue = self.message_queue[agent_id]
            queue.append(message)
            
            # Limit queue size
            if len(queue) > self.max_queue_size:
                queue.pop(0)  # Remove oldest message
                
        except Exception as e:
            logger.error(f"Error queuing message for {agent_id}: {e}")

    async def _handle_ping(self, agent_id: str):
        """Handle ping message from agent."""
        await self.send_message(agent_id, "pong", {"timestamp": datetime.utcnow().isoformat()})

    async def _handle_activity_update(self, agent_id: str, data: Dict[str, Any]):
        """Handle activity update from agent."""
        if self.coordination_engine:
            await self.coordination_engine.update_agent_activity(agent_id, data)
        
        # Broadcast activity update to interested agents
        await self.broadcast_message(
            "agent_activity_changed",
            {"agent_id": agent_id, "activity": data},
            exclude_agent=agent_id
        )

    async def _handle_direct_message(self, from_agent_id: str, data: Dict[str, Any]):
        """Handle direct message routing between agents."""
        target_agent_id = data.get('target_agent_id')
        message_content = data.get('message', {})
        
        if target_agent_id:
            await self.send_message(
                target_agent_id,
                "direct_message",
                {
                    "from_agent_id": from_agent_id,
                    "message": message_content,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

    async def _handle_task_update(self, agent_id: str, data: Dict[str, Any]):
        """Handle task progress update from agent."""
        # Update coordination engine
        if self.coordination_engine:
            task_id = data.get('task_id')
            progress = data.get('progress', 0.0)
            status = data.get('status', 'in_progress')
            
            # Update task in coordination engine (would need to implement this method)
            # await self.coordination_engine.update_task_progress(task_id, progress, status)
        
        # Broadcast task update
        await self.broadcast_message(
            "task_progress_update",
            {"agent_id": agent_id, "task_update": data}
        )

    async def _handle_conflict_report(self, agent_id: str, data: Dict[str, Any]):
        """Handle conflict report from agent."""
        # Process conflict report through coordination engine
        if self.coordination_engine:
            # Create conflict detection record (would need to implement)
            # await self.coordination_engine.report_conflict(agent_id, data)
            pass
        
        # Notify affected agents
        affected_agents = data.get('affected_agents', [])
        for affected_agent in affected_agents:
            if affected_agent != agent_id:
                await self.send_message(
                    affected_agent,
                    "conflict_notification",
                    {
                        "reported_by": agent_id,
                        "conflict_data": data,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )

    async def _handle_handoff_response(self, agent_id: str, data: Dict[str, Any]):
        """Handle handoff acceptance/rejection from agent."""
        handoff_id = data.get('handoff_id')
        response = data.get('response')  # 'accept' or 'reject'
        from_agent_id = data.get('from_agent_id')
        
        # Notify the agent who initiated the handoff
        if from_agent_id:
            await self.send_message(
                from_agent_id,
                "handoff_response",
                {
                    "handoff_id": handoff_id,
                    "response": response,
                    "responding_agent": agent_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        # Update coordination engine if needed
        if self.coordination_engine and response == 'accept':
            # Mark handoff as accepted (would need to implement)
            # await self.coordination_engine.complete_handoff(handoff_id)
            pass