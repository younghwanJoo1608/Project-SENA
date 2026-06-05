from fastapi.testclient import TestClient

from project_sena_desktop_agent.api import app


def test_health_endpoint_returns_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "project-sena-desktop-agent",
        "protocol_version": "0.1",
    }


def test_tool_request_endpoint_returns_approval_request() -> None:
    payload = {
        "protocol_version": "0.1",
        "type": "tool_request",
        "message_id": "msg-http-1",
        "session_id": "session-http-1",
        "timestamp": "2026-06-05T12:00:00Z",
        "source": "inference-server",
        "payload": {
            "tool_name": "open_app",
            "arguments": {"app_name": "notepad"},
            "reason": "The user asked to open a plain text editor.",
            "risk_level": "low",
            "approval_policy": "user_confirmation",
        },
    }

    with TestClient(app) as client:
        response = client.post("/v1/messages", json=payload)

    data = response.json()
    assert response.status_code == 200
    assert data["type"] == "approval_request"
    assert data["payload"]["tool_name"] == "open_app"
