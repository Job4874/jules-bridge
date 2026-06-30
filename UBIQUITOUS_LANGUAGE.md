# Ubiquitous Language — Jules Bridge / Oracle V5

> This document defines the shared vocabulary for the Jules Bridge codebase and its surrounding domain.
> Use these exact terms in code, comments, planning sessions, and AI conversations.
> Generated from the codebase and domain knowledge. Keep this open during grilling sessions.

---

## Bounded Context: Bridge (Flask API Layer)

| Term | Definition | Module | Synonyms to Avoid |
| ------ | ----------- | -------- | ------------------- |
| **Bridge** | The Flask API server (`bridge.py`) that gives remote agents access to the host machine via HTTP | `bridge.py` | "server", "API", "backend" |
| **Route** | A single HTTP endpoint on the bridge (e.g., `POST /shell`) | `bridge.py` | "endpoint", "handler", "path" |
| **Tentacle** | A named route entry in the manifest — each tentacle extends Jules' reach to a specific host capability | `bridge.py` | "endpoint", "feature" |
| **Payload** | The validated JSON body extracted from an HTTP request | `bridge.py` | "body", "data", "request" |
| **BridgeHTTPError** | A structured exception that maps directly to a JSON HTTP error response | `bridge.py` | "error", "exception" |
| **Route error handler** | The `@route_errors` decorator that catches module exceptions and maps them to HTTP status codes | `bridge.py` | "error middleware" |
| **ngrok** | The tunneling service that exposes the bridge to external agents (Jules, Codex) via a public URL | `start.py` | "tunnel", "proxy" |
| **ngrok URL** | The public URL that external agents use to reach the bridge | `start.py` | "bridge URL", "public URL" |

---

## Bounded Context: Modules (Deep Module Layer)

| Term | Definition | Module | Synonyms to Avoid |
| ------ | ----------- | -------- | ------------------- |
| **Module** | One of the five deep modules in `modules/` — each hides a domain's complexity behind a typed interface | `modules/` | "service", "helper", "util" |
| **FSResult** | Typed dict returned by `fs_service` operations — always has `path`, `content`, `data` keys | `modules/fs_service.py` | "file response", "read result" |
| **ShellResult** | Typed dict returned by `shell_executor.execute()` — always has `exit_code`, `stdout`, `stderr`, `shell` | `modules/shell_executor.py` | "command result", "run result" |
| **ShellNotAvailableError** | Raised when a requested shell (bash) is not installed on the host | `modules/shell_executor.py` | "bash not found", "shell error" |
| **ScreenshotResult** | Typed dict from `ui_automation.screenshot()` — has `image_base64`, optionally `saved_path` | `modules/ui_automation.py` | "screenshot", "image result" |
| **InboxMessage** | Typed dict from `inbox_service.inbox_read()` — has `file`, `content` on success; `error`, `inbox_files` on 404 | `modules/inbox_service.py` | "message", "inbox content" |
| **OracleStatus** | Full health snapshot of Oracle V5 + Quantower | `modules/oracle_session.py` | "oracle health", "status" |
| **ChatResult** | Typed dict from `chat_service.chat()` with provider response text, model choice, elapsed time, and redacted errors | `modules/chat_service.py` | "chat response", "LLM result" |
| **ChatHealthResult** | Provider diagnostic snapshot from `chat_service.test_chat_providers()` | `modules/chat_service.py` | "provider status", "LLM health" |
| **Chat provider routing** | Gemini-first and OpenRouter-fallback selection hidden behind `chat_service` | `modules/chat_service.py` | "chat logic in bridge.py", "provider helper" |

---

## Bounded Context: Shell Execution

| Term | Definition | Module | Synonyms to Avoid |
| ------ | ----------- | -------- | ------------------- |
| **Shell selector** | The `shell` parameter in `POST /shell` — chooses the execution engine | `modules/shell_executor.py` | "shell type", "engine" |
| **PowerShell** | Default shell (`powershell.exe -NoProfile -NonInteractive -Command`) | `modules/shell_executor.py` | "PS", "ps1" |
| **cmd** | Windows Command Prompt shell (`cmd.exe /d /s /c`) | `modules/shell_executor.py` | "command prompt", "DOS" |
| **bash** | Git Bash shell, auto-discovered via `JULES_BASH_PATH` or `C:\Program Files\Git\bin\bash.exe` | `modules/shell_executor.py` | "unix shell", "git bash" |
| **exit_code** | The process return code from a shell execution (0 = success) | `modules/shell_executor.py` | "return code", "status code", "code" |
| **cwd** | Working directory for a shell command | `modules/shell_executor.py` | "directory", "path", "working dir" |

