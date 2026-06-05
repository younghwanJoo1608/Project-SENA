# Inference Server

`inference-server/` contains the first Project-SENA backend skeleton.

## Scope Of This Phase

The first implementation goal is not high-quality inference. It is a closed control loop:

- accept typed protocol messages;
- keep per-session state;
- generate typed response messages;
- leave clear adapter boundaries for LLM and TTS replacement later.

## Layout

- `pyproject.toml`: Python package metadata
- `src/project_sena_inference/`: application code
- `tests/`: basic orchestration tests

## Initial API

- `GET /health`
- `POST /v1/messages`

`POST /v1/messages` accepts one inbound protocol message and returns a list of outbound protocol messages.

## Run

```powershell
cd "G:\Repos\LLM Vtuber Agent\inference-server"
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .[dev]
.\.venv\Scripts\python -m uvicorn project_sena_inference.main:app --reload
```

## Desktop-Agent Integration

If `PROJECT_SENA_DESKTOP_AGENT_URL` is set, the inference server will forward
planned `tool_request` and incoming `approval_result` messages to the
desktop-agent automatically.

Example:

```powershell
$env:PROJECT_SENA_DESKTOP_AGENT_URL = "http://127.0.0.1:8010"
.\.venv\Scripts\python -m uvicorn project_sena_inference.main:app --reload
```

With the desktop-agent URL configured:

- a planned tool action returns `approval_request` or `tool_result` from the desktop-agent;
- the inference server includes that response in its outbound message batch;
- `approval_result` sent back to the inference server is forwarded to the desktop-agent automatically.

## Current Limitations

- LLM is a deterministic stub adapter.
- TTS is a stub adapter.
- Vision is represented as screen metadata handling only.
- Tool planning is rule-based for a very small tool set.
