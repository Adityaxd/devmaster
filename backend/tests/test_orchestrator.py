"""Tests for agent orchestrator."""

import pytest
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock

from app.agents.orchestrator import OrchestratorGraph
from app.agents.base import BaseAgent
from app.core.state import DevMasterState, TaskType, AgentStatus
from app.agents.registry import agent_registry


class MockPlanningAgent(BaseAgent):
    """Mock planning agent for testing."""
    
    name = "PlanningAgent"
    description = "Mock planning agent"
    
    async def _execute(self, state: DevMasterState) -> Dict[str, Any]:
        """Create a simple plan and hand off to DataModelingAgent."""
        return {
            "plan": {
                "steps": ["Create User model", "Create API"],
                "requirements": "Simple todo app"
            },
            "active_agent": "DataModelingAgent",
            "messages": state.get("messages", []) + [
                self.create_message("Created plan for todo app")
            ]
        }


class MockDataModelingAgent(BaseAgent):
    """Mock data modeling agent for testing."""
    
    name = "DataModelingAgent"
    description = "Mock data modeling agent"
    
    async def _execute(self, state: DevMasterState) -> Dict[str, Any]:
        """Generate mock SQL and hand off to Done."""
        artifacts = state.get("artifacts", {})
        artifacts["schema.sql"] = {
            "type": "sql",
            "path": "/db/schema.sql",
            "content": "CREATE TABLE users (id SERIAL PRIMARY KEY);",
            "created_by": self.name
        }
        
        return {
            "artifacts": artifacts,
            "active_agent": "Done",  # End the workflow
            "messages": state.get("messages", []) + [
                self.create_message("Generated database schema")
            ]
        }


class TestOrchestratorGraph:
    """Test the orchestrator graph functionality."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create an orchestrator with mock agents."""
        orchestrator = OrchestratorGraph()
        
        # Clear and register mock agents
        agent_registry._agents.clear()
        agent_registry.register(MockPlanningAgent)
        agent_registry.register(MockDataModelingAgent)
        
        # Register agents with orchestrator
        orchestrator.register_agent(MockPlanningAgent())
        orchestrator.register_agent(MockDataModelingAgent())
        
        return orchestrator
    
    async def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator is properly initialized."""
        assert len(orchestrator.agents) == 2
        assert "PlanningAgent" in orchestrator.agents
        assert "DataModelingAgent" in orchestrator.agents
        assert orchestrator.graph is not None
    
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
            "completed_agents": [],
            "agent_history": []
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
            "completed_agents": [],
            "agent_history": []
        }
        
        result = await orchestrator.execute(initial_state)
        
        # Should handle gracefully
        assert result["error_count"] > 0
        assert result["active_agent"] == "Done"
    
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
            "completed_agents": ["PlanningAgent"],
            "agent_history": []
        }
        
        next_node = orchestrator._route_to_next_agent(state_to_data)
        assert next_node == "DataModelingAgent"
        
        # Test routing to Done
        state_to_done = state_to_data.copy()
        state_to_done["active_agent"] = "Done"
        
        next_node = orchestrator._route_to_next_agent(state_to_done)
        assert next_node == "end"
    
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
            "completed_agents": [],
            "agent_history": []
        }
        
        result = await orchestrator.execute(initial_state)
        
        # Check agent history
        assert len(result["agent_history"]) >= 1
        assert result["agent_history"][0]["from_agent"] == "PlanningAgent"
        assert result["agent_history"][0]["to_agent"] == "DataModelingAgent"
        assert "timestamp" in result["agent_history"][0]
    
    async def test_error_propagation(self, orchestrator):
        """Test that errors are properly propagated."""
        class ErrorAgent(BaseAgent):
            name = "ErrorAgent"
            description = "Agent that always errors"
            
            async def _execute(self, state: DevMasterState) -> Dict[str, Any]:
                raise RuntimeError("Intentional test error")
        
        orchestrator.register_agent(ErrorAgent())
        
        initial_state: DevMasterState = {
            "task_type": TaskType.CONVERSATIONAL_CHAT,
            "user_request": "Test",
            "active_agent": "ErrorAgent",
            "messages": [],
            "plan": {},
            "artifacts": {},
            "validation_results": {},
            "error_count": 0,
            "completed_agents": [],
            "agent_history": []
        }
        
        result = await orchestrator.execute(initial_state)
        
        assert result["error_count"] > 0
        assert result["active_agent"] == "Done"
        # Error should be logged but workflow should complete
    
    async def test_chat_workflow(self, orchestrator):
        """Test simple chat workflow."""
        class ChatAgent(BaseAgent):
            name = "ChatAgent"
            description = "Simple chat agent"
            
            async def _execute(self, state: DevMasterState) -> Dict[str, Any]:
                return {
                    "messages": state.get("messages", []) + [
                        self.create_message("Hello! How can I help you?")
                    ],
                    "active_agent": "Done"
                }
        
        orchestrator.register_agent(ChatAgent())
        
        initial_state: DevMasterState = {
            "task_type": TaskType.CONVERSATIONAL_CHAT,
            "user_request": "Hello",
            "active_agent": "ChatAgent",
            "messages": [],
            "plan": {},
            "artifacts": {},
            "validation_results": {},
            "error_count": 0,
            "completed_agents": [],
            "agent_history": []
        }
        
        result = await orchestrator.execute(initial_state)
        
        assert len(result["messages"]) == 1
        assert result["messages"][0]["content"] == "Hello! How can I help you?"
        assert result["active_agent"] == "Done"
        assert "ChatAgent" in result["completed_agents"]