---

## Bounded Context: Oracle V5 (Trading Strategy)

| Term | Definition | Module | Synonyms to Avoid |
| ------ | ----------- | -------- | ------------------- |
| **Oracle** | The OracleV5 trading strategy — a C# DLL deployed to Quantower | `modules/oracle_session.py` | "strategy", "algo", "bot" |
| **Oracle repo** | `C:\aotp\projects\OracleV5` — the git repository containing Oracle source code | `modules/oracle_session.py` | "source", "project folder" |
| **Strategy DLL** | `OracleV5.Strategy.dll` — the compiled binary deployed to Quantower | `modules/oracle_session.py` | "DLL", "binary", "build output" |
| **info.xml** | Quantower's settings file for the Oracle instance — contains symbol/account binding and state | `modules/oracle_session.py` | "config", "settings file" |
| **instance ID** | UUID identifying the specific Oracle V5 instance in Quantower (`f9eb0699-...`) | `modules/oracle_session.py` | "ID", "GUID", "UUID" |
| **Verify script** | `Tools/Verify-OracleReplayReady.ps1` — checks all gates for replay readiness | `modules/oracle_session.py` | "health check", "validation" |
| **Deploy script** | `Tools/Deploy-OracleQuantowerStrategy.ps1` — copies built DLL to Quantower | `modules/oracle_session.py` | "install", "copy" |
| **Blocker** | A condition that prevents Oracle from running (unbound symbol, Quantower not running, etc.) | `modules/oracle_session.py` | "error", "issue", "problem" |
| **Gate** | A named readiness checkpoint (G2 = DLL deployed, G3 = dry run proof, G4 = DOM L2, G5 = order lifecycle) | `modules/oracle_session.py` | "check", "milestone", "step" |
| **Telemetry** | CSV files in `OneDrive/Documents/Oracle_V5_Telemetry/CSV/` — live strategy output | `modules/oracle_session.py` | "logs", "output", "data" |
| **Pipeline active** | Whether the latest telemetry CSV shows non-zero position or order counts | `modules/oracle_session.py` | "running", "live", "active" |

---

## Bounded Context: Quantower (Trading Platform)

| Term | Definition | Module | Synonyms to Avoid |
| ------ | ----------- | -------- | ------------------- |
| **Quantower** | The algorithmic trading platform running Oracle — detected by the `Starter` process | `modules/oracle_session.py` | "trading platform", "QT" |
| **Starter** | Quantower's launcher process name (used to check if Quantower is running) | `modules/oracle_session.py` | "process", "app" |
| **StM** | Strategies Manager in Quantower — UI panel where Oracle instance is configured | (docs) | "strategy manager", "settings" |
| **MES** | Micro E-mini S&P 500 futures — the primary symbol Oracle trades | (docs) | "symbol", "instrument", "ticker" |
| **Symbol binding** | The `Symbol` entry in `info.xml` being set to a valid trading instrument | `modules/oracle_session.py` | "symbol config", "symbol setup" |
| **Account binding** | The `Account` entry in `info.xml` being set to a valid broker account | `modules/oracle_session.py` | "account config", "account setup" |
| **Dry run mode** | Oracle running without real order submission — for testing the pipeline end-to-end | (info.xml) | "paper trading", "simulation", "test mode" |
| **Market replay** | Quantower's backtesting mode — replays historical market data to feed Oracle | (docs) | "backtest", "historical replay" |

---

## Bounded Context: Inbox (Agent Communication)

