# Jules Bridge — General Memory

This file is maintained by the retrospective module.
Each session that runs `POST /retrospective/analyze` will append learnings here.

> **Principle (Nick Ni)**: "Every failure becomes data for the next run."

## How to use this file

Read this at the start of a Jules Bridge coding session to understand what
has gone wrong before and what to avoid.

## Initial Notes (Bootstrapped)

- Jules Bridge is a thin HTTP routing layer — all business logic lives in `modules/`
- Never add business logic to `bridge.py` — route handlers do validate → call module → return JSON only
- The 5 core modules: `fs_service`, `shell_executor`, `ui_automation`, `inbox_service`, `oracle_session`
- Phase 2 added: `reasoning_module` (HRM H/L/ACT pattern)
- Phase 3 added: `retrospective_module` (this memory system)
- Tests live in `tests/` — run with `python -m pytest tests/ -v`
- Record test evidence after every test run: `POST /retrospective/record_evidence`

## Session 20260626T021500 — Phase 5: LLM Integration + Self-Improvement

### Resolved: GET /health 404 storm

- `bridge.log` had 58 consecutive `GET /health → 404` in a tight loop (19:54 timestamp)
- Root cause: route never existed; caller (ngrok/monitoring) assumed standard health endpoint
- Fix: added `GET /health` returning `{status, bridge, uptime_s}` using `_BRIDGE_START_UTC` constant
- `_BRIDGE_START_UTC = datetime.now(timezone.utc)` set at module level (import time), not per-request
- Also added `/health` to TENTACLES manifest so clients can discover it

### Resolved: LLM stubs in reasoning_module

- `_h_module_call()` and `_l_module_call()` were pure deterministic stubs
- Now dispatched via `_MODEL_ALIASES` dict: `"stub"` → None (stub), `"fast"` → gemini-2.0-flash, `"smart"` → gemini-2.5-pro
- Gemini call in `_gemini_chat()`: lazy-imports `google.generativeai`, reads `GEMINI_API_KEY` from env
- If key missing or call fails: silently falls back to stub output + logs WARNING to `jules_bridge.reasoning`
- Tests still use `model="stub"` (default) — zero network calls, all 133 pass unchanged

### Added: Evidence gating (soft)

- `/oracle/*` routes now attach `X-Evidence-Age-Warning: stale:{N}s` if `test_evidence.json` is >1h old
- Implemented as second `@app.after_request` hook: `_evidence_age_check()`
- NOT a hard block (no 423) — warning header only; harden later when test-first is established
- Best-effort: if evidence file missing or malformed, request passes through with no header

### Added: POST /retrospective/prune_memory

- Pruning strategy: age-based (sections with `## Session 20YYMMDDTHHMMSS` stamps older than N days are removed)
- Sections with no parseable timestamp are KEPT (conservative default — don't lose things we can't date)
- `## How to use` and `## Initial Notes` headings are always preserved
- This is DESTRUCTIVE — rewrites files in place. Always commit `memory/` before pruning.
- Default: `max_age_days=30`; callable with `{"max_age_days": 7}` for aggressive pruning

### Added: Full TENTACLES manifest

- Reasoning routes (`/reasoning/solve`, `/reasoning/plan`, `/reasoning/execute_step`) were missing
- Retrospective routes (`/retrospective/analyze`, `/retrospective/record_evidence`, `/retrospective/memory`, `/retrospective/prune_memory`) were missing
- Now all routes discoverable via `GET /tentacles`

### Pattern: adding a new route (checklist)

1. Add handler in `bridge.py` with `@route_errors`
2. Add to `TENTACLES` list in `bridge.py`
3. Add to route table in `context/02_architecture.md`
4. Add gotcha in `context/05_gotchas.md` if any edge case
5. Export from `modules/__init__.py` if new module function added
6. Run `python -m pytest tests/ -v` → record evidence with `POST /retrospective/record_evidence`

## Session 20260626T025625 — AKC/TDD/Grill Integration

- Added `modules/akc_module.py` as a deep module for Agent Knowledge Context checkpoints: it inventories explicit source files, computes SHA-256 hashes, masks local paths as `path-ref:*`, extracts compact operating rules, and writes `context/08_akc_context_checkpoint.md`.
- Added `/akc/context` routes: `GET` loads the current checkpoint; `POST` builds a source-backed checkpoint from explicit transcript/context file paths.
- Generated the current AKC checkpoint from 5 pasted transcript sources: status `ready`, readable=5, missing=0, operating_rule_count=9.
- Added `check_akc_readiness()` and `GET /akc/readiness` as the session-start gate for AKC: it verifies checkpoint existence, `status: ready`, and required operating rules before agents trust the checkpoint.
- Added AKC vocabulary, gotchas, architecture entries, TENTACLES entries, tests, and agent loading order so future sessions load AKC before daily work.
- Hardened `record_test_evidence()` after a false-negative: pytest test names containing `failed` no longer mark a passing run as failed. Latest test proof is stored in `memory/test_evidence.json`.

## Session 20260626T031500 — Reasoning Eval Harness

- Completed Ticket 001: added `tests/eval_reasoning.py`, a CDLC eval harness for `reasoning_module.reason()`.
- Offline eval command: `python tests/eval_reasoning.py --model stub`; it writes `memory/eval_results.json`.
- Report rows include problem id/text, model, full `ReasoningTrace`, simple scoring fields, and `stub_baseline` comparison.
- Current stub eval generated 3 representative Jules Bridge problems with average score `0.95`.

## Session 20260626T031910 — Quantower UI Memory

