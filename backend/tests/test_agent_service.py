"""Tests for agent service layer."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.services.agent_service import AgentService, agent_service
from app.core.state import DevMasterState, TaskType
from app.models import Project, Execution, ExecutionMessage, ExecutionArtifact
from app.models.execution import ExecutionStatus


class TestAgentService:
    """Test the agent service layer."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock(spec=AsyncSession)
        return session
    
    @pytest.fixture
    def test_agent_service(self):
        """Create an agent service instance for testing."""
        service = AgentService()
        # Clear any existing executions
        service.active_executions.clear()
        return service
    
    @pytest.fixture
    def initial_state(self) -> DevMasterState:
        """Create initial state for testing."""
        return {
            "user_request": "Build a todo app",
            "project_id": str(uuid.uuid4()),
            "task_type": "CONVERSATIONAL_CHAT",
            "active_agent": "IntentClassifier",
            "next_agent": None,
            "completed_agents": [],
            "messages": [],
            "plan": None,
            "requirements": None,
            "artifacts": {},
            "validation_results": [],
            "error_count": 0,
            "error_messages": [],
            "retry_count": 0,
            "max_retries": 3,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "project_status": "initializing",
            "agent_history": [],
            "metadata": {},
            "context": {}
        }
    
    @pytest.mark.asyncio
    async def test_execute_task_creates_execution(self, test_agent_service, initial_state):
        """Test that execute_task creates an execution record."""
        # Mock workflow creation
        with patch("app.services.agent_service.create_workflow_for_task") as mock_create_workflow:
            mock_workflow = MagicMock()
            mock_workflow.execute = AsyncMock(return_value={
                **initial_state,
                "status": "completed",
                "messages": [{"role": "assistant", "content": "Task completed"}],
                "completed_agents": ["IntentClassifier", "ChatAgent"]
            })
            mock_create_workflow.return_value = mock_workflow
            
            # Execute task
            result = await test_agent_service.execute_task(
                user_request="Build a todo app",
                project_id=initial_state["project_id"]
            )
            
            # Verify execution was created
            assert "execution_id" in result
            assert result["status"] == "completed"
            assert result["task_type"] == "CONVERSATIONAL_CHAT"
            assert len(result["messages"]) == 1
            
            # Verify execution is stored
            execution_id = result["execution_id"]
            assert execution_id in test_agent_service.active_executions
            stored_execution = test_agent_service.active_executions[execution_id]
            assert stored_execution["state"]["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_execute_task_handles_errors(self, test_agent_service, initial_state):
        """Test that execute_task handles orchestration errors."""
        # Mock workflow to raise an error
        with patch("app.services.agent_service.create_workflow_for_task") as mock_create_workflow:
            mock_workflow = MagicMock()
            mock_workflow.execute = AsyncMock(side_effect=Exception("Workflow failed"))
            mock_create_workflow.return_value = mock_workflow
            
            # Execute should not raise but return error status
            result = await test_agent_service.execute_task(
                user_request="Build app",
                project_id=initial_state["project_id"]
            )
            
            assert result["status"] == "failed"
            assert "error" in result
            assert "Workflow failed" in result["error"]
            
            # Verify error is stored in execution
            execution_id = result["execution_id"]
            stored_execution = test_agent_service.active_executions[execution_id]
            assert stored_execution["state"]["status"] == "failed"
            assert len(stored_execution["state"]["errors"]) > 0
    
    @pytest.mark.asyncio
    async def test_execute_task_no_workflow_available(self, test_agent_service):
        """Test handling when no workflow is available for task type."""
        with patch("app.services.agent_service.create_workflow_for_task") as mock_create_workflow:
            mock_create_workflow.return_value = None
            
            result = await test_agent_service.execute_task(
                user_request="Unknown task",
                project_id=str(uuid.uuid4())
            )
            
            assert result["status"] == "failed"
            assert "No workflow available" in result["error"]
    
    @pytest.mark.asyncio
    async def test_get_execution_status(self, test_agent_service):
        """Test retrieving execution status."""
        # Create a test execution
        execution_id = str(uuid.uuid4())
        test_state: DevMasterState = {
            "user_request": "Test",
            "project_id": str(uuid.uuid4()),
            "task_type": "CONVERSATIONAL_CHAT",
            "active_agent": "TestAgent",
            "status": "running",
            "completed_agents": ["IntentClassifier"],
            "messages": [{"role": "user", "content": "Test"}],
            "artifacts": {"test.py": {"type": "code", "content": "print('test')"}},
            "errors": [],
            "last_update": datetime.utcnow().isoformat(),
            "error_count": 0,
            "validation_results": [],
            "plan": None,
            "requirements": None,
            "retry_count": 0,
            "max_retries": 3,
            "start_time": datetime.utcnow().isoformat(),
            "context": {},
            "next_agent": None
        }
        
        test_agent_service.active_executions[execution_id] = {
            "state": test_state,
            "created_at": datetime.utcnow()
        }
        
        # Get status
        status = await test_agent_service.get_execution_status(execution_id)
        
        assert status is not None
        assert status["execution_id"] == execution_id
        assert status["status"] == "running"
        assert status["active_agent"] == "TestAgent"
        assert status["completed_agents"] == ["IntentClassifier"]
        assert status["artifacts"] == 1
        assert status["errors"] == 0
    
    @pytest.mark.asyncio
    async def test_get_execution_status_not_found(self, test_agent_service):
        """Test getting status for non-existent execution."""
        status = await test_agent_service.get_execution_status("non-existent-id")
        assert status is None
    
    @pytest.mark.asyncio
    async def test_get_execution_artifacts(self, test_agent_service):
        """Test retrieving execution artifacts."""
        # Create a test execution with artifacts
        execution_id = str(uuid.uuid4())
        test_artifacts = {
            "schema.sql": {
                "type": "sql",
                "path": "/db/schema.sql",
                "content": "CREATE TABLE users...;",
                "created_by": "DataModelingAgent",
                "language": "sql"
            },
            "user.py": {
                "type": "code",
                "path": "/models/user.py",
                "content": "class User(Base):...",
                "created_by": "BackendLogicAgent",
                "language": "python"
            }
        }
        
        test_agent_service.active_executions[execution_id] = {
            "state": {
                "artifacts": test_artifacts,
                "status": "completed"
            },
            "created_at": datetime.utcnow()
        }
        
        # Get artifacts
        artifacts = await test_agent_service.get_execution_artifacts(execution_id)
        
        assert artifacts is not None
        assert len(artifacts) == 2
        assert "schema.sql" in artifacts
        assert "user.py" in artifacts
        assert artifacts["schema.sql"]["type"] == "sql"
        assert artifacts["user.py"]["created_by"] == "BackendLogicAgent"
    
    @pytest.mark.asyncio
    async def test_get_execution_artifacts_not_found(self, test_agent_service):
        """Test getting artifacts for non-existent execution."""
        artifacts = await test_agent_service.get_execution_artifacts("non-existent-id")
        assert artifacts is None
    
    @pytest.mark.asyncio
    async def test_workflow_state_tracking(self, test_agent_service):
        """Test that workflow state is properly tracked throughout execution."""
        final_state: DevMasterState = {
            "user_request": "Build app",
            "project_id": str(uuid.uuid4()),
            "task_type": "FULLSTACK_DEVELOPMENT",
            "active_agent": "Done",
            "status": "completed",
            "messages": [
                {"role": "user", "content": "Build app"},
                {"role": "assistant", "content": "Plan created", "agent": "PlanningAgent"}
            ],
            "error_count": 0,
            "errors": [],
            "artifacts": {
                "schema.sql": {
                    "type": "sql",
                    "path": "/db/schema.sql",
                    "content": "CREATE TABLE...",
                    "created_by": "DataModelingAgent"
                }
            },
            "plan": {"steps": ["Create models", "Build API"]},
            "requirements": "Build a todo app with user authentication",
            "completed_agents": ["IntentClassifier", "PlanningAgent", "DataModelingAgent"],
            "validation_results": [
                {"type": "l1", "status": "passed"},
                {"type": "l2", "status": "passed"}
            ],
            "retry_count": 0,
            "max_retries": 3,
            "start_time": datetime.utcnow().isoformat(),
            "last_update": datetime.utcnow().isoformat(),
            "context": {"test": "data"},
            "next_agent": None
        }
        
        with patch("app.services.agent_service.create_workflow_for_task") as mock_create_workflow:
            mock_workflow = MagicMock()
            mock_workflow.execute = AsyncMock(return_value=final_state)
            mock_create_workflow.return_value = mock_workflow
            
            # Execute
            result = await test_agent_service.execute_task(
                user_request="Build app",
                project_id=final_state["project_id"]
            )
            
            # Verify state was properly tracked
            assert result["status"] == "completed"
            # Task type defaults to CONVERSATIONAL_CHAT for now until we implement IntentClassifier
            assert result["task_type"] == "CONVERSATIONAL_CHAT"
            assert len(result["messages"]) == 2
            assert len(result["artifacts"]) == 1
            assert result["errors"] == []
            
            # Verify execution is stored with complete state
            execution_id = result["execution_id"]
            stored_execution = test_agent_service.active_executions[execution_id]
            stored_state = stored_execution["state"]
            
            assert stored_state["completed_agents"] == ["IntentClassifier", "PlanningAgent", "DataModelingAgent"]
            assert stored_state["plan"] == {"steps": ["Create models", "Build API"]}
            assert len(stored_state["validation_results"]) == 2
            assert stored_state["status"] == "completed"


class TestGlobalAgentService:
    """Test the global agent_service instance."""
    
    def test_global_agent_service_exists(self):
        """Test that global agent_service is available."""
        assert agent_service is not None
        assert isinstance(agent_service, AgentService)
    
    def test_global_agent_service_is_singleton(self):
        """Test that we're using the same global instance."""
        from app.services.agent_service import agent_service as service1
        from app.services.agent_service import agent_service as service2
        
        assert service1 is service2
