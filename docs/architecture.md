# Architecture

## Target Split

```text
Desktop PC
  - Unity Live2D client
  - microphone capture
  - speaker playback
  - screen capture
  - Windows control tools
  - approval UI

Inference Server
  - LLM
  - TTS generation
  - vision analysis
  - emotion analysis
  - RAG/search
  - memory and logs
```

## Safety Rule

The inference server may propose tool calls, but only the desktop agent can execute them.
Risky actions must require explicit user approval on the desktop.

