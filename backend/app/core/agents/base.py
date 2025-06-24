"""
Base Agent Infrastructure
Provides the foundation for all specialist agents in the DevMaster system
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import traceback

from ..state import DevMasterState, AgentStatus, Message


class BaseAgent(ABC):
    """
    Abstract base class for all DevMaster agents.
    
    Following the Tech Bible principles:
    - All agents operate on the shared DevMasterState
    - Agent handoffs are done by updating the active_agent field
    - No direct message passing between agents
    """
    
    def __init__(self, name: str, description: str):
        """
        Initialize the base agent.
        
        Args:
            name: Unique name of the agent
            description: Human-readable description of the agent's purpose
        """
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"devmaster.agents.{name}")
        self.status = AgentStatus.IDLE    
    async def execute(self, state: DevMasterState) -> Dict[str, Any]:
        """
        Execute the agent's main logic.
        
        This method handles:
        1. Pre-execution setup
        2. Error handling and recovery
        3. State updates
        4. Post-execution cleanup
        
        Args:
            state: The current DevMaster state
            
        Returns:
            Dict containing the updated state fields
        """
        self.logger.info(f"Agent {self.name} starting execution")
        self.status = AgentStatus.RUNNING
        
        # Record agent execution in history
        execution_record = {
            "agent": self.name,
            "started_at": datetime.utcnow(),
            "status": "running"
        }
        
        try:
            # Add system message about agent activation
            self._add_system_message(
                state, 
                f"Agent '{self.name}' activated: {self.description}"
            )
            
            # Execute the agent's specific logic
            result = await self._execute_impl(state)
            
            # Update execution record
            execution_record["completed_at"] = datetime.utcnow()
            execution_record["status"] = "completed"
            
            self.status = AgentStatus.COMPLETED
            self.logger.info(f"Agent {self.name} completed successfully")
            
            return result
            
        except Exception as e:
            # Log the error
            self.logger.error(f"Agent {self.name} failed: {str(e)}")
            self.logger.error(traceback.format_exc())
            
            # Update execution record
            execution_record["completed_at"] = datetime.utcnow()
            execution_record["status"] = "failed"
            execution_record["error"] = str(e)
            
            self.status = AgentStatus.FAILED
            
            # Handle the error according to our philosophy
            return self._handle_error(state, e)    
    @abstractmethod
    async def _execute_impl(self, state: DevMasterState) -> Dict[str, Any]:
        """
        The actual implementation of the agent's logic.
        
        This method should:
        1. Read necessary information from the state
        2. Perform its specific task
        3. Return a dictionary of state updates
        
        Must be implemented by all concrete agents.
        
        Args:
            state: The current DevMaster state
            
        Returns:
            Dict containing state fields to update
        """
        pass
    
    def _handle_error(self, state: DevMasterState, error: Exception) -> Dict[str, Any]:
        """
        Handle errors according to the DevMaster error philosophy.
        
        Args:
            state: The current state
            error: The exception that occurred
            
        Returns:
            Dict containing error state updates
        """
        error_count = state.get("error_count", 0) + 1
        error_messages = state.get("error_messages", [])
        error_messages.append(f"{self.name}: {str(error)}")
        
        # Determine next action based on error count
        if error_count < 3:
            # Retry with the same agent
            return {
                "error_count": error_count,
                "error_messages": error_messages,
                "active_agent": self.name  # Retry same agent
            }
        else:
            # Too many errors, requires human intervention
            return {
                "error_count": error_count,
                "error_messages": error_messages,
                "project_status": "error_requires_human_input",
                "active_agent": "Done"
            }    
    def _add_system_message(self, state: DevMasterState, content: str) -> None:
        """
        Add a system message to the conversation.
        
        Args:
            state: The current state
            content: The message content
        """
        message: Message = {
            "id": f"msg_{datetime.utcnow().timestamp()}",
            "role": "system",
            "content": content,
            "timestamp": datetime.utcnow(),
            "agent_name": self.name,
            "metadata": {}
        }
        state["messages"].append(message)
    
    def hand_off_to(self, agent_name: str) -> Dict[str, Any]:
        """
        Hand off control to another agent.
        
        This is the ONLY way agents should transfer control,
        following the LangGraph pattern.
        
        Args:
            agent_name: Name of the agent to hand off to
            
        Returns:
            Dict with active_agent update
        """
        self.logger.info(f"Handing off from {self.name} to {agent_name}")
        return {"active_agent": agent_name}
    
    def complete_and_stop(self) -> Dict[str, Any]:
        """
        Mark the workflow as complete and stop execution.
        
        Returns:
            Dict with completion status
        """
        return {
            "active_agent": "Done",
            "project_status": "completed"
        }