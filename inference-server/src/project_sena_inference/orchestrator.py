"""Message orchestration for the Project-SENA MVP server."""

from __future__ import annotations

import re
from typing import cast

from project_sena_inference.adapters.desktop_agent import (
    DesktopAgentClientError,
    HttpDesktopAgentClient,
)
from project_sena_inference.adapters.llm import StubLLMAdapter
from project_sena_inference.adapters.tts import StubTTSAdapter
from project_sena_inference.protocol import (
    ApprovalRequestMessage,
    ApprovalResultMessage,
    ErrorMessage,
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
PENDING_APPROVAL_MESSAGE = (
    "\uc544\uc9c1 \ud655\uc778\uc744 \uae30\ub2e4\ub9ac\ub294 \uc791\uc5c5\uc774 \uc788\uc5b4. "
    "\uba3c\uc800 \uc2b9\uc778 \ucc3d\uc5d0\uc11c \ud5c8\uc6a9\ud558\uac70\ub098 \uac70\uc808\ud574\uc918."
)
PENDING_TOOL_MESSAGE = (
    "\uc774\ubbf8 \uc2e4\ud589 \uc911\uc778 \uc791\uc5c5\uc774 \uc788\uc5b4. "
    "\uacb0\uacfc\uac00 \ub3cc\uc544\uc628 \ub4a4\uc5d0 \ub2e4\uc74c \uc694\uccad\uc744 \ubc1b\uc744\uac8c."
)
TEST_FAILURE_APP_NAME = "__project_sena_missing_app__"
SELF_DESCRIBING_SUCCESS_TOOLS = {"get_active_window"}


class Orchestrator:
    """Routes inbound messages into session updates and outbound messages."""

    def __init__(
        self,
        session_store: SessionStore,
        llm_adapter: StubLLMAdapter,
        tts_adapter: StubTTSAdapter,
        desktop_agent_client: HttpDesktopAgentClient | None = None,
        failure_injection_enabled: bool = False,
    ) -> None:
        self._session_store = session_store
        self._llm_adapter = llm_adapter
        self._tts_adapter = tts_adapter
        self._desktop_agent_client = desktop_agent_client
        self._failure_injection_enabled = failure_injection_enabled

    def handle(self, message: InboundMessage) -> list[OutboundMessage]:
        session = self._session_store.get_or_create(message.session_id)
        cached_response = session.get_cached_response(message.message_id)
        if cached_response is not None:
            return cached_response

        session.turn_count += 1

        if isinstance(message, UserTextMessage):
            response = self._handle_user_text(session, message)
        elif isinstance(message, SpeechInputMessage):
            response = self._handle_speech_input(session, message)
        elif isinstance(message, ScreenFrameMessage):
            response = self._handle_screen_frame(session, message)
        elif isinstance(message, ApprovalResultMessage):
            response = self._handle_approval_result(session, message)
        elif isinstance(message, ToolResultMessage):
            response = self._handle_tool_result(session, message)
        else:
            response = [
                cast(
                    OutboundMessage,
                    make_error(
                        message.session_id,
                        "unsupported_message",
                        "Unsupported message type.",
                    ),
                )
            ]
        session.remember_response(message.message_id, response)
        return response

    def _handle_user_text(
        self,
        session: SessionState,
        message: UserTextMessage,
    ) -> list[OutboundMessage]:
        if session.pending_tool_name is not None:
            return self._handle_user_text_during_pending_tool(session)

        user_text = message.payload.text.strip()
        session.recent_user_texts.append(user_text)
        outbound: list[OutboundMessage] = [
            make_assistant_state(
                session.session_id,
                "thinking",
                "Interpreting user text.",
            )
        ]

        tool_request = self._maybe_plan_tool_request(session, user_text)
        if tool_request is not None:
            if self._desktop_agent_client is None:
                if tool_request.payload.approval_policy == "auto_allowed":
                    assistant_text = AUTO_TOOL_MESSAGE
                    next_state = "tool_running"
                    next_detail = "Waiting for desktop tool execution."
                else:
                    assistant_text = APPROVAL_TOOL_MESSAGE
                    next_state = "awaiting_approval"
                    next_detail = "Waiting for user approval."

                session.start_pending_tool(
                    tool_request.payload.tool_name,
                    tool_request.message_id,
                    next_state,
                )
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

            outbound.extend(self._dispatch_tool_request(session, tool_request))
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
        if session.pending_tool_name is None:
            return [
                make_error(
                    session.session_id,
                    "stale_approval_result",
                    "No pending approval exists for this session.",
                    retryable=False,
                ),
                make_assistant_state(
                    session.session_id,
                    "idle",
                    "No pending approval exists.",
                ),
            ]

        if self._desktop_agent_client is not None:
            return self._dispatch_approval_result(session, message)

        if message.payload.approved:
            pending_tool = session.pending_tool_name or "unknown_tool"
            return [
                make_assistant_text(
                    session.session_id,
                    APPROVED_MESSAGE.format(tool=_tool_display_name(pending_tool)),
                    persona_state="focused",
                    should_speak=True,
                ),
                make_assistant_state(
                    session.session_id,
                    "tool_running",
                    "Waiting for desktop tool execution.",
                ),
            ]

        session.clear_pending_tool()
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
        self._update_desktop_target_from_tool_result(session, message)
        session.clear_pending_tool()
        if message.payload.status == "success":
            if message.payload.tool_name in SELF_DESCRIBING_SUCCESS_TOOLS:
                return [
                    make_assistant_state(
                        session.session_id,
                        "idle",
                        "Observation completed.",
                    )
                ]

            return [
                make_assistant_text(
                    session.session_id,
                    TOOL_SUCCESS_MESSAGE.format(
                        tool=_tool_display_name(message.payload.tool_name)
                    ),
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
                    TOOL_DENIED_MESSAGE.format(
                        tool=_tool_display_name(message.payload.tool_name)
                    ),
                    persona_state="calm",
                    should_speak=True,
                ),
                make_assistant_state(
                    session.session_id,
                    "idle",
                    "Tool execution denied.",
                ),
            ]
        return [
            make_assistant_state(
                session.session_id,
                "error",
                "Tool execution failed.",
            ),
        ]

    def _maybe_plan_tool_request(self, session: SessionState, user_text: str):
        lowered = user_text.lower()
        if self._failure_injection_enabled and (
            "failure test" in lowered
            or TEST_FAILURE_APP_NAME in lowered
            or "\uc2e4\ud328 \ud14c\uc2a4\ud2b8" in user_text
        ):
            return make_tool_request(
                session_id=session.session_id,
                tool_name="open_app",
                arguments={"app_name": TEST_FAILURE_APP_NAME},
                reason="Project-SENA failure injection test requested.",
                risk_level="low",
                approval_policy="user_confirmation",
            )

        type_text_request = _extract_type_text_request(user_text, lowered)
        if type_text_request:
            arguments = {"text": type_text_request["text"]}
            target_app = type_text_request.get("target_app")
            if target_app:
                arguments["target_app"] = target_app
            elif session.latest_desktop_target:
                arguments.update(session.latest_desktop_target)

            return make_tool_request(
                session_id=session.session_id,
                tool_name="type_text",
                arguments=arguments,
                reason="The user asked to type text into the active foreground window.",
                risk_level="medium",
                approval_policy="user_confirmation",
            )

        if "\uba54\ubaa8\uc7a5" in user_text or "notepad" in lowered:
            return make_tool_request(
                session_id=session.session_id,
                tool_name="open_app",
                arguments={"app_name": "notepad"},
                reason="The user asked to open a plain text editor.",
                risk_level="low",
                approval_policy="user_confirmation",
            )
        if "\ud604\uc7ac \ucc3d" in user_text or "active window" in lowered:
            return make_tool_request(
                session_id=session.session_id,
                tool_name="get_active_window",
                arguments={},
                reason="The user asked for current active window context.",
                risk_level="low",
                approval_policy="auto_allowed",
            )
        return None

    def _dispatch_tool_request(
        self,
        session: SessionState,
        tool_request,
    ) -> list[OutboundMessage]:
        session.start_pending_tool(
            tool_request.payload.tool_name,
            tool_request.message_id,
            "dispatching",
        )
        try:
            response = self._desktop_agent_client.dispatch(tool_request)
        except DesktopAgentClientError as exc:
            session.clear_pending_tool()
            return [
                make_error(
                    session.session_id,
                    "desktop_agent_unreachable",
                    str(exc),
                    retryable=True,
                ),
                make_assistant_state(
                    session.session_id,
                    "error",
                    "Desktop-agent dispatch failed.",
                ),
            ]

        if isinstance(response, ApprovalRequestMessage):
            session.pending_tool_state = "awaiting_approval"
            return [
                make_assistant_text(
                    session.session_id,
                    APPROVAL_TOOL_MESSAGE,
                    persona_state="focused",
                    should_speak=True,
                ),
                response,
                make_assistant_state(
                    session.session_id,
                    "awaiting_approval",
                    "Waiting for user approval.",
                ),
            ]

        if isinstance(response, ToolResultMessage):
            return [response, *self._handle_tool_result(session, response)]

        session.clear_pending_tool()
        return [
            cast(OutboundMessage, response),
            make_assistant_state(
                session.session_id,
                "error",
                "Desktop-agent returned an error.",
            ),
        ]

    def _dispatch_approval_result(
        self,
        session: SessionState,
        approval_result: ApprovalResultMessage,
    ) -> list[OutboundMessage]:
        try:
            response = self._desktop_agent_client.dispatch(approval_result)
        except DesktopAgentClientError as exc:
            session.clear_pending_tool()
            return [
                make_error(
                    session.session_id,
                    "desktop_agent_unreachable",
                    str(exc),
                    retryable=True,
                ),
                make_assistant_state(
                    session.session_id,
                    "error",
                    "Desktop-agent dispatch failed.",
                ),
            ]

        if isinstance(response, ToolResultMessage):
            return [response, *self._handle_tool_result(session, response)]

        if isinstance(response, ErrorMessage):
            session.clear_pending_tool()
            return [
                cast(OutboundMessage, response),
                make_assistant_state(
                    session.session_id,
                    "error",
                    "Desktop-agent returned an error.",
                ),
            ]

        return [
            cast(
                OutboundMessage,
                make_error(
                    session.session_id,
                    "unexpected_desktop_agent_response",
                    "Desktop-agent returned approval_request after approval_result.",
                    retryable=False,
                ),
            ),
            make_assistant_state(
                session.session_id,
                "error",
                "Unexpected desktop-agent response type.",
            ),
        ]

    def _handle_user_text_during_pending_tool(
        self,
        session: SessionState,
    ) -> list[OutboundMessage]:
        if session.pending_tool_state == "awaiting_approval":
            return [
                make_assistant_text(
                    session.session_id,
                    PENDING_APPROVAL_MESSAGE,
                    persona_state="focused",
                    should_speak=True,
                ),
                make_assistant_state(
                    session.session_id,
                    "awaiting_approval",
                    "Waiting for user approval.",
                ),
            ]

        return [
            make_assistant_text(
                session.session_id,
                PENDING_TOOL_MESSAGE,
                persona_state="focused",
                should_speak=True,
            ),
            make_assistant_state(
                session.session_id,
                "tool_running",
                "Waiting for desktop tool execution.",
            ),
        ]

    @staticmethod
    def _update_desktop_target_from_tool_result(
        session: SessionState,
        message: ToolResultMessage,
    ) -> None:
        if (
            message.payload.status != "success"
            or message.payload.tool_name != "open_app"
        ):
            return

        result = message.payload.result
        window_handle = result.get("window_handle")
        if not window_handle:
            return

        session.latest_desktop_target = {
            "expected_window_title": result.get("window_title"),
            "expected_window_handle": window_handle,
            "expected_process_id": result.get("process_id") or result.get("pid"),
            "expected_process_name": result.get("process_name"),
            "expected_executable_path": result.get("executable_path"),
        }


def _tool_display_name(tool_name: str) -> str:
    return {
        "open_app": "\uc571 \uc2e4\ud589",
        "get_active_window": "\ud604\uc7ac \ucc3d \ud655\uc778",
        "capture_screen": "\ud654\uba74 \ucea1\ucc98",
        "type_text": "\ud14d\uc2a4\ud2b8 \uc785\ub825",
    }.get(tool_name, tool_name)


def _extract_type_text_request(user_text: str, lowered: str) -> dict[str, str] | None:
    if lowered.startswith("type "):
        return _clean_type_text_candidate(user_text[5:])
    if lowered.startswith("enter "):
        return _clean_type_text_candidate(user_text[6:])

    quoted_match = re.search(
        r"[\u0022\u0027\u201c\u201d\u2018\u2019](.+?)[\u0022\u0027\u201c\u201d\u2018\u2019]"
        r"\s*(?:\ub77c\uace0\s*)?(?:\uc785\ub825|\uc368)",
        user_text,
    )
    if quoted_match:
        request = _clean_type_text_candidate(quoted_match.group(1))
        if request and "\uba54\ubaa8\uc7a5" in user_text:
            request["target_app"] = "notepad"
        return request

    for marker in ("\uc785\ub825", "\uc368"):
        marker_index = user_text.find(marker)
        if marker_index > 0:
            return _clean_type_text_candidate(user_text[:marker_index])

    return None


def _clean_type_text_candidate(candidate: str) -> dict[str, str] | None:
    text = candidate.strip()
    target_app: str | None = None
    for prefix, prefix_target_app in (
        ("\ud604\uc7ac \ucc3d\uc5d0 ", None),
        ("\uc5ec\uae30\uc5d0 ", None),
        ("\uc5f4\ub824 \uc788\ub294 \uba54\ubaa8\uc7a5\uc5d0 ", "notepad"),
        ("\uba54\ubaa8\uc7a5\uc5d0 ", "notepad"),
        ("notepad에 ", "notepad"),
        ("notepad ", "notepad"),
    ):
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
            target_app = prefix_target_app
            break

    if text.endswith("\ub77c\uace0"):
        text = text[: -len("\ub77c\uace0")].strip()

    if not text:
        return None

    request = {"text": text}
    if target_app:
        request["target_app"] = target_app
    return request
