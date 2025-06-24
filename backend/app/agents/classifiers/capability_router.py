"""
Tier 2: Capability Router Agent

This agent takes the classified intent and routes it to the appropriate workflow.
It selects the right "Swarm Template" based on the TaskType.
"""

from typing import Dict, Any, Optional, List, Literal
from pydantic import BaseModel, Field
from app.agents.base import BaseAgent
from app.core.state import DevMasterState, TaskType, AgentStatus
from datetime import datetime


class WorkflowTemplate(BaseModel):
    """Represents a workflow template for a specific capability."""
    
    name: str = Field(description="Name of the workflow")
    description: str = Field(description="Description of what this workflow does")
    agents: List[str] = Field(description="Ordered list of agents in this workflow")
    requires_llm: bool = Field(default=True, description="Whether this workflow needs LLM")
    estimated_duration: str = Field(default="medium", description="Estimated time to complete")
    complexity: Literal["simple", "medium", "complex"] = Field(default="medium")


class RoutingDecision(BaseModel):
    """Represents the routing decision made by the CapabilityRouter."""
    
    selected_workflow: str = Field(description="Name of the selected workflow")
    workflow_template: WorkflowTemplate = Field(description="The workflow template to execute")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the routing decision")
    alternative_workflows: List[str] = Field(
        default_factory=list,
        description="Alternative workflows that could be used"
    )
    reasoning: str = Field(description="Explanation for the routing decision")
    warnings: List[str] = Field(
        default_factory=list,
        description="Any warnings or considerations"
    )


