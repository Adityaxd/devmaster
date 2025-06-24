"""
Agent registry for managing and discovering available agents.

This module provides a centralized registry for all specialist agents
in the DevMaster system.
"""

from typing import Dict, Type, Optional, List
import logging

from .base import BaseAgent


class AgentRegistry:
    """
    Centralized registry for all DevMaster agents.
    
    Agents must be registered here to be available for orchestration.
    """
    
    def __init__(self):
        self._agents: Dict[str, Type[BaseAgent]] = {}
        self._instances: Dict[str, BaseAgent] = {}
        self.logger = logging.getLogger("agent.registry")
    
    def register(self, name: str, agent_class: Type[BaseAgent]) -> None:
        """
        Register an agent class with the registry.
        
        Args:
            name: Unique name for the agent
            agent_class: The agent class (not instance)
        """
        if name in self._agents:
            raise ValueError(f"Agent {name} already registered")
        
        if not issubclass(agent_class, BaseAgent):
            raise TypeError(f"Agent class must inherit from BaseAgent")
        
        self._agents[name] = agent_class
        self.logger.info(f"Registered agent: {name}")
    
    def get_agent_class(self, name: str) -> Optional[Type[BaseAgent]]:
        """Get an agent class by name."""
        return self._agents.get(name)
    
    def get_agent_instance(self, name: str, **kwargs) -> Optional[BaseAgent]:
        """
        Get or create an agent instance.
        
        Instances are cached for reuse within a session.
        """
        if name not in self._agents:
            self.logger.error(f"Agent {name} not found in registry")
            return None
        
        if name not in self._instances:
            agent_class = self._agents[name]
            self._instances[name] = agent_class(name=name, **kwargs)
            self.logger.debug(f"Created agent instance: {name}")
        
        return self._instances[name]
    
    def list_agents(self) -> List[str]:
        """Get a list of all registered agent names."""
        return list(self._agents.keys())
    
    def clear_instances(self) -> None:
        """Clear all cached agent instances."""
        self._instances.clear()
        self.logger.debug("Cleared all agent instances")


# Global agent registry instance
agent_registry = AgentRegistry()


def register_agent(name: str):
    """
    Decorator to register an agent class.
    
    Usage:
        @register_agent("PlanningAgent")
        class PlanningAgent(BaseAgent):
            ...
    """
    def decorator(agent_class: Type[BaseAgent]):
        agent_registry.register(name, agent_class)
        return agent_class
    return decorator
