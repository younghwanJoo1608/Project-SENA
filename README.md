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

## Reference Projects

ProjectLucia repositories are kept under `references/` for study and selective reuse. They are intentionally ignored by this repository.

Current references:

- `references/ProjectLucia_Client_HiyoriEdition`
- `references/ProjectLucia_Server_HiyoriEdition`
- `references/ProjectLucia_Finetuning_Server`

## License

Project-SENA source code is licensed under the MIT License. Third-party models, Live2D assets, voice assets, generated media, and other external resources are downloaded or supplied by the user and remain under their own licenses. See `THIRD_PARTY_NOTICES.md`.
