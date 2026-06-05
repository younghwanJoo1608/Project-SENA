# Inference Server Guide

The inference server is the assistant's reasoning and generation backend.

## Responsibilities

- Korean character LLM responses.
- Character persona and dialogue policy.
- TTS generation.
- Vision analysis for screenshots and selected regions.
- Emotion analysis.
- RAG/search and memory.
- Tool planning through structured requests.

## Boundaries

- Do not directly operate the desktop.
- Do not execute shell commands for user PC control.
- Do not assume a tool request succeeded until a `tool_result` returns.
- Keep heavy inference replaceable so the server can move from desktop to laptop to a dedicated inference PC.

## Model Strategy

- Initial MVP should support small local models first.
- Treat Gemma-class local models as the default path.
- Keep room for fallback providers later, but do not make cloud APIs required.

## Persona Rules

- Persona configuration should be data-driven.
- Keep the assistant Korean-first.
- Separate hidden planning/tool decisions from user-facing character dialogue.

