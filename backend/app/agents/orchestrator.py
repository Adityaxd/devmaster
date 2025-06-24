"""
DevMaster Orchestration Engine
Implements LangGraph-style state machine for agent coordination
"""
from typing import Dict, Any, Callable, Optional, List, Literal
from enum import Enum
import logging
from datetime import datetime

from langgraph.graph import StateGraph, END
from ..core.state import DevMasterState, ProjectStatus
from .base import BaseAgent


logger = logging.getLogger("devmaster.orchestrator")


class OrchestratorGraph:
    """
    The core orchestration engine for DevMaster.
    
    Following the Tech Bible:
    - Uses LangGraph for ALL multi-agent orchestration
    - No custom orchestrator classes with manual loops
    - All workflows modeled as a StateGraph
    - Agent handoffs via active_agent field
    """
    
    def __init__(self):
        """Initialize the orchestrator graph."""
        self.agents: Dict[str, BaseAgent] = {}
        self.graph: Optional[StateGraph] = None
        self.compiled_graph = None
        self._build_graph()    
    def register_agent(self, agent: BaseAgent) -> None:
        """
        Register an agent with the orchestrator.
        
        Args:
            agent: The agent instance to register
        """
        if agent.name in self.agents:
            raise ValueError(f"Agent {agent.name} already registered")
        
        self.agents[agent.name] = agent
        logger.info(f"Registered agent: {agent.name}")
        
        # Rebuild the graph with the new agent
        self._build_graph()
    
    def _build_graph(self) -> None:
        """
        Build the LangGraph state machine.
        
        This creates nodes for each agent and sets up conditional routing.
        """
        if not self.agents:
            return
        
        # Create a new state graph
        self.graph = StateGraph(DevMasterState)
        
        # Add a node for each registered agent
        for agent_name, agent in self.agents.items():
            self.graph.add_node(agent_name, self._create_node_function(agent))
        
        # Add the final node
        self.graph.add_node("Done", self._final_node)
        
        # Set up conditional routing from each agent
        for agent_name in self.agents:
            self.graph.add_conditional_edges(
                agent_name,
                self._route_to_next_agent,
                # Create routing map: each agent can go to any other agent or Done
                {name: name for name in list(self.agents.keys()) + ["Done"]}
            )
        
        # Set entry point - we need a start node that routes to the initial agent
        self.graph.add_node("START", self._start_node)
        self.graph.set_entry_point("START")
        
        # Add conditional edge from START to route to initial agent
        self.graph.add_conditional_edges(
            "START",
            self._route_to_next_agent,
            {name: name for name in list(self.agents.keys()) + ["Done"]}
        )
        
        # Compile the graph
        self.compiled_graph = self.graph.compile()    
    def _create_node_function(self, agent: BaseAgent) -> Callable:
        """
        Create a node function for an agent.
        
        Args:
            agent: The agent instance
            
        Returns:
            Async function that executes the agent
        """
        async def node_function(state: DevMasterState) -> Dict[str, Any]:
            """Execute the agent and return state updates."""
            logger.info(f"Executing agent: {agent.name}")
            
            # Execute the agent
            updates = await agent.execute(state)
            
            # Ensure we have an updated_at timestamp
            updates["updated_at"] = datetime.utcnow()
            
            # Add agent execution to history
            agent_history = state.get("agent_history", [])
            agent_history.append({
                "agent": agent.name,
                "timestamp": datetime.utcnow(),
                "updates": list(updates.keys())
            })
            updates["agent_history"] = agent_history
            
            return updates
        
        return node_function
    
    def _start_node(self, state: DevMasterState) -> Dict[str, Any]:
        """
        The start node that initializes the workflow.
        
        Args:
            state: The current state
            
        Returns:
            Initial state updates
        """
        logger.info("Starting workflow")
        return {}
    
    def _final_node(self, state: DevMasterState) -> Dict[str, Any]:
        """
        The final node that marks workflow completion.
        
        Args:
            state: The current state
            
        Returns:
            Final state updates
        """
        logger.info("Workflow completed")
        return {
            "project_status": ProjectStatus.COMPLETED,
            "updated_at": datetime.utcnow()
        }    
    def _route_to_next_agent(self, state: DevMasterState) -> str:
        """
        Determine the next agent to execute based on the state.
        
        This is the "brain" of the router. It checks the active_agent field
        to determine where to route control next.
        
        Args:
            state: The current state
            
        Returns:
            Name of the next node to execute
        """
        next_agent = state.get("active_agent", "Done")
        
        # Validate the agent exists
        if next_agent not in self.agents and next_agent != "Done":
            logger.error(f"Unknown agent: {next_agent}")
            return "Done"
        
        logger.info(f"Routing to: {next_agent}")
        return next_agent
    
    async def execute(self, initial_state: DevMasterState) -> DevMasterState:
        """
        Execute the orchestration graph with the given initial state.
        
        Args:
            initial_state: The initial state to start with
            
        Returns:
            The final state after all agents have executed
        """
        if not self.compiled_graph:
            raise RuntimeError("No agents registered")
        
        # Ensure we have required fields
        if "active_agent" not in initial_state:
            raise ValueError("initial_state must have 'active_agent' field")
        
        # Initialize state fields if not present
        initial_state.setdefault("messages", [])
        initial_state.setdefault("artifacts", {})
        initial_state.setdefault("validation_results", {})
        initial_state.setdefault("agent_history", [])
        initial_state.setdefault("error_count", 0)
        initial_state.setdefault("error_messages", [])
        initial_state.setdefault("created_at", datetime.utcnow())
        initial_state.setdefault("updated_at", datetime.utcnow())
        initial_state.setdefault("metadata", {})
        
        # Execute the graph
        logger.info(f"Starting orchestration with agent: {initial_state['active_agent']}")
        
        # Run the graph - it will handle all routing and execution
        final_state = await self.compiled_graph.ainvoke(initial_state)
        
        logger.info("Orchestration completed")
        return final_state