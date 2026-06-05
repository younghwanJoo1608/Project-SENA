# Project-SENA Rules

- Build a Korean Windows Live2D desktop assistant.
- Keep the desktop environment and inference backend separable.
- The desktop agent is the only layer that can execute PC-control actions.
- The inference server can propose tool requests, not execute them.
- Unknown or dangerous tool requests are denied by default.
- ProjectLucia repositories under `references/` are reference material, not active source.
- Avoid committing models, generated media, secrets, Unity caches, or local machine data.