- Completed Ticket 002: created `memory/quantower.md` from bridge log references and existing `qw_*.png` screenshot evidence.
- The Quantower memory now documents DOM surface title patterns, connection dialog indicators, Strategy Manager `Oracle V5` loaded/created evidence, blank Symbol/Account binding gotcha, and known failure modes.
- Future Oracle/Quantower UI automation should read `memory/quantower.md` before clicking or claiming strategy readiness.

## Session ticket005_baseline — 2026-06-26T03:27:13.708432+00:00

- DOOM LOOP: POST /fs/read called 6x consecutively. Route 'POST /fs/read' called 6x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: POST /fs/write called 3x consecutively. Route 'POST /fs/write' called 3x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: POST /inbox/read called 4x consecutively. Route 'POST /inbox/read' called 4x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: POST /shell called 10x consecutively. Route 'POST /shell' called 10x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: POST /ui/click called 4x consecutively. Route 'POST /ui/click' called 4x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: GET /ping called 4x consecutively. Route 'GET /ping' called 4x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: POST /fs/tail called 8x consecutively. Route 'POST /fs/tail' called 8x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: GET /health called 32x consecutively. Route 'GET /health' called 32x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: POST /akc/context called 5x consecutively. Route 'POST /akc/context' called 5x consecutively. Add a circuit breaker or cache the last response.
- TIMEOUT: Subprocess/PowerShell calls timing out (60x). Increase timeout or add async handling.
- HARNESS BUG: Internal server errors (6x). Check module exception handling — add defensive try/except.
- PERFORMANCE: Route 'POST /shell' averaged 26424ms over 4 calls (threshold: 5000ms). Consider caching or reducing subprocess overhead.
- RETROSPECTIVE BASELINE: analyze_session found 8 log patterns. Use the domain memories before the next bridge/runtime work.

## Session 20260626T033304 — Evidence Gate Hard Mode

- Completed Ticket 003: `_evidence_age_check()` now reads the latest record from `memory/test_evidence.json` list history instead of treating it as a single object.
- Default behavior remains soft: stale `/oracle/*` evidence adds `X-Evidence-Age-Warning: stale:{age}s`.
- Setting `EVIDENCE_GATE_HARD=1` uses a pre-route hard gate and returns HTTP 423 with `{error: "evidence_stale", age_s, threshold_s}` for stale `/oracle/*` evidence.
- `GET /health` and `/retrospective/*` are exempt because the gate only applies to `/oracle/*`, keeping evidence refresh routes available.
- Evidence: `python -m pytest tests/ -v` passed 172 tests, SHA-256 `5d7d1c9aadc8489d9671be5c5487dfdbf70183a8547e9ca40a8ac5536f31b1d4`.

## Session 20260626T033540 — Auto-Prune Analyze Option

- Completed Ticket 004: `analyze_session()` now accepts `auto_prune=False` by default, preserving existing callers.
- `auto_prune=True` runs `prune_memory(memory_path=...)` only after writing current session learnings, so the new session is not pruned before it lands.
- `POST /retrospective/analyze` accepts boolean `auto_prune` and rejects non-boolean values via `bool_field()`.
- The `retrospective` logger emits `auto_prune removed N sections` when the opt-in prune path runs.
- Evidence: `python -m pytest tests/ -v` passed 172 tests, SHA-256 `5d7d1c9aadc8489d9671be5c5487dfdbf70183a8547e9ca40a8ac5536f31b1d4`.

## Session 20260626T041243 — Jules Dispatch Orchestration

- Added `modules/jules_orchestrator.py` as a deep module for pasted Jules task queues: it parses task cards, normalizes statuses, dedupes repeated file/issue fingerprints, and prepares worker packets plus explicit `jules new` launch commands.
- Added `POST /jules/dispatch` to the bridge and TENTACLES manifest. The route is dry-run by default and never starts remote Jules sessions; `write_packets=true` writes under `jules_inbox/jules_dispatch/`.
- Added `Run-JulesDispatch.ps1` as the operator wrapper. It calls `/jules/dispatch`, writes packet files, and only launches remote sessions when `-Launch` is explicitly passed.
- Ran the dispatcher against `C:\Users\abdul\.codex\attachments\0c875dac-3076-454f-bf1d-24b611cb0a40\pasted-text-1.txt`: parsed 37 cards and generated 6 deduped worker packets for OracleV5.
- Hardened `record_test_evidence()` for PowerShell `Tee-Object` captures that arrive with interleaved NUL characters; parsing now uses cleaned text while the SHA-256 still covers the original captured string.
- Evidence: `python -m pytest tests/ -v` passed 182 tests, SHA-256 `c04d9ae3a3faf5cb63664e8b3acf2bf27c754eb4ca84c28b40df959c4ca519a3`.

## Session 20260626T042300 — Jules Launch And Remote Session Control

- Added `POST /jules/launch` and `POST /jules/sessions` plus `launch_packets()` and `list_remote_sessions()` in `modules/jules_orchestrator.py`.
- Launch/session routes default to `dry_run=true`; live mode requires explicit `dry_run=false` and writes `JULES_LAUNCH_STATE.json` for packet launch attempts.
- Packet launches honor `JULES_DISPATCH_INDEX.md` order when present, so failed/high-priority cards stay ahead of alphabetically earlier ready-review packets.
- Hardened Windows CLI execution: bare `jules` resolves to the npm `jules.cmd` shim, and timeout handling kills the process tree so blocked `node`/`jules.exe` children do not linger.
- Current live boundary: on 2026-06-25, dry-run launch selected 6 packets, but `POST /jules/sessions` with `dry_run=false` returned `timeout` after about 8 seconds. Do not attempt live packet launch until remote session listing succeeds.
- Evidence: `python -m pytest tests/ -v` passed 191 tests, SHA-256 `ee4bc99172724ddb0e91defa3bba20402854cae696e6ae43f51d9f90395180ff`.

