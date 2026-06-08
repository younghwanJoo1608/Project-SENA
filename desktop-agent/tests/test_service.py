from datetime import UTC, datetime

from project_sena_desktop_agent.executor import ToolExecutionOutcome, WindowInfo
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
        self.resolved_target: WindowInfo | None = None
        self.resolve_requests: list[dict] = []

    def execute(self, tool_name: str, arguments: dict) -> ToolExecutionOutcome:
        self.calls.append((tool_name, arguments))
        if tool_name == "open_app":
            return ToolExecutionOutcome(
                result={
                    "launched": True,
                    "app_name": arguments.get("app_name", "notepad"),
                    "pid": 4321,
                    "process_alive": True,
                    "window_detected": False,
                    "process_id": 4321,
                    "process_name": "notepad.exe",
                }
            )

        return ToolExecutionOutcome(result={"ok": True, "tool_name": tool_name})

    def get_foreground_window(self) -> WindowInfo:
        return WindowInfo(
            handle=1001,
            title="Untitled - Notepad",
            process_id=4321,
            process_name="notepad.exe",
            executable_path="C:\\Windows\\System32\\notepad.exe",
        )

    def resolve_window_target(self, target: dict) -> WindowInfo | None:
        self.resolve_requests.append(target)
        return self.resolved_target


def build_tool_request(
    tool_name: str,
    approval_policy: str,
    arguments: dict | None = None,
    message_id: str = "msg-1",
) -> ToolRequestMessage:
    return ToolRequestMessage(
        type="tool_request",
        message_id=message_id,
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


def test_auto_allowed_active_window_executes_without_approval() -> None:
    executor = FakeExecutor()
    service = DesktopAgentService(
        policy_engine=PolicyEngine(),
        executor=executor,
        pending_store=PendingToolStore(),
    )

    response = service.handle(build_tool_request("get_active_window", "auto_allowed"))

    assert response.type == "tool_result"
    assert response.payload.status == "success"
    assert response.payload.result == {"ok": True, "tool_name": "get_active_window"}
    assert executor.calls == [("get_active_window", {})]


def test_type_text_approval_request_includes_foreground_window_snapshot() -> None:
    executor = FakeExecutor()
    service = DesktopAgentService(
        policy_engine=PolicyEngine(),
        executor=executor,
        pending_store=PendingToolStore(),
    )

    response = service.handle(
        build_tool_request(
            "type_text",
            "user_confirmation",
            {"text": "안녕"},
        )
    )

    assert response.type == "approval_request"
    assert response.payload.tool_name == "type_text"
    assert response.payload.arguments["text"] == "안녕"
    assert response.payload.arguments["expected_window_title"] == "Untitled - Notepad"
    assert response.payload.arguments["expected_window_handle"] == 1001
    assert response.payload.arguments["expected_process_name"] == "notepad.exe"
    assert executor.calls == []


def test_type_text_reuses_remembered_open_app_target_instead_of_foreground() -> None:
    executor = FakeExecutor()
    executor.resolved_target = WindowInfo(
        handle=2002,
        title="Untitled - Notepad",
        process_id=4321,
        process_name="notepad.exe",
        executable_path="C:\\Windows\\System32\\notepad.exe",
    )
    store = PendingToolStore()
    service = DesktopAgentService(
        policy_engine=PolicyEngine(),
        executor=executor,
        pending_store=store,
    )
    service.handle(
        build_tool_request("open_app", "user_confirmation", {"app_name": "notepad"})
    )
    service.handle(build_approval_result(True))

    response = service.handle(
        build_tool_request(
            "type_text",
            "user_confirmation",
            {"text": "안녕"},
            message_id="msg-type-after-open",
        )
    )

    assert response.type == "approval_request"
    assert response.payload.arguments["expected_window_handle"] == 2002
    assert response.payload.arguments["expected_window_title"] == "Untitled - Notepad"
    assert response.payload.arguments["expected_process_name"] == "notepad.exe"


def test_type_text_resolves_explicit_target_app_before_foreground() -> None:
    executor = FakeExecutor()
    executor.resolved_target = WindowInfo(
        handle=3003,
        title="Already Open - Notepad",
        process_id=8765,
        process_name="notepad.exe",
        executable_path="C:\\Windows\\System32\\notepad.exe",
    )
    service = DesktopAgentService(
        policy_engine=PolicyEngine(),
        executor=executor,
        pending_store=PendingToolStore(),
    )

    response = service.handle(
        build_tool_request(
            "type_text",
            "user_confirmation",
            {"text": "안녕", "target_app": "notepad"},
            message_id="msg-type-existing-notepad",
        )
    )

    assert response.type == "approval_request"
    assert executor.resolve_requests == [{"target_app": "notepad"}]
    assert response.payload.arguments["target_app"] == "notepad"
    assert response.payload.arguments["expected_window_handle"] == 3003
    assert response.payload.arguments["expected_window_title"] == "Already Open - Notepad"
    assert response.payload.arguments["expected_process_name"] == "notepad.exe"
    assert executor.calls == []


def test_type_text_returns_error_when_explicit_target_app_is_missing() -> None:
    executor = FakeExecutor()
    service = DesktopAgentService(
        policy_engine=PolicyEngine(),
        executor=executor,
        pending_store=PendingToolStore(),
    )

    response = service.handle(
        build_tool_request(
            "type_text",
            "user_confirmation",
            {"text": "안녕", "target_app": "notepad"},
            message_id="msg-type-missing-notepad",
        )
    )

    assert response.type == "tool_result"
    assert response.payload.status == "error"
    assert response.payload.result["reason"] == "target_app_window_not_found"
    assert response.payload.result["target_app"] == "notepad"
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


def test_duplicate_approval_result_returns_cached_tool_result() -> None:
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
    approval_result = build_approval_result(True)

    first_response = service.handle(approval_result)
    second_response = service.handle(approval_result)

    assert first_response.type == "tool_result"
    assert second_response.type == "tool_result"
    assert first_response.message_id == second_response.message_id
    assert executor.calls == [("open_app", {"app_name": "notepad"})]


def test_second_tool_request_is_rejected_while_approval_is_pending() -> None:
    executor = FakeExecutor()
    store = PendingToolStore()
    service = DesktopAgentService(
        policy_engine=PolicyEngine(),
        executor=executor,
        pending_store=store,
    )
    service.handle(
        build_tool_request(
            "open_app",
            "user_confirmation",
            {"app_name": "notepad"},
            message_id="msg-tool-1",
        )
    )

    response = service.handle(
        build_tool_request(
            "open_app",
            "user_confirmation",
            {"app_name": "notepad"},
            message_id="msg-tool-2",
        )
    )

    assert response.type == "error"
    assert response.payload.code == "pending_tool_exists"
    assert executor.calls == []
