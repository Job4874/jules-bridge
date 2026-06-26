# Ticket 004 — Auto-Schedule prune_memory

**Status**: TODO
**Priority**: MEDIUM
**Phase**: Phase 6

## Problem

`POST /retrospective/prune_memory` was added in Phase 5 but is never called automatically.
Memory files will grow unboundedly over time. The workshop principle: the loop should
self-maintain. Pruning is the "garbage collection" of the memory system.

## Acceptance Criteria

- [ ] `analyze_session()` in `retrospective_module.py` optionally calls `prune_memory()`
  when the session log analysis completes — controlled by a param `auto_prune=False`
- [ ] `POST /retrospective/analyze` route passes `auto_prune` from request body
  (default: `false` to preserve existing behaviour)
- [ ] Bridge.log entry written when auto-prune fires: `INFO retrospective: auto_prune removed N sections`
- [ ] Tests updated to cover `auto_prune=True` path

## Implementation Notes

- `auto_prune` default MUST be `False` — existing callers should not be silently modified
- Prune AFTER writing the new session learning, not before (don't delete what you just wrote)
- Log the prune result using the existing logger in retrospective_module
- This is a module-level change — does NOT require bridge.py middleware changes

## Definition of Done

`POST /retrospective/analyze` with `{"auto_prune": true}` runs analysis AND prunes stale
sections. Default (no body or `auto_prune: false`) behaves identically to before. Tests pass.
Ticket status updated to DONE.