class CapabilityRouter(BaseAgent):
    """
    Tier 2 Agent: Capability Router
    
    Takes the intent classification and routes to the appropriate workflow:
    - Maps TaskType to specific workflow templates
    - Considers complexity and context when selecting workflows
    - Provides alternative routing options when appropriate
    """
    
    def __init__(self):
        super().__init__(
            name="CapabilityRouter",
            description="Routes classified intents to appropriate workflow templates"
        )
    
    # Workflow templates for each capability
    WORKFLOW_TEMPLATES = {
        "software_assembly_line": WorkflowTemplate(
            name="Software Assembly Line",
            description="Full-stack application development workflow",
            agents=[
                "PlanningAgent",
                "DataModelingAgent",
                "BackendLogicAgent",
                "APIGenerationAgent",
                "SDKGenerationAgent",
                "FrontendAgent",
                "TestingAgent",
                "IntegrationAgent"
            ],
            requires_llm=True,
            estimated_duration="long",
            complexity="complex"
        ),
        "backend_api_workflow": WorkflowTemplate(
            name="Backend API Workflow",
            description="Backend-only API development workflow",
            agents=[
                "PlanningAgent",
                "DataModelingAgent",
                "BackendLogicAgent",
                "APIGenerationAgent",
                "TestingAgent"
            ],
            requires_llm=True,
            estimated_duration="medium",
            complexity="medium"
        ),
        "frontend_ui_workflow": WorkflowTemplate(
            name="Frontend UI Workflow",
            description="Frontend-only UI development workflow",
            agents=[
                "PlanningAgent",
                "FrontendAgent",
                "UITestingAgent"
            ],
            requires_llm=True,
            estimated_duration="medium",
            complexity="medium"
        ),
        "code_review_workflow": WorkflowTemplate(
            name="Code Review Workflow",
            description="Analyze and improve existing code",
            agents=[
                "CodeAnalysisAgent",
                "ReviewAgent",
                "RefactoringAgent"
            ],
            requires_llm=True,
            estimated_duration="short",
            complexity="simple"
        ),
        "debugging_workflow": WorkflowTemplate(
            name="Debugging Workflow",
            description="Debug and fix code issues",
            agents=[
                "ErrorAnalysisAgent",
                "DebuggingAgent",
                "FixValidationAgent"
            ],
            requires_llm=True,
            estimated_duration="medium",
            complexity="medium"
        ),
        "documentation_workflow": WorkflowTemplate(
            name="Documentation Workflow",
            description="Generate or improve documentation",
            agents=[
                "DocAnalysisAgent",
                "DocumentationAgent"
            ],
            requires_llm=True,
            estimated_duration="short",
            complexity="simple"
        ),
        "testing_workflow": WorkflowTemplate(
            name="Testing Workflow",
            description="Generate comprehensive tests",
            agents=[
                "TestPlanningAgent",
                "TestGenerationAgent",
                "TestExecutionAgent"
            ],
            requires_llm=True,
            estimated_duration="medium",
            complexity="medium"
        ),
        "deployment_workflow": WorkflowTemplate(
            name="Deployment Workflow",
            description="Deploy application to production",
            agents=[
                "DeploymentPlanningAgent",
                "ContainerizationAgent",
                "DeploymentAgent",
                "HealthCheckAgent"
            ],
            requires_llm=True,
            estimated_duration="medium",
            complexity="medium"
        ),
        "single_agent_chat": WorkflowTemplate(
            name="Single Agent Chat",
            description="Simple conversational response",
            agents=["ChatAgent"],
            requires_llm=True,
            estimated_duration="short",
            complexity="simple"
        )
    }
    
    # Mapping from TaskType to workflow templates
    TASK_TO_WORKFLOW = {
        TaskType.FULLSTACK_DEVELOPMENT: "software_assembly_line",
        TaskType.BACKEND_ONLY: "backend_api_workflow",
        TaskType.FRONTEND_ONLY: "frontend_ui_workflow",
        TaskType.CODE_REVIEW: "code_review_workflow",
        TaskType.DEBUGGING: "debugging_workflow",
        TaskType.DOCUMENTATION: "documentation_workflow",
        TaskType.TESTING: "testing_workflow",
        TaskType.DEPLOYMENT: "deployment_workflow",
        TaskType.CONVERSATIONAL_CHAT: "single_agent_chat"
    }
    
    async def _make_routing_decision(
        self, 
        intent: Dict[str, Any],
        state: DevMasterState
    ) -> RoutingDecision:
        """Make the routing decision based on intent and context."""
        
        # Get the primary intent
        primary_intent = TaskType(intent["primary_intent"])
        confidence = intent.get("confidence", 0.5)
        complexity = intent.get("complexity", "medium")
        requires_context = intent.get("requires_context", False)
        sub_intents = [TaskType(t) for t in intent.get("sub_intents", [])]
        
        # Get the primary workflow
        primary_workflow_name = self.TASK_TO_WORKFLOW.get(
            primary_intent, 
            "single_agent_chat"
        )
        primary_workflow = self.WORKFLOW_TEMPLATES[primary_workflow_name]
        
        # Determine alternative workflows
        alternatives = []
        warnings = []
        
        # If confidence is low, suggest alternatives
        if confidence < 0.7:
            warnings.append(
                f"Low confidence ({confidence:.2f}) in intent classification. "
                "Consider clarifying the request."
            )
            
            # Add workflows for sub-intents as alternatives
            for sub_intent in sub_intents:
                alt_workflow = self.TASK_TO_WORKFLOW.get(sub_intent)
                if alt_workflow and alt_workflow != primary_workflow_name:
                    alternatives.append(alt_workflow)
        
        # If context is needed, add a warning
        if requires_context:
            warnings.append(
                "The request may need additional context. "
                "Consider asking for clarification."
            )
        
        # Check complexity match
        if complexity != primary_workflow.complexity:
            warnings.append(
                f"Request complexity ({complexity}) doesn't match "
                f"workflow complexity ({primary_workflow.complexity})"
            )
        
        # Build reasoning
        reasoning = self._build_reasoning(
            primary_intent, 
            primary_workflow,
            confidence,
            complexity
        )
        
        return RoutingDecision(
            selected_workflow=primary_workflow_name,
            workflow_template=primary_workflow,
            confidence=confidence,
            alternative_workflows=alternatives[:3],  # Limit to top 3
            reasoning=reasoning,
            warnings=warnings
        )
    
    def _build_reasoning(
        self,
        intent: TaskType,
        workflow: WorkflowTemplate,
        confidence: float,
        complexity: str
    ) -> str:
        """Build a reasoning explanation for the routing decision."""
        
        reasoning_parts = [
            f"Selected '{workflow.name}' workflow for {intent.value} request."
        ]
        
        if confidence > 0.8:
            reasoning_parts.append("High confidence in intent classification.")
        elif confidence > 0.6:
            reasoning_parts.append("Moderate confidence in intent classification.")
        else:
            reasoning_parts.append("Low confidence - may need clarification.")
        
        reasoning_parts.append(
            f"This workflow involves {len(workflow.agents)} specialized agents "
            f"and is estimated to take a {workflow.estimated_duration} duration."
        )
        
        if complexity == workflow.complexity:
            reasoning_parts.append("Request complexity matches workflow design.")
        
        return " ".join(reasoning_parts)
    
    async def _execute_impl(self, state: DevMasterState) -> Dict[str, Any]:
        """Execute the routing decision."""
        # Get the intent from state
        intent = state.get("intent")
        if not intent:
            raise ValueError("No intent classification found in state")
        
        # Make routing decision
        decision = await self._make_routing_decision(intent, state)
        
        # Determine the first agent in the selected workflow
        first_agent = decision.workflow_template.agents[0]
        
        # Prepare the message
        message = {
            "role": "CapabilityRouter",
            "content": (
                f"Routing to '{decision.selected_workflow}' workflow. "
                f"Starting with {first_agent}."
            ),
            "metadata": {
                "routing_decision": decision.model_dump(),
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        # Update state with routing information
        messages = state.get("messages", []).copy()
        messages.append(message)
        
        result = {
            "messages": messages,
            "routing_decision": decision.model_dump(),
            "selected_workflow": decision.selected_workflow,
            "workflow_agents": decision.workflow_template.agents,
            "current_workflow_index": 0,
            "active_agent": first_agent  # Route to first agent in workflow
        }
        
        # Add warnings as separate messages if any
        if decision.warnings:
            for warning in decision.warnings:
                warning_message = {
                    "role": "CapabilityRouter",
                    "content": f"⚠️ {warning}",
                    "metadata": {
                        "warning": True,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
                messages.append(warning_message)
            result["messages"] = messages
        
        return result
    
    async def validate(self, state: DevMasterState) -> bool:
        """Validate that routing can proceed."""
        return bool(state.get("intent"))