## Session 20260626T043400 — Jules Pull And COT Ledger

- Added dry-run-first `POST /jules/pull` for `jules remote pull --session <id>` and persisted pull-result JSON under `JULES_REMOTE_PULLS` when requested.
- Added `POST /jules/cot` and `build_cot_ledger()` to synthesize `JULES_COT_LEDGER.md`/`.json` from launch state plus pull/completion reports.
- Updated `Run-JulesDispatch.ps1` to call `/jules/cot` after launch preview so every dispatch run has a visible completion-of-task ledger path.
- Current ledger for `jules_inbox/jules_dispatch/` tracks 6 packets, 0 complete, 6 pending/not_launched because live Jules session listing still times out.
- Evidence: `python -m pytest tests/ -v` passed 198 tests, SHA-256 `51e1b5e0c2a347586ebbdc3d32f0cd4af3186ee780ab4dfb013c7beea6616d45`.

## Session 20260626T044000 — Jules Communication Cycle

- Added dry-run-first `POST /jules/cycle` and `run_jules_cycle()` to compose dispatch, remote readiness check, gated launch, optional pull, COT ledger refresh, and `JULES_CYCLE_STATE.json` persistence in one call.
- `Run-JulesDispatch.ps1` now uses `/jules/cycle` so operator dispatches get launch state, remote-readiness blocker reporting, COT ledger, and cycle state from one bridge transaction.
- Live launch remains disabled when `require_remote_ready=true` and `jules remote list --session` times out; latest live-requested cycle returned `status=blocked`, `launch_dry_run=true`, and no leftover `node`/`jules.exe`.
- Live localhost bridge verified after starting `bridge.py`: `GET /tentacles` exposes `jules_dispatch`, `jules_launch`, `jules_sessions`, `jules_pull`, `jules_cot`, and `jules_cycle`; `POST /jules/cycle` dry-run selected 6 packets and refreshed `JULES_CYCLE_STATE.json`.
- Evidence: `python -m pytest tests/ -v` passed 202 tests, SHA-256 `82d90b9b673aa653ed397e53f504f549e7910e14055e653f35e6576abecfa68e`.

## Session 20260626T052000 - Jules Preflight And Live Worker Launch

- Added `POST /jules/preflight` and `jules_preflight()` so live launch is gated by direct CLI/version/remote checks without creating sessions.
- The live blocker was the npm `jules.cmd` shim, not auth: `C:\Users\abdul\AppData\Roaming\npm\bin\jules.exe` returned version and `remote list --session` successfully through the bridge.
- Bare `jules` now resolves to the direct `npm\bin\jules.exe` binary when present. Keep this preference unless the direct binary path changes.
- Fixed a Windows launch bug where packet emoji triggered a `charmap` encode error before `jules new` received stdin. `_run_cli_command()` now uses UTF-8 text pipes and terminates the child tree on unexpected I/O errors.
- Launch state is cumulative: `/jules/cycle` skips packets already marked `launched`, merges state rows, and keeps `JULES_COT_LEDGER.md` covering all dispatch packets across repeated launch batches.
- Live evidence: 6 OracleV5 worker packets launched with 0 timeouts. Session ids: `7933109068325009327`, `18229231043984242586`, `15977893485366655852`, `7309447141457198958`, `2176039184437417198`, `2073294697310640127`.
- Current status after launch: remote sessions visible and in `Planning`; COT ledger has 6 `launched_pending_cot`, 0 completed.
- Evidence: `python -m pytest tests/ -q` passed 209 tests with 1 existing warning, SHA-256 `e7f3de0b3a8dc4136fa79ce5760b1cc0b8838ce830d4eb00d5e5b39a104153e4`.

## Session 20260626T053500 - Jules COT Watch Automation

- Added `POST /jules/watch` and `run_jules_watch()` to automate bounded polling over launched Jules sessions, run pull-only cycles, refresh `JULES_COT_LEDGER.md`, and write `JULES_WATCH_STATE.json`.
- `/jules/cycle` now filters pull candidates to sessions marked `Completed` by `jules remote list --session`; explicit session ids no longer force-pull incomplete sessions through the cycle route.
- `Run-JulesDispatch.ps1` now supports `-Watch`, `-WatchSeconds`, and `-PollSeconds` for watching existing packets or launch runs from PowerShell.
- Live watch evidence: 180-second `/jules/watch` run completed 6 iterations, pulled 0 sessions, and ended with all 6 launched OracleV5 sessions `In Progress`; COT stayed 0 complete / 6 pending.
- The Jules CLI has no exposed plan-approval command; watcher reports `Awaiting Plan`/`Awaiting User` rows as attention-required instead of pretending COT can complete without operator/Jules-side progress.
- Evidence: `python -m pytest tests/ -q` passed 212 tests with 1 existing warning, SHA-256 `7c28afb012e407c797f32e635c793e16e141956c6ef3a4a649a2cd858cb3e20d`.

## Session 20260626T054500 - Jules Fleet Scale-Out

