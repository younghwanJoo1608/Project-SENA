from datetime import UTC, datetime

from project_sena_desktop_agent.executor import ToolExecutionOutcome
from project_sena_desktop_agent.policy import PolicyEngine
from project_sena_desktop_agent.protocol import (
    ApprovalResultMessage,
    ApprovalResultPayload,
    ToolRequestMessage,
    ToolRequestPayload,
)
from project_sena_desktop_agent.service import DesktopAgentService, PendingToolStore


class FakeExecutor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def execute(self, tool_name: str, arguments: dict) -> ToolExecutionOutcome:
        self.calls.append((tool_name, arguments))
        return ToolExecutionOutcome(result={"ok": True, "tool_name": tool_name})


def build_tool_request(
    tool_name: str,
    approval_policy: str,
    arguments: dict | None = None,
) -> ToolRequestMessage:
    return ToolRequestMessage(
        type="tool_request",
        message_id="msg-1",
        session_id="session-1",
        timestamp=datetime.now(UTC),
        payload=ToolRequestPayload(
            tool_name=tool_name,
            arguments=arguments or {},
            reason="test",
            risk_level="low",
            approval_policy=approval_policy,
        ),
    )


def build_approval_result(approved: bool) -> ApprovalResultMessage:
    return ApprovalResultMessage(
        type="approval_result",
        message_id="msg-2",
        session_id="session-1",
        timestamp=datetime.now(UTC),
        source="unity-client",
        payload=ApprovalResultPayload(
            approved=approved,
            decision_reason="approved" if approved else "denied by user",
        ),
    )


def test_tool_request_returns_approval_request_when_confirmation_is_needed() -> None:
    executor = FakeExecutor()
    service = DesktopAgentService(
        policy_engine=PolicyEngine(),
        executor=executor,
        pending_store=PendingToolStore(),
    )

    response = service.handle(
        build_tool_request("open_app", "user_confirmation", {"app_name": "notepad"})
    )

    assert response.type == "approval_request"
    assert response.payload.tool_name == "open_app"
    assert executor.calls == []


def test_approved_tool_request_executes_after_approval() -> None:
    executor = FakeExecutor()
    store = PendingToolStore()
    service = DesktopAgentService(
        policy_engine=PolicyEngine(),
        executor=executor,
        pending_store=store,
    )
    service.handle(
        build_tool_request("open_app", "user_confirmation", {"app_name": "notepad"})
    )

    response = service.handle(build_approval_result(True))

    assert response.type == "tool_result"
    assert response.payload.status == "success"
    assert executor.calls == [("open_app", {"app_name": "notepad"})]


def test_denied_approval_returns_denied_tool_result() -> None:
    executor = FakeExecutor()
    store = PendingToolStore()
    service = DesktopAgentService(
        policy_engine=PolicyEngine(),
        executor=executor,
        pending_store=store,
    )
    service.handle(
        build_tool_request("open_app", "user_confirmation", {"app_name": "notepad"})
    )

    response = service.handle(build_approval_result(False))

    assert response.type == "tool_result"
    assert response.payload.status == "denied"
    assert executor.calls == []
