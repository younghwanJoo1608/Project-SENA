"""In-memory session storage for the MVP server."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SessionState:
    session_id: str
    turn_count: int = 0
    recent_user_texts: list[str] = field(default_factory=list)
    recent_assistant_texts: list[str] = field(default_factory=list)
    latest_screen_context: str | None = None
    pending_tool_name: str | None = None


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

