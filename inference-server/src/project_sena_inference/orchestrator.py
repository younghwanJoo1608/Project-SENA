"""Message orchestration for the Project-SENA MVP server."""

from __future__ import annotations

from typing import cast

from project_sena_inference.adapters.llm import StubLLMAdapter
from project_sena_inference.adapters.tts import StubTTSAdapter
from project_sena_inference.protocol import (
    ApprovalResultMessage,
    InboundMessage,
    OutboundMessage,
    ScreenFrameMessage,
    SpeechInputMessage,
    ToolResultMessage,
    UserTextMessage,
    make_assistant_state,
    make_assistant_text,
    make_error,
    make_tool_request,
)
from project_sena_inference.session_store import SessionState, SessionStore


AUTO_TOOL_MESSAGE = (
    "\uc694\uccad\ud55c \uc791\uc5c5\uc744 \ubc14\ub85c \uc9c4\ud589\ud560 \uc218 \uc788\uc5b4. "
    "\ub370\uc2a4\ud06c\ud1b1 \uc5d0\uc774\uc804\ud2b8 \uacb0\uacfc\ub97c \uae30\ub2e4\ub9b4\uac8c."
)
APPROVAL_TOOL_MESSAGE = (
    "\uc694\uccad\ud55c \uc791\uc5c5\uc744 \uc900\ube44\ud588\uc5b4. "
    "\uc2e4\ud589 \uc804\uc5d0 \ud655\uc778\uc744 \ubc1b\uc744\uac8c."
)
SCREEN_CONTEXT_MESSAGE = (
    "\ud654\uba74 \ucee8\ud14d\uc2a4\ud2b8\ub97c \uac31\uc2e0\ud588\uc5b4. \ud604\uc7ac \uae30\uc900\uc740 "
    "{context}\uc57c. \uc544\uc9c1 \ube44\uc804 \ubaa8\ub378\uc740 \uc5f0\uacb0\ud558\uc9c0 "
    "\uc54a\uc558\uace0, \uc9c0\uae08\uc740 \uc774 \uba54\ud0c0\ub370\uc774\ud130\ub97c "
    "\ub300\ud654 \ubb38\ub9e5\uc5d0 \ubc18\uc601\ud558\ub294 \ub2e8\uacc4\uc57c."
)
APPROVED_MESSAGE = (
    "{tool} \uc2e4\ud589 \uc2b9\uc778\uc744 \ud655\uc778\ud588\uc5b4. "
    "\ub370\uc2a4\ud06c\ud1b1 \uc5d0\uc774\uc804\ud2b8 \uacb0\uacfc\ub97c \uae30\ub2e4\ub9b4\uac8c."
)
DENIED_MESSAGE = (
    "\uc54c\uaca0\uc5b4. \uadf8 \uc791\uc5c5\uc740 \uc2e4\ud589\ud558\uc9c0 \uc54a\uc744\uac8c."
)
TOOL_SUCCESS_MESSAGE = (
    "{tool} \uc2e4\ud589\uc774 \ub05d\ub0ac\uc5b4. \uacb0\uacfc\ub97c \ubc14\ud0d5\uc73c\ub85c "
    "\ub2e4\uc74c \uc791\uc5c5\uc744 \uc774\uc5b4\uac08 \uc218 \uc788\uc5b4."
)
TOOL_DENIED_MESSAGE = (
    "{tool} \uc791\uc5c5\uc740 \uc2e4\ud589\ub418\uc9c0 \uc54a\uc558\uc5b4."
)


