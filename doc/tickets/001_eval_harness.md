# Ticket 001 — Eval Harness for reasoning_module

**Status**: DONE
**Completed**: 2026-06-26T03:15:00Z
**Evidence SHA-256**: 8e5b84fc116c2187d58a4b7c8520906721f619ce960398f9f323601e964d0f80
**Priority**: HIGH (blocks measuring plan quality)
**Phase**: Phase 6

## Problem

`reasoning_module.py` integrates with Gemini (`fast`/`smart` model aliases) but there is no
automated way to measure plan quality. All tests currently use `model="stub"` — we have zero
signal on whether real Gemini calls produce *better* plans than the stub.

## Acceptance Criteria

- [x] A script `tests/eval_reasoning.py` (or similar) that:
  - Calls `reason(problem, model="fast")` with at least 3 representative Jules Bridge problems
  - Records the `ReasoningTrace` for each
  - Scores each trace on: steps taken, confidence achieved, halted-early flag, plan coherence (simple heuristic OK)
  - Writes a JSON report to `memory/eval_results.json`
- [x] Running the eval does NOT require a live Quantower — use mock problems
- [x] Eval report includes a `stub_baseline` column for comparison
- [x] Evidence recorded via `POST /retrospective/record_evidence` after eval run

## Implementation Notes

- Use `reason()` from `modules/reasoning_module.py` — do NOT call Gemini directly
- Scoring heuristic: `confidence >= 0.85` = good, steps <= 5 = efficient
- Store results in `memory/eval_results.json` (not memory/*.md — it's structured data)
- Add a gotcha: eval results are JSON, not markdown — don't confuse with memory files

## Definition of Done

Tests pass. Eval script runs end-to-end with `model="stub"`. Ticket status updated to DONE.
