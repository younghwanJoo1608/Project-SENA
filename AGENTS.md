# Project-SENA Agent Guide

This repository builds Project-SENA: a Korean Windows desktop Live2D character assistant with a split desktop-agent and inference-server architecture.

## Project Intent

Project-SENA should become a local-first assistant that can:

- talk with the user in Korean through text and voice;
- render and control a Live2D character with a stable persona;
- understand the user's desktop through screenshots and window context;
- request safe PC-control actions through a desktop-local tool layer;
- move heavy inference from the desktop PC to a separate server without changing the user-facing client.

## Architecture Boundaries

- `unity-client/`: Live2D presentation, chat UI, microphone capture, audio playback, screen-capture UX, and user approval dialogs.
- `desktop-agent/`: Windows-local inspection and automation. This is the only layer allowed to execute PC-control tools.
- `inference-server/`: LLM, TTS generation, vision analysis, emotion analysis, RAG/search, memory, and conversation orchestration.
- `shared-protocol/`: message schemas and contracts shared between the desktop side and inference server.
- `docs/`: design notes, architecture decisions, setup docs, and operating guides.
- `references/`: external reference repositories. Treat as read-only study material unless the user explicitly asks to modify or sync them.

## Development Rules

- Keep desktop-side capabilities and inference-side capabilities separate even during the single-PC MVP.
- Prefer typed protocols over ad hoc JSON strings.
- Do not let LLM output directly execute shell, mouse, keyboard, or file operations.
- Any potentially destructive or privacy-sensitive action must become an explicit tool request and require desktop-side policy checks.
- Design first for Korean interaction quality, but keep code identifiers and protocol fields in English.
- Keep code and docs ASCII unless a file specifically needs Korean user-facing text.
- Do not vendor large models, generated audio, captures, build artifacts, Unity caches, or local credentials.
- Keep ProjectLucia code in `references/` as reference material; copy only small, well-understood pieces when justified.

## Safety Model

The inference server may propose actions. The desktop agent decides whether they can run.

Tool execution flow:

1. User intent is interpreted by the inference server.
2. Server emits a structured `tool_request`.
3. Desktop agent validates risk and required permission.
4. Unity client asks the user for approval when needed.
5. Desktop agent executes the approved action.
6. Desktop agent returns a structured `tool_result`.

Default to denial for unknown, destructive, credential-related, payment-related, or irreversible operations.

## Git Workflow

- `master`: stable base.
- `develop`: integration branch.
- `codex/*`: Codex working branches.

Make changes on the active `codex/*` branch unless the user asks otherwise.

