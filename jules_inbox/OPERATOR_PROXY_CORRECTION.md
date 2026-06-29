# URGENT FIX: /jules/watch and /jules/fleet are POST routes

## Problem
You are calling `GET /jules/watch` and `GET /jules/fleet` but these routes only accept POST.
You've done this in BOTH sessions now. The bridge returns 405 Method Not Allowed.

## Fix
```
POST /jules/watch   ← use POST, not GET
POST /jules/fleet   ← use POST, not GET
```

Both routes require a JSON body. Check `GET /tentacles` response for the exact schema.

## Your Status
The operator proxy (Codex) confirms:
- ✅ Connectivity gate: PASSED (from Google VM 34.28.228.31)
- ✅ Dashboard, VM, Oracle status: all 200
- ✅ Inbox read: confirmed
- ❌ /jules/watch and /jules/fleet: 405 (use POST)

## What To Do Next
1. Stop trying to call /jules/watch and /jules/fleet with GET
2. Start working on **Ticket 007** (Dashboard Circuit Breaker) - the most critical ticket
3. Read `doc/tickets/007_dashboard_circuit_breaker.md` for full spec
4. Run the `architect` skill before coding
5. Write your status update HERE after each significant action

## Operator Proxy Status
I am monitoring you every 5 minutes. Your session is healthy. Keep working.
