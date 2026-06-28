# Jules Bridge — Gotchas

> Context file 5 of 7. What goes wrong. Not comprehensive docs — just the landmines.
> Nick Ni: "I have 553 lines of gotchas. Instead of 10,000 lines of docs."

## bridge.py

- **`string_field(data, key, default=...)`** — use `default=""` not `default=None` for optional strings
- **`json_payload()`** — raises BridgeHTTPError(400) if body is not valid JSON; always wrap with `@route_errors`
- **`@route_errors`** — MUST be the first decorator after `@app.route` (innermost position)
- **`jsonify(dict(some_dataclass))`** — dataclasses are NOT auto-serializable; convert to dict first
- **Adding a new route** — must also add to the TENTACLES list and to `context/02_architecture.md` route table
- **`POST /notify/email` attachments** - validate every local attachment path with `existing_path(..., kind="file")` before calling SMTP. Do not silently skip missing screenshots; reports must not claim evidence was attached when the file is absent.
- **`ROOT_DIR`** is the Jules Bridge project root — use it for all default paths
- **`LOG_PATH`** is defined at module level — don't redefine it in route handlers
- **`GET /health`** — exists since Phase 5; returns `{status, bridge, uptime_s}`; used by ngrok/monitoring
- **`GET /` and `GET /info`** — authenticated discovery routes; unlike `/health` and `/ping`, they require the bearer token and return bridge metadata instead of browser-facing 404s

## modules/__init__.py

- **Adding a new module** — must add BOTH the import AND the `__all__` entry
- **Order matters** — modules that depend on others must be imported after their dependencies
- **Never re-export private helpers** (those prefixed with `_`)

## fs_service

- **`grep(pattern, path)`** — pattern is Python `re` regex, not glob
- **`tail(path, lines=50)`** — returns last N lines from end of file; `lines` param is from the end
- **`list_dir(path)`** — does NOT recurse; use `grep` for recursive search
- **Encoding** — always `encoding="utf-8", errors="replace"` for reading text files on Windows

## shell_executor

- **PowerShell on Windows** — always use `["powershell", "-Command", cmd]` not `["pwsh", ...]`
- **Timeout** — default is 30s; long builds need `timeout=120` or more
- **Exit codes** — `returncode=0` does NOT mean the command succeeded on Windows (always check output too)
- **Stderr** — captured into `stderr` field; check it even when returncode=0

## oracle_session

- **`oracle_status()`** — NEVER raises; always returns dict with `error` key if something failed
- **Info XML path** — must exist before `oracle_build_deploy()` is called; verify with `Verify-OracleReplayReady.ps1`
- **Quantower process name** — `Starter.exe` (check via `Get-Process -Name Starter`)
- **DLL path** — `C:\Quantower\Settings\Scripts\Strategies\OracleV5.Strategy.dll` (hardcoded in `oracle_session.py`)
- **Build config** — always `-c Release -a x64`; Debug builds won't load in Quantower
- **Quantower UI memory** — read `memory/quantower.md` before UI automation; it records Strategy Manager, connection dialog, screenshot evidence, and failure-mode patterns

## reasoning_module

- **Model aliases** — use `"stub"` (tests), `"fast"` (gemini-2.0-flash), `"smart"` (gemini-2.5-pro). Never pass raw model strings unless the alias doesn't exist yet.
- **`tests/eval_reasoning.py`** — CDLC eval harness for `reasoning_module`; run `python tests/eval_reasoning.py --model stub` for offline proof, or `--model fast` when a live Gemini eval is explicitly desired
- **Eval results** — `memory/eval_results.json` is structured JSON, not markdown memory; do not append prose to it by hand
- **`GEMINI_API_KEY`** — must be set in environment for `model="fast"` or `model="smart"`; if missing, falls back to stub output with a WARNING log (does NOT raise)
- **`reason(problem, budget=10)`** — budget is max L-level steps; keep under 20 to avoid token bloat
- **`ReasoningTrace.to_inbox_summary()`** — call this, not `.inbox_summary()` (no such method)
- **ACT halting** — if confidence > 0.85, halts early; this is intentional, not a bug
- **`plan_only()`** — does NOT run L module; use this for previewing plans without executing
- **Gemini fallback** — if Gemini call fails (network, quota, JSON parse error), falls back to stub output silently; check logs for `WARNING jules_bridge.reasoning`

## retrospective_module

