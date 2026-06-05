"""Typed protocol models for the Project-SENA inference server MVP."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal, Union
from uuid import uuid4

from pydantic import BaseModel, Field

PROTOCOL_VERSION = "0.1"

SourceName = Literal["unity-client", "desktop-agent", "inference-server", "system"]
RiskLevel = Literal["low", "medium", "high", "critical"]
ApprovalPolicy = Literal["auto_allowed", "user_confirmation", "blocked"]
AssistantStateName = Literal[
    "idle",
    "listening",
    "thinking",
    "speaking",
    "awaiting_approval",
    "tool_running",
    "error",
    "disconnected",
]
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


class UserTextPayload(BaseModel):
    text: str
    language: str = "ko"
    input_mode: Literal["typed"] = "typed"


class UserTextMessage(Envelope):
    type: Literal["user_text"]
    payload: UserTextPayload


class SpeechInputPayload(BaseModel):
    text: str
    language: str = "ko"
    stt_engine: str
    confidence: float
    is_final: bool


class SpeechInputMessage(Envelope):
    type: Literal["speech_input"]
    payload: SpeechInputPayload


class ActiveWindowPayload(BaseModel):
    title: str | None = None
    process_name: str | None = None


class ScreenFramePayload(BaseModel):
    image_format: Literal["png", "jpeg"]
    image_base64: str
    capture_mode: Literal["full_screen", "selected_region", "active_window"]
    display_index: int
    active_window: ActiveWindowPayload | None = None


class ScreenFrameMessage(Envelope):
    type: Literal["screen_frame"]
    payload: ScreenFramePayload


class ApprovalResultPayload(BaseModel):
    approved: bool
    decision_reason: str


class ApprovalResultMessage(Envelope):
    type: Literal["approval_result"]
    payload: ApprovalResultPayload


class ApprovalRequestPayload(BaseModel):
    tool_name: ToolName
    reason: str
    risk_level: RiskLevel
    prompt: str
    arguments: dict


class ApprovalRequestMessage(Envelope):
    type: Literal["approval_request"]
    payload: ApprovalRequestPayload


class ToolResultPayload(BaseModel):
    tool_name: ToolName
    status: Literal["success", "denied", "error"]
    result: dict
    error_message: str | None = None


class ToolResultMessage(Envelope):
    type: Literal["tool_result"]
    payload: ToolResultPayload


InboundMessage = Annotated[
    Union[
        UserTextMessage,
        SpeechInputMessage,
        ScreenFrameMessage,
        ApprovalResultMessage,
        ToolResultMessage,
    ],
    Field(discriminator="type"),
]


class AssistantTextPayload(BaseModel):
    text: str
    display_text: str
    persona_state: str
    should_speak: bool


class AssistantTextMessage(Envelope):
    type: Literal["assistant_text"] = "assistant_text"
    source: SourceName = "inference-server"
    payload: AssistantTextPayload


class AssistantStatePayload(BaseModel):
    state: AssistantStateName
    detail: str


class AssistantStateMessage(Envelope):
    type: Literal["assistant_state"] = "assistant_state"
    source: SourceName = "inference-server"
    payload: AssistantStatePayload


class ToolRequestPayload(BaseModel):
    tool_name: ToolName
    arguments: dict
    reason: str
    risk_level: RiskLevel
    approval_policy: ApprovalPolicy


class ToolRequestMessage(Envelope):
    type: Literal["tool_request"] = "tool_request"
    source: SourceName = "inference-server"
    payload: ToolRequestPayload


class ErrorPayload(BaseModel):
    code: str
    message: str
    retryable: bool


class ErrorMessage(Envelope):
    type: Literal["error"] = "error"
    source: SourceName = "inference-server"
    payload: ErrorPayload


OutboundMessage = Union[
    AssistantStateMessage,
    AssistantTextMessage,
    ApprovalRequestMessage,
    ToolRequestMessage,
    ToolResultMessage,
    ErrorMessage,
]


class OutboundBatch(BaseModel):
    messages: list[OutboundMessage]


def make_assistant_state(
    session_id: str,
    state: AssistantStateName,
    detail: str,
) -> AssistantStateMessage:
    return AssistantStateMessage(
        message_id=new_message_id(),
        session_id=session_id,
        timestamp=utc_now(),
        payload=AssistantStatePayload(state=state, detail=detail),
    )


def make_assistant_text(
    session_id: str,
    text: str,
    persona_state: str = "neutral",
    should_speak: bool = True,
) -> AssistantTextMessage:
    return AssistantTextMessage(
        message_id=new_message_id(),
        session_id=session_id,
        timestamp=utc_now(),
        payload=AssistantTextPayload(
            text=text,
            display_text=text,
            persona_state=persona_state,
            should_speak=should_speak,
        ),
    )


def make_tool_request(
    session_id: str,
    tool_name: ToolName,
    arguments: dict,
    reason: str,
    risk_level: RiskLevel,
    approval_policy: ApprovalPolicy,
) -> ToolRequestMessage:
    return ToolRequestMessage(
        message_id=new_message_id(),
        session_id=session_id,
        timestamp=utc_now(),
        payload=ToolRequestPayload(
            tool_name=tool_name,
            arguments=arguments,
            reason=reason,
            risk_level=risk_level,
            approval_policy=approval_policy,
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
