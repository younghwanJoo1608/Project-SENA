from datetime import UTC, datetime

from project_sena_inference.adapters.llm import StubLLMAdapter
from project_sena_inference.adapters.tts import StubTTSAdapter
from project_sena_inference.orchestrator import Orchestrator
from project_sena_inference.protocol import UserTextMessage
from project_sena_inference.session_store import SessionStore


def make_orchestrator() -> Orchestrator:
    return Orchestrator(SessionStore(), StubLLMAdapter(), StubTTSAdapter())


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

