"""Execution models for tracking agent runs and results."""

from sqlalchemy import Column, String, Text, Integer, ForeignKey, Enum, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum

from .base import Base, TimestampMixin


class ExecutionStatus(str, enum.Enum):
    """Status of an execution."""
    INITIALIZING = "initializing"
    PLANNING = "planning"
    EXECUTING = "executing"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, enum.Enum):
    """Type of task being executed."""
    CONVERSATIONAL_CHAT = "conversational_chat"
    FULLSTACK_DEVELOPMENT = "fullstack_development"
    CODE_REVIEW = "code_review"
    DEBUGGING = "debugging"
    DOCUMENTATION = "documentation"


class Execution(Base, TimestampMixin):
    """
    Execution model for tracking agent orchestration runs.
    
    Each execution represents a single run of the agent swarm
    in response to a user request.
    """
    __tablename__ = "executions"
    __table_args__ = (
        Index("ix_executions_project_status", "project_id", "status"),
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    
    # Relationship to project
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Execution details
    user_request = Column(Text, nullable=False)
    task_type = Column(Enum(TaskType), nullable=False)
    status = Column(
        Enum(ExecutionStatus),
        default=ExecutionStatus.INITIALIZING,
        nullable=False,
        index=True
    )
    
    # Agent tracking
    active_agent = Column(String(100))
    completed_agents = Column(JSON, default=list)  # List of completed agent names
    agent_history = Column(JSON, default=list)  # Detailed execution history
    
    # Results
    plan = Column(JSON)  # The generated plan
    artifacts_count = Column(Integer, default=0)
    validation_results = Column(JSON, default=dict)
    
    # Error tracking
    error_count = Column(Integer, default=0)
    error_messages = Column(JSON, default=list)
    
    # State snapshot
    final_state = Column(JSON)  # Complete final state for debugging
    
    # Relationships
    project = relationship("Project", back_populates="executions")
    messages = relationship("ExecutionMessage", back_populates="execution", cascade="all, delete-orphan")
    artifacts = relationship("ExecutionArtifact", back_populates="execution", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Execution(id={self.id}, project_id={self.project_id}, status='{self.status}')>"


class ExecutionMessage(Base, TimestampMixin):
    """
    Messages generated during an execution.
    
    Tracks all messages from agents, users, and the system.
    """
    __tablename__ = "execution_messages"
    __table_args__ = (
        Index("ix_execution_messages_execution_id", "execution_id"),
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    
    execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("executions.id", ondelete="CASCADE"),
        nullable=False
    )
    
    role = Column(String(50), nullable=False)  # user, assistant, system, agent
    content = Column(Text, nullable=False)
    agent_name = Column(String(100))  # Which agent sent this
    message_metadata = Column("metadata", JSON, default=dict)
    
    # Relationships
    execution = relationship("Execution", back_populates="messages")


class ExecutionArtifact(Base, TimestampMixin):
    """
    Artifacts (files, code, etc.) generated during an execution.
    """
    __tablename__ = "execution_artifacts"
    __table_args__ = (
        Index("ix_execution_artifacts_execution_id", "execution_id"),
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    
    execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("executions.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Artifact details
    artifact_type = Column(String(50), nullable=False)  # file, code, schema, etc.
    path = Column(String(500), nullable=False)  # File path in project
    content = Column(Text, nullable=False)  # The actual content
    language = Column(String(50))  # Programming language if applicable
    
    # Validation
    validation_status = Column(String(50), default="pending")  # pending, passed, failed
    validation_errors = Column(JSON, default=list)
    
    # Agent tracking
    created_by = Column(String(100), nullable=False)  # Which agent created this
    
    # Relationships
    execution = relationship("Execution", back_populates="artifacts")
