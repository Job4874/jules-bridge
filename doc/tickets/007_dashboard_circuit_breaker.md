# Ticket 007 — Dashboard Circuit Breaker

Status: DONE

## Priority: CRITICAL

The retrospective baseline detected `/dashboard/status` called **814x consecutively**
with no circuit breaker. This is the highest-risk doom loop in the bridge.
It degrades performance, clogs the log, and wastes cycles that should go to real work.

## Objective

Add a per-route call-rate circuit breaker middleware to `bridge.py` that:

1. Tracks rolling call counts per route per time window (default: 60s)
2. On N consecutive calls to the same route within the window:
   - Returns HTTP 429 with `{"error": "circuit_open", "route": ..., "retry_after_s": ...}`
   - Logs a WARNING to the `jules_bridge` logger
   - Does NOT kill the process or break unrelated routes
3. Configurable via env vars:
   - `CIRCUIT_BREAKER_THRESHOLD` (default: 20 consecutive calls)
   - `CIRCUIT_BREAKER_WINDOW_S` (default: 60)
   - `CIRCUIT_BREAKER_ENABLED` (default: 1, set to 0 to disable for tests)
4. Exempt routes: `GET /ping`, `GET /health`, `GET /dashboard/status`
   are allowed higher thresholds (200) because they are legitimately polled —
   but they still need a ceiling.

## Implementation Location

- `bridge.py` — `_circuit_breaker_check()` pre-route hook via `@app.before_request`
- `context/05_gotchas.md` — add gotcha for circuit breaker exempt routes
- `context/02_architecture.md` — add to Key Design Patterns

## Test Requirements (TDD — red first)

- `tests/test_circuit_breaker.py`
- Test: N calls within window → 429 on call N+1
- Test: counter resets after window expires
- Test: exempt route allows higher threshold
- Test: `CIRCUIT_BREAKER_ENABLED=0` disables entirely
- All 288 existing tests must still pass

## Evidence Required

- `python -m pytest tests/ -q` green with new tests
- SHA-256 recorded via `POST /retrospective/record_evidence`
- Add to `context/06_progress_tracker.md`

## Files Changed

- `bridge.py` (before_request hook + state dict)
- `tests/test_circuit_breaker.py` (new)
- `context/05_gotchas.md` (circuit breaker gotcha)
- `context/02_architecture.md` (pattern note)
- `context/06_progress_tracker.md` (mark done)
- `doc/tickets/007_dashboard_circuit_breaker.md` (this file → set Status: DONE)