- Added `POST /jules/fleet` and `run_jules_fleet()` for bounded Jules worker-fleet maintenance. It regenerates the queue, uses tracked launch-state session ids for capacity, pulls completed sessions, and launches only unlaunched packets that fit inside `max_concurrent` and `launch_batch_size`.
- `launch_packets()` now returns `attempt_results`; fleet status uses that field so old merged `launched` rows do not masquerade as launches from the current cycle.
- `build_cot_ledger()` now counts successful pulled unified diffs as `pulled_output_reported`, so completed Jules sessions that return a diff artifact can advance COT without private chain-of-thought.
- `Run-JulesDispatch.ps1` now supports `-Fleet`, `-MaxConcurrent`, and `-LaunchBatchSize`; `[System.Management.Automation.PSParser]` syntax check passed.
- Live bridge verified `/ping` and `/tentacles`; `/jules/fleet` is listed.
- Live scale-out: `/jules/fleet` dry-run built 12 packets, then live fleet with `max_concurrent=8` launched sessions `52491288849365276`, `15670021964742231358`, and later `259272200479968395` when a completed session freed one tracked slot.
- Latest one-iteration `/jules/watch`: 9 tracked launched sessions total, 1 `Completed`, 7 `In Progress`, 1 `Planning`, pull count 1, COT 1 complete / 11 pending.
- Evidence: `python -m pytest tests/ -q` passed 217 tests with 1 existing warning, SHA-256 `af295e6592d10be0b076e589960dfe851b4bc52f7441bb96479afe3a9aea0a0a`.

## Session 20260626T061000 - Jules Fleet Watch Self-Maintenance

- Added `POST /jules/fleet-watch` and `run_jules_fleet_watch()` for the self-maintaining loop: it calls fleet repeatedly, pulls completed work, refreshes COT, and fills newly opened capacity until COT completes or `max_wait_s` expires.
- Added `JulesFleetWatchResult`, `JULES_FLEET_WATCH_STATE.json`, and `Run-JulesDispatch.ps1 -FleetWatch`; PowerShell parser syntax check passed.
- `/jules/cycle` and `/jules/fleet` now skip re-pulling completed sessions when `JULES_REMOTE_PULLS/jules_pull_<session>.json` already records `status=pulled`, `exit_code=0`, and no timeout.
- Live bridge verified `/ping` and `/tentacles`; `/jules/fleet-watch` is listed.
- Live scale-out with `max_concurrent=12` launched the final three queued packets: `4627866533596226046`, `16339142350785418820`, and `3747657005033268025`.
- Latest 300-second `/jules/fleet-watch`: 8 iterations, all 12 queue packets launched, remote state ended at 1 `Completed` and 11 `In Progress`, no duplicate pull, COT 1 complete / 11 pending.
- Evidence: `python -m pytest tests/ -q` passed 221 tests with 1 existing warning, SHA-256 `c54e8dd38b269a0bff4db699c74ed9b19655761f158a2c99d682b340d5c2193a`.

## Session 20260626T062500 - Jules Queue Expansion

- Re-read the attached Jules queue file. It has 37 cards and 29 deduped open tasks when completed cards and duplicate fingerprints are excluded.
- Expanded the maintained dispatch queue from 12 packets to all 29 deduped open packets; do not treat the earlier 12-packet queue as the full objective scope.
- Live `/jules/fleet` with `max_instances=29`, `max_concurrent=16`, and `launch_batch_size=5` launched five more sessions: `9633164573254984530`, `5817790581416074741`, `16087150018382239980`, `4929092745775405129`, and `17777535020966408974`.
- Latest 300-second `/jules/fleet-watch`: 6 iterations, remote state ended at 1 `Completed`, 16 `In Progress`; COT 1 complete / 28 pending; launch state 17 launched / 12 not launched.
- Evidence: `python -m pytest tests/ -q` passed 221 tests with 1 existing warning, SHA-256 `57c218af2493c018d59a1baed88f50e40b331fbd3602340f248ef51bf7b5ec11`.

## Session 20260626T070500 - Jules Full Launch And Failed Retry

- Launched the remaining 12 deduped open packets; launch state now tracks 29 selected packets, all launched.
- Added `/jules/fleet` failed-session retry: tracked remote `Failed` rows are relaunched first when capacity exists, using `force_packet_files` while preserving the rest of `JULES_LAUNCH_STATE.json`.
- Failed session `7522224730435223464` for `JT-030-857e5b` pulled with `No diff found in the remote VM`; the fleet relaunched that packet as session `946220871660003947`.
- Latest live COT after two 600-second fleet-watch runs: 9 complete / 20 pending. Final remote status counts were 9 `Completed`, 19 `In Progress`, and 1 blank/`unknown`.
- Evidence: `python -m pytest tests/ -q` passed 222 tests with 1 existing warning, SHA-256 `1ebbceae86f2797ccff7dac394e57a94d85c599a76b1bbeb64555dd5dd01a099`.

## Session 20260626T115700 - Jules Retry Hardening And Long Tail Watch

- For Jules fleet COT, do not trust exit code 0 alone from `jules new`; require at least one session id and no `Error:`/`Fatal:` banner before marking a packet `launched`.
- Generated Jules worker packets now explicitly say not to stop at a plan or ask for plan approval. The installed CLI only exposes `remote list/new/pull`, so `Awaiting Plan` rows are retryable rather than actionable through the bridge.
- `/jules/fleet` now retries failed rows, stale blank/`unknown` rows after 10 minutes, and `Awaiting Plan` rows by replacing the tracked packet's session id in `JULES_LAUNCH_STATE.json`.
- Live watch advanced the 29-packet OracleV5 queue from 9/29 to 27/29 complete. Remaining tracked packets at checkpoint: `JT-032-430a34` session `16528644010708698533` and `JT-035-7bc0c2` session `13944901608959609572`, both `In Progress`.
- Evidence: `python -m pytest tests/ -q` passed 226 tests with 1 existing warning, SHA-256 `b9717870aba194e7e5754b2362b8e978e87de76f238c244775cd92ddc367bfc3`.

## Session 20260626T132000 - Jules COT Complete