- **`analyze_session()`** — reads bridge.log from `LOG_PATH`; if log doesn't exist, returns empty report
- **Memory files** — written to `memory/` in project root; create this dir manually or call `analyze_session` once
- **`record_test_evidence(output)`** — takes raw pytest stdout as string; pipe via `result.stdout`
- **Evidence path** — `memory/test_evidence.json` is a capped list of evidence records; middleware must read the latest record, not treat the file as a single object
- **Domain classification** — if the word "oracle" appears in a learning, it goes to `memory/oracle.md`
- **`prune_memory(max_age_days=30)`** — DESTRUCTIVE; rewrites memory files in place. Always commit `memory/` to git before pruning.
- **prune_memory timestamp pattern** — looks for `## Session 20250601T143022` format in headings; sections with no timestamp are kept (conservative)
- **`analyze_session(auto_prune=True)`** — prunes only after the current session learning is written; default is `False` and `/retrospective/analyze` must receive a boolean `auto_prune`
- **Evidence gating** — `/oracle/*` routes return `X-Evidence-Age-Warning: stale:{N}s` when evidence is > 1h old; `EVIDENCE_GATE_HARD=1` uses a pre-route hard gate so stale Oracle route bodies are not invoked and callers get HTTP 423 with `{error, age_s, threshold_s}`
- **Evidence gate exemptions** — `GET /health` and all `/retrospective/*` routes must pass even when hard mode is on, so evidence can always be refreshed
- **HTTP status parsing** — match exact route status codes (`-> 500`, `"HTTP/1.1" 500`); never count `:5000` ports or `5000ms` thresholds as 500 errors
- **Doom-loop memory** — dedupe repeated streaks by route and keep the largest streak so analyze output remains actionable

## akc_module

- **AKC means Agent Knowledge Context** — source-backed checkpoint, not a vague memory note
- **`build_akc_context(source_paths)`** — never returns raw local paths; API and markdown use `path-ref:*` masking
- **Source inventory** — missing or unreadable sources are reported in `sources[]` and status becomes `blocked` or `partial`; the module should not crash on missing transcripts
- **Unreadable source errors** — keep `error` generic (`OSError: unreadable source` style); do not return raw OS exception strings because they can include local paths
- **`POST /akc/context`** — requires at least one `source_paths` entry so an empty POST cannot overwrite the durable checkpoint with an empty blocked file
- **Checkpoint path** — default route destination is `context/08_akc_context_checkpoint.md`
- **`GET /akc/readiness`** — session-start gate; verifies checkpoint exists, checkpoint status is `ready`, and required operating rules are present
- **Default required rules** — include the Google Drive/Cloud operating rule so the source requirement stays visible; readiness still does not prove provider credentials or integration state
- **Readiness status** — missing checkpoint returns `blocked`; present checkpoint with missing required rules returns `partial`; only all gates passing returns `ready`
- **Operating rules** — extracted from curated keywords, so treat them as a compact routing layer, not a complete summary of every transcript
- **Google Drive/Cloud** — AKC may record them as an operating rule, but credentials and provider connection state must be verified separately before claiming integration readiness

## context_orchestrator

- **`build_context_subagents(...)`** — source context planning only; it must not call Jules CLI, list remote sessions, or launch workers.
- **Smart truncation** — packets keep source head/tail excerpts and hash the omitted middle. Do not treat omitted middle as irrelevant; retrieve it only when a role needs it.
- **Context memory store** — `context_memory_store` stores retrieval refs and hashes, not raw omitted text. Use it to decide what survives outside active prompt context without bloating every packet.
- **Long-session evals** — `long_session_eval_plan` follows the 10-turn preload / 11th-turn probe pattern so late context loss is testable before calling a long workflow complete.
- **Path handling** — public source rows and packet text use `path_ref:*`/`inline`, not raw source paths. `packet_files` can be raw paths because those are generated local artifacts.
- **Role ids** — supported defaults are `context_cartographer`, `memory_curator`, `implementation_planner`, and `verification_agent`; unknown requested roles fall back to the default role set.
- **`POST /akc/subagents`** — requires either inline `content`/`data` or at least one `source_paths` entry; empty requests are rejected at the route layer.
- **No-slop workflow** — `no_slop_workflow` must keep `research -> plan -> implement` phases and the review gates `review_research_before_plan`, `review_plan_before_code`, and `record_evidence_before_done`.
- **Context budget** — default target is 40% of a 170k-character window. If `context_budget.over_budget=true`, write/update compaction artifacts before implementation instead of pushing more source text into packets.
- **Packet output** — defaults to `jules_inbox/context_subagents/` and writes `CONTEXT_SUBAGENT_INDEX.md`, `NO_SLOP_WORKFLOW.md`, `CONTEXT_MEMORY_STORE.json`, `CONTEXT_QUALITY_EVAL.md`, and `CONTEXT_SUBAGENT_STATE.json` when `write_packets=true`.

## inbox_service

- **`inbox_read()`** — reads all `.md` files in `jules_inbox/`; sorted alphabetically
- **Message format** — each message is a markdown file; first `##` heading is the subject
- **`inbox_write()`** — creates new file with timestamp; does NOT overwrite existing messages

## jules_orchestrator