class Orchestrator:
    """Routes inbound messages into session updates and outbound messages."""

    def __init__(
        self,
        session_store: SessionStore,
        llm_adapter: StubLLMAdapter,
        tts_adapter: StubTTSAdapter,
    ) -> None:
        self._session_store = session_store
        self._llm_adapter = llm_adapter
        self._tts_adapter = tts_adapter

    def handle(self, message: InboundMessage) -> list[OutboundMessage]:
        session = self._session_store.get_or_create(message.session_id)
        session.turn_count += 1

        if isinstance(message, UserTextMessage):
            return self._handle_user_text(session, message)
        if isinstance(message, SpeechInputMessage):
            return self._handle_speech_input(session, message)
        if isinstance(message, ScreenFrameMessage):
            return self._handle_screen_frame(session, message)
        if isinstance(message, ApprovalResultMessage):
            return self._handle_approval_result(session, message)
        if isinstance(message, ToolResultMessage):
            return self._handle_tool_result(session, message)
        return [
            cast(
                OutboundMessage,
                make_error(
                    message.session_id,
                    "unsupported_message",
                    "Unsupported message type.",
                ),
            )
        ]

    def _handle_user_text(
        self,
        session: SessionState,
        message: UserTextMessage,
    ) -> list[OutboundMessage]:
        user_text = message.payload.text.strip()
        session.recent_user_texts.append(user_text)
        outbound: list[OutboundMessage] = [
            make_assistant_state(
                session.session_id,
                "thinking",
                "Interpreting user text.",
            )
        ]

        tool_request = self._maybe_plan_tool_request(session.session_id, user_text)
        if tool_request is not None:
            session.pending_tool_name = tool_request.payload.tool_name
            if tool_request.payload.approval_policy == "auto_allowed":
                assistant_text = AUTO_TOOL_MESSAGE
                next_state = "tool_running"
                next_detail = "Waiting for desktop tool execution."
            else:
                assistant_text = APPROVAL_TOOL_MESSAGE
                next_state = "awaiting_approval"
                next_detail = "Waiting for user approval."

            outbound.append(
                make_assistant_text(
                    session.session_id,
                    assistant_text,
                    persona_state="focused",
                    should_speak=True,
                )
            )
            outbound.append(tool_request)
            outbound.append(
                make_assistant_state(
                    session.session_id,
                    next_state,
                    next_detail,
                )
            )
            return outbound

        llm_reply = self._llm_adapter.generate_reply(session, user_text)
        session.recent_assistant_texts.append(llm_reply.text)
        outbound.append(
            make_assistant_text(
                session.session_id,
                llm_reply.text,
                persona_state=llm_reply.persona_state,
                should_speak=llm_reply.should_speak,
            )
        )
        outbound.append(
            make_assistant_state(
                session.session_id,
                "idle",
                "Ready for the next input.",
            )
        )
        return outbound

    def _handle_speech_input(
        self,
        session: SessionState,
        message: SpeechInputMessage,
    ) -> list[OutboundMessage]:
        if not message.payload.is_final:
            return [
                make_assistant_state(
                    session.session_id,
                    "listening",
                    "Received partial speech recognition result.",
                )
            ]

        user_message = UserTextMessage(
            protocol_version=message.protocol_version,
            type="user_text",
            message_id=message.message_id,
            session_id=message.session_id,
            timestamp=message.timestamp,
            source=message.source,
            payload={
                "text": message.payload.text,
                "language": message.payload.language,
                "input_mode": "typed",
            },
        )
        return self._handle_user_text(session, user_message)

    def _handle_screen_frame(
        self,
        session: SessionState,
        message: ScreenFrameMessage,
    ) -> list[OutboundMessage]:
        active_window = message.payload.active_window
        window_desc = ""
        if active_window and (active_window.title or active_window.process_name):
            parts = [
                part
                for part in [active_window.process_name, active_window.title]
                if part
            ]
            window_desc = ", ".join(parts)

        session.latest_screen_context = (
            f"{message.payload.capture_mode} capture on display "
            f"{message.payload.display_index}"
            + (f" with active window {window_desc}" if window_desc else "")
        )
        response_text = SCREEN_CONTEXT_MESSAGE.format(
            context=session.latest_screen_context
        )
        session.recent_assistant_texts.append(response_text)
        return [
            make_assistant_state(
                session.session_id,
                "thinking",
                "Updating screen context.",
            ),
            make_assistant_text(
                session.session_id,
                response_text,
                persona_state="observing",
                should_speak=True,
            ),
            make_assistant_state(
                session.session_id,
                "idle",
                "Screen context stored.",
            ),
        ]

    def _handle_approval_result(
        self,
        session: SessionState,
        message: ApprovalResultMessage,
    ) -> list[OutboundMessage]:
        if message.payload.approved:
            pending_tool = session.pending_tool_name or "unknown_tool"
            return [
                make_assistant_text(
                    session.session_id,
                    APPROVED_MESSAGE.format(tool=pending_tool),
                    persona_state="focused",
                    should_speak=True,
                ),
                make_assistant_state(
                    session.session_id,
                    "tool_running",
                    "Waiting for desktop tool execution.",
                ),
            ]

        session.pending_tool_name = None
        return [
            make_assistant_text(
                session.session_id,
                DENIED_MESSAGE,
                persona_state="calm",
                should_speak=True,
            ),
            make_assistant_state(
                session.session_id,
                "idle",
                "Tool request denied by user.",
            ),
        ]

    def _handle_tool_result(
        self,
        session: SessionState,
        message: ToolResultMessage,
    ) -> list[OutboundMessage]:
        session.pending_tool_name = None
        if message.payload.status == "success":
            return [
                make_assistant_text(
                    session.session_id,
                    TOOL_SUCCESS_MESSAGE.format(tool=message.payload.tool_name),
                    persona_state="satisfied",
                    should_speak=True,
                ),
                make_assistant_state(
                    session.session_id,
                    "idle",
                    "Tool execution completed.",
                ),
            ]
        if message.payload.status == "denied":
            return [
                make_assistant_text(
                    session.session_id,
                    TOOL_DENIED_MESSAGE.format(tool=message.payload.tool_name),
                    persona_state="calm",
                    should_speak=True,
                ),
                make_assistant_state(
                    session.session_id,
                    "idle",
                    "Tool execution denied.",
                ),
            ]
        error_text = message.payload.error_message or "Unknown tool execution error."
        return [
            make_error(
                session.session_id,
                "tool_execution_error",
                error_text,
                retryable=True,
            ),
            make_assistant_state(
                session.session_id,
                "error",
                "Tool execution failed.",
            ),
        ]

    def _maybe_plan_tool_request(self, session_id: str, user_text: str):
        lowered = user_text.lower()
        if "\uba54\ubaa8\uc7a5" in user_text or "notepad" in lowered:
            return make_tool_request(
                session_id=session_id,
                tool_name="open_app",
                arguments={"app_name": "notepad"},
                reason="The user asked to open a plain text editor.",
                risk_level="low",
                approval_policy="user_confirmation",
            )
        if "\ud604\uc7ac \ucc3d" in user_text or "active window" in lowered:
            return make_tool_request(
                session_id=session_id,
                tool_name="get_active_window",
                arguments={},
                reason="The user asked for current active window context.",
                risk_level="low",
                approval_policy="auto_allowed",
            )
        return None