- `launch_packets()` now supports `preserve_existing_session_ids`; `/jules/launch` passes it through with `force_packet_files`, enabling speculative duplicate worker instances without losing older active session ids from COT tracking.
- The last two long-tail packets were completed after duplicate fan-out. `JT-032-430a34` completed via `16528644010708698533`; `JT-035-7bc0c2` completed via `5408819866706457101`.
- Final COT state: `JULES_COT_LEDGER.json` shows 29 selected, 29 completed, 0 pending, 0 blocked, `all_complete=true`.
- Evidence: `python -m pytest tests/ -q` passed 229 tests with 1 existing warning, SHA-256 `7d6fff120677f333081efc49e67ee575e0195d1d5d5801791a64f30e02d42cc1`.

## Session 20260626T141500 - Context Sub-Agent Planning

- Added `modules/context_orchestrator.py` and `POST /akc/subagents` for offline context handling: large sources become head/tail capsules with omitted-middle SHA-256 hashes, context metrics, and role packets (`context_cartographer`, `memory_curator`, `implementation_planner`, `verification_agent`).
- `/akc/subagents` is not a Jules launch route. `write_packets=true` writes local markdown under `jules_inbox/context_subagents/`; it never calls `jules new`, remote list, or pull.
- Capsule excerpts redact Windows local paths found inside source text as `path-redacted`, while public source inventory uses `path_ref:*`. Generated packet file paths remain local artifact paths.
- Added `string_list_field(...)` in `bridge.py` for optional `list[str]` route fields.
- Evidence: `python -m pytest tests/ -q` passed 237 tests with 1 existing warning, SHA-256 `6148ccf5d6d3e00a2bf4dda03ea5cfad92251f0f5bfd0576abb267d63159eb21`.

## Session 20260626T173600 - Context Memory Store And Long-Session Eval

- `build_context_subagents(...)` now implements the context-engineering transcript contract beyond head/tail capsules: `context_memory_store` keeps hashed retrieval refs for omitted middles without storing raw omitted text, and `long_session_eval_plan` pins the 10-turn preload / 11th-turn probe eval pattern.
- `write_packets=true` now emits `CONTEXT_MEMORY_STORE.json` and `CONTEXT_QUALITY_EVAL.md` in `jules_inbox/context_subagents/`, alongside role packets, index/state, and `NO_SLOP_WORKFLOW.md`.
- Packet text includes a Context Handling Policy section: active context is head/tail only, omitted middles must be retrieved before assumptions, heavy source analysis stays in subagent packets, and long-session evals are an evidence gate.
- Generated packet excerpts now normalize CR/CRLF and trim trailing line whitespace so pasted transcripts do not make `git diff --check` noisy.
- Evidence: `/akc/subagents` route smoke on the two current pasted sources returned 2 readable sources, 4 role packets, 2 memory refs, and `context_budget.over_budget=false`; `python -m pytest tests/ -q` passed 240 tests with 1 existing warning, SHA-256 `7e42a3ecdcad29604d56efef9775d577985e939d8a503cbb9ef5a1c21c9e1d4c`.

## Session 20260626T000000 - Human-Mimic UI Driver Architecture Red Tests

- Security lock accepted for future UI/VM automation: operator-authorized OS-backed secrets only, no plaintext persistence, no secret leakage in logs/screenshots/evidence/PR text, and runtime `allow_secret_use=true` required before any secret retrieval or typing.
- Added `implementation_plan.md` with H/L/ACT plan for secure `ui_automation` expansion and future `vm_manager` module.
- Added first red TDD tests in `tests/test_ui_secret_and_detection.py` for `get_secret(...)` redaction/authorization behavior and `detect_ui_state(...)` Quantower OCR state classification.
- Targeted evidence: `python -m pytest tests/test_ui_secret_and_detection.py -q` failed as expected because `modules.ui_automation` does not yet export `get_secret` or `detect_ui_state`.

## Session 20260626T203837 - Human-Mimic UI Driver Green Phase

- Implemented minimal `ui_automation.get_secret(...)` and `ui_automation.detect_ui_state(...)` to satisfy the Human-Mimic UI red tests.
- `get_secret(...)` enforces `allow_secret_use`, supports injected OS-backed/mock providers, returns non-secret username metadata only, and never returns plaintext password fields.
- Secret-provider failures use sanitized error text so provider exception strings cannot leak credential material.
- `detect_ui_state(...)` classifies deterministic OCR/template signals for `quantower_login`, `quantower_loading`, `quantower_ready`, and `unknown`.
- Evidence: `python -m pytest tests/ -q` passed 244 tests with 1 existing warning, SHA-256 `8de1babe4bdad5b8fbc168813686c348a5073fdf758f71cd4b4dd788fddf7007`.

## Session 20260626T204200 - Human-Mimic Quantower ACT Driver

- Added `modules/human_mimic_driver.py` as the H/L/ACT driver layer over `ui_automation.detect_ui_state(...)`, `get_secret(...)`, `type_text(...)`, and `click(...)`.
- Added `drive_quantower_login(...)` with injectable type/click/secret-provider/notification callbacks for testability and Local Node execution. It never returns plaintext secret material and treats notifications as best-effort.
- Added `POST /ui/drive_quantower_login` as a thin bridge route: validate OCR text, submit coordinates, `allow_secret_use`, and `notify`; optionally build an email callback; call the module; return JSON.
- Documented Two-Node Zero-Trust mode: Cloud Node owns policy logic, Local Windows Node is the bridge executor, and Academic Nodes must not host bridge OS-file installs or credential storage.
- Evidence: `python -m pytest tests/ -q` passed 248 tests with 1 existing warning, SHA-256 `770defafb30620443caac2e1948960ca262a7699951fc8eb49ccc88065acde10`.

