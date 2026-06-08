"""In-memory session storage for the MVP server."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

MAX_CACHED_RESPONSES = 128


@dataclass
class SessionState:
    session_id: str
    turn_count: int = 0
    recent_user_texts: list[str] = field(default_factory=list)
    recent_assistant_texts: list[str] = field(default_factory=list)
    latest_screen_context: str | None = None
    latest_desktop_target: dict[str, Any] | None = None
    pending_tool_name: str | None = None
    pending_tool_request_id: str | None = None
    pending_tool_state: str | None = None
    processed_responses: dict[str, list[Any]] = field(default_factory=dict)
    processed_message_order: list[str] = field(default_factory=list)

    def get_cached_response(self, message_id: str) -> list[Any] | None:
        response = self.processed_responses.get(message_id)
        return list(response) if response is not None else None

    def remember_response(self, message_id: str, response: list[Any]) -> None:
        if message_id in self.processed_responses:
            self.processed_responses[message_id] = list(response)
            return

        self.processed_responses[message_id] = list(response)
        self.processed_message_order.append(message_id)

        while len(self.processed_message_order) > MAX_CACHED_RESPONSES:
            expired_message_id = self.processed_message_order.pop(0)
            self.processed_responses.pop(expired_message_id, None)

    def start_pending_tool(
        self,
        tool_name: str,
        tool_request_id: str,
        state: str,
    ) -> None:
        self.pending_tool_name = tool_name
        self.pending_tool_request_id = tool_request_id
        self.pending_tool_state = state

    def clear_pending_tool(self) -> None:
        self.pending_tool_name = None
        self.pending_tool_request_id = None
        self.pending_tool_state = None


class SessionStore:
    """Simple in-memory session store.

    The point of this class is not durability. It is to isolate state
    management from transport and generation logic so later persistence
    layers can replace it.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def get_or_create(self, session_id: str) -> SessionState:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionState(session_id=session_id)
        return self._sessions[session_id]

