"""
Test the orchestration system
"""
import pytest
import asyncio
from datetime import datetime

from app.agents.orchestrator import OrchestratorGraph
from app.core.agents.test_agents import EchoAgent, SequentialTestAgent
from app.core.state import DevMasterState, TaskType, ProjectStatus


@pytest.mark.asyncio
async def test_echo_agent():
    """Test single agent execution."""
    # Create orchestrator
    orchestrator = OrchestratorGraph()
    
    # Register echo agent
    echo_agent = EchoAgent()
    orchestrator.register_agent(echo_agent)
    
    # Create initial state
    initial_state: DevMasterState = {
        "user_request": "Test message",
        "task_type": TaskType.CONVERSATIONAL_CHAT,
        "project_id": "test-1",
        "active_agent": "EchoAgent",
        "agent_history": [],
        "plan": {},
        "requirements": {},
        "artifacts": {},
        "validation_results": {},
        "messages": [],
        "project_status": ProjectStatus.INITIALIZING,
        "error_count": 0,
        "error_messages": [],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "metadata": {}
    }
    
    # Execute
    final_state = await orchestrator.execute(initial_state)
    
    # Verify
    assert final_state["project_status"] == ProjectStatus.COMPLETED
    assert final_state["active_agent"] == "Done"
    assert len(final_state["messages"]) > 0
    assert any("Echo: Test message" in msg["content"] for msg in final_state["messages"])

@pytest.mark.asyncio
async def test_sequential_agents():
    """Test multiple agents in sequence."""
    # Create orchestrator
    orchestrator = OrchestratorGraph()
    
    # Register agents
    agent1 = SequentialTestAgent("Agent1", "Agent2")
    agent2 = SequentialTestAgent("Agent2", "Agent3")
    agent3 = SequentialTestAgent("Agent3", "Done")
    
    orchestrator.register_agent(agent1)
    orchestrator.register_agent(agent2)
    orchestrator.register_agent(agent3)
    
    # Create initial state
    initial_state: DevMasterState = {
        "user_request": "Test sequential execution",
        "task_type": TaskType.FULLSTACK_DEVELOPMENT,
        "project_id": "test-2",
        "active_agent": "Agent1",
        "agent_history": [],
        "plan": {},
        "requirements": {},
        "artifacts": {},
        "validation_results": {},
        "messages": [],
        "project_status": ProjectStatus.INITIALIZING,
        "error_count": 0,
        "error_messages": [],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "metadata": {}
    }
    
    # Execute
    final_state = await orchestrator.execute(initial_state)
    
    # Verify
    assert final_state["project_status"] == ProjectStatus.COMPLETED
    assert final_state["active_agent"] == "Done"
    
    # Check execution order
    agent_names = [h["agent"] for h in final_state["agent_history"]]
    assert agent_names == ["Agent1", "Agent2", "Agent3"]
    
    # Check messages
    assert len(final_state["messages"]) >= 3
    for i, agent_name in enumerate(["Agent1", "Agent2", "Agent3"]):
        assert any(agent_name in msg["content"] for msg in final_state["messages"])


if __name__ == "__main__":
    # Run tests directly
    asyncio.run(test_echo_agent())
    asyncio.run(test_sequential_agents())
    print("All tests passed!")