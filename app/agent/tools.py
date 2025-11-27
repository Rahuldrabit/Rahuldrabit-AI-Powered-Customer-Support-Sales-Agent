"""Agent tools and utilities."""

from typing import Optional, Dict, Any, Callable, List
import re
import json
import hashlib
from app.utils.logger import log
from app.integrations.tiktok import TikTokClient
from app.integrations.linkedin import LinkedInClient

# ============================================================================
# Core Utilities
# ============================================================================

def detect_language(text: str) -> str:
    """Detects the language of the given text using keyword heuristics.

    Currently distinguishes 'en' (English), 'es' (Spanish), 'fr' (French),
    and 'de' (German). Falls back to 'en' if no keywords match.

    Args:
        text: The input text to analyze.

    Returns:
        The detected language code ('en', 'es', 'fr', 'de').
    """
    t = text.lower()
    # Spanish hints
    if any(w in t for w in ["hola", "gracias", "por favor", "ayuda", "pedido"]):
        return "es"
    # French hints
    if any(w in t for w in ["bonjour", "merci", "s'il vous plaît", "commande", "aide"]):
        return "fr"
    # German hints
    if any(w in t for w in ["hallo", "danke", "bitte", "bestellung", "hilfe"]):
        return "de"
    return "en"


def select_prompt_variant(base_key: str, variant: str) -> str:
    """Builds a prompt key name with a variant suffix for A/B testing.

    Args:
        base_key: The base name of the prompt (e.g., 'support').
        variant: The variant identifier (e.g., 'A' or 'B').

    Returns:
        The combined key string (e.g., 'support_B').
    """
    return f"{base_key}_{variant.upper()}"


def assign_sticky_ab_variant(platform_user_id: str) -> str:
    """Deterministically assigns an A/B variant based on user ID.

    Uses a hash of the user ID to ensure the same user always gets the
    same variant.

    Args:
        platform_user_id: The unique user ID from the platform.

    Returns:
        'A' or 'B' based on the hash parity.
    """
    h = hashlib.sha256(platform_user_id.encode('utf-8')).hexdigest()
    # Use last hex digit parity for split
    return 'A' if int(h[-1], 16) % 2 == 0 else 'B'


def adjust_response_for_sentiment(response: str, sentiment: float) -> str:
    """Adjusts the response tone based on the sentiment score.

    If the sentiment is strongly negative (<= -0.6), prepends an apology
    to show empathy.

    Args:
        response: The generated response text.
        sentiment: The sentiment score between -1.0 and 1.0.

    Returns:
        The adjusted response text.
    """
    if sentiment <= -0.6:
        prefix = "I'm really sorry about this experience. "
        # Avoid double-prefixing
        if not response.startswith(prefix):
            return prefix + response
    return response


def extract_sentiment_indicators(text: str) -> float:
    """
    Extract basic sentiment from text.
    
    Returns a score from -1.0 (very negative) to 1.0 (very positive).
    
    Args:
        text: The text to analyze
        
    Returns:
        Sentiment score between -1.0 and 1.0
    """
    text_lower = text.lower()
    
    # Positive indicators
    positive_words = [
        'thank', 'thanks', 'great', 'excellent', 'good', 'love', 'happy',
        'pleased', 'wonderful', 'fantastic', 'perfect', 'amazing'
    ]
    
    # Negative indicators
    negative_words = [
        'bad', 'terrible', 'awful', 'horrible', 'worst', 'hate', 'angry',
        'frustrated', 'disappointed', 'unacceptable', 'ridiculous', 'pathetic'
    ]
    
    # Urgent/distress indicators
    urgent_indicators = [
        '!!!', 'asap', 'immediately', 'urgent', 'emergency', 'critical'
    ]
    
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)
    urgent_count = sum(1 for indicator in urgent_indicators if indicator in text_lower)
    
    # Calculate sentiment score
    score = (positive_count - negative_count - urgent_count) / max(len(text.split()), 1)
    
    # Normalize to -1.0 to 1.0 range
    score = max(-1.0, min(1.0, score))
    
    return round(score, 2)


def detect_urgency(text: str) -> bool:
    """
    Detect if a message indicates urgency requiring human intervention.
    
    Args:
        text: The message text
        
    Returns:
        True if urgent, False otherwise
    """
    text_lower = text.lower()
    
    # Urgency indicators
    urgent_keywords = [
        'ridiculous', 'unacceptable', 'immediately', 'asap', 'urgent',
        'lawsuit', 'lawyer', 'legal action', 'complain', 'manager',
        'supervisor', 'charged twice', 'unauthorized', 'fraud'
    ]
    
    # Multiple exclamation marks
    if text.count('!') >= 3:
        return True
    
    # All caps (more than 50% of letters)
    caps_ratio = sum(1 for c in text if c.isupper()) / max(len([c for c in text if c.isalpha()]), 1)
    if caps_ratio > 0.5 and len(text) > 10:
        return True
    
    # Check for urgent keywords
    for keyword in urgent_keywords:
        if keyword in text_lower:
            return True
    
    # Very negative sentiment
    sentiment = extract_sentiment_indicators(text)
    if sentiment <= -0.5:
        return True
    
    return False


