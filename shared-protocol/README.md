# Shared Protocol

`shared-protocol/` defines the message contract between:

- `unity-client`
- `desktop-agent`
- `inference-server`

The first implementation target is a transport-agnostic MVP protocol. The same message shapes should work over WebSocket, HTTP, local IPC, or future distributed deployment.

## Design Principles

- All messages use the same envelope fields for routing, tracing, and debugging.
- Payloads are typed by `type`, not by ad hoc field inspection.
- Desktop control is always request/approval/result based.
- Binary-heavy artifacts such as screenshots and audio should be referenced by metadata or encoded explicitly, never implied.
- The protocol should remain stable when inference moves from the desktop PC to a separate server.

## Core Files

- `protocol-v0.1.md`: human-readable MVP contract
- `schemas/`: JSON Schema definitions for each message family
- `examples/`: small reference payloads for early integration tests

## Initial Message Families

- `user_text`
- `speech_input`
- `screen_frame`
- `assistant_text`
- `assistant_state`
- `tts_audio`
- `tool_request`
- `tool_result`
- `approval_request`
- `approval_result`
- `error`
