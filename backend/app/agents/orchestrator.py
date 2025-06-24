"""
LangGraph-style orchestrator for DevMaster agent coordination.

This is the core orchestration engine that manages agent execution,
state transitions, and control flow using a graph-based approach.
"""

from typing import Dict, Any, Optional, Callable, List, Literal
from datetime import datetime
import logging
import asyncio
from enum import Enum

from app.core.state import DevMasterState
from .base import BaseAgent
from .registry import agent_registry


class NodeType(str, Enum):
    """Types of nodes in the orchestration graph."""
    AGENT = "agent"
    ROUTER = "router"
    END = "end"


class Edge:
    """Represents an edge in the orchestration graph."""
    
    def __init__(
        self,
        source: str,
        target: str,
        condition: Optional[Callable[[DevMasterState], bool]] = None
    ):
        self.source = source
        self.target = target
        self.condition = condition
    
    def should_traverse(self, state: DevMasterState) -> bool:
        """Check if this edge should be traversed given the current state."""
        if self.condition is None:
            return True
        return self.condition(state)


class Node:
    """Represents a node in the orchestration graph."""
    
    def __init__(
        self,
        name: str,
        node_type: NodeType,
        agent: Optional[BaseAgent] = None,
        router_func: Optional[Callable[[DevMasterState], str]] = None
    ):
        self.name = name
        self.type = node_type
        self.agent = agent
        self.router_func = router_func
        self.edges: List[Edge] = []
    
    def add_edge(self, edge: Edge):
        """Add an outgoing edge from this node."""
        self.edges.append(edge)


