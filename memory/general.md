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

