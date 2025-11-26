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
    language: str              # detected language code
    prompt_variant: str        # A/B variant used
    sticky_prompt_variant: str # per-user sticky A/B preference (optional)
    platform: str              # platform id (tiktok/linkedin) optional
    platform_user_id: str      # platform user id optional
    planned_tool_calls: List[Dict[str, Any]]
    tool_results: Dict[str, Any]


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
        workflow.add_node("plan_tools", self.nodes.plan_tools)
        workflow.add_node("run_tools", self.nodes.run_tools)
        workflow.add_node("resolve_with_tools", self.nodes.resolve_with_tools)
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
            """Determine next node based on escalation.

            If escalation is required, generate a response (handoff message) and skip validation.
            Otherwise, proceed to normal response and validation.
            """
            if state.get("requires_escalation"):
                return "generate_response_escalated"
            return "plan_tools"
        
        # Add a branch node for escalated path which goes directly to END
        workflow.add_node("generate_response_escalated", self.nodes.generate_response)
        workflow.add_conditional_edges(
            "check_escalation",
            should_escalate,
            {
                "plan_tools": "plan_tools",
                "generate_response_escalated": "generate_response_escalated",
            }
        )
        
        # Decide whether to run tools after planning
        def has_tools(state: AgentState) -> str:
            planned = state.get("planned_tool_calls") or []
            return "run" if len(planned) > 0 else "direct"

        workflow.add_conditional_edges(
            "plan_tools",
            has_tools,
            {
                "run": "run_tools",
                "direct": "generate_response",
            }
        )

        # After running tools, resolve with tools then validate
        workflow.add_edge("run_tools", "resolve_with_tools")
        workflow.add_edge("resolve_with_tools", "validate_response")

        # After generating response (no tools), validate it
        workflow.add_edge("generate_response", "validate_response")
        # Escalated path ends after generating handoff response
        workflow.add_edge("generate_response_escalated", END)
        
        # After validation, end
        workflow.add_edge("validate_response", END)
        
        log.info("Agent workflow graph built successfully")
        return workflow
    
    def process_message(
        self,
        message: str,
        conversation_history: List[Dict[str, Any]] = None,
        sticky_prompt_variant: str | None = None,
        platform: str | None = None,
        platform_user_id: str | None = None,
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
            "classification_reason": "",
            "language": "",          # will be detected in nodes
            "prompt_variant": "",     # will be set from settings in nodes or sticky preference
            "sticky_prompt_variant": sticky_prompt_variant or "",
            "platform": platform or "",
            "platform_user_id": platform_user_id or "",
            "planned_tool_calls": [],
            "tool_results": {},
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
                "language": final_state.get("language", ""),
                "prompt_variant": final_state.get("prompt_variant", "A"),
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
