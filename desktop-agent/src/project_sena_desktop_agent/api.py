"""FastAPI transport for the Project-SENA desktop agent."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .protocol import InboundMessage, PROTOCOL_VERSION, OutboundMessage
from .service import DesktopAgentService


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.desktop_agent_service = DesktopAgentService()
    yield


app = FastAPI(
    title="Project-SENA Desktop Agent",
    version=PROTOCOL_VERSION,
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "project-sena-desktop-agent",
        "protocol_version": PROTOCOL_VERSION,
    }


@app.post("/v1/messages", response_model=OutboundMessage)
async def post_message(message: InboundMessage) -> OutboundMessage:
    return app.state.desktop_agent_service.handle(message)
