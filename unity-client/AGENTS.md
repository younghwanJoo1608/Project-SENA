# Unity Client Guide

The Unity client is the user-facing body of Project-SENA.

## Responsibilities

- Render the Live2D character.
- Provide text chat UI.
- Capture microphone input and play assistant audio.
- Show screen-capture controls.
- Show approval dialogs for tool requests.
- Display connection, listening, speaking, thinking, and tool-execution states.

## Boundaries

- Do not run LLM, TTS, RAG, or vision inference here.
- Do not directly execute PC automation here unless it is delegated to `desktop-agent/`.
- Do not store secrets in Unity assets or scene files.
- Keep network communication aligned with `shared-protocol/`.

## UX Rules

- The assistant should feel like a desktop companion, not a web dashboard.
- Approval prompts must clearly say what action will happen and why.
- Risky tool requests need explicit allow/deny UI.
- Keep Korean user-facing text natural and concise.