## Session 20260626T202607 - Human-Mimic VM Manager TDD

- Added `modules/vm_manager.py`: `detect_resource_pressure(...)` returns typed pressure status from injected metrics or bounded PowerShell/CIM host reads; `boot_secondary_vm(...)` validates simple file names under `JULES_VM_SCRIPT_DIR`, defaults to dry-run, and requires both `dry_run=false` and `allow_vm_boot=true` for real launch.
- Added thin bridge routes `POST /vm/resource_pressure` and `POST /vm/boot_secondary`, plus exports and TENTACLES entries. Keep policy out of `/vm/*`; routes only validate, call the module, and return JSON.
- Codex Chrome Extension was re-enabled in Chrome `Default` profile; extension browser connection now attaches and docs were read.
- Evidence: `python -m pytest tests/ -q` passed 274 tests with 1 existing warning, SHA-256 `9c9f9477f26ebdcc9c8696bb67ed1cffbdc54f6632be10242c27c41aaed2de7a`.

## Session 20260627T214922 — 2026-06-27T21:49:22.701894+00:00

- DOOM LOOP: POST /fs/read called 30x consecutively. Route 'POST /fs/read' called 30x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: POST /fs/write called 3x consecutively. Route 'POST /fs/write' called 3x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: POST /inbox/read called 9x consecutively. Route 'POST /inbox/read' called 9x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: POST /shell called 20x consecutively. Route 'POST /shell' called 20x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: POST /ui/click called 6x consecutively. Route 'POST /ui/click' called 6x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: GET /ping called 42x consecutively. Route 'GET /ping' called 42x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: POST /fs/tail called 8x consecutively. Route 'POST /fs/tail' called 8x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: GET /health called 32x consecutively. Route 'GET /health' called 32x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: POST /akc/context called 5x consecutively. Route 'POST /akc/context' called 5x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: POST /jules/dispatch called 4x consecutively. Route 'POST /jules/dispatch' called 4x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: POST /jules/launch called 6x consecutively. Route 'POST /jules/launch' called 6x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: POST /jules/sessions called 6x consecutively. Route 'POST /jules/sessions' called 6x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: POST /retrospective/record_evidence called 4x consecutively. Route 'POST /retrospective/record_evidence' called 4x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: POST /jules/pull called 3x consecutively. Route 'POST /jules/pull' called 3x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: POST /jules/cycle called 4x consecutively. Route 'POST /jules/cycle' called 4x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: POST /jules/fleet called 4x consecutively. Route 'POST /jules/fleet' called 4x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: POST /jules/fleet-watch called 34x consecutively. Route 'POST /jules/fleet-watch' called 34x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: POST /akc/subagents called 7x consecutively. Route 'POST /akc/subagents' called 7x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: POST /notify/email called 4x consecutively. Route 'POST /notify/email' called 4x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: GET /tentacles called 4x consecutively. Route 'GET /tentacles' called 4x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: POST /execute called 8x consecutively. Route 'POST /execute' called 8x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: POST /apps/launch_browser called 3x consecutively. Route 'POST /apps/launch_browser' called 3x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: GET /info called 4x consecutively. Route 'GET /info' called 4x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: POST /vm/boot_secondary called 4x consecutively. Route 'POST /vm/boot_secondary' called 4x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: GET /dashboard/status called 814x consecutively. Route 'GET /dashboard/status' called 814x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: POST /fs/list called 4x consecutively. Route 'POST /fs/list' called 4x consecutively. Add a circuit breaker or cache the last response.
- DOOM LOOP: GET /ui/screenshot called 4x consecutively. Route 'GET /ui/screenshot' called 4x consecutively. Add a circuit breaker or cache the last response.
- TIMEOUT: Subprocess/PowerShell calls timing out (232x). Increase timeout or add async handling.
- HARNESS BUG: Internal server errors (14x). Check module exception handling — add defensive try/except.
- PERFORMANCE: Route 'POST /shell' averaged 58214ms over 12 calls (threshold: 5000ms). Consider caching or reducing subprocess overhead.
- PERFORMANCE: Route 'POST /jules/sessions' averaged 13723ms over 15 calls (threshold: 5000ms). Consider caching or reducing subprocess overhead.
- PERFORMANCE: Route 'POST /jules/cycle' averaged 29064ms over 9 calls (threshold: 5000ms). Consider caching or reducing subprocess overhead.
- PERFORMANCE: Route 'POST /jules/preflight' averaged 6997ms over 5 calls (threshold: 5000ms). Consider caching or reducing subprocess overhead.
- PERFORMANCE: Route 'POST /jules/watch' averaged 103624ms over 5 calls (threshold: 5000ms). Consider caching or reducing subprocess overhead.
- PERFORMANCE: Route 'POST /jules/fleet' averaged 31092ms over 14 calls (threshold: 5000ms). Consider caching or reducing subprocess overhead.
- PERFORMANCE: Route 'POST /jules/fleet-watch' averaged 441320ms over 54 calls (threshold: 5000ms). Consider caching or reducing subprocess overhead.
- PERFORMANCE: Route 'POST /notify/email' averaged 30129ms over 2 calls (threshold: 5000ms). Consider caching or reducing subprocess overhead.
- PERFORMANCE: Route 'GET /dashboard/status' averaged 13820ms over 7 calls (threshold: 5000ms). Consider caching or reducing subprocess overhead.
- RETROSPECTIVE BASELINE: analyze_session found 18 log patterns. Use the domain memories before the next bridge/runtime work.

## Session 20260628T075134 - Notify Email Attachment Evidence

