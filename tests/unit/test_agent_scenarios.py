"""Scenario-based tests for the agent workflow using mock LLM mode.

These tests validate classification, escalation, and response content using
CustomerSupportAgent with default mock responses.
"""

import pytest
from app.agent.graph import CustomerSupportAgent


@pytest.mark.asyncio
async def test_support_flow_order_request():
    agent = CustomerSupportAgent()
    msg = "Hey, I ordered the blue hoodie 3 days ago but haven't received tracking info yet"
    result = await agent.process_message(message=msg, conversation_history=[])

    assert result["intent"] in ("support", "general")  # rule-based may classify as support
    assert not result.get("requires_escalation", False)
    # Mock support response asks for order number
    assert "order" in result["response"].lower()


@pytest.mark.asyncio
async def test_sales_flow_pricing_and_demo():
    agent = CustomerSupportAgent()
    msg = "I'm interested in your enterprise plan. What's the pricing for 50 users?"
    result = await agent.process_message(message=msg, conversation_history=[])

    assert result["intent"] == "sales"
    text = result["response"].lower()
    # Mock sales response references pricing and offers a demo
    assert "pricing" in text or "$" in text
    assert "demo" in text


@pytest.mark.asyncio
async def test_urgent_escalation_flow():
    agent = CustomerSupportAgent()
    msg = "This is ridiculous! I've been charged twice and no one is helping me!"
    result = await agent.process_message(message=msg, conversation_history=[])

    assert result["intent"] == "urgent"
    assert result["requires_escalation"] is True
    text = result["response"].lower()
    # Escalation message should apologize and indicate human handoff/high priority
    assert "connecting you with a human" in text or "human agent" in text
    assert "priority" in text

