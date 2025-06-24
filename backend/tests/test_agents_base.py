"""Tests for agent base classes and infrastructure."""

import pytest
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from app.agents.base import BaseAgent, AgentResult, AgentState
from app.core.state import DevMasterState, Message, Artifact, TaskType
from app.agents.registry import agent_registry, register_agent


class TestAgentImplementation(BaseAgent):
    """Test implementation of BaseAgent."""
    
    def __init__(self):
        super().__init__(name="TestAgent", description="Agent for testing")
        self.execute_called = False
    
    async def execute(self, state: DevMasterState) -> AgentResult:
        """Test execution."""
        self.execute_called = True
        return AgentResult(
            success=True,
            state_updates={
                "test_executed": True
            },
            messages=[self.add_message("Test execution completed")]
        )


class TestBaseAgent:
    """Test BaseAgent functionality."""
    
    def test_agent_initialization(self):
        """Test agent initialization."""
        agent = TestAgentImplementation()
        
        assert agent.name == "TestAgent"
        assert agent.description == "Agent for testing"
        assert agent.state == AgentState.IDLE
    
    @pytest.mark.asyncio
    async def test_agent_run_success(self):
        """Test successful agent execution via run method."""
        agent = TestAgentImplementation()
        initial_state: DevMasterState = {
            "messages": [],
            "active_agent": "TestAgent",
            "task_type": TaskType.CONVERSATIONAL_CHAT,
            "user_request": "Test request",
            "plan": {},
            "artifacts": {},
            "validation_results": [],
            "error_count": 0,
            "error_messages": [],
            "completed_agents": [],
            "context": {},
            "project_id": "test-project",
            "project_status": "initializing",
            "agent_history": [],
            "metadata": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "retry_count": 0,
            "max_retries": 3,
            "next_agent": None
        }
        
        result = await agent.run(initial_state)
        
        assert agent.execute_called
        assert agent.state == AgentState.COMPLETED
        assert result.get("test_executed") is True
        assert "TestAgent" in result.get("completed_agents", [])
        assert len(result.get("messages", [])) == 1
        assert result["messages"][0]["content"] == "Test execution completed"
    
    @pytest.mark.asyncio
    async def test_agent_run_with_error(self):
        """Test agent execution with error handling."""
        class ErrorAgent(BaseAgent):
            def __init__(self):
                super().__init__(name="ErrorAgent", description="Agent that throws errors")
            
            async def execute(self, state: DevMasterState) -> AgentResult:
                raise ValueError("Test error")
        
        agent = ErrorAgent()
        initial_state: DevMasterState = {
            "messages": [],
            "active_agent": "ErrorAgent",
            "task_type": TaskType.CONVERSATIONAL_CHAT,
            "user_request": "Test request",
            "plan": {},
            "artifacts": {},
            "validation_results": [],
            "error_count": 0,
            "error_messages": [],
            "completed_agents": [],
            "context": {},
            "project_id": "test-project",
            "project_status": "initializing",
            "agent_history": [],
            "metadata": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "retry_count": 0,
            "max_retries": 3,
            "next_agent": None
        }
        
        # Should not raise, but handle the error
        result = await agent.run(initial_state)
        
        assert agent.state == AgentState.FAILED
        assert result.get("error_count", 0) == 1
        assert len(result.get("error_messages", [])) == 1
        assert "Test error" in result["error_messages"][0]
    
    @pytest.mark.asyncio
    async def test_agent_preconditions(self):
        """Test agent precondition validation."""
        class PreconditionAgent(BaseAgent):
            def __init__(self):
                super().__init__(name="PreconditionAgent", description="Agent with preconditions")
            
            async def validate_preconditions(self, state: DevMasterState) -> bool:
                """Require a plan to exist."""
                return bool(state.get("plan"))
            
            async def execute(self, state: DevMasterState) -> AgentResult:
                return AgentResult(success=True, state_updates={"precondition_passed": True})
        
        agent = PreconditionAgent()
        
        # State without plan - should fail preconditions
        state_no_plan: DevMasterState = {
            "messages": [],
            "active_agent": "PreconditionAgent",
            "task_type": TaskType.CONVERSATIONAL_CHAT,
            "user_request": "Test",
            "plan": {},  # Empty plan
            "artifacts": {},
            "validation_results": [],
            "error_count": 0,
            "error_messages": [],
            "completed_agents": [],
            "context": {},
            "project_id": "test-project",
            "project_status": "initializing",
            "agent_history": [],
            "metadata": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "retry_count": 0,
            "max_retries": 3,
            "next_agent": None
        }
        
        result = await agent.run(state_no_plan)
        assert result.get("error_count", 0) > 0
        assert "Preconditions not met" in result["error_messages"][0]
        
        # State with plan - should succeed
        state_with_plan = state_no_plan.copy()
        state_with_plan["plan"] = {"steps": ["test"]}
        
        result = await agent.run(state_with_plan)
        assert result.get("precondition_passed") is True
    
    def test_add_message_helper(self):
        """Test the add_message helper method."""
        agent = TestAgentImplementation()
        
        message = agent.add_message("Test content", role="system")
        
        assert isinstance(message, Message)
        assert message.role == "system"
        assert message.content == "Test content"
        assert message.agent_name == "TestAgent"
        assert message.timestamp is not None
    
    def test_create_artifact_helper(self):
        """Test the create_artifact helper method."""
        agent = TestAgentImplementation()
        
        artifact = agent.create_artifact(
            artifact_id="test-artifact",
            artifact_type="python",
            path="/test.py",
            content="print('hello')"
        )
        
        assert isinstance(artifact, Artifact)
        assert artifact.id == "test-artifact"
        assert artifact.type == "python"
        assert artifact.path == "/test.py"
        assert artifact.content == "print('hello')"
        assert artifact.created_at is not None
    
    @pytest.mark.asyncio
    async def test_next_agent_handoff(self):
        """Test agent handoff via next_agent."""
        class HandoffAgent(BaseAgent):
            def __init__(self):
                super().__init__(name="HandoffAgent", description="Agent that hands off")
            
            async def execute(self, state: DevMasterState) -> AgentResult:
                return AgentResult(
                    success=True,
                    next_agent="NextAgent",
                    state_updates={"handoff_completed": True}
                )
        
        agent = HandoffAgent()
        state: DevMasterState = {
            "messages": [],
            "active_agent": "HandoffAgent",
            "task_type": TaskType.CONVERSATIONAL_CHAT,
            "user_request": "Test",
            "plan": {},
            "artifacts": {},
            "validation_results": [],
            "error_count": 0,
            "error_messages": [],
            "completed_agents": [],
            "context": {},
            "project_id": "test-project",
            "project_status": "initializing",
            "agent_history": [],
            "metadata": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "retry_count": 0,
            "max_retries": 3,
            "next_agent": None
        }
        
        result = await agent.run(state)
        
        assert result["active_agent"] == "NextAgent"
        assert result["handoff_completed"] is True
        assert "HandoffAgent" in result["completed_agents"]


