"""
WebSocket Manager

Manages WebSocket connections for real-time updates.
"""

from typing import Dict, Set, Any
from fastapi import WebSocket
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections."""
    
    def __init__(self):
        # Active connections by project_id
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Connection metadata
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, project_id: str):
        """Accept and register a new connection."""
        await websocket.accept()
        
        if project_id not in self.active_connections:
            self.active_connections[project_id] = set()
        
        self.active_connections[project_id].add(websocket)
        self.connection_info[websocket] = {
            "project_id": project_id,
            "connected_at": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"WebSocket connected for project {project_id}")
        
        # Send welcome message
        await self.send_personal_message(
            {
                "type": "connection",
                "status": "connected",
                "message": "Connected to DevMaster real-time updates",
                "project_id": project_id
            },
            websocket
        )
    
    def disconnect(self, websocket: WebSocket):
        """Remove a connection."""
        if websocket in self.connection_info:
            project_id = self.connection_info[websocket]["project_id"]
            
            if project_id in self.active_connections:
                self.active_connections[project_id].discard(websocket)
                
                # Clean up empty sets
                if not self.active_connections[project_id]:
                    del self.active_connections[project_id]
            
            del self.connection_info[websocket]
            logger.info(f"WebSocket disconnected for project {project_id}")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send a message to a specific connection."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {str(e)}")
            self.disconnect(websocket)
    
    async def broadcast_to_project(self, project_id: str, message: Dict[str, Any]):
        """Broadcast a message to all connections for a project."""
        if project_id in self.active_connections:
            # Add timestamp if not present
            if "timestamp" not in message:
                message["timestamp"] = datetime.now(timezone.utc).isoformat()
            
            # Send to all connections for this project
            disconnected = []
            for connection in self.active_connections[project_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to connection: {str(e)}")
                    disconnected.append(connection)
            
            # Clean up disconnected connections
            for connection in disconnected:
                self.disconnect(connection)


class WebSocketManager:
    """High-level WebSocket management service."""
    
    def __init__(self):
        self.manager = ConnectionManager()
    
    async def handle_connection(self, websocket: WebSocket, project_id: str):
        """Handle a WebSocket connection lifecycle."""
        await self.manager.connect(websocket, project_id)
        
        try:
            while True:
                # Wait for messages from client
                data = await websocket.receive_json()
                
                # Process different message types
                if data.get("type") == "ping":
                    await self.manager.send_personal_message(
                        {"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()},
                        websocket
                    )
                elif data.get("type") == "subscribe":
                    # Handle subscription requests
                    await self._handle_subscription(websocket, data)
                else:
                    # Echo unknown messages back
                    await self.manager.send_personal_message(
                        {
                            "type": "echo",
                            "original": data,
                            "message": "Unknown message type"
                        },
                        websocket
                    )
        
        except Exception as e:
            logger.error(f"WebSocket error: {str(e)}")
        finally:
            self.manager.disconnect(websocket)
    
    async def _handle_subscription(self, websocket: WebSocket, data: Dict[str, Any]):
        """Handle subscription requests."""
        subscription_type = data.get("subscription_type")
        
        if subscription_type == "agent_updates":
            await self.manager.send_personal_message(
                {
                    "type": "subscription_confirmed",
                    "subscription_type": "agent_updates",
                    "message": "You will receive real-time agent execution updates"
                },
                websocket
            )
        elif subscription_type == "file_changes":
            await self.manager.send_personal_message(
                {
                    "type": "subscription_confirmed",
                    "subscription_type": "file_changes",
                    "message": "You will receive real-time file system updates"
                },
                websocket
            )
    
    async def broadcast_to_project(self, project_id: str, message: Dict[str, Any]):
        """Broadcast a message to all connections for a project."""
        await self.manager.broadcast_to_project(project_id, message)
    
    async def send_agent_update(self, project_id: str, agent_name: str, status: str, data: Any = None):
        """Send an agent execution update."""
        message = {
            "type": "agent_update",
            "agent": agent_name,
            "status": status,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.broadcast_to_project(project_id, message)
    
    async def send_file_update(self, project_id: str, operation: str, file_path: str, data: Any = None):
        """Send a file system update."""
        message = {
            "type": "file_update",
            "operation": operation,
            "file_path": file_path,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.broadcast_to_project(project_id, message)
    
    def get_connection_count(self, project_id: str) -> int:
        """Get the number of active connections for a project."""
        return len(self.manager.active_connections.get(project_id, set()))
    
    def get_all_connection_counts(self) -> Dict[str, int]:
        """Get connection counts for all projects."""
        return {
            project_id: len(connections)
            for project_id, connections in self.manager.active_connections.items()
        }


# Global WebSocket manager instance
websocket_manager = WebSocketManager()
