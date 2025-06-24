"""
Tests for the Intent Classification System

NOTE: These tests are for Week 3 implementation. The IntentClassifier and related
agents are abstract classes that haven't been implemented yet.
"""

import pytest
from app.agents.classifiers import IntentClassifier, CapabilityRouter
from app.agents.specialists import ChatAgent
from app.core.state import DevMasterState, TaskType, AgentStatus
from app.core.orchestrator.graph import OrchestratorGraph
from app.core.events import EventBus

# Skip all tests in this file until Week 3 implementation
pytestmark = pytest.mark.skip(reason="Week 3 features not implemented yet")


@pytest.mark.asyncio
class TestIntentClassifier:
    """Test the IntentClassifier agent."""
    
    async def test_fullstack_development_classification(self):
        """Test classification of fullstack development requests."""
        classifier = IntentClassifier()
        
        state = DevMasterState(
            user_request="Build me a todo list application with user authentication",
            active_agent="IntentClassifier",
            messages=[],
            agent_history=[]
        )
        
        result = await classifier.execute(state)
        
        # Check the intent was classified correctly
        assert "intent" in result
        intent = result["intent"]
        assert intent["primary_intent"] == TaskType.FULLSTACK_DEVELOPMENT.value
        assert intent["confidence"] > 0.5
        assert "build" in intent["keywords"] or "application" in intent["keywords"]
        
        # Check handoff to CapabilityRouter
        assert result["active_agent"] == "CapabilityRouter"
    
    async def test_backend_only_classification(self):
        """Test classification of backend-only requests."""
        classifier = IntentClassifier()
        
        state = DevMasterState(
            user_request="Create a REST API for user management with CRUD operations",
            active_agent="IntentClassifier",
            messages=[],
            agent_history=[]
        )
        
        result = await classifier.execute(state)
        
        intent = result["intent"]
        assert intent["primary_intent"] == TaskType.BACKEND_ONLY.value
        assert intent["confidence"] > 0.5
        assert any(kw in intent["keywords"] for kw in ["api", "rest", "crud"])
    
    async def test_conversational_chat_classification(self):
        """Test classification of chat requests."""
        classifier = IntentClassifier()
        
        state = DevMasterState(
            user_request="Hello, what can you help me with?",
            active_agent="IntentClassifier",
            messages=[],
            agent_history=[]
        )
        
        result = await classifier.execute(state)
        
        intent = result["intent"]
        assert intent["primary_intent"] == TaskType.CONVERSATIONAL_CHAT.value
    
    async def test_complexity_estimation(self):
        """Test complexity estimation."""
        classifier = IntentClassifier()
        
        # Simple request
        simple_state = DevMasterState(
            user_request="Create a simple demo app",
            active_agent="IntentClassifier",
            messages=[],
            agent_history=[]
        )
        
        result = await classifier.execute(simple_state)
        assert result["intent"]["complexity"] == "simple"
        
        # Complex request
        complex_state = DevMasterState(
            user_request="Build a complex production-ready e-commerce platform with payment integration, inventory management, and real-time analytics",
            active_agent="IntentClassifier",
            messages=[],
            agent_history=[]
        )
        
        result = await classifier.execute(complex_state)
        assert result["intent"]["complexity"] == "complex"
    
    async def test_missing_user_request(self):
        """Test handling of missing user request."""
        classifier = IntentClassifier()
        
        state = DevMasterState(
            user_request="",
            active_agent="IntentClassifier",
            messages=[],
            agent_history=[]
        )
        
        result = await classifier.execute(state)
        
        # Should route to error handler
        assert result["active_agent"] == "ErrorHandler"
        assert "error" in result


@pytest.mark.asyncio
class TestCapabilityRouter:
    """Test the CapabilityRouter agent."""
    
    async def test_fullstack_workflow_routing(self):
        """Test routing to Software Assembly Line workflow."""
        router = CapabilityRouter()
        
        state = DevMasterState(
            intent={
                "primary_intent": TaskType.FULLSTACK_DEVELOPMENT.value,
                "confidence": 0.9,
                "keywords": ["build", "application"],
                "complexity": "medium",
                "requires_context": False,
                "sub_intents": []
            },
            active_agent="CapabilityRouter",
            messages=[],
            agent_history=[]
        )
        
        result = await router.execute(state)
        
        # Check routing decision
        assert "routing_decision" in result
        routing = result["routing_decision"]
        assert routing["selected_workflow"] == "software_assembly_line"
        assert routing["confidence"] == 0.9
        
        # Check workflow agents
        assert "workflow_agents" in result
        assert result["workflow_agents"][0] == "PlanningAgent"
        assert result["active_agent"] == "PlanningAgent"
    
    async def test_chat_workflow_routing(self):
        """Test routing to single agent chat workflow."""
        router = CapabilityRouter()
        
        state = DevMasterState(
            intent={
                "primary_intent": TaskType.CONVERSATIONAL_CHAT.value,
                "confidence": 0.8,
                "keywords": ["hello"],
                "complexity": "simple",
                "requires_context": False,
                "sub_intents": []
            },
            active_agent="CapabilityRouter",
            messages=[],
            agent_history=[]
        )
        
        result = await router.execute(state)
        
        routing = result["routing_decision"]
        assert routing["selected_workflow"] == "single_agent_chat"
        assert result["active_agent"] == "ChatAgent"
    
    async def test_low_confidence_warnings(self):
        """Test warnings for low confidence classifications."""
        router = CapabilityRouter()
        
        state = DevMasterState(
            intent={
                "primary_intent": TaskType.FULLSTACK_DEVELOPMENT.value,
                "confidence": 0.5,  # Low confidence
                "keywords": [],
                "complexity": "medium",
                "requires_context": True,
                "sub_intents": [TaskType.BACKEND_ONLY.value]
            },
            active_agent="CapabilityRouter",
            messages=[],
            agent_history=[]
        )
        
        result = await router.execute(state)
        
        routing = result["routing_decision"]
        assert len(routing["warnings"]) > 0
        assert any("Low confidence" in w for w in routing["warnings"])
        assert any("context" in w for w in routing["warnings"])
        
        # Should suggest alternatives
        assert len(routing["alternative_workflows"]) > 0
    
    async def test_missing_intent(self):
        """Test handling of missing intent."""
        router = CapabilityRouter()
        
        state = DevMasterState(
            active_agent="CapabilityRouter",
            messages=[],
            agent_history=[]
        )
        
        result = await router.execute(state)
        
        # Should route to error handler
        assert result["active_agent"] == "ErrorHandler"
        assert "error" in result


