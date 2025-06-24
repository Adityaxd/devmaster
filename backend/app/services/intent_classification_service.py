"""
Intent Classification Service

This service handles the complete intent classification workflow:
1. IntentClassifier analyzes the user request
2. CapabilityRouter selects the appropriate workflow
3. Orchestrator executes the selected workflow
"""

from typing import Dict, Any, Optional
from app.core.state import DevMasterState, TaskType
from app.agents.classifiers import IntentClassifier, CapabilityRouter
from app.agents.specialists import ChatAgent
from app.agents.orchestrator import OrchestratorGraph
from app.core.events import EventBus, EventType
from app.services.websocket_manager import WebSocketManager
import logging

logger = logging.getLogger(__name__)


class IntentClassificationService:
    """Service that handles intent classification and routing."""
    
    def __init__(
        self, 
        event_bus: EventBus,
        websocket_manager: WebSocketManager
    ):
        self.event_bus = event_bus
        self.websocket_manager = websocket_manager
        self.orchestrator = OrchestratorGraph(event_bus)
        
        # Register classification agents
        self._register_agents()
    
    def _register_agents(self):
        """Register all required agents with the orchestrator."""
        # Classification agents
        self.orchestrator.register_agent(IntentClassifier())
        self.orchestrator.register_agent(CapabilityRouter())
        
        # Specialist agents (for now, just ChatAgent)
        self.orchestrator.register_agent(ChatAgent())
        
        # TODO: Register other specialist agents as they are implemented
        # self.orchestrator.register_agent(PlanningAgent())
        # self.orchestrator.register_agent(DataModelingAgent())
        # etc.
    
    async def classify_and_route(
        self, 
        user_request: str,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Classify user intent and route to appropriate workflow.
        
        Args:
            user_request: The user's input request
            project_id: Optional project ID for context
            
        Returns:
            The final state after classification and routing
        """
        try:
            # Create initial state
            initial_state = DevMasterState(
                user_request=user_request,
                active_agent="IntentClassifier",  # Start with intent classification
                messages=[],
                artifacts={},
                validation_results={},
                project_id=project_id or "default",
                agent_history=[]
            )
            
            # Emit start event
            await self.event_bus.emit(
                EventType.INTENT_CLASSIFICATION_STARTED,
                {
                    "project_id": project_id,
                    "user_request": user_request
                }
            )
            
            # Execute the classification workflow
            final_state = await self.orchestrator.execute(initial_state)
            
            # Extract classification results
            intent = final_state.get("intent", {})
            routing_decision = final_state.get("routing_decision", {})
            
            # Emit completion event
            await self.event_bus.emit(
                EventType.INTENT_CLASSIFICATION_COMPLETED,
                {
                    "project_id": project_id,
                    "intent": intent,
                    "routing_decision": routing_decision,
                    "selected_workflow": final_state.get("selected_workflow")
                }
            )
            
            # Send results via WebSocket if project_id provided
            if project_id:
                await self.websocket_manager.broadcast_to_project(
                    project_id,
                    {
                        "type": "classification_complete",
                        "intent": intent,
                        "routing": routing_decision,
                        "messages": final_state.get("messages", [])
                    }
                )
            
            return {
                "success": True,
                "intent": intent,
                "routing": routing_decision,
                "messages": final_state.get("messages", []),
                "final_state": final_state
            }
            
        except Exception as e:
            logger.error(f"Error in classify_and_route: {str(e)}")
            
            # Emit error event
            await self.event_bus.emit(
                EventType.AGENT_ERROR,
                {
                    "project_id": project_id,
                    "error": str(e),
                    "agent": "IntentClassificationService"
                }
            )
            
            return {
                "success": False,
                "error": str(e),
                "messages": [{
                    "role": "system",
                    "content": f"Classification failed: {str(e)}"
                }]
            }
    
    async def get_workflow_info(self, task_type: TaskType) -> Dict[str, Any]:
        """Get information about the workflow for a given task type."""
        from app.agents.classifiers.capability_router import CapabilityRouter
        
        workflow_name = CapabilityRouter.TASK_TO_WORKFLOW.get(task_type)
        if not workflow_name:
            return {"error": f"No workflow found for task type: {task_type.value}"}
        
        workflow = CapabilityRouter.WORKFLOW_TEMPLATES.get(workflow_name)
        if not workflow:
            return {"error": f"Workflow template not found: {workflow_name}"}
        
        return {
            "task_type": task_type.value,
            "workflow": workflow.model_dump()
        }
