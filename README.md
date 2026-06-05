# Hiyori Desktop Agent

Windows desktop Live2D character assistant inspired by ProjectLucia.

This repository is intended to become a split desktop-agent and inference-server system:

- Desktop client: Live2D UI, chat, microphone input, speaker output, screen capture, and user approval.
- Desktop agent: local Windows automation tools for screen/window state and safe PC control.
- Inference server: Korean LLM, TTS, vision analysis, emotion analysis, RAG, and memory.
- Shared protocol: typed messages between the desktop side and the inference server.

## Roadmap

1. Run a single-PC MVP on the RTX 3060 Ti desktop.
2. Move inference workloads to the gaming laptop.
3. Replace the laptop server with a dedicated high-end inference PC later.

## Reference Projects

ProjectLucia repositories are kept under `references/` for study and selective reuse. They are intentionally ignored by this repository.

