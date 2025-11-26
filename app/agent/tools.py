"""Agent tools and utilities."""

from typing import Optional
import re
import json
import hashlib


def detect_language(text: str) -> str:
    """
    Very simple language detection heuristic.

    Currently distinguishes 'en' vs 'es' vs 'fr' vs 'de' using keyword hints.
    Falls back to 'en'.
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
    """
    Build a prompt key name with variant suffix for A/B testing.

    Example:
        base_key='support' and variant='B' -> 'support_B'
    """
    return f"{base_key}_{variant.upper()}"


def assign_sticky_ab_variant(platform_user_id: str) -> str:
    """
    Deterministic A/B assignment per user based on hash of platform_user_id.

    Returns 'A' or 'B'.
    """
    h = hashlib.sha256(platform_user_id.encode('utf-8')).hexdigest()
    # Use last hex digit parity for split
    return 'A' if int(h[-1], 16) % 2 == 0 else 'B'


def adjust_response_for_sentiment(response: str, sentiment: float) -> str:
    """
    Lightly adjust response tone based on sentiment score.

    If sentiment is strongly negative, prepend an extra apology.
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