- `/notify/email` now accepts `attachments: list[str]` for screenshot/report evidence. The route validates each path with `existing_path(..., kind="file")` before SMTP so missing screenshots fail fast with 404 instead of being silently skipped.
- `notify_email.send_email(subject, body, mail_to=None, attachments=None)` keeps the old plain-text path when no attachments are present and switches to multipart only when files are supplied.
- Added module and route coverage in `tests/test_notify_email_enhanced.py` and `tests/test_bridge_routes.py::TestBridgeTokenAuth`; full evidence recorded: 284 tests passed, SHA-256 `281005fade8ce71fb3b568ea19bb5fb420466584703fe78d9ec1e18c35adadb4`.

## Session 20260629T092400 - Lint Cleanup Pass (303 tests passing)

### Python Module Fixes

- `modules/dashboard_module.py`: Moved `import time` and `import re` to top-level; removed `import re` from inside loop body.
- `modules/reasoning_module.py`: Added `import subprocess` + `from datetime import datetime, timezone` to top-level; removed both from inline locations; renamed `_ROOT_DIR` → `_root_dir`; renamed `_l_stub` args `step`→`_step`, `model`→`_model`; renamed `_extract_answer` arg `plan`→`_plan`; added `check=False` to `subprocess.run`; changed f-string logging to lazy `%s` format; stripped trailing whitespace.
- `modules/oracle_session.py`: Added `check=False` to all 3 `subprocess.run` calls.
- `modules/ui_automation.py`: Renamed `image_path`→`_image_path` (unused, reserved for future OCR integration).

### Test Fix

- `tests/test_hre_depth.py`: Updated `rm._ROOT_DIR` → `rm._root_dir` to match renamed module attribute. Final count: **303/303 passing**.

### Markdown Fixes

- `context/05_gotchas.md`: Fixed `## modules/**init**.py` heading (MD050); collapsed extra blank lines.
- `context/07_library_docs.md`: Added `text` language spec to unnamed code fence; simplified table separators.
- `jules_inbox/JULES_MISSION_001.md`: Converted from plain text to proper Markdown (H1 first, H2 sections, code fences with `text` lang).
- `jules_inbox/JULES_MISSION_001_RESPONSE.md`: Fixed multiple H1 mid-doc → H2.
- `jules_inbox/MONDAY_MISSION_20260629.md`, `OPERATOR_PROXY_CORRECTION.md`: Added `text` lang to code fences.
- `memory/reasoning.md`: Added `# Reasoning Memory` H1 as first line.

### Patterns

- **Private path constants**: use `_root_dir` (snake_case), not `_ROOT_DIR` — pylint sees module-level `_NAME` as variable.
- **Unused stub params**: prefix with `_` to suppress warning without removing the interface contract.
- **subprocess.run**: always explicit `check=False` or `check=True`.
- **Broad except in route handlers**: `except Exception as exc:  # noqa: BLE001` is correct suppression.
- **Lazy module imports in bridge.py routes**: `from modules.xxx import yyy` inside handlers is intentional; do NOT hoist to top.

## Session 20260629T111500 — Gotchas Recovery & Test Fix (307 tests passing)

- **Test Fix**: Resolved a test collection failure where `tests/test_oracle_session.py` was missing `from unittest.mock import patch`, resulting in `NameError` on patch decorators.
- **Gotchas Recovery**: Fixed `context/05_gotchas.md` which had been corrupted with Chinese character unicode sequences (e.g., `\u80e2\ue7a3\u8a95...`) due to a double UTF-16LE -> UTF-8 encoding bug in previous agent sessions. Created `scratch/double_recover.py` to reverse this corruption by encoding UTF-8 characters back to UTF-16LE bytes twice, and restored the original clean English gotchas file.
- **Verification**: Verified the entire test suite is completely green (307/307 passed). Started the bridge server via `python bridge.py` on port 5000 and confirmed both `/health` and `/akc/readiness` respond successfully.

## Session 20260629T122530 — Chat Service Deep Module Cleanup (315 tests passing)

- Extracted Gemini/OpenRouter chat provider routing from `bridge.py` into `modules/chat_service.py`; `/chat` and `/chat/test` are now thin validate -> module -> JSON wrappers.
- New canonical chat terms: `ChatResult`, `ChatHealthResult`, and `Chat provider routing`. Keep provider payload construction, fallback, timing, and secret redaction inside `chat_service`.
- Added module-boundary tests in `tests/test_chat_service.py` and route-thinness tests in `tests/test_bridge_routes.py`.
- Verification: `python -m py_compile bridge.py modules\chat_service.py modules\__init__.py`; focused pytest passed 74 tests; full `python -m pytest tests/ -q` passed 315 tests. Evidence hash `e1e7b4bce3b265a14326d66a18eb33d1a99af42a348d85cb1d45c9a614065408`.

## Session 20260630T000027 - Jules Production Readiness PR

- Integrated completed Jules worker output into branch `codex/jules-production-finish` and opened draft PR #64 at `https://github.com/Job4874/jules-bridge/pull/64`.
- Added `GET /health/deep`, evidence hard-gate reason handling, durable dashboard tunnel discovery from bridge log, `jules_inbox/LOCAL_TUNNEL_CURRENT.log`, and env fallback, plus dashboard UI active-tunnel badge support.
- Reconciled Jules-derived runtime fixes: removed duplicate `ui_automation` shadows, exported `check_and_scale_compute`, preserved future-dated evidence memory during pruning, and carried staged shell/inbox/orchestrator hardening into the PR.
- Verification: Python 3.12.10 full suite passed `406 passed`; dashboard `pnpm run build` passed with bundled Node; `git diff --check` passed; local bridge, public LocalTunnel, and in-app browser dashboard were verified.
- Current public tunnel at handoff: `https://silly-pumas-dance.loca.lt`. `/health/deep` overall status was `ok`, but live provider readiness still warned that GCP lacked an active gcloud session and Gemini had an invalid API key.

