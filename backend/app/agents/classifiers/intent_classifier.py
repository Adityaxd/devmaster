"""
Tier 1: Intent Classification Agent

This agent analyzes user prompts to determine the TaskType.
It's the entry point for all user requests in the DevMaster platform.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from app.agents.base import BaseAgent
from app.core.state import DevMasterState, TaskType, AgentStatus
import json
import re
from datetime import datetime, timezone


class ScopeIntent(BaseModel):
    """Structured representation of user intent."""
    
    primary_intent: TaskType = Field(
        description="The main type of task the user is requesting"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence score for the classification"
    )
    keywords: List[str] = Field(
        default_factory=list,
        description="Key terms that influenced the classification"
    )
    complexity: str = Field(
        default="medium",
        description="Estimated complexity: simple, medium, complex"
    )
    requires_context: bool = Field(
        default=False,
        description="Whether the request needs additional context"
    )
    sub_intents: List[TaskType] = Field(
        default_factory=list,
        description="Secondary intents detected in the request"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the intent"
    )


class IntentClassifier(BaseAgent):
    """
    Tier 1 Agent: Intent Classification
    
    Analyzes user prompts to determine:
    - What type of task the user is requesting (TaskType)
    - The complexity and scope of the request
    - Whether additional context is needed
    - Any secondary intents in the request
    """
    
    def __init__(self):
        super().__init__(
            name="IntentClassifier",
            description="Analyzes user requests to determine intent and task type"
        )
    
    # Keywords and patterns for each TaskType
    INTENT_PATTERNS = {
        TaskType.FULLSTACK_DEVELOPMENT: {
            "keywords": [
                "build", "create", "develop", "app", "application", "website",
                "platform", "system", "full-stack", "fullstack", "web app",
                "crud", "api", "database", "frontend", "backend"
            ],
            "patterns": [
                r"build\s+(?:me\s+)?(?:a|an)\s+\w+\s+(?:app|application|platform|system)",
                r"create\s+(?:a|an)\s+\w+\s+(?:for|that|with)",
                r"i\s+(?:need|want)\s+(?:a|an)\s+\w+\s+(?:app|application|system)",
                r"develop\s+(?:a|an)\s+\w+\s+(?:platform|service|api)"
            ]
        },
        TaskType.BACKEND_ONLY: {
            "keywords": [
                "api", "backend", "server", "endpoint", "microservice",
                "rest", "graphql", "service", "database schema", "migration"
            ],
            "patterns": [
                r"(?:create|build|design)\s+(?:an?\s+)?api\s+(?:for|that)",
                r"backend\s+(?:service|api|server)\s+(?:for|that)",
                r"database\s+(?:schema|design|structure)\s+(?:for|that)",
                r"rest(?:ful)?\s+api\s+(?:for|that|with)"
            ]
        },
        TaskType.FRONTEND_ONLY: {
            "keywords": [
                "ui", "interface", "frontend", "react", "component",
                "design", "layout", "page", "view", "dashboard", "landing"
            ],
            "patterns": [
                r"(?:create|build|design)\s+(?:a|an|the)?\s*(?:ui|interface|frontend)",
                r"react\s+(?:component|app|page)\s+(?:for|that)",
                r"(?:landing|dashboard|admin)\s+(?:page|interface)",
                r"user\s+interface\s+(?:for|that|with)"
            ]
        },
        TaskType.CODE_REVIEW: {
            "keywords": [
                "review", "check", "analyze", "improve", "refactor",
                "optimize", "fix", "debug", "issue", "problem", "error"
            ],
            "patterns": [
                r"review\s+(?:my|this|the)\s+code",
                r"check\s+(?:my|this|the)\s+(?:code|implementation)",
                r"(?:find|fix)\s+(?:bugs?|issues?|problems?|errors?)",
                r"improve\s+(?:my|this|the)\s+(?:code|implementation)"
            ]
        },
        TaskType.DEBUGGING: {
            "keywords": [
                "debug", "error", "bug", "issue", "problem", "crash",
                "not working", "broken", "fail", "exception", "stack trace"
            ],
            "patterns": [
                r"(?:debug|fix)\s+(?:this|my|the)\s+(?:error|bug|issue)",
                r"(?:getting|have|got)\s+(?:an?\s+)?error",
                r"(?:is|it's)\s+not\s+working",
                r"(?:help|assist)\s+(?:me\s+)?(?:debug|fix)"
            ]
        },
        TaskType.DOCUMENTATION: {
            "keywords": [
                "document", "docs", "readme", "guide", "tutorial",
                "explain", "describe", "write documentation", "api docs"
            ],
            "patterns": [
                r"(?:write|create|generate)\s+(?:documentation|docs)",
                r"document\s+(?:my|this|the)\s+(?:code|api|project)",
                r"(?:create|write)\s+(?:a|an)?\s*readme",
                r"(?:api|code)\s+documentation"
            ]
        },
        TaskType.TESTING: {
            "keywords": [
                "test", "testing", "unit test", "integration test",
                "test case", "pytest", "jest", "coverage", "qa"
            ],
            "patterns": [
                r"(?:write|create|generate)\s+(?:tests?|test cases?)",
                r"(?:unit|integration|e2e)\s+tests?\s+(?:for|that)",
                r"test\s+(?:my|this|the)\s+(?:code|function|component)",
                r"(?:add|create)\s+test\s+coverage"
            ]
        },
        TaskType.DEPLOYMENT: {
            "keywords": [
                "deploy", "deployment", "host", "hosting", "production",
                "docker", "kubernetes", "ci/cd", "devops", "release"
            ],
            "patterns": [
                r"deploy\s+(?:my|this|the)\s+(?:app|application|project)",
                r"(?:set\s*up|setup)\s+(?:deployment|ci\/?cd)",
                r"host\s+(?:my|this|the)\s+(?:app|application)",
                r"(?:production|staging)\s+(?:deployment|release)"
            ]
        },
        TaskType.CONVERSATIONAL_CHAT: {
            "keywords": [
                "hello", "hi", "help", "what", "how", "why", "when",
                "explain", "tell me", "can you", "please"
            ],
            "patterns": [
                r"^(?:hi|hello|hey)",
                r"^(?:what|how|why|when)\s+(?:is|are|do|does|can)",
                r"^(?:explain|tell\s+me|help\s+me\s+understand)",
                r"^(?:can\s+you|could\s+you|would\s+you)"
            ]
        }
    }
    
    async def _analyze_prompt(self, prompt: str) -> ScopeIntent:
        """Analyze the user prompt to determine intent."""
        prompt_lower = prompt.lower().strip()
        
        # Score each TaskType based on keyword and pattern matching
        scores: Dict[TaskType, float] = {}
        matched_keywords: Dict[TaskType, List[str]] = {}
        
        for task_type, config in self.INTENT_PATTERNS.items():
            score = 0.0
            keywords_found = []
            
            # Check keywords
            for keyword in config["keywords"]:
                if keyword in prompt_lower:
                    score += 0.1
                    keywords_found.append(keyword)
            
            # Check patterns
            for pattern in config["patterns"]:
                if re.search(pattern, prompt_lower, re.IGNORECASE):
                    score += 0.3
            
            scores[task_type] = min(score, 1.0)  # Cap at 1.0
            matched_keywords[task_type] = keywords_found
        
        # Determine primary intent
        if not scores or max(scores.values()) == 0:
            # Default to chat if no clear intent
            primary_intent = TaskType.CONVERSATIONAL_CHAT
            confidence = 0.5
        else:
            primary_intent = max(scores, key=scores.get)
            confidence = scores[primary_intent]
        
        # Find secondary intents
        sub_intents = [
            task_type for task_type, score in scores.items()
            if task_type != primary_intent and score > 0.2
        ]
        
        # Estimate complexity
        complexity = self._estimate_complexity(prompt, primary_intent)
        
        # Check if additional context is needed
        requires_context = self._needs_context(prompt, confidence)
        
        return ScopeIntent(
            primary_intent=primary_intent,
            confidence=confidence,
            keywords=matched_keywords.get(primary_intent, []),
            complexity=complexity,
            requires_context=requires_context,
            sub_intents=sub_intents,
            metadata={
                "prompt_length": len(prompt),
                "all_scores": {k.value: v for k, v in scores.items()},
                "analyzed_at": datetime.now(timezone.utc).isoformat()
            }
        )
    
    def _estimate_complexity(self, prompt: str, intent: TaskType) -> str:
        """Estimate the complexity of the request."""
        prompt_lower = prompt.lower()
        
        # Simple indicators
        simple_indicators = ["simple", "basic", "quick", "small", "demo", "example"]
        complex_indicators = ["complex", "advanced", "full", "complete", "production", "scalable"]
        
        if any(word in prompt_lower for word in simple_indicators):
            return "simple"
        elif any(word in prompt_lower for word in complex_indicators):
            return "complex"
        
        # Estimate based on intent and prompt length
        if intent in [TaskType.CONVERSATIONAL_CHAT, TaskType.DOCUMENTATION]:
            return "simple"
        elif intent == TaskType.FULLSTACK_DEVELOPMENT:
            return "complex" if len(prompt) > 200 else "medium"
        
        return "medium"
    
    def _needs_context(self, prompt: str, confidence: float) -> bool:
        """Determine if additional context is needed."""
        # Low confidence suggests ambiguity
        if confidence < 0.6:
            return True
        
        # Check for vague terms
        vague_terms = ["it", "this", "that", "the thing", "stuff", "something"]
        prompt_lower = prompt.lower()
        
        return any(term in prompt_lower for term in vague_terms)
    
    async def _execute_impl(self, state: DevMasterState) -> Dict[str, Any]:
        """Execute the intent classification."""
        # Get the user request from state
        user_request = state.get("user_request", "")
        if not user_request:
            raise ValueError("No user request found in state")
        
        # Analyze the prompt
        intent = await self._analyze_prompt(user_request)
        
        # Prepare the message
        message = {
            "role": "IntentClassifier",
            "content": f"Classified request as: {intent.primary_intent.value}",
            "metadata": {
                "intent": intent.model_dump(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        
        # Update state
        messages = state.get("messages", []).copy()
        messages.append(message)
        
        return {
            "messages": messages,
            "intent": intent.model_dump(),
            "active_agent": "CapabilityRouter"  # Hand off to next tier
        }
    
    async def validate(self, state: DevMasterState) -> bool:
        """Validate that classification can proceed."""
        return bool(state.get("user_request"))
