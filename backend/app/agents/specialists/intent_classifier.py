"""
Intent Classifier Agent - Tier 1 of the DevMaster architecture.

This lightweight agent analyzes user prompts to determine the TaskType
and route to the appropriate workflow.
"""

from typing import Dict, Any
import logging

from ..base import BaseAgent, AgentResult
from ..state import DevMasterState, Message
from ..registry import register_agent


@register_agent("IntentClassifier")
class IntentClassifierAgent(BaseAgent):
    """
    Tier 1: Intent Classification
    
    Analyzes the user's prompt to determine:
    - Primary intent (chat, development, review, debug)
    - Complexity level
    - Required capabilities
    """
    
    def __init__(self, name: str = "IntentClassifier", **kwargs):
        super().__init__(
            name=name,
            description="Classifies user intent and determines task type"
        )
        self.logger = logging.getLogger(f"agent.{name}")
    
    async def execute(self, state: DevMasterState) -> AgentResult:
        """
        Analyze the user request and classify the intent.
        
        For now, this is a simple rule-based classifier.
        In production, this would use an LLM for nuanced understanding.
        """
        user_request = state.get("user_request", "").lower()
        
        # Simple rule-based classification
        task_type = self._classify_request(user_request)
        
        # Determine the next agent based on task type
        if task_type == "FULLSTACK_DEVELOPMENT":
            next_agent = "PlanningAgent"
        elif task_type == "CODE_REVIEW":
            next_agent = "CodeReviewAgent"
        elif task_type == "DEBUGGING":
            next_agent = "DebuggingAgent"
        else:  # CONVERSATIONAL_CHAT
            next_agent = "ChatAgent"
        
        # Create classification message
        message = self.add_message(
            f"Classified request as: {task_type}. Routing to {next_agent}."
        )
        
        return AgentResult(
            success=True,
            state_updates={
                "task_type": task_type,
                "status": "planning"
            },
            next_agent=next_agent,
            messages=[message]
        )
    
    def _classify_request(self, request: str) -> str:
        """
        Simple rule-based classification logic.
        
        In production, this would be replaced with an LLM call.
        """
        # Development keywords
        dev_keywords = [
            "build", "create", "develop", "make", "implement",
            "app", "application", "website", "api", "backend", "frontend",
            "database", "full-stack", "fullstack"
        ]
        
        # Review keywords
        review_keywords = [
            "review", "check", "analyze", "audit", "improve",
            "optimize", "refactor"
        ]
        
        # Debug keywords
        debug_keywords = [
            "debug", "fix", "error", "bug", "issue", "problem",
            "not working", "broken", "crash"
        ]
        
        # Check for development intent
        if any(keyword in request for keyword in dev_keywords):
            return "FULLSTACK_DEVELOPMENT"
        
        # Check for review intent
        if any(keyword in request for keyword in review_keywords):
            return "CODE_REVIEW"
        
        # Check for debugging intent
        if any(keyword in request for keyword in debug_keywords):
            return "DEBUGGING"
        
        # Default to conversational chat
        return "CONVERSATIONAL_CHAT"
    
    async def validate_preconditions(self, state: DevMasterState) -> bool:
        """Ensure we have a user request to classify."""
        return bool(state.get("user_request"))
