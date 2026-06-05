"""Policy engine for desktop-local tool execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .protocol import ApprovalPolicy, ToolRequestMessage

DecisionType = Literal["execute", "request_approval", "deny"]


@dataclass(slots=True)
class PolicyDecision:
    action: DecisionType
    reason: str


class PolicyEngine:
    """Decides whether a tool request may run on the desktop."""

    def evaluate(self, request: ToolRequestMessage) -> PolicyDecision:
        tool_name = request.payload.tool_name
        approval_policy = request.payload.approval_policy

        if tool_name not in {
            "capture_screen",
            "get_active_window",
            "open_app",
            "type_text",
        }:
            return PolicyDecision("deny", "Unknown tools are denied by default.")

        if approval_policy == "blocked":
            return PolicyDecision("deny", "The request is blocked by server policy.")

        if tool_name == "type_text":
            return PolicyDecision(
                "request_approval",
                "Typing text mutates desktop state and requires confirmation.",
            )

        if approval_policy == "user_confirmation":
            return PolicyDecision(
                "request_approval",
                "The request requires explicit user confirmation.",
            )

        return PolicyDecision("execute", "The request may run immediately.")


def requires_user_confirmation(approval_policy: ApprovalPolicy) -> bool:
    return approval_policy == "user_confirmation"
