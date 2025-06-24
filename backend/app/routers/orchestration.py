"""
Orchestration API endpoints for testing
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict, Any
import uuid
import logging

from ..core.orchestrator.graph import OrchestratorGraph
from ..core.agents.test_agents import EchoAgent, SequentialTestAgent
from ..core.state import DevMasterState, TaskType, ProjectStatus
from ..core.websocket import manager
from ..core.events import event_bus, Event, EventType


router = APIRouter(prefix="/api/v1/orchestration", tags=["orchestration"])
logger = logging.getLogger("devmaster.api.orchestration")

# Initialize orchestrator
orchestrator = OrchestratorGraph()

# Register test agents
echo_agent = EchoAgent()
agent1 = SequentialTestAgent("TestAgent1", "TestAgent2")
agent2 = SequentialTestAgent("TestAgent2", "TestAgent3")
agent3 = SequentialTestAgent("TestAgent3", "EchoAgent")

orchestrator.register_agent(echo_agent)
orchestrator.register_agent(agent1)
orchestrator.register_agent(agent2)
orchestrator.register_agent(agent3)

@router.post("/test/echo")
async def test_echo_orchestration(request: Dict[str, Any]):
    """
    Test endpoint for echo orchestration.
    
    This will run a simple echo agent and return the result.
    """
    project_id = str(uuid.uuid4())
    
    # Create initial state
    initial_state: DevMasterState = {
        "user_request": request.get("message", "Hello, DevMaster!"),
        "task_type": TaskType.CONVERSATIONAL_CHAT,
        "project_id": project_id,
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
        "created_at": None,
        "updated_at": None,
        "metadata": {}
    }
    
    # Publish project created event
    await event_bus.publish(Event(
        EventType.PROJECT_CREATED,
        project_id,
        {"message": "Test echo orchestration started"}
    ))
    
    try:
        # Execute orchestration
        final_state = await orchestrator.execute(initial_state)
        
        # Publish completion event
        await event_bus.publish(Event(
            EventType.PROJECT_COMPLETED,
            project_id,
            {"message": "Test completed successfully"}
        ))
        
        return {
            "project_id": project_id,
            "status": final_state["project_status"],
            "messages": final_state["messages"],
            "agent_history": final_state["agent_history"]
        }
        
    except Exception as e:
        logger.error(f"Orchestration failed: {e}")
        
        # Publish failure event
        await event_bus.publish(Event(
            EventType.PROJECT_FAILED,
            project_id,
            {"error": str(e)}
        ))
        
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test/sequence")
async def test_sequence_orchestration(request: Dict[str, Any]):
    """
    Test endpoint for sequential agent orchestration.
    
    This will run multiple agents in sequence.
    """
    project_id = str(uuid.uuid4())
    
    # Create initial state
    initial_state: DevMasterState = {
        "user_request": request.get("message", "Test sequential execution"),
        "task_type": TaskType.FULLSTACK_DEVELOPMENT,
        "project_id": project_id,
        "active_agent": "TestAgent1",  # Start with first agent
        "agent_history": [],
        "plan": {},
        "requirements": {},
        "artifacts": {},
        "validation_results": {},
        "messages": [],
        "project_status": ProjectStatus.INITIALIZING,
        "error_count": 0,
        "error_messages": [],
        "created_at": None,
        "updated_at": None,
        "metadata": {}
    }
    
    try:
        # Execute orchestration
        final_state = await orchestrator.execute(initial_state)
        
        return {
            "project_id": project_id,
            "status": final_state["project_status"],
            "messages": final_state["messages"],
            "agent_history": final_state["agent_history"],
            "execution_path": [h["agent"] for h in final_state["agent_history"]]
        }
        
    except Exception as e:
        logger.error(f"Orchestration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    """
    WebSocket endpoint for real-time project updates.
    """
    await manager.connect(websocket, project_id)
    
    try:
        while True:
            # Keep connection alive and handle any client messages
            data = await websocket.receive_text()
            # Could handle client commands here if needed
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)