- **`POST /jules/dispatch`** only prepares worker packets and launch commands; it must not start remote Jules sessions by itself
- **Packet output** defaults to `jules_inbox/jules_dispatch/`; review `jules_launch_commands.ps1` before running because it calls `jules new`
- **`POST /jules/launch`** defaults to `dry_run=true`; only `dry_run=false` attempts live `jules new` calls and writes `JULES_LAUNCH_STATE.json`
- **`POST /jules/launch` duplicate fan-out** can use `force_packet_files` with `preserve_existing_session_ids=true` so a speculative duplicate launch appends the new session id instead of forgetting older active attempts for that packet
- **`POST /jules/preflight`** should be the live gate before launch; it verifies direct CLI version and remote-session readiness without creating sessions
- **`POST /jules/sessions`** defaults to `dry_run=true`; live mode calls `jules remote list --session` with process-tree cleanup on timeout
- **`POST /jules/pull`** defaults to `dry_run=true`; live mode calls `jules remote pull --session <id>` and persists pull JSON under `JULES_REMOTE_PULLS`
- **`POST /jules/cot`** writes `JULES_COT_LEDGER.md`/`.json`; completion is only proven when a matching completion report or pull output contains evidence sections
- **`pulled_output_reported`** means `jules remote pull` returned a successful unified diff artifact; this counts as COT evidence without requesting private chain-of-thought
- **`POST /jules/cycle`** is the operator-safe orchestration route; it composes dispatch/launch/pull/COT and keeps live launch disabled if remote listing is not `ok`
- **Windows Jules CLI** should prefer `C:\Users\abdul\AppData\Roaming\npm\bin\jules.exe` for bare `jules`; the npm `jules.cmd` shim can hang while the direct binary returns version and remote sessions cleanly
- **Launch packet encoding** must stay UTF-8; Windows `charmap` encoding failed on packet emoji and left `jules.exe new` waiting for input
- **Cumulative COT state** depends on `skip_launched=true` behavior in cycle launches; repeated small launch batches must merge `JULES_LAUNCH_STATE.json` instead of overwriting earlier session ids
- **Pull-only cycles** must preserve live launch state; when `pull=true` and `launch=false`, `/jules/cycle` only pulls session ids marked `Completed` by remote listing and must not rewrite launched rows to dry-run
- **`POST /jules/watch`** automates bounded polling/pull/COT refresh, but it cannot approve Jules plans; `Awaiting Plan` and `Awaiting User` statuses are surfaced as attention-required rows
- **`POST /jules/fleet`** respects `max_concurrent`; `In Progress`, `Planning`, and fresh `unknown` remote statuses consume capacity, while `Completed`, `Failed`, `missing`, stale `unknown`, and `Awaiting Plan` free capacity for retry
- **`POST /jules/fleet-watch`** is the self-maintaining loop; it alternates fleet scaling and COT refresh until the wait window ends or all COT rows complete
- **Successful pull artifacts** are not re-pulled on later cycle/fleet loops; delete the corresponding `JULES_REMOTE_PULLS/jules_pull_<session>.json` file only if you intentionally need to force a fresh pull
- **Failed remote sessions** are relaunched by `/jules/fleet` when capacity is available; the new launch replaces the failed session id for that packet in `JULES_LAUNCH_STATE.json`
- **Live launch success requires a session id**; Jules can return exit code 0 with `Error:` in stderr, so `launch_packets()` must treat CLI error output or missing session ids as failed, not launched
- **Worker packets must stay noninteractive**; packet operating rules tell Jules not to stop for plan approval because this CLI only exposes `remote list/new/pull`
- **Stale blank remote rows** become retryable after 10 minutes; this prevents COT from sticking forever on a row with no terminal status
- **COT handling** means completion-of-task evidence summaries here, not private chain-of-thought disclosure

## Windows-specific

- **Paths** — always use raw strings `r"C:\path"` or forward slashes `"C:/path"` (avoid backslash escaping bugs)
- **`os.path.join` on Windows** — produces backslashes; Flask routes need forward slashes
- **PowerShell execution policy** — if scripts fail with "not digitally signed", add `-ExecutionPolicy Bypass`
- **File locking** — Windows locks files that are open; `oracle_status()` uses `try/except` on file reads


## human_mimic_driver

- Keep H/L/ACT desktop-driving loops in `modules/human_mimic_driver.py`; `bridge.py` routes must only validate request fields, optionally build notification callbacks, call the module, and return JSON.
- `drive_quantower_login(...)` must never receive or return plaintext passwords. It types only non-secret username metadata from `get_secret(...)`; real OS-backed secret providers must keep secret material inside the provider/action boundary.
- On Academic/Local Node setups, treat `/ui/drive_quantower_login` as a Local Node executor route. Policy decisions belong in the Cloud Node prompt/code path; the school computer must not host bridge OS-file installs or credential storage.
- Notifications for Human-Mimic tasks are best-effort callbacks. Email failures must not crash the UI driver or leak secret material into error text.

## vm_manager

- `detect_resource_pressure(...)` accepts injected `cpu_percent` and `memory_percent` for deterministic tests; when omitted it uses a bounded PowerShell/CIM host metric read and returns `status="error"` instead of raising if metrics cannot be collected.
- `boot_secondary_vm(...)` is dry-run by default. Real launch requires both `dry_run=false` and `allow_vm_boot=true`.
- VM scripts must live under `JULES_VM_SCRIPT_DIR` and `script_name` must be a simple file name, not a path. Allowed extensions are `.ps1`, `.cmd`, and `.bat`.
- `/vm/*` routes are Local Node executor routes. They should validate fields, call `modules.vm_manager`, and return typed JSON without policy logic in `bridge.py`.
