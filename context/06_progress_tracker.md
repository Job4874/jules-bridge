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
| Evidence gating | Warning header | `X-Evidence-Age-Warning` on `/oracle/*`; soft enforcement first |
| Memory pruning | Age-based (30 days) | Shippable without LLM; conservative (keeps undated sections) |

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
- [x] Evidence gating — `X-Evidence-Age-Warning` header on `/oracle/*` routes
- [x] `POST /retrospective/prune_memory` — age-based pruning, 30-day default
- [x] All missing routes added to TENTACLES manifest

## Phase 6 — Ralph Loop Infrastructure ✅ (Just Added)

Added a Ralph Loop agentic framework to Jules Bridge:
- Created `doc/tickets/` with 5 Phase 6 tickets (eval harness, Quantower memory, evidence gating, auto-prune, analyze baseline)
- Created `.agents/skills/ralph-loop/SKILL.md` — full loop protocol as a reusable Claude skill
- Created `Run-RalphLoop.ps1` — Windows PowerShell autonomous loop runner

## What's Next (Phase 6 — Active Tickets)

- [ ] `doc/tickets/001_eval_harness.md` — Eval harness for reasoning_module (HIGH)
- [ ] `doc/tickets/002_quantower_memory.md` — Quantower memory file with UI gotchas (HIGH)
- [ ] `doc/tickets/003_harden_evidence_gating.md` — Harden evidence gating to 423 (MEDIUM, depends on 001)
- [ ] `doc/tickets/004_auto_prune_memory.md` — Auto-schedule prune_memory (MEDIUM)
- [ ] `doc/tickets/005_analyze_baseline.md` — Analyze baseline from real bridge.log (HIGH)

**To run the loop**: `.\Run-RalphLoop.ps1` from the project root.
