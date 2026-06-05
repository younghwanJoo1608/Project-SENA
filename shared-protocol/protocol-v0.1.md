# Protocol v0.1

`protocol-v0.1` is the first MVP contract for Project-SENA.

## Objective

The protocol must support a full desktop-assistant loop:

1. user input enters from text or speech;
2. inference produces visible dialogue and optional TTS;
3. screenshots can be attached as context;
4. tool calls are proposed by the inference server;
5. the desktop side approves and executes tools;
6. results return to the inference server.

## Message Model

Every message uses the same outer envelope.

Common fields:

- `protocol_version`: protocol version string such as `0.1`
- `type`: message family name
- `message_id`: unique per message
- `session_id`: stable per conversation session
- `timestamp`: ISO-8601 UTC timestamp
- `source`: `unity-client`, `desktop-agent`, `inference-server`, or `system`
- `payload`: typed payload object

## Why An Envelope

This separates transport concerns from semantic concerns.

- The transport only needs to route a message blob.
- Each module can log, replay, validate, and test messages consistently.
- Cross-process debugging becomes easier because every message has a traceable identity.

For someone with robotics middleware experience, this is similar to imposing one common header across topic, service, and action messages so tracing and bag-style replay stay simple.

## Message Families

### `user_text`

Purpose:
User-typed text from the client UI.

Key payload fields:

- `text`
- `language`
- `input_mode`

### `speech_input`

Purpose:
Speech-to-text result from the desktop side.

Key payload fields:

- `text`
- `language`
- `stt_engine`
- `confidence`
- `is_final`

### `screen_frame`

Purpose:
A screenshot or selected screen region sent as inference context.

Key payload fields:

- `image_format`
- `image_base64`
- `capture_mode`
- `display_index`
- `active_window`

### `assistant_text`

Purpose:
User-facing assistant response text.

Key payload fields:

- `text`
- `display_text`
- `persona_state`
- `should_speak`

### `assistant_state`

Purpose:
UI-visible assistant state transitions.

Key payload fields:

- `state`
- `detail`

### `tts_audio`

Purpose:
Synthesized speech payload metadata.

Key payload fields:

- `audio_format`
- `audio_base64`
- `sample_rate_hz`
- `text`

### `tool_request`

Purpose:
Inference-side proposal for a desktop tool invocation.

Key payload fields:

- `tool_name`
- `arguments`
- `reason`
- `risk_level`
- `approval_policy`

### `approval_request`

Purpose:
Desktop-side request to ask the user whether a tool should run.

Key payload fields:

- `tool_name`
- `reason`
- `risk_level`
- `arguments_preview`

### `approval_result`

Purpose:
User decision for a pending tool request.

Key payload fields:

- `approved`
- `decision_reason`

### `tool_result`

Purpose:
Execution result returned by the desktop side.

Key payload fields:

- `tool_name`
- `status`
- `result`
- `error_message`

### `error`

Purpose:
Structured failure event.

Key payload fields:

- `code`
- `message`
- `retryable`

## Safety Contract

The inference server is not allowed to directly execute desktop actions.

Required flow:

1. inference emits `tool_request`;
2. desktop policy evaluates it;
3. if required, UI emits `approval_request`;
4. user decision returns as `approval_result`;
5. desktop executes;
6. desktop emits `tool_result`.

This is effectively a command gate. In robotics terms, think of it as keeping planning and actuation in separate nodes with an explicit safety supervisor in between.

## Initial Tool Set

Allowed MVP tools:

- `capture_screen`
- `get_active_window`
- `open_app`
- `type_text`

Any tool outside the known set is invalid in `v0.1`.

## Versioning Rule

Additive changes are preferred.

- new optional payload fields: allowed in minor revisions;
- field removal or meaning changes: require a new protocol version;
- new tool names: allowed only when desktop policy support exists.

