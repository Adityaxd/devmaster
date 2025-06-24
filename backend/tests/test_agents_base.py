"""Tests for agent base classes and infrastructure."""

import pytest
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock

from app.agents.base import BaseAgent
from app.core.state import DevMasterState, AgentStatus, TaskType
from app.agents.registry import agent_registry, register_agent


class TestAgentClass(BaseAgent):
    """Test implementation of BaseAgent."""
    
    name = "TestAgent"
    description = "Agent for testing"
    
    async def _execute(self, state: DevMasterState) -> Dict[str, Any]:
        """Test execution."""
        return {
            "messages": state.get("messages", []) + [{
                "role": "assistant",
                "content": "Test execution",
                "agent": self.name
            }]
        }


class TestBaseAgent:
    """Test BaseAgent functionality."""
    
    async def test_agent_initialization(self):
        """Test agent initialization."""
        agent = TestAgentClass()
        
        assert agent.name == "TestAgent"
        assert agent.description == "Agent for testing"
        assert agent.status == AgentStatus.IDLE
        assert agent.error_count == 0
        assert agent.last_error is None
    
    async def test_agent_execution_success(self):
        """Test successful agent execution."""
        agent = TestAgentClass()
        initial_state: DevMasterState = {
            "messages": [],
            "active_agent": "TestAgent",
            "task_type": TaskType.CONVERSATIONAL_CHAT,
            "user_request": "Test request",
            "plan": {},
            "artifacts": {},
            "validation_results": {},
            "error_count": 0,
            "completed_agents": [],
            "agent_history": []
        }
        
        result = await agent.execute(initial_state)
        
        assert agent.status == AgentStatus.IDLE
        assert len(result["messages"]) == 1
        assert result["messages"][0]["content"] == "Test execution"
    
    async def test_agent_execution_with_error(self):
        """Test agent execution with error handling."""
        class ErrorAgent(BaseAgent):
            name = "ErrorAgent"
            description = "Agent that throws errors"
            
            async def _execute(self, state: DevMasterState) -> Dict[str, Any]:
                raise ValueError("Test error")
        
        agent = ErrorAgent()
        initial_state: DevMasterState = {
            "messages": [],
            "active_agent": "ErrorAgent",
            "task_type": TaskType.CONVERSATIONAL_CHAT,
            "user_request": "Test request",
            "plan": {},
            "artifacts": {},
            "validation_results": {},
            "error_count": 0,
            "completed_agents": [],
            "agent_history": []
        }
        
        # Should not raise, but handle the error
        result = await agent.execute(initial_state)
        
        assert agent.status == AgentStatus.IDLE
        assert agent.error_count == 1
        assert agent.last_error is not None
        assert "Test error" in str(agent.last_error)
        assert result["error_count"] == 1
    
    async def test_agent_preconditions(self):
        """Test agent precondition validation."""
        class PreconditionAgent(BaseAgent):
            name = "PreconditionAgent"
            description = "Agent with preconditions"
            
            async def validate_preconditions(self, state: DevMasterState) -> bool:
                """Require a plan to exist."""
                return bool(state.get("plan"))
            
            async def _execute(self, state: DevMasterState) -> Dict[str, Any]:
                return {"success": True}
        
        agent = PreconditionAgent()
        
        # State without plan - should fail preconditions
        state_no_plan: DevMasterState = {
            "messages": [],
            "active_agent": "PreconditionAgent",
            "task_type": TaskType.CONVERSATIONAL_CHAT,
            "user_request": "Test",
            "plan": {},  # Empty plan
            "artifacts": {},
            "validation_results": {},
            "error_count": 0,
            "completed_agents": [],
            "agent_history": []
        }
        
        result = await agent.execute(state_no_plan)
        assert result.get("error_count", 0) > 0
        
        # State with plan - should succeed
        state_with_plan = state_no_plan.copy()
        state_with_plan["plan"] = {"steps": ["test"]}
        
        result = await agent.execute(state_with_plan)
        assert result.get("success") is True
    
    async def test_create_message_helper(self):
        """Test the create_message helper method."""
        agent = TestAgentClass()
        
        message = agent.create_message("Test content", role="system")
        
        assert message["role"] == "system"
        assert message["content"] == "Test content"
        assert message["agent"] == "TestAgent"
        assert "timestamp" in message
    
    async def test_create_artifact_helper(self):
        """Test the create_artifact helper method."""
        agent = TestAgentClass()
        
        artifact = agent.create_artifact(
            artifact_type="code",
            path="/test.py",
            content="print('hello')",
            language="python"
        )
        
        assert artifact["type"] == "code"
        assert artifact["path"] == "/test.py"
        assert artifact["content"] == "print('hello')"
        assert artifact["language"] == "python"
        assert artifact["created_by"] == "TestAgent"
        assert "id" in artifact
        assert "timestamp" in artifact
    
    async def test_update_active_agent(self):
        """Test the update_active_agent helper method."""
        agent = TestAgentClass()
        state: DevMasterState = {
            "messages": [],
            "active_agent": "TestAgent",
            "task_type": TaskType.CONVERSATIONAL_CHAT,
            "user_request": "Test",
            "plan": {},
            "artifacts": {},
            "validation_results": {},
            "error_count": 0,
            "completed_agents": [],
            "agent_history": []
        }
        
        updates = agent.update_active_agent(state, "NextAgent", "Moving to next phase")
        
        assert updates["active_agent"] == "NextAgent"
        assert "TestAgent" in updates["completed_agents"]
        assert len(updates["agent_history"]) == 1
        assert updates["agent_history"][0]["from_agent"] == "TestAgent"
        assert updates["agent_history"][0]["to_agent"] == "NextAgent"
        assert updates["agent_history"][0]["reason"] == "Moving to next phase"


