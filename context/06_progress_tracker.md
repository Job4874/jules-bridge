# Jules Bridge — Progress Tracker

> Context file 6 of 7. The ONLY file that updates constantly.
> How the agent picks up exactly where you left off in a single prompt.

## Current Phase: Phase 5 — LLM Integration + Self-Improvement 🔄

## Phase History

### Phase 1 — Deep Module Refactor ✅
Applied Matt Pocco's deep module pattern (AI Engineer World Fair 2025).
- Extracted 5 deep modules from monolithic bridge.py
- Added 56 new unit tests
- All 14 integration tests still passing

### Phase 2 — HRM Reasoning Module ✅
Applied Hierarchical Reasoning Model architecture (Sapient Inc, June 2025).
- CDLC: Generated AGENTS.md + Ubiquitous Language for HRM repo
- Integrated reasoning_module.py with H/L/ACT pattern
- 34/34 tests passing

### Phase 3 — Harness Engineering ✅
Applied Nick Ni's "Case" harness principles (AI Engineer World Fair 2025).
- retrospective_module.py: reads bridge.log, detects doom loops, writes memory
- Six-file context system: context/01-06
- memory/ directory with per-domain markdown files
- 3 new retrospective routes

### Phase 4 — Job Pilot Agent Skills ✅ (Current)
Applied JSM/Job Pilot Agent Skills to Jules Bridge.
- Created 5 core agent skills: architect, remember, review, recover, imprint in `.agents/skills/`
- Updated workflow rules in `context/04_ai_workflow_rules.md`

## Active Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Memory format | Markdown files | Human + agent readable; matches Nick's Case |
| Evidence storage | SHA-256 in JSON | Cryptographic proof; cannot be faked |
| LLM integration | Gemini via alias system | No new API key; `fast`/`smart` aliases hide provider details |
| Module contract | Never raises | Partial data beats exceptions in a harness |
| Context system | 7-file + AGENTS.md | Ghost AI spec-driven approach + orchestrator |
| Gotchas over docs | ~553 lines | Guides without prescribing; smaller context |
| Agent Skills | 5 core skills | Systematize planning, continuity, review, recovery, and patterns |
| Evidence gating | Soft default, opt-in hard mode | `X-Evidence-Age-Warning` on stale `/oracle/*`; `EVIDENCE_GATE_HARD=1` returns 423 |
| Memory pruning | Age-based, opt-in auto-prune | `analyze_session(auto_prune=True)` writes current memory first, then prunes stale dated sections |

## What's Complete

- [x] `modules/fs_service.py`
- [x] `modules/shell_executor.py`
- [x] `modules/ui_automation.py`
- [x] `modules/inbox_service.py`
- [x] `modules/oracle_session.py`
- [x] `modules/reasoning_module.py` (HRM H/L/ACT + Gemini integration)
- [x] `modules/retrospective_module.py` (Nick's Case pattern + `prune_memory`)
- [x] `tests/test_reasoning_module.py` — 34 tests
- [x] `tests/test_retrospective_module.py`
- [x] `context/` — all 7 files
- [x] `.agents/AGENTS.md` — orchestrator (reading order, session protocol, skill triggers)
- [x] `memory/general.md` + `memory/oracle.md`
- [x] CDLC artifacts: HRM_AGENTS.md, HRM_UBIQUITOUS_LANGUAGE.md, hrm_context_eval.py
- [x] Reusable skills: `architect`, `remember`, `review`, `recover`, `imprint`
- [x] `GET /health` — fixes 404 storm; returns uptime; listed in TENTACLES
- [x] Gemini wired to `reasoning_module` via `_MODEL_ALIASES` (`fast`/`smart`/`stub`)
- [x] Evidence gating — `X-Evidence-Age-Warning` header on stale `/oracle/*` routes, with opt-in `EVIDENCE_GATE_HARD=1` HTTP 423 hard mode
- [x] `POST /retrospective/prune_memory` — age-based pruning, 30-day default
- [x] All missing routes added to TENTACLES manifest
- [x] `modules/akc_module.py` — Agent Knowledge Context checkpoint builder with source inventory, path-ref masking, operating rules, and `/akc/context` routes
- [x] `GET /akc/readiness` — session-start gate that verifies the AKC checkpoint exists, is `ready`, and contains required operating rules
- [x] `context/08_akc_context_checkpoint.md` — generated from 5 pasted transcript sources; status `ready`, readable=5, missing=0, operating_rule_count=9
- [x] Evidence parser hardened — pytest output with test names containing `failed` no longer records false failed evidence
- [x] `doc/tickets/001_eval_harness.md` — `tests/eval_reasoning.py` writes `memory/eval_results.json` with 3 representative reasoning problems, trace rows, scoring heuristics, and `stub_baseline`
- [x] `doc/tickets/002_quantower_memory.md` — `memory/quantower.md` now records Quantower window patterns, Strategy Manager evidence, connection indicators, screenshot refs, and failure modes
- [x] `doc/tickets/005_analyze_baseline.md` — `POST /retrospective/analyze` seeded real `bridge.log` learnings into `memory/general.md` and `memory/oracle.md`; evidence `d8a29098bcb0195ae05c03f940372e2b2e59b92337fa001122047b58e0f220a0`
- [x] `doc/tickets/003_harden_evidence_gating.md` — stale `/oracle/*` evidence can preempt route execution with HTTP 423 when `EVIDENCE_GATE_HARD=1`; evidence `5d7d1c9aadc8489d9671be5c5487dfdbf70183a8547e9ca40a8ac5536f31b1d4`
- [x] `doc/tickets/004_auto_prune_memory.md` — `POST /retrospective/analyze` accepts boolean `auto_prune` and prunes stale memory after writing current learnings; evidence `5d7d1c9aadc8489d9671be5c5487dfdbf70183a8547e9ca40a8ac5536f31b1d4`

## Phase 6 — Ralph Loop Infrastructure ✅ (Just Added)

Added a Ralph Loop agentic framework to Jules Bridge:
- Created `doc/tickets/` with 5 Phase 6 tickets (eval harness, Quantower memory, evidence gating, auto-prune, analyze baseline)
- Created `.agents/skills/ralph-loop/SKILL.md` — full loop protocol as a reusable Claude skill
- Created `Run-RalphLoop.ps1` — Windows PowerShell autonomous loop runner

## What's Next (Phase 6 — Active Tickets)

- [x] No active Phase 6 tickets remain in `doc/tickets/`.

**To run the loop**: `.\Run-RalphLoop.ps1` from the project root.
