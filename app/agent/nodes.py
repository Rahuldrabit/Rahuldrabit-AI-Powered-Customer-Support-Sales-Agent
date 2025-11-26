"""LangGraph agent nodes for message processing."""

from typing import Dict, Any, Optional
try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    ChatAnthropic = None

try:
    from langchain_core.prompts import ChatPromptTemplate
except ImportError:
    try:
        from langchain.prompts import ChatPromptTemplate
    except ImportError:
        ChatPromptTemplate = None

from app.config import settings
from app.agent.prompts import (
    CLASSIFICATION_PROMPT,
    SUPPORT_RESPONSE_PROMPT_A,
    SUPPORT_RESPONSE_PROMPT_B,
    SALES_RESPONSE_PROMPT_A,
    SALES_RESPONSE_PROMPT_B,
    GENERAL_RESPONSE_PROMPT_A,
    GENERAL_RESPONSE_PROMPT_B,
    ESCALATION_MESSAGE,
    MOCK_RESPONSES
)
from app.agent.tools import (
    detect_urgency,
    extract_sentiment_indicators,
    format_context,
    detect_language,
    select_prompt_variant,
    adjust_response_for_sentiment
)
from app.utils.logger import log
from app.agent.lc_tools import get_langchain_tools, execute_tool_call
from app.agent.runtime_tools import lookup_order_status, fetch_profile

try:
    from langchain_core.messages import AIMessage, ToolMessage
except Exception:
    AIMessage = None
    ToolMessage = None


from app.integrations.gemini import get_gemini_client

