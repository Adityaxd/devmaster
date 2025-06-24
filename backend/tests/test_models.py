"""Tests for database models."""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import uuid

from app.models import User, Project, Execution, ExecutionMessage, ExecutionArtifact
from app.models.project import ProjectStatus, ProjectType
from app.models.execution import ExecutionStatus, TaskType


class TestUserModel:
    """Test User model."""
    
    async def test_create_user(self, async_session: AsyncSession):
        """Test creating a new user."""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password_here",
            full_name="Test User"
        )
        
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)
        
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.is_active is True
        assert user.is_superuser is False
        assert user.email_verified is False
        assert user.created_at is not None
        assert user.updated_at is not None
    
    async def test_unique_email_constraint(self, async_session: AsyncSession):
        """Test that email must be unique."""
        user1 = User(
            email="duplicate@example.com",
            username="user1",
            hashed_password="password"
        )
        user2 = User(
            email="duplicate@example.com",
            username="user2",
            hashed_password="password"
        )
        
        async_session.add(user1)
        await async_session.commit()
        
        async_session.add(user2)
        with pytest.raises(IntegrityError):
            await async_session.commit()
    
    async def test_unique_username_constraint(self, async_session: AsyncSession):
        """Test that username must be unique."""
        user1 = User(
            email="user1@example.com",
            username="duplicate",
            hashed_password="password"
        )
        user2 = User(
            email="user2@example.com",
            username="duplicate",
            hashed_password="password"
        )
        
        async_session.add(user1)
        await async_session.commit()
        
        async_session.add(user2)
        with pytest.raises(IntegrityError):
            await async_session.commit()


class TestProjectModel:
    """Test Project model."""
    
    async def test_create_project(self, async_session: AsyncSession, test_user: User):
        """Test creating a new project."""
        project = Project(
            name="Test Project",
            description="A test project",
            owner_id=test_user.id,
            project_type=ProjectType.FULLSTACK_WEB,
            technology_stack={
                "backend": "FastAPI",
                "frontend": "React",
                "database": "PostgreSQL"
            }
        )
        
        async_session.add(project)
        await async_session.commit()
        await async_session.refresh(project)
        
        assert project.id is not None
        assert project.name == "Test Project"
        assert project.status == ProjectStatus.ACTIVE
        assert project.owner_id == test_user.id
        assert project.is_deployed is False
        assert project.technology_stack["backend"] == "FastAPI"
    
    async def test_project_cascade_delete(self, async_session: AsyncSession, test_user: User):
        """Test that deleting a user cascades to projects."""
        project = Project(
            name="Test Project",
            owner_id=test_user.id
        )
        
        async_session.add(project)
        await async_session.commit()
        
        # Delete the user
        await async_session.delete(test_user)
        await async_session.commit()
        
        # Project should be deleted
        result = await async_session.get(Project, project.id)
        assert result is None


class TestExecutionModel:
    """Test Execution model."""
    
    async def test_create_execution(self, async_session: AsyncSession, test_project: Project):
        """Test creating a new execution."""
        execution = Execution(
            project_id=test_project.id,
            user_request="Build a todo app",
            task_type=TaskType.FULLSTACK_DEVELOPMENT
        )
        
        async_session.add(execution)
        await async_session.commit()
        await async_session.refresh(execution)
        
        assert execution.id is not None
        assert execution.project_id == test_project.id
        assert execution.status == ExecutionStatus.INITIALIZING
        assert execution.error_count == 0
        assert execution.artifacts_count == 0
        assert execution.completed_agents == []
        assert execution.agent_history == []
    
    async def test_execution_relationships(self, async_session: AsyncSession, test_execution: Execution):
        """Test execution relationships."""
        # Add a message
        message = ExecutionMessage(
            execution_id=test_execution.id,
            role="assistant",
            content="Starting execution",
            agent_name="PlanningAgent"
        )
        
        # Add an artifact
        artifact = ExecutionArtifact(
            execution_id=test_execution.id,
            artifact_type="file",
            path="/models/user.py",
            content="class User(Base): ...",
            language="python",
            created_by="DataModelingAgent"
        )
        
        async_session.add_all([message, artifact])
        await async_session.commit()
        
        # Refresh and check relationships
        await async_session.refresh(test_execution)
        
        messages = await async_session.run_sync(lambda session: test_execution.messages)
        artifacts = await async_session.run_sync(lambda session: test_execution.artifacts)
        
        assert len(messages) == 1
        assert messages[0].content == "Starting execution"
        assert len(artifacts) == 1
        assert artifacts[0].path == "/models/user.py"


class TestExecutionMessage:
    """Test ExecutionMessage model."""
    
    async def test_message_metadata_field(self, async_session: AsyncSession, test_execution: Execution):
        """Test that metadata field doesn't conflict with SQLAlchemy."""
        message = ExecutionMessage(
            execution_id=test_execution.id,
            role="system",
            content="System message",
            message_metadata={"key": "value"}
        )
        
        async_session.add(message)
        await async_session.commit()
        await async_session.refresh(message)
        
        assert message.message_metadata == {"key": "value"}
        # Verify the column name is still 'metadata' in the database
        assert "metadata" in ExecutionMessage.__table__.columns


class TestExecutionArtifact:
    """Test ExecutionArtifact model."""
    
    async def test_create_artifact(self, async_session: AsyncSession, test_execution: Execution):
        """Test creating an artifact."""
        artifact = ExecutionArtifact(
            execution_id=test_execution.id,
            artifact_type="schema",
            path="/migrations/001_initial.sql",
            content="CREATE TABLE users (...);",
            language="sql",
            created_by="DataModelingAgent",
            validation_status="passed"
        )
        
        async_session.add(artifact)
        await async_session.commit()
        await async_session.refresh(artifact)
        
        assert artifact.id is not None
        assert artifact.validation_status == "passed"
        assert artifact.validation_errors == []
        assert artifact.created_by == "DataModelingAgent"
    
    async def test_artifact_cascade_delete(self, async_session: AsyncSession, test_execution: Execution):
        """Test that deleting an execution cascades to artifacts."""
        artifact = ExecutionArtifact(
            execution_id=test_execution.id,
            artifact_type="file",
            path="/test.py",
            content="print('test')",
            created_by="TestAgent"
        )
        
        async_session.add(artifact)
        await async_session.commit()
        
        # Delete the execution
        await async_session.delete(test_execution)
        await async_session.commit()
        
        # Artifact should be deleted
        result = await async_session.get(ExecutionArtifact, artifact.id)
        assert result is None
