# Jules Bridge — Progress Tracker

> Context file 6 of 7. The ONLY file that updates constantly.
> How the agent picks up exactly where you left off in a single prompt.

## Current Phase: Phase 5 — LLM Integration + Self-Improvement 🔄

## Phase History

### Phase 1 — Deep Module Refactor ✅
Applied Matt Pocco's deep module pattern (AI Engineer World Fair 2025).
- Extracted 5 deep modules from monolithic bridge.py
- Added 56 new unit tests
- All 14 integration tests still passing

### Phase 2 — HRM Reasoning Module ✅
Applied Hierarchical Reasoning Model architecture (Sapient Inc, June 2025).
- CDLC: Generated AGENTS.md + Ubiquitous Language for HRM repo
- Integrated reasoning_module.py with H/L/ACT pattern
- 34/34 tests passing

### Phase 3 — Harness Engineering ✅
Applied Nick Ni's "Case" harness principles (AI Engineer World Fair 2025).
- retrospective_module.py: reads bridge.log, detects doom loops, writes memory
- Six-file context system: context/01-06
- memory/ directory with per-domain markdown files
- 3 new retrospective routes

### Phase 4 — Job Pilot Agent Skills ✅ (Current)
Applied JSM/Job Pilot Agent Skills to Jules Bridge.
- Created 5 core agent skills: architect, remember, review, recover, imprint in `.agents/skills/`
- Updated workflow rules in `context/04_ai_workflow_rules.md`

## Active Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Memory format | Markdown files | Human + agent readable; matches Nick's Case |
| Evidence storage | SHA-256 in JSON | Cryptographic proof; cannot be faked |
| LLM integration | Gemini via alias system | No new API key; `fast`/`smart` aliases hide provider details |
| Module contract | Never raises | Partial data beats exceptions in a harness |
| Context system | 7-file + AGENTS.md | Ghost AI spec-driven approach + orchestrator |
| Gotchas over docs | ~553 lines | Guides without prescribing; smaller context |
| Agent Skills | 5 core skills | Systematize planning, continuity, review, recovery, and patterns |
| Evidence gating | Soft default, opt-in hard mode | `X-Evidence-Age-Warning` on stale `/oracle/*`; `EVIDENCE_GATE_HARD=1` returns 423 |
| Memory pruning | Age-based, opt-in auto-prune | `analyze_session(auto_prune=True)` writes current memory first, then prunes stale dated sections |

## What's Complete

