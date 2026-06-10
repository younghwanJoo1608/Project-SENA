# Project-SENA

**Screen-aware Emotional Native Assistant**

[한국어](README.KR.md)

Project-SENA is a Korean Windows desktop Live2D character assistant. It is designed to see the user's desktop, talk through text and voice, respond in character, and safely operate the PC when the user approves.

The project is inspired by ProjectLucia, but the long-term goal is a cleaner split between the desktop environment and the inference backend.

## Goals

- Korean text and voice conversation
- Live2D character rendering with a stable persona
- Screen-aware dialogue based on desktop screenshots and window context
- Safe PC control through explicit tool requests and user approval
- Local-first inference, with the option to move heavy workloads to a separate server PC

## Architecture

Project-SENA is organized around four main parts:

- `unity-client`: Live2D UI, chat, microphone input, speaker output, and approval dialogs.
- `desktop-agent`: Windows-local screen capture, active-window inspection, and safe PC automation.
- `inference-server`: Korean LLM, TTS, vision analysis, emotion analysis, RAG, and memory.
- `shared-protocol`: typed messages between the desktop side and the inference server.

The desktop PC acts as the assistant's eyes, ears, voice, and hands. The inference server acts as the assistant's brain.

## Roadmap

1. Run a single-PC MVP on the RTX 3060 Ti desktop.
2. Move inference workloads to the gaming laptop.
3. Replace the laptop server with a dedicated high-end inference PC later.

## Running Locally

After rebooting the PC, open two PowerShell 7 windows and run the desktop-agent and inference-server separately.

### 1. Start desktop-agent

First PowerShell 7 window:

```powershell
cd "G:\Repos\LLM Vtuber Agent\desktop-agent"
.\.venv\Scripts\python -m uvicorn project_sena_desktop_agent.api:app --reload --port 8010
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8010/health
```

### 2. Start inference-server

Second PowerShell 7 window:

```powershell
cd "G:\Repos\LLM Vtuber Agent\inference-server"
$env:PROJECT_SENA_DESKTOP_AGENT_URL = "http://127.0.0.1:8010"
.\.venv\Scripts\python -m uvicorn project_sena_inference.main:app --reload --port 8000
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

### 3. Start Unity client

After both servers are running, open `Project-SENA-UnityClient` in Unity and press Play. For a standalone build, start both servers first and then run the built app.

### First setup or dependency updates

Run these commands in each Python service folder only when `.venv` is missing or `pyproject.toml` dependencies changed:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .[dev]
```

## Reference Projects

ProjectLucia repositories are kept under `references/` for study and selective reuse. They are intentionally ignored by this repository.

Current references:

- `references/ProjectLucia_Client_HiyoriEdition`
- `references/ProjectLucia_Server_HiyoriEdition`
- `references/ProjectLucia_Finetuning_Server`

## License

Project-SENA source code is licensed under the MIT License. Third-party models, Live2D assets, voice assets, generated media, and other external resources are downloaded or supplied by the user and remain under their own licenses. See `THIRD_PARTY_NOTICES.md`.
