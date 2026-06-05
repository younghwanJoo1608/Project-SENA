"""FastAPI entrypoint for the Project-SENA inference server MVP."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from project_sena_inference.adapters.llm import StubLLMAdapter
from project_sena_inference.adapters.tts import StubTTSAdapter
from project_sena_inference.orchestrator import Orchestrator
from project_sena_inference.protocol import InboundMessage, OutboundBatch
from project_sena_inference.session_store import SessionStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    session_store = SessionStore()
    llm_adapter = StubLLMAdapter()
    tts_adapter = StubTTSAdapter()
    app.state.orchestrator = Orchestrator(session_store, llm_adapter, tts_adapter)
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

