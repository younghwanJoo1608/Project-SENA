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


@dataclass(slots=True)
class PendingToolStore:
    pending_by_session: dict[str, ToolRequestMessage] = field(default_factory=dict)

    def remember(self, request: ToolRequestMessage) -> None:
        self.pending_by_session[request.session_id] = request

    def pop(self, session_id: str) -> ToolRequestMessage | None:
        return self.pending_by_session.pop(session_id, None)


class DesktopAgentService:
    """Coordinates policy decisions and local tool execution."""

    def __init__(
        self,
        policy_engine: PolicyEngine | None = None,
        executor: DesktopToolExecutor | None = None,
        pending_store: PendingToolStore | None = None,
    ) -> None:
        self._policy = policy_engine or PolicyEngine()
        self._executor = executor or DesktopToolExecutor()
        self._pending_store = pending_store or PendingToolStore()

    def handle(self, message: InboundMessage) -> OutboundMessage:
        if message.type == "tool_request":
            return self._handle_tool_request(message)
        if message.type == "approval_result":
            return self._handle_approval_result(message)
        return make_error(
            session_id=message.session_id,
            code="unsupported_message_type",
            message=f"Unsupported message type: {message.type}",
            retryable=False,
        )

    def _handle_tool_request(self, request: ToolRequestMessage) -> OutboundMessage:
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

        return make_tool_result(
            session_id=request.session_id,
            tool_name=request.payload.tool_name,
            status="success",
            result=outcome.result,
        )