@pytest.mark.asyncio
class TestChatAgent:
    """Test the ChatAgent for conversational interactions."""
    
    async def test_greeting_response(self):
        """Test response to greetings."""
        agent = ChatAgent()
        
        state = DevMasterState(
            user_request="Hello!",
            active_agent="ChatAgent",
            messages=[],
            agent_history=[]
        )
        
        result = await agent.execute(state)
        
        # Check response
        assert len(result["messages"]) > 0
        message = result["messages"][-1]
        assert message["role"] == "ChatAgent"
        assert "DevMaster" in message["content"]
        assert result["active_agent"] == "Done"
    
    async def test_capabilities_response(self):
        """Test response to capability questions."""
        agent = ChatAgent()
        
        state = DevMasterState(
            user_request="What can you do?",
            active_agent="ChatAgent",
            messages=[],
            agent_history=[]
        )
        
        result = await agent.execute(state)
        
        message = result["messages"][-1]
        assert "Full-stack application development" in message["content"]
        assert "Backend API creation" in message["content"]
    
    async def test_help_response(self):
        """Test response to help requests."""
        agent = ChatAgent()
        
        state = DevMasterState(
            user_request="How do I get started?",
            active_agent="ChatAgent",
            messages=[],
            agent_history=[]
        )
        
        result = await agent.execute(state)
        
        message = result["messages"][-1]
        assert "Build a todo list application" in message["content"]
        assert "Create a REST API" in message["content"]


@pytest.mark.asyncio
class TestFullClassificationWorkflow:
    """Test the complete classification workflow."""
    
    async def test_end_to_end_classification_to_chat(self):
        """Test complete workflow from classification to chat response."""
        # Set up orchestrator with all agents
        event_bus = EventBus()
        orchestrator = OrchestratorGraph(event_bus)
        
        orchestrator.register_agent(IntentClassifier())
        orchestrator.register_agent(CapabilityRouter())
        orchestrator.register_agent(ChatAgent())
        
        # Create initial state
        initial_state = DevMasterState(
            user_request="Hello, what can you help me with?",
            active_agent="IntentClassifier",
            messages=[],
            agent_history=[],
            project_id="test-project"
        )
        
        # Execute workflow
        final_state = await orchestrator.execute(initial_state)
        
        # Verify complete execution
        assert len(final_state["agent_history"]) == 3
        assert final_state["agent_history"][0]["agent"] == "IntentClassifier"
        assert final_state["agent_history"][1]["agent"] == "CapabilityRouter"
        assert final_state["agent_history"][2]["agent"] == "ChatAgent"
        
        # Verify classification results
        assert "intent" in final_state
        assert final_state["intent"]["primary_intent"] == TaskType.CONVERSATIONAL_CHAT.value
        
        # Verify routing decision
        assert "routing_decision" in final_state
        assert final_state["routing_decision"]["selected_workflow"] == "single_agent_chat"
        
        # Verify final message
        messages = final_state["messages"]
        assert len(messages) >= 3  # One from each agent
        assert "DevMaster" in messages[-1]["content"]
    
    async def test_end_to_end_development_request(self):
        """Test workflow for development requests (up to routing)."""
        event_bus = EventBus()
        orchestrator = OrchestratorGraph(event_bus)
        
        orchestrator.register_agent(IntentClassifier())
        orchestrator.register_agent(CapabilityRouter())
        # Note: We don't have PlanningAgent yet, so workflow will stop at routing
        
        initial_state = DevMasterState(
            user_request="Build me a blog application with posts and comments",
            active_agent="IntentClassifier",
            messages=[],
            agent_history=[],
            project_id="test-blog-project"
        )
        
        final_state = await orchestrator.execute(initial_state)
        
        # Verify intent classification
        assert final_state["intent"]["primary_intent"] == TaskType.FULLSTACK_DEVELOPMENT.value
        assert final_state["intent"]["confidence"] > 0.7
        
        # Verify routing to software assembly line
        assert final_state["routing_decision"]["selected_workflow"] == "software_assembly_line"
        assert final_state["workflow_agents"][0] == "PlanningAgent"
        
        # Should stop here since PlanningAgent isn't registered
        assert final_state["active_agent"] == "PlanningAgent"
