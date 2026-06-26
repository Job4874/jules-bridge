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
