"""LangGraph workflow definition."""

from typing import Dict, Any, TypedDict, List
from langgraph.graph import StateGraph, END
from app.agent.nodes import AgentNodes
from app.utils.logger import log


class AgentState(TypedDict):
    """State schema for the agent workflow."""
    message: str
    conversation_history: List[Dict[str, Any]]
    intent: str
    formatted_context: str
    response: str
    requires_escalation: bool
    escalation_reason: str
    sentiment_score: float
    response_valid: bool
    classification_reason: str


class CustomerSupportAgent:
    """LangGraph-based customer support agent."""
    
    def __init__(self):
        """Initialize the agent with workflow graph."""
        self.nodes = AgentNodes()
        self.graph = self._build_graph()
        self.workflow = self.graph.compile()
    
    def _build_graph(self) -> StateGraph:
        """
        Build the LangGraph workflow.
        
        Returns:
            Compiled state graph
        """
        log.info("Building agent workflow graph")
        
        # Create state graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("classify", self.nodes.classify_message)
        workflow.add_node("retrieve_context", self.nodes.retrieve_context)
        workflow.add_node("check_escalation", self.nodes.check_escalation)
        workflow.add_node("generate_response", self.nodes.generate_response)
        workflow.add_node("validate_response", self.nodes.validate_response)
        
        # Define edges
        workflow.set_entry_point("classify")
        
        # After classification, retrieve context
        workflow.add_edge("classify", "retrieve_context")
        
        # After context retrieval, check for escalation
        workflow.add_edge("retrieve_context", "check_escalation")
        
        # Conditional edge based on escalation
        def should_escalate(state: AgentState) -> str:
            """Determine next node based on escalation."""
            if state.get("requires_escalation"):
                # If escalation is needed, still generate response but skip validation
                return "generate_response"
            return "generate_response"
        
        workflow.add_conditional_edges(
            "check_escalation",
            should_escalate,
            {
                "generate_response": "generate_response"
            }
        )
        
        # After generating response, validate it
        workflow.add_edge("generate_response", "validate_response")
        
        # After validation, end
        workflow.add_edge("validate_response", END)
        
        log.info("Agent workflow graph built successfully")
        return workflow
    
    def process_message(
        self,
        message: str,
        conversation_history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process an incoming message through the agent workflow.
        
        Args:
            message: The incoming message text
            conversation_history: Optional list of previous messages
            
        Returns:
            Dictionary containing response and metadata
        """
        log.info(f"Processing message: {message[:50]}...")
        
        # Initialize state
        initial_state: AgentState = {
            "message": message,
            "conversation_history": conversation_history or [],
            "intent": "",
            "formatted_context": "",
            "response": "",
            "requires_escalation": False,
            "escalation_reason": "",
            "sentiment_score": 0.0,
            "response_valid": True,
            "classification_reason": ""
        }
        
        # Run workflow
        try:
            final_state = self.workflow.invoke(initial_state)
            
            log.info(
                f"Message processed successfully. "
                f"Intent: {final_state.get('intent')}, "
                f"Escalation: {final_state.get('requires_escalation')}"
            )
            
            return {
                "response": final_state.get("response", ""),
                "intent": final_state.get("intent", "general"),
                "requires_escalation": final_state.get("requires_escalation", False),
                "escalation_reason": final_state.get("escalation_reason", ""),
                "sentiment_score": final_state.get("sentiment_score", 0.0),
                "metadata": {
                    "classification_reason": final_state.get("classification_reason", ""),
                    "response_valid": final_state.get("response_valid", True)
                }
            }
            
        except Exception as e:
            log.error(f"Error processing message: {e}")
            return {
                "response": "I apologize for the inconvenience. Let me connect you with a human agent.",
                "intent": "error",
                "requires_escalation": True,
                "escalation_reason": f"Processing error: {str(e)}",
                "sentiment_score": 0.0,
                "metadata": {"error": str(e)}
            }


# Global agent instance
_agent_instance = None


def get_agent() -> CustomerSupportAgent:
    """Get or create the global agent instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = CustomerSupportAgent()
    return _agent_instance
