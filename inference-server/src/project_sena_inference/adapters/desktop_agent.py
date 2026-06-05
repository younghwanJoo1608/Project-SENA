"""HTTP client adapter for the Project-SENA desktop agent."""

from __future__ import annotations

import json
from typing import Annotated, Union
from urllib import error, request

from pydantic import Field, TypeAdapter

from project_sena_inference.protocol import (
    ApprovalRequestMessage,
    ApprovalResultMessage,
    ErrorMessage,
    ToolRequestMessage,
    ToolResultMessage,
)

DesktopAgentResponse = Annotated[
    Union[ApprovalRequestMessage, ToolResultMessage, ErrorMessage],
    Field(discriminator="type"),
]


class DesktopAgentClientError(RuntimeError):
    """Raised when the desktop-agent transport fails."""


class HttpDesktopAgentClient:
    """Posts structured tool messages to the desktop-agent HTTP API."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._response_adapter = TypeAdapter(DesktopAgentResponse)

    @property
    def base_url(self) -> str:
        return self._base_url

    def dispatch(
        self,
        message: ToolRequestMessage | ApprovalResultMessage,
    ) -> ApprovalRequestMessage | ToolResultMessage | ErrorMessage:
        url = f"{self._base_url}/v1/messages"
        payload = json.dumps(message.model_dump(mode="json")).encode("utf-8")
        http_request = request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=10) as response:
                body = response.read().decode("utf-8")
        except error.URLError as exc:
            raise DesktopAgentClientError(
                f"Failed to reach desktop-agent at {url}: {exc}"
            ) from exc

        try:
            decoded = json.loads(body)
            return self._response_adapter.validate_python(decoded)
        except (json.JSONDecodeError, ValueError) as exc:
            raise DesktopAgentClientError(
                "Desktop-agent returned an invalid response payload."
            ) from exc
