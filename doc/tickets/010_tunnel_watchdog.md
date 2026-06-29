# Ticket 010 — Ngrok Tunnel Health Watchdog

Status: OPEN

## Priority: CRITICAL

## Root Cause

The ngrok tunnel is a **single point of failure**. When it dies, Jules on the
remote VM loses all tool access (shell, UI, Oracle, screenshots, inbox write).
He cannot restart it himself. Sessions stall at "Awaiting User" and the operator
has to manually intervene every time.

On 2026-06-28, the tunnel was dead for **7+ hours** causing 5 sessions to stall
or fail without Jules being able to communicate what was wrong.

## Objective

Add a tunnel health watchdog to `start.py` that:

1. Checks public tunnel reachability every 60s via `GET /ping` on the ngrok URL
2. After 3 consecutive failures:
   - Kills the stale ngrok process
   - Reconnects via `pyngrok.ngrok.connect()`
   - Logs the reconnection attempt and result
3. Writes `TUNNEL_HEALTH.json` to `jules_inbox/` with:
   - `status`: "healthy" | "reconnecting" | "dead"
   - `last_check_utc`: ISO timestamp
   - `consecutive_failures`: int
   - `last_reconnect_utc`: ISO timestamp or null
   - `uptime_s`: seconds since last successful connect
4. If reconnection fails 3 times in a row, writes a blocker to
   `jules_inbox/TUNNEL_BLOCKER.md` so Jules can at least read it via git

## Implementation

- `start.py` — add `_tunnel_watchdog()` thread that runs alongside the flask process loop
- `jules_inbox/TUNNEL_HEALTH.json` — written every health check cycle
- `jules_inbox/TUNNEL_BLOCKER.md` — written only on persistent failure

## Offline Escalation Path

When tunnel is confirmed dead and cannot self-heal:
1. Jules writes blocker to `JULES_RESPONSE.md` via **git commit + push** (not via bridge)
2. The commit message includes `[TUNNEL_DEAD]` tag
3. This gives the operator visibility even when the bridge is unreachable

## Test Requirements

- `tests/test_tunnel_watchdog.py`
- Test: mock ping success → status healthy
- Test: mock 3 failures → reconnect attempted
- Test: mock reconnect failure → blocker file written
- All existing tests must still pass

## Files Changed

- `start.py` (watchdog thread)
- `tests/test_tunnel_watchdog.py` (new)
- `doc/tickets/010_tunnel_watchdog.md` (this file → set Status: DONE)
