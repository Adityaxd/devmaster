"""
Tier 1: Intent Classification Agent

This agent analyzes user prompts to determine the TaskType.
It's the entry point for all user requests in the DevMaster platform.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from app.agents.base import BaseAgent
from app.core.state import DevMasterState, TaskType, AgentStatus
from app.core.llm import get_llm_client
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
        self.llm_client = get_llm_client()
    
    async def _analyze_prompt_with_llm(self, prompt: str) -> ScopeIntent:
        """Analyze the user prompt using LLM to determine intent."""
        
        # Create the system prompt
        system_prompt = """You are an intent classification agent for a software development platform.
        
Your task is to analyze user requests and classify them into one of these categories:
- FULLSTACK_DEVELOPMENT: Building complete applications with frontend and backend
- BACKEND_ONLY: API development, database design, server-side logic
- FRONTEND_ONLY: UI/UX development, React components, user interfaces
- CODE_REVIEW: Reviewing and improving existing code
- DEBUGGING: Finding and fixing bugs or errors
- DOCUMENTATION: Writing documentation, READMEs, or guides
- TESTING: Writing unit tests, integration tests, or test cases
- DEPLOYMENT: Setting up deployment, CI/CD, hosting
- CONVERSATIONAL_CHAT: General questions, help, or casual conversation

Respond with a JSON object containing:
{
    "primary_intent": "ONE_OF_THE_ABOVE_CATEGORIES",
    "confidence": 0.0-1.0,
    "keywords": ["relevant", "keywords", "from", "prompt"],
    "complexity": "simple|medium|complex",
    "requires_context": true|false,
    "sub_intents": ["SECONDARY_CATEGORIES_IF_ANY"],
    "reasoning": "Brief explanation of your classification"
}"""

        # Create the user prompt
        classification_prompt = f"""Analyze this user request and classify the intent:

User Request: "{prompt}"

Provide your classification as a JSON object."""

        try:
            # Get LLM response
            response = await self.llm_client.complete(
                prompt=classification_prompt,
                system_prompt=system_prompt,
                temperature=0.3,  # Lower temperature for more consistent classification
                use_cheap_model=True  # Use cheaper model for classification
            )
            
            # Parse the JSON response
            # First try to extract JSON from the response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                # Fallback if no JSON found
                raise ValueError("No JSON found in LLM response")
            
            # Map the string intent to TaskType enum
            primary_intent = TaskType(result["primary_intent"])
            
            # Extract sub_intents and map to TaskType
            sub_intents = []
            for sub_intent_str in result.get("sub_intents", []):
                try:
                    sub_intents.append(TaskType(sub_intent_str))
                except ValueError:
                    # Skip invalid task types
                    pass
            
            return ScopeIntent(
                primary_intent=primary_intent,
                confidence=result.get("confidence", 0.8),
                keywords=result.get("keywords", []),
                complexity=result.get("complexity", "medium"),
                requires_context=result.get("requires_context", False),
                sub_intents=sub_intents,
                metadata={
                    "prompt_length": len(prompt),
                    "reasoning": result.get("reasoning", ""),
                    "analyzed_at": datetime.now(timezone.utc).isoformat(),
                    "llm_used": True
                }
            )
            
        except Exception as e:
            self.logger.warning(f"LLM classification failed: {str(e)}. Falling back to pattern matching.")
            # Fall back to pattern matching
            return await self._analyze_prompt_pattern_matching(prompt)
    
    async def _analyze_prompt_pattern_matching(self, prompt: str) -> ScopeIntent:
        """Fallback pattern matching for when LLM is unavailable."""
        prompt_lower = prompt.lower().strip()
        
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
        
        # Score each TaskType based on keyword and pattern matching
        scores: Dict[TaskType, float] = {}
        matched_keywords: Dict[TaskType, List[str]] = {}
        
        for task_type, config in INTENT_PATTERNS.items():
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
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
                "llm_used": False
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
        
        # Analyze the prompt (try LLM first, fall back to patterns)
        intent = await self._analyze_prompt_with_llm(user_request)
        
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
        
        # Log the classification
        self.logger.info(
            f"Intent classified: {intent.primary_intent.value} "
            f"(confidence: {intent.confidence}, complexity: {intent.complexity})"
        )
        
        return {
            "messages": messages,
            "intent": intent.model_dump(),
            "active_agent": "CapabilityRouter"  # Hand off to next tier
        }
    
    async def validate(self, state: DevMasterState) -> bool:
        """Validate that classification can proceed."""
        return bool(state.get("user_request"))