class TestAgentRegistry:
    """Test agent registry functionality."""
    
    def setup_method(self):
        """Clear registry before each test."""
        agent_registry._agents.clear()
        agent_registry._instances.clear()
    
    def test_register_agent(self):
        """Test manual agent registration."""
        class ManualAgent(BaseAgent):
            def __init__(self):
                super().__init__(name="ManualAgent", description="Manually registered")
            
            async def execute(self, state: DevMasterState) -> AgentResult:
                return AgentResult(success=True)
        
        agent_registry.register("ManualAgent", ManualAgent)
        
        assert "ManualAgent" in agent_registry._agents
        assert agent_registry.get_agent_class("ManualAgent") == ManualAgent
    
    def test_register_agent_decorator(self):
        """Test the register_agent decorator."""
        @register_agent("DecoratedAgent")
        class DecoratedAgent(BaseAgent):
            def __init__(self):
                super().__init__(name="DecoratedAgent", description="Test decorated agent")
            
            async def execute(self, state: DevMasterState) -> AgentResult:
                return AgentResult(success=True)
        
        assert "DecoratedAgent" in agent_registry._agents
        assert agent_registry.get_agent_class("DecoratedAgent") == DecoratedAgent
    
    def test_get_agent_instance(self):
        """Test getting agent instances."""
        class TestAgent(BaseAgent):
            def __init__(self, **kwargs):
                super().__init__(name=kwargs.get("name", "TestAgent"), description="Test")
            
            async def execute(self, state: DevMasterState) -> AgentResult:
                return AgentResult(success=True)
        
        agent_registry.register("TestAgent", TestAgent)
        
        # First call creates instance
        instance1 = agent_registry.get_agent_instance("TestAgent")
        assert instance1 is not None
        assert instance1.name == "TestAgent"
        
        # Second call returns cached instance
        instance2 = agent_registry.get_agent_instance("TestAgent")
        assert instance2 is instance1
    
    def test_list_agents(self):
        """Test listing all registered agents."""
        class Agent1(BaseAgent):
            def __init__(self):
                super().__init__(name="Agent1", description="First agent")
            
            async def execute(self, state: DevMasterState) -> AgentResult:
                return AgentResult(success=True)
        
        class Agent2(BaseAgent):
            def __init__(self):
                super().__init__(name="Agent2", description="Second agent")
            
            async def execute(self, state: DevMasterState) -> AgentResult:
                return AgentResult(success=True)
        
        agent_registry.register("Agent1", Agent1)
        agent_registry.register("Agent2", Agent2)
        
        agents = agent_registry.list_agents()
        
        assert len(agents) == 2
        assert "Agent1" in agents
        assert "Agent2" in agents
    
    def test_get_nonexistent_agent(self):
        """Test getting a non-existent agent."""
        result = agent_registry.get_agent_class("NonExistentAgent")
        assert result is None
        
        instance = agent_registry.get_agent_instance("NonExistentAgent")
        assert instance is None
    
    def test_duplicate_agent_registration(self):
        """Test that duplicate registration raises error."""
        class DuplicateAgent(BaseAgent):
            def __init__(self):
                super().__init__(name="DuplicateAgent", description="First registration")
            
            async def execute(self, state: DevMasterState) -> AgentResult:
                return AgentResult(success=True)
        
        agent_registry.register("DuplicateAgent", DuplicateAgent)
        
        # Try to register another agent with same name
        with pytest.raises(ValueError, match="already registered"):
            agent_registry.register("DuplicateAgent", DuplicateAgent)
    
    def test_clear_instances(self):
        """Test clearing cached instances."""
        class TestAgent(BaseAgent):
            def __init__(self, **kwargs):
                super().__init__(name=kwargs.get("name", "TestAgent"), description="Test")
            
            async def execute(self, state: DevMasterState) -> AgentResult:
                return AgentResult(success=True)
        
        agent_registry.register("TestAgent", TestAgent)
        
        # Create instance
        instance1 = agent_registry.get_agent_instance("TestAgent")
        assert len(agent_registry._instances) == 1
        
        # Clear instances
        agent_registry.clear_instances()
        assert len(agent_registry._instances) == 0
        
        # Get instance again - should be new
        instance2 = agent_registry.get_agent_instance("TestAgent")
        assert instance2 is not instance1
