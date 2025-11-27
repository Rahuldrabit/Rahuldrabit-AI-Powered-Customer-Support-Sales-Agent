"""Integration tests for API endpoints."""

from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data


def test_health_check(client: TestClient):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_webhook_verify(client: TestClient):
    """Test webhook verification endpoint."""
    response = client.get("/webhooks/verify?challenge=test123")
    assert response.status_code == 200
    data = response.json()
    assert data["challenge"] == "test123"


def test_tiktok_webhook(client: TestClient):
    """Test TikTok webhook endpoint."""
    webhook_data = {
        "event_type": "message",
        "user_id": "tiktok_user_123",
        "message": "Hello, I need help with my order",
        "conversation_id": "conv_123",
        "timestamp": 1234567890
    }
    
    response = client.post("/webhooks/tiktok", json=webhook_data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "message_id" in data


def test_linkedin_webhook(client: TestClient):
    """Test LinkedIn webhook endpoint."""
    webhook_data = {
        "event_type": "message",
        "sender_id": "linkedin_user_456",
        "message_text": "What's the pricing for 50 users?",
        "conversation_id": "conv_456",
        "timestamp": 1234567890
    }
    
    response = client.post("/webhooks/linkedin", json=webhook_data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "message_id" in data


def test_list_conversations(client: TestClient):
    """Test listing conversations."""
    response = client.get("/messages/conversations")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_metrics(client: TestClient):
    """Test analytics metrics endpoint."""
    response = client.get("/analytics/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "total_messages" in data
    assert "total_conversations" in data
    assert "escalation_rate" in data


def test_get_agent_status(client: TestClient):
    """Test agent status endpoint."""
    response = client.get("/admin/agent/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "total_conversations" in data


def test_get_metrics_endpoint(client: TestClient):
    """Test Prometheus metrics endpoint."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text
