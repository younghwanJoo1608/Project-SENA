"""FastAPI entrypoint for the Project-SENA inference server MVP."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from project_sena_inference.adapters.desktop_agent import HttpDesktopAgentClient
from project_sena_inference.adapters.llm import StubLLMAdapter
from project_sena_inference.adapters.tts import StubTTSAdapter
from project_sena_inference.orchestrator import Orchestrator
from project_sena_inference.protocol import InboundMessage, OutboundBatch
from project_sena_inference.session_store import SessionStore


def _is_truthy_env(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    session_store = SessionStore()
    llm_adapter = StubLLMAdapter()
    tts_adapter = StubTTSAdapter()
    desktop_agent_url = os.getenv("PROJECT_SENA_DESKTOP_AGENT_URL")
    desktop_agent_client = (
        HttpDesktopAgentClient(desktop_agent_url) if desktop_agent_url else None
    )
    app.state.orchestrator = Orchestrator(
        session_store,
        llm_adapter,
        tts_adapter,
        desktop_agent_client=desktop_agent_client,
        failure_injection_enabled=_is_truthy_env(
            "PROJECT_SENA_ENABLE_FAILURE_INJECTION"
        ),
    )
    yield


app = FastAPI(
    title="Project-SENA Inference Server",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "project-sena-inference", "protocol_version": "0.1"}


@app.post("/v1/messages", response_model=OutboundBatch)
async def post_message(message: InboundMessage) -> OutboundBatch:
    messages = app.state.orchestrator.handle(message)
    return OutboundBatch(messages=messages)
