"""Application service for desktop-agent message handling."""

from __future__ import annotations

from dataclasses import dataclass, field

from .executor import DesktopToolExecutor, ToolExecutionError
from .policy import PolicyEngine
from .protocol import (
    ApprovalResultMessage,
    InboundMessage,
    OutboundMessage,
    ToolRequestMessage,
    make_approval_request,
    make_error,
    make_tool_result,
)

MAX_CACHED_RESPONSES = 128


@dataclass(slots=True)
class PendingToolStore:
    pending_by_session: dict[str, ToolRequestMessage] = field(default_factory=dict)

    def remember(self, request: ToolRequestMessage) -> None:
        self.pending_by_session[request.session_id] = request

    def pop(self, session_id: str) -> ToolRequestMessage | None:
        return self.pending_by_session.pop(session_id, None)

    def has_pending(self, session_id: str) -> bool:
        return session_id in self.pending_by_session


@dataclass(slots=True)
class ProcessedMessageStore:
    responses_by_message_id: dict[str, OutboundMessage] = field(default_factory=dict)
    message_order: list[str] = field(default_factory=list)

    def get(self, message_id: str) -> OutboundMessage | None:
        return self.responses_by_message_id.get(message_id)

    def remember(self, message_id: str, response: OutboundMessage) -> None:
        if message_id in self.responses_by_message_id:
            self.responses_by_message_id[message_id] = response
            return

        self.responses_by_message_id[message_id] = response
        self.message_order.append(message_id)

        while len(self.message_order) > MAX_CACHED_RESPONSES:
            expired_message_id = self.message_order.pop(0)
            self.responses_by_message_id.pop(expired_message_id, None)


@dataclass(slots=True)
class DesktopTargetStore:
    targets_by_session: dict[str, dict] = field(default_factory=dict)

    def remember_open_app_result(self, session_id: str, result: dict) -> None:
        if not result.get("launched"):
            return

        target = {
            "app_name": result.get("app_name"),
            "expected_window_title": result.get("window_title"),
            "expected_window_handle": result.get("window_handle"),
            "expected_process_id": result.get("process_id") or result.get("pid"),
            "expected_process_name": result.get("process_name"),
            "expected_executable_path": result.get("executable_path"),
        }
        self.targets_by_session[session_id] = target

    def get(self, session_id: str) -> dict | None:
        target = self.targets_by_session.get(session_id)
        return dict(target) if target is not None else None


