#!/usr/bin/env python3
"""
Test script for intent classification system
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.classifiers import IntentClassifier, CapabilityRouter
from app.agents.specialists import ChatAgent
from app.core.state import DevMasterState
from app.agents.orchestrator import OrchestratorGraph
from app.core.events import EventBus


async def test_classification():
    """Test the intent classification system."""
    
    # Set up orchestrator
    orchestrator = OrchestratorGraph()
    
    # Register agents
    orchestrator.register_agent(IntentClassifier())
    orchestrator.register_agent(CapabilityRouter())
    orchestrator.register_agent(ChatAgent())
    
    # Test cases
    test_requests = [
        "Hello, what can you help me with?",
        "Build me a todo list application with user authentication",
        "Create a REST API for managing blog posts",
        "Debug this error in my code",
        "Write documentation for my project",
        "Deploy my application to production"
    ]
    
    print("Testing Intent Classification System\n" + "="*50)
    
    for request in test_requests:
        print(f"\n📝 User Request: '{request}'")
        
        # Create initial state
        initial_state = DevMasterState(
            user_request=request,
            active_agent="IntentClassifier",
            messages=[],
            agent_history=[],
            project_id=f"test-{hash(request)}"
        )
        
        # Execute workflow
        try:
            final_state = await orchestrator.execute(initial_state)
            
            # Extract results
            intent = final_state.get("intent", {})
            routing = final_state.get("routing_decision", {})
            
            print(f"✅ Intent: {intent.get('primary_intent', 'Unknown')}")
            print(f"   Confidence: {intent.get('confidence', 0):.2f}")
            print(f"   Complexity: {intent.get('complexity', 'Unknown')}")
            print(f"   Keywords: {', '.join(intent.get('keywords', []))}")
            
            if routing:
                print(f"🔄 Workflow: {routing.get('selected_workflow', 'Unknown')}")
                print(f"   Agents: {', '.join(routing.get('workflow_template', {}).get('agents', [])[:3])}...")
                
                if routing.get('warnings'):
                    print(f"⚠️  Warnings: {'; '.join(routing['warnings'])}")
            
            # Show final message if it's a chat response
            if final_state.get("active_agent") == "Done" and final_state.get("messages"):
                last_message = final_state["messages"][-1]
                if last_message.get("role") == "ChatAgent":
                    print(f"💬 Response: {last_message['content'][:100]}...")
                    
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    print("\n" + "="*50 + "\nTest completed!")


if __name__ == "__main__":
    asyncio.run(test_classification())
