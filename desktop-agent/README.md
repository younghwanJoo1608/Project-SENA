# Desktop Agent

Local Windows process for:

- active window inspection
- screenshots and screen-region capture
- mouse and keyboard automation
- app launching
- tool-risk validation
- execution result reporting

## Phase 1 Scope

The first desktop-agent slice closes the local control loop for:

- `tool_request -> approval_request`
- `tool_request -> tool_result`
- `approval_result -> tool_result`

The initial real tool implementations are:

- `open_app`
- `get_active_window`

`capture_screen` and `type_text` are wired into the executor interface, but their runtime support remains dependency-driven and should be treated as early integration hooks for now.

## Local Test Loop

Install the package in editable mode:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .[dev]
```

Run tests:

```powershell
.\.venv\Scripts\python -m pytest
```

Pipe a JSON `tool_request` into the CLI:

```powershell
Get-Content request.json | .\.venv\Scripts\python -m project_sena_desktop_agent.main
```

Run a stateful manual flow for `open_app(notepad)`:

```powershell
.\.venv\Scripts\python -m project_sena_desktop_agent.manual_flow
```

Run the local HTTP server:

```powershell
.\.venv\Scripts\python -m uvicorn project_sena_desktop_agent.api:app --reload --port 8010
```

Check health:

```powershell
Invoke-RestMethod http://127.0.0.1:8010/health
```

Send a `tool_request` over HTTP:

```powershell
$body = @{
  protocol_version = "0.1"
  type = "tool_request"
  message_id = "msg-http-1"
  session_id = "session-http-1"
  timestamp = "2026-06-05T12:00:00Z"
  source = "inference-server"
  payload = @{
    tool_name = "open_app"
    arguments = @{ app_name = "notepad" }
    reason = "The user asked to open a plain text editor."
    risk_level = "low"
    approval_policy = "user_confirmation"
  }
} | ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Uri http://127.0.0.1:8010/v1/messages `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```
