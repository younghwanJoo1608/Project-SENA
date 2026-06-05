"""CLI entrypoint for early desktop-agent integration tests."""

from __future__ import annotations

import json
import sys

from pydantic import TypeAdapter

from .protocol import InboundMessage
from .service import DesktopAgentService


def main() -> int:
    payload = json.load(sys.stdin)
    message = TypeAdapter(InboundMessage).validate_python(payload)
    service = DesktopAgentService()
    response = service.handle(message)
    print(json.dumps(response.model_dump(mode="json"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