| Term | Definition | Module | Synonyms to Avoid |
| ------ | ----------- | -------- | ------------------- |
| **Inbox** | The `jules_inbox/` directory — file-based message exchange between operator and Jules | `modules/inbox_service.py` | "messages", "mailbox" |
| **OPERATOR_RESPONSE.md** | Default file the operator writes to communicate with Jules | `modules/inbox_service.py` | "operator message", "input file" |
| **JULES_RESPONSE.md** | Default file Jules writes to communicate with the operator | `modules/inbox_service.py` | "agent response", "output file" |
| **Operator** | The human (you) who controls Jules and monitors the bridge | (bridge context) | "user", "admin", "human" |
| **Jules** | The external AI agent that calls the bridge API to accomplish tasks | (bridge context) | "agent", "AI", "bot" |
| **Codex** | An alternate AI agent system (used in TIBIN handover context) | `modules/oracle_session.py` | "assistant", "model" |

---

## Bounded Context: UI Automation

| Term | Definition | Module | Synonyms to Avoid |
| ------ | ----------- | -------- | ------------------- |
| **Screenshot** | A full-desktop PNG captured via pyautogui, returned as base64 | `modules/ui_automation.py` | "image", "capture", "screen" |
| **Display bounds** | The screen resolution (e.g., 1920×1080) — coordinates must be within this | `modules/ui_automation.py` | "screen size", "resolution" |
| **pyautogui** | Python library for mouse/keyboard control — hidden inside `ui_automation.py` | `modules/ui_automation.py` | (internal — don't expose in routes) |
| **FAILSAFE** | pyautogui's safety mechanism — move mouse to top-left corner to abort automation | `bridge.py` | "kill switch", "abort" |

---

## Bounded Context: AKC (Agent Knowledge Context)

| Term | Definition | Module | Synonyms to Avoid |
| ------ | ----------- | -------- | ------------------- |
| **AKC** | Agent Knowledge Context: a source-backed checkpoint that turns transcripts, project context, and runtime learnings into compact operating rules | `modules/akc_module.py` | "random memory", "summary" |
| **AKC checkpoint** | Markdown file containing source inventory, path refs, extracted operating rules, and the daily loop | `context/08_akc_context_checkpoint.md` | "notes", "dump" |
| **AKC readiness** | Session-start gate that verifies the AKC checkpoint exists, has `status: ready`, and includes required operating rules | `modules/akc_module.py` | "context check", "preflight" |
| **Source inventory** | List of source files with readability, SHA-256, line counts, and redacted path references | `modules/akc_module.py` | "file list" |
| **path-ref** | Stable redacted local path identifier returned instead of raw absolute paths | `modules/akc_module.py` | "path", "filename" |
| **Operating rule** | Compact rule extracted from source material that guides future agent behavior | `modules/akc_module.py` | "summary bullet" |

---

## Bounded Context: Repo Context Guard

| Term | Definition | Module | Synonyms to Avoid |
| ------ | ----------- | -------- | ------------------- |
| **Repo context guard** | Bounded Git repo inventory and collision detector used before orchestration work crosses project boundaries | `modules/repo_context_guard.py` | "repo scanner", "project list" |
| **Repo provenance label** | Stable repo identity composed from name plus path-derived `path_ref`, branch, and redacted remote URL | `modules/repo_context_guard.py` | "folder name", "project name" |
| **Collision** | A shared remote, repo name, package name, port, node ref, workspace dependency, or local dependency crossing repo roots | `modules/repo_context_guard.py` | "warning", "duplicate" |
| **Port collision** | Two or more repos claiming the same detected service port | `modules/repo_context_guard.py` | "server conflict" |
| **Node ref collision** | Two or more repos pointing at the same non-secret host, IP, VM, worker, or server env reference | `modules/repo_context_guard.py` | "machine conflict" |
| **Local dependency coupling** | A `file:`, `link:`, or workspace dependency that binds one repo to another local repo | `modules/repo_context_guard.py` | "shared package" |

---

## Anti-Patterns (Terms to Never Use)

| Wrong Term | Correct Term | Why |
| ----------- | ------------- | ----- |
| "API" (unqualified) | "bridge route" or "bridge endpoint" | "API" is too vague — everything is an API |
| "run" (for shell) | `execute` | Matches the actual function name |
| "file" (for inbox) | "inbox file" or "inbox message" | Distinguishes from filesystem files |
| "error" (for HTTP response) | "BridgeHTTPError" or "route error" | Too generic |
| "result" (unqualified) | `FSResult`, `ShellResult`, etc. | Use the specific TypedDict name |
| "code" (for exit code) | `exit_code` | `code` is an alias; prefer the canonical name |