class AgentNodes:
    """Agent nodes for LangGraph workflow."""
    
    def __init__(self):
        """Initialize the agent nodes with LLM client."""
        self.llm = self._initialize_llm()
        self.gemini = None
        if settings.llm_provider == "gemini":
            self.gemini = get_gemini_client()
    
    def _initialize_llm(self):
        """Initialize LLM based on configuration."""
        if settings.llm_provider == "openai" and settings.openai_api_key:
            if ChatOpenAI is None:
                log.error("langchain_openai not installed, falling back to mock")
                return None
            log.info("Initializing OpenAI LLM")
            return ChatOpenAI(
                api_key=settings.openai_api_key,
                model="gpt-3.5-turbo",
                temperature=settings.agent_temperature,
                max_tokens=settings.agent_max_tokens
            )
        elif settings.llm_provider == "anthropic" and settings.anthropic_api_key:
            if ChatAnthropic is None:
                log.error("langchain_anthropic not installed, falling back to mock")
                return None
            log.info("Initializing Anthropic LLM")
            return ChatAnthropic(
                api_key=settings.anthropic_api_key,
                model="claude-3-haiku-20240307",
                temperature=settings.agent_temperature,
                max_tokens=settings.agent_max_tokens
            )
        elif settings.llm_provider == "gemini" and settings.gemini_api_key:
            log.info("Initializing Gemini LLM")
            # Gemini is handled via self.gemini client directly
            return None
        else:
            if settings.llm_provider != "gemini":
                log.warning("No LLM provider configured, using mock responses")
            return None

    async def _invoke_with_tools(self, messages) -> str:
        """Invoke LLM with optional tool bindings and handle one round of tool calls."""
        if not self.llm:
            raise RuntimeError("LLM not initialized")

        tools = []
        try:
            tools = get_langchain_tools()
        except Exception:
            tools = []

        llm_runner = self.llm
        if tools:
            try:
                llm_runner = self.llm.bind_tools(tools)
            except Exception as e:
                log.error(f"Failed to bind tools to LLM: {e}")
                llm_runner = self.llm

        # First pass
        resp = await llm_runner.ainvoke(messages)
        # If tool calls present and we can construct ToolMessage, execute and do a second pass
        try:
            tool_calls = getattr(resp, "tool_calls", None)
            if tool_calls and ToolMessage is not None:
                tool_msgs = []
                for call in tool_calls:
                    name = call.get("name")
                    args = call.get("args", {})
                    call_id = call.get("id")
                    try:
                        result = execute_tool_call(name, args)
                        tool_msgs.append(ToolMessage(content=str(result), tool_call_id=call_id))
                    except Exception as te:
                        tool_msgs.append(ToolMessage(content=f"ERROR: {te}", tool_call_id=call_id))
                # Re-invoke with tool results appended
                final = await llm_runner.ainvoke([*messages, resp, *tool_msgs])
                return getattr(final, "content", str(final))
        except Exception as e:
            log.error(f"Tool call handling failed: {e}")

        return getattr(resp, "content", str(resp))
    
    async def classify_message(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify incoming message intent.
        
        Args:
            state: Current agent state containing message and context
            
        Returns:
            Updated state with intent classification
        """
        log.info("Classifying message intent")
        
        message = state.get("message", "")
        
        # Language detection
        if settings.agent_auto_detect_language:
            lang = detect_language(message)
        else:
            lang = settings.agent_default_language
        state["language"] = lang

        # Prompt variant selection (A/B testing)
        variant_setting = (settings.agent_prompt_variant or "").strip().lower()
        sticky_pref = (state.get("sticky_prompt_variant") or "").strip().upper()

        # If explicitly forced by settings to A or B, honor that first
        if variant_setting in {"a", "b"}:
            variant = variant_setting.upper()
        elif sticky_pref in {"A", "B"}:
            # Otherwise, if a per-user sticky preference exists, use it
            variant = sticky_pref
        elif variant_setting == "random":
            # Uniform random split
            import random
            variant = random.choice(["A", "B"])
        elif variant_setting == "auto":
            # Choose variant B for non-English languages to test alternative phrasing
            variant = "B" if lang != "en" else "A"
        else:
            # Default: use explicit A/B or fallback to settings value
            variant = settings.agent_prompt_variant.upper()[:1] if settings.agent_prompt_variant else "A"

        state["prompt_variant"] = variant

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
                messages = prompt.format_messages(message=message, context=context)
                response_text = await self._invoke_with_tools(messages)
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
        elif self.gemini:
            try:
                prompt_text = CLASSIFICATION_PROMPT.format(message=message, context=context)
                response_text = await self.gemini.generate_content(prompt_text)
                
                if "CLASSIFICATION:" in response_text:
                    intent_line = [line for line in response_text.split("\n") if "CLASSIFICATION:" in line][0]
                    intent = intent_line.split(":")[1].strip().lower()
                    state["intent"] = intent
                    state["classification_reason"] = response_text
                else:
                    state["intent"] = self._rule_based_classification(message)
            except Exception as e:
                log.error(f"Gemini classification failed: {e}")
                state["intent"] = self._rule_based_classification(message)
        else:
            # Rule-based classification
            state["intent"] = self._rule_based_classification(message)
        
        log.info(f"Message classified as: {state['intent']} (lang={state['language']}, variant={state['prompt_variant']})")
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

    async def plan_tools(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Plan which tools to run based on intent and message.

        Produces a list of planned tool calls with args stored in state["planned_tool_calls"].
        """
        log.info("Planning tools")
        planned = []
        message = state.get("message", "")
        intent = state.get("intent", "")
        platform = state.get("platform", "")
        platform_user_id = state.get("platform_user_id", "")

        # If support-related, attempt to extract order number and maybe lookup status
        if intent == "support" or any(k in message.lower() for k in ["order", "tracking"]):
            planned.append({"name": "extract_order_number", "args": {"text": message}})
            # We'll decide to call lookup_order_status after running extract (if found)
        
        # If we have platform context, plan a profile fetch for personalization
        if platform and platform_user_id:
            planned.append({"name": "fetch_profile", "args": {"platform": platform, "user_id": platform_user_id}})

        state["planned_tool_calls"] = planned
        return state

    async def run_tools(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute planned tools sequentially and store results in state["tool_results"]."""
        log.info("Running planned tools")
        results: Dict[str, Any] = {}
        for call in state.get("planned_tool_calls", []) or []:
            name = call.get("name")
            args = call.get("args", {})
            try:
                if name == "extract_order_number":
                    res = execute_tool_call(name, args)
                    results[name] = res
                    # If found, also lookup order status
                    if res:
                        order_number = res
                        results["lookup_order_status"] = lookup_order_status(order_number)
                elif name == "fetch_profile":
                    platform = args.get("platform")
                    user_id = args.get("user_id")
                    res = await fetch_profile(platform, user_id)
                    results[name] = res
                else:
                    # Try registry first (detect_language/sentiment etc.)
                    res = execute_tool_call(name, args)
                    results[name] = res
            except Exception as e:
                log.error(f"Tool {name} failed: {e}")
                results[name] = {"error": str(e)}

        state["tool_results"] = results
        return state

    async def resolve_with_tools(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate response considering tool results before validation."""
        log.info("Resolving with tool results")
        # Reuse generate_response path but enrich context with tool results JSON
        import json as _json
        tool_json = ""
        try:
            tool_json = _json.dumps(state.get("tool_results", {}))
        except Exception:
            tool_json = str(state.get("tool_results", {}))

        # Build augmented prompt template by appending tool data
        intent = state.get("intent", "general")
        language = state.get("language", settings.agent_default_language)
        variant = state.get("prompt_variant", settings.agent_prompt_variant.upper())
        base_prompt_template = self._get_prompt_for_intent(intent, variant)
        augmented_template = base_prompt_template + "\n\nAdditional data from tools (JSON): {tool_results}\nUse this data if relevant."
        prompt_template = self._wrap_prompt_with_language_hint(augmented_template, language)

        message = state.get("message", "")
        context = state.get("formatted_context", "")

        if self.llm:
            try:
                prompt = ChatPromptTemplate.from_template(prompt_template)
                messages = prompt.format_messages(message=message, context=context, tool_results=tool_json)
                final_text = await self._invoke_with_tools(messages)
                state["response"] = final_text
                return state
            except Exception as e:
                log.error(f"resolve_with_tools LLM failed: {e}")

        # Fallback to simple generation path without tools
        return await self.generate_response(state)
    
    def _get_prompt_for_intent(self, intent: str, variant: str) -> str:
        """
        Select the correct prompt template for given intent and A/B variant.
        """
        key = select_prompt_variant(intent, variant)
        mapping = {
            "support_A": SUPPORT_RESPONSE_PROMPT_A,
            "support_B": SUPPORT_RESPONSE_PROMPT_B,
            "sales_A": SALES_RESPONSE_PROMPT_A,
            "sales_B": SALES_RESPONSE_PROMPT_B,
            "general_A": GENERAL_RESPONSE_PROMPT_A,
            "general_B": GENERAL_RESPONSE_PROMPT_B,
        }
        return mapping.get(key, GENERAL_RESPONSE_PROMPT_A)
    
    def _wrap_prompt_with_language_hint(self, base_prompt: str, language: str) -> str:
        """
        Add a brief language instruction at the top of the prompt.

        This lets the LLM respond in the detected language where possible.
        """
        if not language or language == "en":
            return base_prompt
        prefix = f"You MUST answer in language code '{language}'.\n\n"
        return prefix + base_prompt

    async def generate_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
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
        language = state.get("language", settings.agent_default_language)
        variant = state.get("prompt_variant", settings.agent_prompt_variant.upper())
        sentiment = state.get("sentiment_score", 0.0)
        
        # Handle urgent/escalation
        if intent == "urgent" or state.get("requires_escalation"):
            state["response"] = ESCALATION_MESSAGE
            state["requires_escalation"] = True
            return state
        
        # Select appropriate prompt based on intent + variant
        base_prompt_template = self._get_prompt_for_intent(intent, variant)
        prompt_template = self._wrap_prompt_with_language_hint(base_prompt_template, language)
        
        # Generate response using LLM if available
        final_text = ""
        
        if self.llm:
            try:
                prompt = ChatPromptTemplate.from_template(prompt_template)
                messages = prompt.format_messages(message=message, context=context)
                final_text = await self._invoke_with_tools(messages)
            except Exception as e:
                log.error(f"LLM response generation failed: {e}")
                final_text = MOCK_RESPONSES.get(intent, MOCK_RESPONSES["general"])
        elif self.gemini:
            try:
                # For Gemini, we can use the chat capability or just generate content
                # Here we use generate_content with the full prompt for consistency
                full_prompt = prompt_template.format(message=message, context=context)
                final_text = await self.gemini.generate_content(full_prompt)
            except Exception as e:
                log.error(f"Gemini response generation failed: {e}")
                final_text = MOCK_RESPONSES.get(intent, MOCK_RESPONSES["general"])
        else:
            # Use mock responses
            final_text = MOCK_RESPONSES.get(intent, MOCK_RESPONSES["general"])
        
        # Adjust tone based on sentiment (Sentiment Analysis -> tone tuning)
        final_text = adjust_response_for_sentiment(final_text, sentiment)
        
        state["response"] = final_text
        log.info(f"Response generated: {state['response'][:50]}...")
        return state
    
    def check_escalation(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine if human escalation is needed.

        Also computes sentiment_score used later for tone adjustment.
        """
        log.info("Checking escalation requirements")
        
        intent = state.get("intent", "")
        message = state.get("message", "")
        
        # Always escalate urgent messages
        if intent == "urgent":
            state["requires_escalation"] = True
            state["escalation_reason"] = "Urgent issue requiring immediate human attention"
            # still compute sentiment for analytics & tone
            state["sentiment_score"] = extract_sentiment_indicators(message)
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
