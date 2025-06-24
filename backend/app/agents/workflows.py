"""
Workflow builders for different task types.

These functions create and configure orchestration graphs
for various DevMaster workflows.
"""

from typing import Optional

from .orchestrator import OrchestratorGraph, create_default_router, NodeType
from .registry import agent_registry
from .state import DevMasterState


def build_development_workflow() -> OrchestratorGraph:
    """
    Build the full Software Assembly Line workflow for development tasks.
    
    This creates the complete multi-agent swarm for full-stack development.
    """
    graph = OrchestratorGraph("DevelopmentWorkflow")
    
    # Add all specialist agent nodes
    agents = [
        "IntentClassifier",
        "PlanningAgent",
        "DataModelingAgent",
        "BackendLogicAgent", 
        "APIGenerationAgent",
        "SDKGenerationAgent",
        "FrontendAgent",
        "TestingAgent",
        "IntegrationAgent"
    ]
    
    for agent_name in agents:
        agent_instance = agent_registry.get_agent_instance(agent_name)
        if agent_instance:
            graph.add_node(
                agent_name,
                NodeType.AGENT,
                agent=agent_instance
            )
    
    # Set up the flow
    graph.set_entry_point("IntentClassifier")
    
    # Add conditional routing based on active_agent field
    for agent_name in agents:
        graph.add_conditional_edges(
            agent_name,
            create_default_router,
            {
                agent: agent for agent in agents + ["END"]
            }
        )
    
    return graph


def build_chat_workflow() -> OrchestratorGraph:
    """
    Build a simple single-agent chat workflow.
    
    For conversational interactions that don't require development.
    """
    graph = OrchestratorGraph("ChatWorkflow")
    
    # Add nodes
    for agent_name in ["IntentClassifier", "ChatAgent"]:
        agent_instance = agent_registry.get_agent_instance(agent_name)
        if agent_instance:
            graph.add_node(
                agent_name,
                NodeType.AGENT,
                agent=agent_instance
            )
    
    # Set up flow
    graph.set_entry_point("IntentClassifier")
    graph.add_edge("IntentClassifier", "ChatAgent")
    graph.add_edge("ChatAgent", "END")
    
    return graph


def create_workflow_for_task(task_type: str) -> Optional[OrchestratorGraph]:
    """
    Create the appropriate workflow based on task type.
    
    This is the Tier 2 capability mapping.
    """
    workflows = {
        "FULLSTACK_DEVELOPMENT": build_development_workflow,
        "CONVERSATIONAL_CHAT": build_chat_workflow,
        # Add more workflows as implemented
    }
    
    builder = workflows.get(task_type)
    if builder:
        return builder()
    
    return None
