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
| Jules dispatch | `POST /jules/dispatch` | Convert pasted Jules task queues into worker packets and explicit launch commands |
| Jules packet launch | `POST /jules/launch` | Dry-run or explicitly launch prepared packets through `jules new` |
| Jules preflight | `POST /jules/preflight` | Verify direct Jules CLI version and remote readiness before live launch |
| Jules remote sessions | `POST /jules/sessions` | Dry-run or query `jules remote list --session` with timeout cleanup |
| Jules remote pull | `POST /jules/pull` | Dry-run or pull one remote session by id into persisted JSON evidence |
| Jules COT ledger | `POST /jules/cot` | Build the completion-of-task ledger from launch state and pull/report artifacts |
| Jules cycle | `POST /jules/cycle` | Run one dispatch/remote-check/launch/pull/COT communication cycle |
| Jules COT watch | `POST /jules/watch` | Poll launched sessions, pull completed results, and refresh COT within a bounded window |

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

## Jules Dispatch Packets

Use `POST /jules/dispatch` when the operator provides a pasted queue of Jules
cards with statuses such as `Needs review`, `Ready for review`, `Failed`, or
`Complete`.

Preview only:

```json
{
  "path": "C:\\Users\\abdul\\.codex\\attachments\\...\\pasted-text-1.txt",
  "max_instances": 4,
  "repo_path": "C:\\aotp\\projects\\OracleV5"
}
```

Write packet files and launch commands:

```json
{
  "path": "C:\\Users\\abdul\\.codex\\attachments\\...\\pasted-text-1.txt",
  "max_instances": 4,
  "write_packets": true,
  "repo_path": "C:\\aotp\\projects\\OracleV5"
}
```

`POST /jules/dispatch` does not start remote Jules sessions. Review
`jules_inbox\\jules_dispatch\\jules_launch_commands.ps1` before any live launch.
When `JULES_DISPATCH_INDEX.md` exists, `/jules/launch` follows that priority
order instead of alphabetical packet filenames.

Dry-run prepared launch packets:

```json
{
  "packet_dir": "C:\\Users\\abdul\\.jules\\jules_inbox\\jules_dispatch",
  "repo_path": "C:\\aotp\\projects\\OracleV5"
}
```

Live launch requires an explicit opt-in:

```json
{
  "packet_dir": "C:\\Users\\abdul\\.jules\\jules_inbox\\jules_dispatch",
  "repo_path": "C:\\aotp\\projects\\OracleV5",
  "dry_run": false,
  "limit": 1,
  "timeout_s": 120
}
```

Check remote sessions:

```json
{
  "dry_run": false,
  "timeout_s": 30
}
```

Preflight the local Jules CLI before live launch:

```json
{
  "timeout_s": 8,
  "check_remote": true,
  "write_state": true
}
```

Pull one completed remote session:

```json
{
  "session_id": "123456",
  "repo_path": "C:\\aotp\\projects\\OracleV5",
  "dry_run": false,
  "timeout_s": 120
}
```

Build or refresh the completion-of-task ledger:

```json
{
  "packet_dir": "C:\\Users\\abdul\\.jules\\jules_inbox\\jules_dispatch",
  "write_ledger": true
}
```

Run the full safe communication cycle:

```json
{
  "path": "C:\\Users\\abdul\\.codex\\attachments\\...\\pasted-text-1.txt",
  "packet_dir": "C:\\Users\\abdul\\.jules\\jules_inbox\\jules_dispatch",
  "repo_path": "C:\\aotp\\projects\\OracleV5",
  "max_instances": 6,
  "launch": false,
  "dry_run": true,
  "check_remote": true,
  "require_remote_ready": true
}
```

For live launch, set both `"launch": true` and `"dry_run": false`. The cycle
still refuses live launch when remote session listing is not `ok`. Cycle
launches skip packets already marked `launched`, merge `JULES_LAUNCH_STATE.json`,
and keep `JULES_COT_LEDGER.md` cumulative across multiple launch batches.
Pull-only cycles preserve live launch state and auto-pull only session ids that
remote listing marks `Completed` when no explicit `session_ids` list is provided.

Watch launched sessions until COT progresses or the bounded window ends:

```json
{
  "packet_dir": "C:\\Users\\abdul\\.jules\\jules_inbox\\jules_dispatch",
  "repo_path": "C:\\aotp\\projects\\OracleV5",
  "max_wait_s": 900,
  "poll_interval_s": 30,
  "dry_run": false,
  "require_remote_ready": true
}
```

`/jules/watch` writes `JULES_WATCH_STATE.json`. It cannot approve Jules plans
because the current Jules CLI exposes no plan-approval command; inspect
`latest_remote_statuses` for `Awaiting Plan` or `Awaiting User` rows.

Maintain a bounded worker fleet:

```json
{
  "path": "C:\\Users\\abdul\\.codex\\attachments\\...\\pasted-text-1.txt",
  "packet_dir": "C:\\Users\\abdul\\.jules\\jules_inbox\\jules_dispatch",
  "repo_path": "C:\\aotp\\projects\\OracleV5",
  "max_instances": 12,
  "max_concurrent": 8,
  "launch_batch_size": 2,
  "dry_run": true,
  "require_remote_ready": true
}
```

For live scale-out, set `"dry_run": false` only after reviewing
`active_remote_count`, `available_launch_capacity`, and `requested_launch_limit`.
`/jules/fleet` writes `JULES_FLEET_STATE.json`, pulls completed sessions, and
launches only unlaunched packets that fit inside the active-session cap.

Run the self-maintaining fleet watch loop:

```json
{
  "path": "C:\\Users\\abdul\\.codex\\attachments\\...\\pasted-text-1.txt",
  "packet_dir": "C:\\Users\\abdul\\.jules\\jules_inbox\\jules_dispatch",
  "repo_path": "C:\\aotp\\projects\\OracleV5",
  "max_instances": 12,
  "max_concurrent": 8,
  "launch_batch_size": 2,
  "max_wait_s": 900,
  "poll_interval_s": 30,
  "dry_run": false,
  "require_remote_ready": true
}
```

`/jules/fleet-watch` writes `JULES_FLEET_WATCH_STATE.json` and repeats the
fleet cycle until COT completes or the bounded wait expires. Successful pull
artifacts under `JULES_REMOTE_PULLS/` are reused instead of re-pulled.
When remote listing marks a tracked session `Failed`, `/jules/fleet` prioritizes
relaunching that packet before starting fresh unlaunched packets, if capacity is
available.

On Windows, the bridge resolves bare `jules` to the direct
`C:\Users\abdul\AppData\Roaming\npm\bin\jules.exe` when present because the npm
`jules.cmd` shim can hang. Packet prompts are piped as UTF-8; keep that behavior
or emoji/non-ASCII packet text can fail before `jules new` receives input.
Completion evidence should be a concise checklist, not private chain-of-thought.
If a completed Jules session pulls back a successful unified diff instead of a
prose report, `/jules/cot` records `pulled_output_reported` and counts that row
as completion evidence.

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
