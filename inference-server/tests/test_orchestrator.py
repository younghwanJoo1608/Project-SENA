from datetime import UTC, datetime

from project_sena_inference.adapters.llm import StubLLMAdapter
from project_sena_inference.adapters.tts import StubTTSAdapter
from project_sena_inference.orchestrator import Orchestrator
from project_sena_inference.protocol import (
    ApprovalRequestMessage,
    ApprovalResultMessage,
    ToolResultMessage,
    UserTextMessage,
)
from project_sena_inference.session_store import SessionStore


class FakeDesktopAgentClient:
    def __init__(self) -> None:
        self.dispatched_types: list[str] = []

    def dispatch(self, message):
        self.dispatched_types.append(message.type)
        if message.type == "tool_request":
            return ApprovalRequestMessage(
                type="approval_request",
                message_id="msg-da-1",
                session_id=message.session_id,
                timestamp=datetime.now(UTC),
                source="desktop-agent",
                payload={
                    "tool_name": "open_app",
                    "reason": message.payload.reason,
                    "risk_level": message.payload.risk_level,
                    "prompt": "The request requires explicit user confirmation.",
                    "arguments": message.payload.arguments,
                },
            )
        return ToolResultMessage(
            type="tool_result",
            message_id="msg-da-2",
            session_id=message.session_id,
            timestamp=datetime.now(UTC),
            source="desktop-agent",
            payload={
                "tool_name": "open_app",
                "status": "success",
                "result": {
                    "launched": True,
                    "app_name": "notepad",
                    "pid": 9999,
                    "process_alive": True,
                    "window_detected": False,
                },
                "error_message": None,
            },
        )


def make_orchestrator(desktop_agent_client=None) -> Orchestrator:
    return Orchestrator(
        SessionStore(),
        StubLLMAdapter(),
        StubTTSAdapter(),
        desktop_agent_client=desktop_agent_client,
    )


def test_user_text_produces_assistant_text():
    orchestrator = make_orchestrator()
    message = UserTextMessage(
        type="user_text",
        message_id="msg-1",
        session_id="session-1",
        timestamp=datetime.now(UTC),
        source="unity-client",
        payload={"text": "안녕", "language": "ko", "input_mode": "typed"},
    )

    result = orchestrator.handle(message)

    assert any(item.type == "assistant_text" for item in result)
    assert result[-1].type == "assistant_state"
    assert result[-1].payload.state == "idle"


def test_notepad_request_produces_tool_request():
    orchestrator = make_orchestrator()
    message = UserTextMessage(
        type="user_text",
        message_id="msg-2",
        session_id="session-2",
        timestamp=datetime.now(UTC),
        source="unity-client",
        payload={"text": "메모장 열어줘", "language": "ko", "input_mode": "typed"},
    )

    result = orchestrator.handle(message)

    assert any(item.type == "tool_request" for item in result)
    tool_request = next(item for item in result if item.type == "tool_request")
    assert tool_request.payload.tool_name == "open_app"


def test_notepad_request_dispatches_to_desktop_agent_when_enabled():
    desktop_agent_client = FakeDesktopAgentClient()
    orchestrator = make_orchestrator(desktop_agent_client=desktop_agent_client)
    message = UserTextMessage(
        type="user_text",
        message_id="msg-3",
        session_id="session-3",
        timestamp=datetime.now(UTC),
        source="unity-client",
        payload={"text": "메모장 열어줘", "language": "ko", "input_mode": "typed"},
    )

    result = orchestrator.handle(message)

    assert "tool_request" in desktop_agent_client.dispatched_types
    assert any(item.type == "approval_request" for item in result)
    assert not any(item.type == "tool_request" for item in result)


def test_approval_result_dispatches_and_returns_tool_result_when_enabled():
    desktop_agent_client = FakeDesktopAgentClient()
    orchestrator = make_orchestrator(desktop_agent_client=desktop_agent_client)
    first_message = UserTextMessage(
        type="user_text",
        message_id="msg-4",
        session_id="session-4",
        timestamp=datetime.now(UTC),
        source="unity-client",
        payload={"text": "메모장 열어줘", "language": "ko", "input_mode": "typed"},
    )
    orchestrator.handle(first_message)

    approval_message = ApprovalResultMessage(
        type="approval_result",
        message_id="msg-5",
        session_id="session-4",
        timestamp=datetime.now(UTC),
        source="unity-client",
        payload={
            "approved": True,
            "decision_reason": "approved in test",
        },
    )

    result = orchestrator.handle(approval_message)

    assert desktop_agent_client.dispatched_types == ["tool_request", "approval_result"]
    assert any(item.type == "tool_result" for item in result)
    assert any(item.type == "assistant_text" for item in result)
