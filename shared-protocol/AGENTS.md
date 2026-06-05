# Shared Protocol Guide

`shared-protocol/` defines contracts between the Unity client, desktop agent, and inference server.

## Responsibilities

- Message schemas.
- Tool request/result schemas.
- Approval request/result schemas.
- Error codes and state events.
- Versioning notes for protocol changes.

## Rules

- Prefer explicit typed fields over loose maps.
- Include protocol version fields when useful.
- Keep names in English.
- Avoid embedding binary blobs directly in JSON unless there is a clear reason.
- Document every tool's risk level and approval behavior.

## Initial Message Families

- `user_text`
- `screen_frame`
- `assistant_text`
- `tts_audio`
- `tool_request`
- `tool_result`
- `approval_request`
- `approval_result`
- `state_event`
- `error`

