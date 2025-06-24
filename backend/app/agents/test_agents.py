"""
Test agents for development and testing purposes.
"""
from typing import Dict, Any
from ..agents.base import BaseAgent


class EchoAgent(BaseAgent):
    """Simple agent that echoes the user request."""
    
    def __init__(self):
        super().__init__(
            name="EchoAgent",
            description="Echoes the user request for testing"
        )
    
    async def _execute_impl(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Echo the user request."""
        user_request = state.get("user_request", "No request provided")
        
        # Add a message
        self._add_system_message(state, f"Echo: {user_request}")
        
        # Mark as complete
        return self.complete_and_stop()


class SequentialTestAgent(BaseAgent):
    """Test agent that hands off to the next agent in sequence."""
    
    def __init__(self, name: str, next_agent: str):
        super().__init__(
            name=name,
            description=f"Test agent that hands off to {next_agent}"
        )
        self.next_agent_name = next_agent
    
    async def _execute_impl(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process and hand off to next agent."""
        # Add a message
        self._add_system_message(state, f"{self.name} processed the request")
        
        # Hand off to next agent
        return self.hand_off_to(self.next_agent_name)
