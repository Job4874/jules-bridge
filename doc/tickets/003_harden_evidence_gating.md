# Ticket 003 — Harden Evidence Gating to 423

**Status**: TODO
**Priority**: MEDIUM (soft enforcement first; harden after test discipline established)
**Phase**: Phase 6
**Depends on**: Ticket 001 (eval harness — need test-first confidence before hardening)

## Problem

Evidence gating on `/oracle/*` routes currently returns `X-Evidence-Age-Warning` header only.
This is "soft" enforcement — agents can still call Oracle routes with stale evidence.
The goal is to eventually block with HTTP 423 (Locked) when evidence is stale.

## Acceptance Criteria

- [ ] `_evidence_age_check()` in `bridge.py` updated to return `423 Locked` (not just a header)
  when `test_evidence.json` is older than the configured threshold (default: 1 hour)
- [ ] Response body on 423: `{"error": "evidence_stale", "age_s": N, "threshold_s": 3600}`
- [ ] New env var `EVIDENCE_GATE_HARD=1` controls whether it's a hard block (423) or soft warning
  — default `EVIDENCE_GATE_HARD=0` (soft) to avoid breaking existing callers
- [ ] `GET /health` exempt from gating (always passes)
- [ ] Tests added for both soft and hard modes

## Implementation Notes

- Modify ONLY `_evidence_age_check()` in bridge.py after-request hook — this is middleware
- The `EVIDENCE_GATE_HARD` env var check must be inside the hook, not at module level
- Hardening must NOT block `POST /retrospective/record_evidence` itself (infinite loop!)
- Add to gotchas: routes exempt from evidence gating: `GET /health`, `POST /retrospective/*`

## Definition of Done

`EVIDENCE_GATE_HARD=1` causes 423 on stale evidence. `EVIDENCE_GATE_HARD=0` (default) still
returns warning header only. All tests pass. Ticket status updated to DONE.
