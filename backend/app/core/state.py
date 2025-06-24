"""
DevMaster State Management
Defines the shared state structure for the entire agent swarm.

This module defines the shared state that flows through the entire agent graph.
Following LangGraph patterns, all agents read from and write to this unified state.
This is the "Universal Context" that all agents operate on.
"""
from typing import TypedDict, List, Dict, Any, Optional, Literal
from datetime import datetime
from enum import Enum
from pydantic import BaseModel


class TaskType(str, Enum):
    """Types of tasks the system can handle."""
    CONVERSATIONAL_CHAT = "conversational_chat"
    FULLSTACK_DEVELOPMENT = "fullstack_development"
    BACKEND_ONLY = "backend_only"
    FRONTEND_ONLY = "frontend_only"
    CODE_REVIEW = "code_review"
    DEBUGGING = "debugging"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    DEPLOYMENT = "deployment"


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


class Message(BaseModel):
    """Message in the conversation history."""
    role: Literal["user", "assistant", "system", "agent"]
    content: str
    timestamp: datetime
    agent_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class Artifact(BaseModel):
    """Generated code artifact."""
    id: str
    type: Literal["sql", "python", "typescript", "json", "yaml", "text", "file", "code", "schema", "api", "ui_component", "test"]
    path: str
    content: str
    language: Optional[str] = None
    validation_status: Literal["pending", "passed", "failed"] = "pending"
    validation_errors: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime
    created_by: str  # Agent name that created this artifact


class ValidationResult(BaseModel):
    """Result of code validation."""
    level: Literal["L1", "L2", "L3"]  # Static, Unit, Integration
    passed: bool
    errors: List[str]
    warnings: List[str]
    timestamp: datetime


class DevMasterState(TypedDict):
    """
    The unified state object that flows through the agent graph.
    
    This is the "Universal Context" that all agents share. Each agent
    can read the entire state but should only write to relevant fields.
    
    Following LangGraph patterns, this state is passed between nodes (agents)
    in the graph, with the 'active_agent' field controlling routing.
    """
    # Request Information
    user_request: str
    project_id: str
    task_type: TaskType  # Using the enum for type safety
    
    # Agent Control Flow (Critical for LangGraph routing)
    active_agent: str  # Name of the currently active agent
    next_agent: Optional[str]  # Explicitly set next agent (overrides routing)
    completed_agents: List[str]  # Agents that have completed their tasks
    agent_history: List[Dict[str, Any]]  # Track agent executions with timestamps
    
    # Conversation & Messages
    messages: List[Dict[str, Any]]  # Serialized Message objects
    
    # Planning & Analysis
    plan: Optional[Dict[str, Any]]  # Generated project plan
    requirements: Optional[Dict[str, Any]]  # Parsed requirements
    
    # Generated Artifacts
    artifacts: Dict[str, Dict[str, Any]]  # Keyed by artifact ID, serialized Artifact objects
    
    # Validation Results
    validation_results: List[Dict[str, Any]]  # Serialized ValidationResult objects
    
    # Error Handling
    error_count: int
    error_messages: List[str]  # Renamed from 'errors' to be more specific
    retry_count: int
    max_retries: int
    
    # Project Status
    project_status: ProjectStatus  # Overall project status
    
    # Metadata
    created_at: str  # ISO format timestamp
    updated_at: str  # ISO format timestamp
    metadata: Dict[str, Any]  # Flexible field for additional data
    
    # Classification specific fields (Week 3 - optional for now)
    intent: Optional[Dict[str, Any]]
    routing_decision: Optional[Dict[str, Any]]
    selected_workflow: Optional[str]
    workflow_agents: Optional[List[str]]
    current_workflow_index: Optional[int]
    
    # Additional Context
    context: Dict[str, Any]  # Flexible field for agent-specific data
