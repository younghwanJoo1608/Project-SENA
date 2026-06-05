"""Typed protocol models for the Project-SENA desktop agent MVP."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal, Union
from uuid import uuid4

from pydantic import BaseModel, Field

PROTOCOL_VERSION = "0.1"

SourceName = Literal["unity-client", "desktop-agent", "inference-server", "system"]
RiskLevel = Literal["low", "medium", "high", "critical"]
ApprovalPolicy = Literal["auto_allowed", "user_confirmation", "blocked"]
ToolName = Literal["capture_screen", "get_active_window", "open_app", "type_text"]


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_message_id() -> str:
    return f"msg-{uuid4().hex}"


class Envelope(BaseModel):
    protocol_version: str = PROTOCOL_VERSION
    type: str
    message_id: str
    session_id: str
    timestamp: datetime
    source: SourceName


class ToolRequestPayload(BaseModel):
    tool_name: ToolName
    arguments: dict
    reason: str
    risk_level: RiskLevel
    approval_policy: ApprovalPolicy


class ToolRequestMessage(Envelope):
    type: Literal["tool_request"]
    source: SourceName = "inference-server"
    payload: ToolRequestPayload


class ApprovalResultPayload(BaseModel):
    approved: bool
    decision_reason: str


class ApprovalResultMessage(Envelope):
    type: Literal["approval_result"]
    payload: ApprovalResultPayload


InboundMessage = Annotated[
    Union[ToolRequestMessage, ApprovalResultMessage],
    Field(discriminator="type"),
]


class ApprovalRequestPayload(BaseModel):
    tool_name: ToolName
    reason: str
    risk_level: RiskLevel
    prompt: str
    arguments: dict


class ApprovalRequestMessage(Envelope):
    type: Literal["approval_request"] = "approval_request"
    source: SourceName = "desktop-agent"
    payload: ApprovalRequestPayload


class ToolResultPayload(BaseModel):
    tool_name: ToolName
    status: Literal["success", "denied", "error"]
    result: dict
    error_message: str | None = None


class ToolResultMessage(Envelope):
    type: Literal["tool_result"] = "tool_result"
    source: SourceName = "desktop-agent"
    payload: ToolResultPayload


class ErrorPayload(BaseModel):
    code: str
    message: str
    retryable: bool


class ErrorMessage(Envelope):
    type: Literal["error"] = "error"
    source: SourceName = "desktop-agent"
    payload: ErrorPayload


OutboundMessage = Union[ApprovalRequestMessage, ToolResultMessage, ErrorMessage]


def make_approval_request(
    request: ToolRequestMessage,
    prompt: str,
) -> ApprovalRequestMessage:
    return ApprovalRequestMessage(
        message_id=new_message_id(),
        session_id=request.session_id,
        timestamp=utc_now(),
        payload=ApprovalRequestPayload(
            tool_name=request.payload.tool_name,
            reason=request.payload.reason,
            risk_level=request.payload.risk_level,
            prompt=prompt,
            arguments=request.payload.arguments,
        ),
    )


def make_tool_result(
    session_id: str,
    tool_name: ToolName,
    status: Literal["success", "denied", "error"],
    result: dict,
    error_message: str | None = None,
) -> ToolResultMessage:
    return ToolResultMessage(
        message_id=new_message_id(),
        session_id=session_id,
        timestamp=utc_now(),
        payload=ToolResultPayload(
            tool_name=tool_name,
            status=status,
            result=result,
            error_message=error_message,
        ),
    )


def make_error(
    session_id: str,
    code: str,
    message: str,
    retryable: bool = False,
) -> ErrorMessage:
    return ErrorMessage(
        message_id=new_message_id(),
        session_id=session_id,
        timestamp=utc_now(),
        payload=ErrorPayload(code=code, message=message, retryable=retryable),
    )
