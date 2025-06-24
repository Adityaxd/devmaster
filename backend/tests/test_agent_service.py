"""Tests for agent service layer."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.services.agent_service import AgentService
from app.core.state import DevMasterState, TaskType
from app.models import Project, Execution, ExecutionMessage, ExecutionArtifact
from app.models.execution import ExecutionStatus


class TestAgentService:
    """Test the agent service layer."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock(spec=AsyncSession)
        # Mock the context manager
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        return session
    
    @pytest.fixture
    def agent_service(self, mock_db_session):
        """Create an agent service with mocked dependencies."""
        return AgentService(mock_db_session)
    
    @pytest.fixture
    def mock_project(self):
        """Create a mock project."""
        project = Mock(spec=Project)
        project.id = uuid.uuid4()
        project.name = "Test Project"
        project.owner_id = uuid.uuid4()
        return project
    
    async def test_execute_task_creates_execution(self, agent_service, mock_project):
        """Test that execute_task creates an execution record."""
        # Mock the orchestrator
        with patch.object(agent_service.orchestrator, 'execute') as mock_execute:
            mock_execute.return_value = {
                "messages": [{"role": "assistant", "content": "Done"}],
                "active_agent": "Done",
                "error_count": 0,
                "artifacts": {},
                "plan": {"steps": ["test"]},
                "completed_agents": ["PlanningAgent"],
                "validation_results": {"passed": True}
            }
            
            # Mock database operations
            agent_service.db.add = Mock()
            agent_service.db.commit = AsyncMock()
            agent_service.db.refresh = AsyncMock()
            
            # Execute task
            execution = await agent_service.execute_task(
                project_id=mock_project.id,
                user_request="Build a todo app",
                task_type=TaskType.FULLSTACK_DEVELOPMENT
            )
            
            # Verify execution was created
            assert execution is not None
            assert execution.project_id == mock_project.id
            assert execution.user_request == "Build a todo app"
            assert execution.task_type == TaskType.FULLSTACK_DEVELOPMENT
            assert execution.status == ExecutionStatus.COMPLETED
            
            # Verify database operations
            agent_service.db.add.assert_called_once()
            agent_service.db.commit.assert_called()
    
    async def test_execute_task_handles_errors(self, agent_service, mock_project):
        """Test that execute_task handles orchestration errors."""
        # Mock orchestrator to raise an error
        with patch.object(agent_service.orchestrator, 'execute') as mock_execute:
            mock_execute.side_effect = Exception("Orchestration failed")
            
            # Mock database operations
            agent_service.db.add = Mock()
            agent_service.db.commit = AsyncMock()
            agent_service.db.refresh = AsyncMock()
            
            # Execute should not raise but mark as failed
            execution = await agent_service.execute_task(
                project_id=mock_project.id,
                user_request="Build app",
                task_type=TaskType.FULLSTACK_DEVELOPMENT
            )
            
            assert execution.status == ExecutionStatus.FAILED
            assert execution.error_count > 0
            assert len(execution.error_messages) > 0
    
    async def test_save_execution_messages(self, agent_service):
        """Test saving execution messages to database."""
        execution_id = uuid.uuid4()
        messages = [
            {
                "role": "user",
                "content": "Build a todo app"
            },
            {
                "role": "assistant",
                "content": "I'll help you build that",
                "agent": "PlanningAgent"
            }
        ]
        
        # Mock database batch insert
        agent_service.db.add_all = Mock()
        agent_service.db.commit = AsyncMock()
        
        await agent_service._save_execution_messages(execution_id, messages)
        
        # Verify add_all was called with ExecutionMessage objects
        agent_service.db.add_all.assert_called_once()
        saved_messages = agent_service.db.add_all.call_args[0][0]
        
        assert len(saved_messages) == 2
        assert all(isinstance(msg, ExecutionMessage) for msg in saved_messages)
        assert saved_messages[0].role == "user"
        assert saved_messages[0].content == "Build a todo app"
        assert saved_messages[1].agent_name == "PlanningAgent"
    
    async def test_save_execution_artifacts(self, agent_service):
        """Test saving execution artifacts to database."""
        execution_id = uuid.uuid4()
        artifacts = {
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
        
        # Mock database operations
        agent_service.db.add_all = Mock()
        agent_service.db.commit = AsyncMock()
        
        await agent_service._save_execution_artifacts(execution_id, artifacts)
        
        # Verify artifacts were saved
        agent_service.db.add_all.assert_called_once()
        saved_artifacts = agent_service.db.add_all.call_args[0][0]
        
        assert len(saved_artifacts) == 2
        assert all(isinstance(art, ExecutionArtifact) for art in saved_artifacts)
        
        # Check first artifact
        schema_artifact = next(a for a in saved_artifacts if a.path == "/db/schema.sql")
        assert schema_artifact.artifact_type == "sql"
        assert schema_artifact.created_by == "DataModelingAgent"
        assert schema_artifact.language == "sql"
    
    async def test_get_execution_history(self, agent_service):
        """Test retrieving execution history for a project."""
        project_id = uuid.uuid4()
        
        # Mock database query
        mock_query = Mock()
        mock_result = Mock()
        mock_executions = [
            Mock(spec=Execution, id=uuid.uuid4(), status=ExecutionStatus.COMPLETED),
            Mock(spec=Execution, id=uuid.uuid4(), status=ExecutionStatus.FAILED)
        ]
        
        agent_service.db.query = Mock(return_value=mock_query)
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all = AsyncMock(return_value=mock_executions)
        
        # Get history
        history = await agent_service.get_execution_history(project_id, limit=10)
        
        assert len(history) == 2
        agent_service.db.query.assert_called_with(Execution)
        mock_query.filter.assert_called()
    
    async def test_get_execution_details(self, agent_service):
        """Test retrieving detailed execution information."""
        execution_id = uuid.uuid4()
        
        # Mock execution with relationships
        mock_execution = Mock(spec=Execution)
        mock_execution.id = execution_id
        mock_execution.messages = [
            Mock(spec=ExecutionMessage, content="Message 1"),
            Mock(spec=ExecutionMessage, content="Message 2")
        ]
        mock_execution.artifacts = [
            Mock(spec=ExecutionArtifact, path="/test.py")
        ]
        
        agent_service.db.get = AsyncMock(return_value=mock_execution)
        
        # Get details
        execution = await agent_service.get_execution_details(execution_id)
        
        assert execution == mock_execution
        agent_service.db.get.assert_called_with(Execution, execution_id)
    
    async def test_workflow_state_tracking(self, agent_service, mock_project):
        """Test that workflow state is properly tracked throughout execution."""
        final_state = {
            "messages": [
                {"role": "user", "content": "Build app"},
                {"role": "assistant", "content": "Plan created", "agent": "PlanningAgent"}
            ],
            "active_agent": "Done",
            "error_count": 0,
            "artifacts": {
                "schema.sql": {
                    "type": "sql",
                    "path": "/db/schema.sql",
                    "content": "CREATE TABLE...",
                    "created_by": "DataModelingAgent"
                }
            },
            "plan": {"steps": ["Create models", "Build API"]},
            "completed_agents": ["PlanningAgent", "DataModelingAgent"],
            "validation_results": {"l1": "passed", "l2": "passed"},
            "agent_history": [
                {
                    "from_agent": "PlanningAgent",
                    "to_agent": "DataModelingAgent",
                    "timestamp": datetime.utcnow().isoformat()
                }
            ]
        }
        
        with patch.object(agent_service.orchestrator, 'execute') as mock_execute:
            mock_execute.return_value = final_state
            
            # Mock database operations
            agent_service.db.add = Mock()
            agent_service.db.commit = AsyncMock()
            agent_service.db.refresh = AsyncMock()
            agent_service.db.add_all = Mock()
            
            # Execute
            execution = await agent_service.execute_task(
                project_id=mock_project.id,
                user_request="Build app",
                task_type=TaskType.FULLSTACK_DEVELOPMENT
            )
            
            # Verify state was properly stored
            assert execution.completed_agents == ["PlanningAgent", "DataModelingAgent"]
            assert execution.agent_history == final_state["agent_history"]
            assert execution.artifacts_count == 1
            assert execution.validation_results == {"l1": "passed", "l2": "passed"}
            assert execution.final_state == final_state
