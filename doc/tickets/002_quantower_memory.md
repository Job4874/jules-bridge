# Ticket 002 — Quantower Memory File

**Status**: TODO
**Priority**: HIGH (agents currently have no Quantower UI gotchas)
**Phase**: Phase 6

## Problem

`memory/quantower.md` exists in the architecture but has minimal content. Agents touching
`oracle_session.py` or `ui_automation.py` for Quantower-related work have no accumulated
session learnings about the Quantower UI — window titles, button positions, dialog patterns,
known failure modes.

## Acceptance Criteria

- [ ] `memory/quantower.md` expanded to include:
  - Window title patterns (`Quantower`, `Starter.exe`, title bar text after strategy load)
  - Known modal dialogs and how to dismiss them (screenshot evidence refs)
  - Connection status indicators visible in the Quantower UI
  - DLL load confirmation pattern (what to look for in the Strategy Manager)
  - Known failure modes: DLL not found, wrong architecture, strategy already running
- [ ] At least 3 `## Session` entries with real observations (can be seeded from bridge.log)
- [ ] Cross-referenced from `context/05_gotchas.md` under `## oracle_session` section

## Implementation Notes

- Mine `bridge.log` using `analyze_session()` for any Quantower-related log lines
- Screenshots in project root (`qw_*.png`) are evidence — describe what each shows
- Use the `retrospective_module.analyze_session()` flow — don't write manually if you can help it

## Definition of Done

`memory/quantower.md` has substantive content. Ticket status updated to DONE.
