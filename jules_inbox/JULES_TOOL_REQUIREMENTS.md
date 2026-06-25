# Jules Tool Requirements — Codex Parity on Windows Host

**Read this after WAKE_UP.txt.** Shell-only sessions are **incomplete** unless every blocker below is cleared with evidence.

Bridge: `https://parade-marrow-pulp.ngrok-free.dev`  
Header: `ngrok-skip-browser-warning: true`

---

## 1. What Codex has that you must mirror via bridge

| Codex / Cursor (local) | Jules bridge equivalent | Required? |
|------------------------|-------------------------|-----------|
| Read any project file | `POST /fs/read` | **Yes** — playbooks, logs, `info.xml` |
| List directories | `POST /fs/list` | **Yes** — find logs, diagnostics |
| Tail logs | `POST /fs/tail` | **Yes** — Serilog, telemetry CSV |
| Search logs | `POST /fs/grep` | **Yes** — `BROKER_SUBMISSION_BLOCKED_DRY_RUN` |
| Terminal | `POST /shell` | Yes — but not for everything |
| See UI | `GET /ui/screenshot?save=true` | **Yes — before every click** |
| Click / type | `POST /ui/click`, `/ui/type` | **Yes** — StM, Symbol, Account, replay |
| Structured health | `GET /oracle/status` | **Yes — start every session** |
| One-shot build | `POST /oracle/build-deploy` | Only if code changed |
| Codex handover docs | `GET /codex/handover` + `/fs/read` | **Yes** — read before guessing |
| Audit trail | `GET /session/log` | Operator uses this to grade you |
| Inbox | `/inbox/read`, `/inbox/write` | **Yes** — every 30 min |

---

## 2. Mandatory session workflow (do not skip)

```
1. GET  /ping
2. GET  /tentacles
3. POST /inbox/read  → JULES_TOOL_REQUIREMENTS.md (this file)
4. POST /inbox/read  → WAKE_UP.txt
5. GET  /oracle/status          ← blockers list in JSON
6. GET  /ui/screenshot?save=true
7. … fix blockers using ui/* + fs/* …
8. POST /inbox/write → JULES_RESPONSE.md with evidence
```

**Forbidden:** Eight `/shell` build loops while Symbol/Account remain empty.

### `/shell` selector contract

Payload:

```json
{
  "command": "Get-Process",
  "shell": "powershell",
  "timeout": 30
}
```

Supported selectors:

- `powershell` (default): native Windows PowerShell via `powershell -Command`.
- `cmd`: Windows command prompt via `cmd.exe /d /s /c`.
- `bash`: Git Bash only. The bridge checks `JULES_BASH_PATH`, then local Git install paths, then `PATH`.

Do not request `wsl`; this host exposes `wsl.exe` but has no installed WSL distribution.

Input and error rules:

- POST bodies must be JSON objects.
- Malformed JSON or non-JSON bodies return `400`.
- Missing files return `404`.
- Access denied returns `403`.
- Command timeouts return `504`.

---

## 3. Codex handover access (on this host)

Index:

```http
GET /codex/handover
```

Then read files:

```json
POST /fs/read
{"path": "C:\\Users\\abdul\\.gemini\\antigravity-ide\\scratch\\tibin_handover\\TIBIN_CODEX_MASTER_HANDOVER_V2\\..."}
```

Playbook (acceptance gates):

```json
POST /fs/read
{"path": "C:\\aotp\\projects\\Quantower-c-sat\\Quantower c+ sat\\VISUAL_STUDIO_QUANTOWER_ACCEPTANCE_PLAYBOOK.md"}
```

Oracle replay checklist:

```json
POST /fs/read
{"path": "C:\\aotp\\projects\\OracleV5\\diagnostics\\REPLAY_POST_DEPLOY_CHECKLIST.md"}
```

---

## 4. Gate evidence (grep targets)

```json
POST /fs/grep
{"path": "<serilog path>", "pattern": "BROKER_SUBMISSION_BLOCKED_DRY_RUN"}
```

```json
POST /fs/tail
{"path": "C:\\Users\\abdul\\OneDrive\\Documents\\Oracle_V5_Telemetry\\CSV\\heartbeat_2026-06-25.csv", "lines": 10}
```

Gate G3 is **not** proven until grep finds dry-run block lines or playbook-equivalent log proof.

---

## 5. GitHub / repo access (Codex accs)

| Resource | URL / path |
|----------|------------|
| OracleV5 canonical repo | `C:\aotp\projects\OracleV5` |
| GitHub remote | `https://github.com/Job4874/OracleV5.git` |
| Branch | `perf/fix-empty-catch-block-datafeedmanager` |
| Do not build from | `Quantower-c-sat` LFS pointers, `Downloads\OracleV5-main` |

Use shell for git only when needed:

```powershell
cd C:\aotp\projects\OracleV5
git fetch origin
git status
dotnet test
```

Prefer `GET /oracle/status` over re-running verify by hand.

---

## 6. Completion checklist (all required)

- [ ] `GET /oracle/status` → `blockers: []`
- [ ] Symbol + Account bound in `info.xml`
- [ ] `GET /ui/screenshot?save=true` — StM Running
- [ ] MES Market Replay wired — telemetry `pipeline_active: true`
- [ ] `POST /fs/grep` — G3 dry-run proof
- [ ] `POST /inbox/write` — paste JSON snippets + screenshot paths

---

## 7. Operator grades you on tool mix

| Pattern | Grade |
|---------|-------|
| shell + inbox only | **F** for Quantower tasks |
| + oracle/status + fs/read | **C** |
| + ui/screenshot before clicks | **B** |
| + StM wired + replay telemetry + G3 grep | **A** |

— Operator, 2026-06-25
