"""Unit tests for agent nodes."""

import pytest
from app.agent.nodes import AgentNodes


@pytest.fixture
def agent_nodes():
    """Create agent nodes instance."""
    return AgentNodes()


@pytest.mark.asyncio
async def test_classify_message_support(agent_nodes):
    """Test classification of support message."""
    state = {
        "message": "I have an issue with my order #12345",
        "conversation_history": []
    }
    
    result = await agent_nodes.classify_message(state)
    assert result["intent"] in ["support", "urgent"]


@pytest.mark.asyncio
async def test_classify_message_sales(agent_nodes):
    """Test classification of sales message."""
    state = {
        "message": "What's the pricing for your enterprise plan?",
        "conversation_history": []
    }
    
    result = await agent_nodes.classify_message(state)
    assert result["intent"] == "sales"


@pytest.mark.asyncio
async def test_classify_message_urgent(agent_nodes):
    """Test classification of urgent message."""
    state = {
        "message": "This is ridiculous!!! I've been charged twice!",
        "conversation_history": []
    }
    
    result = await agent_nodes.classify_message(state)
    assert result["intent"] == "urgent"
    assert result["requires_escalation"] == True


@pytest.mark.asyncio
async def test_generate_response(agent_nodes):
    """Test response generation."""
    state = {
        "message": "Hello, I need help",
        "intent": "general",
        "formatted_context": "No previous context.",
        "requires_escalation": False,
        "language": "en",
        "prompt_variant": "A",
        "sentiment_score": 0.0
    }
    
    result = await agent_nodes.generate_response(state)
    assert "response" in result
    assert len(result["response"]) > 0


def test_check_escalation(agent_nodes):
    """Test escalation checking."""
    # Urgent intent
    state_urgent = {
        "message": "This is terrible!",
        "intent": "urgent"
    }
    result = agent_nodes.check_escalation(state_urgent)
    assert result["requires_escalation"] == True
    
    # Normal intent
    state_normal = {
        "message": "I have a question",
        "intent": "general"
    }
    result = agent_nodes.check_escalation(state_normal)
    assert result.get("requires_escalation", False) == False


def test_validate_response(agent_nodes):
    """Test response validation."""
    # Valid response
    state_valid = {
        "response": "This is a valid response to your question."
    }
    result = agent_nodes.validate_response(state_valid)
    assert result["response_valid"] == True
    
    # Invalid (too short) response
    state_invalid = {
        "response": "Hi"
    }
    result = agent_nodes.validate_response(state_invalid)
    assert result["response_valid"] == False
    assert result["requires_escalation"] == True

