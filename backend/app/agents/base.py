"""
Base agent class for all DevMaster specialist agents.

Following the Tech Bible, all agents inherit from this base class
and operate on the shared DevMasterState.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import logging
import traceback

from pydantic import BaseModel, Field

from app.core.state import DevMasterState, Message, Artifact


class AgentState(str, Enum):
    """Possible states for an agent."""
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"  # Waiting for external resource
    COMPLETED = "completed"
    FAILED = "failed"


class AgentResult(BaseModel):
    """Result returned by an agent after execution."""
    success: bool
    state_updates: Dict[str, Any] = Field(default_factory=dict)
    next_agent: Optional[str] = None
    error: Optional[str] = None
    artifacts_created: List[str] = Field(default_factory=list)
    messages: List[Message] = Field(default_factory=list)


class BaseAgent(ABC):
    """
    Base class for all DevMaster agents.
    
    Each agent:
    1. Receives the full DevMasterState
    2. Performs its specialized task
    3. Updates relevant fields in the state
    4. Returns control to the orchestrator
    """
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.state = AgentState.IDLE
        self.logger = logging.getLogger(f"agent.{name}")
        
    @abstractmethod
    async def execute(self, state: DevMasterState) -> AgentResult:
        """
        Execute the agent's primary task.
        
        Args:
            state: The current DevMaster state
            
        Returns:
            AgentResult containing state updates and control flow information
        """
        pass
    
    async def validate_preconditions(self, state: DevMasterState) -> bool:
        """
        Validate that the agent can execute given the current state.
        Override in subclasses for specific validation.
        """
        return True
    
    async def run(self, state: DevMasterState) -> Dict[str, Any]:
        """
        Main entry point for agent execution with error handling.
        
        Returns a dictionary of state updates to be merged into DevMasterState.
        """
        self.state = AgentState.RUNNING
        self.logger.info(f"Agent {self.name} starting execution")
        
        try:
            # Validate preconditions
            if not await self.validate_preconditions(state):
                raise ValueError(f"Preconditions not met for agent {self.name}")
            
            # Execute agent logic
            result = await self.execute(state)
            
            if result.success:
                self.state = AgentState.COMPLETED
                self.logger.info(f"Agent {self.name} completed successfully")
            else:
                self.state = AgentState.FAILED
                self.logger.error(f"Agent {self.name} failed: {result.error}")
            
            # Prepare state updates
            updates = result.state_updates.copy()
            
            # Add agent to completed list
            completed = state.get("completed_agents", []).copy()
            if self.name not in completed and result.success:
                completed.append(self.name)
                updates["completed_agents"] = completed
            
            # Update active agent
            if result.next_agent:
                updates["active_agent"] = result.next_agent
            
            # Add messages
            if result.messages:
                messages = state.get("messages", []).copy()
                for msg in result.messages:
                    messages.append(msg.model_dump())
                updates["messages"] = messages
            
            # Update last update timestamp
            updates["updated_at"] = datetime.utcnow().isoformat()
            
            # Update agent history
            agent_history = state.get("agent_history", []).copy()
            agent_history.append({
                "agent": self.name,
                "status": "completed" if result.success else "failed",
                "timestamp": datetime.utcnow().isoformat()
            })
            updates["agent_history"] = agent_history
            
            return updates
            
        except Exception as e:
            self.state = AgentState.FAILED
            self.logger.error(f"Agent {self.name} encountered error: {str(e)}")
            self.logger.debug(traceback.format_exc())
            
            # Return error state updates
            error_messages = state.get("error_messages", []).copy()
            error_messages.append(f"[{self.name}] {str(e)}")
            
            # Also update agent history with the error
            agent_history = state.get("agent_history", []).copy()
            agent_history.append({
                "agent": self.name,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return {
                "error_messages": error_messages,
                "error_count": state.get("error_count", 0) + 1,
                "agent_history": agent_history,
                "updated_at": datetime.utcnow().isoformat()
            }
    
    def add_message(self, content: str, role: str = "agent") -> Message:
        """Helper to create a message from this agent."""
        return Message(
            role=role,
            content=content,
            timestamp=datetime.utcnow(),
            agent_name=self.name
        )
    
    def create_artifact(
        self,
        artifact_id: str,
        artifact_type: str,
        path: str,
        content: str,
        language: Optional[str] = None
    ) -> Artifact:
        """Helper to create an artifact."""
        now = datetime.utcnow()
        return Artifact(
            id=artifact_id,
            type=artifact_type,
            path=path,
            content=content,
            language=language,
            created_at=now,
            updated_at=now,
            created_by=self.name
        )
