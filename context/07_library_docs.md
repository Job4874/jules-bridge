# Jules Bridge — Library Docs

> Context file 7 of 7. How each dependency is used *in this specific project*.
> Not generic docs — project-specific patterns, configurations, and rules.

## Flask (flask + flask-cors)

### Configuration

- App created in `bridge.py` line 66: `app = Flask(__name__)`

- CORS enabled globally: `CORS(app)` — no origin restrictions (runs locally)

- No authentication middleware — local-only, firewall-protected

- Runs on port **5000** by default

### Error Handling Chain

All route handlers MUST use the `@route_errors` decorator (bridge.py lines 92–134). The decorator maps exceptions to HTTP status codes in this priority:

1. `BridgeHTTPError` → custom status code

2. `subprocess.TimeoutExpired` → 504

3. `ShellNotAvailableError` / `UnsupportedShellError` → 400

4. `IsADirectoryError` / `NotADirectoryError` → 400

5. `FileNotFoundError` → 404

6. `PermissionError` → 403

7. `re.error` → 400

8. `ValueError` → 400

9. `OSError` (EACCES/EPERM) → 403, (ENOENT) → 404, (other) → 500

10. All other exceptions → 500

### Request Parsing Pattern

Always use the bridge.py field helpers, never parse `request.json` directly:

```python
data = json_payload()                          # validates Content-Type + JSON
path = path_field(data)                        # string + control-char safe
name = string_field(data, "name")              # required string
opt  = string_field(data, "key", default="")   # optional with default
n    = int_field(data, "lines", default=50)    # optional int with default
content = content_field(data)                  # accepts "content" or "data" key

```

### Response Pattern

Always return `jsonify(dict(result))` where `result` is a typed dict/dataclass from a module. Never construct response dicts inline in route handlers.

---

## google-generativeai (Gemini API)

Used exclusively by `modules/reasoning_module.py` for H-module and L-module LLM calls.

### Configuration

- **Env var required**: `GEMINI_API_KEY` must be set before the bridge starts

- **Package**: `google-generativeai` — install with `pip install google-generativeai`

- **Lazy import**: imported inside `_gemini_chat()` — never at module level. This keeps tests working without the package installed.

### Model Alias System

Never pass raw model strings to reasoning routes. Use aliases:

```python
# In route body:
{"problem": "...", "model": "fast"}    # → gemini-2.0-flash  (cheap, low latency)
{"problem": "...", "model": "smart"}   # → gemini-2.5-pro    (high quality)
{"problem": "...", "model": "stub"}    # → deterministic stub (unit tests, offline)

```

Alias mapping lives in `_MODEL_ALIASES` at the top of `reasoning_module.py`. Change the right-hand value there to update the model, not the call sites.

### Fallback Behavior

If Gemini call fails for any reason (missing key, network error, quota, non-JSON response), the module **silently falls back to stub output** and logs a `WARNING` to `jules_bridge.reasoning`. It does NOT raise. This is intentional — the bridge must never crash due to LLM failure.

### Usage Pattern

```python
# Direct module call (for testing):
from modules.reasoning_module import _h_gemini_call
result = _h_gemini_call("My problem", context="", model_name="gemini-2.0-flash")

# Via bridge route:
POST /reasoning/solve
{"problem": "My problem", "model": "fast"}

# Plan-only (H module, no execution):
POST /reasoning/plan
{"problem": "My problem", "model": "smart"}

```

### Rules

- Never call `genai.configure()` outside of `_gemini_chat()` — it's a global side effect

- Always use `response_mime_type="application/json"` and `temperature=0.2` for structured outputs

- Never pass `model="fast"` or `model="smart"` in unit tests — use `model="stub"` to avoid network calls

---

## pyautogui

### Configuration

- Lazy-imported via `_pyautogui()` helper in `modules/ui_automation.py` — never imported at module level

- This allows test files to mock pyautogui without it being installed

- **No failsafe configured** — runs locally, operator is physically present

### Screenshot Pattern

```python
modules.screenshot(save=False)           # returns ScreenshotResult with image_base64
modules.screenshot(save=True)            # also saves PNG to jules_inbox/screenshots/

```

- Screenshots are base64-encoded PNG, returned in `image_base64` key

- Saved screenshots go to `jules_inbox/screenshots/` with UTC timestamp filenames

### Click/Type Pattern

```python
modules.click(x=100, y=200)              # left-click at absolute coordinates
modules.type_text("hello")               # types text at current cursor position

```

- Coordinates are absolute screen pixels — no relative or element-based targeting