class DesktopAgentService:
    """Coordinates policy decisions and local tool execution."""

    def __init__(
        self,
        policy_engine: PolicyEngine | None = None,
        executor: DesktopToolExecutor | None = None,
        pending_store: PendingToolStore | None = None,
        processed_store: ProcessedMessageStore | None = None,
        target_store: DesktopTargetStore | None = None,
    ) -> None:
        self._policy = policy_engine or PolicyEngine()
        self._executor = executor or DesktopToolExecutor()
        self._pending_store = pending_store or PendingToolStore()
        self._processed_store = processed_store or ProcessedMessageStore()
        self._target_store = target_store or DesktopTargetStore()

    def handle(self, message: InboundMessage) -> OutboundMessage:
        cached_response = self._processed_store.get(message.message_id)
        if cached_response is not None:
            return cached_response

        if message.type == "tool_request":
            response = self._handle_tool_request(message)
        elif message.type == "approval_result":
            response = self._handle_approval_result(message)
        else:
            response = make_error(
                session_id=message.session_id,
                code="unsupported_message_type",
                message=f"Unsupported message type: {message.type}",
                retryable=False,
            )

        self._processed_store.remember(message.message_id, response)
        return response

    def _handle_tool_request(self, request: ToolRequestMessage) -> OutboundMessage:
        if self._pending_store.has_pending(request.session_id):
            return make_error(
                session_id=request.session_id,
                code="pending_tool_exists",
                message="A tool request is already waiting for approval.",
                retryable=False,
            )

        try:
            request = self._prepare_tool_request(request)
        except ToolExecutionError as exc:
            return make_tool_result(
                session_id=request.session_id,
                tool_name=request.payload.tool_name,
                status="error",
                result=exc.result,
                error_message=str(exc),
            )

        decision = self._policy.evaluate(request)
        if decision.action == "deny":
            return make_tool_result(
                session_id=request.session_id,
                tool_name=request.payload.tool_name,
                status="denied",
                result={"reason": decision.reason},
                error_message=decision.reason,
            )

        if decision.action == "request_approval":
            self._pending_store.remember(request)
            return make_approval_request(
                request=request,
                prompt=decision.reason,
            )

        return self._execute_request(request)

    def _handle_approval_result(
        self,
        approval_result: ApprovalResultMessage,
    ) -> OutboundMessage:
        request = self._pending_store.pop(approval_result.session_id)
        if request is None:
            return make_error(
                session_id=approval_result.session_id,
                code="missing_pending_tool",
                message="No pending tool request was found for this session.",
                retryable=False,
            )

        if not approval_result.payload.approved:
            return make_tool_result(
                session_id=approval_result.session_id,
                tool_name=request.payload.tool_name,
                status="denied",
                result={"reason": approval_result.payload.decision_reason},
                error_message=approval_result.payload.decision_reason,
            )

        return self._execute_request(request)

    def _execute_request(self, request: ToolRequestMessage) -> OutboundMessage:
        try:
            outcome = self._executor.execute(
                tool_name=request.payload.tool_name,
                arguments=request.payload.arguments,
            )
        except ToolExecutionError as exc:
            return make_tool_result(
                session_id=request.session_id,
                tool_name=request.payload.tool_name,
                status="error",
                result=exc.result,
                error_message=str(exc),
            )
        except Exception as exc:  # pragma: no cover - defensive boundary
            return make_tool_result(
                session_id=request.session_id,
                tool_name=request.payload.tool_name,
                status="error",
                result={
                    "reason": "unexpected_executor_error",
                    "error_type": type(exc).__name__,
                },
                error_message=str(exc),
            )

        if request.payload.tool_name == "open_app":
            self._target_store.remember_open_app_result(
                request.session_id,
                outcome.result,
            )

        return make_tool_result(
            session_id=request.session_id,
            tool_name=request.payload.tool_name,
            status="success",
            result=outcome.result,
        )

    def _prepare_tool_request(self, request: ToolRequestMessage) -> ToolRequestMessage:
        if request.payload.tool_name != "type_text":
            return request

        arguments = dict(request.payload.arguments)
        if "expected_window_handle" in arguments or "expected_process_id" in arguments:
            return request

        target_app = str(arguments.get("target_app") or "").strip()
        if target_app:
            window = self._executor.resolve_window_target({"target_app": target_app})
            if window is None:
                raise ToolExecutionError(
                    "The requested app window could not be found for type_text.",
                    result={
                        "typed": False,
                        "reason": "target_app_window_not_found",
                        "target_app": target_app,
                    },
                )

            return self._with_expected_window(request, arguments, window)

        remembered_target = self._target_store.get(request.session_id)
        if remembered_target is not None:
            window = self._executor.resolve_window_target(remembered_target)
            if window is None:
                raise ToolExecutionError(
                    "The last desktop target window could not be found for type_text.",
                    result={
                        "typed": False,
                        "reason": "target_window_not_found",
                        "expected_window": remembered_target,
                    },
                )

            arguments.update(remembered_target)
            return self._with_expected_window(request, arguments, window)

        window = self._executor.get_foreground_window()
        if window is None:
            raise ToolExecutionError(
                "No active foreground window was detected for type_text.",
                result={"typed": False, "reason": "missing_foreground_window"},
            )

        return self._with_expected_window(request, arguments, window)

    @staticmethod
    def _with_expected_window(
        request: ToolRequestMessage,
        arguments: dict,
        window,
    ) -> ToolRequestMessage:
        arguments.update(
            {
                "expected_window_title": window.title,
                "expected_window_handle": window.handle,
                "expected_process_id": window.process_id,
                "expected_process_name": window.process_name,
                "expected_executable_path": window.executable_path,
            }
        )
        payload = request.payload.model_copy(update={"arguments": arguments})
        return request.model_copy(update={"payload": payload})
