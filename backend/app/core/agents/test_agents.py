"""
Example test agents for verifying orchestration
"""
from typing import Dict, Any
import asyncio

from .base import BaseAgent
from ..state import DevMasterState


class EchoAgent(BaseAgent):
    """
    Simple test agent that echoes the user request.
    """
    
    def __init__(self):
        super().__init__(
            name="EchoAgent",
            description="Test agent that echoes user input"
        )
    
    async def _execute_impl(self, state: DevMasterState) -> Dict[str, Any]:
        """Echo the user request and complete."""
        user_request = state.get("user_request", "No request provided")
        
        # Simulate some work
        await asyncio.sleep(0.5)
        
        # Add a message
        self._add_system_message(state, f"Echo: {user_request}")
        
        # Complete and stop
        return self.complete_and_stop()


class SequentialTestAgent(BaseAgent):
    """
    Test agent that hands off to another agent.
    """
    
    def __init__(self, name: str, next_agent: str):
        super().__init__(
            name=name,
            description=f"Test agent that hands off to {next_agent}"
        )
        self.next_agent = next_agent
    
    async def _execute_impl(self, state: DevMasterState) -> Dict[str, Any]:
        """Do some work and hand off to next agent."""
        # Simulate some work
        await asyncio.sleep(0.5)
        
        # Add a message
        self._add_system_message(
            state, 
            f"{self.name} completed, handing off to {self.next_agent}"
        )
        
        # Hand off to next agent
        return self.hand_off_to(self.next_agent)