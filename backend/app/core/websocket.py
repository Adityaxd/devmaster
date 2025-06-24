"""
WebSocket connection manager for real-time agent updates
"""
from typing import List, Dict, Any
from fastapi import WebSocket
import json
import logging
from datetime import datetime


logger = logging.getLogger("devmaster.websocket")


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates.
    
    This allows the frontend to receive live updates about:
    - Agent status changes
    - Project progress
    - Validation results
    - Error messages
    """
    
    def __init__(self):
        """Initialize the connection manager."""
        self.active_connections: List[WebSocket] = []
        self.project_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, project_id: str = None):
        """
        Accept a new WebSocket connection.
        
        Args:
            websocket: The WebSocket connection
            project_id: Optional project ID to subscribe to specific updates
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        
        if project_id:
            if project_id not in self.project_connections:
                self.project_connections[project_id] = []
            self.project_connections[project_id].append(websocket)
        
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection.
        
        Args:
            websocket: The WebSocket connection to remove
        """
        self.active_connections.remove(websocket)
        
        # Remove from project-specific connections
        for project_id, connections in self.project_connections.items():
            if websocket in connections:
                connections.remove(websocket)
        
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """
        Send a message to a specific WebSocket connection.
        
        Args:
            message: The message to send
            websocket: The target WebSocket
        """
        await websocket.send_text(message)
    
    async def broadcast(self, message: Dict[str, Any]):
        """
        Broadcast a message to all connected clients.
        
        Args:
            message: The message dictionary to broadcast
        """
        message_str = json.dumps({
            **message,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)
    
    async def broadcast_to_project(self, project_id: str, message: Dict[str, Any]):
        """
        Broadcast a message to all clients connected to a specific project.
        
        Args:
            project_id: The project ID
            message: The message dictionary to broadcast
        """
        if project_id not in self.project_connections:
            return
        
        message_str = json.dumps({
            **message,
            "project_id": project_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        disconnected = []
        for connection in self.project_connections[project_id]:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"Error sending message to project {project_id}: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)


# Global connection manager instance
manager = ConnectionManager()