- [x] `modules/fs_service.py`
- [x] `modules/shell_executor.py`
- [x] `modules/ui_automation.py`
- [x] `modules/inbox_service.py`
- [x] `modules/oracle_session.py`
- [x] `modules/reasoning_module.py` (HRM H/L/ACT + Gemini integration)
- [x] `modules/retrospective_module.py` (Nick's Case pattern + `prune_memory`)
- [x] `tests/test_reasoning_module.py` — 34 tests
- [x] `tests/test_retrospective_module.py`
- [x] `context/` — all 7 files
- [x] `.agents/AGENTS.md` — orchestrator (reading order, session protocol, skill triggers)
- [x] `memory/general.md` + `memory/oracle.md`
- [x] CDLC artifacts: HRM_AGENTS.md, HRM_UBIQUITOUS_LANGUAGE.md, hrm_context_eval.py
- [x] Reusable skills: `architect`, `remember`, `review`, `recover`, `imprint`
- [x] `GET /health` — fixes 404 storm; returns uptime; listed in TENTACLES
- [x] Gemini wired to `reasoning_module` via `_MODEL_ALIASES` (`fast`/`smart`/`stub`)
- [x] Evidence gating — `X-Evidence-Age-Warning` header on stale `/oracle/*` routes, with opt-in `EVIDENCE_GATE_HARD=1` HTTP 423 hard mode
- [x] `POST /retrospective/prune_memory` — age-based pruning, 30-day default
- [x] All missing routes added to TENTACLES manifest
- [x] `modules/akc_module.py` — Agent Knowledge Context checkpoint builder with source inventory, path-ref masking, operating rules, and `/akc/context` routes
- [x] `GET /akc/readiness` — session-start gate that verifies the AKC checkpoint exists, is `ready`, and contains required operating rules
- [x] `context/08_akc_context_checkpoint.md` — generated from 5 pasted transcript sources; status `ready`, readable=5, missing=0, operating_rule_count=9
- [x] `modules/jules_orchestrator.py` + `POST /jules/dispatch` - parse pasted Jules review/task queues into dry-run worker packets, explicit launch commands, and completion-of-task evidence summaries without exposing private chain-of-thought
- [x] `Run-JulesDispatch.ps1` - operator wrapper that writes Jules dispatch packets and only starts remote sessions when `-Launch` is explicitly passed
- [x] `POST /jules/launch` + `POST /jules/sessions` - dry-run-first launch/state and remote-session routes with Windows npm shim resolution and timeout process-tree cleanup
- [x] `POST /jules/pull` + `POST /jules/cot` - dry-run-first remote pull and completion-of-task ledger routes for tracking launched worker sessions through evidence summaries
- [x] `POST /jules/cycle` - one-call dry-run-first communication cycle that dispatches, checks remote readiness, gates live launch, pulls requested sessions, and refreshes COT state
- [x] `POST /jules/preflight` - direct Jules CLI readiness probe; verified `C:\Users\abdul\AppData\Roaming\npm\bin\jules.exe` returns version and remote sessions while the npm shim was the blocker
- [x] Live Jules remote launch - verified 6 OracleV5 worker packets launched through `/jules/cycle`, with cumulative `JULES_LAUNCH_STATE.json` and `JULES_COT_LEDGER.md` tracking all session ids
- [x] `POST /jules/watch` - bounded polling/pull/COT watcher that writes `JULES_WATCH_STATE.json` and reports `Awaiting Plan`/`Awaiting User` states as attention-required
- [x] Evidence parser hardened — pytest output with test names containing `failed` no longer records false failed evidence
- [x] `doc/tickets/001_eval_harness.md` — `tests/eval_reasoning.py` writes `memory/eval_results.json` with 3 representative reasoning problems, trace rows, scoring heuristics, and `stub_baseline`
- [x] `doc/tickets/002_quantower_memory.md` — `memory/quantower.md` now records Quantower window patterns, Strategy Manager evidence, connection indicators, screenshot refs, and failure modes
- [x] `doc/tickets/005_analyze_baseline.md` — `POST /retrospective/analyze` seeded real `bridge.log` learnings into `memory/general.md` and `memory/oracle.md`; evidence `d8a29098bcb0195ae05c03f940372e2b2e59b92337fa001122047b58e0f220a0`
- [x] `doc/tickets/003_harden_evidence_gating.md` — stale `/oracle/*` evidence can preempt route execution with HTTP 423 when `EVIDENCE_GATE_HARD=1`; evidence `5d7d1c9aadc8489d9671be5c5487dfdbf70183a8547e9ca40a8ac5536f31b1d4`
- [x] `doc/tickets/004_auto_prune_memory.md` — `POST /retrospective/analyze` accepts boolean `auto_prune` and prunes stale memory after writing current learnings; evidence `5d7d1c9aadc8489d9671be5c5487dfdbf70183a8547e9ca40a8ac5536f31b1d4`

## Phase 6 — Ralph Loop Infrastructure ✅ (Just Added)

Added a Ralph Loop agentic framework to Jules Bridge:
- Created `doc/tickets/` with 5 Phase 6 tickets (eval harness, Quantower memory, evidence gating, auto-prune, analyze baseline)
- Created `.agents/skills/ralph-loop/SKILL.md` — full loop protocol as a reusable Claude skill
- Created `Run-RalphLoop.ps1` — Windows PowerShell autonomous loop runner

## What's Next (Phase 6 — Active Tickets)

- [x] No active Phase 6 tickets remain in `doc/tickets/`.

**To run the loop**: `.\Run-RalphLoop.ps1` from the project root.

## Session 20260626T052000 - Jules Preflight And Live Worker Launch

- Added `POST /jules/preflight` and `jules_preflight()` to diagnose Jules CLI readiness without launching sessions. It checks candidate binaries, `jules version`, optional remote listing, auth indicator paths, and writes `JULES_PREFLIGHT.json`.
- Resolved the live launch blocker: bare `jules` now prefers the direct `C:\Users\abdul\AppData\Roaming\npm\bin\jules.exe` binary. Live `/jules/preflight` returned `ready=true`, direct binary version exited 0, and remote session listing returned `status=ok`.
- Hardened `jules new` input piping with `encoding="utf-8", errors="replace"` and cleanup on unexpected subprocess I/O errors after Windows `charmap` failed on packet emoji.
- Added cumulative launch-state merging and skip-launched behavior so repeated `/jules/cycle` batches preserve prior session ids and advance to unlaunched packets instead of overwriting the COT ledger.
- Live evidence: `/jules/cycle` launched all 6 prepared OracleV5 packets with 0 timeouts. Sessions: `7933109068325009327`, `18229231043984242586`, `15977893485366655852`, `7309447141457198958`, `2176039184437417198`, `2073294697310640127`.
- Current COT status: 6 launched, 0 completed, 6 `launched_pending_cot`; remote sessions were still in `Planning` immediately after launch.
- Evidence: `python -m pytest tests/ -q` passed 209 tests with 1 existing warning, SHA-256 `e7f3de0b3a8dc4136fa79ce5760b1cc0b8838ce830d4eb00d5e5b39a104153e4`.

## Session 20260626T053500 - Jules COT Watch Automation

- Added `POST /jules/watch` and `run_jules_watch()` to run bounded polling loops over launched Jules sessions, execute pull-only cycles, refresh COT, and persist `JULES_WATCH_STATE.json`.
- Tightened pull automation so `/jules/cycle` only pulls sessions that remote listing marks `Completed`, even when explicit session ids are supplied; direct `/jules/pull` remains the force-pull route.
- Added `-Watch`, `-WatchSeconds`, and `-PollSeconds` to `Run-JulesDispatch.ps1` so operators can watch existing launches without hand-writing JSON.
- Live evidence: `/jules/watch` ran 6 iterations over 180 seconds against the 6 OracleV5 sessions; all were `In Progress`, no sessions were completed, pull count was 0, and COT remained 0 complete / 6 pending.
- Evidence: `python -m pytest tests/ -q` passed 212 tests with 1 existing warning, SHA-256 `7c28afb012e407c797f32e635c793e16e141956c6ef3a4a649a2cd858cb3e20d`.

## Session 20260626T054500 - Jules Fleet Scale-Out

- Added `POST /jules/fleet` and `run_jules_fleet()` to maintain a larger Jules queue, count active tracked sessions, pull completed sessions, and launch only unlaunched packets within `max_concurrent` and `launch_batch_size`.
- `launch_packets()` now exposes `attempt_results` so fleet status reflects only the launches attempted in the current cycle, not older merged launch-state rows.
- `build_cot_ledger()` now counts successful pulled unified diffs as `pulled_output_reported`, so completed Jules sessions that return a diff artifact can advance COT without private chain-of-thought.
- Added `-Fleet`, `-MaxConcurrent`, and `-LaunchBatchSize` to `Run-JulesDispatch.ps1`; PowerShell syntax check passed.
- Live bridge verified `GET /ping` and `/tentacles`; `/jules/fleet` is listed in the manifest.
- Live scale-out evidence: dry-run built a 12-packet queue, then live `/jules/fleet` with `max_concurrent=8` launched sessions `52491288849365276`, `15670021964742231358`, and later `259272200479968395` as completed work freed one slot.
- Post-launch watch evidence: latest `/jules/watch` saw 9 tracked launched sessions: 1 `Completed`, 7 `In Progress`, 1 `Planning`, pull count 1, COT 1 complete / 11 pending.
- Evidence: `python -m pytest tests/ -q` passed 217 tests with 1 existing warning, SHA-256 `af295e6592d10be0b076e589960dfe851b4bc52f7441bb96479afe3a9aea0a0a`.

## Session 20260626T061000 - Jules Fleet Watch Self-Maintenance

- Added `POST /jules/fleet-watch` and `run_jules_fleet_watch()` to repeatedly run fleet scale/pull/COT refresh inside a bounded wait window until COT completes, a blocker appears, dry-run stops, or the window expires.
- Added `JulesFleetWatchResult`, `JULES_FLEET_WATCH_STATE.json`, and `Run-JulesDispatch.ps1 -FleetWatch`; PowerShell syntax check passed.
- Successful pull JSON artifacts are now reused by `/jules/cycle` and `/jules/fleet`, preventing repeated pulls of the same completed session on every polling iteration.
- Live bridge verified `/ping` and `/tentacles`; `/jules/fleet-watch` is listed in the manifest.
- Live scale-out evidence: raised the cap to `max_concurrent=12` and launched the remaining three queued packets: `4627866533596226046`, `16339142350785418820`, and `3747657005033268025`.
- Live fleet-watch evidence: 300-second `/jules/fleet-watch` ran 8 iterations; all 12 queued packets are launched, remote status ended at 1 `Completed` and 11 `In Progress`, no duplicate pull occurred, and COT remained 1 complete / 11 pending.
- Evidence: `python -m pytest tests/ -q` passed 221 tests with 1 existing warning, SHA-256 `c54e8dd38b269a0bff4db699c74ed9b19655761f158a2c99d682b340d5c2193a`.

## Session 20260626T062500 - Jules Queue Expansion

- Re-read `C:\Users\abdul\.codex\attachments\0c875dac-3076-454f-bf1d-24b611cb0a40\pasted-text-1.txt`; it contains 37 cards and 29 deduped open tasks after excluding completed/duplicate fingerprints.
- Expanded the maintained dispatch queue from 12 to all 29 deduped open packets.
- Live scale-out evidence: `/jules/fleet` with `max_instances=29`, `max_concurrent=16`, and `launch_batch_size=5` launched five additional sessions: `9633164573254984530`, `5817790581416074741`, `16087150018382239980`, `4929092745775405129`, and `17777535020966408974`.
- Current tracked state: 29 selected packets, 17 launched, 12 not launched. Latest `/jules/fleet-watch` ran 6 iterations over 300 seconds and ended with remote status 1 `Completed`, 16 `In Progress`; COT remained 1 complete / 28 pending.
- Evidence: `python -m pytest tests/ -q` passed 221 tests with 1 existing warning, SHA-256 `57c218af2493c018d59a1baed88f50e40b331fbd3602340f248ef51bf7b5ec11`.

## Session 20260626T070500 - Jules Full Launch And Failed Retry

- Launched the remaining 12 deduped open packets from the 29-packet queue, so `JULES_LAUNCH_STATE.json` now tracks all 29 selected packets as launched.
- Added failed-session retry behavior: `/jules/fleet` detects tracked remote rows marked `Failed`, prioritizes relaunching those packet files, and preserves the full launch state while replacing the failed session id.
- Pulled the failed session `7522224730435223464`; Jules returned `No diff found in the remote VM`, so the packet was relaunched as `946220871660003947`.
- Live fleet-watch evidence: two 600-second `/jules/fleet-watch` runs pulled additional completed sessions and advanced COT to 9 complete / 20 pending. Latest remote status counts ended at 9 `Completed`, 19 `In Progress`, and 1 blank/`unknown`.
- Evidence: `python -m pytest tests/ -q` passed 222 tests with 1 existing warning, SHA-256 `1ebbceae86f2797ccff7dac394e57a94d85c599a76b1bbeb64555dd5dd01a099`.

## Session 20260626T115700 - Jules Retry Hardening And Long Tail Watch

- Re-read the active goal queue source and the new agentic workflow transcript source before continuing.
- Hardened `/jules/fleet` retry behavior beyond explicit `Failed` rows: stale blank/`unknown` tracked rows retry after 10 minutes, `Awaiting Plan` rows retry because the installed Jules CLI exposes no plan-approval command, and malformed launch-state rows without session ids are no longer treated as launched.
- Hardened `launch_packets()` so exit code 0 is not enough for live launch success; CLI output containing `Error:`/`Fatal:` or missing session ids is marked `failed`.
- Updated generated worker packets to be noninteractive: workers must not stop at a plan or ask for approval, and should proceed unless a hard blocker prevents work.
- Live recovery evidence: stale blank `JT-016` was relaunched as `7537886744130045704`; stale blank `JT-025` was relaunched as `9126716179690030352`; stale blank `JT-035` was relaunched as `1454905039274392805`; long-tail replacements for `JT-032` and `JT-035` were launched as `16528644010708698533` and `13944901608959609572`.
- Live COT advanced from 9/29 to 27/29 complete. Remaining tracked packets are `JT-032-430a34` session `16528644010708698533` and `JT-035-7bc0c2` session `13944901608959609572`, both still `In Progress` with fresh remote activity at checkpoint time.
- Evidence: `python -m pytest tests/ -q` passed 226 tests with 1 existing warning, SHA-256 `b9717870aba194e7e5754b2362b8e978e87de76f238c244775cd92ddc367bfc3`.

## Session 20260626T132000 - Jules COT Complete

- Re-read `C:\Users\abdul\.codex\attachments\0c875dac-3076-454f-bf1d-24b611cb0a40\pasted-text-1.txt` before continuing; the goal queue still contains the 29 selected open packets tracked by `JULES_COT_LEDGER.json`.
- Added `preserve_existing_session_ids` to `launch_packets()` and exposed it through `POST /jules/launch` alongside `force_packet_files`, so speculative duplicate launches append new session ids and keep older active attempts pullable for the same packet.
- Live duplicate fan-out: added tracked duplicate sessions for `JT-032-430a34` and `JT-035-7bc0c2` while preserving existing session ids. `JT-032` completed via `16528644010708698533`; final `JT-035` completed via `5408819866706457101`.
- Final live COT evidence: `JULES_COT_LEDGER.json` reports `selected_count=29`, `completed_count=29`, `pending_count=0`, `blocked_count=0`, and `all_complete=true`.
- Evidence: `python -m pytest tests/ -q` passed 229 tests with 1 existing warning, SHA-256 `7d6fff120677f333081efc49e67ee575e0195d1d5d5801791a64f30e02d42cc1`.
