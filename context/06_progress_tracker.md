# Jules Bridge — Progress Tracker

> Context file 6 of 7. The ONLY file that updates constantly.
> How the agent picks up exactly where you left off in a single prompt.

## Current Phase: Phase 4 — Job Pilot Agent Skills ✅

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
| LLM stubs | Deterministic | No LLM cost until integration is needed |
| Module contract | Never raises | Partial data beats exceptions in a harness |
| Context system | 7-file + AGENTS.md | Ghost AI spec-driven approach + orchestrator |
| Gotchas over docs | ~553 lines | Guides without prescribing; smaller context |
| Agent Skills | 5 core skills | Systematize planning, continuity, review, recovery, and patterns |

## What's Complete

- [x] `modules/fs_service.py`
- [x] `modules/shell_executor.py`
- [x] `modules/ui_automation.py`
- [x] `modules/inbox_service.py`
- [x] `modules/oracle_session.py`
- [x] `modules/reasoning_module.py` (HRM H/L/ACT)
- [x] `modules/retrospective_module.py` (Nick's Case pattern)
- [x] `tests/test_reasoning_module.py` — 34 tests
- [x] `tests/test_retrospective_module.py`
- [x] `context/` — all 7 files
- [x] `.agents/AGENTS.md` — orchestrator (reading order, session protocol, skill triggers)
- [x] `memory/general.md` + `memory/oracle.md`
- [x] CDLC artifacts: HRM_AGENTS.md, HRM_UBIQUITOUS_LANGUAGE.md, hrm_context_eval.py
- [x] Reusable skills: `architect`, `remember`, `review`, `recover`, `imprint`

## What's Next (Phase 5 ideas)

- [ ] Wire `_h_module_call()` / `_l_module_call()` to real LLM provider (Gemini / Anthropic)
- [ ] Add eval harness for reasoning_module (measure plan quality with/without context)
- [ ] Quantower memory file with UI-specific gotchas
- [ ] `POST /retrospective/prune_memory` — auto-prune old/redundant learnings (Claude's autodream idea)
- [ ] Evidence gating — route returns 423 if test evidence is stale (> 1h old)
