"""
Event system for agent communication and UI updates
"""
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from datetime import datetime, timezone
import asyncio
import logging

from .websocket import manager


logger = logging.getLogger("devmaster.events")


class EventType(str, Enum):
    """Types of events in the system."""
    # Agent events
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    AGENT_MESSAGE = "agent_message"
    AGENT_ERROR = "agent_error"
    
    # Project events
    PROJECT_CREATED = "project_created"
    PROJECT_UPDATED = "project_updated"
    PROJECT_COMPLETED = "project_completed"
    PROJECT_FAILED = "project_failed"
    
    # File system events
    PROJECT_FILE_SYSTEM_INITIALIZED = "project_file_system_initialized"
    PROJECT_FILE_CREATED = "project_file_created"
    PROJECT_FILE_UPDATED = "project_file_updated"
    PROJECT_FILE_DELETED = "project_file_deleted"
    PROJECT_SNAPSHOT_CREATED = "project_snapshot_created"
    
    # Artifact events
    ARTIFACT_CREATED = "artifact_created"
    ARTIFACT_UPDATED = "artifact_updated"
    ARTIFACT_VALIDATED = "artifact_validated"
    CODE_GENERATED = "code_generated"
    
    # Validation events
    VALIDATION_STARTED = "validation_started"
    VALIDATION_COMPLETED = "validation_completed"
    VALIDATION_FAILED = "validation_failed"
    
    # Intent classification events
    INTENT_CLASSIFICATION_STARTED = "intent_classification_started"
    INTENT_CLASSIFICATION_COMPLETED = "intent_classification_completed"


class Event:
    """Represents an event in the system."""
    
    def __init__(
        self,
        event_type: EventType,
        project_id: str,
        data: Dict[str, Any],
        agent_name: Optional[str] = None
    ):
        """
        Initialize an event.
        
        Args:
            event_type: The type of event
            project_id: The project this event relates to
            data: Event-specific data
            agent_name: Optional agent that triggered the event
        """
        self.event_type = event_type
        self.project_id = project_id
        self.data = data
        self.agent_name = agent_name
        self.timestamp = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_type": self.event_type,
            "project_id": self.project_id,
            "data": self.data,
            "agent_name": self.agent_name,
            "timestamp": self.timestamp.isoformat()
        }

class EventBus:
    """
    Central event bus for the system.
    
    This follows the Tech Bible principle:
    - Used by the orchestrator to broadcast state changes to the UI
    - NOT used for inter-agent command and control
    """
    
    def __init__(self):
        """Initialize the event bus."""
        self.handlers: Dict[EventType, List[Callable]] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
    
    def subscribe(self, event_type: EventType, handler: Callable):
        """
        Subscribe to an event type.
        
        Args:
            event_type: The event type to subscribe to
            handler: Async function to handle the event
        """
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        logger.info(f"Handler subscribed to {event_type}")
    
    async def publish(self, event: Event):
        """
        Publish an event.
        
        Args:
            event: The event to publish
        """
        await self._queue.put(event)
        
        # Also broadcast to WebSocket clients immediately
        await manager.broadcast_to_project(
            event.project_id,
            {
                "type": "event",
                "event": event.to_dict()
            }
        )
    
    async def emit(self, event_type: EventType, data: Dict[str, Any], project_id: Optional[str] = None):
        """
        Convenience method to emit an event.
        
        Args:
            event_type: The type of event
            data: Event data
            project_id: Optional project ID (extracted from data if not provided)
        """
        if project_id is None:
            project_id = data.get("project_id", "system")
        
        event = Event(
            event_type=event_type,
            project_id=project_id,
            data=data,
            agent_name=data.get("agent")
        )
        
        await self.publish(event)
    
    async def start(self):
        """Start processing events."""
        self._running = True
        logger.info("Event bus started")
        
        while self._running:
            try:
                # Get event from queue with timeout
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                
                # Process event
                await self._process_event(event)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing event: {e}")
    
    async def stop(self):
        """Stop processing events."""
        self._running = False
        logger.info("Event bus stopped")
    
    async def _process_event(self, event: Event):
        """
        Process an event by calling all registered handlers.
        
        Args:
            event: The event to process
        """
        handlers = self.handlers.get(event.event_type, [])
        
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")


# Global event bus instance
event_bus = EventBus()