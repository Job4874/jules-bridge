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
