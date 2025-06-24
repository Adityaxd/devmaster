"""
Agent execution service for handling agent orchestration requests.

This service bridges the FastAPI endpoints with the agent infrastructure.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import uuid
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from ..agents import DevMasterState, OrchestratorGraph
from ..agents.workflows import create_workflow_for_task
from ..agents.specialists import IntentClassifierAgent
from ..core.config import settings


logger = logging.getLogger(__name__)


class AgentService:
    """
    Service for managing agent execution and orchestration.
    
    This handles:
    - Creating execution contexts
    - Running agent workflows
    - Tracking execution state
    - Persisting results
    """
    
    def __init__(self):
        self.active_executions: Dict[str, Dict[str, Any]] = {}
    
    async def execute_task(
        self,
        user_request: str,
        project_id: str,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Execute a task using the appropriate agent workflow.
        
        Args:
            user_request: The user's request/prompt
            project_id: The project context
            db: Optional database session
            
        Returns:
            Execution result with task ID and initial status
        """
        # Generate execution ID
        execution_id = str(uuid.uuid4())
        
        # Create initial state
        initial_state: DevMasterState = {
            "user_request": user_request,
            "project_id": project_id,
            "task_type": "CONVERSATIONAL_CHAT",  # Will be updated by classifier
            "active_agent": "IntentClassifier",
            "next_agent": None,
            "completed_agents": [],
            "messages": [],
            "plan": None,
            "requirements": None,
            "artifacts": {},
            "validation_results": [],
            "error_count": 0,
            "errors": [],
            "retry_count": 0,
            "max_retries": 3,
            "start_time": datetime.utcnow().isoformat(),
            "last_update": datetime.utcnow().isoformat(),
            "status": "initializing",
            "context": {
                "execution_id": execution_id
            }
        }
        
        # Store execution state
        self.active_executions[execution_id] = {
            "state": initial_state,
            "created_at": datetime.utcnow()
        }
        
        try:
            # First, run intent classification
            classifier = IntentClassifierAgent()
            result = await classifier.run(initial_state)
            initial_state.update(result)
            
            # Get the appropriate workflow
            task_type = initial_state.get("task_type", "CONVERSATIONAL_CHAT")
            workflow = create_workflow_for_task(task_type)
            
            if not workflow:
                raise ValueError(f"No workflow available for task type: {task_type}")
            
            # Execute the workflow asynchronously
            # In production, this would be queued to Celery
            final_state = await workflow.execute(initial_state)
            
            # Update stored state
            self.active_executions[execution_id]["state"] = final_state
            self.active_executions[execution_id]["completed_at"] = datetime.utcnow()
            
            return {
                "execution_id": execution_id,
                "status": final_state.get("status", "unknown"),
                "task_type": task_type,
                "messages": final_state.get("messages", []),
                "artifacts": final_state.get("artifacts", {}),
                "errors": final_state.get("errors", [])
            }
            
        except Exception as e:
            logger.error(f"Error executing task: {str(e)}")
            
            # Update error state
            if execution_id in self.active_executions:
                self.active_executions[execution_id]["state"]["status"] = "failed"
                self.active_executions[execution_id]["state"]["errors"].append({
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            return {
                "execution_id": execution_id,
                "status": "failed",
                "error": str(e)
            }
    
    async def get_execution_status(
        self,
        execution_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get the current status of an execution."""
        if execution_id not in self.active_executions:
            return None
        
        execution = self.active_executions[execution_id]
        state = execution["state"]
        
        return {
            "execution_id": execution_id,
            "status": state.get("status", "unknown"),
            "active_agent": state.get("active_agent"),
            "completed_agents": state.get("completed_agents", []),
            "messages": state.get("messages", []),
            "artifacts": len(state.get("artifacts", {})),
            "errors": len(state.get("errors", [])),
            "created_at": execution["created_at"],
            "last_update": state.get("last_update")
        }
    
    async def get_execution_artifacts(
        self,
        execution_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get artifacts from an execution."""
        if execution_id not in self.active_executions:
            return None
        
        state = self.active_executions[execution_id]["state"]
        return state.get("artifacts", {})


# Global service instance
agent_service = AgentService()
