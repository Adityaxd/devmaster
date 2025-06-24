"""
Chat Agent for conversational interactions.

This is a simple agent that handles conversational chat requests.
It will be replaced with an LLM-powered version in production.
"""

from typing import Dict, Any
from app.agents.base import BaseAgent
from app.core.state import DevMasterState, AgentStatus
from datetime import datetime


class ChatAgent(BaseAgent):
    """
    Simple chat agent for conversational interactions.
    
    This agent handles basic conversational requests when the user
    isn't asking for development tasks.
    """
    
    def __init__(self):
        super().__init__(
            name="ChatAgent",
            description="Handles conversational chat interactions"
        )
    
    # Predefined responses for demo purposes
    RESPONSES = {
        "greeting": [
            "Hello! I'm DevMaster, your AI-powered development assistant. "
            "I can help you build full-stack applications, create APIs, "
            "design user interfaces, and much more. What would you like to create today?"
        ],
        "capabilities": [
            "I can help you with:\n"
            "🚀 Full-stack application development\n"
            "🔧 Backend API creation\n"
            "🎨 Frontend UI development\n"
            "🔍 Code review and optimization\n"
            "🐛 Debugging and error fixing\n"
            "📚 Documentation generation\n"
            "🧪 Test creation\n"
            "☁️ Deployment assistance\n\n"
            "Just describe what you want to build, and I'll take care of the rest!"
        ],
        "help": [
            "To get started, try asking me to:\n"
            "• 'Build a todo list application'\n"
            "• 'Create a REST API for user management'\n"
            "• 'Design a landing page for my startup'\n"
            "• 'Review my Python code'\n"
            "• 'Help me debug this error'\n\n"
            "I'll analyze your request and use the appropriate workflow to help you."
        ],
        "default": [
            "I understand you're looking for conversational assistance. "
            "While I'm primarily designed for development tasks, "
            "I'm here to help! Could you tell me more about what you need?"
        ]
    }
    
    async def _generate_response(self, user_request: str) -> str:
        """Generate a response based on the user request."""
        request_lower = user_request.lower().strip()
        
        # Check for greetings
        greetings = ["hello", "hi", "hey", "greetings", "good morning", "good afternoon"]
        if any(greeting in request_lower for greeting in greetings):
            return self.RESPONSES["greeting"][0]
        
        # Check for capability questions
        capability_keywords = ["what can you do", "capabilities", "features", "help me with"]
        if any(keyword in request_lower for keyword in capability_keywords):
            return self.RESPONSES["capabilities"][0]
        
        # Check for help requests
        help_keywords = ["help", "how to", "get started", "example", "guide"]
        if any(keyword in request_lower for keyword in help_keywords):
            return self.RESPONSES["help"][0]
        
        # Default response
        return self.RESPONSES["default"][0]
    
    async def _execute_impl(self, state: DevMasterState) -> Dict[str, Any]:
        """Execute the chat interaction."""
        # Get user request
        user_request = state.get("user_request", "")
        
        # Generate response
        response = await self._generate_response(user_request)
        
        # Prepare the message
        message = {
            "role": "ChatAgent",
            "content": response,
            "metadata": {
                "interaction_type": "conversational",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        # Update state
        messages = state.get("messages", []).copy()
        messages.append(message)
        
        return {
            "messages": messages,
            "active_agent": "Done"  # End the workflow
        }
    
    async def validate(self, state: DevMasterState) -> bool:
        """Validate that chat can proceed."""
        return True  # Chat agent can always proceed
