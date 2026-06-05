"""LLM adapter boundary for the MVP server."""

from __future__ import annotations

from dataclasses import dataclass

from project_sena_inference.session_store import SessionState


@dataclass
class LLMResponse:
    text: str
    persona_state: str = "neutral"
    should_speak: bool = True


class StubLLMAdapter:
    """Deterministic stand-in for a future Gemma-backed adapter.

    This lets us exercise the full control loop before model integration.
    """

    def generate_reply(self, session: SessionState, user_text: str) -> LLMResponse:
        screen_hint = (
            f" \uc9c0\uae08 \ubcf4\uace0 \uc788\ub294 \ud654\uba74 \ub9e5\ub77d\uc740 {session.latest_screen_context}."
            if session.latest_screen_context
            else ""
        )
        text = (
            f"\uc785\ub825\ud55c \ub0b4\uc6a9\uc740 '{user_text}'\ub85c \uc774\ud574\ud588\uc5b4.{screen_hint} "
            "\uc9c0\uae08\uc740 Project-SENA \ucd94\ub860 \uc11c\ubc84 \uace8\uaca9\uc744 "
            "\uc810\uac80\ud558\ub294 \ub2e8\uacc4\ub77c \uaddc\uce59 \uae30\ubc18 \uc751\ub2f5\uc73c\ub85c "
            "\ub3cc\uc544\uac00\uace0 \uc788\uc5b4."
        )
        return LLMResponse(text=text)
