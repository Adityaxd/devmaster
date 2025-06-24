"""Tests for agent orchestrator."""

import pytest
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from app.agents.orchestrator import OrchestratorGraph, NodeType
from app.agents.base import BaseAgent, AgentResult
from app.core.state import DevMasterState, TaskType, AgentStatus, Message
from app.agents.registry import agent_registry


class MockPlanningAgent(BaseAgent):
    """Mock planning agent for testing."""
    
    def __init__(self):
        super().__init__(name="PlanningAgent", description="Mock planning agent")
    
    async def execute(self, state: DevMasterState) -> AgentResult:
        """Create a simple plan and hand off to DataModelingAgent."""
        return AgentResult(
            success=True,
            state_updates={
                "plan": {
                    "steps": ["Create User model", "Create API"],
                    "requirements": "Simple todo app"
                }
            },
            next_agent="DataModelingAgent",
            messages=[self.add_message("Created plan for todo app")]
        )


class MockDataModelingAgent(BaseAgent):
    """Mock data modeling agent for testing."""
    
    def __init__(self):
        super().__init__(name="DataModelingAgent", description="Mock data modeling agent")
    
    async def execute(self, state: DevMasterState) -> AgentResult:
        """Generate mock SQL and hand off to Done."""
        artifacts = state.get("artifacts", {})
        artifacts["schema.sql"] = {
            "type": "sql",
            "path": "/db/schema.sql",
            "content": "CREATE TABLE users (id SERIAL PRIMARY KEY);",
            "created_by": self.name
        }
        
        return AgentResult(
            success=True,
            state_updates={"artifacts": artifacts},
            next_agent="Done",  # End the workflow
            messages=[self.add_message("Generated database schema")]
        )


