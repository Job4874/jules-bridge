# Ticket 004 — Auto-Schedule prune_memory

**Status**: DONE
**Completed**: 2026-06-26T03:35:40Z
**Evidence SHA-256**: 5d7d1c9aadc8489d9671be5c5487dfdbf70183a8547e9ca40a8ac5536f31b1d4
**Priority**: MEDIUM
**Phase**: Phase 6

## Problem

`POST /retrospective/prune_memory` was added in Phase 5 but is never called automatically.
Memory files will grow unboundedly over time. The workshop principle: the loop should
self-maintain. Pruning is the "garbage collection" of the memory system.

## Acceptance Criteria

- [x] `analyze_session()` in `retrospective_module.py` optionally calls `prune_memory()`
  when the session log analysis completes — controlled by a param `auto_prune=False`
- [x] `POST /retrospective/analyze` route passes `auto_prune` from request body
  (default: `false` to preserve existing behaviour)
- [x] Bridge.log entry written when auto-prune fires: `INFO retrospective: auto_prune removed N sections`
- [x] Tests updated to cover `auto_prune=True` path

## Completion Notes

- `analyze_session(..., auto_prune=False)` preserves existing behavior.
- `analyze_session(..., auto_prune=True)` writes the current session memory, then runs `prune_memory(memory_path=...)`.
- The route parses `auto_prune` as a boolean and passes it through from `POST /retrospective/analyze`.
- `retrospective` logger emits `auto_prune removed N sections` when auto-prune runs.
- Added tests for default no-prune behavior, opt-in prune-after-write behavior, and route passthrough.
- Final evidence run: `python -m pytest tests/ -v` -> 172 passed, 1 warning.

## Implementation Notes

- `auto_prune` default MUST be `False` — existing callers should not be silently modified
- Prune AFTER writing the new session learning, not before (don't delete what you just wrote)
- Log the prune result using the existing logger in retrospective_module
- This is a module-level change — does NOT require bridge.py middleware changes

## Definition of Done

`POST /retrospective/analyze` with `{"auto_prune": true}` runs analysis AND prunes stale
sections. Default (no body or `auto_prune: false`) behaves identically to before. Tests pass.
Ticket status updated to DONE.
