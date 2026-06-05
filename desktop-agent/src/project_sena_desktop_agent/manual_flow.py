"""Manual local test helpers for desktop-agent integration."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime

from .protocol import (
    ApprovalResultMessage,
    ApprovalResultPayload,
    ToolRequestMessage,
    ToolRequestPayload,
)
from .service import DesktopAgentService


def utc_now() -> datetime:
    return datetime.now(UTC)


def build_open_app_request(app_name: str) -> ToolRequestMessage:
    return ToolRequestMessage(
        type="tool_request",
        message_id="msg-manual-tool-request",
        session_id="session-manual-open-app",
        timestamp=utc_now(),
        source="inference-server",
        payload=ToolRequestPayload(
            tool_name="open_app",
            arguments={"app_name": app_name},
            reason="Manual desktop-agent verification flow.",
            risk_level="low",
            approval_policy="user_confirmation",
        ),
    )


def build_approval_result(approved: bool) -> ApprovalResultMessage:
    return ApprovalResultMessage(
        type="approval_result",
        message_id="msg-manual-approval-result",
        session_id="session-manual-open-app",
        timestamp=utc_now(),
        source="unity-client",
        payload=ApprovalResultPayload(
            approved=approved,
            decision_reason="approved in manual flow"
            if approved
            else "denied in manual flow",
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a manual desktop-agent tool flow without HTTP."
    )
    parser.add_argument(
        "--app-name",
        default="notepad",
        help="Application name for the open_app flow.",
    )
    args = parser.parse_args()

    service = DesktopAgentService()

    tool_request = build_open_app_request(args.app_name)
    first_response = service.handle(tool_request)
    print("== Tool request response ==")
    print(json.dumps(first_response.model_dump(mode="json"), ensure_ascii=False, indent=2))

    if first_response.type != "approval_request":
        print("Flow ended before approval.")
        return 0

    approval_input = input("Approve this request? [y/N]: ").strip().lower()
    approved = approval_input in {"y", "yes"}

    approval_result = build_approval_result(approved)
    second_response = service.handle(approval_result)
    print("== Approval result response ==")
    print(json.dumps(second_response.model_dump(mode="json"), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
