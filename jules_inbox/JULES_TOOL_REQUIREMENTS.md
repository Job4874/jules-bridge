# Jules System Tool Requirements

Read this after `WAKE_UP.txt`. Shell-only sessions are incomplete unless the bridge also uses the structured host tools needed for the current blocker.

Bridge: `https://parade-marrow-pulp.ngrok-free.dev`

## Required Tool Mix

| Local capability | Jules bridge route | Use |
|------------------|--------------------|-----|
| Health check | `GET /ping` | Confirm the bridge is online |
| Route manifest | `GET /tentacles` | Discover available tools |
| Request audit | `GET /session/log` | Review recent bridge calls |
| Read project files | `POST /fs/read` | Read playbooks, logs, `info.xml`, handovers |
| List folders | `POST /fs/list` | Discover logs and diagnostics |
| Tail logs | `POST /fs/tail` | Inspect recent telemetry and runtime output |
| Search logs | `POST /fs/grep` | Find gate strings such as `BROKER_SUBMISSION_BLOCKED_DRY_RUN` |
| Shell | `POST /shell` | Run targeted terminal commands |
| Desktop screenshot | `GET /ui/screenshot?save=true` | Capture UI state before clicks |
| Desktop input | `POST /ui/click`, `POST /ui/type` | Bind Symbol/Account or interact with Quantower when needed |
| Structured Oracle status | `GET /oracle/status` | Start every Oracle/Quantower session |
| One-shot Oracle build | `POST /oracle/build-deploy` | Use only when code changed |
| Codex handover index | `GET /codex/handover` | Locate host handover files |
| Operator inbox | `POST /inbox/read`, `POST /inbox/write` | Read instructions and write evidence |

## Mandatory Session Workflow

```text
1. GET  /ping
2. GET  /tentacles
3. POST /inbox/read  {"file": "JULES_TOOL_REQUIREMENTS.md"}
4. POST /inbox/read  {"file": "WAKE_UP.txt"}
5. GET  /oracle/status
6. GET  /ui/screenshot?save=true
7. Fix blockers with the narrowest route that proves the state.
8. POST /inbox/write with evidence and next action.
```

Do not run repeated `/shell` build loops while Symbol, Account, or telemetry blockers remain visible in `/oracle/status`.

## Shell Routing Architecture

All terminal calls should explicitly choose the intended shell when the command syntax matters.

### PowerShell

Engine:

```text
powershell.exe -NoProfile -NonInteractive -Command
```

Use for Windows objects, Quantower/Oracle PowerShell scripts, file checks, process checks, and structured admin queries.

```json
{
  "command": "Get-Process -Name Starter -ErrorAction SilentlyContinue | Select-Object Id, CPU",
  "shell": "powershell",
  "timeout": 30
}
```

### Command Prompt

Engine:

```text
cmd.exe /d /s /c
```

Use for simple batch syntax and Windows environment variable expansion.

```json
{
  "command": "echo %COMPUTERNAME%",
  "shell": "cmd",
  "timeout": 30
}
```

### Git Bash

Engine:

```text
bash.exe -lc
```

Discovery order:

1. `JULES_BASH_PATH`
2. `C:\Program Files\Git\bin\bash.exe`
3. `C:\Program Files (x86)\Git\bin\bash.exe`
4. `C:\Program Files\Git\usr\bin\bash.exe`
5. `PATH`

Use for Unix-style text pipelines when Git Bash is installed.

```json
{
  "command": "printf ok | grep ok",
  "shell": "bash",
  "timeout": 30
}
```

Do not request `wsl`; this host exposes `wsl.exe` but has no installed WSL distribution.

## Request And Error Rules

- POST bodies must be JSON objects.
- Empty POST bodies are treated as `{}` and then validated per route.
- Malformed JSON or non-JSON bodies return `400`.
- Missing or invalid parameters return `400`.
- Missing files or directories return `404`.
- Access denied returns `403`.
- Shell timeouts return `504`.
- Unexpected runtime failures return `500` without raw stack traces.

## UI Safety Rules

- Always run `GET /ui/screenshot?save=true` before `POST /ui/click`.
- `x` and `y` must be non-negative integers.
- Click coordinates must fit within the current display bounds.
- `button` must be `left`, `right`, or `middle`.
- `/ui/click` and `/ui/type` affect the real desktop, not a simulation.

## Codex Handover Access

Index:

```http
GET /codex/handover
```

Read files:

```json
POST /fs/read
{"path": "C:\\Users\\abdul\\.gemini\\antigravity-ide\\scratch\\tibin_handover\\TIBIN_CODEX_MASTER_HANDOVER_V2\\..."}
```

Useful Oracle/Quantower references:

```json
POST /fs/read
{"path": "C:\\aotp\\projects\\Quantower-c-sat\\Quantower c+ sat\\VISUAL_STUDIO_QUANTOWER_ACCEPTANCE_PLAYBOOK.md"}
```

```json
POST /fs/read
{"path": "C:\\aotp\\projects\\OracleV5\\diagnostics\\REPLAY_POST_DEPLOY_CHECKLIST.md"}
```

## Gate Evidence Targets

Dry-run broker block proof:

```json
POST /fs/grep
{"path": "<serilog path>", "pattern": "BROKER_SUBMISSION_BLOCKED_DRY_RUN"}
```

Telemetry tail:

```json
POST /fs/tail
{"path": "C:\\Users\\abdul\\OneDrive\\Documents\\Oracle_V5_Telemetry\\CSV\\heartbeat_2026-06-25.csv", "lines": 10}
```

G3 is not proven until logs or an equivalent playbook artifact prove dry-run broker blocking.

## Completion Checklist

- [ ] `GET /oracle/status` reviewed.
- [ ] Symbol and Account are bound in the Oracle V5 `info.xml`.
- [ ] `GET /ui/screenshot?save=true` shows the expected StM/UI state.
- [ ] MES Market Replay or equivalent feed is wired.
- [ ] Telemetry shows `pipeline_active: true`.
- [ ] Dry-run broker block proof is captured.
- [ ] `/inbox/write` records JSON snippets, screenshot paths, and next action.
