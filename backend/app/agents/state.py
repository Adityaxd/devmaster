"""
Core state management for DevMaster agents.

This module defines the shared state that flows through the entire agent graph.
Following LangGraph patterns, all agents read from and write to this unified state.
"""

from typing import TypedDict, List, Dict, Any, Optional, Literal
from datetime import datetime
from pydantic import BaseModel


class Message(BaseModel):
    """A message in the conversation history."""
    role: Literal["user", "assistant", "system", "agent"]
    content: str
    timestamp: datetime
    agent_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class Artifact(BaseModel):
    """Generated code artifact."""
    id: str
    type: Literal["sql", "python", "typescript", "json", "yaml", "text"]
    path: str
    content: str
    validation_status: Literal["pending", "passed", "failed"] = "pending"
    validation_errors: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime


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
    """
    # Request Information
    user_request: str
    project_id: str
    task_type: Literal["CONVERSATIONAL_CHAT", "FULLSTACK_DEVELOPMENT", "CODE_REVIEW", "DEBUGGING"]
    
    # Agent Control Flow
    active_agent: str  # Name of the currently active agent
    next_agent: Optional[str]  # Explicitly set next agent (overrides routing)
    completed_agents: List[str]  # Agents that have completed their tasks
    
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
    errors: List[Dict[str, Any]]  # Error details
    retry_count: int
    max_retries: int
    
    # Metadata
    start_time: str  # ISO format timestamp
    last_update: str  # ISO format timestamp
    status: Literal["initializing", "planning", "executing", "validating", "completed", "failed", "paused"]
    
    # Additional Context
    context: Dict[str, Any]  # Flexible field for agent-specific data
