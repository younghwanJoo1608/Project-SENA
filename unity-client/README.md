# Unity Client

Unity Live2D client for:

- character rendering
- chat UI
- microphone input
- audio playback
- screen-capture controls
- user approval dialogs

## Phase 1 Focus

Phase 1 is a UI and protocol integration step, not a Live2D step yet.

- connect to `inference-server` over HTTP;
- display assistant chat and state messages;
- show approval dialogs for `approval_request`;
- send `approval_result` back to the inference server;
- display `tool_result` follow-up messages.

See [phase-1-setup.kr.md](phase-1-setup.kr.md) for the first Unity scene wiring plan.
