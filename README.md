# Jules Bridge API

Jules Bridge is a Flask service for host orchestration over one local or ngrok URL. It exposes routes for file inspection, shell execution, operator inbox messages, Oracle/Quantower status checks, and desktop UI automation.

This bridge is intentionally open-access at the HTTP layer. Possession of the bridge URL is possession of host access, so keep the local port and ngrok URL private.

## Core Behavior

- `POST` routes parse JSON consistently with `request.get_json(silent=True)` and route-level validators.
- Empty `POST` bodies are treated as `{}` so callers receive field-specific `400` errors.
- Malformed JSON or a non-JSON body returns:

```json
{"error": "Malformed JSON or missing Content-Type header."}
```

- Operational errors are mapped to predictable JSON responses.
- Bridge and startup events are written to stdout and `bridge.log` with a 10 MB rotating file handler.

## Security Posture

The bridge does not implement HTTP authentication or a command allowlist. It can read and write host files, execute commands, and drive the UI through routes exposed by the configured URL.

Operator rules:

- Do not publish the ngrok URL.
- Do not send secrets through logs, inbox messages, or screenshots.
- Do not use `/shell`, `/fs/write`, or `/ui/*` for destructive system changes unless the operator explicitly requests that exact action.
- Prefer structured routes like `/oracle/status`, `/fs/read`, `/fs/tail`, and `/fs/grep` before broad shell commands.

## Error Mapping

| Condition | HTTP code | JSON shape |
|-----------|-----------|------------|
| Missing parameters, invalid types, schema mismatch, negative coordinates | `400` | `{"error": "Invalid input", "details": "..."}` |
| Malformed JSON or missing JSON `Content-Type` | `400` | `{"error": "Malformed JSON or missing Content-Type header."}` |
| File or directory missing | `404` | `{"error": "Resource not found", "path": "..."}` |
| Windows access denied | `403` | `{"error": "Access denied", "reason": "Insufficient permissions"}` |
| Shell execution timeout | `504` | `{"error": "Execution timed out after X seconds"}` |
| Unexpected platform/runtime failure | `500` | `{"error": "Internal operational failure"}` |

## Endpoints

### `GET /ping`

Health check.

```json
{"status": "Jules Bridge Online"}
```

### `GET /tentacles`

Lists available routes and their intended reach.

### `GET /session/log?limit=50`

Returns recent request metadata from the in-memory request log.

```json
{
  "entries": [
    {
      "time_utc": "2026-06-25T16:41:24.401988+00:00",
      "method": "POST",
      "path": "/shell",
      "status": 200,
      "remote": "127.0.0.1",
      "ms": 523.89
    }
  ]
}
```

### `POST /fs/read`

Reads a text file. Optional `offset` and `limit` apply to line reads.

```json
{"path": "C:\\Windows\\win.ini", "offset": 0, "limit": 5}
```

Response includes both `content` and `data` for compatibility.

```json
{"path": "C:\\Windows\\win.ini", "offset": 0, "content": "...", "data": "..."}
```

### `POST /fs/list`

Lists a directory. Defaults to `jules_inbox` if `path` is omitted.

```json
{"path": "C:\\Users\\abdul\\.jules\\jules_inbox"}
```

### `POST /fs/tail`

Returns the last `lines` lines from a text file. Default: `50`.

```json
{"path": "C:\\path\\to\\log.txt", "lines": 20}
```

### `POST /fs/grep`

Searches a text file with a case-insensitive regex. Default `max_matches`: `50`.

```json
{"path": "C:\\path\\to\\log.txt", "pattern": "ERROR|CRITICAL", "max_matches": 20}
```

### `POST /fs/write`

Writes text to a file. Either `content` or `data` must be present.

```json
{"path": "C:\\tmp\\bridge.txt", "content": "hello"}
```

### `POST /shell`

Executes a command through a selected native shell.

```json
{
  "command": "Get-Process",
  "shell": "powershell",
  "timeout": 30
}
```

Options:

- `command` is required.
- `shell` defaults to `powershell`.
- `timeout` defaults to `30` seconds.
- `stdin` is optional.
- `cwd` defaults to the bridge process working directory.

Supported shell selectors:

- `powershell`: runs `powershell.exe -NoProfile -NonInteractive -Command`.
- `cmd`: runs `cmd.exe /d /s /c`.
- `bash`: runs Git Bash through `JULES_BASH_PATH`, known Git install paths, or `PATH`.

`wsl` is intentionally rejected because this host exposes `wsl.exe` without an installed distribution.

Response includes both `code` and `exit_code` for compatibility.

```json
{"code": 0, "exit_code": 0, "shell": "powershell", "stdout": "...", "stderr": ""}
```

### `GET /ui/screenshot?save=true`

Captures the desktop and returns a base64 PNG. If `save=true`, the response also includes `saved_path`.

### `POST /ui/click`

Moves the real mouse and clicks. Coordinates must be non-negative integers inside the current display bounds.

```json
{"x": 100, "y": 200, "button": "left"}
```

### `POST /ui/type`

Types real keyboard text.

```json
{"text": "hello"}
```

### `POST /notify/email`

Sends an operator email using `.env` settings. Body is required; `to` is optional and must be an email address.

```json
{"subject": "Jules Bridge update", "body": "Bridge is online."}
```

### `POST /inbox/read`

Reads a file from `jules_inbox`. Defaults to `OPERATOR_RESPONSE.md`.

```json
{"file": "OPERATOR_RESPONSE.md"}
```

### `POST /inbox/write`

Writes a file into `jules_inbox`. Defaults to `JULES_RESPONSE.md`.

```json
{"file": "JULES_RESPONSE.md", "content": "message"}
```

### `GET /oracle/status`

Returns structured Oracle/Quantower readiness, blockers, telemetry, and gate status.

### `POST /oracle/build-deploy`

Runs the Oracle build/deploy/verify helper sequence.

### `GET /codex/handover`

Indexes the configured Codex handover directory on the host.