class OrchestratorGraph:
    """
    LangGraph-style orchestrator for managing agent execution flow.
    
    This implements a stateful graph where:
    - Nodes represent agents or routing decisions
    - Edges represent transitions with optional conditions
    - State flows through the graph, being transformed by each node
    """
    
    def __init__(self, name: str = "DevMasterOrchestrator"):
        self.name = name
        self.nodes: Dict[str, Node] = {}
        self.entry_point: Optional[str] = None
        self.logger = logging.getLogger(f"orchestrator.{name}")
        
        # Add the special END node
        self.add_node("END", NodeType.END)
    
    def add_node(
        self,
        name: str,
        node_type: NodeType,
        agent: Optional[BaseAgent] = None,
        router_func: Optional[Callable[[DevMasterState], str]] = None
    ) -> None:
        """Add a node to the orchestration graph."""
        if name in self.nodes:
            raise ValueError(f"Node {name} already exists")
        
        node = Node(name, node_type, agent, router_func)
        self.nodes[name] = node
        self.logger.debug(f"Added node: {name} (type: {node_type})")
    
    def add_edge(
        self,
        source: str,
        target: str,
        condition: Optional[Callable[[DevMasterState], bool]] = None
    ) -> None:
        """Add an edge between two nodes."""
        if source not in self.nodes:
            raise ValueError(f"Source node {source} not found")
        if target not in self.nodes:
            raise ValueError(f"Target node {target} not found")
        
        edge = Edge(source, target, condition)
        self.nodes[source].add_edge(edge)
        self.logger.debug(f"Added edge: {source} -> {target}")
    
    def add_conditional_edges(
        self,
        source: str,
        router: Callable[[DevMasterState], str],
        routes: Dict[str, str]
    ) -> None:
        """
        Add conditional routing from a node.
        
        The router function determines which route to take,
        and routes maps the router output to target nodes.
        """
        if source not in self.nodes:
            raise ValueError(f"Source node {source} not found")
        
        # Create a router node
        router_name = f"{source}_router"
        self.add_node(router_name, NodeType.ROUTER, router_func=router)
        
        # Connect source to router
        self.add_edge(source, router_name)
        
        # Connect router to all possible targets
        for route_key, target in routes.items():
            if target not in self.nodes:
                raise ValueError(f"Target node {target} not found")
            
            # Edge condition checks if router output matches route key
            condition = lambda state, key=route_key: router(state) == key
            self.add_edge(router_name, target, condition)
    
    def set_entry_point(self, node_name: str) -> None:
        """Set the entry point for the graph execution."""
        if node_name not in self.nodes:
            raise ValueError(f"Node {node_name} not found")
        self.entry_point = node_name
        self.logger.debug(f"Set entry point: {node_name}")
    
    async def execute(self, initial_state: DevMasterState) -> DevMasterState:
        """
        Execute the orchestration graph with the given initial state.
        
        Returns the final state after all agents have completed.
        """
        if not self.entry_point:
            raise ValueError("Entry point not set")
        
        state = initial_state.copy()
        # Use active_agent from state if present, otherwise use entry_point
        current_node_name = state.get("active_agent", self.entry_point)
        
        # Initialize execution metadata
        state["start_time"] = datetime.utcnow().isoformat()
        state["status"] = "executing"
        state["completed_agents"] = []
        state["errors"] = []
        state["error_count"] = 0
        
        self.logger.info(f"Starting orchestration from {current_node_name}")
        
        while current_node_name != "END":
            # Check if node exists
            if current_node_name not in self.nodes:
                self.logger.error(f"Node {current_node_name} not found")
                state["status"] = "failed"
                state["error_count"] = state.get("error_count", 0) + 1
                state["error_messages"] = state.get("error_messages", []) + [f"Node {current_node_name} not found"]
                break
            
            node = self.nodes[current_node_name]
            self.logger.info(f"Executing node: {current_node_name} (type: {node.type})")
            
            try:
                if node.type == NodeType.AGENT and node.agent:
                    # Execute agent and update state
                    state["active_agent"] = node.name
                    updates = await node.agent.run(state)
                    state.update(updates)
                    
                elif node.type == NodeType.ROUTER and node.router_func:
                    # Router nodes don't modify state, just determine next node
                    pass
                
                # Determine next node
                next_node = self._get_next_node(node, state)
                
                if next_node is None:
                    self.logger.warning(f"No valid edge from {current_node_name}")
                    break
                
                # Handle the "Done" mapping here as well
                if next_node == "Done":
                    next_node = "END"
                    
                current_node_name = next_node
                
            except Exception as e:
                self.logger.error(f"Error in node {current_node_name}: {str(e)}")
                state["status"] = "failed"
                state["error_count"] = state.get("error_count", 0) + 1
                
                # Check if we should retry
                if state["error_count"] < state.get("max_retries", 3):
                    self.logger.info(f"Retrying node {current_node_name}")
                    await asyncio.sleep(1)  # Brief delay before retry
                    continue
                else:
                    break
        
        # Set final status
        if state["status"] == "executing":
            state["status"] = "completed"
        
        state["last_update"] = datetime.utcnow().isoformat()
        
        self.logger.info(f"Orchestration completed with status: {state['status']}")
        return state
    
    def _get_next_node(self, node: Node, state: DevMasterState) -> Optional[str]:
        """Determine the next node to execute based on the current node and state."""
        # Check for explicit next_agent override in state
        if "next_agent" in state and state["next_agent"]:
            next_agent = state["next_agent"]
            state["next_agent"] = None  # Clear the override
            # Map "Done" to "END"
            if next_agent == "Done":
                return "END"
            return next_agent
        
        # For router nodes, use the router function
        if node.type == NodeType.ROUTER and node.router_func:
            return node.router_func(state)
        
        # Otherwise, find the first valid edge
        for edge in node.edges:
            if edge.should_traverse(state):
                return edge.target
        
        return None
    
    def visualize(self) -> str:
        """Generate a text representation of the graph for debugging."""
        lines = [f"Orchestration Graph: {self.name}"]
        lines.append(f"Entry Point: {self.entry_point}")
        lines.append("\nNodes:")
        
        for name, node in self.nodes.items():
            lines.append(f"  - {name} ({node.type})")
            if node.agent:
                lines.append(f"    Agent: {node.agent.name}")
            for edge in node.edges:
                lines.append(f"    -> {edge.target}")
        
        return "\n".join(lines)


def create_default_router(state: DevMasterState) -> str:
    """
    Default routing function that uses the active_agent field.
    
    This is the standard LangGraph pattern for agent handoffs.
    """
    if agent_name := state.get("active_agent"):
        if agent_name == "Done":
            return "END"
        return agent_name
    return "END"