- No coordinate validation against screen bounds (caller's responsibility)

---

## subprocess (via shell_executor)

### Configuration

- Wrapped by `modules/shell_executor.py` — never use `subprocess` directly in route handlers

- Three supported shells: `powershell`, `cmd`, `bash`

- Default timeout: **30 seconds** — pass `timeout=120` for long builds

### PowerShell Invocation

Always use `["powershell", "-Command", cmd]`, never `["pwsh", ...]`. The executor handles this internally:

```python
modules.execute(command="Get-Process", shell="powershell", timeout=30)

```

### Bash on Windows

The executor searches these paths in order:

1. `C:\Program Files\Git\bin\bash.exe`

2. `C:\Program Files (x86)\Git\bin\bash.exe`

3. `C:\Program Files\Git\usr\bin\bash.exe`

### Output Encoding

All subprocess output is coerced to UTF-8 via `_coerce_text()`: bytes → `decode("utf-8", errors="replace")`.
`modules.jules_orchestrator._run_cli_command()` also sets `encoding="utf-8"` and
`errors="replace"` on text pipes so `jules new` can receive packet prompts with
emoji/non-ASCII text on Windows.

### Return Contract

```python
ShellResult(exit_code=0, stdout="...", stderr="...", shell="powershell")

```

- `exit_code=0` does NOT guarantee success on Windows — always check stdout/stderr content too

---

## pyngrok

### Configuration

- Used ONLY in `start.py` — never in bridge.py or modules

- Fixed ngrok domain: `parade-marrow-pulp.ngrok-free.dev`

- Connects to local port 5000: `ngrok.connect(5000, domain=NGROK_DOMAIN)`

- Auth token: stored in ngrok's own config, not in `.env`

### Startup Sequence (start.py)

1. Launch `bridge.py` as subprocess

2. Poll `http://127.0.0.1:5000/ping` for up to 10 seconds (20 × 0.5s)

3. Open ngrok tunnel to port 5000 with fixed domain

4. If ngrok fails but local bridge is UP → warn but continue (local-only mode)

5. Keep-alive loop: check subprocess health every 2 seconds

### Rules

- Never import pyngrok in bridge.py or any module

- If ngrok tunnel fails, the bridge still works on localhost — this is intentional

- The ngrok URL is logged to console and bridge.log — agents can read it from there

---

## pytest

### Configuration

- Test files in `tests/` — one file per module: `test_{module_name}.py`

- Run with: `python -m pytest tests/ -v`

- Tests run against the module boundary (public interface) — no internal mocking

### Evidence Recording

After every test run, the output MUST be recorded for cryptographic proof:

```

POST /retrospective/record_evidence
Body: { "test_output": "<raw pytest stdout>" }

```

This stores a SHA-256 hash in `memory/test_evidence.json`.

### Key Test Files

| File | Module | Test Count |
|------|--------|------------|
| `test_fs_service.py` | fs_service | — |
| `test_shell_executor.py` | shell_executor | — |
| `test_inbox_service.py` | inbox_service | — |
| `test_reasoning_module.py` | reasoning_module | 34 |
| `test_retrospective_module.py` | retrospective_module | — |

---

## smtplib (via notify_email)

### Configuration

- Used ONLY in `notify_email.py` — never in bridge.py or modules

- Gmail SMTP: `smtp.gmail.com:587` with STARTTLS

- Credentials from `.env` file: `GMAIL_USER` + `GMAIL_APP_PASSWORD` (16-char Google app password)

- Default recipient: `abdul487417@icloud.com` (overridable via `EMAIL_TO` env var)

### Usage Pattern

```python
import notify_email as email_service
email_service.send_email(subject="Alert", body="Something happened")

```

### Rules

- Never hardcode email credentials — always from `.env` via `os.environ.get()`

- The `.env` loader is manual (`load_env()`) — not using python-dotenv

- Timeout: 30 seconds on SMTP connection

---

## logging (stdlib)

### Configuration

- `RotatingFileHandler` writing to `bridge.log` at project root

- Max size: 10 MB, 3 backup files, UTF-8 encoding

- Format: `2025-06-25T14:30:00+0000 INFO jules_bridge: message`

- Both file and stdout handlers are tagged with `_jules_bridge_handler = True` to prevent duplicate registration

### Rules

- Always use `LOGGER = logging.getLogger("jules_bridge")` — never use `print()` for operational output

- The retrospective module reads `bridge.log` for pattern analysis — if you break the log format, you break retrospective analysis

- `start.py` has its own logger: `jules_bridge_start` — separate from the main bridge logger

---

## MCP Servers

If an MCP server is configured for any library used in this project:

1. Read its schema/instructions file first

2. Use MCP tools for discovery and exploration (schema introspection, available endpoints)

3. Fall back to the patterns in this file for project-specific conventions

Currently no MCP servers are configured for the core dependencies (Flask, pyautogui, pyngrok). If one becomes available, add its usage patterns to this section.
