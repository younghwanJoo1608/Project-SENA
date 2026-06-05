"""TTS adapter boundary for the MVP server."""

from __future__ import annotations


class StubTTSAdapter:
    """Placeholder for future synthesis integration.

    The first server slice only proves message flow, so no audio is produced yet.
    """

    def is_enabled(self) -> bool:
        return False