class TestOrchestratorGraph:
    """Test the orchestrator graph functionality."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create an orchestrator with mock agents."""
        orchestrator = OrchestratorGraph()
        
        # Clear and register mock agents in registry
        agent_registry._agents.clear()
        agent_registry.register("PlanningAgent", MockPlanningAgent)
        agent_registry.register("DataModelingAgent", MockDataModelingAgent)
        
        # Add agent nodes to orchestrator
        orchestrator.add_node("PlanningAgent", NodeType.AGENT, MockPlanningAgent())
        orchestrator.add_node("DataModelingAgent", NodeType.AGENT, MockDataModelingAgent())
        
        # Set up routing
        orchestrator.set_entry_point("PlanningAgent")
        orchestrator.add_conditional_edges(
            "PlanningAgent",
            lambda state: state.get("active_agent", "END"),
            {"DataModelingAgent": "DataModelingAgent", "END": "END"}
        )
        orchestrator.add_conditional_edges(
            "DataModelingAgent",
            lambda state: state.get("active_agent", "END"),
            {"Done": "END", "END": "END"}
        )
        
        return orchestrator
    
    async def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator is properly initialized."""
        # We have agent nodes + router nodes + END node
        assert len(orchestrator.nodes) >= 4  # 2 agents + 2 routers + END
        assert "PlanningAgent" in orchestrator.nodes
        assert "DataModelingAgent" in orchestrator.nodes
        assert "END" in orchestrator.nodes
        assert orchestrator.entry_point == "PlanningAgent"
    
    async def test_fullstack_workflow_creation(self, orchestrator):
        """Test creating a fullstack development workflow."""
        initial_state: DevMasterState = {
            "task_type": TaskType.FULLSTACK_DEVELOPMENT,
            "user_request": "Build a todo app",
            "active_agent": "PlanningAgent",
            "messages": [],
            "plan": {},
            "artifacts": {},
            "validation_results": {},
            "error_count": 0,
            "error_messages": [],
            "completed_agents": [],
            "agent_history": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Execute the workflow
        result = await orchestrator.execute(initial_state)
        
        # Verify the workflow executed properly
        assert result is not None
        assert "plan" in result
        assert result["plan"]["steps"] == ["Create User model", "Create API"]
        assert "artifacts" in result
        assert "schema.sql" in result["artifacts"]
        assert result["active_agent"] == "Done"
        assert len(result["messages"]) >= 2
        assert result["completed_agents"] == ["PlanningAgent", "DataModelingAgent"]
    
    async def test_agent_not_found_handling(self, orchestrator):
        """Test handling when an agent is not found."""
        initial_state: DevMasterState = {
            "task_type": TaskType.CONVERSATIONAL_CHAT,
            "user_request": "Test",
            "active_agent": "NonExistentAgent",  # This agent doesn't exist
            "messages": [],
            "plan": {},
            "artifacts": {},
            "validation_results": {},
            "error_count": 0,
            "error_messages": [],
            "completed_agents": [],
            "agent_history": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = await orchestrator.execute(initial_state)
        
        # Should handle gracefully
        assert result["error_count"] > 0
        assert result["status"] == "failed"
        assert "NonExistentAgent" in str(result["error_messages"])
    
    async def test_conditional_routing(self, orchestrator):
        """Test that conditional routing works correctly."""
        # First, test routing to DataModelingAgent
        state_to_data: DevMasterState = {
            "task_type": TaskType.FULLSTACK_DEVELOPMENT,
            "user_request": "Test",
            "active_agent": "DataModelingAgent",
            "messages": [],
            "plan": {"steps": ["test"]},
            "artifacts": {},
            "validation_results": {},
            "error_count": 0,
            "error_messages": [],
            "completed_agents": ["PlanningAgent"],
            "agent_history": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Find the PlanningAgent router node
        router_node = orchestrator.nodes["PlanningAgent_router"]
        assert router_node.router_func(state_to_data) == "DataModelingAgent"
        
        # Test routing to Done/END
        state_to_done = state_to_data.copy()
        state_to_done["active_agent"] = "Done"
        
        assert router_node.router_func(state_to_done) == "Done"
    
    async def test_agent_history_tracking(self, orchestrator):
        """Test that agent history is properly tracked."""
        initial_state: DevMasterState = {
            "task_type": TaskType.FULLSTACK_DEVELOPMENT,
            "user_request": "Build app",
            "active_agent": "PlanningAgent",
            "messages": [],
            "plan": {},
            "artifacts": {},
            "validation_results": {},
            "error_count": 0,
            "error_messages": [],
            "completed_agents": [],
            "agent_history": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = await orchestrator.execute(initial_state)
        
        # Check agent history
        assert len(result["agent_history"]) >= 2  # One for each agent
        # BaseAgent stores history with 'agent' and 'status' fields
        assert result["agent_history"][0]["agent"] == "PlanningAgent"
        assert result["agent_history"][0]["status"] == "completed"
        assert "timestamp" in result["agent_history"][0]
    
    async def test_error_propagation(self):
        """Test that errors are properly propagated."""
        # Create a fresh orchestrator for this test
        error_orchestrator = OrchestratorGraph()
        
        class ErrorAgent(BaseAgent):
            def __init__(self):
                super().__init__(name="ErrorAgent", description="Agent that always errors")
            
            async def execute(self, state: DevMasterState) -> AgentResult:
                raise RuntimeError("Intentional test error")
        
        error_orchestrator.add_node("ErrorAgent", NodeType.AGENT, ErrorAgent())
        error_orchestrator.set_entry_point("ErrorAgent")
        error_orchestrator.add_conditional_edges(
            "ErrorAgent",
            lambda state: "END",
            {"END": "END"}
        )
        
        initial_state: DevMasterState = {
            "task_type": TaskType.CONVERSATIONAL_CHAT,
            "user_request": "Test",
            "active_agent": "ErrorAgent",
            "messages": [],
            "plan": {},
            "artifacts": {},
            "validation_results": {},
            "error_count": 0,
            "error_messages": [],
            "completed_agents": [],
            "agent_history": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = await error_orchestrator.execute(initial_state)
        
        assert result["error_count"] > 0
        assert len(result["error_messages"]) > 0
        assert "Intentional test error" in result["error_messages"][0]
        # Error should be logged but workflow should complete
    
    async def test_chat_workflow(self):
        """Test simple chat workflow."""
        # Create a fresh orchestrator for this test
        chat_orchestrator = OrchestratorGraph()
        
        class ChatAgent(BaseAgent):
            def __init__(self):
                super().__init__(name="ChatAgent", description="Simple chat agent")
            
            async def execute(self, state: DevMasterState) -> AgentResult:
                return AgentResult(
                    success=True,
                    state_updates={},
                    next_agent="Done",
                    messages=[self.add_message("Hello! How can I help you?")]
                )
        
        chat_orchestrator.add_node("ChatAgent", NodeType.AGENT, ChatAgent())
        chat_orchestrator.set_entry_point("ChatAgent")
        chat_orchestrator.add_conditional_edges(
            "ChatAgent",
            lambda state: "END" if state.get("active_agent") == "Done" else state.get("active_agent", "END"),
            {"Done": "END", "END": "END"}
        )
        
        initial_state: DevMasterState = {
            "task_type": TaskType.CONVERSATIONAL_CHAT,
            "user_request": "Hello",
            "active_agent": "ChatAgent",
            "messages": [],
            "plan": {},
            "artifacts": {},
            "validation_results": {},
            "error_count": 0,
            "error_messages": [],
            "completed_agents": [],
            "agent_history": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = await chat_orchestrator.execute(initial_state)
        
        assert len(result["messages"]) == 1
        assert result["messages"][0]["content"] == "Hello! How can I help you?"
        assert result["active_agent"] == "Done"
        assert "ChatAgent" in result["completed_agents"]