def extract_order_number(text: str) -> Optional[str]:
    """
    Extract potential order number from text.
    
    Args:
        text: The message text
        
    Returns:
        Extracted order number or None
    """
    # Pattern for order numbers (common formats)
    patterns = [
        r'#?\b[A-Z]{2}\d{6,10}\b',  # e.g., AB123456
        r'\b\d{8,12}\b',             # e.g., 12345678
        r'order[:\s]+([A-Z0-9-]+)',  # e.g., order: ABC-123
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip('#').strip()
    
    return None


def format_context(messages: list) -> str:
    """
    Format conversation history into context string.
    
    Args:
        messages: List of message dictionaries with 'sender_type' and 'content'
        
    Returns:
        Formatted context string
    """
    if not messages:
        return "No previous context."
    
    # Get last 3 messages for context
    recent_messages = messages[-3:]
    
    context_parts = []
    for msg in recent_messages:
        sender = msg.get('sender_type', 'unknown')
        content = msg.get('content', '')
        context_parts.append(f"{sender.upper()}: {content}")
    
    return "\n".join(context_parts)


# ============================================================================
# LangChain Tool Bindings
# ============================================================================

try:
    from langchain_core.tools import tool
    HAVE_LC_TOOLS = True
except Exception:
    HAVE_LC_TOOLS = False
    def tool(fn=None, **kwargs):  # type: ignore
        def _wrap(f):
            return f
        return _wrap(fn) if fn else _wrap


@tool("detect_language", return_direct=False)
def detect_language_tool(text: str) -> str:
    """Detect language code for the given text. Returns codes like 'en', 'es', 'fr', 'de'."""
    return detect_language(text)


@tool("extract_order_number", return_direct=False)
def extract_order_number_tool(text: str) -> str:
    """Extract order number from text if present; returns empty string when not found."""
    val = extract_order_number(text)
    return val or ""


@tool("sentiment", return_direct=False)
def sentiment_tool(text: str) -> float:
    """Compute sentiment score in [-1.0, 1.0] from the text."""
    return float(extract_sentiment_indicators(text))


def get_langchain_tools() -> List[Any]:
    """Return list of LangChain Tool objects if available, else empty list."""
    if not HAVE_LC_TOOLS:
        return []
    return [detect_language_tool, extract_order_number_tool, sentiment_tool]


# Tool execution registry
_TOOL_REGISTRY: Dict[str, Callable[..., Any]] = {
    "detect_language": detect_language_tool,  # type: ignore
    "extract_order_number": extract_order_number_tool,  # type: ignore
    "sentiment": sentiment_tool,  # type: ignore
}


def execute_tool_call(name: str, args: Dict[str, Any]) -> Any:
    """Execute a tool call by name using the local registry."""
    fn = _TOOL_REGISTRY.get(name)
    if fn is None:
        raise ValueError(f"Unknown tool: {name}")
    return fn.invoke(args) if hasattr(fn, "invoke") else fn(**args)


# ============================================================================
# Runtime Tools (async-capable)
# ============================================================================

def lookup_order_status(order_number: str) -> Dict[str, Any]:
    """Mock order status lookup.

    Simulates an API call to an order management system. The result is
    deterministic based on the hash of the order number for development purposes.

    Args:
        order_number: The order identifier.

    Returns:
        A dictionary containing the order status and details.
    """
    if not order_number:
        return {"found": False}
    h = int(hashlib.sha256(order_number.encode("utf-8")).hexdigest(), 16)
    stages = [
        {"status": "processing", "detail": "Your order is being prepared."},
        {"status": "shipped", "detail": "Your order is on the way."},
        {"status": "in_transit", "detail": "Carrier has your package."},
        {"status": "out_for_delivery", "detail": "Out for delivery today."},
        {"status": "delivered", "detail": "Delivered at destination."},
    ]
    rec = stages[h % len(stages)]
    return {"found": True, "order_number": order_number, **rec}


async def fetch_profile(platform: str, user_id: str) -> Dict[str, Any]:
    """Fetches a user profile from the specified platform.

    Args:
        platform: The platform name ('tiktok' or 'linkedin').
        user_id: The unique user identifier on the platform.

    Returns:
        A dictionary containing the profile data or an error message.
    """
    try:
        if not platform or not user_id:
            return {"ok": False, "error": "missing platform or user_id"}
        if platform.lower() == "tiktok":
            client = TikTokClient()
            data = await client.get_user_info(user_id)
            return {"ok": True, "platform": platform, "profile": data}
        elif platform.lower() == "linkedin":
            client = LinkedInClient()
            data = await client.get_user_profile(user_id)
            return {"ok": True, "platform": platform, "profile": data}
        return {"ok": False, "error": f"unsupported platform: {platform}"}
    except Exception as e:
        log.error(f"fetch_profile error: {e}")
        return {"ok": False, "error": str(e)}
