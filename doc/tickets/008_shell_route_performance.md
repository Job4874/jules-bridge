# Ticket 008 — Shell & Jules Route Performance Hardening

Status: OPEN

## Priority: HIGH

Retrospective baseline detected severe performance regressions on high-value routes:

| Route | Avg Response Time | Threshold |
| --- | --- | --- |
| `POST /shell` | **58,214ms** | 5,000ms |
| `POST /jules/watch` | **103,624ms** | 5,000ms |
| `POST /jules/fleet` | **31,092ms** | 5,000ms |
| `POST /jules/fleet-watch` | **441,320ms** | 5,000ms |
| `POST /jules/cycle` | **29,064ms** | 5,000ms |
| `GET /dashboard/status` | **13,820ms** | 5,000ms |

These are not acceptable for Monday enterprise-grade shipping.

## Root Causes (Hypothesis)

1. **`POST /shell`** — PowerShell subprocess blocking event loop; no timeout per-call cache
2. **Jules fleet/watch routes** — Blocking on `jules remote list --session` (external CLI, ~8s each)
3. **Dashboard status** — Polling VM + oracle + bridge state synchronously on every call

## Objective

### Shell Route

- Add result caching: identical command + cwd hashed → cached response for 10s (configurable `SHELL_CACHE_TTL_S`)
- Enforce hard timeout: if `shell_executor` call exceeds `SHELL_MAX_S` (default 30), return partial output + `timed_out: true` instead of blocking forever
- Log slow calls: any shell call >5s emits a WARNING with command hash and duration

### Jules Routes

- Cache `jules remote list --session` output for 30s (`JULES_SESSION_CACHE_TTL_S`)
- Return cached session list on repeated calls within TTL window
- Add `cache_hit: true/false` to all fleet/watch/cycle response payloads
- Do NOT cache launch or pull calls (they are state-mutating)

### Dashboard Status

- Cache `GET /dashboard/status` for 5s (configurable `DASHBOARD_CACHE_TTL_S`)
- Return `cache_age_s` in response so caller knows data freshness
- Emit stale-cache header `X-Cache-Age: {age_s}` on every response

## Implementation Location

- `modules/shell_executor.py` — add `_shell_result_cache` dict + TTL logic
- `modules/jules_orchestrator.py` — add `_session_list_cache` dict + TTL logic
- `modules/dashboard_module.py` — add `_dashboard_status_cache` + TTL
- `bridge.py` — pass cache config from env vars to module calls

## Test Requirements (TDD — red first)

- `tests/test_shell_cache.py` — identical call within TTL hits cache; expired TTL misses
- `tests/test_jules_session_cache.py` — session list cached; launch/pull bypass cache
- `tests/test_dashboard_cache.py` — status cached; cache_age_s present in response
- All 288 existing tests must still pass

## Evidence Required

- `python -m pytest tests/ -q` green
- SHA-256 via `POST /retrospective/record_evidence`
- Add to `context/06_progress_tracker.md`

## Files Changed

- `modules/shell_executor.py`
- `modules/jules_orchestrator.py`
- `modules/dashboard_module.py`
- `bridge.py` (env var plumbing)
- `tests/test_shell_cache.py` (new)
- `tests/test_jules_session_cache.py` (new)
- `tests/test_dashboard_cache.py` (new)
- `context/05_gotchas.md` (caching gotchas)
- `context/06_progress_tracker.md`
- `doc/tickets/008_shell_route_performance.md` (this file → set Status: DONE)