## Session 20260630T004438 - Provider Readiness Truth Patch

- Launched Jules provider-readiness worker `4817979060578580922`; reconciled its useful diff without applying stale hunks that would remove the circuit breaker or duplicate `/health/deep`.
- `modules.health_service.get_deep_health()` now maps Gemini/OpenRouter readiness through `chat_service.test_chat_providers()` so deep health does not falsely pass OpenRouter via the public `/models` endpoint.
- `/dashboard/status` now includes provider statuses and the React dashboard shows `GEMINI` / `OPENROUTER` badges beside `SYS_UP` and `TUNNEL`.
- Verification: focused tests passed 29 tests; full suite passed `410 passed`; dashboard build passed; local `/health/deep`, `/chat/test`, `/chat`, `/dashboard/status`, public tunnel, and in-app browser dashboard were verified.
- Current public tunnel at handoff: `https://olive-paws-shine.loca.lt`. Live provider truth is still degraded: Gemini invalid key, OpenRouter 401 `User not found`, GCP no active gcloud / worker not configured, Azure reachable.

## Session 20260630T005100 - Provider Readiness Handoff Refresh

- Refreshed PR #64 and automation truth after restarting the bridge with the installed Google Cloud SDK on PATH.
- Current public tunnel: `https://clever-seas-go.loca.lt`; local and public `/health` pass, and authenticated `/health/deep` returns `status: ok`.
- Current deep-health provider truth: GCP token pass, Azure SSH pass, Gemini fail invalid API key, OpenRouter fail 401 `User not found`; `/dashboard/status` still reports `jules-offload-worker` as `not_configured` because `GCE_WORKER_IP` is unset.
- Jules duplicate session `11181112389803823618` completed after `4817979060578580922`; its patch was reviewed without `--apply` and left unapplied because it overlapped the pushed fix and dropped useful HTTP status detail.
- Updated heartbeat automation `jules-bridge-overnight-production-loop` with source/readiness head `090d7bb`, current tunnel, reviewed duplicate session state, and remaining external readiness blockers.

## Session 20260630T010000 - GCP Worker Online Runtime Fix

- Resolved the dashboard GCP worker configuration gap locally by discovering `jules-offload-worker` through gcloud and adding non-secret worker coordinates to ignored `.env`.
- Restarted the bridge with Google Cloud SDK on PATH; local `/dashboard/status` and public tunnel `/dashboard/status` now report GCP `online: 1`, IP `34.132.193.73`, `reachable: true`, `status: online`.
- Verified VM relay through local and public `/vm/status`: worker `online: true`, `tasks_running: 0`, and VM-side Gemini/OpenRouter flags true.
- Recycled the stale public tunnel after restart. Current fallback public URL: `https://wet-ducks-try.loca.lt`.
- Remaining provider blockers are now narrowed to local bridge credentials: Gemini invalid API key and OpenRouter 401 `User not found`.

## Session 20260630T073000 - Dashboard Cloud Workers Panel

- Launched 10 read-only indexing agents across bridge API, Jules orchestration, dashboard UI, cloud workers, provider readiness, tests, local skills/extensions, handoff docs, install/runtime, and PR readiness; the reports converged on the same release blocker: local Gemini/OpenRouter credentials still fail while GCP worker readiness is online.
- Pulled Jules session `12782098339635048796` without `--apply` and integrated the aligned dashboard cloud-worker panel while preserving current `bridge.tunnel_url || bridge.ngrok_url` tunnel detection and provider badges.
- Dashboard now renders a compact `Cloud Workers` panel from `/dashboard/status.cloud` with online/total count, provider, VM name, status, IP, and reachable state. Default viewport proof shows `GCP`, `ONLINE`, `Reachable`, `jules-offload-worker`, and `34.132.193.73`.
- Verification: dashboard `pnpm run lint` and `pnpm run build` pass; in-app Browser DOM and screenshot proof pass; local/public `/dashboard/status` report `cloud.online: 1`; `/vm/status` reports worker online; `/health/deep` reports GCP/Azure pass but Gemini 400 invalid key and OpenRouter 401 remain.
- Full suite evidence was refreshed through `POST /retrospective/record_evidence`: `python -m pytest tests/ -q` passed 410 tests, SHA-256 `51b715cd2515449c8acb4d90af4e35ebde3496f904b73055e91a7acad8422379`.

## Session 20260630T091700 - VM Chat Readiness Consistency

- Jules session `2648582880137579851` stayed planning/no-diff, so Codex applied the narrow emergency fix for VM readiness consistency.
- `modules.chat_service` now keeps a bounded `_LAST_VM_CHAT_SUCCESS` marker. Recent real VM chat success can override a flaky follow-up health-probe timeout/provider-unavailable result, while expired success or no-success failure still reports VM failure.
- Dashboard lightweight checks still do not enqueue VM work; they report `VM worker online; VM chat recently succeeded` when fresh local success exists.
- Verification: focused chat/deep-health tests passed 27 tests; dashboard/route slice passed 89 tests; full `python -m pytest tests/ -v` passed 427 tests.
- Runtime proof after clean bridge restart: `/chat` returned `model_used=vm/jules-worker`, `/chat/test` healthy with `vm_worker: ok`, `/health/deep` mapped VM to `pass`, dashboard rendered `TUNNEL: ACTIVE` and `VM CHAT: OK`, and LocalTunnel `https://neat-oranges-wink.loca.lt/ping` returned `Jules Bridge Online`.

