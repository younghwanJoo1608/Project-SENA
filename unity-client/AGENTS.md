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
- Do not trust PowerShell or shell output as proof that Korean text in Unity assets is correct. If console output is mojibake, inspect the asset directly or verify inside Unity before editing adjacent strings.
- Do not make large scene-wide layout changes from a text patch unless the requested layout has been restated in exact terms and the affected RectTransforms are individually identified.
- For `.unity` scene edits, prefer precise object-level patches and avoid batch search/replace over repeated RectTransform patterns.
- When editing input UX, separate concerns:
  1. IME/submit behavior
  2. dynamic sizing behavior
  3. visual layout
  Only change one of these at a time unless the user explicitly asks for a combined redesign.
- Before changing `ChatPanel`, `InputField`, or `SendButton` layout, restate which element should keep its width and which element should expand.
- Runtime text such as placeholders, button labels, and status strings should be set from known-good source text, not copied from garbled terminal output.
- For Unity UI and input bugs, prefer the platform-standard fix path first. If the issue points to a known component limitation, move to the standard replacement or supported workflow instead of layering brittle event-order or timing hacks.
- When replacing a Unity object or component with a new one, remove or disable the superseded object in the same task. Do not leave legacy and replacement inputs, text objects, or controllers active together.
- Before choosing a shortcut implementation for UI or input handling, check whether the feature is likely to expand later. Favor the structure that can absorb future behavior, localization, and asset changes without forcing a second rewrite.

