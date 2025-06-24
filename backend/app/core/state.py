"""
DevMaster State Management
Defines the shared state structure for the entire agent swarm
"""
from typing import TypedDict, List, Dict, Any, Optional, Literal
from datetime import datetime
from enum import Enum


class TaskType(str, Enum):
    """Types of tasks the system can handle."""
    CONVERSATIONAL_CHAT = "conversational_chat"
    FULLSTACK_DEVELOPMENT = "fullstack_development"
    CODE_REVIEW = "code_review"
    DEBUGGING = "debugging"
    DOCUMENTATION = "documentation"


class AgentStatus(str, Enum):
    """Status of an agent execution."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING = "waiting"


class ProjectStatus(str, Enum):
    """Overall project status."""
    INITIALIZING = "initializing"
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    VALIDATING = "validating"
    COMPLETED = "completed"
    ERROR = "error"
    ERROR_REQUIRES_HUMAN_INPUT = "error_requires_human_input"

class ValidationResult(TypedDict):
    """Result of a validation step."""
    level: Literal["L1", "L2", "L3"]
    passed: bool
    errors: List[str]
    warnings: List[str]


class Artifact(TypedDict):
    """Represents a generated artifact (file, code, etc.)."""
    id: str
    type: Literal["file", "code", "schema", "api", "ui_component", "test"]
    path: str
    content: str
    language: Optional[str]
    created_at: datetime
    created_by: str  # Agent name
    validation_results: List[ValidationResult]


class Message(TypedDict):
    """Message in the conversation."""
    id: str
    role: Literal["user", "assistant", "system", "agent"]
    content: str
    timestamp: datetime
    agent_name: Optional[str]
    metadata: Dict[str, Any]


class DevMasterState(TypedDict):
    """
    The shared state for the entire DevMaster swarm.
    This is the "Universal Context" that all agents operate on.
    """
    # Request Information
    user_request: str
    task_type: TaskType
    project_id: str
    
    # Agent Control
    active_agent: str
    agent_history: List[Dict[str, Any]]  # Track agent executions
    
    # Planning
    plan: Dict[str, Any]
    requirements: Dict[str, Any]
    
    # Artifacts
    artifacts: Dict[str, Artifact]  # Keyed by artifact ID
    
    # Validation
    validation_results: Dict[str, List[ValidationResult]]
    
    # Conversation
    messages: List[Message]
    
    # Project Status
    project_status: ProjectStatus
    error_count: int
    error_messages: List[str]
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]