class TestAgentRegistry:
    """Test agent registry functionality."""
    
    def test_register_agent_decorator(self):
        """Test the register_agent decorator."""
        # Clear registry first
        agent_registry._agents.clear()
        
        @register_agent
        class DecoratedAgent(BaseAgent):
            name = "DecoratedAgent"
            description = "Test decorated agent"
            
            async def _execute(self, state: DevMasterState) -> Dict[str, Any]:
                return {}
        
        assert "DecoratedAgent" in agent_registry._agents
        assert agent_registry.get("DecoratedAgent") == DecoratedAgent
    
    def test_register_agent_manually(self):
        """Test manual agent registration."""
        agent_registry._agents.clear()
        
        class ManualAgent(BaseAgent):
            name = "ManualAgent"
            description = "Manually registered"
            
            async def _execute(self, state: DevMasterState) -> Dict[str, Any]:
                return {}
        
        agent_registry.register(ManualAgent)
        
        assert "ManualAgent" in agent_registry._agents
        assert agent_registry.get("ManualAgent") == ManualAgent
    
    def test_list_agents(self):
        """Test listing all registered agents."""
        agent_registry._agents.clear()
        
        @register_agent
        class Agent1(BaseAgent):
            name = "Agent1"
            description = "First agent"
            
            async def _execute(self, state: DevMasterState) -> Dict[str, Any]:
                return {}
        
        @register_agent
        class Agent2(BaseAgent):
            name = "Agent2"
            description = "Second agent"
            
            async def _execute(self, state: DevMasterState) -> Dict[str, Any]:
                return {}
        
        agents = agent_registry.list_agents()
        
        assert len(agents) == 2
        assert "Agent1" in agents
        assert "Agent2" in agents
    
    def test_get_nonexistent_agent(self):
        """Test getting a non-existent agent."""
        result = agent_registry.get("NonExistentAgent")
        assert result is None
    
    def test_duplicate_agent_registration(self):
        """Test that duplicate registration raises error."""
        agent_registry._agents.clear()
        
        @register_agent
        class DuplicateAgent(BaseAgent):
            name = "DuplicateAgent"
            description = "First registration"
            
            async def _execute(self, state: DevMasterState) -> Dict[str, Any]:
                return {}
        
        # Try to register another agent with same name
        with pytest.raises(ValueError, match="already registered"):
            @register_agent
            class DuplicateAgent2(BaseAgent):
                name = "DuplicateAgent"  # Same name!
                description = "Second registration"
                
                async def _execute(self, state: DevMasterState) -> Dict[str, Any]:
                    return {}
