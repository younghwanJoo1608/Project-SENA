# Desktop Agent Guide

The desktop agent is the only Project-SENA component allowed to inspect and operate the user's Windows desktop.

## Responsibilities

- Capture screenshots and selected screen regions.
- Inspect active window/app state.
- Execute approved mouse, keyboard, app-launch, clipboard, and file-opening actions.
- Validate tool requests from the inference server.
- Return tool results with enough context for the assistant to continue.

## Safety Rules

- Unknown tools are denied by default.
- Destructive file operations require explicit user approval.
- Credential, payment, account, system-security, and irreversible actions are blocked unless a future policy explicitly allows them.
- Never execute raw shell commands directly from LLM text.
- Prefer narrowly scoped tool functions over generic command execution.

## Implementation Rules

- Keep tool schemas stable and documented in `shared-protocol/`.
- Log tool decisions without leaking private content where possible.
- Separate observation tools from mutation tools.

