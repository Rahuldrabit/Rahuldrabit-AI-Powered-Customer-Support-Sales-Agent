"""LangGraph agent nodes for message processing."""

from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate

from app.config import settings
from app.agent.prompts import (
    CLASSIFICATION_PROMPT,
    SUPPORT_RESPONSE_PROMPT,
    SALES_RESPONSE_PROMPT,
    GENERAL_RESPONSE_PROMPT,
    ESCALATION_MESSAGE,
    MOCK_RESPONSES
)
from app.agent.tools import (
    detect_urgency,
    extract_sentiment_indicators,
    format_context
)
from app.utils.logger import log


class AgentNodes:
    """Agent nodes for LangGraph workflow."""
    
    def __init__(self):
        """Initialize the agent nodes with LLM client."""
        self.llm = self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize LLM based on configuration."""
        if settings.llm_provider == "openai" and settings.openai_api_key:
            log.info("Initializing OpenAI LLM")
            return ChatOpenAI(
                api_key=settings.openai_api_key,
                model="gpt-3.5-turbo",
                temperature=settings.agent_temperature,
                max_tokens=settings.agent_max_tokens
            )
        elif settings.llm_provider == "anthropic" and settings.anthropic_api_key:
            log.info("Initializing Anthropic LLM")
            return ChatAnthropic(
                api_key=settings.anthropic_api_key,
                model="claude-3-haiku-20240307",
                temperature=settings.agent_temperature,
                max_tokens=settings.agent_max_tokens
            )
        else:
            log.warning("No LLM provider configured, using mock responses")
            return None
    
    def classify_message(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify incoming message intent.
        
        Args:
            state: Current agent state containing message and context
            
        Returns:
            Updated state with intent classification
        """
        log.info("Classifying message intent")
        
        message = state.get("message", "")
        context = format_context(state.get("conversation_history", []))
        
        # Check for urgency first
        if detect_urgency(message):
            log.warning(f"Urgent message detected: {message[:50]}...")
            state["intent"] = "urgent"
            state["requires_escalation"] = True
            return state
        
        # Use LLM for classification if available
        if self.llm:
            try:
                prompt = ChatPromptTemplate.from_template(CLASSIFICATION_PROMPT)
                response = self.llm.invoke(
                    prompt.format_messages(message=message, context=context)
                )
                
                # Parse response
                response_text = response.content
                if "CLASSIFICATION:" in response_text:
                    intent_line = [line for line in response_text.split("\n") if "CLASSIFICATION:" in line][0]
                    intent = intent_line.split(":")[1].strip().lower()
                    state["intent"] = intent
                    state["classification_reason"] = response_text
                else:
                    # Fallback to rule-based
                    state["intent"] = self._rule_based_classification(message)
                    
            except Exception as e:
                log.error(f"LLM classification failed: {e}")
                state["intent"] = self._rule_based_classification(message)
        else:
            # Rule-based classification
            state["intent"] = self._rule_based_classification(message)
        
        log.info(f"Message classified as: {state['intent']}")
        return state
    
    def _rule_based_classification(self, message: str) -> str:
        """Fallback rule-based classification."""
        message_lower = message.lower()
        
        # Sales keywords
        sales_keywords = ['price', 'pricing', 'cost', 'buy', 'purchase', 'plan', 'enterprise', 'demo']
        if any(keyword in message_lower for keyword in sales_keywords):
            return "sales"
        
        # Support keywords
        support_keywords = ['order', 'tracking', 'issue', 'problem', 'help', 'support', 'not working']
        if any(keyword in message_lower for keyword in support_keywords):
            return "support"
        
        # Default to general
        return "general"
    
    def retrieve_context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve and format conversation context.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state with formatted context
        """
        log.info("Retrieving conversation context")
        
        conversation_history = state.get("conversation_history", [])
        state["formatted_context"] = format_context(conversation_history)
        
        return state
    
    def generate_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate appropriate response based on intent.
        
        Args:
            state: Current agent state with intent and context
            
        Returns:
            Updated state with generated response
        """
        log.info("Generating response")
        
        intent = state.get("intent", "general")
        message = state.get("message", "")
        context = state.get("formatted_context", "")
        
        # Handle urgent/escalation
        if intent == "urgent" or state.get("requires_escalation"):
            state["response"] = ESCALATION_MESSAGE
            state["requires_escalation"] = True
            return state
        
        # Select appropriate prompt based on intent
        prompt_map = {
            "support": SUPPORT_RESPONSE_PROMPT,
            "sales": SALES_RESPONSE_PROMPT,
            "general": GENERAL_RESPONSE_PROMPT
        }
        
        prompt_template = prompt_map.get(intent, GENERAL_RESPONSE_PROMPT)
        
        # Generate response using LLM if available
        if self.llm:
            try:
                prompt = ChatPromptTemplate.from_template(prompt_template)
                response = self.llm.invoke(
                    prompt.format_messages(message=message, context=context)
                )
                state["response"] = response.content
            except Exception as e:
                log.error(f"LLM response generation failed: {e}")
                state["response"] = MOCK_RESPONSES.get(intent, MOCK_RESPONSES["general"])
        else:
            # Use mock responses
            state["response"] = MOCK_RESPONSES.get(intent, MOCK_RESPONSES["general"])
        
        log.info(f"Response generated: {state['response'][:50]}...")
        return state
    
    def check_escalation(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine if human escalation is needed.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state with escalation decision
        """
        log.info("Checking escalation requirements")
        
        intent = state.get("intent", "")
        message = state.get("message", "")
        
        # Always escalate urgent messages
        if intent == "urgent":
            state["requires_escalation"] = True
            state["escalation_reason"] = "Urgent issue requiring immediate human attention"
            return state
        
        # Check sentiment
        sentiment = extract_sentiment_indicators(message)
        state["sentiment_score"] = sentiment
        
        if sentiment <= -0.6:
            state["requires_escalation"] = True
            state["escalation_reason"] = "Highly negative sentiment detected"
            return state
        
        # Otherwise, no escalation needed
        state["requires_escalation"] = state.get("requires_escalation", False)
        
        return state
    
    def validate_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the generated response.
        
        Args:
            state: Current agent state with response
            
        Returns:
            Updated state with validation results
        """
        log.info("Validating response")
        
        response = state.get("response", "")
        
        # Basic validation
        is_valid = (
            len(response) > 10 and  # Not too short
            len(response) < 1000 and  # Not too long
            response.strip() != ""  # Not empty
        )
        
        state["response_valid"] = is_valid
        
        if not is_valid:
            log.warning("Response validation failed")
            state["response"] = "I apologize, but I'm having trouble generating a response. Let me connect you with a human agent."
            state["requires_escalation"] = True
        
        return state
