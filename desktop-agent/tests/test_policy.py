from datetime import UTC, datetime

from project_sena_desktop_agent.policy import PolicyEngine
from project_sena_desktop_agent.protocol import ToolRequestMessage, ToolRequestPayload


def build_request(tool_name: str, approval_policy: str) -> ToolRequestMessage:
    return ToolRequestMessage(
        type="tool_request",
        message_id="msg-1",
        session_id="session-1",
        timestamp=datetime.now(UTC),
        payload=ToolRequestPayload(
            tool_name=tool_name,
            arguments={},
            reason="test",
            risk_level="low",
            approval_policy=approval_policy,
        ),
    )


def test_open_app_with_user_confirmation_requests_approval() -> None:
    engine = PolicyEngine()

    decision = engine.evaluate(build_request("open_app", "user_confirmation"))

    assert decision.action == "request_approval"


def test_auto_allowed_active_window_executes() -> None:
    engine = PolicyEngine()

    decision = engine.evaluate(build_request("get_active_window", "auto_allowed"))

    assert decision.action == "execute"


def test_type_text_always_requests_approval() -> None:
    engine = PolicyEngine()

    decision = engine.evaluate(build_request("type_text", "auto_allowed"))

    assert decision.action == "request_approval"


def test_capture_screen_always_requests_approval() -> None:
    engine = PolicyEngine()

    decision = engine.evaluate(build_request("capture_screen", "auto_allowed"))

    assert decision.action == "request_approval"
