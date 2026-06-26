# Ticket 006 — Replay Restart Orchestration (H/L/ACT)

**Status**: DONE
**Completed**: 2026-06-26T18:00:00Z
**Evidence SHA-256**: 884c12c9a702be4ffdde246eee70152128f2c54e12839753408c7fb6795f879a
**Priority**: HIGH
**Phase**: Phase 6 — Paper Trading Readiness
**Depends on**: NEXT_OBJECTIVES.md blocker — Oracle restart + MES replay chart wired

## Problem

`Restart-QuantowerLoadOracle.ps1` must be run on the Windows host to wire MES replay after profile application, but Jules Bridge has no typed module boundary for:

1. Hard-indexing canonical host paths before any orchestration
2. Running the restart script with evidence-backed post-verify (H/L/ACT halting)

Operators currently invoke raw `/shell` calls with no structured result or halt check.

## Acceptance Criteria

- [x] `hard_index_host_paths()` verifies `C:\aotp\projects\OracleV5` and `C:\Quantower\TradingPlatform`
- [x] `oracle_restart_replay(force_close=False)` runs H/L/ACT cycle:
  - **H**: hard index + info.xml exists
  - **L**: `Restart-QuantowerLoadOracle.ps1` (+ optional `-ForceClose`)
  - **ACT**: post-restart verify; halt with reason
- [x] Routes: `GET /oracle/hard-index`, `POST /oracle/restart-replay`
- [x] Unit tests mock subprocess — no live Quantower required
- [x] pytest pass + evidence SHA-256 recorded

## Definition of Done

Tests pass. Ticket status DONE. Progress tracker updated.
